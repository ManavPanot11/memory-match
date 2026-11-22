"""
Forgot-password screen for Memory Match game.
"""

import threading
import customtkinter as ctk
from ui.theme import COLORS, get_font, CORNER_RADIUS
from ui.widgets import RoundedButton
from auth import hash_password, validate_password


class ForgotPasswordScreen(ctk.CTkFrame):
    """Screen that lets a user reset their password by verifying username + email."""

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS["background"], corner_radius=0)
        self.app = app
        self._redirect_after_id = None
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

        card = ctk.CTkFrame(
            outer,
            fg_color=COLORS["card"],
            corner_radius=CORNER_RADIUS * 2,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.pack(padx=20, pady=16, ipadx=24, ipady=16)

        W = 340

        # ── Top Bar: Back to Login button ─────────────────────────────
        top_bar = ctk.CTkFrame(card, fg_color="transparent", width=W)
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
            text="🔑 Reset Password",
            font=get_font(24, "bold"),
            text_color=COLORS["primary"],
        ).pack(pady=(4, 2))

        ctk.CTkLabel(
            card,
            text="Enter your details to reset your password.",
            font=get_font("body"),
            text_color=COLORS["text_muted"],
        ).pack(pady=(0, 14))

        # ── Username ──────────────────────────────────────────────────
        ctk.CTkLabel(
            card, text="Username", font=get_font("label"),
            text_color=COLORS["text"], anchor="w", width=W
        ).pack(padx=16, pady=(4, 2))
        self.username_var = ctk.StringVar()
        self.username_entry = ctk.CTkEntry(
            card, textvariable=self.username_var,
            placeholder_text="Enter your username",
            font=get_font("body"), height=38, corner_radius=CORNER_RADIUS,
            border_color=COLORS["border"], fg_color=COLORS["input_bg"],
            text_color=COLORS["text"], width=W,
        )
        self.username_entry.pack(padx=16, pady=(0, 6))
        self.username_entry.bind("<Return>", lambda _: self.on_submit())
        self.username_entry.bind("<Key>", self._clear_error)

        # ── Email ─────────────────────────────────────────────────────
        ctk.CTkLabel(
            card, text="Email", font=get_font("label"),
            text_color=COLORS["text"], anchor="w", width=W
        ).pack(padx=16, pady=(4, 2))
        self.email_var = ctk.StringVar()
        self.email_entry = ctk.CTkEntry(
            card, textvariable=self.email_var,
            placeholder_text="Registered email address",
            font=get_font("body"), height=38, corner_radius=CORNER_RADIUS,
            border_color=COLORS["border"], fg_color=COLORS["input_bg"],
            text_color=COLORS["text"], width=W,
        )
        self.email_entry.pack(padx=16, pady=(0, 6))
        self.email_entry.bind("<Return>", lambda _: self.on_submit())
        self.email_entry.bind("<Key>", self._clear_error)

        # ── New Password ──────────────────────────────────────────────
        ctk.CTkLabel(
            card, text="New Password", font=get_font("label"),
            text_color=COLORS["text"], anchor="w", width=W
        ).pack(padx=16, pady=(4, 2))

        pw_frame = ctk.CTkFrame(card, fg_color="transparent", width=W, height=38)
        pw_frame.pack_propagate(False)
        pw_frame.pack(padx=16, pady=(0, 6))

        self.new_pw_var = ctk.StringVar()
        self.new_pw_entry = ctk.CTkEntry(
            pw_frame, textvariable=self.new_pw_var,
            placeholder_text="At least 6 characters",
            font=get_font("body"), height=38, corner_radius=CORNER_RADIUS,
            border_color=COLORS["border"], fg_color=COLORS["input_bg"],
            text_color=COLORS["text"], show="•",
        )
        self.new_pw_entry.pack(side="left", fill="x", expand=True)
        self.new_pw_entry.bind("<Return>", lambda _: self.on_submit())
        self.new_pw_entry.bind("<Key>", self._clear_error)

        self._pw1_visible = False
        self._eye1 = ctk.CTkButton(
            pw_frame, text="Show", width=50, height=38,
            corner_radius=CORNER_RADIUS, fg_color=COLORS["input_bg"],
            hover_color=COLORS["border"], text_color=COLORS["text_muted"],
            border_width=1, border_color=COLORS["border"],
            font=get_font(11, "bold"), command=self._toggle_pw1,
            cursor="hand2",
        )
        self._eye1.pack(side="right", padx=(6, 0))

        # ── Confirm New Password ──────────────────────────────────────
        ctk.CTkLabel(
            card, text="Confirm New Password", font=get_font("label"),
            text_color=COLORS["text"], anchor="w", width=W
        ).pack(padx=16, pady=(4, 2))

        cpw_frame = ctk.CTkFrame(card, fg_color="transparent", width=W, height=38)
        cpw_frame.pack_propagate(False)
        cpw_frame.pack(padx=16, pady=(0, 6))

        self.confirm_pw_var = ctk.StringVar()
        self.confirm_pw_entry = ctk.CTkEntry(
            cpw_frame, textvariable=self.confirm_pw_var,
            placeholder_text="Re-enter new password",
            font=get_font("body"), height=38, corner_radius=CORNER_RADIUS,
            border_color=COLORS["border"], fg_color=COLORS["input_bg"],
            text_color=COLORS["text"], show="•",
        )
        self.confirm_pw_entry.pack(side="left", fill="x", expand=True)
        self.confirm_pw_entry.bind("<Return>", lambda _: self.on_submit())
        self.confirm_pw_entry.bind("<Key>", self._clear_error)

        self._pw2_visible = False
        self._eye2 = ctk.CTkButton(
            cpw_frame, text="Show", width=50, height=38,
            corner_radius=CORNER_RADIUS, fg_color=COLORS["input_bg"],
            hover_color=COLORS["border"], text_color=COLORS["text_muted"],
            border_width=1, border_color=COLORS["border"],
            font=get_font(11, "bold"), command=self._toggle_pw2,
            cursor="hand2",
        )
        self._eye2.pack(side="right", padx=(6, 0))

        # ── Feedback label ────────────────────────────────────────────
        self.feedback_var = ctk.StringVar()
        self.feedback_lbl = ctk.CTkLabel(
            card,
            textvariable=self.feedback_var,
            font=get_font("small"),
            text_color=COLORS["error"],
        )
        self.feedback_lbl.pack(pady=(2, 4))

        # ── Submit button ─────────────────────────────────────────────
        self.submit_btn = RoundedButton(
            card,
            text="Reset Password",
            command=self.on_submit,
            width=W,
            height=44,
            fg_color=COLORS["coral"],
            hover_color=COLORS["coral_hover"],
            font=get_font("button"),
        )
        self.submit_btn.pack(padx=16, pady=(4, 12))

        # ── Bottom Back link ──────────────────────────────────────────
        ctk.CTkButton(
            card,
            text="← Back to Login",
            font=get_font("link"),
            fg_color="transparent",
            hover_color=COLORS["hover_link"],
            text_color=COLORS["link"],
            command=self.app.show_login,
            cursor="hand2",
        ).pack(pady=(0, 10))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _toggle_pw1(self):
        self._pw1_visible = not self._pw1_visible
        self.new_pw_entry.configure(show="" if self._pw1_visible else "•")
        self._eye1.configure(text="Hide" if self._pw1_visible else "Show")

    def _toggle_pw2(self):
        self._pw2_visible = not self._pw2_visible
        self.confirm_pw_entry.configure(show="" if self._pw2_visible else "•")
        self._eye2.configure(text="Hide" if self._pw2_visible else "Show")

    def _clear_error(self, _event=None):
        if self.feedback_var.get():
            self.feedback_var.set("")
            self.feedback_lbl.configure(text_color=COLORS["error"])

    def _show_error(self, msg: str):
        self.feedback_lbl.configure(text_color=COLORS["error"])
        self.feedback_var.set(msg)

    def _show_success(self, msg: str):
        self.feedback_lbl.configure(text_color=COLORS["success"])
        self.feedback_var.set(msg)

    def _set_loading(self, loading: bool):
        self.submit_btn.configure(
            state="disabled" if loading else "normal",
            text="Resetting…" if loading else "Reset Password",
        )

    # ------------------------------------------------------------------
    # Logic
    # ------------------------------------------------------------------

    def on_submit(self):
        username = self.username_var.get().strip().lower()
        email = self.email_var.get().strip().lower()
        new_pw = self.new_pw_var.get()
        confirm_pw = self.confirm_pw_var.get()

        # ── Local validation ──────────────────────────────────────────
        if not username:
            self._show_error("Please enter your username.")
            self.username_entry.focus_set()
            return
        if not email:
            self._show_error("Please enter your email address.")
            self.email_entry.focus_set()
            return
        if not new_pw:
            self._show_error("Please enter a new password.")
            self.new_pw_entry.focus_set()
            return

        is_valid, pw_err = validate_password(new_pw, confirm_pw)
        if not is_valid:
            self._show_error(pw_err)
            self.new_pw_entry.focus_set()
            return

        if self.app.db is None:
            self._show_error("Database is not connected. Please check MySQL.")
            return

        self._set_loading(True)
        self._clear_error()

        def _worker():
            try:
                user = self.app.db.get_user_by_username(username)
                if user is None:
                    self.after(0, lambda: self._show_error(
                        "No account found with that username."))
                    self.after(0, lambda: self._set_loading(False))
                    return

                if user.get("email", "").lower() != email:
                    self.after(0, lambda: self._show_error(
                        "Username and email do not match."))
                    self.after(0, lambda: self._set_loading(False))
                    return

                pw_hash = hash_password(new_pw)
                self.app.db.update_password(user["id"], pw_hash)

                self.after(0, lambda: self._show_success(
                    "Password reset! Redirecting to login…"))
                # Auto-redirect after 2 seconds
                self._redirect_after_id = self.after(
                    2000, self.app.show_login
                )
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._show_error(
                    f"Error: {exc}"))
                self.after(0, lambda: self._set_loading(False))

        threading.Thread(target=_worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_show(self):
        if self._redirect_after_id is not None:
            try:
                self.after_cancel(self._redirect_after_id)
            except Exception:  # noqa: BLE001
                pass
            self._redirect_after_id = None
        self.username_entry.focus_set()
        self.feedback_var.set("")
        self._set_loading(False)
