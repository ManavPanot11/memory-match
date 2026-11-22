"""
Win dialog (popup) for Memory Match game.
"""

import random
import tkinter as tk
import customtkinter as ctk
from ui.theme import COLORS, get_font, CORNER_RADIUS


# ---------------------------------------------------------------------------
# Confetti particle
# ---------------------------------------------------------------------------

class _Particle:
    """Represents one falling confetti piece."""

    PALETTE = [
        "#FF6B6B", "#FFD93D", "#6BCB77", "#4D96FF",
        "#C77DFF", "#FF9F43", "#FF6EC7", "#43E8D8",
    ]

    def __init__(self, canvas_width: int, canvas_height: int):
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.reset(start_at_top=True)

    def reset(self, start_at_top: bool = False):
        self.x = random.uniform(0, self.canvas_width)
        self.y = random.uniform(-50, 0) if start_at_top else random.uniform(
            -self.canvas_height, 0
        )
        self.w = random.randint(6, 14)
        self.h = random.randint(4, 10)
        self.color = random.choice(self.PALETTE)
        self.vy = random.uniform(2.0, 5.0)
        self.vx = random.uniform(-1.5, 1.5)
        self.angle = random.uniform(0, 360)
        self.spin = random.uniform(-6, 6)
        self.shape = random.choice(("rect", "oval"))

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.angle += self.spin
        if self.y > self.canvas_height + 20:
            self.reset()


# ---------------------------------------------------------------------------
# WinDialog
# ---------------------------------------------------------------------------

