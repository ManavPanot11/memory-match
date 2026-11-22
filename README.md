# 🃏 Memory Match

A polished, vibrant desktop tile-matching / memory card game built with Python, CustomTkinter, and MySQL.

Created by **[Manav Panot](https://github.com/ManavPanot11)**.

🎮 **[Play Live Web Version on Vercel](https://memory-match-web-one.vercel.app)**  
💾 **[Download Windows Executable (.exe)](https://github.com/ManavPanot11/memory-match/releases/tag/v1.0.0)**

---

## Features

- **4 × 6 Grid** — 24 cards, 12 unique image pairs randomly selected and shuffled every game
- **User Accounts & Auth** — Sign up, log in, forgot-password reset (offline with PBKDF2-HMAC-SHA256)
- **Guest / Quick Play Mode** — Play immediately with 1 click without requiring a running database
- **Leaderboard & Stats** — Top 10 global scores, personal statistics, and recent match history
- **Studio-Grade Animations** — Snappy 84ms 3D flips, tactile hover glow, bounce, shake, and win confetti
- **Scoring & Streak Combos** — Points for matches, dynamic combo bonuses (`🔥 COMBO!`), and time bonuses
- **Pre-Loaded Assets** — Bundled with 30 high-definition emoji tiles, sound effects, and custom Fredoka font
- **Light Theme** — Vibrant candy-color aesthetic (cream, coral, mint, sky blue, sunny yellow, pink)
- **Zero-Crash Design** — Comprehensive exception handling with friendly dialogs for all edge cases

---

## Quick Start

### 1 · Install Dependencies

Ensure Python 3.10+ is installed:

```bash
pip install -r requirements.txt
```

### 2 · Run the Game

```bash
python main.py
```
*(On Windows, you can also double-click `run.bat` or run `python run.py`)*

> **Tip**: Click **"🎮 Play as Guest"** to start playing immediately!  
> To enable user accounts and persistent leaderboards, configure MySQL below.

---

## (Optional) MySQL Setup for User Accounts & Leaderboards

1. Start your local MySQL Server.
2. Ensure you have a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

3. Update `.env` with your credentials:

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=memory_match
```

> **Note**: The application automatically creates the `memory_match` database and all required tables on first launch.

---

## Project Structure

```
memory_match/
├── main.py                  # Entry point & app bootstrap
├── run.py                   # Convenience launcher script
├── run.bat                  # One-click Windows batch launcher
├── database.py              # MySQL connection pool & parameterized queries
├── auth.py                  # Password hashing (PBKDF2) & input validation
├── game.py                  # Pure game logic, cards & scoring (no GUI)
├── .env.example             # Template for MySQL credentials
├── requirements.txt         # Project dependencies
├── README.md                # Documentation & instructions
├── ui/
│   ├── theme.py             # Colors, Fredoka font loader & styles
│   ├── widgets.py           # Reusable widgets (RoundedButton, PillBadge, CardWidget)
│   ├── login_screen.py      # Login with Guest Play & navigation
│   ├── signup_screen.py     # Account registration
│   ├── forgot_password_screen.py # Password reset flow
│   ├── game_screen.py       # Main 4x6 game board & live HUD
│   ├── leaderboard_screen.py# Top 10 table & player statistics
│   └── win_dialog.py        # Victory celebration modal with confetti
├── images/                  # 30 curated high-definition card tiles
├── fonts/                   # Fredoka display font (.ttf)
└── sounds/                  # Audio effects (flip.wav, match.wav, win.wav)
```

---

## Scoring System

| Event | Points |
|-------|--------|
| Matched pair | +100 |
| 2nd consecutive match (combo ×2) | +50 bonus |
| 3rd consecutive match (combo ×3) | +100 bonus |
| *N*th consecutive match | +50 × (N−1) bonus |
| Mismatch flip | −10 |
| Time bonus (on victory) | max(0, 300 − seconds) |
| Score floor | 0 (never negative) |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Missing Dependencies` dialog | Run `pip install -r requirements.txt` |
| `Cannot reach database server` | Ensure MySQL is running and `.env` credentials match, or click **"Play as Guest"** |
| `Database login failed` | Check `DB_USER` and `DB_PASSWORD` in your `.env` file |

---

## License

MIT License — free for academic and personal use.
