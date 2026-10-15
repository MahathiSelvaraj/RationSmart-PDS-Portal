-- ============================================================================
-- RationSmart: Intelligent PDS Distribution & Beneficiary Transparency Platform
-- MySQL Database: digital_ration_db
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `digital_ration_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `digital_ration_db`;

-- Drop tables in reverse order of foreign key dependency
DROP TABLE IF EXISTS `grievances`;
DROP TABLE IF EXISTS `anomaly_logs`;
DROP TABLE IF EXISTS `transaction_items`;
DROP TABLE IF EXISTS `distribution_transactions`;
DROP TABLE IF EXISTS `shop_stocks`;
DROP TABLE IF EXISTS `grain_allocations`;
DROP TABLE IF EXISTS `family_members`;
DROP TABLE IF EXISTS `users`;
DROP TABLE IF EXISTS `ration_cards`;
DROP TABLE IF EXISTS `commodities`;
DROP TABLE IF EXISTS `ration_shops`;

-- 1. Fair Price Shops Table
CREATE TABLE `ration_shops` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `shop_code` VARCHAR(32) NOT NULL UNIQUE,
  `shop_name` VARCHAR(150) NOT NULL,
  `dealer_name` VARCHAR(120) NOT NULL,
  `license_no` VARCHAR(64) NOT NULL UNIQUE,
  `contact_no` VARCHAR(20) NOT NULL,
  `address` VARCHAR(255) NOT NULL,
  `ward` VARCHAR(64) NOT NULL,
  `district` VARCHAR(64) NOT NULL DEFAULT 'Central District',
  `status` VARCHAR(20) DEFAULT 'Active',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Commodities Table
CREATE TABLE `commodities` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `code` VARCHAR(32) NOT NULL UNIQUE,
  `name` VARCHAR(64) NOT NULL,
  `unit` VARCHAR(20) NOT NULL DEFAULT 'kg',
  `price_per_unit` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `is_active` TINYINT(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Ration Cards (Beneficiaries) Table
CREATE TABLE `ration_cards` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `card_number` VARCHAR(64) NOT NULL UNIQUE,
  `card_type` VARCHAR(20) NOT NULL, -- 'AAY', 'PHH', 'NPHH', 'AY'
  `head_of_family` VARCHAR(120) NOT NULL,
  `family_members_count` INT NOT NULL DEFAULT 1,
  `aadhaar_last4` VARCHAR(4) NOT NULL,
  `mobile` VARCHAR(20),
  `address` VARCHAR(255) NOT NULL,
  `assigned_shop_id` INT NOT NULL,
  `status` VARCHAR(20) DEFAULT 'Active',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`assigned_shop_id`) REFERENCES `ration_shops`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Family Members Table
CREATE TABLE `family_members` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `ration_card_id` INT NOT NULL,
  `full_name` VARCHAR(120) NOT NULL,
  `relationship` VARCHAR(64) NOT NULL, -- 'Self (Head)', 'Spouse', 'Son', 'Daughter'
  `age` INT NOT NULL,
  `gender` VARCHAR(20) NOT NULL,
  `aadhaar_last4` VARCHAR(4) NOT NULL,
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`ration_card_id`) REFERENCES `ration_cards`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Users Table (Admin, Dealers, Citizens)
CREATE TABLE `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(64) NOT NULL UNIQUE,
  `password_hash` VARCHAR(256) NOT NULL,
  `full_name` VARCHAR(120) NOT NULL,
  `email` VARCHAR(120) UNIQUE,
  `phone` VARCHAR(20),
  `role` VARCHAR(20) NOT NULL DEFAULT 'citizen', -- 'admin', 'dealer', 'citizen'
  `shop_id` INT NULL,
  `ration_card_id` INT NULL,
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`shop_id`) REFERENCES `ration_shops`(`id`) ON DELETE SET NULL,
  FOREIGN KEY (`ration_card_id`) REFERENCES `ration_cards`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Central Godown Grain Allocations Table
