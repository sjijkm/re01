#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import datetime
import threading
import time
import random
import logging
from config import DB_CONFIG  # 数据库配置单独存放

# 日志文件路径（项目根目录下的greenhouse.log）
log_file = 'greenhouse.log'
# 检查日志文件所在目录是否存在，不存在则创建
log_dir = os.path.dirname(log_file)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志（删除 filename 参数，只通过 handlers 指定输出方式）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # 文件日志处理器（写入日志文件）
        logging.FileHandler(log_file, encoding='utf-8'),  # 指定编码避免中文乱码
        # 控制台日志处理器（输出到命令行）
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
CORS(app)  # 允许跨域请求


# 数据库连接工具
def get_db_connection():
    """获取数据库连接"""
    connection = None
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        logging.error(f"数据库连接错误: {e}")
    return connection


# 首页路由
@app.route('/')
def index():
    return render_template('index.html')


# 传感器数据API
@app.route('/api/sensor-data', methods=['GET'])
def get_sensor_data():
    """获取传感器数据，支持按数量筛选"""
    count = request.args.get('count', 20, type=int)
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT {count}")
        data = cursor.fetchall()
        # 转换时间格式为ISO
        for item in data:
            item['timestamp'] = item['timestamp'].isoformat()
        return jsonify(data[::-1])  # 按时间正序返回
    except Error as e:
        logging.error(f"查询传感器数据错误: {e}")
        return jsonify({"error": "查询数据失败"}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


# 设备控制API
@app.route('/api/devices', methods=['GET'])
def get_devices():
    """获取所有设备状态"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM devices")
        devices = cursor.fetchall()
        return jsonify(devices)
    except Error as e:
        logging.error(f"查询设备错误: {e}")
        return jsonify({"error": "查询设备失败"}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@app.route('/api/devices/<int:device_id>', methods=['PUT'])
def toggle_device(device_id):
    """切换设备状态"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        # 获取当前状态
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT status FROM devices WHERE id = %s", (device_id,))
        device = cursor.fetchone()
        if not device:
            return jsonify({"error": "设备不存在"}), 404

        # 切换状态
        new_status = not device['status']
        cursor.execute(
            "UPDATE devices SET status = %s, last_changed = CURRENT_TIMESTAMP WHERE id = %s",
            (new_status, device_id)
        )
        connection.commit()
        logging.info(f"设备 {device_id} 状态切换为 {new_status}")
        return jsonify({"status": new_status})
    except Error as e:
        connection.rollback()
        logging.error(f"更新设备状态错误: {e}")
        return jsonify({"error": "更新设备状态失败"}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


# 任务管理API
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取所有任务"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tasks ORDER BY create_time DESC")
        tasks = cursor.fetchall()
        return jsonify(tasks)
    except Error as e:
        logging.error(f"查询任务错误: {e}")
        return jsonify({"error": "查询任务失败"}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@app.route('/api/tasks', methods=['POST'])
def add_task():
    """添加新任务"""
    data = request.json
    if not data or 'content' not in data:
        return jsonify({"error": "任务内容不能为空"}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "INSERT INTO tasks (content) VALUES (%s)",
            (data['content'],)
        )
        connection.commit()
        task_id = cursor.lastrowid
        cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
        new_task = cursor.fetchone()
        logging.info(f"添加新任务: {data['content']}")
        return jsonify(new_task), 201
    except Error as e:
        connection.rollback()
        logging.error(f"添加任务错误: {e}")
        return jsonify({"error": "添加任务失败"}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@app.route('/api/tasks/<int:task_id>/complete', methods=['PUT'])
def complete_task(task_id):
    """标记任务为完成"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE tasks SET completed = 1, complete_time = CURRENT_TIMESTAMP WHERE id = %s",
            (task_id,)
        )
        connection.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "任务不存在"}), 404
        logging.info(f"任务 {task_id} 标记为完成")
        return jsonify({"success": True})
    except Error as e:
        connection.rollback()
        logging.error(f"完成任务错误: {e}")
        return jsonify({"error": "更新任务失败"}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


# 提醒管理API
@app.route('/api/reminders', methods=['GET'])
def get_reminders():
    """获取所有提醒"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM reminders ORDER BY reminder_time")
        reminders = cursor.fetchall()
        return jsonify(reminders)
    except Error as e:
        logging.error(f"查询提醒错误: {e}")
        return jsonify({"error": "查询提醒失败"}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@app.route('/api/reminders', methods=['POST'])
def add_reminder():
    """添加新提醒"""
    data = request.json
    required = ['title', 'reminder_time']
    if not data or not all(k in data for k in required):
        return jsonify({"error": "标题和提醒时间不能为空"}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """INSERT INTO reminders (title, content, reminder_time) 
               VALUES (%s, %s, %s)""",
            (data['title'], data.get('content', ''), data['reminder_time'])
        )
        connection.commit()
        reminder_id = cursor.lastrowid
        cursor.execute("SELECT * FROM reminders WHERE id = %s", (reminder_id,))
        new_reminder = cursor.fetchone()
        logging.info(f"添加新提醒: {data['title']}")
        return jsonify(new_reminder), 201
    except Error as e:
        connection.rollback()
        logging.error(f"添加提醒错误: {e}")
        return jsonify({"error": "添加提醒失败"}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@app.route('/api/reminders/<int:reminder_id>', methods=['DELETE'])
def delete_reminder(reminder_id):
    """删除提醒"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = %s", (reminder_id,))
        connection.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "提醒不存在"}), 404
        logging.info(f"删除提醒: {reminder_id}")
        return jsonify({"success": True})
    except Error as e:
        connection.rollback()
        logging.error(f"删除提醒错误: {e}")
        return jsonify({"error": "删除提醒失败"}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


# 系统设置API
@app.route('/api/settings', methods=['GET'])
def get_settings():
    """获取系统设置"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM settings")
        settings = cursor.fetchall()
        return jsonify({s['param']: {'min': s['min_val'], 'max': s['max_val']} for s in settings})
    except Error as e:
        logging.error(f"查询设置错误: {e}")
        return jsonify({"error": "查询设置失败"}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@app.route('/api/settings', methods=['PUT'])
def update_settings():
    """更新系统设置"""
    data = request.json
    if not data:
        return jsonify({"error": "设置数据不能为空"}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        cursor = connection.cursor()
        for param, values in data.items():
            cursor.execute(
                "UPDATE settings SET min_val = %s, max_val = %s WHERE param = %s",
                (values['min'], values['max'], param)
            )
        connection.commit()
        logging.info("系统设置已更新")
        return jsonify({"success": True})
    except Error as e:
        connection.rollback()
        logging.error(f"更新设置错误: {e}")
        return jsonify({"error": "更新设置失败"}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


# 传感器数据模拟线程
class SensorSimulator:
    def __init__(self, interval=10):
        self.interval = interval  # 数据采集间隔(秒)
        self.running = False
        self.thread = None

        # 基础模拟值
        self.base_temp = 25.0
        self.base_humidity = 75.0
        self.base_light = 15.0
        self.base_co2 = 600.0

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._simulate, daemon=True)
        self.thread.start()
        logging.info("传感器模拟器已启动")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        logging.info("传感器模拟器已停止")

    def _simulate(self):
        while self.running:
            # 生成带波动的模拟数据
            temp = self.base_temp + random.uniform(-1.5, 1.5)
            humidity = self.base_humidity + random.uniform(-5, 5)
            light = self.base_light + random.uniform(-3, 3)
            co2 = self.base_co2 + random.uniform(-100, 100)

            # 限制范围
            temp = max(10.0, min(40.0, temp))
            humidity = max(30.0, min(100.0, humidity))
            light = max(0.0, min(30.0, light))
            co2 = max(300.0, min(2000.0, co2))

            # 保存到数据库
            self._save_to_db(temp, humidity, light, co2)

            # 模拟环境缓慢变化
            self.base_temp += random.uniform(-0.1, 0.1)
            self.base_humidity += random.uniform(-0.3, 0.3)

            # 模拟昼夜光照变化
            hour = datetime.datetime.now().hour
            if 6 <= hour < 18:  # 白天
                self.base_light = max(10.0, min(20.0, self.base_light + random.uniform(-0.5, 0.5)))
            else:  # 晚上
                self.base_light = max(0.0, min(5.0, self.base_light + random.uniform(-0.3, 0.3)))

            self.base_co2 += random.uniform(-5, 5)

            time.sleep(self.interval)

    def _save_to_db(self, temp, humidity, light, co2):
        connection = get_db_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO sensor_data (temperature, humidity, light, co2) VALUES (%s, %s, %s, %s)",
                (temp, humidity, light, co2)
            )
            connection.commit()
            logging.debug(f"保存传感器数据: 温度={temp}, 湿度={humidity}, 光照={light}, CO2={co2}")
        except Error as e:
            connection.rollback()
            logging.error(f"保存传感器数据错误: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()


# 提醒检查线程
class ReminderChecker:
    def __init__(self, interval=10):
        self.interval = interval  # 检查间隔(秒)
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._check, daemon=True)
        self.thread.start()
        logging.info("提醒检查器已启动")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        logging.info("提醒检查器已停止")

    def _check(self):
        while self.running:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            connection = get_db_connection()
            if not connection:
                time.sleep(self.interval)
                continue

            try:
                cursor = connection.cursor()
                # 查找已到时间但未触发的提醒
                cursor.execute(
                    "UPDATE reminders SET triggered = 1 WHERE reminder_time <= %s AND triggered = 0",
                    (now,)
                )
                connection.commit()
                if cursor.rowcount > 0:
                    logging.info(f"触发 {cursor.rowcount} 个提醒")
            except Error as e:
                connection.rollback()
                logging.error(f"检查提醒错误: {e}")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()

            time.sleep(self.interval)


class AutoController:
    def __init__(self, interval=30):
        self.interval = interval  # 控制间隔(秒)
        self.running = False
        self.thread = None

    def start(self):
        """启动自动控制线程"""
        self.running = True
        self.thread = threading.Thread(target=self._control, daemon=True)
        self.thread.start()
        logging.info("自动控制器已启动")

    def stop(self):
        """停止自动控制线程"""
        self.running = False
        if self.thread:
            self.thread.join()
        logging.info("自动控制器已停止")

    def _control(self):
        """自动控制逻辑实现"""
        while self.running:
            # 获取最新传感器数据
            latest_data = self._get_latest_sensor_data()
            if not latest_data:
                time.sleep(self.interval)
                continue

            # 获取阈值设置
            settings = self._get_settings()
            if not settings:
                time.sleep(self.interval)
                continue

            # 根据规则控制设备
            self._adjust_devices(latest_data, settings)
            time.sleep(self.interval)

    # 其他方法保持不变...

    def _get_latest_sensor_data(self):
        connection = get_db_connection()
        if not connection:
            return None

        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 1")
            return cursor.fetchone()
        except Error as e:
            logging.error(f"获取最新传感器数据错误: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def _get_settings(self):
        connection = get_db_connection()
        if not connection:
            return None

        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM settings")
            return {s['param']: {'min': s['min_val'], 'max': s['max_val']} for s in cursor.fetchall()}
        except Error as e:
            logging.error(f"获取设置错误: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def _adjust_devices(self, data, settings):
        connection = get_db_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor(dictionary=True)

            # 温度控制
            if data['temperature'] > settings['temperature']['max']:
                cursor.execute("UPDATE devices SET status = 1, last_changed = CURRENT_TIMESTAMP WHERE name = '通风扇'")
                cursor.execute(
                    "UPDATE devices SET status = 0, last_changed = CURRENT_TIMESTAMP WHERE name = '加热系统'")
            elif data['temperature'] < settings['temperature']['min']:
                cursor.execute("UPDATE devices SET status = 0, last_changed = CURRENT_TIMESTAMP WHERE name = '通风扇'")
                cursor.execute(
                    "UPDATE devices SET status = 1, last_changed = CURRENT_TIMESTAMP WHERE name = '加热系统'")

            # 光照控制
            if data['light'] > settings['light']['max']:
                cursor.execute("UPDATE devices SET status = 1, last_changed = CURRENT_TIMESTAMP WHERE name = '遮阳网'")
                cursor.execute("UPDATE devices SET status = 0, last_changed = CURRENT_TIMESTAMP WHERE name = '补光灯'")
            elif data['light'] < settings['light']['min']:
                cursor.execute("UPDATE devices SET status = 0, last_changed = CURRENT_TIMESTAMP WHERE name = '遮阳网'")
                cursor.execute("UPDATE devices SET status = 1, last_changed = CURRENT_TIMESTAMP WHERE name = '补光灯'")

            # 湿度控制
            if data['humidity'] < settings['humidity']['min']:
                cursor.execute(
                    "UPDATE devices SET status = 1, last_changed = CURRENT_TIMESTAMP WHERE name = '灌溉系统'")
            elif data['humidity'] > settings['humidity']['max']:
                cursor.execute(
                    "UPDATE devices SET status = 0, last_changed = CURRENT_TIMESTAMP WHERE name = '灌溉系统'")

            connection.commit()
        except Error as e:
            connection.rollback()
            logging.error(f"自动控制设备错误: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()


if __name__ == '__main__':
    # 初始化并启动后台线程
    simulator = SensorSimulator(interval=10)
    reminder_checker = ReminderChecker(interval=10)
    auto_controller = AutoController(interval=30)

    try:
        simulator.start()
        reminder_checker.start()
        auto_controller.start()
        app.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        simulator.stop()
        reminder_checker.stop()
        auto_controller.stop()