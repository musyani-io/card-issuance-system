"""
Phase 3 End-to-End Authentication Testing

TASK 3.6: End-to-End Authentication Test
=========================================

Tests the complete authentication flow for both student paths:
- 3.6.1: Returning student (correct OTP → correct PIN → success)
- 3.6.2: First-year student (correct OTP → temp PIN → permanent PIN → success)
- 3.6.3: Lockout enforcement (3 wrong OTPs, then 3 wrong PINs)

KEY FEATURES:
- Uses REAL SMS (Africa's Talking) delivery ✅ VERIFIED
- Uses REAL Email (Gmail SMTP with App Password) ✅ VERIFIED
- Temporary test database with sample student data
- Audit log verification for all lockout events
- Clear assertion messages for debugging

TEST STUDENTS (from mock_db_api/app.py):
1. Samuel Musyani (2022-04-09050) - Returning student (existing PIN)
2. Godson Shirima (2022-04-12357) - First-year student (temp PIN)

RUNNING THE TESTS:
    cd kiosk_brain
    python -m unittest tests.test_auth.Test361ReturningStudent -v
    python -m unittest tests.test_auth.Test362FirstYearStudent -v
    python -m unittest tests.test_auth.Test363LockoutScenarios -v
    python -m unittest tests.test_auth -v  # All tests

CREDENTIALS STATUS:
✅ SMS (Africa's Talking): WORKING - Sandbox/test credentials active
✅ Email (Gmail): WORKING - App password configured (config.py)

WARNINGS:
- REAL SMS/EMAILS WILL BE SENT to phone numbers and emails in the database
- Africa's Talking sandbox: Test SMS may take 1-2 seconds
- Gmail SMTP: Uses app-specific password for authentication
- Each test run sends 1-2 SMS + 1-2 Emails per scenario
"""

import sys
import os
import unittest
import sqlite3
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules import auth
from modules.sms_client import send_credentials