class WinDialog(ctk.CTkToplevel):
    """Modal win dialog with confetti animation."""

    _CONFETTI_FPS = 30  # target frames per second
    _PARTICLE_COUNT = 80

    def __init__(
        self,
        parent,
        score: int,
        moves: int,
        time_seconds: float,
        best_streak: int,
        is_new_record: bool,
        on_play_again,
        on_leaderboard,
        on_logout,
    ):
        super().__init__(parent)
        self.title("You Won! 🎉")
        self.resizable(False, False)

        self._on_play_again = on_play_again
        self._on_leaderboard = on_leaderboard
        self._on_logout = on_logout
        self._is_new_record = is_new_record

        self._confetti_after_id = None
        self._record_pulse_id = None
        self._particles: list[_Particle] = []

        # Prevent closing via the X button without choosing an action
        self.protocol("WM_DELETE_WINDOW", self._on_wm_delete)

        self._build_ui(score, moves, time_seconds, best_streak, is_new_record)
        self._center_on_parent(parent)

        # Start confetti after window is rendered
        self.after(100, self.start_confetti)

        # Grab focus
        self.grab_set()
        self.focus_set()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, score, moves, time_seconds, best_streak, is_new_record):
        # Outer purple background
        self.configure(fg_color=COLORS["win_bg"])

        outer = ctk.CTkFrame(self, fg_color=COLORS["win_bg"], corner_radius=0)
        outer.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Confetti canvas (behind everything) ───────────────────────
        CANVAS_W, CANVAS_H = 480, 520
        self._canvas = tk.Canvas(
            outer,
            width=CANVAS_W,
            height=CANVAS_H,
            bg=COLORS["win_bg"],
            highlightthickness=0,
        )
        self._canvas.place(x=0, y=0)

        # ── Content on top of canvas ──────────────────────────────────
        content = ctk.CTkFrame(
            outer,
            fg_color="transparent",
            corner_radius=0,
            width=CANVAS_W,
            height=CANVAS_H,
        )
        content.place(x=0, y=0)
        content.pack_propagate(False)

        # Title
        ctk.CTkLabel(
            content,
            text="🎉 You Won! 🎉",
            font=get_font("win_title"),
            text_color="#FFFFFF",
        ).pack(pady=(36, 4))

        # New record banner
        if is_new_record:
            self._record_lbl = ctk.CTkLabel(
                content,
                text="⭐ NEW RECORD! ⭐",
                font=get_font("record"),
                text_color=COLORS["gold"],
            )
            self._record_lbl.pack(pady=(0, 8))
            self._pulse_record()
        else:
            ctk.CTkLabel(
                content,
                text=" ",
                font=get_font("small"),
            ).pack(pady=(0, 8))

        # ── Stats card ────────────────────────────────────────────────
        stats_card = ctk.CTkFrame(
            content,
            fg_color=COLORS["win_card"],
            corner_radius=CORNER_RADIUS * 2,
            border_width=1,
            border_color="#B388FF",
        )
        stats_card.pack(padx=40, pady=8, fill="x")

        stat_rows = [
            ("🏅 Final Score", str(score)),
            ("🔁 Moves Made", str(moves)),
            ("⏱ Time Taken", self._fmt_time(time_seconds)),
            ("🔥 Best Streak", str(best_streak)),
        ]

        for label, value in stat_rows:
            row = ctk.CTkFrame(stats_card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(
                row,
                text=label,
                font=get_font("body"),
                text_color="#EDE7F6",
                anchor="w",
            ).pack(side="left", expand=True, fill="x")
            ctk.CTkLabel(
                row,
                text=value,
                font=get_font("stat_value_win"),
                text_color="#FFFFFF",
                anchor="e",
            ).pack(side="right")

        # ── Buttons ───────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(pady=(16, 8))

        ctk.CTkButton(
            btn_frame,
            text="▶ Play Again",
            font=get_font("button"),
            width=130,
            height=44,
            corner_radius=CORNER_RADIUS,
            fg_color=COLORS["mint"],
            hover_color=COLORS["mint_hover"],
            text_color="#FFFFFF",
            command=self._play_again,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_frame,
            text="🏆 Leaderboard",
            font=get_font("button"),
            width=150,
            height=44,
            corner_radius=CORNER_RADIUS,
            fg_color=COLORS["gold"],
            hover_color="#C9A227",
            text_color="#1A1A1A",
            command=self._leaderboard,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_frame,
            text="🚪 Logout",
            font=get_font("button"),
            width=110,
            height=44,
            corner_radius=CORNER_RADIUS,
            fg_color="#7E57C2",
            hover_color="#673AB7",
            text_color="#FFFFFF",
            border_width=1,
            border_color="#B388FF",
            command=self._logout,
        ).pack(side="left", padx=6)

        # Window geometry
        self.geometry(f"{CANVAS_W}x{CANVAS_H}")

    # ------------------------------------------------------------------
    # Confetti animation
    # ------------------------------------------------------------------

    def start_confetti(self):
        """Initialise particles and begin the animation loop."""
        try:
            canvas_w = self._canvas.winfo_width() or 480
            canvas_h = self._canvas.winfo_height() or 520
        except tk.TclError:
            return

        self._particles = [
            _Particle(canvas_w, canvas_h) for _ in range(self._PARTICLE_COUNT)
        ]
        self._tick_confetti()

    def stop_confetti(self):
        """Cancel any pending confetti after() call."""
        if self._confetti_after_id is not None:
            try:
                self.after_cancel(self._confetti_after_id)
            except Exception:  # noqa: BLE001
                pass
            self._confetti_after_id = None

    def _tick_confetti(self):
        try:
            canvas = self._canvas
            canvas.delete("confetti")
            for p in self._particles:
                p.update()
                x0, y0 = p.x - p.w / 2, p.y - p.h / 2
                x1, y1 = p.x + p.w / 2, p.y + p.h / 2
                if p.shape == "oval":
                    canvas.create_oval(
                        x0, y0, x1, y1,
                        fill=p.color, outline="", tags="confetti"
                    )
                else:
                    canvas.create_rectangle(
                        x0, y0, x1, y1,
                        fill=p.color, outline="", tags="confetti"
                    )
            interval = int(1000 / self._CONFETTI_FPS)
            self._confetti_after_id = self.after(interval, self._tick_confetti)
        except tk.TclError:
            # Widget destroyed
            pass

    # ------------------------------------------------------------------
    # Record pulse animation
    # ------------------------------------------------------------------

    def _pulse_record(self, bright: bool = True):
        if not self._is_new_record:
            return
        try:
            self._record_lbl.configure(
                text_color=COLORS["gold"] if bright else "#FFFFFF"
            )
            self._record_pulse_id = self.after(
                600, lambda: self._pulse_record(not bright)
            )
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Button actions
    # ------------------------------------------------------------------

    def _play_again(self):
        self._destroy_safe()
        self._on_play_again()

    def _leaderboard(self):
        self._destroy_safe()
        self._on_leaderboard()

    def _logout(self):
        self._destroy_safe()
        self._on_logout()

    def _on_wm_delete(self):
        # Do nothing – force the user to choose an action
        pass

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _destroy_safe(self):
        """Cancel all pending callbacks then destroy."""
        self.stop_confetti()
        if self._record_pulse_id is not None:
            try:
                self.after_cancel(self._record_pulse_id)
            except Exception:  # noqa: BLE001
                pass
            self._record_pulse_id = None
        try:
            self.grab_release()
            self.destroy()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        try:
            s = int(seconds)
            return f"{s // 60}m {s % 60:02d}s"
        except (TypeError, ValueError):
            return "--"

    def _center_on_parent(self, parent):
        self.update_idletasks()
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
        except tk.TclError:
            self.geometry("+200+200")
            return

        w = self.winfo_width() or 480
        h = self.winfo_height() or 520
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
