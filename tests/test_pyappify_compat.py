import os
import unittest
from importlib.metadata import PackageNotFoundError
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pyappify
from PySide6.QtWidgets import QApplication
from ok.ui.qt.about.UpdateCard import UpdateCard
from src.pyappify_compat import install_prerelease_comparison


class TestPyAppifyCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        original = pyappify.is_greater_version
        self.addCleanup(setattr, pyappify, "is_greater_version", original)
        metadata = patch("src.pyappify_compat.version", return_value="1.0.20")
        metadata.start()
        self.addCleanup(metadata.stop)

    def test_supported_tag_order_and_keyword_arguments(self):
        self.assertIsNone(install_prerelease_comparison())
        for left, right, expected in (
            ("v0.1.0-beta.6", "v0.1.0-beta.3", True),
            ("v0.1.0-beta.3", "v0.1.0-beta.6", False),
            ("v0.1.0-beta.6", "v0.1.0-beta.6", False),
            ("v0.1.0-beta.10", "v0.1.0-beta.9", True),
            ("v0.1.0-beta.1", "v0.1.0-alpha.9", True),
            ("v0.1.0-rc.1", "v0.1.0-beta.9", True),
            ("v0.1.0", "v0.1.0-rc.9", True),
            ("v0.1.0-beta.1", "v0.1.0", False),
            ("v0.2.0-alpha.1", "v0.1.9", True),
            ("0.1.0-beta.6", "v0.1.0-beta.3", True),
            ("v1.2.4", "v1.2.3", True),
        ):
            with self.subTest(left=left, right=right):
                self.assertEqual(pyappify.is_greater_version(version1=left, version2=right), expected)

    def test_unrecognized_inputs_delegate_to_original(self):
        original = Mock(return_value="original result")
        pyappify.is_greater_version = original
        self.assertIsNone(install_prerelease_comparison())
        self.assertIsNot(pyappify.is_greater_version, original)
        for pair in (("1.2", "1.1"), ("dev", "v0.1.0"), (None, "v0.1.0"), (12, 11)):
            with self.subTest(pair=pair):
                self.assertEqual(pyappify.is_greater_version(*pair), "original result")
                original.assert_called_with(*pair)

    def test_newer_dependency_is_left_unchanged(self):
        original = pyappify.is_greater_version
        with patch("src.pyappify_compat.version", return_value="1.0.21"):
            self.assertIsNone(install_prerelease_comparison())
        self.assertIs(pyappify.is_greater_version, original)

    def test_missing_package_metadata_returns_diagnostic(self):
        original = pyappify.is_greater_version
        with patch("src.pyappify_compat.version", side_effect=PackageNotFoundError("pyappify")):
            self.assertIn("Unable to identify", install_prerelease_comparison())
        self.assertIs(pyappify.is_greater_version, original)

    def test_repeated_installation_preserves_callable_identity(self):
        self.assertIsNone(install_prerelease_comparison())
        installed = pyappify.is_greater_version
        self.assertIsNone(install_prerelease_comparison())
        self.assertIs(pyappify.is_greater_version, installed)

    def test_public_startup_upgrade_and_downgrade_detection(self):
        install_prerelease_comparison()
        with patch.object(pyappify, "app_version", "v0.1.0-beta.6"), \
                patch.object(pyappify, "app_starting_version", "v0.1.0-beta.3"):
            self.assertTrue(pyappify.is_app_updated())
            self.assertFalse(pyappify.is_app_downgraded())
        with patch.object(pyappify, "app_version", "v0.1.0-beta.3"), \
                patch.object(pyappify, "app_starting_version", "v0.1.0-beta.6"):
            self.assertFalse(pyappify.is_app_updated())
            self.assertTrue(pyappify.is_app_downgraded())

    def card(self):
        with patch.object(pyappify, "is_local_checkout", return_value=False), patch.dict(os.environ):
            os.environ.pop("PYAPPIFY_PYTHON_TEST", None)
            card = UpdateCard("v0.1.0-beta.3", pyappify)
        self.addCleanup(card.deleteLater)
        return card

    def test_actual_update_card_buttons_for_native_entries(self):
        card = self.card()
        entries = [{"version": tag, "update_note": []} for tag in
                   ("v0.1.0-beta.6", "v0.1.0-beta.3", "v0.1.0-beta.2")]
        card._apply_versions((True, entries))
        self.assertFalse(card.update_button.isEnabled())  # The real 1.0.20 regression.
        install_prerelease_comparison()
        available = []
        card.update_available_changed.connect(available.append)
        card._apply_versions((True, entries))
        self.assertEqual(available, [True])
        self.assertTrue(card.update_button.isEnabled())
        self.assertEqual(card.update_button.text(), card.tr("Update"))
        card.version_combo.setCurrentIndex(1)
        self.assertFalse(card.update_button.isEnabled())
        self.assertEqual(card.update_button.text(), card.tr("Current version"))
        card.version_combo.setCurrentIndex(2)
        self.assertTrue(card.update_button.isEnabled())
        self.assertEqual(card.update_button.text(), card.tr("Downgrade"))

    def test_explicit_relation_retains_precedence(self):
        install_prerelease_comparison()
        card = self.card()
        card._apply_versions((True, [{"version": "v0.1.0-beta.6", "relation": "older", "update_note": []}]))
        self.assertTrue(card.update_button.isEnabled())
        self.assertEqual(card.update_button.text(), card.tr("Downgrade"))


if __name__ == "__main__":
    unittest.main()