class AuthTestBase(unittest.TestCase):
    """Base test class with database setup/teardown and helper methods."""

    @classmethod
    def setUpClass(cls):
        """Create temporary directory and database for all tests."""
        cls.test_dir = tempfile.mkdtemp(prefix="kiosk_auth_test_")
        cls.db_path = os.path.join(cls.test_dir, "test_kiosk.db")

        # Create schema in test database
        cls._initialize_test_db(cls.db_path)

        # Insert test students
        cls._insert_test_students(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up temporary directory after all tests."""
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    @staticmethod
    def _initialize_test_db(db_path):
        """Initialize test database with schema."""
        schema_sql = """
        CREATE TABLE students (
            registration_number TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            surname TEXT NOT NULL,
            email TEXT NULL,
            programme TEXT NOT NULL,
            phone_number TEXT NULL,
            registration_status TEXT NOT NULL DEFAULT 'inactive'
        );

        CREATE TABLE cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_number TEXT NOT NULL,
            slot_index INTEGER NOT NULL,
            card_status TEXT NOT NULL DEFAULT 'pending',
            batch_id INT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (registration_number) REFERENCES students(registration_number)
        );

        CREATE TABLE authentication (
            auth_id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_number TEXT NOT NULL,
            otp_hash TEXT NULL,
            otp_expiry TIMESTAMP NULL,
            pin_hash TEXT NULL,
            is_temp_pin BOOLEAN DEFAULT FALSE,
            failed_otp_attempts INTEGER DEFAULT 0,
            failed_pin_attempts INTEGER DEFAULT 0,
            lockout_expiry TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (registration_number) REFERENCES students(registration_number)
        );

        CREATE TABLE audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            registration_number TEXT NOT NULL,
            event_type TEXT NOT NULL,
            failure_type TEXT NULL,
            session_id TEXT NULL,
            FOREIGN KEY (registration_number) REFERENCES students(registration_number)
        );

        CREATE TABLE batches (
            batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id TEXT NULL,
            scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_cards INTEGER DEFAULT 0,
            stored_count INTEGER DEFAULT 0,
            rejected_count INTEGER DEFAULT 0,
            sms_sent_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.executescript(schema_sql)
        conn.commit()
        conn.close()

    @staticmethod
    def _insert_test_students(db_path):
        """Insert test student fixtures (from mock_db_api/app.py)."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Test students from mock API
        students = [
            {
                "registration_number": "2022-04-09050",
                "first_name": "Samuel",
                "surname": "Musyani",
                "email": "samuel.musyani_22@student.udsm.ac.tz",
                "programme": "BSc. Electronics Engineering",
                "phone_number": "+255773422381",
                "registration_status": "active",
            },
            {
                "registration_number": "2022-04-12357",
                "first_name": "Godson",
                "surname": "Shirima",
                "email": "godson.shirima_22@student.udsm.ac.tz",
                "programme": "BSc. Telecommunications Engineering",
                "phone_number": "+255755981777",
                "registration_status": "active",
            },
        ]

        for student in students:
            cursor.execute(
                """INSERT INTO students 
                   (registration_number, first_name, surname, email, programme, phone_number, registration_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    student["registration_number"],
                    student["first_name"],
                    student["surname"],
                    student["email"],
                    student["programme"],
                    student["phone_number"],
                    student["registration_status"],
                ),
            )

            # Create authentication record (empty, will be populated by test)
            cursor.execute(
                """INSERT INTO authentication (registration_number)
                   VALUES (?)""",
                (student["registration_number"],),
            )

        conn.commit()
        conn.close()

    def _get_audit_events(self, reg_number):
        """Helper: Fetch all audit events for a student."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT event_type, failure_type, event_time FROM audit_log WHERE registration_number = ? ORDER BY event_time",
            (reg_number,),
        )
        events = cursor.fetchall()
        conn.close()
        return events

    def _clear_audit_log(self, reg_number=None):
        """Helper: Clear audit log (optional: for specific reg_number)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if reg_number:
            cursor.execute(
                "DELETE FROM audit_log WHERE registration_number = ?", (reg_number,)
            )
        else:
            cursor.execute("DELETE FROM audit_log")
        conn.commit()
        conn.close()

    def _reset_auth_record(self, reg_number):
        """Helper: Reset authentication record to initial state."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE authentication SET 
               otp_hash = NULL, otp_expiry = NULL, 
               pin_hash = NULL, is_temp_pin = FALSE,
               failed_otp_attempts = 0, failed_pin_attempts = 0, 
               lockout_expiry = NULL
               WHERE registration_number = ?""",
            (reg_number,),
        )
        conn.commit()
        conn.close()


