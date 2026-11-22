"""
database.py
===========
MySQL database layer for the Memory Match Tiles game.

Uses mysql-connector-python with a connection pool of size 5.
All queries are parameterized (%s placeholders) – no string formatting in SQL.
On startup the module creates the database and tables if they do not exist.

Usage
-----
    from database import init_db, DatabaseError

    db = init_db()                          # reads env vars
    user_id = db.create_user(...)
    db.save_score(user_id, ...)
"""

from __future__ import annotations

import contextlib
import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

import mysql.connector
from mysql.connector import Error as MySQLError
from mysql.connector.pooling import MySQLConnectionPool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class DatabaseError(Exception):
    """Raised for all database-layer errors with a user-friendly message."""


# ---------------------------------------------------------------------------
# DDL statements
# ---------------------------------------------------------------------------

_DDL_CREATE_DB = "CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

_DDL_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id            INT          NOT NULL AUTO_INCREMENT,
    username      VARCHAR(30)  NOT NULL COLLATE utf8mb4_unicode_ci,
    display_name  VARCHAR(30)  NOT NULL,
    email         VARCHAR(120) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_username (username),
    UNIQUE KEY uq_email    (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

_DDL_SCORES = """
CREATE TABLE IF NOT EXISTS scores (
    id           INT  NOT NULL AUTO_INCREMENT,
    user_id      INT  NOT NULL,
    score        INT  NOT NULL,
    moves        INT  NOT NULL,
    time_seconds INT  NOT NULL,
    best_streak  INT  NOT NULL,
    played_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_score   (score DESC),
    INDEX idx_user_id (user_id),
    CONSTRAINT fk_scores_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------

class DatabaseManager:
    """
    Manages a MySQL connection pool and exposes all game-related queries.

    Parameters
    ----------
    host : str
        MySQL server host name or IP address.
    port : int
        MySQL server port (default 3306).
    user : str
        MySQL user name.
    password : str
        MySQL password.
    database : str
        Schema / database name to use.
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database

        # Step 1 – ensure the schema exists (uses a temporary plain connection
        # because the pool requires the DB to exist before connecting).
        self._ensure_schema()

        # Step 2 – create the connection pool targeting the now-existing DB.
        self._pool = MySQLConnectionPool(
            pool_name="memmatch_pool",
            pool_size=5,
            pool_reset_session=True,
            host=self._host,
            port=self._port,
            user=self._user,
            password=self._password,
            database=self._database,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            use_unicode=True,
            autocommit=False,
        )

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------

    def _ensure_schema(self) -> None:
        """
        Create the database and both tables if they do not already exist.

        Called once during ``__init__`` before the pool is created.
        """
        # Connect without specifying a database so we can CREATE DATABASE.
        try:
            conn = mysql.connector.connect(
                host=self._host,
                port=self._port,
                user=self._user,
                password=self._password,
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci",
                use_unicode=True,
                autocommit=True,
            )
        except MySQLError as exc:
            self._translate_error(exc)

        try:
            cursor = conn.cursor()
            try:
                # CREATE DATABASE is not parameterisable; the name comes from
                # trusted config, never from user input, so this is safe.
                cursor.execute(_DDL_CREATE_DB.format(db=self._database))
                cursor.execute(f"USE `{self._database}`;")
                cursor.execute(_DDL_USERS)
                cursor.execute(_DDL_SCORES)
                conn.commit()
            finally:
                cursor.close()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Connection context manager
    # ------------------------------------------------------------------

    @contextlib.contextmanager
    def get_connection(self):
        """
        Context manager that yields a pooled connection and returns it on exit.

        Example
        -------
            with db.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                ...
        """
        conn = None
        try:
            conn = self._pool.get_connection()
            yield conn
        except MySQLError as exc:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            self._translate_error(exc)
        finally:
            if conn and conn.is_connected():
                conn.close()  # returns to pool

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute(
        self,
        query: str,
        params: tuple = (),
        *,
        fetch: str = "none",   # "none" | "one" | "all"
        dictionary: bool = True,
        retry: bool = True,
    ) -> Any:
        """
        Execute *query* with *params* using a pooled connection.

        Parameters
        ----------
        query : str
            Parameterized SQL statement.
        params : tuple
            Positional %s parameters.
        fetch : str
            Whether to fetch ``"one"``, ``"all"``, or ``"none"`` rows.
        dictionary : bool
            Return rows as dicts when *True*.
        retry : bool
            Retry once with a fresh connection on lost-connection errors (2006/2013).

        Returns
        -------
        Any
            ``None`` for DML, a single ``dict`` for ``fetch="one"``,
            or a ``list[dict]`` for ``fetch="all"``.
        """
        conn = None
        try:
            conn = self._pool.get_connection()
            cursor = conn.cursor(dictionary=dictionary)
            try:
                cursor.execute(query, params)
                if fetch == "one":
                    result = cursor.fetchone()
                elif fetch == "all":
                    result = cursor.fetchall()
                else:
                    result = None
                conn.commit()
                return result
            except MySQLError as exc:
                conn.rollback()
                # Lost connection – retry once.
                if exc.errno in (2006, 2013) and retry:
                    logger.warning("Lost connection to MySQL – retrying once.")
                    cursor.close()
                    conn.close()
                    conn = None
                    return self._execute(
                        query, params, fetch=fetch,
                        dictionary=dictionary, retry=False,
                    )
                self._translate_error(exc)
            finally:
                cursor.close()
        except MySQLError as exc:
            self._translate_error(exc)
        finally:
            if conn and conn.is_connected():
                conn.close()

    @staticmethod
    def _translate_error(exc: MySQLError) -> None:
        """
        Convert a ``mysql.connector.Error`` into a ``DatabaseError`` with a
        user-friendly message, then raise it.
        """
        errno = exc.errno
        msg = str(exc)

        if errno == 2003:
            raise DatabaseError(
                "Cannot reach the database server. Please make sure MySQL is running."
            ) from exc
        if errno == 1045:
            raise DatabaseError(
                "Database login failed. Check your .env credentials."
            ) from exc
        if errno == 1062:
            # Distinguish which unique constraint was violated.
            if "uq_username" in msg or "username" in msg.lower():
                raise DatabaseError(
                    "That username is already taken. Please choose another."
                ) from exc
            if "uq_email" in msg or "email" in msg.lower():
                raise DatabaseError(
                    "An account with that email address already exists."
                ) from exc
            raise DatabaseError("A duplicate record already exists.") from exc
        if errno in (2006, 2013):
            raise DatabaseError(
                "Lost connection to the database server. Please try again."
            ) from exc

        # Generic fallback
        raise DatabaseError(f"Database error ({errno}): {msg}") from exc

    # ------------------------------------------------------------------
    # User queries
    # ------------------------------------------------------------------

    def create_user(
        self,
        username: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        password_hash: Optional[str] = None,
    ) -> int:
        """
        Insert a new user row and return its auto-generated ``id``.
        Supports both (username, display_name, email, password_hash)
        and (username, email, password_hash).
        """
        if password_hash is None:
            # Called with (username, email, password_hash)
            password_hash = email
            email = display_name
            display_name = username

        if not display_name:
            display_name = username

        email_str = (email or "").lower()

        sql = """
            INSERT INTO users (username, display_name, email, password_hash)
            VALUES (%s, %s, %s, %s)
        """
        conn = None
        try:
            conn = self._pool.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(sql, (username, display_name, email_str, password_hash))
                conn.commit()
                return cursor.lastrowid
            except MySQLError as exc:
                conn.rollback()
                self._translate_error(exc)
            finally:
                cursor.close()
        except MySQLError as exc:
            self._translate_error(exc)
        finally:
            if conn and conn.is_connected():
                conn.close()

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        Look up a user by their username.

        Returns
        -------
        dict or None
            Row dict with keys ``id, username, display_name, email,
            password_hash, created_at``, or ``None`` if not found.
        """
        sql = "SELECT * FROM users WHERE username = %s LIMIT 1;"
        return self._execute(sql, (username,), fetch="one")

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Look up a user by their e-mail address (case-insensitive).

        Returns
        -------
        dict or None
            Row dict or ``None``.
        """
        sql = "SELECT * FROM users WHERE email = %s LIMIT 1;"
        return self._execute(sql, (email.lower(),), fetch="one")

    def update_password(self, user_id: int, new_hash: str) -> None:
        """
        Replace the stored password hash for *user_id*.

        Parameters
        ----------
        user_id : int
            Primary key of the user whose password is being changed.
        new_hash : str
            New ``salt$hash`` string.
        """
        sql = "UPDATE users SET password_hash = %s WHERE id = %s;"
        self._execute(sql, (new_hash, user_id))

    # ------------------------------------------------------------------
    # Score queries
    # ------------------------------------------------------------------

    def save_score(
        self,
        user_id: int,
        score: int,
        moves: int,
        time_seconds: int,
        best_streak: int,
    ) -> None:
        """
        Persist a completed game's result.

        Parameters
        ----------
        user_id : int
            The authenticated player's ``id``.
        score : int
            Final numeric score.
        moves : int
            Total card flips / move count.
        time_seconds : int
            Wall-clock duration of the game in seconds.
        best_streak : int
            Longest consecutive-match streak achieved.
        """
        sql = """
            INSERT INTO scores (user_id, score, moves, time_seconds, best_streak)
            VALUES (%s, %s, %s, %s, %s);
        """
        self._execute(sql, (user_id, score, moves, time_seconds, best_streak))

    def get_top_scores(self, limit: int = 10) -> List[Dict]:
        """
        Return the global leaderboard.

        Rows are ordered by ``score DESC``, then ``time_seconds ASC`` as a
        tie-breaker (faster completion is ranked higher).

        Parameters
        ----------
        limit : int
            Maximum number of rows to return (default 10).

        Returns
        -------
        list[dict]
            Each dict contains ``score_id, user_id, username, display_name,
            score, moves, time_seconds, best_streak, played_at``.
        """
        sql = """
            SELECT
                s.id           AS score_id,
                s.user_id,
                u.username,
                u.display_name,
                s.score,
                s.moves,
                s.time_seconds,
                s.best_streak,
                s.played_at
            FROM scores s
            JOIN users u ON u.id = s.user_id
            ORDER BY s.score DESC, s.time_seconds ASC
            LIMIT %s;
        """
        return self._execute(sql, (limit,), fetch="all") or []

    def get_personal_best(self, user_id: int) -> Optional[int]:
        """
        Return the highest score the player has ever achieved.

        Parameters
        ----------
        user_id : int
            Player's primary key.

        Returns
        -------
        int or None
            The top score, or ``None`` if the player has no recorded games.
        """
        sql = "SELECT MAX(score) AS best FROM scores WHERE user_id = %s;"
        row = self._execute(sql, (user_id,), fetch="one")
        return row["best"] if row else None

    def get_player_stats(self, user_id: int) -> Dict:
        """
        Aggregate statistics for a single player.

        Parameters
        ----------
        user_id : int
            Player's primary key.

        Returns
        -------
        dict
            Keys: ``games_played``, ``avg_score``, ``best_score``, ``best_streak``.
        """
        sql = """
            SELECT
                COUNT(*)        AS games_played,
                AVG(score)      AS avg_score,
                MAX(score)      AS best_score,
                MAX(best_streak) AS best_streak
            FROM scores
            WHERE user_id = %s;
        """
        row = self._execute(sql, (user_id,), fetch="one")
        if not row or row["games_played"] == 0:
            return {
                "games_played": 0,
                "avg_score": 0.0,
                "best_score": 0,
                "best_streak": 0,
            }
        return {
            "games_played": row["games_played"],
            "avg_score": float(row["avg_score"] or 0),
            "best_score": row["best_score"] or 0,
            "best_streak": row["best_streak"] or 0,
        }

    # Alias for backward/UI compatibility
    get_user_stats = get_player_stats

    def get_recent_games(self, user_id: int, limit: int = 5) -> List[Dict]:
        """
        Return the most recently played games for *user_id*.

        Parameters
        ----------
        user_id : int
            Player's primary key.
        limit : int
            Maximum rows to return (default 5).

        Returns
        -------
        list[dict]
            Ordered newest-first; each dict has ``id, score, moves,
            time_seconds, best_streak, played_at``.
        """
        sql = """
            SELECT id, score, moves, time_seconds, best_streak, played_at
            FROM scores
            WHERE user_id = %s
            ORDER BY played_at DESC, id DESC
            LIMIT %s;
        """
        return self._execute(sql, (user_id, limit), fetch="all") or []

    def is_new_record(self, user_id: int, score: int) -> bool:
        """
        Return ``True`` if *score* beats the player's current personal best.

        Parameters
        ----------
        user_id : int
            Player's primary key.
        score : int
            The score to compare.

        Returns
        -------
        bool
            ``True`` when *score* is strictly greater than all previously
            stored scores for this user, or when the user has no prior games.
        """
        personal_best = self.get_personal_best(user_id)
        if personal_best is None:
            return True
        return score > personal_best

    def close(self) -> None:
        """Close the database manager and release pooled resources."""
        logger.info("Closing DatabaseManager resources.")


# ---------------------------------------------------------------------------
# Module-level factory
# ---------------------------------------------------------------------------

def init_db() -> DatabaseManager:
    """
    Read connection parameters from environment variables and return a
    configured :class:`DatabaseManager` instance.

    Environment Variables
    ---------------------
    DB_HOST     MySQL host (default ``localhost``).
    DB_PORT     MySQL port as an integer (default ``3306``).
    DB_USER     MySQL user name (required).
    DB_PASSWORD MySQL password (required).
    DB_NAME     Database / schema name (default ``memory_match``).

    Returns
    -------
    DatabaseManager

    Raises
    ------
    DatabaseError
        If a required variable is missing or the connection cannot be made.
    """
    host = os.getenv("DB_HOST", "localhost")
    port_str = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "root") or "root"
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "memory_match")

    if not user:
        raise DatabaseError(
            "DB_USER environment variable is not set. "
            "Please add it to your .env file."
        )

    try:
        port = int(port_str)
    except ValueError:
        raise DatabaseError(
            f"DB_PORT must be an integer, got: {port_str!r}"
        )

    try:
        return DatabaseManager(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
        )
    except DatabaseError:
        raise
    except Exception as exc:
        raise DatabaseError(
            f"Failed to initialise the database: {exc}"
        ) from exc
