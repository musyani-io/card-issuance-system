CREATE TABLE students (
    registration_number UNIQUE TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    surname TEXT NOT NULL,
    programme TEXT NOT NULL,
    email TEXT,
    phone_number TEXT NOT NULL,
    year_of_study INTEGER NOT NULL,
    registration status TEXT NOT NULL DEFAULT 'inactive',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);