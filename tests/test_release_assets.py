import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / ".github/scripts/stage_release_assets.py"
spec = importlib.util.spec_from_file_location("stage_release_assets", SCRIPT)
stager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stager)
SEVEN_ZIP = os.environ.get("SEVEN_ZIP") or shutil.which("7z")
if not SEVEN_ZIP:
    candidate = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "7-Zip/7z.exe"
    SEVEN_ZIP = str(candidate) if candidate.is_file() else None


class TestReleaseAssets(unittest.TestCase):
    def setUp(self):
        # Leave owned test fixtures for normal runner cleanup; no recursive deletion.
        self.root = Path(tempfile.mkdtemp(prefix="mc-helper-release-assets-"))
        self.output = self.root / "out"
        self.output.mkdir()

    def source(self, size, name="mc-helper-win32-China-test.7z"):
        path = self.root / name
        path.write_bytes(bytes(range(size)))
        return path

    def assert_parts(self, source, entry, sizes):
        parts = [self.output / item["name"] for item in entry["parts"]]
        self.assertEqual([path.stat().st_size for path in parts], sizes)
        self.assertEqual(b"".join(path.read_bytes() for path in parts), source.read_bytes())
        self.assertEqual(entry["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        for path, item in zip(parts, entry["parts"]):
            self.assertEqual(item["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_under_limit_keeps_original_name(self):
        source = self.source(31)
        entry = stager.copy_or_split(source, self.output, limit=32, volume_size=20)
        self.assertEqual(entry["parts"][0]["name"], source.name)
        self.assert_parts(source, entry, [31])

    def test_exact_limit_is_split_and_original_is_retained(self):
        source = self.source(32)
        entry = stager.copy_or_split(source, self.output, limit=32, volume_size=20)
        self.assertEqual([p["name"] for p in entry["parts"]],
                         [source.name + ".001", source.name + ".002"])
        self.assert_parts(source, entry, [20, 12])
        self.assertTrue(source.is_file())

    def test_multiple_volumes_and_short_last_volume(self):
        source = self.source(70)
        entry = stager.copy_or_split(source, self.output, limit=32, volume_size=20)
        self.assert_parts(source, entry, [20, 20, 20, 10])

    def test_oversized_non_archive_fails(self):
        with self.assertRaises(ValueError):
            stager.copy_or_split(self.source(32, "native.zip"), self.output, limit=32, volume_size=20)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_invalid_volume_size_fails(self):
        for volume_size in (0, 32, 33):
            with self.subTest(volume_size=volume_size), self.assertRaises(ValueError):
                stager.copy_or_split(self.source(1), self.output, limit=32, volume_size=volume_size)

    def test_staging_allowlist_manifest_and_existing_destination(self):
        dist = self.root / "dist"
        dist.mkdir()
        (dist / "mc-helper-win32-China-test.7z").write_bytes(b"portable")
        (dist / "mc-helper-win32-Global-test.7z").write_bytes(b"portable global")
        with zipfile.ZipFile(dist / "mc-helper-win32.zip", "w") as archive:
            archive.writestr("mc-helper.exe", b"native")
        (dist / "win32_sha256.txt").write_text("native zip checksum\n")
        (dist / "unrelated.bin").write_bytes(b"not a release asset")
        output = self.root / "release"
        manifest = stager.stage_release_assets(dist, output)
        self.assertEqual(len(manifest["archives"]), 4)
        self.assertFalse((output / "unrelated.bin").exists())
        self.assertEqual(json.loads((output / "release-manifest.json").read_text()), manifest)
        for line in (output / "SHA256SUMS").read_text().splitlines():
            expected, name = line.split("  ", 1)
            self.assertEqual(stager.file_hash(output / name), expected)
        with self.assertRaises(FileExistsError):
            stager.stage_release_assets(dist, output)

    def test_missing_required_asset_fails(self):
        dist = self.root / "dist"
        dist.mkdir()
        (dist / "mc-helper-win32-China-test.7z").write_bytes(b"portable")
        (dist / "mc-helper-win32-Global-test.7z").write_bytes(b"portable global")
        with self.assertRaises(FileNotFoundError):
            stager.stage_release_assets(dist, self.root / "release")

    def test_missing_duplicate_or_unknown_profile_fails(self):
        cases = (("China",), ("China", "China", "Global"), ("China", "Unknown"))
        for number, profiles in enumerate(cases):
            dist = self.root / f"dist-{number}"
            dist.mkdir()
            for index, profile in enumerate(profiles):
                (dist / f"mc-helper-win32-{profile}-test{index}.7z").write_bytes(b"portable")
            with self.subTest(profiles=profiles), self.assertRaises(ValueError):
                stager.stage_release_assets(dist, self.root / f"release-{number}")

    @unittest.skipUnless(SEVEN_ZIP, "7-Zip is required for volume integration")
    def test_real_seven_zip_reads_byte_split_volumes(self):
        data = os.urandom(32768)
        (self.root / "payload.bin").write_bytes(data)
        archive = self.root / "mc-helper-win32-QA-test.7z"
        subprocess.run([SEVEN_ZIP, "a", "-t7z", "-mx=1", "-bso0", str(archive), "payload.bin"],
                       cwd=self.root, check=True, capture_output=True)
        entry = stager.copy_or_split(archive, self.output, limit=8192, volume_size=7000)
        first = self.output / entry["parts"][0]["name"]
        subprocess.run([SEVEN_ZIP, "t", "-bso0", str(first)], check=True, capture_output=True)
        restored = subprocess.check_output([SEVEN_ZIP, "x", "-so", str(first), "payload.bin"])
        self.assertEqual(restored, data)


if __name__ == "__main__":
    unittest.main()
