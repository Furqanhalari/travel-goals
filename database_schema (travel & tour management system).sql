-- ============================================================================
-- TRAVEL GOALS - DATABASE SCHEMA
-- Complete Database Setup Script for Oracle Database
-- ============================================================================

SET DEFINE OFF;

-- ============================================================================
-- SECTION 1: SEQUENCES
-- ============================================================================

CREATE SEQUENCE user_id_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE role_id_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE destination_id_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE vendor_id_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE package_id_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE booking_id_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE pending_dest_id_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE pending_pkg_id_seq START WITH 1 INCREMENT BY 1;


-- ============================================================================
-- SECTION 2: USERS TABLE
-- ============================================================================

-- Create USERS table
CREATE TABLE users (
    user_id NUMBER PRIMARY KEY,
    username VARCHAR2(50) UNIQUE NOT NULL,
    email VARCHAR2(100) UNIQUE NOT NULL,
    password_hash VARCHAR2(256) NOT NULL,
    full_name VARCHAR2(100) NOT NULL,
    phone VARCHAR2(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active NUMBER(1) DEFAULT 1,
    role_id NUMBER DEFAULT 3 NOT NULL
);

-- Trigger for USERS auto-increment
CREATE OR REPLACE TRIGGER user_id_trigger
BEFORE INSERT ON users
FOR EACH ROW
BEGIN
    IF :NEW.user_id IS NULL THEN
        SELECT user_id_seq.NEXTVAL INTO :NEW.user_id FROM DUAL;
    END IF;
END;
/

-- Indexes for USERS
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);


-- ============================================================================
-- SECTION 3: USER ROLES TABLE
-- ============================================================================

-- Create USER_ROLES table
CREATE TABLE user_roles (
    role_id NUMBER PRIMARY KEY,
    user_id NUMBER NOT NULL,
    role_name VARCHAR2(20) NOT NULL CHECK (role_name IN ('admin', 'customer', 'vendor')),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_role FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Trigger for USER_ROLES auto-increment
CREATE OR REPLACE TRIGGER role_id_trigger
BEFORE INSERT ON user_roles
FOR EACH ROW
BEGIN
    IF :NEW.role_id IS NULL THEN
        SELECT role_id_seq.NEXTVAL INTO :NEW.role_id FROM DUAL;
    END IF;
END;
/

-- Indexes for USER_ROLES
CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_name);

-- Add foreign key constraint to USERS table for role_id
ALTER TABLE users ADD CONSTRAINT fk_users_role 
FOREIGN KEY (role_id) REFERENCES user_roles(role_id);


-- ============================================================================
-- SECTION 4: DESTINATIONS TABLE
-- ============================================================================

