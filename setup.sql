-- ===============================================
-- Setup Database for Bookstore Mobile App Login
-- ===============================================

USE book_store;

-- สร้างตาราง user_login
CREATE TABLE IF NOT EXISTS user_login (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- เพิ่มข้อมูลผู้ใช้ทดสอบ
INSERT IGNORE INTO user_login (username, password) VALUES 
('admin', 'admin123'),
('user', 'password'),
('test', 'test123');

-- ตรวจสอบข้อมูล
SELECT * FROM user_login;

-- แสดงโครงสร้างตาราง
DESCRIBE user_login;
