"""
main.py - Entry point for the Memory Match game.

Responsibilities:
- Bootstrap: load .env, init DB, load sounds
- Global exception handling (sys.excepthook + Tk report_callback_exception)
- Logging to app.log
- App class: screen routing (login / signup / forgot / game / leaderboard)
- Clean shutdown on window close
"""

import os
import sys

# Guarantee working directory is the script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Auto-re-execute inside .venv if invoked via system Python
_VENV_PY = os.path.join(SCRIPT_DIR, ".venv", "Scripts", "python.exe")
if not os.path.isfile(_VENV_PY):
    _VENV_PY = os.path.join(SCRIPT_DIR, ".venv", "bin", "python")

if os.path.isfile(_VENV_PY):
    _cur = os.path.abspath(sys.executable).lower()
    _tgt = os.path.abspath(_VENV_PY).lower()
    if _cur != _tgt:
        import subprocess
        try:
            sys.exit(subprocess.call([_VENV_PY] + sys.argv))
        except SystemExit as _se:
            raise _se
        except Exception:
            pass

import logging
import threading
import traceback

# ── Logging setup (before any other imports so all modules use it) ──────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ── Third-party imports ──────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv not installed. Falling back to environment variables.")

try:
    import customtkinter as ctk
    from PIL import Image, ImageTk
    import mysql.connector
except ImportError as err:
    import tkinter as tk
    import tkinter.messagebox as mb
    root = tk.Tk()
    root.withdraw()
    mb.showerror(
        "Missing Dependencies",
        f"Could not import required package: {getattr(err, 'name', err)}\n\n"
        f"Please install dependencies with:\n"
        f"pip install -r requirements.txt",
    )
    root.destroy()
    sys.exit(1)

# ── Internal imports ─────────────────────────────────────────────────────────
from ui.theme import apply_theme, BG_CREAM, CORAL, get_font, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT
from game import MemoryGame


# ────────────────────────────────────────────────────────────────────────────
#  Sound Loader
# ────────────────────────────────────────────────────────────────────────────

def _load_sounds() -> dict | None:
    """
    Attempt to load pygame.mixer and sound files.
    Returns a dict with 'flip', 'match', 'win' Sound objects,
    or None if sounds are unavailable (no pygame, no audio device, missing files).
    """
    try:
        import pygame.mixer as mixer
        try:
            mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass
        mixer.init()
        sounds = {}
        base = os.path.join(os.path.dirname(__file__), "sounds")
        for name, fname in [("flip", "flip.wav"), ("match", "match.wav"), ("win", "win.wav")]:
            path = os.path.join(base, fname)
            if os.path.isfile(path):
                try:
                    sounds[name] = mixer.Sound(path)
                except Exception:
                    pass
        logger.info(f"Sounds loaded: {list(sounds.keys())}")
        return sounds if sounds else None
    except Exception as e:
        logger.info(f"Sound system unavailable: {e}")
        return None


# ────────────────────────────────────────────────────────────────────────────
#  Main Application Class
# ────────────────────────────────────────────────────────────────────────────

