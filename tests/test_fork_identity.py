import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_fork_identity", ROOT / ".github/scripts/check_fork_identity.py")
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)
FILES = ["pyappify.yml", "pyproject.toml", "config.py", "main.py", "main_debug.py", "requirements.txt",
         "src/update_repo.py", "src/pyappify_compat.py", "tests/test_update_repo.py",
         "tests/test_pyappify_compat.py", ".github/workflows/build.yml"]


class TestForkIdentity(unittest.TestCase):
    def setUp(self):
        # Preserve fixtures for normal runner cleanup; never recursively delete them.
        self.root = Path(tempfile.mkdtemp(prefix="mc-helper-identity-"))
        for relative in FILES:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)

    def replace(self, relative, before, after):
        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(before, text)
        path.write_text(text.replace(before, after), encoding="utf-8")

    def test_current_fork_and_upstream_documentation_links_are_valid(self):
        self.assertEqual(identity.check_identity(self.root), [])

    def test_upstream_update_source_is_rejected(self):
        self.replace("pyappify.yml", "EmiliasamaEMT", "ok-oldking")
        self.assertTrue(any("update source" in error for error in identity.check_identity(self.root)))

    def test_restored_upstream_name_or_title_is_rejected(self):
        for relative, before, after in [("pyproject.toml", 'name = "mc-helper"', 'name = "ok-ww"'),
                                        ("config.py", "mc小帮手", "OK-WW")]:
            with self.subTest(relative=relative):
                self.replace(relative, before, after)
                self.assertTrue(identity.check_identity(self.root))
                self.replace(relative, after, before)

    def test_config_is_parsed_without_running_python(self):
        marker = self.root / "must-not-run"
        with (self.root / "config.py").open("a", encoding="utf-8") as output:
            output.write(f"\nopen({str(marker)!r}, 'w').write('bad')\n")
        self.assertEqual(identity.check_identity(self.root), [])
        self.assertFalse(marker.exists())

    def test_removed_startup_compatibility_hook_is_rejected(self):
        self.replace("main.py", "version_compare_warning = install_prerelease_comparison()", "version_compare_warning = None")
        self.assertTrue(any("must run before" in error for error in identity.check_identity(self.root)))

    def test_dependency_change_requires_compatibility_review(self):
        self.replace("requirements.txt", "ok-script[ocr,qt]==3.0.5b5", "ok-script[ocr,qt]==3.0.5b7")
        self.assertTrue(any("review update compatibility" in error for error in identity.check_identity(self.root)))

    def test_unsafe_yaml_is_rejected(self):
        (self.root / "pyappify.yml").write_text("!!python/object/apply:builtins.print ['must not run']", encoding="utf-8")
        self.assertTrue(identity.check_identity(self.root))

    def test_removed_portable_version_fix_is_rejected(self):
        self.replace(".github/workflows/build.yml", "fix_portable_versions.py", "other.py")
        self.assertTrue(any("retain fix_portable_versions.py" in error for error in identity.check_identity(self.root)))


if __name__ == "__main__":
    unittest.main()
