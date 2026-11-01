import hashlib
import unittest
from unittest import mock

from booking import auth
from booking.auth import StaffDirectory, hash_password, needs_rehash, verify_password

FAST_N = 2 ** 10  # keeps tests quick; production parameters are checked in test_default_parameters


class AuthTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(auth, "SCRYPT_N", FAST_N)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_correct_password_verifies(self):
        stored = hash_password("correct horse")
        self.assertTrue(verify_password("correct horse", stored))

    def test_wrong_password_is_rejected(self):
        stored = hash_password("correct horse")
        self.assertFalse(verify_password("wrong", stored))

    def test_directory_authenticates_known_staff_only(self):
        staff = StaffDirectory()
        staff.add("reception", "s3cret-pass")
        self.assertTrue(staff.authenticate("reception", "s3cret-pass"))
        self.assertFalse(staff.authenticate("reception", "nope"))
        self.assertFalse(staff.authenticate("unknown", "s3cret-pass"))

    def test_same_password_gets_different_salts(self):
        self.assertNotEqual(hash_password("same"), hash_password("same"))

    def test_tampered_key_is_rejected(self):
        stored = hash_password("correct horse")
        tampered = stored[:-1] + ("0" if stored[-1] != "0" else "1")
        self.assertFalse(verify_password("correct horse", tampered))

    def test_malformed_hashes_fail_closed(self):
        for bad in ("", "plain-text-password", "scrypt$abc$8$1$00$00", "md5$1$2$3$4$5",
                    "scrypt$4194304$8$1$00ff$00ff"):
            with self.subTest(stored=bad):
                self.assertFalse(verify_password("anything", bad))
                self.assertTrue(needs_rehash(bad))

    def test_legacy_sha256_hash_verifies_and_is_upgraded_on_sign_in(self):
        staff = StaffDirectory()
        staff._hashes["nurse"] = hashlib.sha256(b"old-pass").hexdigest()
        self.assertFalse(staff.authenticate("nurse", "wrong"))
        self.assertEqual(len(staff._hashes["nurse"]), 64, "a failed sign-in must not upgrade the hash")
        self.assertTrue(staff.authenticate("nurse", "old-pass"))
        self.assertTrue(staff._hashes["nurse"].startswith("scrypt$"))
        self.assertTrue(staff.authenticate("nurse", "old-pass"))


class DefaultParametersTest(unittest.TestCase):
    def test_default_parameters_meet_the_documented_minimum(self):
        stored = hash_password("correct horse")
        self.assertTrue(stored.startswith("scrypt$131072$8$1$"))
        self.assertTrue(verify_password("correct horse", stored))
        self.assertFalse(needs_rehash(stored))


if __name__ == "__main__":
    unittest.main()
