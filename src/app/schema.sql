CREATE TABLE IF NOT EXISTS users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(100) NOT NULL,
  role ENUM('boss','admin','employee') NOT NULL DEFAULT 'employee',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance (
  att_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  work_date DATE NOT NULL,
  check_in DATETIME NULL,
  check_out DATETIME NULL,
  status ENUM('open','done') NOT NULL DEFAULT 'open',
  note VARCHAR(255) NULL,
  duty_zone ENUM('港口','近海','外海') NULL,
  sea_state ENUM('平靜','輕浪','中浪','大浪') NULL,
  vessel_id VARCHAR(20) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_att_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  CONSTRAINT uq_user_date UNIQUE (user_id, work_date),
  INDEX idx_user_date (user_id, work_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS leaves (
  leave_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  date_from DATE NOT NULL,
  date_to DATE NOT NULL,
  leave_type ENUM('personal','sick','other') NOT NULL DEFAULT 'personal',
  reason VARCHAR(255) NULL,
  status ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
  decided_by INT NULL,
  decided_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_leave_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  CONSTRAINT fk_leave_decider FOREIGN KEY (decided_by) REFERENCES users(user_id),
  INDEX idx_leave_user (user_id),
  INDEX idx_leave_range (date_from, date_to),
  INDEX idx_leave_status (status)
) ENGINE=InnoDB;

-- Default accounts (seeded)
-- boss: can manage self/admin/employee
-- admin: can manage employees only
-- employee: read-only for account management

-- Default accounts (seeded)
-- boss: can manage boss/admin/employee (including self)
INSERT INTO users(username, password_hash, full_name, role, is_active) VALUES
('boss1', '$2y$10$74/Dh9n/MLxTKopstTwvvuyb/XR0lY6.QK/oNrIgYp6IgdnTacovW', 'Boss', 'boss', 1); -- password: boss1234

-- admin: can manage employee only
INSERT INTO users(username, password_hash, full_name, role, is_active) VALUES
('admin1', '$2y$10$KRC4JX.5wL3WQdt5Wy/Wv.4Jweva.Wm9C1MYOIHbgtYeQGCau3JvC', 'Admin', 'admin', 1); -- password: admin1234

-- employee: view-only for account management
INSERT INTO users(username, password_hash, full_name, role, is_active) VALUES
('em1', '$2y$10$XjWHhrwlPp3VRcD41gApOu/YTs0MQD.7Gfrtl9KVsqlMasoyvIbGG', 'Employee', 'employee', 1); -- password: em1234
