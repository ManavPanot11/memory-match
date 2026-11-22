"""
test_auth.py - Unit tests for auth.py
"""

import unittest
from auth import (
    hash_password,
    verify_password,
    validate_username,
    validate_email,
    validate_password,
)


class TestAuth(unittest.TestCase):
    def test_password_hashing_and_verification(self):
        pwd = "SecretPassword123!"
        hashed = hash_password(pwd)
        self.assertIn("$", hashed)
        self.assertTrue(verify_password(pwd, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))
        self.assertFalse(verify_password("", hashed))
        self.assertFalse(verify_password(pwd, "invalid$format$extra"))
        self.assertFalse(verify_password(pwd, "corrupted_hash"))

    def test_validate_username(self):
        # Valid usernames
        ok, msg = validate_username("john_doe")
        self.assertTrue(ok)
        self.assertEqual(msg, "")

        ok, msg = validate_username("  Alice123  ")
        self.assertTrue(ok)

        # Invalid: too short
        ok, msg = validate_username("ab")
        self.assertFalse(ok)
        self.assertIn("3-20 characters", msg)

        # Invalid: too long (>20)
        ok, msg = validate_username("a" * 21)
        self.assertFalse(ok)
        self.assertIn("3-20 characters", msg)

        # Invalid: special chars
        ok, msg = validate_username("john-doe!")
        self.assertFalse(ok)

        # Invalid: empty
        ok, msg = validate_username("   ")
        self.assertFalse(ok)

    def test_validate_email(self):
        # Valid
        ok, msg = validate_email("user@example.com")
        self.assertTrue(ok)
        self.assertEqual(msg, "")

        ok, msg = validate_email("test.user+tag@sub.domain.org")
        self.assertTrue(ok)

        # Invalid emails
        ok, msg = validate_email("plainaddress")
        self.assertFalse(ok)

        ok, msg = validate_email("user@")
        self.assertFalse(ok)

        ok, msg = validate_email("@domain.com")
        self.assertFalse(ok)

        ok, msg = validate_email("   ")
        self.assertFalse(ok)

    def test_validate_password(self):
        # Valid
        ok, msg = validate_password("Pass123", "Pass123")
        self.assertTrue(ok)
        self.assertEqual(msg, "")

        # Mismatch
        ok, msg = validate_password("Pass123", "Pass456")
        self.assertFalse(ok)
        self.assertIn("do not match", msg)

        # Too short (<6 chars)
        ok, msg = validate_password("12345", "12345")
        self.assertFalse(ok)
        self.assertIn("at least 6", msg)

        # Empty
        ok, msg = validate_password("", "")
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
