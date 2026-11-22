"""
ui/widgets.py
=============
Reusable custom widgets for the Memory Match Tiles game.

Widgets
-------
- :class:`RoundedButton`  – stylised CTkButton subclass with hover feedback.
- :class:`PillBadge`      – pill-shaped score/info badge with dynamic color transitions.
- :class:`CardWidget`     – ultra-responsive memory card with tactile hover, 84ms flip,
                            and non-blocking shake and bounce animations.

All visual constants are imported from :mod:`ui.theme`.
"""

from __future__ import annotations

import logging
from typing import Callable, List, Optional

import customtkinter as ctk

from ui.theme import (
    CARD_BACK_TEXT,
    CARD_COLORS,
    CARD_DEFAULT_BORDER,
    CARD_HEIGHT,
    CARD_MATCHED_BORDER,
    CARD_WIDTH,
    SKY_BLUE,
    WHITE,
    _darken,
    button_style,
    get_font,
    pill_badge_style,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RoundedButton
# ---------------------------------------------------------------------------

class RoundedButton(ctk.CTkButton):
    """
    A :class:`ctk.CTkButton` subclass pre-configured with the game's visual
    defaults: rounded corners, themed colour, hand cursor, and hover shade.
    """

    def __init__(
        self,
        master,
        *,
        color: Optional[str] = None,
        hover_color: Optional[str] = None,
        text_color: str = WHITE,
        corner_radius: int = 20,
        height: int = 40,
        font_size: int = 14,
        **kwargs,
    ) -> None:
        btn_color = color or kwargs.get("fg_color", SKY_BLUE)
        resolved_hover = hover_color or kwargs.get("hover_color") or _darken(btn_color, 0.15)
        style = button_style(
            color=btn_color,
            text_color=text_color,
            hover_color=resolved_hover,
            corner_radius=corner_radius,
            height=height,
            font_size=font_size,
        )
        merged = {**style, **kwargs}
        if "color" in merged:
            del merged["color"]
        super().__init__(master, **merged)


# ---------------------------------------------------------------------------
# PillBadge
# ---------------------------------------------------------------------------

class PillBadge(ctk.CTkFrame):
    """
    A pill-shaped badge displaying a ``label: value`` pair with dynamic
    value and background color updates.
    """

    def __init__(
        self,
        master,
        *,
        label: str,
        value=0,
        color: Optional[str] = None,
        bg_color: Optional[str] = None,
        text_color: str = WHITE,
        font_size: int = 13,
        pad_x: int = 14,
        pad_y: int = 4,
        **kwargs,
    ) -> None:
        self._current_color = color or bg_color or kwargs.pop("fg_color", SKY_BLUE)
        if "color" in kwargs:
            del kwargs["color"]
        frame_kwargs = {**pill_badge_style(bg_color=self._current_color, text_color=text_color), **kwargs}
        super().__init__(master, **frame_kwargs)

        self._label_text = label
        self._text_color = text_color
        self._font_size = font_size
        self._pad_x = pad_x
        self._pad_y = pad_y

        self._lbl = ctk.CTkLabel(
            self,
            text=self._build_text(value),
            font=get_font(font_size, "bold"),
            text_color=text_color,
            fg_color="transparent",
        )
        self._lbl.pack(padx=pad_x, pady=pad_y)

    def _build_text(self, value) -> str:
        return f"{self._label_text}: {value}"

    def update_value(self, new_val) -> None:
        """Update the displayed value portion of the badge."""
        self._lbl.configure(text=self._build_text(new_val))

    def set_color(self, new_color: str) -> None:
        """Dynamically update the badge background color."""
        if new_color != self._current_color:
            self._current_color = new_color
            self.configure(fg_color=new_color)


# ---------------------------------------------------------------------------
# CardWidget
# ---------------------------------------------------------------------------

class CardWidget(ctk.CTkFrame):
    """
    An interactive memory-card widget with rock-solid grid positioning,
    tactile hover response, 84ms 3D flip animation, and non-blocking
    bounce and shake effects.
    """

    def __init__(
        self,
        master,
        *,
        card_index: int,
        on_click: Callable[[int], None],
        back_color: Optional[str] = None,
        width: int = CARD_WIDTH,
        height: int = CARD_HEIGHT,
        **kwargs,
    ) -> None:
        self._card_index = card_index
        self._on_click = on_click
        self._back_color = back_color or CARD_COLORS[card_index % len(CARD_COLORS)]
        self._card_width = width
        self._card_height = height

        self._face_image = None
        self._is_flipped = False
        self._is_matched = False
        self._animating = False
        self._is_hovered = False

        self._after_ids: List[str] = []

        # The outer frame is transparent and strictly obeys its grid cell.
        # It NEVER resizes, shifts, or changes geometry managers.
        frame_kwargs = {
            "fg_color": "transparent",
            "corner_radius": 0,
            "border_width": 0,
            **kwargs,
        }
        super().__init__(master, **frame_kwargs)

        # ── Inner Card Body ──────────────────────────────────────────
        self._body = ctk.CTkFrame(
            self,
            corner_radius=14,
            border_width=2,
            border_color=CARD_DEFAULT_BORDER,
            fg_color=self._back_color,
            cursor="hand2",
        )
        self._body.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0, relheight=1.0)

        # ── Back-face widgets ──────────────────────────────────────────
        self._back_frame = ctk.CTkFrame(
            self._body,
            fg_color="transparent",
            corner_radius=12,
            cursor="hand2",
        )
        self._back_frame.place(relx=0.5, rely=0.5, anchor="center")

        self._question_lbl = ctk.CTkLabel(
            self._back_frame,
            text="?",
            font=get_font(44, "bold"),
            text_color=CARD_BACK_TEXT,
            fg_color="transparent",
            cursor="hand2",
        )
        self._question_lbl.pack()

        # ── Face widgets ───────────────────────────────────────────────
        self._face_frame = ctk.CTkFrame(
            self._body,
            fg_color="transparent",
            corner_radius=12,
        )

        self._face_image_lbl = ctk.CTkLabel(
            self._face_frame,
            text="",
            fg_color="transparent",
        )
        self._face_image_lbl.pack(expand=True, fill="both")

        # ── Bind click & hover ────────────────────────────────────────
        for w in (self, self._body, self._back_frame, self._question_lbl, self._face_frame, self._face_image_lbl):
            w.bind("<Button-1>", self._handle_click)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        self.bind("<Destroy>", self._on_destroy)

    # ------------------------------------------------------------------
    # Hover & Click handling
    # ------------------------------------------------------------------

    def _on_enter(self, _event=None) -> None:
        """Subtle tactile border glow when hovering unflipped cards."""
        if not self._is_matched and not self._is_flipped and not self._animating:
            self._is_hovered = True
            try:
                self._body.configure(border_color="#FFFFFF", border_width=3)
            except Exception:
                pass

    def _on_leave(self, _event=None) -> None:
        """Restore normal border on mouse leave."""
        if not self._is_matched and not self._is_flipped and not self._animating:
            self._is_hovered = False
            try:
                self._body.configure(border_color=CARD_DEFAULT_BORDER, border_width=2)
            except Exception:
                pass

    def _handle_click(self, _event=None) -> None:
        """Invoke on_click if card is available to be flipped."""
        if not self._is_matched and not self._is_flipped:
            self._on_click(self._card_index)

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def flip_to_face(self, image=None) -> None:
        """Flip from back face to front face with 3D horizontal shrink/grow."""
        if self._is_matched:
            return
        self._cancel_pending()

        if image is not None:
            self._face_image = image
            self._face_image_lbl.configure(image=image)

        if self._is_flipped:
            self._show_face()
            try:
                self._body.place_configure(relx=0.5, rely=0.5, relwidth=1.0, relheight=1.0)
            except Exception:
                pass
            return

        self._is_flipped = True
        self._animating = True
        self._animate_flip_shrink(on_halfway=self._show_face)

    def flip_to_back(self) -> None:
        """Flip from front face back to candy back face."""
        if self._is_matched:
            return
        self._cancel_pending()

        if not self._is_flipped:
            self._show_back()
            try:
                self._body.place_configure(relx=0.5, rely=0.5, relwidth=1.0, relheight=1.0)
            except Exception:
                pass
            return

        self._is_flipped = False
        self._animating = True
        self._animate_flip_shrink(on_halfway=self._show_back)

    def set_matched(self, image=None) -> None:
        """Lock the card in matched state with emerald glow border."""
        self._is_matched = True
        self._is_flipped = True
        self._animating = False
        self._cancel_pending()

        if image is not None:
            self._face_image = image
            self._face_image_lbl.configure(image=image)

        self._show_face()
        try:
            self._body.configure(
                border_color=CARD_MATCHED_BORDER,
                border_width=4,
                fg_color="#FFFFFF",
                cursor="arrow",
            )
            self._body.place_configure(relx=0.5, rely=0.5, relwidth=1.0, relheight=1.0)
        except Exception:
            pass

    def cancel_animations(self) -> None:
        """Cancel all pending animation callbacks."""
        self._cancel_pending()
        self._animating = False
        try:
            self._body.place_configure(relx=0.5, rely=0.5, relwidth=1.0, relheight=1.0)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Animation implementations (Snappy 84ms 3-step interpolation)
    # ------------------------------------------------------------------

    def _show_face(self) -> None:
        try:
            self._back_frame.place_forget()
            self._face_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.92, relheight=0.92)
            self._body.configure(fg_color="#FFFFFF", border_color=CARD_DEFAULT_BORDER, border_width=2)
        except Exception:
            pass

    def _show_back(self) -> None:
        try:
            self._face_frame.place_forget()
            self._back_frame.place(relx=0.5, rely=0.5, anchor="center")
            self._body.configure(
                fg_color=self._back_color,
                border_color=CARD_DEFAULT_BORDER,
                border_width=2,
                cursor="hand2",
            )
        except Exception:
            pass

    def _animate_flip_shrink(self, on_halfway: Callable, step: int = 0) -> None:
        total_steps = 3
        if step <= total_steps:
            frac = max(0.04, 1.0 - (step / total_steps))
            try:
                self._body.place_configure(relx=0.5, rely=0.5, relwidth=frac, relheight=1.0)
            except Exception:
                return
            aid = self.after(14, lambda s=step + 1: self._animate_flip_shrink(on_halfway, s))
            self._after_ids.append(aid)
        else:
            on_halfway()
            self._animate_flip_grow(0)

    def _animate_flip_grow(self, step: int = 0) -> None:
        total_steps = 3
        if step <= total_steps:
            frac = min(1.0, max(0.04, step / total_steps))
            try:
                self._body.place_configure(relx=0.5, rely=0.5, relwidth=frac, relheight=1.0)
            except Exception:
                return
            aid = self.after(14, lambda s=step + 1: self._animate_flip_grow(s))
            self._after_ids.append(aid)
        else:
            self._animating = False
            try:
                self._body.place_configure(relx=0.5, rely=0.5, relwidth=1.0, relheight=1.0)
            except Exception:
                pass

    def shake(self) -> None:
        """Play a smooth horizontal wobble on mismatch without affecting grid layout."""
        if not self._is_flipped and not self._is_matched:
            self._show_face()
            self._is_flipped = True
        self._cancel_pending()
        self._animating = True
        offsets = [-0.04, 0.04, -0.03, 0.03, -0.015, 0.015, 0.0]
        self._schedule_shake(offsets, 0)

    def _schedule_shake(self, offsets: List[float], idx: int) -> None:
        if idx >= len(offsets):
            self._animating = False
            try:
                self._body.place_configure(relx=0.5, rely=0.5, relwidth=1.0, relheight=1.0)
            except Exception:
                pass
            return
        dx = offsets[idx]
        try:
            self._body.place_configure(relx=0.5 + dx, rely=0.5, relwidth=1.0, relheight=1.0)
        except Exception:
            return
        aid = self.after(20, lambda: self._schedule_shake(offsets, idx + 1))
        self._after_ids.append(aid)

    def bounce(self) -> None:
        """Play a smooth vertical pop/bounce on match."""
        if not self._is_flipped and not self._is_matched:
            self._show_face()
            self._is_flipped = True
        self._cancel_pending()
        self._animating = True
        lifts = [0.0, -0.06, -0.09, -0.05, 0.02, 0.0]
        self._schedule_bounce(lifts, 0)

    def _schedule_bounce(self, lifts: List[float], idx: int) -> None:
        if idx >= len(lifts):
            self._animating = False
            try:
                self._body.place_configure(relx=0.5, rely=0.5, relwidth=1.0, relheight=1.0)
            except Exception:
                pass
            return
        dy = lifts[idx]
        try:
            self._body.place_configure(relx=0.5, rely=0.5 + dy, relwidth=1.0, relheight=1.0)
        except Exception:
            return
        aid = self.after(20, lambda: self._schedule_bounce(lifts, idx + 1))
        self._after_ids.append(aid)

    def _cancel_pending(self) -> None:
        for aid in self._after_ids:
            try:
                self.after_cancel(aid)
            except Exception:
                pass
        self._after_ids.clear()
        self._animating = False

    def _on_destroy(self, _event=None) -> None:
        self._cancel_pending()
