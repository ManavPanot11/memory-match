"""
game_screen.py - Main game screen for Memory Match.

Handles:
- 4x6 grid of CardWidgets
- HUD (Score, Moves, Time, Streak pill badges)
- Top bar (player name, Logout, New Game, Leaderboard buttons)
- Integrates with MemoryGame logic
- All animations via after() with careful callback tracking
- Optional sound effects
- DB score saving in background thread
"""

import logging
import threading
from typing import Optional, Callable

import customtkinter as ctk
from PIL import Image, ImageTk

from ui.theme import (
    BG_CREAM, CORAL, MINT, SKY_BLUE, PURPLE, YELLOW, PINK,
    CARD_BACK_COLORS, CARD_WIDTH, CARD_HEIGHT, GRID_ROWS, GRID_COLS,
    get_font, TEXT_DARK, WHITE
)
from ui.widgets import RoundedButton, PillBadge, CardWidget

logger = logging.getLogger(__name__)


def _try_sound(mixer, sound_name: str):
    """Safely play a sound if mixer and the sound are available."""
    try:
        if isinstance(mixer, dict):
            sound = mixer.get(sound_name)
            if sound is not None:
                sound.play()
        elif mixer is not None:
            sound = getattr(mixer, sound_name, None)
            if sound is not None:
                sound.play()
    except Exception:
        pass


