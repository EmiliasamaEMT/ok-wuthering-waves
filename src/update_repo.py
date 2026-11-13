"""Keep a negotiation head for PyAppify's tag-only managed repositories."""

import json
import os
from pathlib import Path


HAVE_REF = b"refs/heads/mc-helper-current"
OWNER_FILE = "mc-helper-current.owner"
OWNER_CONTENT = b"mc-helper update negotiation cache v1\n"


def prepare_update_repository(entrypoint, environ=None):
    """Return a diagnostic on failure; ordinary development checkouts are a no-op."""
    try:
        entrypoint = Path(entrypoint).resolve()
        working = entrypoint.parent
        base = working.parent
        if (working.name != "working" or base.name != "mc-helper"
                or base.parent.name != "apps" or base.parent.parent.name != "data"):
            return None
        _synchronize(base, working, os.environ if environ is None else environ)
    except Exception as error:
        return (f"Unable to prepare the local update cache: {error}. "
                "Checking for updates may download existing Git data again.")
    return None


def _synchronize(base, working, environ):
    from dulwich.file import GitFile
    from dulwich.objects import Commit
    from dulwich.repo import Repo

    repo_path = base / "repo"
    app_json = base / "app.json"
    if repo_path.is_symlink() or not repo_path.is_dir() or (working / ".git").exists():
        raise ValueError("expected an independent managed bare repository")
    for name, expected in (("PYAPPIFY_REPO_PATH", repo_path), ("PYAPPIFY_APP_JSON_PATH", app_json)):
        if environ.get(name) and Path(environ[name]).resolve() != expected.resolve():
            raise ValueError(f"{name} points outside this installation")
    app = json.loads(app_json.read_text(encoding="utf-8-sig"))
    if app.get("name") != "mc-helper" or app.get("installed") is not True:
        raise ValueError("expected an installed mc-helper application")
    ref_path = repo_path / "refs/heads/mc-helper-current"
    owner_path = repo_path / OWNER_FILE
    if ref_path.is_symlink() or ref_path.resolve() != ref_path or owner_path.is_symlink():
        raise ValueError("update cache paths must not be symbolic links")
    with Repo(str(repo_path)) as repo:
        if not repo.bare:
            raise ValueError("expected a bare repository")
        try:
            configured_working = Path(repo.get_config().get((b"core",), b"worktree").decode())
        except KeyError:
            configured_working = working
        if not configured_working.is_absolute():
            configured_working = repo_path / configured_working
        if configured_working.resolve() != working:
            raise ValueError("repository worktree points outside this installation")
        head = repo.refs.read_ref(b"HEAD")
        if not head or head.startswith(b"ref:") or not isinstance(repo[head], Commit):
            raise ValueError("expected a detached commit HEAD")
        before = repo.refs.read_ref(HAVE_REF)
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        # Lock this exact path rather than following a potentially symbolic ref.
        with GitFile(str(ref_path), "wb") as locked:
            current = repo.refs.read_ref(HAVE_REF)
            if current != before or (current and current.startswith(b"ref:")):
                raise ValueError("update cache reference changed or is symbolic")
            if owner_path.exists():
                if owner_path.read_bytes() != OWNER_CONTENT:
                    raise ValueError("update cache ownership marker is unrecognized")
            elif current is not None:
                raise ValueError("reserved update reference already belongs to another caller")
            else:
                with owner_path.open("xb") as marker:
                    marker.write(OWNER_CONTENT)
            if repo.refs.read_ref(b"HEAD") != head:
                raise ValueError("HEAD changed during update cache preparation")
            if current == head:
                locked.abort()
            else:
                locked.write(head + b"\n")
        if repo.refs.read_ref(b"HEAD") != head:
            raise ValueError("HEAD changed after update cache preparation; retry on next launch")
