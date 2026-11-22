"""
test_ui_screens.py - Integration test for all UI screens and dialogs.
Tests that each screen can instantiate, layout, and destroy without Tk exceptions.
"""

import os
import unittest
import customtkinter as ctk

from main import MemoryMatchApp
from ui.login_screen import LoginScreen
from ui.signup_screen import SignupScreen
from ui.forgot_password_screen import ForgotPasswordScreen
from ui.game_screen import GameScreen
from ui.leaderboard_screen import LeaderboardScreen
from ui.win_dialog import WinDialog
from game import MemoryGame, generate_placeholder_images


class TestUIScreens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["MEMORY_MATCH_TEST"] = "1"
        # Create a hidden CTk app
        cls.app = MemoryMatchApp()
        cls.app.withdraw()  # hide during testing

        # Prepare dummy user
        cls.dummy_user = {
            "id": 1,
            "username": "testplayer",
            "display_name": "Test Player",
            "email": "test@example.com",
        }
        cls.app.current_user = cls.dummy_user

        # Ensure images directory has at least 12 valid images
        img_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")
        if not os.path.isdir(img_dir) or len(os.listdir(img_dir)) < 12:
            os.makedirs(img_dir, exist_ok=True)
            generate_placeholder_images(img_dir, count=15)
        cls.app.game = MemoryGame(img_dir)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.app._on_close()
        except Exception:
            pass

    def test_01_login_screen(self):
        screen = LoginScreen(self.app, self.app)
        screen.pack(fill="both", expand=True)
        self.app.update_idletasks()
        self.assertTrue(screen.winfo_exists())
        screen.destroy()

    def test_02_signup_screen(self):
        screen = SignupScreen(self.app, self.app)
        screen.pack(fill="both", expand=True)
        self.app.update_idletasks()
        self.assertTrue(screen.winfo_exists())
        screen.destroy()

    def test_03_forgot_password_screen(self):
        screen = ForgotPasswordScreen(self.app, self.app)
        screen.pack(fill="both", expand=True)
        self.app.update_idletasks()
        self.assertTrue(screen.winfo_exists())
        screen.destroy()

    def test_04_game_screen(self):
        screen = GameScreen(self.app, self.app)
        screen.pack(fill="both", expand=True)
        self.app.update_idletasks()
        self.assertTrue(screen.winfo_exists())
        self.assertEqual(len(screen._card_widgets), 24)
        screen.destroy()

    def test_05_leaderboard_screen(self):
        screen = LeaderboardScreen(self.app, self.app, self.dummy_user)
        screen.pack(fill="both", expand=True)
        self.app.update_idletasks()
        self.assertTrue(screen.winfo_exists())
        screen.destroy()

    def test_06_win_dialog(self):
        dialog = WinDialog(
            parent=self.app,
            score=500,
            moves=18,
            time_seconds=65,
            best_streak=4,
            is_new_record=True,
            on_play_again=lambda: None,
            on_leaderboard=lambda: None,
            on_logout=lambda: None,
        )
        self.app.update_idletasks()
        self.assertTrue(dialog.winfo_exists())
        dialog.start_confetti()
        dialog.stop_confetti()
        dialog._destroy_safe()


if __name__ == "__main__":
    unittest.main()
