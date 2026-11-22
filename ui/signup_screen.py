"""
Signup screen for Memory Match game.
"""

import threading
import customtkinter as ctk
from ui.theme import COLORS, get_font, CORNER_RADIUS
from ui.widgets import RoundedButton
from auth import (
    hash_password,
    validate_username,
    validate_email,
    validate_password,
)


class SignupScreen(ctk.CTkFrame):
    """Registration screen with username, email, and password fields."""

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS["background"], corner_radius=0)
        self.app = app
        self._build_ui()
        self.username_entry.focus_set()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        outer = ctk.CTkFrame(self, fg_color=COLORS["background"], corner_radius=0)
        outer.grid(row=0, column=0)

        # Centered card with clean proportions and padding
        card = ctk.CTkFrame(
            outer,
            fg_color=COLORS["card"],
            corner_radius=CORNER_RADIUS * 2,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.pack(padx=20, pady=16, ipadx=24, ipady=16)

        FIELD_WIDTH = 340

        # ── Top Bar: Back to Login button ─────────────────────────────
        top_bar = ctk.CTkFrame(card, fg_color="transparent", width=FIELD_WIDTH)
        top_bar.pack(fill="x", padx=16, pady=(10, 4))

        back_btn = ctk.CTkButton(
            top_bar,
            text="← Back to Login",
            font=get_font("small_button"),
            fg_color="transparent",
            hover_color=COLORS["table_header"],
            text_color=COLORS["primary"],
            width=110,
            height=28,
            corner_radius=14,
            command=self.app.show_login,
            cursor="hand2",
        )
        back_btn.pack(side="left")

        # ── Title & Subtitle ──────────────────────────────────────────
        ctk.CTkLabel(
            card,
            text="🃏 Memory Match",
            font=get_font(24, "bold"),
            text_color=COLORS["primary"],
        ).pack(pady=(4, 2))

        ctk.CTkLabel(
            card,
            text="Create an account to track your scores.",
            font=get_font("body"),
            text_color=COLORS["text_muted"],
        ).pack(pady=(0, 14))

        # ── Username ──────────────────────────────────────────────────
        self.username_var, self.username_entry, self.username_err_lbl = \
            self._field_block(card, "Username", FIELD_WIDTH, "Choose a username")
        self.username_entry.bind("<Return>", lambda _: self.on_signup())
        self.username_entry.bind(
            "<Key>", lambda e: self._clear_field_error(self.username_err_lbl))

        # ── Email ─────────────────────────────────────────────────────
        self.email_var, self.email_entry, self.email_err_lbl = \
            self._field_block(card, "Email", FIELD_WIDTH, "name@example.com")
        self.email_entry.bind("<Return>", lambda _: self.on_signup())
        self.email_entry.bind(
            "<Key>", lambda e: self._clear_field_error(self.email_err_lbl))

        # ── Password ──────────────────────────────────────────────────
        self.password_var, self.password_entry, self.pw_err_lbl = \
            self._password_block(card, "Password", FIELD_WIDTH, "At least 6 characters")
        self.password_entry.bind("<Return>", lambda _: self.on_signup())
        self.password_entry.bind(
            "<Key>", lambda e: self._clear_field_error(self.pw_err_lbl))

        # ── Confirm Password ──────────────────────────────────────────
        self.confirm_var, self.confirm_entry, self.confirm_err_lbl = \
            self._password_block(card, "Confirm Password", FIELD_WIDTH, "Re-enter password")
        self.confirm_entry.bind("<Return>", lambda _: self.on_signup())
        self.confirm_entry.bind(
            "<Key>", lambda e: self._clear_field_error(self.confirm_err_lbl))

        # ── Global error label ────────────────────────────────────────
        self.global_err_var = ctk.StringVar()
        self.global_err_lbl = ctk.CTkLabel(
            card,
            textvariable=self.global_err_var,
            font=get_font("small"),
            text_color=COLORS["error"],
        )
        self.global_err_lbl.pack(pady=(2, 4))

        # ── Sign-up button ────────────────────────────────────────────
        self.signup_btn = RoundedButton(
            card,
            text="Create Account",
            command=self.on_signup,
            width=FIELD_WIDTH,
            height=44,
            fg_color=COLORS["mint"],
            hover_color=COLORS["mint_hover"],
            font=get_font("button"),
        )
        self.signup_btn.pack(padx=16, pady=(4, 12))

        # ── Bottom Login link ─────────────────────────────────────────
        link_frame = ctk.CTkFrame(card, fg_color="transparent")
        link_frame.pack(pady=(0, 10))

        ctk.CTkLabel(
            link_frame,
            text="Already have an account?",
            font=get_font("body"),
            text_color=COLORS["text_muted"],
        ).pack(side="left")

        ctk.CTkButton(
            link_frame,
            text="Log In",
            font=get_font("link"),
            fg_color="transparent",
            hover_color=COLORS["hover_link"],
            text_color=COLORS["link"],
            width=60,
            command=self.app.show_login,
            cursor="hand2",
        ).pack(side="left", padx=(4, 0))

    # ------------------------------------------------------------------
    # Helper builders
    # ------------------------------------------------------------------

    def _field_block(self, parent, label_text, width, placeholder):
        """Build a labelled entry with aligned width and compact error label."""
        ctk.CTkLabel(
            parent,
            text=label_text,
            font=get_font("label"),
            text_color=COLORS["text"],
            anchor="w",
            width=width,
        ).pack(padx=16, pady=(4, 2))

        var = ctk.StringVar()
        entry = ctk.CTkEntry(
            parent,
            textvariable=var,
            placeholder_text=placeholder,
            font=get_font("body"),
            height=38,
            corner_radius=CORNER_RADIUS,
            border_color=COLORS["border"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            width=width,
        )
        entry.pack(padx=16, pady=(0, 1))

        err_var = ctk.StringVar()
        err_lbl = ctk.CTkLabel(
            parent,
            textvariable=err_var,
            font=get_font(11),
            text_color=COLORS["error"],
            anchor="w",
            width=width,
            height=14,
        )
        err_lbl.pack(padx=16, pady=(0, 3))
        err_lbl._err_var = err_var  # type: ignore[attr-defined]
        return var, entry, err_lbl

    def _password_block(self, parent, label_text, width, placeholder):
        """Build a password entry with show/hide toggle, strictly matching width."""
        ctk.CTkLabel(
            parent,
            text=label_text,
            font=get_font("label"),
            text_color=COLORS["text"],
            anchor="w",
            width=width,
        ).pack(padx=16, pady=(4, 2))

        pw_frame = ctk.CTkFrame(parent, fg_color="transparent", width=width, height=38)
        pw_frame.pack_propagate(False)
        pw_frame.pack(padx=16, pady=(0, 1))

        var = ctk.StringVar()
        entry = ctk.CTkEntry(
            pw_frame,
            textvariable=var,
            placeholder_text=placeholder,
            font=get_font("body"),
            height=38,
            corner_radius=CORNER_RADIUS,
            border_color=COLORS["border"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            show="•",
        )
        entry.pack(side="left", fill="x", expand=True)

        visible_state = [False]

        def toggle():
            visible_state[0] = not visible_state[0]
            entry.configure(show="" if visible_state[0] else "•")
            eye.configure(text="Hide" if visible_state[0] else "Show")

        eye = ctk.CTkButton(
            pw_frame,
            text="Show",
            width=50,
            height=38,
            corner_radius=CORNER_RADIUS,
            fg_color=COLORS["input_bg"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_muted"],
            border_width=1,
            border_color=COLORS["border"],
            font=get_font(11, "bold"),
            command=toggle,
            cursor="hand2",
        )
        eye.pack(side="right", padx=(6, 0))

        err_var = ctk.StringVar()
        err_lbl = ctk.CTkLabel(
            parent,
            textvariable=err_var,
            font=get_font(11),
            text_color=COLORS["error"],
            anchor="w",
            width=width,
            height=14,
        )
        err_lbl.pack(padx=16, pady=(0, 3))
        err_lbl._err_var = err_var  # type: ignore[attr-defined]
        return var, entry, err_lbl

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _clear_field_error(self, lbl):
        lbl._err_var.set("")  # type: ignore[attr-defined]

    def _set_field_error(self, lbl, msg):
        lbl._err_var.set(msg)  # type: ignore[attr-defined]

    def _set_loading(self, loading: bool):
        state = "disabled" if loading else "normal"
        self.signup_btn.configure(
            state=state,
            text="Creating Account…" if loading else "Create Account"
        )

    def _clear_all_errors(self):
        for lbl in (
            self.username_err_lbl,
            self.email_err_lbl,
            self.pw_err_lbl,
            self.confirm_err_lbl,
        ):
            self._clear_field_error(lbl)
        self.global_err_var.set("")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_fields(self):
        """Return True only if all fields pass local validation."""
        ok = True

        raw_username = self.username_var.get().strip()
        if not raw_username:
            self._set_field_error(self.username_err_lbl, "Username is required.")
            ok = False
        else:
            is_valid, err = validate_username(raw_username)
            if not is_valid:
                self._set_field_error(self.username_err_lbl, err)
                ok = False

        email = self.email_var.get().strip()
        if not email:
            self._set_field_error(self.email_err_lbl, "Email is required.")
            ok = False
        else:
            is_valid, err = validate_email(email)
            if not is_valid:
                self._set_field_error(self.email_err_lbl, err)
                ok = False

        password = self.password_var.get()
        confirm = self.confirm_var.get()
        if not password:
            self._set_field_error(self.pw_err_lbl, "Password is required.")
            ok = False
        else:
            is_valid, err = validate_password(password, confirm)
            if not is_valid:
                if "match" in err.lower():
                    self._set_field_error(self.confirm_err_lbl, err)
                else:
                    self._set_field_error(self.pw_err_lbl, err)
                ok = False

        if not confirm and password:
            self._set_field_error(self.confirm_err_lbl, "Please confirm your password.")
            ok = False

        return ok

    # ------------------------------------------------------------------
    # Logic
    # ------------------------------------------------------------------

    def on_signup(self):
        self._clear_all_errors()

        if not self._validate_fields():
            return

        if self.app.db is None:
            self.global_err_var.set("Database is not connected. Please check MySQL.")
            return

        display_name = self.username_var.get().strip()
        username = display_name.lower()
        email = self.email_var.get().strip().lower()
        password = self.password_var.get()

        self._set_loading(True)

        def _worker():
            try:
                # Check uniqueness
                if self.app.db.get_user_by_username(username) is not None:
                    self.after(0, lambda: self._set_field_error(
                        self.username_err_lbl, "Username already taken."))
                    self.after(0, lambda: self._set_loading(False))
                    return

                if self.app.db.get_user_by_email(email) is not None:
                    self.after(0, lambda: self._set_field_error(
                        self.email_err_lbl, "Email already registered."))
                    self.after(0, lambda: self._set_loading(False))
                    return

                pw_hash = hash_password(password)
                user_id = self.app.db.create_user(username, display_name, email, pw_hash)
                user = self.app.db.get_user_by_username(username)
                if not user:
                    user = {
                        "id": user_id,
                        "username": username,
                        "display_name": display_name,
                        "email": email,
                    }
                self.after(0, lambda: self.app.show_game(user))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self.global_err_var.set(
                    f"Registration failed: {exc}"))
                self.after(0, lambda: self._set_loading(False))

        threading.Thread(target=_worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_show(self):
        self.username_entry.focus_set()
        self._clear_all_errors()
        self._set_loading(False)
