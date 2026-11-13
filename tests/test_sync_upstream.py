import copy
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sync_upstream", ROOT / ".github/scripts/sync_upstream.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def git(root, *args):
    return subprocess.check_output(["git", "-c", "user.name=Tester", "-c", "user.email=test@example.invalid",
                                    *args], cwd=root, text=True, encoding="utf-8", stderr=subprocess.PIPE).strip()


class FakeGitHub:
    def __init__(self, remote):
        self.remote = remote
        self.prs = []
        self.statuses = []
        self.fail_create = False

    def __call__(self, method, path, payload=None):
        if path == "/git/ref/heads/dev":
            return {"object": {"sha": git(self.remote, "rev-parse", "refs/heads/dev")}}
        for pr in self.prs:
            pr["head"]["sha"] = git(self.remote, "rev-parse", "refs/heads/" + sync.SYNC_BRANCH)
        if path.startswith("/pulls?"):
            return copy.deepcopy(self.prs)
        if path == "/pulls" and method == "POST":
            if self.fail_create:
                raise sync.SyncError("Simulated PR API failure after push")
            pr = dict(payload, number=len(self.prs) + 1, state="open", merged_at=None,
                      user={"login": sync.BOT},
                      head={"ref": sync.SYNC_BRANCH, "sha": git(self.remote, "rev-parse", sync.SYNC_BRANCH),
                            "repo": {"full_name": sync.FORK}},
                      base={"ref": "dev", "repo": {"full_name": sync.FORK}})
            self.prs.append(pr)
            return copy.deepcopy(pr)
        if path.startswith("/pulls/"):
            pr = self.prs[int(path.rsplit("/", 1)[1]) - 1]
            if method == "PATCH":
                pr.update(payload)
            return copy.deepcopy(pr)
        if path.startswith("/statuses/"):
            self.statuses.append(dict(payload, sha=path.rsplit("/", 1)[1]))
            return {}
        raise AssertionError((method, path))


