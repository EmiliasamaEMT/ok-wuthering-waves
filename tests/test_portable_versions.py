import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from dulwich import porcelain
from pyappify import standalone


SCRIPT = Path(__file__).resolve().parents[1] / ".github/scripts/fix_portable_versions.py"
spec = importlib.util.spec_from_file_location("fix_portable_versions", SCRIPT)
fixer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixer)


LAUNCHER = ('@echo off\r\nsetlocal\r\n'
            'set "PYAPPIFY_APP_VERSION=v0.1.0-beta.1"\r\n'
            'set "PYAPPIFY_APP_STARTING_VERSION=v0.1.0-beta.1"\r\n'
            'set "PYAPPIFY_APP_PROFILE=QA"\r\n'
            'set "PYAPPIFY_UPGRADEABLE=0"\r\n')


class TestPortableLauncher(unittest.TestCase):
    def test_clears_only_cached_versions_and_preserves_controls_and_line_endings(self):
        patched = fixer.patch_launcher(LAUNCHER.encode("utf-8"))
        self.assertEqual(
            patched,
            LAUNCHER.replace("=v0.1.0-beta.1", "=").encode("utf-8"),
        )
        self.assertEqual(fixer.patch_launcher(patched), patched)

    def test_preserves_utf8_bom_and_non_ascii_text(self):
        content = b"\xef\xbb\xbf" + ("rem mc小帮手\r\n" + LAUNCHER).encode("utf-8")
        self.assertEqual(fixer.patch_launcher(content), content.replace(b"=v0.1.0-beta.1", b"="))

    def test_rejects_missing_or_duplicate_version_assignments(self):
        for text in (LAUNCHER.replace('set "PYAPPIFY_APP_VERSION=v0.1.0-beta.1"\r\n', ''),
                     LAUNCHER + 'set "PYAPPIFY_APP_VERSION=v0.1.0-beta.2"\r\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                fixer.patch_launcher(text.encode("utf-8"))

    def test_rejects_launcher_upgrade_mode(self):
        with self.assertRaises(ValueError):
            fixer.patch_launcher(LAUNCHER.replace("UPGRADEABLE=0", "UPGRADEABLE=1").encode("utf-8"))

    @unittest.skipUnless(os.name == "nt", "portable CMD execution requires Windows")
    def test_fresh_cmd_launch_follows_managed_checkout_after_update(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            repo = porcelain.init(str(source))
            commits = []
            try:
                for number in (1, 2):
                    (source / "marker.txt").write_text(str(number), encoding="utf-8")
                    porcelain.add(repo, ["marker.txt"])
                    commit = porcelain.commit(repo, message=f"Version {number}".encode(),
                                              author=b"QA <qa@example.invalid>",
                                              committer=b"QA <qa@example.invalid>")
                    repo.refs[f"refs/tags/v0.1.0-beta.{number}".encode()] = commit
                    commits.append(commit)
            finally:
                repo.close()
            base = root / "mc-helper/data/apps/mc-helper"
            base.mkdir(parents=True)
            managed = porcelain.clone(str(source), str(base / "repo"), bare=True)
            managed.close()
            probe = root / "probe.py"
            probe.write_text("import json,pyappify; print(json.dumps([pyappify.app_version,"
                             "pyappify.app_starting_version]))", encoding="utf-8")
            launcher = root / "mc-helper.cmd"
            launcher.write_bytes(fixer.patch_launcher(LAUNCHER.encode("utf-8")) +
                                 f'"{sys.executable}" "{probe}"\r\n'.encode("utf-8"))
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith("PYAPPIFY_")}
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONNOUSERSITE"] = "1"
            for number, commit in enumerate(commits, 1):
                with standalone.open_repo(str(base / "repo")) as managed:
                    porcelain.checkout(managed, managed[commit], force=True)
                result = subprocess.run([os.environ["COMSPEC"], "/d", "/c", str(launcher)],
                                        cwd=base / "working", env=env, capture_output=True,
                                        text=True, encoding="utf-8", check=True)
                self.assertEqual(json.loads(result.stdout.strip()),
                                 [f"v0.1.0-beta.{number}"] * 2)


if __name__ == "__main__":
    unittest.main()
