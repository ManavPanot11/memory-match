"""
test_live_db_flow.py - End-to-end test against the live MySQL server.
Tests:
1. User creation (signup)
2. Case-insensitive login
3. Score recording & leaderboard rank
4. Player statistics aggregation
5. New record detection
6. Password reset flow
"""

import os
import unittest
from dotenv import load_dotenv

load_dotenv()

from database import init_db, DatabaseError
from auth import hash_password, verify_password, validate_username, validate_email, validate_password


class TestLiveDBFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = init_db()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_full_user_and_game_flow(self):
        import time
        ts = int(time.time())
        username = f"player_{ts}"
        display_name = f"Player {ts}"
        email = f"player_{ts}@example.com"
        raw_password = "SecretPassword123!"

        # 1. Validation
        ok, msg = validate_username(username)
        self.assertTrue(ok)
        ok, msg = validate_email(email)
        self.assertTrue(ok)
        ok, msg = validate_password(raw_password, raw_password)
        self.assertTrue(ok)

        user_id = None
        try:
            # 2. Registration / User Creation
            pw_hash = hash_password(raw_password)
            user_id = self.db.create_user(username, display_name, email, pw_hash)
            self.assertIsInstance(user_id, int)
            self.assertGreater(user_id, 0)

            # 3. Duplicate checks
            with self.assertRaises(DatabaseError) as ctx:
                self.db.create_user(username, display_name, "other@example.com", pw_hash)
            self.assertIn("username is already taken", str(ctx.exception).lower())

            with self.assertRaises(DatabaseError) as ctx:
                self.db.create_user(f"other_{ts}", "Other", email, pw_hash)
            self.assertIn("already exists", str(ctx.exception).lower())

            # 4. Login (case-insensitive username lookup)
            user = self.db.get_user_by_username(username.upper())
            self.assertIsNotNone(user)
            self.assertEqual(user["id"], user_id)
            self.assertTrue(verify_password(raw_password, user["password_hash"]))
            self.assertFalse(verify_password("WrongPassword!", user["password_hash"]))

            # 5. Play game / Save score
            self.assertTrue(self.db.is_new_record(user_id, 350))
            self.db.save_score(user_id=user_id, score=350, moves=16, time_seconds=55, best_streak=4)

            # Verify not record if lower score
            self.assertFalse(self.db.is_new_record(user_id, 300))
            self.assertTrue(self.db.is_new_record(user_id, 450))

            # Save second score
            self.db.save_score(user_id=user_id, score=450, moves=14, time_seconds=42, best_streak=6)

            # 6. Leaderboard & Stats
            top_scores = self.db.get_top_scores(limit=10)
            self.assertGreater(len(top_scores), 0)
            # Check that top score is ordered correctly
            for i in range(len(top_scores) - 1):
                self.assertGreaterEqual(top_scores[i]["score"], top_scores[i + 1]["score"])

            stats = self.db.get_player_stats(user_id)
            self.assertEqual(stats["games_played"], 2)
            self.assertEqual(stats["best_score"], 450)
            self.assertEqual(stats["best_streak"], 6)
            self.assertAlmostEqual(stats["avg_score"], 400.0)

            recent = self.db.get_recent_games(user_id, limit=5)
            self.assertEqual(len(recent), 2)
            self.assertEqual(recent[0]["score"], 450)

            # 7. Password reset flow
            new_password = "NewSecretPassword456!"
            ok, msg = validate_password(new_password, new_password)
            self.assertTrue(ok)
            new_hash = hash_password(new_password)
            self.db.update_password(user_id, new_hash)

            # Verify login with new password
            updated_user = self.db.get_user_by_username(username)
            self.assertTrue(verify_password(new_password, updated_user["password_hash"]))
            self.assertFalse(verify_password(raw_password, updated_user["password_hash"]))
        finally:
            if user_id:
                try:
                    with self.db.get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                        conn.commit()
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()

