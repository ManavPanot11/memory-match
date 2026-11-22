"""
game.py - Pure game logic for the Memory Match Tiles game.

No GUI imports. Uses only stdlib + Pillow (PIL).
"""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from PIL import Image, ImageDraw, ImageFont


# ---------------------------------------------------------------------------
# Helper: list valid images
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def list_valid_images(images_dir: str) -> List[str]:
    """Return a sorted list of valid image file paths in *images_dir*.

    A file is considered valid if:
    - Its extension is in SUPPORTED_EXTENSIONS (case-insensitive).
    - It can be opened and verified by Pillow without error.

    Corrupt or unreadable files are silently skipped.

    Args:
        images_dir: Path to the directory containing image files.

    Returns:
        A list of absolute paths to valid image files, sorted for
        deterministic ordering before any randomisation.
    """
    valid: List[str] = []

    if not os.path.isdir(images_dir):
        return valid

    for filename in sorted(os.listdir(images_dir)):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue

        filepath = os.path.abspath(os.path.join(images_dir, filename))
        try:
            with Image.open(filepath) as img:
                img.verify()  # Pillow verifies the file without decoding fully
            valid.append(filepath)
        except Exception:
            # Skip corrupt or unreadable files
            pass

    return valid


# ---------------------------------------------------------------------------
# Helper: generate placeholder images
# ---------------------------------------------------------------------------

# Palette of vibrant icon emojis and pastel card backgrounds
_STUDIO_EMOJIS = [
    '🍓', '🥑', '🍕', '🍩', '🍔', '🍦', '💎', '🚀', '🎮', '⭐',
    '🎨', '🎧', '🏆', '⚽', '🏀', '🎸', '👑', '⚡', '🌈', '🎈',
    '🍒', '🍉', '🍍', '🍇', '🍋', '🍎', '🌸', '🦋', '🦄', '🦁'
]

_STUDIO_PASTELS = [
    ('#FFF0F3', '#FFCCD5'), ('#F0FFF4', '#C6F6D5'), ('#FFF5EB', '#FEEBC8'),
    ('#F7FAFC', '#E2E8F0'), ('#FAF5FF', '#E9D8FD'), ('#EBF8FF', '#BEE3F8'),
    ('#FFFFF0', '#FEFCBF'), ('#F0FDFA', '#CCFBF1'), ('#FFF1F2', '#FECDD3'),
    ('#FFFBEB', '#FDE68A'), ('#F3F4F6', '#E5E7EB'), ('#ECFDF5', '#A7F3D0'),
    ('#F5F3FF', '#DDD6FE'), ('#EFF6FF', '#BFDBFE'), ('#FEF2F2', '#FECACA'),
    ('#FFF7ED', '#FFEDD5'), ('#FAFAF9', '#E7E5E4'), ('#FDF2F8', '#FBCFE8'),
    ('#F0FDF4', '#BBF7D0'), ('#F8FAFC', '#E2E8F0'), ('#FFF1F2', '#FFE4E6'),
    ('#ECFCCB', '#D9F99D'), ('#FEF9C3', '#FEF08A'), ('#F3E8FF', '#E9D8FD'),
    ('#E0E7FF', '#C7D2FE'), ('#FFE4E6', '#FECDD3'), ('#FCE7F3', '#FBCFE8'),
    ('#CFFAFE', '#A5F3FC'), ('#EDE9FE', '#DDD6FE'), ('#FEF3C7', '#FDE68A')
]


