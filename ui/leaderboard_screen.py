"""
Leaderboard screen for Memory Match game.
"""

import threading
import customtkinter as ctk
from ui.theme import COLORS, get_font, CORNER_RADIUS
from ui.widgets import RoundedButton


# Rank medal helpers
_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def _rank_label(rank: int) -> str:
    return _MEDALS.get(rank, str(rank))


def _fmt_time(seconds: float) -> str:
    """Format seconds as M:SS."""
    try:
        s = int(seconds)
        return f"{s // 60}:{s % 60:02d}"
    except (TypeError, ValueError):
        return "--"


class LeaderboardScreen(ctk.CTkFrame):
    """Leaderboard with top-10 table, personal stats, and recent games."""

    def __init__(self, parent, app, current_user: dict):
        super().__init__(parent, fg_color=COLORS["background"], corner_radius=0)
        self.app = app
        self.current_user = current_user
        self._build_ui()
        self._load_data()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Scrollable main area
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=COLORS["background"], corner_radius=0
        )
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

        content = self._scroll

        # ── Header ────────────────────────────────────────────────────
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(24, 8))

        ctk.CTkLabel(
            header,
            text="🏆 Leaderboard",
            font=get_font("title"),
            text_color=COLORS["primary"],
        ).pack(side="left")

        RoundedButton(
            header,
            text="← Back",
            command=lambda: self.app.show_game(self.current_user),
            width=110,
            height=36,
            fg_color=COLORS["coral"],
            hover_color=COLORS["coral_hover"],
            font=get_font("small_button"),
        ).pack(side="right")

        # ── Spinner / status ──────────────────────────────────────────
        self.status_lbl = ctk.CTkLabel(
            content,
            text="⏳ Loading…",
            font=get_font("body"),
            text_color=COLORS["text_muted"],
        )
        self.status_lbl.pack(pady=20)

        # ── Containers that will be populated after data loads ────────
        self.top10_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.top10_frame.pack(fill="x", padx=30, pady=(0, 16))

        self.stats_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=30, pady=(0, 16))

        self.recent_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.recent_frame.pack(fill="x", padx=30, pady=(0, 24))

    # ------------------------------------------------------------------
    # Data loading (background thread)
    # ------------------------------------------------------------------

    def _load_data(self):
        def _worker():
            try:
                if not self.winfo_exists():
                    return
                if self.app.db is None:
                    try:
                        if self.winfo_exists():
                            self.after(
                                0,
                                lambda: self.status_lbl.configure(
                                    text="⚠ Database is not connected.",
                                    text_color=COLORS["error"],
                                ),
                            )
                    except Exception:
                        pass
                    return

                top10 = self.app.db.get_top_scores(limit=10)
                stats = self.app.db.get_player_stats(self.current_user["id"])
                recent = self.app.db.get_recent_games(
                    self.current_user["id"], limit=5
                )
                try:
                    if self.winfo_exists():
                        self.after(0, lambda: self._populate(top10, stats, recent))
                except Exception:
                    pass
            except Exception as exc:  # noqa: BLE001
                try:
                    if self.winfo_exists():
                        self.after(
                            0,
                            lambda: self.status_lbl.configure(
                                text=f"⚠ Failed to load data: {exc}",
                                text_color=COLORS["error"],
                            ),
                        )
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Populating UI with data
    # ------------------------------------------------------------------

    def _populate(self, top10, stats, recent):
        self.status_lbl.pack_forget()
        self._build_top10(top10)
        self._build_stats(stats)
        self._build_recent(recent)

    def _build_top10(self, rows):
        """Render the top-10 table."""
        # Clear previous
        for w in self.top10_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self.top10_frame,
            text="Top 10 Players",
            font=get_font("section"),
            text_color=COLORS["text"],
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        table = ctk.CTkFrame(
            self.top10_frame,
            fg_color=COLORS["card"],
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=COLORS["border"],
        )
        table.pack(fill="x")

        # Header row
        self._table_row(
            table,
            ["Rank", "Player", "Score", "Moves", "Time"],
            is_header=True,
            row_idx=0,
        )

        for idx, row in enumerate(rows, start=1):
            uid = row.get("user_id") or row.get("id")
            is_me = uid == self.current_user["id"]
            self._table_row(
                table,
                [
                    _rank_label(idx),
                    row.get("username", "—"),
                    str(row.get("score", 0)),
                    str(row.get("moves", "—")),
                    _fmt_time(row.get("time_seconds", 0)),
                ],
                is_header=False,
                row_idx=idx,
                highlight=is_me,
            )

        if not rows:
            ctk.CTkLabel(
                table,
                text="No scores yet. Be the first!",
                font=get_font("body"),
                text_color=COLORS["text_muted"],
            ).pack(pady=20)

    def _table_row(self, parent, values, *, is_header, row_idx, highlight=False):
        col_widths = [60, 160, 80, 80, 80]
        col_anchors = ["center", "w", "center", "center", "center"]

        if is_header:
            bg = COLORS["table_header"]
        elif highlight:
            bg = COLORS["table_highlight"]
        elif row_idx % 2 == 0:
            bg = COLORS["table_even"]
        else:
            bg = COLORS["table_odd"]

        row_frame = ctk.CTkFrame(parent, fg_color=bg, corner_radius=0)
        row_frame.pack(fill="x")

        for val, w, anchor in zip(values, col_widths, col_anchors):
            ctk.CTkLabel(
                row_frame,
                text=str(val),
                font=get_font("table_header" if is_header else "table"),
                text_color=COLORS["text"] if not is_header else COLORS["text_muted"],
                width=w,
                anchor=anchor,
            ).pack(side="left", padx=4, pady=6)

    def _build_stats(self, stats):
        """Render the 'Your Stats' section."""
        for w in self.stats_frame.winfo_children():
            w.destroy()

        if stats is None:
            return

        ctk.CTkLabel(
            self.stats_frame,
            text="Your Stats",
            font=get_font("section"),
            text_color=COLORS["text"],
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        card = ctk.CTkFrame(
            self.stats_frame,
            fg_color=COLORS["card"],
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.pack(fill="x")

        avg_score = stats.get("avg_score")
        avg_display = f"{float(avg_score):.1f}" if avg_score is not None else "0.0"
        best_score = stats.get("best_score")
        best_display = str(best_score) if best_score is not None else "0"
        best_streak = stats.get("best_streak")
        streak_display = str(best_streak) if best_streak is not None else "0"

        stat_items = [
            ("🎮 Games Played", str(stats.get("games_played") or 0)),
            ("⭐ Best Score", best_display),
            ("📊 Avg Score", avg_display),
            ("🔥 Best Streak", streak_display),
        ]

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", pady=12, padx=12)

        for label, value in stat_items:
            stat_card = ctk.CTkFrame(
                row,
                fg_color=COLORS["background"],
                corner_radius=CORNER_RADIUS,
                border_width=1,
                border_color=COLORS["border"],
            )
            stat_card.pack(side="left", expand=True, fill="both", padx=6)

            ctk.CTkLabel(
                stat_card,
                text=str(value),
                font=get_font("stat_value"),
                text_color=COLORS["primary"],
            ).pack(pady=(12, 2))

            ctk.CTkLabel(
                stat_card,
                text=label,
                font=get_font("small"),
                text_color=COLORS["text_muted"],
            ).pack(pady=(0, 12))

    def _build_recent(self, rows):
        """Render the 'Recent Games' mini-table."""
        for w in self.recent_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self.recent_frame,
            text="Recent Games",
            font=get_font("section"),
            text_color=COLORS["text"],
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        table = ctk.CTkFrame(
            self.recent_frame,
            fg_color=COLORS["card"],
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=COLORS["border"],
        )
        table.pack(fill="x")

        self._recent_row(table, ["#", "Score", "Moves", "Time", "Date"], is_header=True)

        for idx, row in enumerate(rows, start=1):
            self._recent_row(
                table,
                [
                    str(idx),
                    str(row.get("score", 0)),
                    str(row.get("moves", "—")),
                    _fmt_time(row.get("time_seconds", 0)),
                    str(row.get("played_at", "—"))[:10],
                ],
                is_header=False,
                row_idx=idx,
            )

        if not rows:
            ctk.CTkLabel(
                table,
                text="No games played yet.",
                font=get_font("body"),
                text_color=COLORS["text_muted"],
            ).pack(pady=14)

    def _recent_row(self, parent, values, *, is_header, row_idx=0):
        col_widths = [40, 80, 80, 80, 120]
        bg = COLORS["table_header"] if is_header else (
            COLORS["table_even"] if row_idx % 2 == 0 else COLORS["table_odd"]
        )
        row_frame = ctk.CTkFrame(parent, fg_color=bg, corner_radius=0)
        row_frame.pack(fill="x")
        for val, w in zip(values, col_widths):
            ctk.CTkLabel(
                row_frame,
                text=str(val),
                font=get_font("table_header" if is_header else "table"),
                text_color=COLORS["text_muted"] if is_header else COLORS["text"],
                width=w,
                anchor="center",
            ).pack(side="left", padx=4, pady=5)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_show(self):
        """Reload data every time the screen is shown."""
        for w in self.top10_frame.winfo_children():
            w.destroy()
        for w in self.stats_frame.winfo_children():
            w.destroy()
        for w in self.recent_frame.winfo_children():
            w.destroy()

        self.status_lbl.configure(text="⏳ Loading…", text_color=COLORS["text_muted"])
        self.status_lbl.pack(pady=20)
        self._load_data()
