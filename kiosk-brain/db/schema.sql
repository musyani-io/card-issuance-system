CREATE TABLE students (
    registration_number TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
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