class MemoryMatchApp(ctk.CTk):
    """
    Root application window and screen router.

    Attributes:
        db (DatabaseManager | None): Database connection pool.
        current_user (dict | None): Currently logged-in user record.
        game (MemoryGame | None): Current MemoryGame instance.
        sound_mixer (dict | None): Sound effects dict.
    """

    def __init__(self):
        super().__init__()

        apply_theme()

        self.title("🃏 Memory Match")
        self.geometry("1024x720")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.configure(fg_color=BG_CREAM)

        # Install Tk-level exception handler
        self.report_callback_exception = self._handle_tk_exception

        self.db = None
        self.current_user = None
        self.game = None
        self.sound_mixer = None
        self._current_screen = None

        # Handle window close cleanly
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Bootstrap in a thread so the window appears immediately
        self._show_splash()
        self.after(50, self._bootstrap)

    # ------------------------------------------------------------------ #
    #  Bootstrap                                                           #
    # ------------------------------------------------------------------ #

    def _show_splash(self):
        """Show a simple loading label while bootstrapping."""
        self._splash = ctk.CTkLabel(
            self,
            text="🃏  Loading Memory Match…",
            font=get_font(28, "bold"),
            text_color=CORAL,
        )
        self._splash.place(relx=0.5, rely=0.5, anchor="center")

    def _bootstrap(self):
        """Initialize DB and sounds, then show the login screen."""
        def _worker():
            db_error = None
            db = None
            try:
                from database import init_db
                db = init_db()
                logger.info("Database initialized successfully.")
            except Exception as e:
                db_error = str(e)
                logger.error(f"DB init error: {e}")

            sounds = _load_sounds()
            try:
                if self.winfo_exists():
                    self.after(0, lambda: self._finish_bootstrap(db, db_error, sounds))
            except Exception:
                pass

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _finish_bootstrap(self, db, db_error, sounds):
        """Called on main thread after bootstrap completes."""
        if not self.winfo_exists():
            return

        if hasattr(self, "_splash") and self._splash.winfo_exists():
            self._splash.destroy()

        self.db = db
        self.sound_mixer = sounds

        self.show_login()

        if db_error and not os.environ.get("MEMORY_MATCH_TEST"):
            logger.warning(f"DB unavailable: {db_error}")
            import tkinter.messagebox as mb
            self.after(200, lambda: (
                mb.showwarning(
                    "Database Warning",
                    f"{db_error}\n\nThe app will run, but database features won't be saved until MySQL credentials are configured.",
                    parent=self,
                ) if self.winfo_exists() else None
            ))

    # ------------------------------------------------------------------ #
    #  Screen Router                                                       #
    # ------------------------------------------------------------------ #

    def _switch_screen(self, new_screen_widget):
        """Destroy the current screen and show the new one."""
        if not self.winfo_exists():
            return
        if self._current_screen is not None:
            try:
                self._current_screen.destroy()
            except Exception:
                pass
        self._current_screen = new_screen_widget
        new_screen_widget.pack(fill="both", expand=True)

    def show_login(self):
        """Show the login screen."""
        self.current_user = None
        if self.game:
            try:
                self.game.stop_timer()
            except Exception:
                pass
            self.game = None
        from ui.login_screen import LoginScreen
        self._switch_screen(LoginScreen(self, self))

    def show_signup(self):
        """Show the signup screen."""
        from ui.signup_screen import SignupScreen
        self._switch_screen(SignupScreen(self, self))

    def show_forgot_password(self):
        """Show the forgot password screen."""
        from ui.forgot_password_screen import ForgotPasswordScreen
        self._switch_screen(ForgotPasswordScreen(self, self))

    def show_game(self, user: dict):
        """Show the main game screen for a logged-in user."""
        self.current_user = user

        images_dir = os.path.join(os.path.dirname(__file__), "images")

        # Ensure images dir exists
        if not os.path.isdir(images_dir):
            os.makedirs(images_dir, exist_ok=True)

        from game import list_valid_images
        valid_imgs = list_valid_images(images_dir)
        if len(valid_imgs) < 12:
            self._offer_placeholder_images(images_dir)
            return

        self.game = MemoryGame(images_dir)
        from ui.game_screen import GameScreen
        self._switch_screen(GameScreen(self, self))

    def _offer_placeholder_images(self, images_dir: str):
        """Ask user if they want placeholder images generated."""
        import tkinter.messagebox as mb
        answer = mb.askyesno(
            "No Images Found",
            "The images/ folder has fewer than 12 valid images.\n\n"
            "Would you like to auto-generate 30 colorful placeholder tiles so you can try the game?",
            parent=self,
        )
        if answer:
            try:
                from game import generate_placeholder_images
                generate_placeholder_images(images_dir, count=30)
                logger.info("Placeholder images generated.")
                self.game = MemoryGame(images_dir)
                from ui.game_screen import GameScreen
                self._switch_screen(GameScreen(self, self))
            except Exception as e:
                logger.exception("Failed to generate placeholders")
                import tkinter.messagebox as mb
                mb.showerror("Error", f"Could not generate placeholders:\n{e}", parent=self)
        else:
            import tkinter.messagebox as mb
            mb.showinfo(
                "Add Images",
                "Please add at least 30 images (PNG/JPG/JPEG/WEBP/GIF) to the images/ folder, then restart.",
                parent=self,
            )

    def show_leaderboard(self):
        """Show the leaderboard screen."""
        from ui.leaderboard_screen import LeaderboardScreen
        self._switch_screen(LeaderboardScreen(self, self, self.current_user))

    # ------------------------------------------------------------------ #
    #  Exception Handling                                                  #
    # ------------------------------------------------------------------ #

    def _handle_tk_exception(self, exc_type, exc_value, exc_tb):
        """
        Tk's report_callback_exception override.
        Logs the error and shows a friendly dialog instead of crashing.
        """
        err_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.error(f"Unhandled Tk exception:\n{err_text}")
        try:
            import tkinter.messagebox as mb
            mb.showerror(
                "Unexpected Error",
                f"Something went wrong, but the app is still running.\n\n"
                f"{exc_type.__name__}: {exc_value}\n\nDetails saved to app.log.",
                parent=self,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  Window Close                                                        #
    # ------------------------------------------------------------------ #

    def _on_close(self):
        """Clean up resources before exiting."""
        logger.info("Application closing.")
        if self.game:
            try:
                self.game.stop_timer()
            except Exception:
                pass
        if self.db:
            try:
                self.db.close()
            except Exception:
                pass
        try:
            import pygame.mixer as mixer
            mixer.quit()
        except Exception:
            pass
        self.destroy()


# ────────────────────────────────────────────────────────────────────────────
#  Global Exception Hook
# ────────────────────────────────────────────────────────────────────────────

def _global_exception_hook(exc_type, exc_value, exc_tb):
    """sys.excepthook override — log and show a dialog for unhandled exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    err_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.critical(f"Unhandled exception:\n{err_text}")
    try:
        import tkinter.messagebox as mb
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        mb.showerror(
            "Fatal Error",
            f"An unexpected error occurred.\n\n"
            f"{exc_type.__name__}: {exc_value}\n\nDetails saved to app.log.",
        )
        root.destroy()
    except Exception:
        print(f"FATAL: {exc_type.__name__}: {exc_value}", file=sys.stderr)


sys.excepthook = _global_exception_hook


# ────────────────────────────────────────────────────────────────────────────
#  Entry Point
# ────────────────────────────────────────────────────────────────────────────

def main():
    """Application entry point."""
    try:
        app = MemoryMatchApp()
        app.mainloop()
    except Exception as e:
        err = traceback.format_exc()
        logger.critical(f"Fatal error in main():\n{err}")
        try:
            import tkinter.messagebox as mb
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            mb.showerror("Fatal Error", f"Memory Match failed to start:\n\n{e}")
            root.destroy()
        except Exception:
            print(f"Fatal: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