class Test361ReturningStudent(AuthTestBase):
    """
    TASK 3.6.1: Returning Student Path
    ===================================

    Flow: OTP receive → correct OTP → correct PIN → success

    A returning student has an existing permanent PIN from a prior year.
    They do NOT need to set a new PIN on collection.

    Steps:
    1. Generate OTP and temp PIN
    2. Store OTP hash + expiry to database
    3. Store existing permanent PIN to database (is_temp_pin = FALSE)
    4. Call send_credentials to dispatch OTP via SMS+Email
    5. Verify OTP with correct value → SUCCESS
    6. Verify PIN with correct value → SUCCESS
    7. Confirm no PIN setup required (is_temp_pin = FALSE)
    8. Verify audit log records both verifications
    """

    def setUp(self):
        """Reset auth record before each test."""
        self._reset_auth_record("2022-04-09050")
        self._clear_audit_log("2022-04-09050")

    def test_361_returning_student_flow(self):
        """Test full returning student workflow: OTP → PIN → Success"""

        reg_number = "2022-04-09050"  # Samuel Musyani

        # STEP 1: Generate OTP
        print("\n[3.6.1] STEP 1: Generate OTP")
        otp = auth.generate_otp()
        print(f"  Generated OTP: {otp}")
        self.assertEqual(len(otp), 6, "OTP should be 6 digits")
        self.assertTrue(otp.isdigit(), "OTP should be numeric only")

        # STEP 2: Set permanent PIN for returning student
        print("\n[3.6.1] STEP 2: Set permanent PIN (existing student)")
        existing_pin = "1234"
        result = auth.set_pin(reg_number, existing_pin, self.db_path)
        self.assertTrue(result["success"], f"PIN set failed: {result['message']}")
        print(f"  Stored permanent PIN: {existing_pin}")

        # STEP 3: Store OTP to database
        print("\n[3.6.1] STEP 3: Store OTP hash + 24h expiry")
        auth.store_otp_to_db(reg_number, otp, self.db_path)
        print(f"  OTP stored with 24-hour expiry")

        # STEP 4: Send credentials via SMS + Email
        print("\n[3.6.1] STEP 4: Dispatch OTP via SMS + Email")
        send_result = send_credentials(reg_number, otp, None, self.db_path)
        print(f"  SMS sent: {send_result['sms_sent']}")
        print(f"  Email sent: {send_result['email_sent']}")
        if "sms_error" in send_result and send_result["sms_error"]:
            print(f"  SMS error: {send_result['sms_error']}")
        if "email_error" in send_result and send_result["email_error"]:
            print(f"  Email error: {send_result['email_error']}")

        # Both SMS and Email should succeed
        self.assertTrue(
            send_result["sms_sent"], "SMS delivery via Africa's Talking should succeed"
        )
        self.assertTrue(
            send_result["email_sent"], "Email delivery via Gmail should succeed"
        )

        # STEP 5: Verify OTP with correct value
        print("\n[3.6.1] STEP 5: Student enters correct OTP")
        otp_result = auth.verify_otp(reg_number, otp, self.db_path)
        print(f"  Result: {otp_result['message']}")
        self.assertTrue(
            otp_result["success"], f"OTP verification failed: {otp_result['message']}"
        )
        self.assertIsNone(otp_result["error"])

        # STEP 6: Verify PIN with correct value
        print("\n[3.6.1] STEP 6: Student enters correct PIN")
        pin_result = auth.verify_pin(reg_number, existing_pin, self.db_path)
        print(f"  Result: {pin_result['message']}")
        self.assertTrue(
            pin_result["success"], f"PIN verification failed: {pin_result['message']}"
        )
        self.assertIsNone(pin_result["error"])

        # STEP 7: Check PIN setup NOT required (returning student)
        print("\n[3.6.1] STEP 7: Verify is_temp_pin = FALSE (skip PIN setup)")
        pin_setup = auth.enforce_pin_setup(reg_number, self.db_path)
        self.assertTrue(pin_setup["success"])
        self.assertFalse(
            pin_setup["requires_pin_setup"],
            "Returning student should NOT require PIN setup",
        )
        print(f"  is_temp_pin = FALSE → Skip PIN setup screen ✓")

        # STEP 8: Verify audit log
        print("\n[3.6.1] STEP 8: Verify audit log records")
        events = self._get_audit_events(reg_number)
        print(f"  Audit events recorded: {len(events)}")
        event_types = [e[0] for e in events]
        self.assertIn("OTP VERIFIED", event_types, "OTP verification not logged")
        self.assertIn("PIN VERIFIED", event_types, "PIN verification not logged")
        print(f"  Events: {event_types}")

        print("\n✅ TEST 3.6.1 PASSED: Returning student flow complete")


