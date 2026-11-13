import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
from wsgiref.simple_server import WSGIRequestHandler, make_server

from dulwich import porcelain
from dulwich.file import GitFile
from dulwich.objects import Commit, Tag
from dulwich.repo import Repo
from dulwich.web import ChunkReader
from pyappify import standalone

from src.update_repo import HAVE_REF, OWNER_FILE, prepare_update_repository


class QuietRequestHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


class TestUpdateRepository(unittest.TestCase):
    def setUp(self):
        # Test files remain available for runner cleanup; no recursive deletion.
        self.root = Path(tempfile.mkdtemp(prefix="mc-helper-update-repo-"))
        self.source_path = self.root / "source"
        self.source_path.mkdir()
        self.source = porcelain.init(str(self.source_path))
        self.addCleanup(self.source.close)
        (self.source_path / "asset.bin").write_bytes(os.urandom(512 * 1024))
        (self.source_path / "main.py").write_text("pass\n")
        self.first = self.version(1)

    def version(self, number):
        (self.source_path / "version.txt").write_text(str(number))
        porcelain.add(self.source)
        commit = porcelain.commit(self.source, message=f"Version {number}".encode(),
                                  author=b"QA <qa@example.invalid>", committer=b"QA <qa@example.invalid>")
        tag = Tag()
        tag.name = f"v0.1.0-beta.{number}".encode()
        tag.object = (Commit, commit)
        tag.tagger = b"QA <qa@example.invalid>"
        tag.tag_time, tag.tag_timezone = 1700000000 + number, 0
        tag.message = b"Preview\n"
        self.source.object_store.add_object(tag)
        self.source.refs[b"refs/tags/" + tag.name] = tag.id
        return commit

    def install(self, label="client"):
        base = self.root / label / "data/apps/mc-helper"
        working = base / "working"
        working.mkdir(parents=True)
        (working / "main.py").write_text("pass\n")
        (base / "app.json").write_text(json.dumps({"name": "mc-helper", "installed": True}))
        repo_path = base / "repo"
        repo_path.mkdir()
        repo = Repo.init_bare(str(repo_path))
        for oid in self.source.object_store:
            repo.object_store.add_object(self.source[oid])
        # Assigning through refs follows an unborn HEAD; native bundles detach it.
        (repo_path / "HEAD").write_bytes(self.first + b"\n")
        tag = b"refs/tags/v0.1.0-beta.1"
        repo.refs[tag] = self.source.refs[tag]
        (repo_path / "shallow").write_bytes(self.first + b"\n")
        self.addCleanup(repo.close)
        return base, working / "main.py", repo

    def test_tag_only_repo_gains_head_without_changing_version_metadata(self):
        base, entry, repo = self.install()
        self.assertIsNone(repo.get_graph_walker().next())
        tags = repo.refs.as_dict(b"refs/tags")
        config = (base / "repo/config").read_bytes()
        shallow = (base / "repo/shallow").read_bytes()
        self.assertIsNone(prepare_update_repository(entry, {}))
        self.assertEqual(repo.get_graph_walker().next(), self.first)
        self.assertEqual(repo.refs[HAVE_REF], self.first)
        self.assertEqual(repo.head(), self.first)
        self.assertEqual(repo.refs.as_dict(b"refs/tags"), tags)
        self.assertEqual((base / "repo/config").read_bytes(), config)
        self.assertEqual((base / "repo/shallow").read_bytes(), shallow)
        before = (base / "repo/refs/heads/mc-helper-current").stat().st_mtime_ns
        self.assertIsNone(prepare_update_repository(entry, {}))
        self.assertEqual((base / "repo/refs/heads/mc-helper-current").stat().st_mtime_ns, before)

    def test_reference_follows_upgrade_and_rollback(self):
        base, entry, repo = self.install()
        self.assertIsNone(prepare_update_repository(entry, {}))
        second = self.version(2)
        for oid in self.source.object_store:
            repo.object_store.add_object(self.source[oid])
        for head in (second, self.first):
            repo.refs[b"HEAD"] = head
            self.assertIsNone(prepare_update_repository(entry, {}))
            self.assertEqual(repo.refs[HAVE_REF], head)
            self.assertEqual(repo.head(), head)

    def test_development_checkout_is_unchanged(self):
        before = self.source.refs.as_dict()
        config = (self.source_path / ".git/config").read_bytes()
        self.assertIsNone(prepare_update_repository(self.source_path / "main.py", {}))
        self.assertEqual(self.source.refs.as_dict(), before)
        self.assertEqual((self.source_path / ".git/config").read_bytes(), config)

    def test_environment_redirect_is_rejected(self):
        base, entry, repo = self.install()
        for name in ("PYAPPIFY_REPO_PATH", "PYAPPIFY_APP_JSON_PATH"):
            with self.subTest(name=name):
                self.assertIn("outside", prepare_update_repository(entry, {name: str(self.source_path)}))
                self.assertNotIn(HAVE_REF, repo.refs)

    def test_preparation_failure_does_not_block_startup(self):
        with patch("src.update_repo.Path.resolve", side_effect=OSError("unavailable")):
            self.assertIn("unavailable", prepare_update_repository("main.py", {}))

    def test_unowned_or_symbolic_reference_is_not_overwritten(self):
        base, entry, repo = self.install()
        repo.refs[HAVE_REF] = self.first
        self.assertIn("another caller", prepare_update_repository(entry, {}))
        self.assertFalse((base / "repo" / OWNER_FILE).exists())
        target = b"refs/heads/user-owned"
        repo.refs[target] = self.first
        repo.refs.set_symbolic_ref(HAVE_REF, target)
        self.assertIn("symbolic", prepare_update_repository(entry, {}))
        self.assertEqual(repo.refs.read_ref(HAVE_REF), b"ref: " + target)
        self.assertEqual(repo.refs[target], self.first)

    def test_lock_contention_does_not_change_reference(self):
        base, entry, repo = self.install()
        path = base / "repo/refs/heads/mc-helper-current"
        path.parent.mkdir(parents=True, exist_ok=True)
        locked = GitFile(str(path), "wb")
        try:
            self.assertIn("Unable to prepare", prepare_update_repository(entry, {}))
            self.assertNotIn(HAVE_REF, repo.refs)
        finally:
            locked.abort()

    def test_concurrent_head_change_aborts_the_reference_write(self):
        base, entry, repo = self.install()
        second = self.version(2)
        for oid in self.source.object_store:
            repo.object_store.add_object(self.source[oid])

        def change_head(filename, mode):
            locked = GitFile(filename, mode)
            repo.refs[b"HEAD"] = second
            return locked

        with patch("dulwich.file.GitFile", side_effect=change_head):
            self.assertIn("HEAD changed", prepare_update_repository(entry, {}))
        self.assertNotIn(HAVE_REF, repo.refs)
        self.assertEqual(repo.head(), second)

    def test_http_fetch_reuses_large_unchanged_blob(self):
        old_base, old_entry, old = self.install("unfixed")
        fixed_base, fixed_entry, fixed = self.install("fixed")
        second = self.version(2)
        self.assertIsNone(prepare_update_repository(fixed_entry, {}))
        git = shutil.which("git")
        self.assertIsNotNone(git, "Git is required for the HTTP interoperability test")
        server_repo = porcelain.clone(str(self.source_path), str(self.root / "server.git"), bare=True)
        self.addCleanup(server_repo.close)

        def application(environ, start_response):
            path = environ.get("PATH_INFO", "")
            if path not in ("/server.git/info/refs", "/server.git/git-upload-pack"):
                start_response("404 Not Found", [("Content-Type", "text/plain")])
                return [b"Not found"]
            if environ.get("HTTP_TRANSFER_ENCODING") == "chunked":
                body = ChunkReader(environ["wsgi.input"]).read(1024 * 1024)
            else:
                body = environ["wsgi.input"].read(int(environ.get("CONTENT_LENGTH") or 0))
            env = dict(os.environ, GIT_PROJECT_ROOT=str(self.root), GIT_HTTP_EXPORT_ALL="1",
                       REQUEST_METHOD=environ["REQUEST_METHOD"], PATH_INFO=path,
                       QUERY_STRING=environ.get("QUERY_STRING", ""),
                       CONTENT_TYPE=environ.get("CONTENT_TYPE", ""), CONTENT_LENGTH=str(len(body)))
            if environ.get("HTTP_GIT_PROTOCOL"):
                env["GIT_PROTOCOL"] = environ["HTTP_GIT_PROTOCOL"]
            process = subprocess.run([git, "http-backend"], input=body, env=env,
                                     capture_output=True, timeout=20)
            if process.returncode:
                raise RuntimeError(process.stderr.decode("utf-8", "replace"))
            separator = b"\r\n\r\n" if b"\r\n\r\n" in process.stdout else b"\n\n"
            raw_headers, response_body = process.stdout.split(separator, 1)
            headers, status = [], "200 OK"
            for line in raw_headers.decode("iso-8859-1").splitlines():
                name, value = line.split(":", 1)
                if name.lower() == "status":
                    status = value.strip()
                else:
                    headers.append((name, value.strip()))
            start_response(status, headers)
            return [response_body]

        server = make_server("127.0.0.1", 0, application, handler_class=QuietRequestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        received = []
        try:
            for base, repo in ((old_base, old), (fixed_base, fixed)):
                config = repo.get_config()
                config.set((b"remote", b"origin"), b"url", f"http://127.0.0.1:{server.server_port}/server.git".encode())
                config.write_to_path()
                before = sum(p.stat().st_size for p in (base / "repo/objects/pack").glob("*.pack"))
                updated, _ = standalone.fetch_tags(str(base / "repo"))
                after = sum(p.stat().st_size for p in (base / "repo/objects/pack").glob("*.pack"))
                received.append(after - before)
                self.assertIn("v0.1.0-beta.2", updated)
                target = repo[repo.refs[b"refs/tags/v0.1.0-beta.2"]].object[1]
                self.assertEqual(target, second)
                marker = repo[repo[second].tree][b"version.txt"][1]
                self.assertEqual(repo[marker].data, b"2")
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
        self.assertGreater(received[0], 512 * 1024)
        self.assertLess(received[1], 16 * 1024)
        print(f"HTTP fetch pack bytes: before={received[0]}, after={received[1]}")


if __name__ == "__main__":
    unittest.main()