class GameScreen(ctk.CTkFrame):
    """Main game screen showing the 4x6 card grid and HUD."""

    def __init__(self, parent, app):
        """
        Initialize the game screen.

        Args:
            parent: The parent widget (root window).
            app: The main application instance with attributes:
                 db (DatabaseManager), current_user (dict),
                 show_leaderboard(), show_login(), game (MemoryGame),
                 sound_mixer (optional dict with 'flip','match','win' sounds)
        """
        super().__init__(parent, fg_color=BG_CREAM)
        self.app = app
        self.db = app.db
        self.current_user = app.current_user
        self.game = app.game

        # Track all pending after() callback IDs to cancel on cleanup
        self._after_ids: list[str] = []
        # Cached PIL images keyed by image_path
        self._image_cache: dict[str, ImageTk.PhotoImage] = {}
        # CardWidget instances indexed by card index (0..23)
        self._card_widgets: list[Optional[CardWidget]] = []
        # Whether score has been saved for the current game
        self._score_saved = False
        # Timer update callback id
        self._timer_cb: Optional[str] = None

        # Register game callbacks
        self.game.on_match = self._on_match
        self.game.on_mismatch = self._on_mismatch
        self.game.on_win = self._on_win
        self.game.on_state_change = self._on_state_change

        self._build_ui()
        self._start_new_game()

    # ------------------------------------------------------------------ #
    #  UI Construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        """Build the full game screen layout."""
        self.grid_rowconfigure(0, weight=0)  # top bar
        self.grid_rowconfigure(1, weight=0)  # HUD
        self.grid_rowconfigure(2, weight=1)  # card grid
        self.grid_columnconfigure(0, weight=1)

        self._build_top_bar()
        self._build_hud()
        self._build_card_grid()

    def _build_top_bar(self):
        """Build the top bar with player name and action buttons."""
        top_bar = ctk.CTkFrame(self, fg_color=CORAL, corner_radius=0)
        top_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        top_bar.grid_columnconfigure(1, weight=1)

        # Player name
        name = self.current_user.get("display_name", "Player")
        ctk.CTkLabel(
            top_bar,
            text=f"👤 {name}",
            font=get_font(18, "bold"),
            text_color=WHITE,
        ).grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Right-side buttons frame
        btn_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=10, pady=5, sticky="e")

        RoundedButton(
            btn_frame,
            text="🏆 Leaderboard",
            color=YELLOW,
            text_color=TEXT_DARK,
            command=self._on_leaderboard,
            font=get_font(13, "bold"),
        ).pack(side="left", padx=6)

        RoundedButton(
            btn_frame,
            text="🔄 New Game",
            color=MINT,
            text_color=TEXT_DARK,
            command=self._on_new_game,
            font=get_font(13, "bold"),
        ).pack(side="left", padx=6)

        RoundedButton(
            btn_frame,
            text="🚪 Logout",
            color=WHITE,
            text_color=CORAL,
            command=self._on_logout,
            font=get_font(13, "bold"),
        ).pack(side="left", padx=6)

    def _build_hud(self):
        """Build the HUD row with score/moves/time/streak badges."""
        hud = ctk.CTkFrame(self, fg_color="transparent")
        hud.grid(row=1, column=0, padx=20, pady=8, sticky="ew")
        hud.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._score_badge = PillBadge(hud, label="Score", value="0", color=CORAL)
        self._score_badge.grid(row=0, column=0, padx=8, pady=4, sticky="ew")

        self._moves_badge = PillBadge(hud, label="Moves", value="0", color=SKY_BLUE)
        self._moves_badge.grid(row=0, column=1, padx=8, pady=4, sticky="ew")

        self._time_badge = PillBadge(hud, label="Time", value="0:00", color=MINT)
        self._time_badge.grid(row=0, column=2, padx=8, pady=4, sticky="ew")

        self._streak_badge = PillBadge(hud, label="Streak", value="0", color=PURPLE)
        self._streak_badge.grid(row=0, column=3, padx=8, pady=4, sticky="ew")

    def _build_card_grid(self):
        """Build the 4x6 grid container (cards added in _start_new_game)."""
        self._grid_container = ctk.CTkFrame(self, fg_color="transparent")
        self._grid_container.grid(row=2, column=0, padx=16, pady=(4, 16), sticky="nsew")

        # Center the grid within the container, keeping all cells uniform
        for r in range(GRID_ROWS):
            self._grid_container.grid_rowconfigure(r, weight=1, uniform="card_row")
        for c in range(GRID_COLS):
            self._grid_container.grid_columnconfigure(c, weight=1, uniform="card_col")

    # ------------------------------------------------------------------ #
    #  Game Flow                                                           #
    # ------------------------------------------------------------------ #

    def _start_new_game(self):
        """Start a new game: reset state, load images, build card widgets."""
        self._cancel_all_callbacks()
        self._score_saved = False
        self._image_cache.clear()

        # Clear existing card widgets
        for w in self._card_widgets:
            if w is not None:
                try:
                    w.destroy()
                except Exception:
                    pass
        self._card_widgets = []

        # Tell game logic to start a new game
        try:
            state = self.game.new_game()
        except ValueError as e:
            self._show_error(str(e))
            return
        except Exception as e:
            logger.exception("Failed to start new game")
            self._show_error(f"Could not start game: {e}")
            return

        # Pre-load images in background, then build widgets on main thread
        self._preload_images_then_build(state)

    def _preload_images_then_build(self, state):
        """Load + resize all card images once per game, cache them, then build widgets."""
        unique_paths = list({c.image_path for c in state.cards})
        # Standard crisp card image size for CustomTkinter
        face_size = (120, 120)

        for path in unique_paths:
            try:
                with Image.open(path) as raw:
                    img = raw.convert("RGBA")
                    self._image_cache[path] = ctk.CTkImage(
                        light_image=img,
                        dark_image=img,
                        size=face_size,
                    )
            except Exception as e:
                logger.warning(f"Could not load image: {path} ({e})")

        self._build_card_widgets(state)
        self._update_hud()
        self._start_timer()

    def _build_card_widgets(self, state):
        """Create CardWidget instances for all 24 cards and place them in the grid."""
        self._card_widgets = [None] * len(state.cards)

        for card in state.cards:
            back_color = CARD_BACK_COLORS[card.index % len(CARD_BACK_COLORS)]
            cw = CardWidget(
                self._grid_container,
                card_index=card.index,
                back_color=back_color,
                on_click=self._on_card_clicked,
                width=CARD_WIDTH,
                height=CARD_HEIGHT,
            )
            cw.grid(
                row=card.row,
                column=card.col,
                padx=6,
                pady=6,
                sticky="nsew",
            )
            self._card_widgets[card.index] = cw

    # ------------------------------------------------------------------ #
    #  Timer                                                               #
    # ------------------------------------------------------------------ #

    def _start_timer(self):
        """Schedule the timer update loop."""
        self._tick_timer()

    def _tick_timer(self):
        """Update the time badge every second."""
        if not self.winfo_exists():
            return
        state = self.game.state
        if state and not state.game_over:
            elapsed = self.game.get_elapsed_seconds()
            minutes = elapsed // 60
            seconds = elapsed % 60
            self._time_badge.update_value(f"{minutes}:{seconds:02d}")
        cb = self.after(1000, self._tick_timer)
        self._after_ids.append(cb)
        self._timer_cb = cb

    # ------------------------------------------------------------------ #
    #  Card Click Handler                                                  #
    # ------------------------------------------------------------------ #

    def _on_card_clicked(self, index: int):
        """Handle a card click: delegate to game logic, play sound."""
        if self.game.state and self.game.state.is_locked:
            return
        _try_sound(self.app.sound_mixer, "flip")
        self.game.flip_card(index)

    # ------------------------------------------------------------------ #
    #  Game Callbacks (called by MemoryGame)                              #
    # ------------------------------------------------------------------ #

    def _on_state_change(self, state):
        """Called after every state change to refresh the UI."""
        if not self.winfo_exists():
            return
        self.after(0, self._refresh_cards)
        self.after(0, self._update_hud)

    def _refresh_cards(self):
        """Sync card widget visual states with game state only when changed."""
        state = self.game.state
        if not state:
            return
        for card in state.cards:
            cw = self._card_widgets[card.index] if card.index < len(self._card_widgets) else None
            if cw is None:
                continue
            img = self._image_cache.get(card.image_path)
            if card.state == "matched":
                if not cw._is_matched:
                    if not cw._is_flipped:
                        cw.flip_to_face(img)
                    else:
                        cw.set_matched(img)
            elif card.state == "flipped":
                if not cw._is_flipped:
                    cw.flip_to_face(img)
            else:  # hidden
                if cw._is_flipped or cw._is_matched:
                    cw.flip_to_back()

    def _on_match(self, card1_idx: int, card2_idx: int):
        """Called when two cards match."""
        _try_sound(self.app.sound_mixer, "match")
        cb = self.after(100, lambda: self._animate_match(card1_idx, card2_idx))
        self._after_ids.append(cb)

    def _animate_match(self, idx1: int, idx2: int):
        """Trigger bounce + glow on matched cards."""
        for idx in (idx1, idx2):
            cw = self._card_widgets[idx] if idx < len(self._card_widgets) else None
            if cw:
                img = self._image_cache.get(self.game.state.cards[idx].image_path)
                cw.set_matched(img)
                cw.bounce()
        self._update_hud()

    def _on_mismatch(self, card1_idx: int, card2_idx: int):
        """Called when two flipped cards don't match — shake then flip back."""
        cb1 = self.after(100, lambda: self._animate_mismatch(card1_idx, card2_idx))
        self._after_ids.append(cb1)
        cb2 = self.after(720, self._resolve_mismatch_ui)
        self._after_ids.append(cb2)

    def _resolve_mismatch_ui(self):
        """Flip mismatched cards back in game logic and refresh UI."""
        if not self.winfo_exists():
            return
        self.game.resolve_mismatch()
        self._refresh_cards()
        self._update_hud()

    def _animate_mismatch(self, idx1: int, idx2: int):
        """Shake both cards; after shake the game logic will flip them back."""
        for idx in (idx1, idx2):
            cw = self._card_widgets[idx] if idx < len(self._card_widgets) else None
            if cw:
                cw.shake()
        self._update_hud()

    def _on_win(self, state):
        """Called when the player wins all 12 pairs."""
        _try_sound(self.app.sound_mixer, "win")
        # Stop timer display updates
        self._cancel_timer()
        # Save score in background, then show win dialog
        self._save_score_async(state, callback=lambda is_record: self.after(0, lambda: self._show_win_dialog(state, is_record)))

    # ------------------------------------------------------------------ #
    #  HUD Update                                                          #
    # ------------------------------------------------------------------ #

    def _update_hud(self):
        """Refresh all HUD badges from game state with dynamic streak styling."""
        if not self.winfo_exists():
            return
        state = self.game.state
        if not state:
            return
        self._score_badge.update_value(str(max(0, state.score)))
        self._moves_badge.update_value(str(state.moves))
        if state.current_streak >= 2:
            self._streak_badge.update_value(f"{state.current_streak}  🔥 COMBO!")
            self._streak_badge.set_color(PINK)
        else:
            self._streak_badge.update_value(str(state.current_streak))
            self._streak_badge.set_color(PURPLE)

    # ------------------------------------------------------------------ #
    #  Win Dialog                                                          #
    # ------------------------------------------------------------------ #

    def _show_win_dialog(self, state, is_new_record: bool):
        """Show the win popup dialog."""
        from ui.win_dialog import WinDialog
        dialog = WinDialog(
            parent=self.winfo_toplevel(),
            score=max(0, state.score),
            moves=state.moves,
            time_seconds=state.time_seconds,
            best_streak=state.best_streak,
            is_new_record=is_new_record,
            on_play_again=self._on_new_game,
            on_leaderboard=self._on_leaderboard,
            on_logout=self._on_logout,
        )

    # ------------------------------------------------------------------ #
    #  Score Saving                                                        #
    # ------------------------------------------------------------------ #

    def _save_score_async(self, state, callback: Callable[[bool], None]):
        """Save the score in a background thread, then call callback(is_new_record)."""
        if self._score_saved:
            callback(False)
            return
        self._score_saved = True
        user_id = self.current_user["id"]
        score = max(0, state.score)
        moves = state.moves
        time_s = state.time_seconds
        streak = state.best_streak

        def _worker():
            is_record = False
            if self.db is not None and user_id > 0:
                try:
                    is_record = self.db.is_new_record(user_id, score)
                    self.db.save_score(user_id, score, moves, time_s, streak)
                    logger.info(f"Score saved: user={user_id} score={score}")
                except Exception as e:
                    logger.error(f"Failed to save score: {e}")
                    self._score_saved = False  # allow retry
            self.after(0, lambda: callback(is_record))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    # ------------------------------------------------------------------ #
    #  Button Handlers                                                     #
    # ------------------------------------------------------------------ #

    def _on_new_game(self):
        """Start a fresh new game."""
        self.game.stop_timer()
        self._cancel_all_callbacks()
        self._score_saved = False
        self._start_new_game()

    def _on_leaderboard(self):
        """Switch to leaderboard screen."""
        self.game.stop_timer()
        self._cancel_all_callbacks()
        self.app.show_leaderboard()

    def _on_logout(self):
        """Log out and return to login screen."""
        self.game.stop_timer()
        self._cancel_all_callbacks()
        self.app.show_login()

    def _show_error(self, message: str):
        """Show an error dialog (non-crashing)."""
        import tkinter.messagebox as mb
        mb.showerror("Error", message, parent=self.winfo_toplevel())

    # ------------------------------------------------------------------ #
    #  Callback Management                                                 #
    # ------------------------------------------------------------------ #

    def _cancel_timer(self):
        """Cancel only the timer callback."""
        if self._timer_cb:
            try:
                self.after_cancel(self._timer_cb)
            except Exception:
                pass
            self._timer_cb = None

    def _cancel_all_callbacks(self):
        """Cancel every tracked after() callback."""
        for cb_id in self._after_ids:
            try:
                self.after_cancel(cb_id)
            except Exception:
                pass
        self._after_ids.clear()
        self._timer_cb = None
        # Also tell card widgets to cancel theirs
        for cw in self._card_widgets:
            if cw is not None:
                try:
                    cw.cancel_animations()
                except Exception:
                    pass

    def destroy(self):
        """Override destroy to clean up before widget removal."""
        self._cancel_all_callbacks()
        self.game.stop_timer()
        super().destroy()