class TestSyncUpstream(unittest.TestCase):
    def setUp(self):
        # Small local repositories only. Leave fixtures intact; no recursive cleanup.
        self.root = Path(tempfile.mkdtemp(prefix="mc-helper-sync-"))
        self.upstream = self.root / "upstream"
        self.upstream.mkdir()
        git(self.upstream, "init", "-b", "master")
        self.commit(self.upstream, "game.txt", "base", "Base")
        self.remote = self.root / "fork.git"
        git(self.root, "init", "--bare", str(self.remote))
        self.work = self.root / "work"
        git(self.root, "clone", "--no-tags", str(self.upstream), str(self.work))
        git(self.work, "switch", "-c", "dev")
        self.commit(self.work, "identity.txt", "mc-helper", "Fork identity")
        git(self.work, "remote", "set-url", "origin", str(self.remote))
        git(self.work, "push", "origin", "dev")
        self.api = FakeGitHub(self.remote)
        self.clones = 0

    def commit(self, root, relative, text, message):
        (root / relative).write_text(text, encoding="utf-8")
        git(root, "add", relative)
        git(root, "commit", "-m", message)

    def advance(self):
        self.commit(self.upstream, "new-game.txt", "upstream improvement", "Upstream improvement")
        git(self.upstream, "tag", "v99.0.0")

    def fresh(self):
        self.clones += 1
        work = self.root / f"fresh{self.clones}"
        git(self.root, "clone", "--no-tags", "--branch", "dev", str(self.remote), str(work))
        return work

    def run_sync(self, work=None, **kwargs):
        return sync.synchronize(work or self.work, self.api, upstream_url=str(self.upstream),
                                run_url="https://github.com/example/run/1", **kwargs)

    def test_clean_merge_preserves_fork_ancestry_and_publishes_no_tags(self):
        self.advance()
        git(self.work, "config", "push.followTags", "true")
        git(self.work, "tag", "-a", "v0.1.9", "-m", "Local tag must not be published by synchronization")
        result = self.run_sync()
        self.assertEqual(result["mode"], "candidate")
        self.assertEqual((self.work / "identity.txt").read_text(), "mc-helper")
        self.assertTrue((self.work / "new-game.txt").exists())
        self.assertEqual(len(git(self.work, "show", "-s", "--format=%P", result["head_sha"]).split()), 2)
        self.assertEqual(git(self.remote, "tag", "--list"), "")
        self.assertNotIn("v99.0.0", git(self.work, "tag", "--list"))
        self.assertTrue(self.api.prs[0]["draft"])
        self.assertEqual(self.run_sync(self.fresh())["mode"], "unchanged_pr")

    def test_up_to_date_and_optional_current_checks(self):
        self.assertEqual(self.run_sync()["head_sha"], "")
        result = self.run_sync(check_current=True)
        self.assertEqual(result["head_sha"], result["base_sha"])
        self.assertEqual(self.api.prs, [])

    def test_conflict_publishes_nothing(self):
        self.commit(self.work, "game.txt", "fork value", "Fork change")
        git(self.work, "push", "origin", "dev")
        self.commit(self.upstream, "game.txt", "upstream value", "Conflicting change")
        with self.assertRaisesRegex(sync.SyncError, "Conflict paths"):
            self.run_sync()
        self.assertEqual(git(self.remote, "ls-remote", "--heads", str(self.remote), sync.SYNC_BRANCH), "")
        self.assertEqual(self.api.prs, [])

    def test_manual_commit_on_sync_branch_is_not_overwritten(self):
        self.advance()
        result = self.run_sync()
        self.commit(self.work, "human.txt", "manual fix", "Human review")
        git(self.work, "push", "origin", "HEAD:refs/heads/" + sync.SYNC_BRANCH)
        human = git(self.work, "rev-parse", "HEAD")
        self.assertNotEqual(result["head_sha"], human)
        with self.assertRaisesRegex(sync.SyncError, "manual commits"):
            self.run_sync(self.fresh())
        self.assertEqual(git(self.remote, "rev-parse", sync.SYNC_BRANCH), human)

    def test_concurrent_remote_update_rejects_lease(self):
        self.advance()
        result = self.run_sync()
        candidate = self.work
        other = self.root / "other"
        git(self.root, "clone", "--branch", sync.SYNC_BRANCH, str(self.remote), str(other))
        self.commit(other, "human.txt", "keep", "Concurrent edit")
        git(other, "push", "origin", sync.SYNC_BRANCH)
        human = git(other, "rev-parse", "HEAD")
        with self.assertRaises(sync.SyncError):
            sync.push_candidate(sync.Git(candidate), result["head_sha"])
        self.assertEqual(git(self.remote, "rev-parse", sync.SYNC_BRANCH), human)

    def test_pr_creation_recovers_after_push_succeeded(self):
        self.advance()
        self.api.fail_create = True
        with self.assertRaisesRegex(sync.SyncError, "API failure"):
            self.run_sync()
        pushed = git(self.remote, "rev-parse", sync.SYNC_BRANCH)
        self.api.fail_create = False
        result = self.run_sync(self.fresh())
        self.assertEqual(result["head_sha"], pushed)
        self.assertEqual(len(self.api.prs), 1)

    def test_new_base_regenerates_owned_merge_and_preserves_pr_notes(self):
        self.advance()
        old = self.run_sync()
        self.api.prs[0]["body"] += "\nMaintainer review notes"
        work = self.fresh()
        self.commit(work, "fork-new.txt", "new", "Fork advanced")
        git(work, "push", "origin", "dev")
        result = self.run_sync(self.fresh())
        self.assertNotEqual(old["head_sha"], result["head_sha"])
        self.assertEqual(len(self.api.prs), 1)
        self.assertIn("Maintainer review notes", self.api.prs[0]["body"])

    def test_closed_pr_is_not_reopened_automatically(self):
        self.advance()
        self.run_sync()
        self.api.prs[0]["state"] = "closed"
        self.assertEqual(self.run_sync(self.fresh())["mode"], "closed_pr_preserved")
        self.assertEqual(len(self.api.prs), 1)

    def test_failed_skipped_or_cancelled_checks_cannot_publish_success(self):
        self.advance()
        result = self.run_sync()
        for outcome in ["failure", "skipped", "cancelled", "success"]:
            state = sync.publish_status(self.api, result["base_sha"], result["head_sha"], 1, outcome, "https://example/run")
            self.assertEqual(state, "success" if outcome == "success" else "failure")

    def test_base_or_head_movement_prevents_success_status(self):
        self.advance()
        result = self.run_sync()
        work = self.fresh()
        self.commit(work, "later.txt", "later", "Base advanced")
        git(work, "push", "origin", "dev")
        self.assertEqual(sync.publish_status(self.api, result["base_sha"], result["head_sha"], 1,
                                            "success", "https://example/run"), "failure")
        self.commit(self.work, "human.txt", "human", "Head advanced")
        git(self.work, "push", "origin", "HEAD:refs/heads/" + sync.SYNC_BRANCH)
        self.assertEqual(sync.publish_status(self.api, result["base_sha"], result["head_sha"], 1,
                                            "success", "https://example/run"), "failure")

    def test_pr_without_owner_marker_is_not_modified(self):
        self.advance()
        self.run_sync()
        self.api.prs[0]["body"] = "Human-owned PR"
        with self.assertRaisesRegex(sync.SyncError, "ownership"):
            self.run_sync(self.fresh())

    def test_candidate_job_has_no_write_permissions_or_persisted_credentials(self):
        workflow = yaml.load((ROOT / ".github/workflows/upstream-sync.yml").read_text(), Loader=yaml.BaseLoader)
        checks = workflow["jobs"]["checks"]
        self.assertEqual(checks["permissions"], {"contents": "read"})
        for step in checks["steps"]:
            if step.get("uses", "").startswith("actions/checkout@"):
                self.assertEqual(step["with"]["persist-credentials"], "false")
        self.assertNotIn("secrets.", str(checks))
        self.assertEqual(workflow["concurrency"]["cancel-in-progress"], "false")


if __name__ == "__main__":
    unittest.main()