def generate_placeholder_images(images_dir: str, count: int = 30) -> List[str]:
    """Generate *count* colourful, studio-grade icon PNG images in *images_dir*.

    Each image features a crisp rounded card with soft pastel fill and
    an energetic full-colour icon or emblem.

    Args:
        images_dir: Directory where images are saved. Created if necessary.
        count: Number of placeholder images to generate (default 30).

    Returns:
        A list of absolute paths to the generated PNG files.
    """
    os.makedirs(images_dir, exist_ok=True)

    emoji_font_path = 'C:/Windows/Fonts/seguiemj.ttf'
    has_emoji_font = os.path.exists(emoji_font_path)

    generated: List[str] = []
    for i in range(count):
        emoji = _STUDIO_EMOJIS[i % len(_STUDIO_EMOJIS)]
        bg, border = _STUDIO_PASTELS[i % len(_STUDIO_PASTELS)]

        img = Image.new("RGBA", (200, 200), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Rounded card plate
        draw.rounded_rectangle([8, 8, 192, 192], radius=24, fill=bg, outline=border, width=3)

        if has_emoji_font:
            try:
                font = ImageFont.truetype(emoji_font_path, 88)
                bbox = draw.textbbox((0, 0), emoji, font=font, embedded_color=True)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                x = (200 - w) // 2 - bbox[0]
                y = (200 - h) // 2 - bbox[1]
                draw.text((x, y), emoji, font=font, embedded_color=True)
            except Exception:
                has_emoji_font = False

        if not has_emoji_font:
            # Fallback for systems without seguiemj
            font = ImageFont.load_default()
            label = f"#{i + 1:02d}"
            draw.text((80, 85), label, fill=(50, 50, 50), font=font)

        filename = f"placeholder_{i + 1:03d}.png"
        filepath = os.path.abspath(os.path.join(images_dir, filename))
        img.save(filepath, "PNG")
        generated.append(filepath)

    return generated


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Card:
    """Represents a single card on the game board.

    Attributes:
        index:      Unique position index in the flat card list (0-23).
        image_path: Absolute path to the image shown when the card is flipped.
        state:      Current card state: 'hidden', 'flipped', or 'matched'.
        row:        Row position in the 4-row × 6-column grid.
        col:        Column position in the 4-row × 6-column grid.
    """
    index: int
    image_path: str
    state: str  # 'hidden' | 'flipped' | 'matched'
    row: int
    col: int


@dataclass
class GameState:
    """Snapshot of the complete game state.

    Attributes:
        cards:           Flat list of all 24 Card objects (row-major order).
        score:           Current score (never below 0).
        moves:           Number of pair-flip attempts so far.
        time_seconds:    Elapsed seconds since the first card was flipped.
        best_streak:     Longest consecutive-match streak in this game.
        current_streak:  Current consecutive-match streak.
        is_locked:       True while the board is locked (mismatch delay).
        game_over:       True once all 12 pairs are matched.
        timer_started:   True after the first card flip.
        flipped_cards:   Indices (into *cards*) of currently flipped cards
                         (0, 1, or 2 entries).
    """
    cards: List[Card] = field(default_factory=list)
    score: int = 0
    moves: int = 0
    time_seconds: int = 0
    best_streak: int = 0
    current_streak: int = 0
    is_locked: bool = False
    game_over: bool = False
    timer_started: bool = False
    flipped_cards: List[int] = field(default_factory=list)


# ---------------------------------------------------------------------------
# MemoryGame class
# ---------------------------------------------------------------------------

GRID_ROWS = 4
GRID_COLS = 6
PAIRS_NEEDED = GRID_ROWS * GRID_COLS // 2   # 12
TOTAL_CARDS = GRID_ROWS * GRID_COLS          # 24

MATCH_SCORE = 100
COMBO_SCORE_PER_LEVEL = 50  # bonus = 50 × (streak_length - 1) for streak >= 2
MISMATCH_PENALTY = 10
MISMATCH_DELAY_MS = 800      # milliseconds before flipping mismatched cards back


class MemoryGame:
    """Core game logic for Memory Match Tiles.

    Responsibilities:
    - Selecting and shuffling images from a directory.
    - Maintaining card state (hidden / flipped / matched).
    - Enforcing flip rules (locking, ignoring duplicates, etc.).
    - Computing score, streaks, and time bonus.
    - Firing optional UI callbacks.

    Usage::

        game = MemoryGame("images/")
        state = game.new_game()
        game.on_match = lambda s: print("match!", s.score)
        game.flip_card(0)
        game.flip_card(5)

    Attributes:
        images_dir:   Path to the directory containing game images.
        on_match:     Called with (GameState) after a successful match.
        on_mismatch:  Called with (GameState) after a failed match.
        on_win:       Called with (GameState) when all pairs are found.
        on_state_change: Called with (GameState) on every state change.
    """

    def __init__(self, images_dir: str) -> None:
        """Initialise the game engine.

        Args:
            images_dir: Path to the directory containing image assets.
                        May be relative; stored as-is and resolved at
                        new_game() time.
        """
        self.images_dir: str = images_dir

        # Optional UI callbacks (set by the GUI layer after construction)
        self.on_match: Optional[Callable[[GameState], None]] = None
        self.on_mismatch: Optional[Callable[[GameState], None]] = None
        self.on_win: Optional[Callable[[GameState], None]] = None
        self.on_state_change: Optional[Callable[[GameState], None]] = None

        # Internal state — populated by new_game()
        self._state: Optional[GameState] = None
        self._start_time: Optional[float] = None

        # Internal: track whether a mismatch-flip-back is pending so that
        # the GUI can schedule a delayed callback.  The GUI is responsible
        # for calling flip_card with index=-1 (or for calling the returned
        # callable) after MISMATCH_DELAY_MS ms.  Internally we store the two
        # card indices that need flipping back.
        self._pending_flip_back: Optional[tuple[int, int]] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def new_game(self) -> GameState:
        """Start a brand-new game.

        Selects 12 distinct valid images at random, duplicates each to form
        24 cards, shuffles them, and places them on a 4×6 grid.

        Returns:
            The initial GameState for the new game.

        Raises:
            ValueError: If fewer than 12 valid images are found in images_dir,
                        with a descriptive message suitable for display to the
                        user.
        """
        valid_images = list_valid_images(self.images_dir)

        if len(valid_images) < PAIRS_NEEDED:
            raise ValueError(
                f"Not enough valid images found in '{self.images_dir}'. "
                f"Need at least {PAIRS_NEEDED}, but found {len(valid_images)}. "
                f"Add more images or run generate_placeholder_images() first."
            )

        # Pick 12 distinct images and duplicate to make 24 cards
        chosen = random.sample(valid_images, PAIRS_NEEDED)
        image_paths = chosen * 2
        random.shuffle(image_paths)

        # Build Card objects
        cards: List[Card] = []
        for idx, path in enumerate(image_paths):
            row = idx // GRID_COLS
            col = idx % GRID_COLS
            cards.append(Card(index=idx, image_path=path, state="hidden",
                               row=row, col=col))

        self._state = GameState(cards=cards)
        self._start_time = None
        self._pending_flip_back = None

        self._fire(self.on_state_change)
        return self._state

    def flip_card(self, index: int) -> None:
        """Attempt to flip the card at position *index*.

        All flip rules are enforced here:
        - Ignored if the board is locked.
        - Ignored if the card is already 'flipped' or 'matched'.
        - Ignored if *index* is the same as the first flipped card.
        - After two flips, checks for a match or schedules a flip-back.

        The method may schedule an asynchronous flip-back via the internal
        ``_schedule_flip_back`` method (which in a GUI context is delegated
        to the GUI's event loop via ``_resolve_mismatch``).

        Args:
            index: Zero-based index into state.cards.
        """
        state = self._state
        if state is None or state.game_over:
            return

        # Rule: board locked
        if state.is_locked:
            return

        # Validate index range
        if index < 0 or index >= len(state.cards):
            return

        card = state.cards[index]

        # Rule: ignore already flipped or matched
        if card.state in ("flipped", "matched"):
            return

        # Rule: ignore if same card as first flip
        if len(state.flipped_cards) == 1 and state.flipped_cards[0] == index:
            return

        # Start the timer on the very first flip
        if not state.timer_started:
            state.timer_started = True
            self._start_time = time.time()

        # Flip the card
        card.state = "flipped"
        state.flipped_cards.append(index)

        self._fire(self.on_state_change)

        # Only evaluate when two cards are face-up
        if len(state.flipped_cards) == 2:
            self._evaluate_pair()

    def get_elapsed_seconds(self) -> int:
        """Return the number of whole seconds elapsed since the first flip.

        Returns 0 if the timer has not started or the game is over.

        Returns:
            Elapsed seconds as a non-negative integer.
        """
        if self._start_time is None or self._state is None:
            return 0
        if self._state.game_over:
            return self._state.time_seconds
        elapsed = int(time.time() - self._start_time)
        self._state.time_seconds = elapsed
        return elapsed

    def stop_timer(self) -> None:
        """Freeze the timer (called when the game is won or paused)."""
        if self._state is not None and self._start_time is not None:
            self._state.time_seconds = int(time.time() - self._start_time)
        self._start_time = None

    def restart(self) -> GameState:
        """Restart the game with the same images directory.

        Equivalent to calling new_game() — re-randomises both image selection
        and card positions.

        Returns:
            A fresh GameState.
        """
        return self.new_game()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> Optional[GameState]:
        """The current GameState, or None if new_game() has not been called."""
        return self._state

    @property
    def is_game_over(self) -> bool:
        """True if all pairs have been matched in the current game."""
        return self._state is not None and self._state.game_over

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evaluate_pair(self) -> None:
        """Evaluate the two currently face-up cards for a match.

        If they share the same image path → match (score, streak updates).
        Otherwise → mismatch (lock board, schedule flip-back).
        """
        state = self._state
        idx_a, idx_b = state.flipped_cards
        card_a = state.cards[idx_a]
        card_b = state.cards[idx_b]

        state.moves += 1

        if card_a.image_path == card_b.image_path:
            # ---- Match ----
            card_a.state = "matched"
            card_b.state = "matched"
            state.flipped_cards.clear()

            # Update streak
            state.current_streak += 1
            if state.current_streak > state.best_streak:
                state.best_streak = state.current_streak

            # Base score
            earned = MATCH_SCORE
            # Combo bonus for consecutive matches
            if state.current_streak >= 2:
                earned += COMBO_SCORE_PER_LEVEL * (state.current_streak - 1)

            state.score = max(0, state.score + earned)

            self._fire(self.on_state_change, self._state)
            self._fire(self.on_match, idx_a, idx_b)

            # Check win condition
            if all(c.state == "matched" for c in state.cards):
                self._handle_win()
        else:
            # ---- Mismatch ----
            state.current_streak = 0
            state.score = max(0, state.score - MISMATCH_PENALTY)
            state.is_locked = True

            self._fire(self.on_state_change, self._state)
            self._fire(self.on_mismatch, idx_a, idx_b)

            # Remember which cards to flip back
            self._pending_flip_back = (idx_a, idx_b)
            # The GUI layer should schedule _resolve_mismatch after
            # MISMATCH_DELAY_MS.  In test/headless mode callers may call it
            # directly via resolve_mismatch().

    def resolve_mismatch(self) -> None:
        """Flip the two mismatched cards back to hidden and unlock the board.

        In a GUI context this is called after MISMATCH_DELAY_MS via the event
        loop.  In tests it can be called immediately.
        """
        state = self._state
        if state is None or self._pending_flip_back is None:
            return

        idx_a, idx_b = self._pending_flip_back
        self._pending_flip_back = None

        state.cards[idx_a].state = "hidden"
        state.cards[idx_b].state = "hidden"
        state.flipped_cards.clear()
        state.is_locked = False

        self._fire(self.on_state_change)

    def _handle_win(self) -> None:
        """Mark the game as won and apply the time bonus."""
        state = self._state
        state.game_over = True
        self.stop_timer()

        # Time bonus: max(0, 300 - seconds_taken)
        time_bonus = max(0, 300 - state.time_seconds)
        state.score = max(0, state.score + time_bonus)

        self._fire(self.on_state_change)
        self._fire(self.on_win)

    def _fire(self, callback: Optional[Callable], *args) -> None:
        """Safely invoke *callback*, trying provided *args*, then (self._state), then ()."""
        if callback is None or self._state is None:
            return
        try:
            if args:
                try:
                    callback(*args)
                    return
                except TypeError:
                    pass
            try:
                callback(self._state)
            except TypeError:
                callback()
        except Exception:
            pass  # Never let a callback crash the game logic