CREATE TABLE `grain_allocations` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `allocation_code` VARCHAR(64) NOT NULL UNIQUE,
  `shop_id` INT NOT NULL,
  `commodity_id` INT NOT NULL,
  `allocated_qty` DECIMAL(10,2) NOT NULL,
  `allocation_month` VARCHAR(7) NOT NULL, -- 'YYYY-MM'
  `dispatch_date` DATE NOT NULL,
  `status` VARCHAR(20) DEFAULT 'Received',
  `notes` VARCHAR(255),
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`shop_id`) REFERENCES `ration_shops`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`commodity_id`) REFERENCES `commodities`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Shop Stock Table
CREATE TABLE `shop_stocks` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `shop_id` INT NOT NULL,
  `commodity_id` INT NOT NULL,
  `current_stock` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `min_threshold` DECIMAL(10,2) NOT NULL DEFAULT 150.00,
  `last_replenished_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_shop_commodity_stock` (`shop_id`, `commodity_id`),
  FOREIGN KEY (`shop_id`) REFERENCES `ration_shops`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`commodity_id`) REFERENCES `commodities`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Distribution Transactions Table
CREATE TABLE `distribution_transactions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `bill_number` VARCHAR(64) NOT NULL UNIQUE,
  `ration_card_id` INT NOT NULL,
  `shop_id` INT NOT NULL,
  `user_id` INT NULL,
  `transaction_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `month_period` VARCHAR(7) NOT NULL,
  `total_amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `payment_mode` VARCHAR(32) DEFAULT 'Cash / Direct Subsidy',
  `auth_mode` VARCHAR(64) DEFAULT 'Biometric Aadhaar Authentication (Simulated)',
  `status` VARCHAR(20) DEFAULT 'Completed',
  `notes` VARCHAR(255),
  FOREIGN KEY (`ration_card_id`) REFERENCES `ration_cards`(`id`) ON DELETE RESTRICT,
  FOREIGN KEY (`shop_id`) REFERENCES `ration_shops`(`id`) ON DELETE RESTRICT,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. Transaction Items Table
CREATE TABLE `transaction_items` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `transaction_id` INT NOT NULL,
  `commodity_id` INT NOT NULL,
  `quantity` DECIMAL(10,2) NOT NULL,
  `unit_price` DECIMAL(10,2) NOT NULL,
  `subtotal` DECIMAL(10,2) NOT NULL,
  FOREIGN KEY (`transaction_id`) REFERENCES `distribution_transactions`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`commodity_id`) REFERENCES `commodities`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. Anomaly Logs Table
CREATE TABLE `anomaly_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `transaction_id` INT NULL,
  `ration_card_id` INT NULL,
  `shop_id` INT NULL,
  `anomaly_type` VARCHAR(64) NOT NULL,
  `severity` VARCHAR(20) DEFAULT 'Medium',
  `description` TEXT NOT NULL,
  `status` VARCHAR(20) DEFAULT 'Flagged',
  `detected_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `resolution_notes` TEXT NULL,
  FOREIGN KEY (`transaction_id`) REFERENCES `distribution_transactions`(`id`) ON DELETE SET NULL,
  FOREIGN KEY (`ration_card_id`) REFERENCES `ration_cards`(`id`) ON DELETE SET NULL,
  FOREIGN KEY (`shop_id`) REFERENCES `ration_shops`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11. Grievances Table
CREATE TABLE `grievances` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `grievance_code` VARCHAR(32) NOT NULL UNIQUE,
  `ration_card_number` VARCHAR(64) NOT NULL,
  `citizen_name` VARCHAR(120) NOT NULL,
  `citizen_phone` VARCHAR(20) NOT NULL,
  `shop_id` INT NULL,
  `subject` VARCHAR(150) NOT NULL,
  `description` TEXT NOT NULL,
  `status` VARCHAR(20) DEFAULT 'Pending',
  `response_text` TEXT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `resolved_at` DATETIME NULL,
  FOREIGN KEY (`shop_id`) REFERENCES `ration_shops`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- Initial Sample Inserts
-- ============================================================================

INSERT INTO `commodities` (`id`, `code`, `name`, `unit`, `price_per_unit`, `is_active`) VALUES
(1, 'RICE', 'Rice (NFSA Grade A)', 'kg', 2.00, 1),
(2, 'WHEAT', 'Wheat (Fortified Atta)', 'kg', 3.00, 1),
(3, 'SUGAR', 'Refined Sugar', 'kg', 13.50, 1),
(4, 'KEROSENE', 'Subsidized Kerosene', 'liter', 25.00, 1),
(5, 'DAL', 'Tur Dal / Pulses', 'kg', 35.00, 1);

INSERT INTO `ration_shops` (`id`, `shop_code`, `shop_name`, `dealer_name`, `license_no`, `contact_no`, `address`, `ward`, `district`, `status`) VALUES
(1, 'FPS-101', 'Central Ward Fair Price Shop #101', 'Ramesh Kumar Verma', 'LIC-PDS-2024-0089', '9876543210', 'Shop 12, Main Bazaar, Anna Nagar', 'Ward 12', 'Metro Central', 'Active'),
(2, 'FPS-102', 'Gandhi Chowk PDS Distribution Center #102', 'Sunita Devi', 'LIC-PDS-2023-0145', '9876501234', 'Plot 45, Near Post Office, Gandhi Nagar', 'Ward 15', 'Metro Central', 'Active'),
(3, 'FPS-103', 'Market Road Public Ration Store #103', 'Abdul Razak', 'LIC-PDS-2022-0312', '9845123456', 'Shop 3B, Old Vegetable Market, Sector 4', 'Ward 21', 'Metro Central', 'Active'),
(4, 'FPS-104', 'Railway Colony Ration Depot #104', 'Manish Sharma', 'LIC-PDS-2025-0077', '9812345678', 'Platform Road, Near Gate 2, Railway Colony', 'Ward 08', 'Metro Central', 'Active');

INSERT INTO `ration_cards` (`id`, `card_number`, `card_type`, `head_of_family`, `family_members_count`, `aadhaar_last4`, `mobile`, `address`, `assigned_shop_id`, `status`) VALUES
(1, 'RC-AAY-1001', 'AAY', 'Munna Lal', 4, '4512', '9823112233', 'House 14, Slum Colony, Anna Nagar', 1, 'Active'),
(2, 'RC-AAY-1002', 'AAY', 'Devaki Ammal', 3, '7821', '9823223344', 'Hut 8, Canal Road, Anna Nagar', 1, 'Active'),
(3, 'RC-PHH-2001', 'PHH', 'Suresh Babu', 4, '9034', '9834112233', '12/4, Gandhi Street, Anna Nagar', 1, 'Active'),
(4, 'RC-PHH-2002', 'PHH', 'Lakshmi Narayan', 5, '1129', '9834223344', '45, Market Lane, Anna Nagar', 1, 'Active'),
(5, 'RC-PHH-2003', 'PHH', 'Meenakshi Sundaram', 2, '6643', '9834334455', '89/1, 2nd Cross, Anna Nagar', 1, 'Active'),
(6, 'RC-NPHH-3001', 'NPHH', 'Anand Joshi', 3, '5521', '9845112233', 'Flat 202, Surya Apts, Anna Nagar', 1, 'Active'),
(7, 'RC-NPHH-3002', 'NPHH', 'Pooja Agarwal', 4, '8872', '9845223344', '104, Green Avenue, Anna Nagar', 1, 'Active'),
(8, 'RC-AY-4001', 'AY', 'Ramachandra Rao (Sr. Citizen)', 1, '3310', '9856112233', 'Old Age Quarters, Block C, Anna Nagar', 1, 'Active');

INSERT INTO `family_members` (`id`, `ration_card_id`, `full_name`, `relationship`, `age`, `gender`, `aadhaar_last4`, `is_active`) VALUES
(1, 1, 'Munna Lal', 'Self (Head)', 46, 'Male', '4512', 1),
(2, 1, 'Shanti Devi', 'Spouse', 42, 'Female', '7819', 1),
(3, 1, 'Rahul Kumar', 'Son', 19, 'Male', '2314', 1),
(4, 1, 'Priya Kumari', 'Daughter', 16, 'Female', '6690', 1),
(5, 3, 'Suresh Babu', 'Self (Head)', 40, 'Male', '9034', 1),
(6, 3, 'Radha Suresh', 'Spouse', 36, 'Female', '5543', 1),
(7, 3, 'Ananya Suresh', 'Daughter', 14, 'Female', '8812', 1),
(8, 3, 'Karthik Suresh', 'Son', 11, 'Male', '4421', 1),
(9, 8, 'Ramachandra Rao', 'Self (Head)', 68, 'Male', '3310', 1);

-- Default passwords:
-- admin: admin123
-- dealer1, dealer2, dealer3: dealer123
-- citizen1, citizen2, citizen3: citizen123
INSERT INTO `users` (`id`, `username`, `password_hash`, `full_name`, `email`, `phone`, `role`, `shop_id`, `ration_card_id`, `is_active`) VALUES
(1, 'admin', 'scrypt:32768:8:1$05cE3Q6EwWkFp0vQ$9e8557ea6cf3f9cb907b8a786ec33c399585642e1858a74ecdf3fc6f69300eb058097daeecbb7a4c7cf98d655f463326162ae068779fb652eb6a1d8212187f54', 'District Food Supply Officer (Admin)', 'admin@rationsmart.gov.in', '9900011223', 'admin', NULL, NULL, 1),
(2, 'dealer1', 'scrypt:32768:8:1$05cE3Q6EwWkFp0vQ$9e8557ea6cf3f9cb907b8a786ec33c399585642e1858a74ecdf3fc6f69300eb058097daeecbb7a4c7cf98d655f463326162ae068779fb652eb6a1d8212187f54', 'Ramesh Kumar Verma', 'dealer1@rationsmart.gov.in', '9876543210', 'dealer', 1, NULL, 1),
(3, 'dealer2', 'scrypt:32768:8:1$05cE3Q6EwWkFp0vQ$9e8557ea6cf3f9cb907b8a786ec33c399585642e1858a74ecdf3fc6f69300eb058097daeecbb7a4c7cf98d655f463326162ae068779fb652eb6a1d8212187f54', 'Sunita Devi', 'dealer2@rationsmart.gov.in', '9876501234', 'dealer', 2, NULL, 1),
(4, 'citizen1', 'scrypt:32768:8:1$05cE3Q6EwWkFp0vQ$9e8557ea6cf3f9cb907b8a786ec33c399585642e1858a74ecdf3fc6f69300eb058097daeecbb7a4c7cf98d655f463326162ae068779fb652eb6a1d8212187f54', 'Munna Lal', 'munnalal@citizen.gov.in', '9823112233', 'citizen', NULL, 1, 1),
(5, 'citizen2', 'scrypt:32768:8:1$05cE3Q6EwWkFp0vQ$9e8557ea6cf3f9cb907b8a786ec33c399585642e1858a74ecdf3fc6f69300eb058097daeecbb7a4c7cf98d655f463326162ae068779fb652eb6a1d8212187f54', 'Suresh Babu', 'sureshbabu@citizen.gov.in', '9834112233', 'citizen', NULL, 3, 1),
(6, 'citizen3', 'scrypt:32768:8:1$05cE3Q6EwWkFp0vQ$9e8557ea6cf3f9cb907b8a786ec33c399585642e1858a74ecdf3fc6f69300eb058097daeecbb7a4c7cf98d655f463326162ae068779fb652eb6a1d8212187f54', 'Ramachandra Rao', 'ramachandra@citizen.gov.in', '9856112233', 'citizen', NULL, 8, 1);

INSERT INTO `shop_stocks` (`shop_id`, `commodity_id`, `current_stock`, `min_threshold`, `last_replenished_at`) VALUES
(1, 1, 850.00, 150.00, NOW()),
(1, 2, 620.00, 150.00, NOW()),
(1, 3, 180.00, 50.00, NOW()),
(1, 4, 120.00, 40.00, NOW()),
(1, 5, 210.00, 50.00, NOW()),
(2, 1, 500.00, 150.00, NOW()),
(2, 2, 85.00, 150.00, NOW()),
(2, 3, 95.00, 50.00, NOW()),
(2, 4, 30.00, 40.00, NOW()),
(2, 5, 140.00, 50.00, NOW());
