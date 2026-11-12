"""Stage complete release assets within GitHub's per-file size limit."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


ASSET_LIMIT = 2 * 1024 ** 3
VOLUME_SIZE = 1900 * 1024 ** 2
CHUNK_SIZE = 1024 ** 2


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_or_split(source, destination, limit=ASSET_LIMIT, volume_size=VOLUME_SIZE):
    source, destination = Path(source), Path(destination)
    if not 0 < volume_size < limit:
        raise ValueError("Volume size must be positive and below the asset limit")
    size = source.stat().st_size
    split = size >= limit
    if split and source.suffix != ".7z":
        raise ValueError(f"Non-7z asset exceeds GitHub's size limit: {source.name}")
    parts = []
    original = hashlib.sha256()
    remaining = size
    with source.open("rb") as stream:
        while remaining or not parts:
            name = f"{source.name}.{len(parts) + 1:03d}" if split else source.name
            part_path = destination / name
            part_size = min(volume_size, remaining) if split else remaining
            part_hash = hashlib.sha256()
            written = 0
            with part_path.open("xb") as output:
                while written < part_size:
                    chunk = stream.read(min(CHUNK_SIZE, part_size - written))
                    if not chunk:
                        raise RuntimeError(f"Source asset changed while reading: {source.name}")
                    output.write(chunk)
                    part_hash.update(chunk)
                    original.update(chunk)
                    written += len(chunk)
            parts.append({"name": name, "size": written, "sha256": part_hash.hexdigest()})
            remaining -= written
            if not split:
                break
        if stream.read(1):
            raise RuntimeError(f"Source asset grew while reading: {source.name}")

    # Re-read the staged bytes to prove both each volume and their ordering.
    combined = hashlib.sha256()
    for part in parts:
        path = destination / part["name"]
        if path.stat().st_size != part["size"] or part["size"] >= limit:
            raise RuntimeError(f"Invalid staged asset size: {path.name}")
        if file_hash(path) != part["sha256"]:
            raise RuntimeError(f"Staged asset hash mismatch: {path.name}")
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
                combined.update(chunk)
    if combined.hexdigest() != original.hexdigest():
        raise RuntimeError(f"Reassembled archive hash mismatch: {source.name}")
    return {"name": source.name, "size": size, "sha256": original.hexdigest(), "parts": parts}


def stage_release_assets(dist, destination, app_name="mc-helper", verify_archive=None):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", app_name):
        raise ValueError("App name must be a single filename component")
    dist, destination = Path(dist).resolve(), Path(destination).resolve()
    if destination == dist or destination.is_relative_to(dist):
        raise ValueError("Release staging must be outside the build output directory")
    if destination.exists():
        raise FileExistsError(destination)
    archives = sorted(dist.glob(f"{app_name}-win32-*.7z"))
    if not archives:
        raise FileNotFoundError("No complete portable archives found")
    if len(archives) != 2:
        raise ValueError("Expected exactly the China and Global portable archives")
    for profile in ("China", "Global"):
        matches = [path for path in archives if path.name.startswith(f"{app_name}-win32-{profile}-")]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one complete {profile} archive")
    sources = [*archives, dist / f"{app_name}-win32.zip", dist / "win32_sha256.txt"]
    for source in sources:
        if not source.is_file() or source.is_symlink():
            raise FileNotFoundError(source)
    destination.mkdir(parents=True)
    entries = []
    for source in sources:
        entry = copy_or_split(source, destination)
        if verify_archive and source.suffix == ".7z":
            verify_archive(destination / entry["parts"][0]["name"])
        if source.suffix == ".zip":
            with zipfile.ZipFile(destination / source.name) as archive:
                if archive.testzip() is not None:
                    raise RuntimeError(f"Invalid native launcher ZIP: {source.name}")
        entries.append(entry)

    manifest = {"asset_limit_exclusive": ASSET_LIMIT, "volume_size": VOLUME_SIZE, "archives": entries}
    (destination / "release-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    checksums = "".join(f"{file_hash(path)}  {path.name}\n"
                        for path in sorted(destination.iterdir()) if path.is_file())
    (destination / "SHA256SUMS").write_text(checksums, encoding="utf-8", newline="\n")
    for path in destination.iterdir():
        if not path.is_file() or path.stat().st_size >= ASSET_LIMIT:
            raise ValueError(f"Invalid published asset: {path.name}")
        print(f"Staged {path.name} ({path.stat().st_size} bytes)")
    return manifest


def main():
    from fix_portable_versions import find_seven_zip, run_seven_zip

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--app-name", default="mc-helper")
    parser.add_argument("--seven-zip")
    args = parser.parse_args()
    seven_zip = find_seven_zip(args.seven_zip)
    stage_release_assets(args.dist, args.output, args.app_name,
                         verify_archive=lambda path: run_seven_zip(seven_zip, ["t", "-bd", str(path)]))


if __name__ == "__main__":
    main()