-- Create DESTINATIONS table
CREATE TABLE destinations (
    destination_id NUMBER PRIMARY KEY,
    name VARCHAR2(100) NOT NULL UNIQUE,
    country VARCHAR2(100) NOT NULL,
    description CLOB,
    image_url VARCHAR2(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger for DESTINATIONS auto-increment
CREATE OR REPLACE TRIGGER destination_id_trigger
BEFORE INSERT ON destinations
FOR EACH ROW
BEGIN
    IF :NEW.destination_id IS NULL THEN
        SELECT destination_id_seq.NEXTVAL INTO :NEW.destination_id FROM DUAL;
    END IF;
END;
/

-- Indexes for DESTINATIONS
CREATE INDEX idx_destinations_name ON destinations(name);


-- ============================================================================
-- SECTION 5: VENDOR PROFILES TABLE
-- ============================================================================

-- Create VENDOR_PROFILES table
CREATE TABLE vendor_profiles (
    vendor_id NUMBER PRIMARY KEY,
    user_id NUMBER NOT NULL UNIQUE,
    company_name VARCHAR2(200) NOT NULL,
    business_license VARCHAR2(100),
    commission_rate NUMBER(5,2) DEFAULT 10.00,
    rating NUMBER(3,2) DEFAULT 0.00,
    verification_status VARCHAR2(20) DEFAULT 'pending' 
        CHECK (verification_status IN ('pending', 'verified', 'suspended')),
    image_url VARCHAR2(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_vendor_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Trigger for VENDOR_PROFILES auto-increment
CREATE OR REPLACE TRIGGER vendor_id_trigger
BEFORE INSERT ON vendor_profiles
FOR EACH ROW
BEGIN
    IF :NEW.vendor_id IS NULL THEN
        SELECT vendor_id_seq.NEXTVAL INTO :NEW.vendor_id FROM DUAL;
    END IF;
END;
/

-- Indexes for VENDOR_PROFILES
CREATE INDEX idx_vendor_user ON vendor_profiles(user_id);
CREATE INDEX idx_vendor_status ON vendor_profiles(verification_status);


-- ============================================================================
-- SECTION 6: PACKAGES TABLE
-- ============================================================================

-- Create PACKAGES table
CREATE TABLE packages (
    package_id NUMBER PRIMARY KEY,
    vendor_id NUMBER NOT NULL,
    destination_id NUMBER NOT NULL,
    name VARCHAR2(200) NOT NULL,
    description CLOB,
    price NUMBER(10,2) NOT NULL,
    duration_days NUMBER NOT NULL,
    max_travelers NUMBER,
    includes CLOB,
    image_url VARCHAR2(500),
    is_active NUMBER(1) DEFAULT 1,
    adult_price NUMBER(10,2) NOT NULL,
    child_price NUMBER(10,2) NOT NULL,
    infant_price NUMBER(10,2) NOT NULL,
    economy_adult_price NUMBER(10,2),
    economy_child_price NUMBER(10,2),
    economy_infant_price NUMBER(10,2),
    business_adult_price NUMBER(10,2),
    business_child_price NUMBER(10,2),
    business_infant_price NUMBER(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_package_vendor FOREIGN KEY (vendor_id) 
        REFERENCES vendor_profiles(vendor_id) ON DELETE CASCADE,
    CONSTRAINT fk_package_destination FOREIGN KEY (destination_id) 
        REFERENCES destinations(destination_id) ON DELETE CASCADE
);

-- Trigger for PACKAGES auto-increment
CREATE OR REPLACE TRIGGER package_id_trigger
BEFORE INSERT ON packages
FOR EACH ROW
BEGIN
    IF :NEW.package_id IS NULL THEN
        SELECT package_id_seq.NEXTVAL INTO :NEW.package_id FROM DUAL;
    END IF;
END;
/

-- Indexes for PACKAGES
CREATE INDEX idx_packages_vendor ON packages(vendor_id);
CREATE INDEX idx_packages_destination ON packages(destination_id);
CREATE INDEX idx_packages_active ON packages(is_active);


-- ============================================================================
-- SECTION 7: BOOKINGS TABLE
-- ============================================================================

-- Create BOOKINGS table
CREATE TABLE bookings (
    booking_id NUMBER PRIMARY KEY,
    user_id NUMBER NOT NULL,
    package_id NUMBER NOT NULL,
    departure_date DATE NOT NULL,
    return_date DATE,
    num_travelers NUMBER,
    total_price NUMBER(10,2),
    status VARCHAR2(20) DEFAULT 'pending' 
        CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed')),
    booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    special_requests CLOB,
    -- Additional booking details
    from_location VARCHAR2(100),
    to_location VARCHAR2(100),
    departure_time VARCHAR2(20),
    preferred_airline VARCHAR2(100),
    preferred_seating VARCHAR2(50),
    num_adults NUMBER(3) DEFAULT 1,
    num_children NUMBER(3) DEFAULT 0,
    num_infants NUMBER(3) DEFAULT 0,
    fare_type VARCHAR2(20) CHECK (fare_type IN ('one_way', 'round_trip')),
    return_time VARCHAR2(20),
    message VARCHAR2(1000),
    customer_full_name VARCHAR2(100),
    customer_phone VARCHAR2(20),
    customer_email VARCHAR2(100),
    -- Payment Information
    payment_status VARCHAR2(20) DEFAULT 'Unpaid' 
        CHECK (payment_status IN ('Unpaid', 'Processing', 'Paid', 'Failed')),
    payment_method VARCHAR2(50),
    payment_date TIMESTAMP,
    payment_transaction_id VARCHAR2(50),
    CONSTRAINT fk_booking_user FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_booking_package FOREIGN KEY (package_id) 
        REFERENCES packages(package_id) ON DELETE CASCADE
);

-- Trigger for BOOKINGS auto-increment
CREATE OR REPLACE TRIGGER booking_id_trigger
BEFORE INSERT ON bookings
FOR EACH ROW
BEGIN
    IF :NEW.booking_id IS NULL THEN
        SELECT booking_id_seq.NEXTVAL INTO :NEW.booking_id FROM DUAL;
    END IF;
END;
/

-- Indexes for BOOKINGS
CREATE INDEX idx_bookings_user ON bookings(user_id);
CREATE INDEX idx_bookings_package ON bookings(package_id);
CREATE INDEX idx_bookings_date ON bookings(booking_date);
CREATE INDEX idx_bookings_status ON bookings(status);


-- ============================================================================
-- SECTION 10: PENDING DESTINATIONS TABLE (Vendor Submissions)
-- ============================================================================

-- Create PENDING_DESTINATIONS table
CREATE TABLE pending_destinations (
    pending_id NUMBER PRIMARY KEY,
    vendor_id NUMBER NOT NULL,
    name VARCHAR2(100) NOT NULL,
    country VARCHAR2(100) NOT NULL,
    description CLOB,
    image_url VARCHAR2(500),
    status VARCHAR2(20) DEFAULT 'pending' 
        CHECK (status IN ('pending', 'approved', 'rejected')),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by NUMBER,
    admin_notes CLOB,
    CONSTRAINT fk_pending_dest_vendor FOREIGN KEY (vendor_id) 
        REFERENCES vendor_profiles(vendor_id) ON DELETE CASCADE,
);

-- Trigger for PENDING_DESTINATIONS auto-increment
CREATE OR REPLACE TRIGGER pending_dest_id_trigger
BEFORE INSERT ON pending_destinations
FOR EACH ROW
BEGIN
    IF :NEW.pending_id IS NULL THEN
        SELECT pending_dest_id_seq.NEXTVAL INTO :NEW.pending_id FROM DUAL;
    END IF;
END;
/

-- Indexes for PENDING_DESTINATIONS
CREATE INDEX idx_pending_dest_vendor ON pending_destinations(vendor_id);
CREATE INDEX idx_pending_dest_status ON pending_destinations(status);


-- ============================================================================
-- SECTION 11: PENDING PACKAGES TABLE (Vendor Submissions)
-- ============================================================================

-- Create PENDING_PACKAGES table
CREATE TABLE pending_packages (
    pending_pkg_id NUMBER PRIMARY KEY,
    vendor_id NUMBER NOT NULL,
    destination_id NUMBER NOT NULL,
    name VARCHAR2(200) NOT NULL,
    description CLOB,
    price NUMBER(10,2) NOT NULL,
    duration_days NUMBER NOT NULL,
    max_travelers NUMBER,
    includes CLOB,
    image_url VARCHAR2(500),
    adult_price NUMBER(10,2),
    child_price NUMBER(10,2),
    infant_price NUMBER(10,2),
    economy_adult_price NUMBER(10,2),
    economy_child_price NUMBER(10,2),
    economy_infant_price NUMBER(10,2),
    business_adult_price NUMBER(10,2),
    business_child_price NUMBER(10,2),
    business_infant_price NUMBER(10,2),
    status VARCHAR2(20) DEFAULT 'pending' 
        CHECK (status IN ('pending', 'approved', 'rejected')),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by NUMBER,
    admin_notes CLOB,
    CONSTRAINT fk_pending_pkg_vendor FOREIGN KEY (vendor_id) 
        REFERENCES vendor_profiles(vendor_id) ON DELETE CASCADE,
    CONSTRAINT fk_pending_pkg_dest FOREIGN KEY (destination_id) 
        REFERENCES destinations(destination_id) ON DELETE CASCADE,
);

-- Trigger for PENDING_PACKAGES auto-increment
CREATE OR REPLACE TRIGGER pending_pkg_id_trigger
BEFORE INSERT ON pending_packages
FOR EACH ROW
BEGIN
    IF :NEW.pending_pkg_id IS NULL THEN
        SELECT pending_pkg_id_seq.NEXTVAL INTO :NEW.pending_pkg_id FROM DUAL;
    END IF;
END;
/

-- Indexes for PENDING_PACKAGES
CREATE INDEX idx_pending_pkg_vendor ON pending_packages(vendor_id);
CREATE INDEX idx_pending_pkg_status ON pending_packages(status);

-- ============================================================================
-- SECTION 13: VIEWS
-- ============================================================================

-- View: USER_DETAILS
CREATE OR REPLACE VIEW user_details AS
SELECT 
    u.user_id,
    u.username,
    u.email,
    u.full_name,
    u.phone,
    u.created_at,
    u.last_login,
    u.is_active,
    ur.role_name,
    vp.vendor_id,
    vp.company_name,
    vp.verification_status
FROM users u
LEFT JOIN user_roles ur ON u.user_id = ur.user_id
LEFT JOIN vendor_profiles vp ON u.user_id = vp.user_id;

-- View: PACKAGE_DETAILS
CREATE OR REPLACE VIEW package_details AS
SELECT 
    p.package_id,
    p.name AS package_name,
    p.description,
    p.price,
    p.duration_days,
    p.max_travelers,
    p.includes,
    p.image_url,
    p.is_active,
    d.name AS destination_name,
    d.country,
    vp.company_name AS vendor_name,
    vp.rating AS vendor_rating,
    u.username AS vendor_username,
    (SELECT AVG(rating) FROM reviews WHERE package_id = p.package_id) AS avg_rating,
    (SELECT COUNT(*) FROM reviews WHERE package_id = p.package_id) AS review_count
FROM packages p
JOIN destinations d ON p.destination_id = d.destination_id
JOIN vendor_profiles vp ON p.vendor_id = vp.vendor_id
JOIN users u ON vp.user_id = u.user_id;

-- View: BOOKING_DETAILS
CREATE OR REPLACE VIEW booking_details AS
SELECT 
    b.booking_id,
    b.departure_date,
    b.return_date,
    b.num_travelers,
    b.total_price,
    b.status,
    b.booking_date,
    u.username,
    u.email,
    u.full_name,
    u.phone,
    p.name AS package_name,
    d.name AS destination_name,
    vp.company_name AS vendor_name
FROM bookings b
JOIN users u ON b.user_id = u.user_id
JOIN packages p ON b.package_id = p.package_id
JOIN destinations d ON p.destination_id = d.destination_id
JOIN vendor_profiles vp ON p.vendor_id = vp.vendor_id;

-- View: ACTIVE_VENDORS
CREATE OR REPLACE VIEW active_vendors AS
SELECT 
    vp.vendor_id,
    u.user_id,
    u.username,
    u.email,
    u.full_name,
    vp.company_name,
    vp.business_license,
    vp.commission_rate,
    vp.rating,
    vp.verification_status,
    vp.image_url,
    vp.created_at
FROM vendor_profiles vp
JOIN users u ON vp.user_id = u.user_id
WHERE vp.verification_status = 'verified'
  AND u.is_active = 1;

-- View: ADMIN_PENDING_APPROVALS
CREATE OR REPLACE VIEW admin_pending_approvals AS
SELECT 
    'vendor' as type,
    vp.vendor_id as id,
    vp.company_name as name,
    u.email,
    vp.created_at as submitted_at,
    vp.verification_status as status
FROM vendor_profiles vp
JOIN users u ON vp.user_id = u.user_id
WHERE vp.verification_status = 'pending'
UNION ALL
SELECT 
    'destination' as type,
    pd.pending_id as id,
    pd.name,
    u.email,
    pd.submitted_at,
    pd.status
FROM pending_destinations pd
JOIN vendor_profiles vp ON pd.vendor_id = vp.vendor_id
JOIN users u ON vp.user_id = u.user_id
WHERE pd.status = 'pending'
UNION ALL
SELECT 
    'package' as type,
    pp.pending_pkg_id as id,
    pp.name,
    u.email,
    pp.submitted_at,
    pp.status
FROM pending_packages pp
JOIN vendor_profiles vp ON pp.vendor_id = vp.vendor_id
JOIN users u ON vp.user_id = u.user_id
WHERE pp.status = 'pending'
ORDER BY submitted_at DESC;



-- ============================================================================
-- SECTION 14: SAMPLE DATA - DESTINATIONS
-- ============================================================================

INSERT INTO destinations (name, country, description, image_url) 
VALUES ('Paris', 'France', 'The city of lights and romance', 
        'https://media.istockphoto.com/id/1145422105/photo/eiffel-tower-aerial-view-paris.jpg');

INSERT INTO destinations (name, country, description, image_url) 
VALUES ('Tokyo', 'Japan', 'Modern metropolis with ancient traditions', 
        'https://media.istockphoto.com/id/484915982/photo/akihabara-tokyo.jpg');

INSERT INTO destinations (name, country, description, image_url) 
VALUES ('Dubai', 'UAE', 'Modern city known for luxury shopping and futuristic architecture', 
        'https://plus.unsplash.com/premium_photo-1661954654458-c673671d4a08');

-- Additional destinations
BEGIN
    INSERT INTO destinations (name, country, description, image_url)
    SELECT 'Barcelona', 'Spain', 'Beautiful coastal city with stunning architecture', 
           '../static/images/places/barcelona.jpg' FROM DUAL
    WHERE NOT EXISTS (SELECT 1 FROM destinations WHERE name = 'Barcelona');
END;
/

BEGIN
    INSERT INTO destinations (name, country, description, image_url)
    SELECT 'Bali', 'Indonesia', 'Tropical paradise with stunning beaches', 
           '../static/images/places/bali.jpg' FROM DUAL
    WHERE NOT EXISTS (SELECT 1 FROM destinations WHERE name = 'Bali');
END;
/

BEGIN
    INSERT INTO destinations (name, country, description, image_url)
    SELECT 'Hawaii', 'USA', 'Island paradise with volcanic landscapes', 
           '../static/images/places/hawaii.jpg' FROM DUAL
    WHERE NOT EXISTS (SELECT 1 FROM destinations WHERE name = 'Hawaii');
END;
/

BEGIN
    INSERT INTO destinations (name, country, description, image_url)
    SELECT 'London', 'United Kingdom', 'Historic city with iconic landmarks', 
           '../static/images/places/london.jpg' FROM DUAL
    WHERE NOT EXISTS (SELECT 1 FROM destinations WHERE name = 'London');
END;
/

BEGIN
    INSERT INTO destinations (name, country, description, image_url)
    SELECT 'Miami', 'USA', 'Vibrant city with beautiful beaches', 
           '../static/images/places/miami.jpg' FROM DUAL
    WHERE NOT EXISTS (SELECT 1 FROM destinations WHERE name = 'Miami');
END;
/

BEGIN
    INSERT INTO destinations (name, country, description, image_url)
    SELECT 'Munich', 'Germany', 'Bavarian city famous for beer culture', 
           '../static/images/places/munich.jpg' FROM DUAL
    WHERE NOT EXISTS (SELECT 1 FROM destinations WHERE name = 'Munich');
END;
/

BEGIN
    INSERT INTO destinations (name, country, description, image_url)
    SELECT 'New York City', 'USA', 'The city that never sleeps', 
           '../static/images/places/new-york-city.jpg' FROM DUAL
    WHERE NOT EXISTS (SELECT 1 FROM destinations WHERE name = 'New York City');
END;
/

BEGIN
    INSERT INTO destinations (name, country, description, image_url)
    SELECT 'Sydney', 'Australia', 'Harbor city with stunning opera house', 
           '../static/images/places/sydney.jpg' FROM DUAL
    WHERE NOT EXISTS (SELECT 1 FROM destinations WHERE name = 'Sydney');
END;
/

BEGIN
    INSERT INTO destinations (name, country, description, image_url)
    SELECT 'Ocean', 'Maldives', 'Crystal clear waters and white sand beaches', 
           '../static/images/places/ocean.jpg' FROM DUAL
    WHERE NOT EXISTS (SELECT 1 FROM destinations WHERE name = 'Ocean');
END;
/


-- ============================================================================
-- SECTION 15: SAMPLE DATA - USERS AND VENDORS
-- ============================================================================

-- Insert Admin user (password: admin123)
INSERT INTO users (username, email, password_hash, full_name, phone, is_active)
VALUES ('admin', 'admin@travelgoals.com', 
        '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 
        'System Administrator', '1234567890', 1);

-- Insert Vendor users
INSERT INTO users (username, email, password_hash, full_name, phone, is_active)
VALUES ('PIA', 'admin@piac.com.pk', 
        '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 
        'Pakistan International Airlines', '1234567891', 1);

INSERT INTO users (username, email, password_hash, full_name, phone, is_active)
VALUES ('FLY_JINNAH', 'admin@flyjinnah.com', 
        '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 
        'Fly Jinnah', '1234567892', 1);

INSERT INTO users (username, email, password_hash, full_name, phone, is_active)
VALUES ('AIR_BLUE', 'admin@airblue.com', 
        '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 
        'Air Blue', '1234567893', 1);

-- Assign roles
INSERT INTO user_roles (user_id, role_name)
SELECT user_id, 'admin' FROM users WHERE username = 'admin';

INSERT INTO user_roles (user_id, role_name)
SELECT user_id, 'vendor' FROM users WHERE username = 'PIA';

INSERT INTO user_roles (user_id, role_name)
SELECT user_id, 'vendor' FROM users WHERE username = 'FLY_JINNAH';

INSERT INTO user_roles (user_id, role_name)
SELECT user_id, 'vendor' FROM users WHERE username = 'AIR_BLUE';

-- Update users with role_id
UPDATE users SET role_id = 1 WHERE username = 'admin';
UPDATE users SET role_id = 2 WHERE username IN ('PIA', 'FLY_JINNAH', 'AIR_BLUE');

-- Create vendor profiles
INSERT INTO vendor_profiles (user_id, company_name, business_license, 
                             commission_rate, rating, verification_status, image_url)
SELECT user_id, 'PIA', 'LIC-001', 10.00, 4.8, 'verified',
       'https://logowik.com/content/uploads/images/pakistan-international-airlines4661.logowik.com.webp'
FROM users WHERE username = 'PIA';

INSERT INTO vendor_profiles (user_id, company_name, business_license, 
                             commission_rate, rating, verification_status, image_url)
SELECT user_id, 'FLY JINNAH', 'LIC-002', 10.00, 4.6, 'verified',
       'https://upload.wikimedia.org/wikipedia/commons/a/a8/Fly_Jinnah_logo.jpg'
FROM users WHERE username = 'FLY_JINNAH';

INSERT INTO vendor_profiles (user_id, company_name, business_license, 
                             commission_rate, rating, verification_status, image_url)
SELECT user_id, 'AIR BLUE', 'LIC-003', 10.00, 4.9, 'verified',
       'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/Airblue_Logo.svg/2560px-Airblue_Logo.svg.png'
FROM users WHERE username = 'AIR_BLUE';


-- ============================================================================
-- SECTION 16: SAMPLE DATA - PACKAGES
-- ============================================================================

-- Paris Packages
INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days, 
                     max_travelers, includes, image_url, is_active, 
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Paris Romance Tour',
       'Fall in love with the City of Lights', 90.00, 5, 18,
       'Boutique hotel, Breakfast, Museum passes, Seine cruise, Wine tasting',
       '../static/images/places/paris.jpg', 1,
       1200, 900, 300, 1200, 900, 300, 1800, 1350, 450
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'PIA' AND d.name = 'Paris';

INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Paris City of Lights',
       'Experience the magic of Paris', 90.00, 5, 8,
       'Hotel, Daily breakfast, Guided tours, Museum passes, Transfers',
       '../static/images/places/paris.jpg', 1,
       1200, 900, 300, 1200, 900, 300, 1800, 1350, 450
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'FLY JINNAH' AND d.name = 'Paris';

INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Romantic Paris Getaway',
       'A romantic escape to Paris with luxury accommodations', 90.00, 4, 4,
       'Luxury hotel, All meals, Private tours, Champagne cruise, Spa access',
       '../static/images/places/paris.jpg', 1,
       1500, 1100, 400, 1500, 1100, 400, 2250, 1650, 600
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'AIR BLUE' AND d.name = 'Paris';

-- Tokyo Packages
INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Tokyo Modern & Traditional',
       'Perfect blend of ancient temples and modern technology', 90.00, 7, 15,
       'Hotel, Breakfast, Temple visits, Sushi class, Train pass',
       '../static/images/places/tokyo.jpg', 1,
       1400, 1000, 350, 1400, 1000, 350, 2100, 1500, 525
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'PIA' AND d.name = 'Tokyo';

INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Tokyo Traditional Experience',
       'Immerse in Japanese culture with temple visits and tea ceremonies', 90.00, 6, 10,
       'Hotel, Daily breakfast, Cultural workshops, Temple visits, Local guide',
       '../static/images/places/tokyo.jpg', 1,
       1400, 1000, 350, 1400, 1000, 350, 2100, 1500, 525
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'FLY JINNAH' AND d.name = 'Tokyo';

INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Modern Tokyo Tech Tour',
       'Explore cutting-edge technology and anime culture', 90.00, 5, 8,
       '4-star hotel, Daily meals, Tech museum passes, Anime tours, Rail passes',
       '../static/images/places/tokyo.jpg', 1,
       1600, 1150, 400, 1600, 1150, 400, 2400, 1725, 600
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'AIR BLUE' AND d.name = 'Tokyo';

-- Dubai Packages
INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Dubai Desert Safari Package',
       'Experience Arabian desert with dune bashing and traditional BBQ', 90.00, 4, 12,
       'Hotel with pool, Breakfast and dinner, Desert safari, City tour, Theme park',
       '../static/images/places/dubai.jpg', 1,
       1100, 800, 250, 1100, 800, 250, 1650, 1200, 375
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'FLY JINNAH' AND d.name = 'Dubai';

INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Luxury Dubai Experience',
       'Ultimate luxury with 5-star accommodations and private yacht', 90.00, 6, 6,
       'Five-star suite, All meals, Private yacht, Helicopter tour, Shopping, Spa',
       '../static/images/places/dubai.jpg', 1,
       2500, 1800, 600, 2500, 1800, 600, 3750, 2700, 900
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'AIR BLUE' AND d.name = 'Dubai';

-- Barcelona Package
INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Barcelona City Break',
       'Explore Gaudi architecture, enjoy tapas, and relax on beaches', 90.00, 5, 15,
       'Hotel, Breakfast, City tour guide, Museum tickets',
       '../static/images/places/barcelona.jpg', 1,
       900, 650, 200, 900, 650, 200, 1350, 975, 300
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'PIA' AND d.name = 'Barcelona';

-- Bali Package
INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Bali Paradise Getaway',
       'Experience Bali magic with temple visits and beach relaxation', 90.00, 7, 12,
       'Resort, All meals, Airport transfer, Temple tours, Spa session',
       '../static/images/places/bali.jpg', 1,
       1000, 700, 250, 1000, 700, 250, 1500, 1050, 375
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'PIA' AND d.name = 'Bali';

-- Hawaii Package
INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Hawaiian Island Adventure',
       'Discover Hawaiian beauty with volcano tours and snorkeling', 90.00, 6, 10,
       'Beachfront hotel, Breakfast and dinner, Snorkeling, Island hopping',
       '../static/images/places/hawaii.jpg', 1,
       1300, 900, 300, 1300, 900, 300, 1950, 1350, 450
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'AIR BLUE' AND d.name = 'Hawaii';

-- London Package
INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'London Royal Experience',
       'Experience British royalty with palace visits and afternoon tea', 90.00, 5, 20,
       'Central hotel, Breakfast, Thames cruise, Palace tickets, Theater show',
       '../static/images/places/london.jpg', 1,
       1100, 800, 250, 1100, 800, 250, 1650, 1200, 375
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'PIA' AND d.name = 'London';

-- Miami Package
INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Miami Beach Escape',
       'Soak up sun on South Beach and experience vibrant nightlife', 90.00, 4, 15,
       'Ocean view hotel, Breakfast, Beach club access, Everglades tour',
       '../static/images/places/miami.jpg', 1,
       950, 650, 200, 950, 650, 200, 1425, 975, 300
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'AIR BLUE' AND d.name = 'Miami';

-- Munich Package
INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Munich Beer & Culture Tour',
       'Experience Bavarian culture with brewery tours and castle visits', 90.00, 4, 16,
       'Hotel, Breakfast, Brewery tours, Castle visit, Beer garden meal',
       '../static/images/places/munich.jpg', 1,
       900, 650, 200, 900, 650, 200, 1350, 975, 300
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'PIA' AND d.name = 'Munich';

-- New York City Package
INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'NYC Big Apple Experience',
       'Discover the city that never sleeps with all iconic landmarks', 90.00, 5, 20,
       'Manhattan hotel, Breakfast, Statue ferry, Broadway show, City pass',
       '../static/images/places/new-york-city.jpg', 1,
       1200, 850, 300, 1200, 850, 300, 1800, 1275, 450
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'PIA' AND d.name = 'New York City';

-- Sydney Package
INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Sydney Harbor Adventure',
       'Explore Opera House, climb Harbor Bridge, and visit Blue Mountains', 90.00, 6, 12,
       'Harbor view hotel, Breakfast, Opera tour, Bridge climb, Wildlife park',
       '../static/images/places/sydney.jpg', 1,
       1400, 1000, 350, 1400, 1000, 350, 2100, 1500, 525
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'PIA' AND d.name = 'Sydney';

-- Ocean/Maldives Package
INSERT INTO packages (vendor_id, destination_id, name, description, price, duration_days,
                     max_travelers, includes, image_url, is_active,
                     adult_price, child_price, infant_price,
                     economy_adult_price, economy_child_price, economy_infant_price,
                     business_adult_price, business_child_price, business_infant_price)
SELECT vp.vendor_id, d.destination_id, 'Maldives Ocean Paradise',
       'Ultimate luxury in overwater bungalows with crystal waters', 90.00, 5, 8,
       'Overwater villa, All-inclusive meals, Water sports, Spa, Diving',
       '../static/images/places/ocean.jpg', 1,
       2000, 1400, 500, 2000, 1400, 500, 3000, 2100, 750
FROM vendor_profiles vp, destinations d
WHERE vp.company_name = 'AIR BLUE' AND d.name = 'Ocean';
