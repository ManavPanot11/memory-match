"""
Login screen for Memory Match game.
"""

import threading
import customtkinter as ctk
from ui.theme import COLORS, get_font, CORNER_RADIUS
from ui.widgets import RoundedButton
from auth import verify_password


class LoginScreen(ctk.CTkFrame):
    """Login screen with username/password fields and navigation links."""

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS["background"], corner_radius=0)
        self.app = app
        self._build_ui()
        self.username_entry.focus_set()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Lay out all widgets."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Outer centering frame
        outer = ctk.CTkFrame(self, fg_color=COLORS["background"], corner_radius=0)
        outer.grid(row=0, column=0)

        # Card
        FIELD_WIDTH = 340
        card = ctk.CTkFrame(
            outer,
            fg_color=COLORS["card"],
            corner_radius=CORNER_RADIUS * 2,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.pack(padx=20, pady=20, ipadx=24, ipady=20)

        # Title
        ctk.CTkLabel(
            card,
            text="🃏 Memory Match",
            font=get_font("title"),
            text_color=COLORS["primary"],
        ).pack(pady=(16, 4))

        ctk.CTkLabel(
            card,
            text="Welcome back! Sign in to continue.",
            font=get_font("body"),
            text_color=COLORS["text_muted"],
        ).pack(pady=(0, 20))

        # ── Username ──────────────────────────────────────────────────
        ctk.CTkLabel(
            card,
            text="Username",
            font=get_font("label"),
            text_color=COLORS["text"],
            anchor="w",
            width=FIELD_WIDTH,
        ).pack(padx=20, pady=(0, 2))

        self.username_var = ctk.StringVar()
        self.username_entry = ctk.CTkEntry(
            card,
            textvariable=self.username_var,
            placeholder_text="Enter your username",
            font=get_font("body"),
            height=40,
            corner_radius=CORNER_RADIUS,
            border_color=COLORS["border"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            width=FIELD_WIDTH,
        )
        self.username_entry.pack(padx=20, pady=(0, 10))
        self.username_entry.bind("<Return>", lambda _: self.on_login())
        self.username_entry.bind("<Key>", self._clear_error)

        # ── Password ──────────────────────────────────────────────────
        ctk.CTkLabel(
            card,
            text="Password",
            font=get_font("label"),
            text_color=COLORS["text"],
            anchor="w",
            width=FIELD_WIDTH,
        ).pack(padx=20, pady=(0, 2))

        pw_frame = ctk.CTkFrame(card, fg_color="transparent", width=FIELD_WIDTH, height=40)
        pw_frame.pack_propagate(False)
        pw_frame.pack(padx=20, pady=(0, 4))

        self.password_var = ctk.StringVar()
        self.password_entry = ctk.CTkEntry(
            pw_frame,
            textvariable=self.password_var,
            placeholder_text="Enter your password",
            font=get_font("body"),
            height=40,
            corner_radius=CORNER_RADIUS,
            border_color=COLORS["border"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            show="•",
        )
        self.password_entry.pack(side="left", fill="x", expand=True)
        self.password_entry.bind("<Return>", lambda _: self.on_login())
        self.password_entry.bind("<Key>", self._clear_error)

        self._pw_visible = False
        self.eye_btn = ctk.CTkButton(
            pw_frame,
            text="Show",
            width=50,
            height=40,
            corner_radius=CORNER_RADIUS,
            fg_color=COLORS["input_bg"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_muted"],
            border_width=1,
            border_color=COLORS["border"],
            font=get_font(11, "bold"),
            command=self._toggle_password,
            cursor="hand2",
        )
        self.eye_btn.pack(side="right", padx=(6, 0))

        # ── Forgot password link ──────────────────────────────────────
        forgot_wrap = ctk.CTkFrame(card, fg_color="transparent", width=FIELD_WIDTH)
        forgot_wrap.pack(padx=20, pady=(0, 12))
        ctk.CTkButton(
            forgot_wrap,
            text="Forgot Password?",
            font=get_font("link"),
            fg_color="transparent",
            hover_color=COLORS["hover_link"],
            text_color=COLORS["link"],
            anchor="e",
            command=self.app.show_forgot_password,
            cursor="hand2",
            height=20,
        ).pack(side="right")

        # ── Error label ───────────────────────────────────────────────
        self.error_var = ctk.StringVar()
        self.error_label = ctk.CTkLabel(
            card,
            textvariable=self.error_var,
            font=get_font("small"),
            text_color=COLORS["error"],
        )
        self.error_label.pack(pady=(0, 4))

        # ── Login button ──────────────────────────────────────────────
        self.login_btn = RoundedButton(
            card,
            text="Log In",
            command=self.on_login,
            width=340,
            height=48,
            fg_color=COLORS["coral"],
            hover_color=COLORS["coral_hover"],
            font=get_font("button"),
        )
        self.login_btn.pack(padx=20, pady=(4, 10))

        # ── Guest play button ─────────────────────────────────────────
        self.guest_btn = RoundedButton(
            card,
            text="🎮 Play as Guest (Quick Play)",
            command=self.on_guest_login,
            width=340,
            height=40,
            fg_color=COLORS["input_bg"],
            hover_color=COLORS["border"],
            text_color=COLORS["primary"],
            border_width=2,
            border_color=COLORS["primary"],
            font=get_font(13, "bold"),
        )
        self.guest_btn.pack(padx=20, pady=(0, 14))

        # ── Sign-up link ──────────────────────────────────────────────
        link_frame = ctk.CTkFrame(card, fg_color="transparent")
        link_frame.pack(pady=(0, 24))

        ctk.CTkLabel(
            link_frame,
            text="Don't have an account?",
            font=get_font("body"),
            text_color=COLORS["text_muted"],
        ).pack(side="left")

        ctk.CTkButton(
            link_frame,
            text="Sign Up",
            font=get_font("link"),
            fg_color="transparent",
            hover_color=COLORS["hover_link"],
            text_color=COLORS["link"],
            command=self.app.show_signup,
        ).pack(side="left", padx=(2, 0))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _toggle_password(self):
        self._pw_visible = not self._pw_visible
        self.password_entry.configure(show="" if self._pw_visible else "•")
        self.eye_btn.configure(text="Hide" if self._pw_visible else "Show")

    def _clear_error(self, _event=None):
        if self.error_var.get():
            self.error_var.set("")

    def _set_loading(self, loading: bool):
        state = "disabled" if loading else "normal"
        self.login_btn.configure(state=state)
        self.login_btn.configure(
            text="Logging in…" if loading else "Log In"
        )

    def _show_error(self, msg: str):
        self.error_var.set(msg)

    # ------------------------------------------------------------------
    # Logic
    # ------------------------------------------------------------------

    def on_guest_login(self):
        """Allow immediate play without requiring MySQL database credentials."""
        guest_user = {
            "id": 0,
            "username": "guest",
            "display_name": "Guest",
            "email": "guest@memorymatch.local",
        }
        self.app.show_game(guest_user)

    def on_login(self):
        username = self.username_var.get().strip().lower()
        password = self.password_var.get()

        if not username:
            self._show_error("Please enter your username.")
            self.username_entry.focus_set()
            return
        if not password:
            self._show_error("Please enter your password.")
            self.password_entry.focus_set()
            return

        if self.app.db is None:
            self._show_error("Database is not connected. Please check MySQL.")
            return

        self._set_loading(True)
        self.error_var.set("")

        def _worker():
            try:
                user = self.app.db.get_user_by_username(username)
                if user is None or not verify_password(password, user["password_hash"]):
                    self.after(0, lambda: self._show_error(
                        "Invalid username or password."))
                    self.after(0, lambda: self._set_loading(False))
                    return
                self.after(0, lambda: self.app.show_game(user))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._show_error(
                    f"Connection error: {exc}"))
                self.after(0, lambda: self._set_loading(False))

        threading.Thread(target=_worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_show(self):
        """Called when this screen becomes visible."""
        self.username_entry.focus_set()
        self.error_var.set("")
        self._set_loading(False)
