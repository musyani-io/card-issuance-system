-- ============================================================================
-- Smart ID Card Distribution Kiosk — SQLite Database Schema
-- ============================================================================
-- 
-- This schema defines 5 core tables for managing student card issuance process:
-- students, cards, authentication, audit_log, batches
--
-- KEY DESIGN PATTERNS:
-- =====================
-- 1. PRIMARY KEY: registration_number (TEXT, UNIQUE)
--    - Students identified by unique registration number across all tables
--    - Example: "2022-04-09050"
--
-- 2. AUTHENTICATION DESIGN: is_temp_pin column
--    - is_temp_pin = FALSE (returning student or user-set PIN)
--    - is_temp_pin = TRUE (first-year student gets temporary system-generated PIN)
--    - After first PIN verification, student creates permanent PIN and is_temp_pin → FALSE
--
-- 3. CREDENTIAL VALIDATION: *_hash and *_attempts columns
--    - otp_hash: Hashed OTP (never store plaintext)
--    - pin_hash: Bcrypt-hashed PIN
--    - failed_otp_attempts: Counter incremented on wrong OTP (lockout after 3)
--    - failed_pin_attempts: Counter incremented on wrong PIN (lockout after 3)
--    - lockout_expiry: Timestamp when 15-minute lockout ends
--
-- 4. AUDIT TRAIL: audit_log table (immutable, append-only)
--    - Records every transaction for compliance and debugging
--    - event_type: otp_sent, otp_verified, pin_verified, card_dispensed, auth_failed, etc.
--    - failure_type: Why operation failed (invalid_otp, invalid_pin, expired, etc.)
--    - session_id: Traces all events within one transaction session
--
-- 5. BATCH PROCESSING: cards and batches tables
--    - Batch: Group of cards loaded together (e.g., "Batch_20260402_001")
--    - Cards table: Tracks physical card location and status
--    - Slots enable efficient batch management (slot_index = position in batch)
--
-- TIMESTAMPS: All *_at and *_expiry columns use TIMESTAMP for sorting and filtering
--
-- ============================================================================

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