"""
test_database.py - Unit tests for database.py (with mocked MySQL connections)
"""

import unittest
from unittest.mock import MagicMock, patch
from mysql.connector import Error as MySQLError

from database import DatabaseManager, DatabaseError


class TestDatabaseManager(unittest.TestCase):
    @patch("database.mysql.connector.connect")
    @patch("database.MySQLConnectionPool")
    def setUp(self, mock_pool_cls, mock_connect):
        self.mock_connect = mock_connect
        self.mock_pool_cls = mock_pool_cls

        # Mock plain connection used in _ensure_schema
        self.mock_init_conn = MagicMock()
        self.mock_init_cursor = MagicMock()
        self.mock_init_conn.cursor.return_value = self.mock_init_cursor
        mock_connect.return_value = self.mock_init_conn

        # Mock pool
        self.mock_pool = MagicMock()
        self.mock_pooled_conn = MagicMock()
        self.mock_pooled_cursor = MagicMock()
        self.mock_pooled_conn.cursor.return_value = self.mock_pooled_cursor
        self.mock_pooled_conn.is_connected.return_value = True
        self.mock_pool.get_connection.return_value = self.mock_pooled_conn
        mock_pool_cls.return_value = self.mock_pool

        self.db = DatabaseManager(
            host="localhost",
            port=3306,
            user="testuser",
            password="testpassword",
            database="testdb",
        )

    def test_schema_creation_on_init(self):
        # Verify CREATE DATABASE and tables were executed
        self.assertTrue(self.mock_init_cursor.execute.called)
        calls = [c[0][0] for c in self.mock_init_cursor.execute.call_args_list]
        self.assertTrue(any("CREATE DATABASE" in q for q in calls))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS users" in q for q in calls))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS scores" in q for q in calls))

    def test_create_user(self):
        self.mock_pooled_cursor.lastrowid = 42
        user_id = self.db.create_user("Alice", "Alice", "Alice@Example.com", "salt$hash")
        self.assertEqual(user_id, 42)
        # Check lowercase email
        call_args = self.mock_pooled_cursor.execute.call_args[0]
        self.assertIn("INSERT INTO users", call_args[0])
        self.assertEqual(call_args[1][2], "alice@example.com")
        self.mock_pooled_conn.commit.assert_called()
        self.mock_pooled_conn.close.assert_called()

    def test_get_user_by_username(self):
        self.mock_pooled_cursor.fetchone.return_value = {
            "id": 1,
            "username": "alice",
            "display_name": "Alice",
            "email": "alice@example.com",
            "password_hash": "salt$hash",
        }
        user = self.db.get_user_by_username("alice")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "alice")
        self.mock_pooled_conn.close.assert_called()

    def test_save_score(self):
        self.db.save_score(user_id=1, score=250, moves=15, time_seconds=85, best_streak=3)
        call_args = self.mock_pooled_cursor.execute.call_args[0]
        self.assertIn("INSERT INTO scores", call_args[0])
        self.assertEqual(call_args[1], (1, 250, 15, 85, 3))
        self.mock_pooled_conn.commit.assert_called()
        self.mock_pooled_conn.close.assert_called()

    def test_error_translation_server_down(self):
        err = MySQLError(errno=2003, msg="Can't connect to MySQL server")
        with self.assertRaises(DatabaseError) as ctx:
            DatabaseManager._translate_error(err)
        self.assertIn("Cannot reach the database server", str(ctx.exception))

    def test_error_translation_login_denied(self):
        err = MySQLError(errno=1045, msg="Access denied for user")
        with self.assertRaises(DatabaseError) as ctx:
            DatabaseManager._translate_error(err)
        self.assertIn("Database login failed", str(ctx.exception))

    def test_error_translation_duplicate_username(self):
        err = MySQLError(errno=1062, msg="Duplicate entry 'alice' for key 'uq_username'")
        with self.assertRaises(DatabaseError) as ctx:
            DatabaseManager._translate_error(err)
        self.assertIn("username is already taken", str(ctx.exception))

    def test_error_translation_duplicate_email(self):
        err = MySQLError(errno=1062, msg="Duplicate entry 'a@b.com' for key 'uq_email'")
        with self.assertRaises(DatabaseError) as ctx:
            DatabaseManager._translate_error(err)
        self.assertIn("email address already exists", str(ctx.exception))

    def test_is_new_record_no_prior_scores(self):
        self.mock_pooled_cursor.fetchone.return_value = None
        self.assertTrue(self.db.is_new_record(user_id=1, score=100))

    def test_is_new_record_beats_best(self):
        self.mock_pooled_cursor.fetchone.return_value = {"best": 150}
        self.assertTrue(self.db.is_new_record(user_id=1, score=200))
        self.assertFalse(self.db.is_new_record(user_id=1, score=150))
        self.assertFalse(self.db.is_new_record(user_id=1, score=120))


if __name__ == "__main__":
    unittest.main()

