"""
tests/test_game.py - Unit tests for game.py

Uses unittest and a temporary directory populated with placeholder images.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

# Ensure the project root is on sys.path so we can import game.py
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from game import (  # noqa: E402
    MemoryGame,
    GameState,
    generate_placeholder_images,
    PAIRS_NEEDED,
    TOTAL_CARDS,
    MATCH_SCORE,
    COMBO_SCORE_PER_LEVEL,
    MISMATCH_PENALTY,
)


# ---------------------------------------------------------------------------
# Test fixture helpers
# ---------------------------------------------------------------------------

class BaseGameTest(unittest.TestCase):
    """Base class that sets up a temp image directory with 15 placeholder images."""

    NUM_IMAGES = 15  # > 12, so new_game() can always pick 12

    def setUp(self) -> None:
        """Create a temporary directory with placeholder images."""
        self._tmpdir = tempfile.TemporaryDirectory()
        self.images_dir: str = self._tmpdir.name
        generate_placeholder_images(self.images_dir, count=self.NUM_IMAGES)
        self.game = MemoryGame(self.images_dir)
        self.state = self.game.new_game()

    def tearDown(self) -> None:
        """Remove the temporary directory."""
        self._tmpdir.cleanup()

    # ------------------------------------------------------------------
    # Utility helpers used across multiple tests
    # ------------------------------------------------------------------

    def _find_pair(self) -> tuple[int, int]:
        """Return the indices of two cards that share the same image path."""
        from collections import defaultdict
        groups: dict[str, list[int]] = defaultdict(list)
        for card in self.state.cards:
            groups[card.image_path].append(card.index)
        for path, indices in groups.items():
            if len(indices) >= 2 and self.state.cards[indices[0]].state == "hidden":
                a, b = indices[0], indices[1]
                if self.state.cards[a].state == "hidden" and \
                   self.state.cards[b].state == "hidden":
                    return a, b
        raise AssertionError("Could not find a valid hidden pair.")

    def _find_mismatch(self) -> tuple[int, int]:
        """Return indices of two hidden cards that do NOT share an image path."""
        hidden = [c for c in self.state.cards if c.state == "hidden"]
        for i, ca in enumerate(hidden):
            for cb in hidden[i + 1:]:
                if ca.image_path != cb.image_path:
                    return ca.index, cb.index
        raise AssertionError("Could not find a mismatched hidden pair.")

    def _match_pair(self, idx_a: int, idx_b: int) -> None:
        """Flip two matching cards and resolve the match."""
        self.game.flip_card(idx_a)
        self.game.flip_card(idx_b)
        # Matches are resolved synchronously — no unlock needed.

    def _mismatch_pair(self, idx_a: int, idx_b: int) -> None:
        """Flip two non-matching cards and resolve the flip-back."""
        self.game.flip_card(idx_a)
        self.game.flip_card(idx_b)
        # Resolve mismatch synchronously (no real delay in tests)
        self.game.resolve_mismatch()


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestNewGame(BaseGameTest):
    """Tests for new_game() initialisation."""

    def test_new_game_card_count(self) -> None:
        """new_game() produces exactly 24 cards."""
        self.assertEqual(len(self.state.cards), TOTAL_CARDS,
                         f"Expected {TOTAL_CARDS} cards, got {len(self.state.cards)}")

    def test_new_game_pairs(self) -> None:
        """Each image appears exactly twice among the 24 cards."""
        from collections import Counter
        path_counts = Counter(c.image_path for c in self.state.cards)
        for path, count in path_counts.items():
            self.assertEqual(
                count, 2,
                f"Image {os.path.basename(path)} appears {count} times, expected 2."
            )
        self.assertEqual(len(path_counts), PAIRS_NEEDED,
                         f"Expected {PAIRS_NEEDED} distinct images, got {len(path_counts)}.")

    def test_shuffle_randomness(self) -> None:
        """Two consecutive new_game() calls must differ in ordering at least once in 5 tries."""
        def card_order(state: GameState) -> tuple[str, ...]:
            return tuple(c.image_path for c in state.cards)

        first_order = card_order(self.state)
        found_different = False
        for _ in range(5):
            new_state = self.game.new_game()
            if card_order(new_state) != first_order:
                found_different = True
                break

        self.assertTrue(
            found_different,
            "Card order was identical across 5 consecutive new_game() calls — "
            "shuffling does not appear to be working."
        )

    def test_insufficient_images_raises(self) -> None:
        """new_game() raises ValueError when fewer than 12 valid images exist."""
        with tempfile.TemporaryDirectory() as d:
            generate_placeholder_images(d, count=5)
            game = MemoryGame(d)
            with self.assertRaises(ValueError):
                game.new_game()


class TestFlipRules(BaseGameTest):
    """Tests for flip rule enforcement."""

    def test_flip_hidden_card(self) -> None:
        """Flipping a hidden card changes its state to 'flipped'."""
        target_idx = next(c.index for c in self.state.cards if c.state == "hidden")
        self.game.flip_card(target_idx)
        self.assertEqual(self.state.cards[target_idx].state, "flipped",
                         "Card should be 'flipped' after a valid flip.")

    def test_flip_matched_card_ignored(self) -> None:
        """Flipping a matched card is ignored (state stays 'matched')."""
        a, b = self._find_pair()
        self._match_pair(a, b)

        # Both should be matched now
        self.assertEqual(self.state.cards[a].state, "matched")
        self.assertEqual(self.state.cards[b].state, "matched")

        score_before = self.state.score
        moves_before = self.state.moves

        # Attempt to flip a matched card
        self.game.flip_card(a)
        self.assertEqual(self.state.cards[a].state, "matched",
                         "Matched card should not change state.")
        self.assertEqual(self.state.score, score_before,
                         "Score should not change when clicking a matched card.")
        self.assertEqual(self.state.moves, moves_before,
                         "Move count should not change when clicking a matched card.")

    def test_flip_locked_ignored(self) -> None:
        """Flipping while locked (mismatch delay) is ignored."""
        a, b = self._find_mismatch()
        self.game.flip_card(a)
        self.game.flip_card(b)

        # Board should now be locked
        self.assertTrue(self.state.is_locked, "Board should be locked after mismatch.")

        # Find a third hidden card
        hidden_others = [
            c.index for c in self.state.cards
            if c.state == "hidden" and c.index not in (a, b)
        ]
        self.assertTrue(hidden_others, "Need a third hidden card for this test.")
        third = hidden_others[0]

        state_before = self.state.cards[third].state
        self.game.flip_card(third)
        self.assertEqual(self.state.cards[third].state, state_before,
                         "Card flip should be ignored when board is locked.")

    def test_flip_same_card_twice_ignored(self) -> None:
        """Flipping the same card a second time is ignored."""
        hidden = next(c.index for c in self.state.cards if c.state == "hidden")
        self.game.flip_card(hidden)
        flipped_count_before = sum(1 for c in self.state.cards if c.state == "flipped")

        # Flip the same card again
        self.game.flip_card(hidden)
        flipped_count_after = sum(1 for c in self.state.cards if c.state == "flipped")
        self.assertEqual(flipped_count_before, flipped_count_after,
                         "Flipping the same card twice should not increase flipped count.")
        self.assertEqual(len(self.state.flipped_cards), 1,
                         "flipped_cards should still contain only one entry.")


class TestScoring(BaseGameTest):
    """Tests for scoring logic."""

    def test_match_scoring(self) -> None:
        """Matching two cards increases score by 100 (first match, no combo)."""
        score_before = self.state.score
        a, b = self._find_pair()
        self._match_pair(a, b)
        expected = score_before + MATCH_SCORE
        self.assertEqual(self.state.score, expected,
                         f"Score should increase by {MATCH_SCORE} on first match.")

    def test_mismatch_scoring(self) -> None:
        """A mismatch decreases score by 10."""
        # Give the player some score first to avoid hitting zero
        a, b = self._find_pair()
        self._match_pair(a, b)
        score_before_mismatch = self.state.score

        c, d = self._find_mismatch()
        self._mismatch_pair(c, d)

        expected = max(0, score_before_mismatch - MISMATCH_PENALTY)
        self.assertEqual(self.state.score, expected,
                         f"Score should decrease by {MISMATCH_PENALTY} on mismatch.")

    def test_combo_bonus(self) -> None:
        """Second consecutive match gives +150 total (100 base + 50 combo)."""
        # First match (no combo yet)
        a1, b1 = self._find_pair()
        self._match_pair(a1, b1)
        score_after_first = self.state.score
        self.assertEqual(self.state.current_streak, 1)

        # Second consecutive match → combo bonus
        a2, b2 = self._find_pair()
        self._match_pair(a2, b2)

        expected_gain = MATCH_SCORE + COMBO_SCORE_PER_LEVEL * 1  # streak=2 → bonus=50
        self.assertEqual(self.state.score, score_after_first + expected_gain,
                         "Second consecutive match should award 100 + 50 combo bonus.")
        self.assertEqual(self.state.current_streak, 2)

    def test_best_streak_tracking(self) -> None:
        """best_streak updates correctly across matches and mismatches."""
        # Two consecutive matches → best_streak should be 2
        a1, b1 = self._find_pair()
        self._match_pair(a1, b1)
        a2, b2 = self._find_pair()
        self._match_pair(a2, b2)
        self.assertEqual(self.state.best_streak, 2)

        # A mismatch resets current_streak but not best_streak
        c, d = self._find_mismatch()
        self._mismatch_pair(c, d)
        self.assertEqual(self.state.current_streak, 0)
        self.assertEqual(self.state.best_streak, 2,
                         "best_streak should not drop after a mismatch.")

        # Single match after mismatch → current_streak=1, best_streak still 2
        a3, b3 = self._find_pair()
        self._match_pair(a3, b3)
        self.assertEqual(self.state.current_streak, 1)
        self.assertEqual(self.state.best_streak, 2)

    def test_score_never_negative(self) -> None:
        """Score stays >= 0 even after many mismatches from a zero start."""
        # The score starts at 0; apply many mismatches
        for _ in range(20):
            try:
                c, d = self._find_mismatch()
            except AssertionError:
                break  # No more mismatched pairs available
            self._mismatch_pair(c, d)
            self.assertGreaterEqual(self.state.score, 0,
                                    "Score should never go below 0.")


class TestWinCondition(BaseGameTest):
    """Tests for the win condition."""

    def test_win_condition(self) -> None:
        """Matching all 12 pairs sets game_over to True."""
        self.assertFalse(self.state.game_over)

        # Collect pairs grouped by image path
        from collections import defaultdict
        groups: dict[str, list[int]] = defaultdict(list)
        for card in self.state.cards:
            groups[card.image_path].append(card.index)

        win_callback_called = []
        self.game.on_win = lambda s: win_callback_called.append(True)

        for path, indices in groups.items():
            self.assertEqual(len(indices), 2,
                             "Every image must appear exactly twice.")
            a, b = indices
            # Re-fetch state in case indices have changed (they don't in this impl)
            self._match_pair(a, b)

        self.assertTrue(self.state.game_over,
                        "game_over should be True after all 12 pairs are matched.")
        self.assertTrue(win_callback_called, "on_win callback should have been fired.")
        self.assertFalse(self.game.is_game_over is False,
                         "is_game_over property should return True.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
