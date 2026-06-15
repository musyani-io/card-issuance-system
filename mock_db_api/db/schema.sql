CREATE TABLE students (
    reg_number VARCHAR(11) PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    surname VARCHAR(100) NOT NULL,
    programme VARCHAR(50) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone_number VARCHAR(15) NOT NULL,
    year_of_study INT NOT NULL,
    registration_status VARCHAR(8) NOT NULL DEFAULT 'inactive',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

DELIMITER //

CREATE TRIGGER auto_email
BEFORE INSERT ON students
FOR EACH ROW
BEGIN
    SET NEW.email = CONCAT(
        LOWER(NEW.first_name),
        ".",
        LOWER(NEW.surname),
        "_",
        SUBSTRING(NEW.reg_number, 3, 2),
        "@student.udsm.ac.tz"
    );
END//

DELIMITER ;