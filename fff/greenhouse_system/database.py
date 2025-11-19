import mysql.connector
from mysql.connector import Error
import os
from config import Config


class Database:
    def __init__(self):
        self.host = Config.DB_HOST
        self.database = Config.DB_NAME
        self.user = Config.DB_USER
        self.password = Config.DB_PASSWORD
        self.port = Config.DB_PORT
        self.connection = None
        self.cursor = None
        self.connect()
        self.initialize_tables()  # 初始化数据表

    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            if self.connection.is_connected():
                self.cursor = self.connection.cursor(dictionary=True)  # 返回字典格式
                print("数据库连接成功")
        except Error as e:
            print(f"数据库连接失败: {e}")

    def execute_query(self, query, params=None):
        """执行 INSERT/UPDATE/DELETE 语句"""
        if not self.connection or not self.connection.is_connected():
            self.connect()  # 重新连接

        try:
            self.cursor.execute(query, params or ())
            self.connection.commit()
            return True
        except Error as e:
            print(f"执行查询错误: {e}")
            self.connection.rollback()
            return False

    def fetch_data(self, query, params=None):
        """执行 SELECT 语句，返回多条数据"""
        if not self.connection or not self.connection.is_connected():
            self.connect()  # 重新连接

        try:
            self.cursor.execute(query, params or ())
            return self.cursor.fetchall()
        except Error as e:
            print(f"查询数据错误: {e}")
            return []

    def fetch_one(self, query, params=None):
        """执行 SELECT 语句，返回单条数据"""
        if not self.connection or not self.connection.is_connected():
            self.connect()  # 重新连接

        try:
            self.cursor.execute(query, params or ())
            return self.cursor.fetchone()
        except Error as e:
            print(f"查询单条数据错误: {e}")
            return None

    def initialize_tables(self):
        """初始化所有数据表（如果不存在）"""
        if not self.connection or not self.connection.is_connected():
            self.connect()

        # 1. 用户表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(100) NOT NULL,
            role ENUM('admin', 'user') DEFAULT 'user',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # 2. 传感器数据表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            temperature FLOAT NOT NULL,
            humidity FLOAT NOT NULL,
            light_intensity FLOAT NOT NULL,
            co2_level FLOAT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # 3. 设备状态表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_status (
            id INT AUTO_INCREMENT PRIMARY KEY,
            device_name VARCHAR(50) NOT NULL UNIQUE,
            status ENUM('ON', 'OFF') DEFAULT 'OFF',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        ''')

        # 4. 报警信息表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            parameter VARCHAR(50) NOT NULL,
            value FLOAT NOT NULL,
            message TEXT NOT NULL,
            handled BOOLEAN DEFAULT FALSE,
            handled_by VARCHAR(50),
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # 5. 控制模式表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS control_mode (
            id INT PRIMARY KEY DEFAULT 1,
            auto_mode BOOLEAN DEFAULT TRUE,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        ''')
        # 初始化控制模式记录（如果不存在）
        self.cursor.execute("INSERT IGNORE INTO control_mode (id) VALUES (1)")

        # 6. 阈值参数表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS thresholds (
            param VARCHAR(50) PRIMARY KEY,
            value FLOAT NOT NULL
        )
        ''')

        # 7. 定时任务表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            device_name VARCHAR(50) NOT NULL,
            action ENUM('ON', 'OFF') NOT NULL,
            schedule_time VARCHAR(5) NOT NULL,  # 格式 HH:MM
            enabled BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # 8. 传感器校准表 — 已移除，功能不再初始化此表

        # 9. 大棚信息表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS greenhouses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            location VARCHAR(200),
            area FLOAT,
            status ENUM('active', 'inactive') DEFAULT 'active',
            code VARCHAR(50),
            purpose VARCHAR(100),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        ''')

        # 新增：插入默认大棚（确保至少有一条记录）
        self.cursor.execute('''
            INSERT IGNORE INTO greenhouses (id, name, location, area) 
            VALUES (1, '一号大棚', '默认位置', 100.0)
            ''')  # IGNORE 确保重复插入时不报错

        # 9.1 确保 code、purpose 字段存在（兼容旧版本）
        self.cursor.execute('''
           SELECT COUNT(*) AS cnt
           FROM information_schema.COLUMNS
           WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'greenhouses' AND COLUMN_NAME = 'code'
        ''', (self.database,))
        if self.cursor.fetchone()['cnt'] == 0:
            self.cursor.execute("ALTER TABLE greenhouses ADD COLUMN code VARCHAR(50)")

        self.cursor.execute('''
           SELECT COUNT(*) AS cnt
           FROM information_schema.COLUMNS
           WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'greenhouses' AND COLUMN_NAME = 'purpose'
        ''', (self.database,))
        if self.cursor.fetchone()['cnt'] == 0:
            self.cursor.execute("ALTER TABLE greenhouses ADD COLUMN purpose VARCHAR(100)")

        # 10. 种植记录表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS plantings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            greenhouse_id INT NOT NULL,
            crop_type VARCHAR(100) NOT NULL,
            variety VARCHAR(100),
            plant_date DATE NOT NULL,
            expected_harvest DATE,
            actual_harvest DATE,
            status ENUM('growing', 'harvested', 'failed') DEFAULT 'growing',
            yield_kg FLOAT,
            notes TEXT,
            FOREIGN KEY (greenhouse_id) REFERENCES greenhouses(id)
        )
        ''')

        # 11. 大棚可种植作物表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS greenhouse_crops (
            id INT AUTO_INCREMENT PRIMARY KEY,
            greenhouse_id INT NOT NULL,
            crop_value VARCHAR(50) NOT NULL,
            crop_name VARCHAR(100) NOT NULL,
            UNIQUE KEY uniq_greenhouse_crop (greenhouse_id, crop_value),
            FOREIGN KEY (greenhouse_id) REFERENCES greenhouses(id) ON DELETE CASCADE
        )
        ''')

        # 12. 作物养护记录表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS plant_care_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            greenhouse_id INT NOT NULL,
            planting_id INT,
            action_type ENUM('watering','fertilizing','temperature','disease') NOT NULL,
            detail TEXT,
            performed_by VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (greenhouse_id) REFERENCES greenhouses(id) ON DELETE CASCADE,
            FOREIGN KEY (planting_id) REFERENCES plantings(id) ON DELETE SET NULL
        )
        ''')

        # 11. 为 sensor_data 表添加大棚关联字段和外键（保持之前的修改）
        # 11.1 检查并添加 greenhouse_id 字段（兼容旧版本）
        self.cursor.execute('''
           SELECT COUNT(*) AS cnt 
           FROM information_schema.COLUMNS 
           WHERE TABLE_SCHEMA = %s 
             AND TABLE_NAME = 'sensor_data' 
             AND COLUMN_NAME = 'greenhouse_id'
           ''', (self.database,))
        column_exists = self.cursor.fetchone()['cnt'] > 0

        if not column_exists:
            self.cursor.execute('''
               ALTER TABLE sensor_data
               ADD COLUMN greenhouse_id INT DEFAULT 1  # 默认关联到 ID=1 的大棚
               ''')

        # 11.2 检查并添加外键
        self.cursor.execute('''
           SELECT COUNT(*) AS cnt 
           FROM information_schema.KEY_COLUMN_USAGE 
           WHERE TABLE_SCHEMA = %s 
             AND TABLE_NAME = 'sensor_data' 
             AND COLUMN_NAME = 'greenhouse_id' 
             AND CONSTRAINT_NAME = 'fk_sensor_greenhouse'
           ''', (self.database,))
        foreign_key_exists = self.cursor.fetchone()['cnt'] > 0

        if not foreign_key_exists:
            self.cursor.execute('''
               ALTER TABLE sensor_data
               ADD CONSTRAINT fk_sensor_greenhouse
               FOREIGN KEY (greenhouse_id) REFERENCES greenhouses(id)
               ''')

        self.connection.commit()
        # 根据配置决定是否删除旧的校准表（默认保留，避免误删）
        try:
            if getattr(Config, 'REMOVE_CALIBRATION_TABLE', False):
                self.cursor.execute('DROP TABLE IF EXISTS sensor_calibration')
                self.connection.commit()
                print('已删除旧的 sensor_calibration 表（如存在）')
            else:
                print('未启用删除 sensor_calibration（保留原表以防数据丢失）')
        except Exception as e:
            print('删除 sensor_calibration 时发生错误:', e)

        print("数据表初始化完成")

    def close(self):
        """关闭数据库连接"""
        if self.connection and self.connection.is_connected():
            self.cursor.close()
            self.connection.close()
            print("数据库连接已关闭")

    def __del__(self):
        """对象销毁时关闭连接"""
        self.close()