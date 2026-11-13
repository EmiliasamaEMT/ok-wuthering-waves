"""Lock the reviewed b7 startup-check behavior without starting a real app."""

import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


window = importlib.import_module("ok.ui.qt.MainWindow")


class TestUpdateStartupCompatibility(unittest.TestCase):
    def make_window(self, game_active):
        return SimpleNamespace(
            about_tab=SimpleNamespace(update_card=object(), check_for_updates=Mock()),
            config={"update_only_game_exit": True},
            _game_starting_or_started=Mock(return_value=game_active),
            _poll_game_process_for_update_check=Mock(),
        )

    def test_idle_startup_checks_immediately(self):
        app = self.make_window(False)
        with patch.object(window, "QTimer") as timer:
            window.MainWindow._startup_update_check(app)
        app.about_tab.check_for_updates.assert_called_once_with(automatic=True)
        timer.assert_not_called()

    def test_active_game_skips_without_scheduling_a_check_after_exit(self):
        app = self.make_window(True)
        with patch.object(window, "QTimer") as timer:
            window.MainWindow._startup_update_check(app)
            app._game_starting_or_started.return_value = False
        app.about_tab.check_for_updates.assert_not_called()
        app._poll_game_process_for_update_check.assert_not_called()
        timer.assert_not_called()

    def test_missing_update_card_skips_the_startup_check(self):
        app = self.make_window(False)
        app.about_tab.update_card = None
        window.MainWindow._startup_update_check(app)
        app.about_tab.check_for_updates.assert_not_called()
        app._game_starting_or_started.assert_not_called()


if __name__ == "__main__":
    unittest.main()