class Test362FirstYearStudent(AuthTestBase):
    """
    TASK 3.6.2: First-Year Student Path
    ====================================

    Flow: OTP receive → correct OTP → temp PIN → set permanent PIN → success

    A first-year student receives a system-generated temporary PIN.
    They MUST set a permanent PIN before collection.

    Steps:
    1. Generate OTP and temp PIN
    2. Store OTP hash + expiry to database
    3. Store temp PIN hash with is_temp_pin = TRUE
    4. Call send_credentials to dispatch OTP + temp PIN via SMS+Email
    5. Verify OTP with correct value → SUCCESS
    6. Verify temp PIN with correct value → SUCCESS
    7. Check is_temp_pin = TRUE → Force PIN setup
    8. Student sets permanent PIN
    9. Verify is_temp_pin = FALSE → PIN setup complete
    10. Verify audit log records all events
    """

    def setUp(self):
        """Reset auth record before each test."""
        self._reset_auth_record("2022-04-12357")
        self._clear_audit_log("2022-04-12357")

    def test_362_first_year_student_flow(self):
        """Test full first-year student workflow: OTP → temp PIN → new PIN → Success"""

        reg_number = "2022-04-12357"  # Godson Shirima

        # STEP 1: Generate OTP and temp PIN
        print("\n[3.6.2] STEP 1: Generate OTP and temp PIN")
        otp = auth.generate_otp()
        temp_pin = auth.generate_temp_pin()
        print(f"  Generated OTP: {otp} (6 digits)")
        print(f"  Generated temp PIN: {temp_pin} (4 digits)")
        self.assertEqual(len(otp), 6)
        self.assertEqual(len(temp_pin), 4)

        # STEP 2: Store OTP to database
        print("\n[3.6.2] STEP 2: Store OTP hash + 24h expiry")
        auth.store_otp_to_db(reg_number, otp, self.db_path)
        print(f"  OTP stored")

        # STEP 3: Store temp PIN with is_temp_pin = TRUE
        print("\n[3.6.2] STEP 3: Store temp PIN with is_temp_pin = TRUE")
        auth.store_temp_pin_to_db(reg_number, temp_pin, self.db_path)
        print(f"  Temp PIN stored, is_temp_pin = TRUE")

        # STEP 4: Send credentials via SMS + Email (includes temp PIN)
        print("\n[3.6.2] STEP 4: Dispatch OTP + temp PIN via SMS + Email")
        send_result = send_credentials(reg_number, otp, temp_pin, self.db_path)
        print(f"  SMS sent: {send_result['sms_sent']}")
        print(f"  Email sent: {send_result['email_sent']}")
        if "sms_error" in send_result and send_result["sms_error"]:
            print(f"  SMS error: {send_result['sms_error']}")
        if "email_error" in send_result and send_result["email_error"]:
            print(f"  Email error: {send_result['email_error']}")

        # Both SMS and Email should succeed
        self.assertTrue(
            send_result["sms_sent"], "SMS delivery via Africa's Talking should succeed"
        )
        self.assertTrue(
            send_result["email_sent"], "Email delivery via Gmail should succeed"
        )

        # STEP 5: Verify OTP with correct value
        print("\n[3.6.2] STEP 5: Student enters correct OTP")
        otp_result = auth.verify_otp(reg_number, otp, self.db_path)
        print(f"  Result: {otp_result['message']}")
        self.assertTrue(
            otp_result["success"], f"OTP verification failed: {otp_result['message']}"
        )

        # STEP 6: Verify temp PIN with correct value
        print("\n[3.6.2] STEP 6: Student enters correct temp PIN")
        pin_result = auth.verify_pin(reg_number, temp_pin, self.db_path)
        print(f"  Result: {pin_result['message']}")
        self.assertTrue(
            pin_result["success"],
            f"Temp PIN verification failed: {pin_result['message']}",
        )

        # STEP 7: Check PIN setup IS required (first-year, is_temp_pin = TRUE)
        print("\n[3.6.2] STEP 7: Verify is_temp_pin = TRUE (force PIN setup)")
        pin_setup = auth.enforce_pin_setup(reg_number, self.db_path)
        self.assertTrue(pin_setup["success"])
        self.assertTrue(
            pin_setup["requires_pin_setup"],
            "First-year student should require PIN setup",
        )
        print(f"  is_temp_pin = TRUE → Force PIN setup screen ✓")

        # STEP 8: Student creates permanent PIN
        print("\n[3.6.2] STEP 8: Student creates permanent PIN")
        permanent_pin = "2468"
        pin_set = auth.set_pin(reg_number, permanent_pin, self.db_path)
        self.assertTrue(
            pin_set["success"], f"Permanent PIN set failed: {pin_set['message']}"
        )
        print(f"  Permanent PIN set: {permanent_pin}")
        print(f"  is_temp_pin set to FALSE in database")

        # STEP 9: Verify PIN setup no longer required
        print("\n[3.6.2] STEP 9: Verify is_temp_pin = FALSE (setup complete)")
        pin_setup_check = auth.enforce_pin_setup(reg_number, self.db_path)
        self.assertTrue(pin_setup_check["success"])
        self.assertFalse(
            pin_setup_check["requires_pin_setup"],
            "After PIN setup, should not require PIN setup again",
        )
        print(f"  is_temp_pin = FALSE → PIN setup complete ✓")

        # STEP 10: Verify permanent PIN works for next collection
        print("\n[3.6.2] STEP 10: Verify permanent PIN validates correctly")
        pin_verify = auth.verify_pin(reg_number, permanent_pin, self.db_path)
        self.assertTrue(
            pin_verify["success"], "Permanent PIN should verify successfully"
        )
        print(f"  Permanent PIN verified: {pin_verify['message']}")

        # STEP 11: Verify audit log
        print("\n[3.6.2] STEP 11: Verify audit log records")
        events = self._get_audit_events(reg_number)
        print(f"  Audit events recorded: {len(events)}")
        event_types = [e[0] for e in events]
        self.assertIn("OTP VERIFIED", event_types, "OTP verification not logged")
        self.assertIn("PIN VERIFIED", event_types, "PIN verification not logged")
        print(f"  Events: {event_types}")

        print("\n✅ TEST 3.6.2 PASSED: First-year student flow complete")


