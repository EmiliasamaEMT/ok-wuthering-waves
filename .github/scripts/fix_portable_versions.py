"""Make portable launchers discover the version of their active Git checkout."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


VERSION_VARIABLES = ("PYAPPIFY_APP_VERSION", "PYAPPIFY_APP_STARTING_VERSION")


def patch_launcher(content):
    text = content.decode("utf-8-sig")
    bom = b"\xef\xbb\xbf" if content.startswith(b"\xef\xbb\xbf") else b""
    for name in VERSION_VARIABLES:
        pattern = re.compile(r'^set "' + name + r'=[^\r\n]*"(?=\r?$)', re.MULTILINE)
        if len(pattern.findall(text)) != 1:
            raise ValueError(f"Expected exactly one {name} assignment in portable launcher")
        text = pattern.sub(f'set "{name}="', text)
    if len(re.findall(r'^set "PYAPPIFY_UPGRADEABLE=0"(?=\r?$)', text, re.MULTILINE)) != 1:
        raise ValueError("Expected a standalone portable launcher")
    return bom + text.encode("utf-8")


def find_seven_zip(configured=None):
    if configured:
        candidate = Path(configured).resolve()
        if candidate.is_file():
            return str(candidate)
        raise FileNotFoundError(candidate)
    found = shutil.which("7z")
    if found:
        return found
    candidate = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "7-Zip/7z.exe"
    if candidate.is_file():
        return str(candidate)
    raise FileNotFoundError("7-Zip is required to update portable launchers")


def run_seven_zip(executable, arguments, cwd=None):
    return subprocess.run([executable, *arguments], cwd=cwd, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def read_launcher(executable, archive, member):
    listing = run_seven_zip(executable, ["l", "-slt", "-sccUTF-8", str(archive)])
    members = [line[7:].replace("\\", "/") for line in listing.decode("utf-8").splitlines()
               if line.startswith("Path = ")]
    if members.count(member) != 1:
        raise ValueError(f"Expected exactly one {member} in {archive.name}")
    return run_seven_zip(executable, ["x", "-so", "-bd", str(archive), member])


def patch_archive(executable, archive, app_name):
    archive = Path(archive).resolve()
    member = f"{app_name}/{app_name}.cmd"
    original = read_launcher(executable, archive, member)
    updated = patch_launcher(original)
    if updated != original:
        # Write only the known launcher; never extract arbitrary archive paths.
        # Runner temporary files are left for the runner's normal cleanup.
        temporary = Path(tempfile.mkdtemp(prefix="mc-helper-launcher-"))
        target = temporary / app_name / f"{app_name}.cmd"
        target.parent.mkdir()
        target.write_bytes(updated)
        run_seven_zip(executable, ["u", "-y", "-bd", str(archive), member], cwd=temporary)
    run_seven_zip(executable, ["t", "-bd", str(archive)])
    if read_launcher(executable, archive, member) != updated:
        raise RuntimeError(f"Portable launcher verification failed: {archive.name}")
    print(f"Verified portable launcher: {archive.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", required=True)
    parser.add_argument("--app-name", default="mc-helper")
    parser.add_argument("--seven-zip")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.app_name):
        parser.error("app-name must be a single filename component")
    archives = sorted(Path(args.dist).glob(f"{args.app_name}-win32-*.7z"))
    if not archives:
        parser.error("no portable 7z archives found")
    executable = find_seven_zip(args.seven_zip)
    for archive in archives:
        patch_archive(executable, archive, args.app_name)


if __name__ == "__main__":
    main()
