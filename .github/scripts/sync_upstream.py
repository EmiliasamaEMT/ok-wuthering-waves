"""Prepare a reviewable upstream merge; never execute merged application code."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FORK = "EmiliasamaEMT/ok-wuthering-waves"
UPSTREAM = "https://github.com/ok-oldking/ok-wuthering-waves.git"
BASE_BRANCH = "dev"
SYNC_BRANCH = "codex/upstream-sync"
BOT = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
MARKER = "<!-- mc-helper:upstream-sync -->"
END_MARKER = "<!-- /mc-helper:upstream-sync -->"
SHA = re.compile(r"^[0-9a-f]{40}$")


class SyncError(RuntimeError):
    pass


class Git:
    def __init__(self, root):
        self.root = Path(root)

    def run(self, *args, check=True, env=None):
        process_env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1", GIT_TERMINAL_PROMPT="0")
        process_env.update(env or {})
        result = subprocess.run(["git", "-c", "core.hooksPath=" + str(self.root / ".git/no-hooks"),
                                 "-c", "user.name=" + BOT, "-c", "user.email=" + BOT_EMAIL, *args],
                                cwd=self.root, env=process_env, capture_output=True,
                                text=True, encoding="utf-8", errors="replace")
        if check and result.returncode:
            raise SyncError(f"git {args[0]} failed: {result.stderr.strip()[:2000]}")
        return result.stdout.strip() if check else result


class GitHub:
    def __init__(self, token):
        self.token = token

    def __call__(self, method, path, payload=None):
        request = Request("https://api.github.com/repos/" + FORK + path,
                          data=json.dumps(payload).encode() if payload is not None else None,
                          method=method, headers={"Authorization": "Bearer " + self.token,
                          "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
        with urlopen(request, timeout=45) as response:
            body = response.read()
            return json.loads(body) if body else {}


def owned_commit(git, commit):
    name, email, parents, message = git.run("show", "-s", "--format=%an%x00%ae%x00%P%x00%B", commit).split("\0", 3)
    base = re.findall(r"^Base: ([0-9a-f]{40})$", message, re.MULTILINE)
    upstream = re.findall(r"^Upstream: ([0-9a-f]{40})$", message, re.MULTILINE)
    if (name != BOT or email != BOT_EMAIL or "MC-Helper-Sync: 1" not in message.splitlines()
            or len(base) != 1 or len(upstream) != 1 or parents.split() != base + upstream):
        raise SyncError("The sync branch contains unrecognized or manual commits; leave it unchanged and review it manually.")
    return base[0], upstream[0]


def owned_pr(pr, expected_head):
    if (pr.get("user", {}).get("login") != BOT
            or (pr.get("head", {}).get("repo") or {}).get("full_name") != FORK
            or (pr.get("base", {}).get("repo") or {}).get("full_name") != FORK
            or pr.get("head", {}).get("ref") != SYNC_BRANCH
            or pr.get("base", {}).get("ref") != BASE_BRANCH
            or pr.get("head", {}).get("sha") != expected_head
            or (pr.get("body") or "").count(MARKER) != 1
            or (pr.get("body") or "").count(END_MARKER) != 1):
        raise SyncError("The existing PR has unexpected ownership, refs or markers; leave it unchanged.")


def current_base(api):
    return api("GET", "/git/ref/heads/" + BASE_BRANCH)["object"]["sha"]


def pr_body(base, upstream, run_url):
    return (f"{MARKER}\n"
            "## 同步上游 master\n\n"
            f"- 定制基线：`{base}`\n- 上游提交：`{upstream}`\n"
            f"- [自动检查与合并记录]({run_url})\n\n"
            "此 PR 由自动同步流程生成，保留上游提交关系。自动检查包含名称、更新源、更新兼容依赖和测试。"
            "请查看 `mc-helper/upstream-sync` 状态与运行日志；普通 PR 工作流若显示等待批准，可在 PR 页批准运行。\n\n"
            "请人工审核后合并；发布自己的版本仍需单独创建本 fork 的标签。"
            "本流程仅推送同步分支，不推送上游标签、不合并 PR、不发布版本。\n"
            f"{END_MARKER}")


def ensure_pr(api, existing, base, upstream, run_url):
    body = pr_body(base, upstream, run_url)
    title = "Sync upstream master (" + upstream[:7] + ")"
    if existing:
        old = existing["body"]
        start, end = old.index(MARKER), old.index(END_MARKER) + len(END_MARKER)
        return api("PATCH", f"/pulls/{existing['number']}", {"title": title, "body": old[:start] + body + old[end:]})
    return api("POST", "/pulls", {"title": title, "body": body, "head": SYNC_BRANCH,
                                  "base": BASE_BRANCH, "draft": True, "maintainer_can_modify": True})


def push_candidate(git, expected):
    # No persisted credentials and no tags, including when push.followTags is set globally.
    git.run("-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential",
            "push", "--no-follow-tags", "--force-with-lease=refs/heads/" + SYNC_BRANCH + ":" + expected,
            "origin", "HEAD:refs/heads/" + SYNC_BRANCH)


def synchronize(root, api, upstream_url=UPSTREAM, check_current=False, run_url=""):
    git = Git(root)
    if git.run("status", "--porcelain"):
        raise SyncError("Start from a clean, disposable checkout of dev.")
    base = git.run("rev-parse", "HEAD")
    if current_base(api) != base:
        raise SyncError("dev moved before preparation; run synchronization again.")
    git.run("fetch", "--no-tags", "--no-recurse-submodules", upstream_url,
            "refs/heads/master:refs/remotes/mc-helper-upstream/master")
    upstream = git.run("rev-parse", "refs/remotes/mc-helper-upstream/master")
    remote = git.run("ls-remote", "--heads", "origin", "refs/heads/" + SYNC_BRANCH)
    expected = remote.split()[0] if remote else ""
    query = urlencode({"state": "all", "head": FORK.split('/')[0] + ":" + SYNC_BRANCH,
                       "sort": "created", "direction": "desc", "per_page": 100})
    history = api("GET", "/pulls?" + query)
    open_prs = [pr for pr in history if pr["state"] == "open"]
    if len(open_prs) > 1 or (open_prs and not expected):
        raise SyncError("Ambiguous existing sync PR state; review it manually.")
    existing = open_prs[0] if open_prs else None
    previous = None
    if expected:
        git.run("fetch", "--no-tags", "origin", "refs/heads/" + SYNC_BRANCH +
                ":refs/remotes/origin/" + SYNC_BRANCH)
        if git.run("rev-parse", "refs/remotes/origin/" + SYNC_BRANCH) != expected:
            raise SyncError("The sync branch moved during preparation; run again.")
        previous = owned_commit(git, expected)
        if existing:
            owned_pr(existing, expected)

    result = {"base_sha": base, "head_sha": "", "pr_number": "", "mode": "up_to_date"}
    if git.run("merge-base", "--is-ancestor", upstream, base, check=False).returncode == 0:
        if check_current:
            result["head_sha"] = base
        return result

    if previous == (base, upstream):
        if not existing and any(pr.get("head", {}).get("sha") == expected and not pr.get("merged_at")
                                for pr in history if pr["state"] == "closed"):
            result["mode"] = "closed_pr_preserved"
            return result
        if existing and not check_current:
            return dict(result, mode="unchanged_pr", pr_number=str(existing["number"]))
        candidate = expected
    else:
        merge = git.run("merge", "--no-ff", "--no-commit", upstream, check=False)
        if merge.returncode:
            paths = git.run("diff", "--name-only", "--diff-filter=U", "-z").split("\0")
            raise SyncError("Merge stopped; no branch or PR published. Conflict paths: " +
                            json.dumps([path for path in paths if path], ensure_ascii=False) +
                            ". " + merge.stderr.strip()[:1200])
        message = f"Merge upstream master into mc-helper\n\nMC-Helper-Sync: 1\nBase: {base}\nUpstream: {upstream}"
        git.run("commit", "-m", message, env={"GIT_AUTHOR_NAME": BOT, "GIT_AUTHOR_EMAIL": BOT_EMAIL,
                                             "GIT_COMMITTER_NAME": BOT, "GIT_COMMITTER_EMAIL": BOT_EMAIL})
        candidate = git.run("rev-parse", "HEAD")
        if current_base(api) != base:
            raise SyncError("dev moved during the merge; no candidate was published. Run again.")
        push_candidate(git, expected)

    if current_base(api) != base:
        raise SyncError("dev moved before PR publication; keep the candidate branch and run again.")
    pr = ensure_pr(api, existing, base, upstream, run_url)
    return dict(result, head_sha=candidate, pr_number=str(pr["number"]), mode="candidate")


def publish_status(api, base, head, number, checks_result, run_url):
    if not SHA.fullmatch(base) or not SHA.fullmatch(head) or not str(number).isdigit():
        raise SyncError("Invalid trusted preparation outputs.")
    pr = api("GET", f"/pulls/{number}")
    try:
        owned_pr(pr, head)
        fresh = pr.get("state") == "open" and current_base(api) == base
    except SyncError:
        fresh = False
    state = "success" if checks_result == "success" and fresh else "failure"
    description = ("Identity and tests passed for this dev baseline" if state == "success" else
                   "Candidate/base changed; rerun sync" if not fresh else "Checks " + checks_result + "; review workflow logs")
    api("POST", f"/statuses/{head}", {"state": state, "context": "mc-helper/upstream-sync",
         "description": description, "target_url": run_url})
    return state


def main():
    if os.environ.get("GITHUB_REPOSITORY") != FORK or os.environ.get("GITHUB_REF") != "refs/heads/dev":
        raise SyncError("This workflow only runs in the configured fork from refs/heads/dev.")
    api = GitHub(os.environ["GH_TOKEN"])
    url = f"{os.environ['GITHUB_SERVER_URL']}/{FORK}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        state = publish_status(api, os.environ["BASE_SHA"], os.environ["HEAD_SHA"],
                               os.environ["PR_NUMBER"], os.environ["CHECKS_RESULT"], url)
        print("Published candidate status:", state)
        return 0 if state == "success" else 1
    result = synchronize(Path.cwd(), api, check_current=os.environ.get("CHECK_CURRENT") == "1", run_url=url)
    if result["head_sha"] and not SHA.fullmatch(result["head_sha"]):
        raise SyncError("Invalid candidate SHA.")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
        for key, value in result.items():
            output.write(f"{key}={value}\n")
    with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as output:
        output.write("## mc-helper upstream synchronization\n\n```json\n" +
                     json.dumps(result, indent=2) + "\n```\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SyncError, OSError, KeyError, ValueError) as error:
        print(f"Upstream synchronization stopped: {error}", file=sys.stderr)
        raise SystemExit(1)