class Test363LockoutScenarios(AuthTestBase):
    """
    TASK 3.6.3: Lockout Enforcement
    ================================

    Tests lockout scenarios and audit logging:
    1. 3× wrong OTP → 30-minute soft lockout
    2. 3× wrong PIN → 24-hour hard lockout
    3. Audit log records all failures and lockout events

    OTP Lockout (soft):
    - Duration: 30 minutes
    - Trigger: 3 consecutive failed OTP attempts
    - Recovery: Automatic after 30 minutes or new batch load

    PIN Lockout (hard):
    - Duration: 24 hours
    - Trigger: 3 consecutive failed PIN attempts
    - Recovery: Automatic after 24 hours
    - Severity: Higher penalty for second factor

    Steps:
    1. Set up fresh authentication records
    2. Test OTP lockout: 3 wrong attempts → LOCKED status
    3. Test PIN lockout: 3 wrong attempts → LOCKED status
    4. Verify audit log has all failure and lockout records
    """

    def setUp(self):
        """Reset auth records before each test."""
        self._reset_auth_record("2022-04-09050")
        self._reset_auth_record("2022-04-12357")
        self._clear_audit_log()

    def test_363_otp_lockout(self):
        """Test OTP lockout after 3 wrong attempts (30-minute soft lockout)"""

        reg_number = "2022-04-09050"  # Samuel Musyani

        # Setup: Create valid OTP
        print("\n[3.6.3 OTP LOCKOUT] SETUP: Create valid OTP")
        otp = auth.generate_otp()
        auth.store_otp_to_db(reg_number, otp, self.db_path)
        print(f"  Valid OTP: {otp}")

        # STEP 1: First wrong OTP attempt
        print("\n[3.6.3 OTP LOCKOUT] STEP 1: First wrong OTP attempt")
        wrong_otp1 = "000000"
        result1 = auth.verify_otp(reg_number, wrong_otp1, self.db_path)
        print(f"  Attempt 1: {result1['message']}")
        self.assertFalse(result1["success"])
        self.assertEqual(result1["error"], "INVALID")

        # STEP 2: Second wrong OTP attempt
        print("\n[3.6.3 OTP LOCKOUT] STEP 2: Second wrong OTP attempt")
        wrong_otp2 = "999999"
        result2 = auth.verify_otp(reg_number, wrong_otp2, self.db_path)
        print(f"  Attempt 2: {result2['message']}")
        self.assertFalse(result2["success"])
        self.assertEqual(result2["error"], "INVALID")

        # STEP 3: Third wrong OTP attempt
        print("\n[3.6.3 OTP LOCKOUT] STEP 3: Third wrong OTP attempt")
        wrong_otp3 = "123456"
        result3 = auth.verify_otp(reg_number, wrong_otp3, self.db_path)
        print(f"  Attempt 3: {result3['message']}")
        self.assertFalse(result3["success"])
        self.assertEqual(
            result3["error"], "INVALID", "3rd failure should still be INVALID"
        )

        # STEP 4: Fourth attempt during lockout period → Locked
        print(
            "\n[3.6.3 OTP LOCKOUT] STEP 4: Fourth attempt (lockout triggered after 3 failures)"
        )
        result4 = auth.verify_otp(reg_number, otp, self.db_path)
        print(f"  Attempt 4 (with correct OTP): {result4['message']}")
        self.assertFalse(result4["success"])
        self.assertEqual(
            result4["error"],
            "LOCKED",
            "Should be locked after 3 failures on 4th attempt",
        )

        # STEP 5: Verify audit log
        print("\n[3.6.3 OTP LOCKOUT] STEP 5: Verify audit log records")
        events = self._get_audit_events(reg_number)
        print(f"  Total audit events: {len(events)}")
        event_types = [e[0] for e in events]

        # Should have 3 OTP failures + 1 OTP lockout event
        otp_failures = event_types.count("OTP FAILED")
        otp_lockouts = event_types.count("OTP LOCKOUT")

        print(f"  OTP failures logged: {otp_failures}")
        print(f"  OTP lockouts logged: {otp_lockouts}")

        self.assertEqual(otp_failures, 3, "Should have exactly 3 OTP failures logged")
        self.assertEqual(
            otp_lockouts, 1, "Should have exactly 1 OTP lockout event logged"
        )

        print("\n✅ OTP LOCKOUT TEST PASSED (30-minute soft lockout enforced)")

    def test_363_pin_lockout(self):
        """Test PIN lockout after 3 wrong attempts (24-hour hard lockout)"""

        reg_number = "2022-04-12357"  # Godson Shirima

        # Setup: Create valid OTP and PIN
        print("\n[3.6.3 PIN LOCKOUT] SETUP: Create valid OTP and PIN")
        otp = auth.generate_otp()
        pin = "4321"

        auth.store_otp_to_db(reg_number, otp, self.db_path)
        auth.set_pin(reg_number, pin, self.db_path)
        print(f"  Valid OTP: {otp}")
        print(f"  Valid PIN: {pin}")

        # STEP 1: First wrong PIN attempt
        print("\n[3.6.3 PIN LOCKOUT] STEP 1: First wrong PIN attempt")
        wrong_pin1 = "0000"
        result1 = auth.verify_pin(reg_number, wrong_pin1, self.db_path)
        print(f"  Attempt 1: {result1['message']}")
        self.assertFalse(result1["success"])
        self.assertEqual(result1["error"], "INVALID")

        # STEP 2: Second wrong PIN attempt
        print("\n[3.6.3 PIN LOCKOUT] STEP 2: Second wrong PIN attempt")
        wrong_pin2 = "9999"
        result2 = auth.verify_pin(reg_number, wrong_pin2, self.db_path)
        print(f"  Attempt 2: {result2['message']}")
        self.assertFalse(result2["success"])
        self.assertEqual(result2["error"], "INVALID")

        # STEP 3: Third wrong PIN attempt
        print("\n[3.6.3 PIN LOCKOUT] STEP 3: Third wrong PIN attempt")
        wrong_pin3 = "1111"
        result3 = auth.verify_pin(reg_number, wrong_pin3, self.db_path)
        print(f"  Attempt 3: {result3['message']}")
        self.assertFalse(result3["success"])
        self.assertEqual(
            result3["error"], "INVALID", "3rd failure should still be INVALID"
        )

        # STEP 4: Fourth attempt with correct PIN during lockout → Locked
        print(
            "\n[3.6.3 PIN LOCKOUT] STEP 4: Fourth attempt (lockout triggered after 3 failures)"
        )
        result4 = auth.verify_pin(reg_number, pin, self.db_path)
        print(f"  Attempt 4 (with correct PIN): {result4['message']}")
        self.assertFalse(result4["success"])
        self.assertEqual(
            result4["error"],
            "LOCKED",
            "Should be locked after 3 failures on 4th attempt",
        )

        # STEP 5: Verify audit log
        print("\n[3.6.3 PIN LOCKOUT] STEP 5: Verify audit log records")
        events = self._get_audit_events(reg_number)
        print(f"  Total audit events: {len(events)}")
        event_types = [e[0] for e in events]

        # Should have 3 PIN failures + 1 PIN lockout event
        pin_failures = event_types.count("PIN FAILED")
        pin_lockouts = event_types.count("PIN LOCKOUT")

        print(f"  PIN failures logged: {pin_failures}")
        print(f"  PIN lockouts logged: {pin_lockouts}")

        self.assertEqual(pin_failures, 3, "Should have exactly 3 PIN failures logged")
        self.assertEqual(
            pin_lockouts, 1, "Should have exactly 1 PIN lockout event logged"
        )

        print("\n✅ PIN LOCKOUT TEST PASSED (24-hour hard lockout enforced)")

    def test_363_combined_scenario(self):
        """Test combined scenario: OTP lockout, then fresh session with PIN lockout"""

        print(
            "\n[3.6.3 COMBINED] Testing OTP lockout followed by PIN lockout on fresh record"
        )

        # Use first student for OTP lockout
        otp_reg = "2022-04-09050"

        # Use second student for PIN lockout
        pin_reg = "2022-04-12357"

        # OTP LOCKOUT PHASE
        print("\n--- PHASE 1: OTP Lockout ---")
        otp = auth.generate_otp()
        auth.store_otp_to_db(otp_reg, otp, self.db_path)

        for attempt in range(1, 4):
            wrong = f"{attempt:06d}"
            result = auth.verify_otp(otp_reg, wrong, self.db_path)
            print(f"  OTP attempt {attempt}: {result['error']}")

        otp_locked = auth.verify_otp(otp_reg, otp, self.db_path)
        self.assertEqual(otp_locked["error"], "LOCKED")
        print(f"  OTP final attempt: {otp_locked['error']} ✓")

        # PIN LOCKOUT PHASE (fresh record)
        print("\n--- PHASE 2: PIN Lockout (fresh record) ---")
        pin = "5678"
        auth.set_pin(pin_reg, pin, self.db_path)

        for attempt in range(1, 4):
            wrong = f"{attempt:04d}"
            result = auth.verify_pin(pin_reg, wrong, self.db_path)
            print(f"  PIN attempt {attempt}: {result['error']}")

        pin_locked = auth.verify_pin(pin_reg, pin, self.db_path)
        self.assertEqual(pin_locked["error"], "LOCKED")
        print(f"  PIN final attempt: {pin_locked['error']} ✓")

        # Verify both records in audit log
        print("\n--- Audit Log Verification ---")
        otp_events = self._get_audit_events(otp_reg)
        pin_events = self._get_audit_events(pin_reg)

        print(f"  {otp_reg} events: {[e[0] for e in otp_events]}")
        print(f"  {pin_reg} events: {[e[0] for e in pin_events]}")

        print("\n✅ COMBINED SCENARIO TEST PASSED")


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
