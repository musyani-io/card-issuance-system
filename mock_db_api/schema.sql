-- ============================================================================
-- Mock University Database - MySQL Schema & Seed Data
-- ============================================================================

CREATE DATABASE IF NOT EXISTS card_issuance;
USE card_issuance;

-- Create students table with normalization-ready columns
CREATE TABLE IF NOT EXISTS students (
    reg_number VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NULL,
    phone VARCHAR(50) NULL,
    programme VARCHAR(150) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active'
);

-- Truncate existing data to avoid duplicate key errors on fresh imports
TRUNCATE TABLE students;

-- Seed student records for testing integration
INSERT INTO students (reg_number, first_name, last_name, email, phone, programme, status)
VALUES 
('2022-04-09050', 'Alice', 'Mwangi', 'alice.mwangi@udsm.ac.tz', '+255712345601', 'Computer Science', 'active'),
('T/UDSM/2022/1234', 'Bob', 'Kipchoge', 'bob.kipchoge@udsm.ac.tz', '+255712345602', 'Information Systems', 'active'),
('2022-04-09051', 'Charlie', 'Masanja', 'charlie.masanja@udsm.ac.tz', '+255712345603', 'Business Studies', 'inactive'),
('2022-04-09052', 'Diana', 'Komba', 'diana.komba@udsm.ac.tz', '+255712345604', 'Engineering', 'suspended');
