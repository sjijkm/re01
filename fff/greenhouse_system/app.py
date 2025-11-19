import os
import random
import time
import threading
import hashlib
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
from functools import wraps
import pandas as pd
from io import BytesIO
from models.greenhouse import Greenhouse
from models.planting import Planting

# 导入配置和模型
from config import Config
from database import Database
from models.sensor import SensorData
from models.device import DeviceStatus
from models.alert import Alert
from models.user import User
from models.schedule import ScheduledTask
# removed SensorCalibration import — calibration feature disabled

# 初始化Flask应用
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# 初始化新模型
greenhouse_model = Greenhouse()
planting_model = Planting()

# 初始化数据库和模型
db = Database()
sensor_model = SensorData()
device_model = DeviceStatus()
alert_model = Alert()
user_model = User()
schedule_model = ScheduledTask()
# calibration_model removed

# 二维码登录已移除


# 全局模板上下文注入：确保模板中能使用到大棚统计信息，避免变量未定义错误
@app.context_processor
def inject_greenhouse_stats():
    try:
        houses = greenhouse_model.get_all() or []
        total_area = sum([house.get('area') or 0 for house in houses]) if houses else 0
        return {
            'greenhouse_total': len(houses),
            'greenhouse_area': total_area
        }
    except Exception:
        return {
            'greenhouse_total': 0,
            'greenhouse_area': 0
        }

# 设备列表
DEVICES = ['heater', 'cooler', 'fan', 'light', 'co2_generator', 'water_pump']


# 登录装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


# 管理员权限装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'status': 'error', 'message': '权限不足'}), 403
        return f(*args, **kwargs)

    return decorated_function


# 传感器模拟类
class Sensors:
    def __init__(self):
        self.temperature = 25.0
        self.humidity = 60.0
        self.light_intensity = 5000.0
        self.co2_level = 600.0

    def read(self):
        # 模拟数据波动
        self.temperature += random.uniform(-0.5, 0.5)
        self.humidity += random.uniform(-1.0, 1.0)
        self.light_intensity += random.uniform(-200, 200)
        self.co2_level += random.uniform(-20, 20)

        # 限制范围
        self.temperature = max(10.0, min(40.0, self.temperature))
        self.humidity = max(30.0, min(90.0, self.humidity))
        self.light_intensity = max(0.0, min(10000.0, self.light_intensity))
        self.co2_level = max(300.0, min(1500.0, self.co2_level))

        # 不再应用校准，直接返回原始读数（保留一位小数）
        return {
            'temperature': round(self.temperature, 1),
            'humidity': round(self.humidity, 1),
            'light_intensity': round(self.light_intensity, 1),
            'co2_level': round(self.co2_level, 1)
        }


# 控制逻辑类
class ControlSystem:
    def __init__(self):
        self.auto_mode = True  # 默认自动模式

    def get_thresholds(self):
        """获取所有阈值参数"""
        thresholds = {}
        for param in Config.THRESHOLDS.keys():
            res = db.fetch_one("SELECT value FROM thresholds WHERE param = %s", (param,))
            thresholds[param] = res['value'] if res else Config.THRESHOLDS[param]
        return thresholds

    def adjust_devices(self):
        """根据传感器数据自动调节设备"""
        if not self.auto_mode:
            return

        data = sensor_model.get_latest()
        if not data:
            return

        thresholds = self.get_thresholds()
        alerts = []

        # 温度控制
        if data['temperature'] < thresholds['temp_min']:
            device_model.update('heater', 'ON')
            device_model.update('cooler', 'OFF')
            if data['temperature'] < thresholds['temp_min'] - 2:
                alerts.append(('temperature', data['temperature'], f'温度过低: {data["temperature"]}°C'))
        elif data['temperature'] > thresholds['temp_max']:
            device_model.update('heater', 'OFF')
            device_model.update('cooler', 'ON')
            device_model.update('fan', 'ON')
            if data['temperature'] > thresholds['temp_max'] + 2:
                alerts.append(('temperature', data['temperature'], f'温度过高: {data["temperature"]}°C'))
        else:
            device_model.update('heater', 'OFF')
            device_model.update('cooler', 'OFF')
            device_model.update('fan', 'OFF')

        # 湿度控制
        if data['humidity'] < thresholds['humidity_min']:
            device_model.update('water_pump', 'ON')
            if data['humidity'] < thresholds['humidity_min'] - 5:
                alerts.append(('humidity', data['humidity'], f'湿度过低: {data["humidity"]}%'))
        elif data['humidity'] > thresholds['humidity_max']:
            device_model.update('water_pump', 'OFF')
            device_model.update('fan', 'ON')
            if data['humidity'] > thresholds['humidity_max'] + 5:
                alerts.append(('humidity', data['humidity'], f'湿度过高: {data["humidity"]}%'))
        else:
            device_model.update('water_pump', 'OFF')

        # 光照控制
        if data['light_intensity'] < thresholds['light_min']:
            device_model.update('light', 'ON')
            if data['light_intensity'] < thresholds['light_min'] - 1000:
                alerts.append(('light_intensity', data['light_intensity'], f'光照不足: {data["light_intensity"]} lux'))
        elif data['light_intensity'] > thresholds['light_max']:
            device_model.update('light', 'OFF')
            if data['light_intensity'] > thresholds['light_max'] + 1000:
                alerts.append(('light_intensity', data['light_intensity'], f'光照过强: {data["light_intensity"]} lux'))
        else:
            device_model.update('light', 'OFF')

        # CO2控制
        if data['co2_level'] < thresholds['co2_min']:
            device_model.update('co2_generator', 'ON')
            if data['co2_level'] < thresholds['co2_min'] - 100:
                alerts.append(('co2_level', data['co2_level'], f'CO2浓度过低: {data["co2_level"]} ppm'))
        elif data['co2_level'] > thresholds['co2_max']:
            device_model.update('co2_generator', 'OFF')
            device_model.update('fan', 'ON')
            if data['co2_level'] > thresholds['co2_max'] + 100:
                alerts.append(('co2_level', data['co2_level'], f'CO2浓度过高: {data["co2_level"]} ppm'))
        else:
            device_model.update('co2_generator', 'OFF')

        # 插入报警
        for alert in alerts:
            alert_model.insert(alert[0], alert[1], alert[2])


# 初始化系统
sensors = Sensors()
control = ControlSystem()


# 系统主循环
def system_loop():
    last_check_minute = None
    last_cleanup_day = None
    BATCH_DELETE_SIZE = 500
    while True:
        # 读取传感器数据并保存
        data = sensors.read()
        sensor_model.insert(data['temperature'], data['humidity'], data['light_intensity'], data['co2_level'])

        # 定时任务检查（每分钟）
        current_minute = datetime.now().strftime('%H:%M')
        if current_minute != last_check_minute:
            last_check_minute = current_minute
            tasks = schedule_model.get_all_tasks()
            for task in tasks:
                if task['enabled'] and task['schedule_time'] == current_minute:
                    device_model.update(task['device_name'], task['action'])
                    print(f"执行定时任务: {task['device_name']} -> {task['action']}")

        # 自动调节设备
        control.adjust_devices()

        # 每天分批清理过期传感器数据（按 Config.SENSOR_RETENTION_DAYS），避免长时间锁表
        try:
            today = datetime.now().date()
            if last_cleanup_day != today:
                last_cleanup_day = today
                days = int(getattr(Config, 'SENSOR_RETENTION_DAYS', 7))
                while True:
                    # 使用子查询包装以支持 LIMIT 在 DELETE 中
                    delete_sql = (
                        "DELETE FROM sensor_data WHERE id IN ("
                        "SELECT id FROM (SELECT id FROM sensor_data WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY) LIMIT %s) tmp)"
                    )
                    ok = db.execute_query(delete_sql, (days, BATCH_DELETE_SIZE))
                    if not ok:
                        print('分批清理传感器数据时发生错误')
                        break
                    # 检查是否还有超过保留期的数据
                    rem = db.fetch_one(
                        "SELECT COUNT(*) AS cnt FROM sensor_data WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)",
                        (days,)
                    )
                    if not rem or rem.get('cnt', 0) == 0:
                        print(f"已完成传感器数据分批清理（保留最近 {days} 天）")
                        break
                    # 否则继续下一批
        except Exception as e:
            print('传感器数据清理异常:', e)

        time.sleep(Config.UPDATE_INTERVAL)


# 启动系统循环线程
threading.Thread(target=system_loop, daemon=True).start()


# 路由定义
@app.route('/')
@login_required
def index():
    latest_data = sensor_model.get_latest()
    devices = device_model.get_all()
    unhandled_alerts = alert_model.get_unhandled(5)
    houses = greenhouse_model.get_all()
    return render_template('index.html',
                           latest_data=latest_data,
                           devices=devices,
                           alerts=unhandled_alerts,
                           houses=houses,
                           username=session['username'],
                           role=session['role'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.md5(request.form['password'].encode()).hexdigest()
        user = user_model.get_by_username(username)

        if user and user['password'] == password:
            session['username'] = username
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='用户名或密码错误')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))


@app.route('/status')
@login_required
def status():
    latest_data = sensor_model.get_latest()
    devices = device_model.get_all()
    thresholds = control.get_thresholds()
    return render_template('status.html',
                           latest_data=latest_data,
                           devices=devices,
                           thresholds=thresholds,
                           auto_mode=control.auto_mode,
                           username=session['username'],
                           role=session['role'])


@app.route('/control')
@login_required
def device_control():
    devices = device_model.get_all()
    return render_template('control.html',
                           devices=devices,
                           auto_mode=control.auto_mode,
                           username=session['username'],
                           role=session['role'])


@app.route('/history')
@login_required
def history():
    hours = request.args.get('hours', 24, type=int)
    data = sensor_model.get_by_time_range(hours)
    return render_template('history.html',
                           data=data,
                           hours=hours,
                           username=session['username'],
                           role=session['role'])


@app.route('/alerts')
@login_required
def alerts():
    status = request.args.get('status', 'all')
    if status == 'unhandled':
        alerts = alert_model.get_unhandled()
    elif status == 'handled':
        alerts = alert_model.get_handled()
    else:
        alerts = alert_model.get_all()
    return render_template('alerts.html',
                           alerts=alerts,
                           current_status=status,
                           username=session['username'],
                           role=session['role'])


@app.route('/api/get-mode-status')
@login_required
def get_mode_status():
    """返回当前控制模式（用于前端定时刷新）"""
    return jsonify({
        'status': 'success',
        'auto_mode': control.auto_mode
    })
# 新增：获取最新数据的路由（解决 BuildError）
@app.route('/api/get-latest-data')
@login_required
def get_latest_data():
    """返回最新的传感器数据，用于前端实时刷新"""
    latest_data = sensor_model.get_latest()
    devices = device_model.get_all()
    if latest_data:
        return jsonify({'status': 'success', 'sensor_data': latest_data, 'devices': devices})
    return jsonify({'status': 'error', 'message': '暂无数据'}), 404


# 设备控制API
@app.route('/api/device/<device_name>/<status>', methods=['POST'])
@login_required
def set_device_status(device_name, status):
    if device_name not in DEVICES or status not in ['ON', 'OFF']:
        return jsonify({'status': 'error', 'message': '参数错误'})

    # 非管理员在自动模式下不能操作
    if control.auto_mode and session['role'] != 'admin':
        return jsonify({'status': 'error', 'message': '自动模式下仅管理员可操作'})

    success = device_model.update(device_name, status)
    return jsonify({'status': 'success' if success else 'error'})


# 切换控制模式API
@app.route('/api/toggle-mode', methods=['POST'])
@admin_required
def toggle_mode():
    control.auto_mode = not control.auto_mode
    # 同步到数据库（确保数据库操作成功）
    success = db.execute_query("UPDATE control_mode SET auto_mode = %s", (control.auto_mode,))
    if success:
        return jsonify({'status': 'success', 'auto_mode': control.auto_mode})
    else:
        # 数据库更新失败时回滚
        control.auto_mode = not control.auto_mode
        return jsonify({'status': 'error', 'message': '模式切换失败'})


# 更新阈值API
@app.route('/api/update-threshold/<param>', methods=['POST'])
@admin_required
def update_threshold(param):
    if param not in Config.THRESHOLDS:
        return jsonify({'status': 'error', 'message': '参数错误'})

    try:
        value = float(request.form['value'])
        db.execute_query("UPDATE thresholds SET value = %s WHERE param = %s", (value, param))
        return jsonify({'status': 'success'})
    except:
        return jsonify({'status': 'error', 'message': '数值无效'})


# 处理报警API
@app.route('/api/handle-alert/<int:alert_id>', methods=['POST'])
@login_required
def handle_alert(alert_id):
    success = alert_model.handle(alert_id, session['username'])
    return jsonify({'status': 'success' if success else 'error'})


# 数据导出路由
@app.route('/export-data')
@login_required
def export_data():
    # 限制最大导出时长为7天（168小时），避免数据量过大
    hours = min(request.args.get('hours', 24, type=int), 168)  # 最多导出7天数据
    data = sensor_model.get_by_time_range(hours)

    if not data:
        return jsonify({'status': 'error', 'message': '无数据可导出'})

    # 优化：只保留需要的列，减少数据处理量
    df = pd.DataFrame(data)[['timestamp', 'temperature', 'humidity', 'light_intensity', 'co2_level']]
    df.columns = ['记录时间', '温度(°C)', '湿度(%)', '光照(lux)', 'CO2(ppm)']

    # 优化：使用更高效的文件格式（如 CSV 作为备选，速度比 Excel 快）
    output = BytesIO()
    # 仅在数据量小时用 Excel，数据量大时自动切换为 CSV
    if len(df) < 10000:  # 1万条以内用 Excel
        with pd.ExcelWriter(output, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, index=False, sheet_name=f'近{hours}小时数据')
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = f'温室数据_{hours}h.xlsx'
    else:  # 超过1万条用 CSV（速度快10倍以上）
        df.to_csv(output, index=False, encoding='utf-8-sig')
        content_type = 'text/csv'
        filename = f'温室数据_{hours}h.csv'

    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.headers['Content-Type'] = content_type
    return response


# 定时任务路由
@app.route('/schedule')
@login_required
def schedule():
    tasks = schedule_model.get_all_tasks()
    return render_template('schedule.html',
                           tasks=tasks,
                           username=session['username'],
                           role=session['role'])


@app.route('/api/schedule/add', methods=['POST'])
@admin_required
def add_schedule():
    device = request.form['device']
    action = request.form['action']
    time = request.form['time']
    # 基本校验
    if device not in DEVICES or action not in ['ON', 'OFF']:
        return jsonify({'status': 'error', 'message': '参数错误'}), 400

    # 验证时间格式 HH:MM（00-23:59）
    if not isinstance(time, str) or not re.match(r'^\d{2}:\d{2}$', time):
        return jsonify({'status': 'error', 'message': '时间格式应为 HH:MM'}), 400
    hh, mm = time.split(':')
    try:
        hh_i = int(hh)
        mm_i = int(mm)
        if hh_i < 0 or hh_i > 23 or mm_i < 0 or mm_i > 59:
            return jsonify({'status': 'error', 'message': '时间超出范围 (00:00-23:59)'}), 400
    except ValueError:
        return jsonify({'status': 'error', 'message': '时间格式无效'}), 400

    success = schedule_model.add_task(device, action, time)
    return jsonify({'status': 'success' if success else 'error'})


@app.route('/api/schedule/toggle/<int:task_id>', methods=['POST'])
@admin_required
def toggle_schedule(task_id):
    success = schedule_model.toggle_task_status(task_id)
    return jsonify({'status': 'success' if success else 'error'})


@app.route('/api/schedule/delete/<int:task_id>', methods=['POST'])
@admin_required
def delete_schedule(task_id):
    success = schedule_model.delete_task(task_id)
    return jsonify({'status': 'success' if success else 'error'})


# 传感器校准路由
@app.route('/calibration')
@login_required
def calibration():
    # 该功能已移除
    return "传感器校准功能已被移除", 404


# calibration update endpoint removed


# 用户管理路由
@app.route('/users')
@admin_required
def user_management():
    users = user_model.get_all()
    admin_users = [user for user in users if user.get('role') == 'admin']
    normal_users = [user for user in users if user.get('role') == 'user']
    return render_template('users.html',
                           users=users,
                           admin_users=admin_users,
                           normal_users=normal_users,
                           username=session['username'],
                           role=session['role'])


@app.route('/api/user/add', methods=['POST'])
@admin_required
def add_user():
    username = request.form.get('username')
    raw_password = request.form.get('password')
    role = request.form.get('role')

    if not username or not raw_password:
        return jsonify({'status': 'error', 'message': '用户名和密码不能为空'}), 400

    # 用户名规则：3-30位 字母数字 下划线或短横
    if not re.match(r'^[A-Za-z0-9_-]{3,30}$', username):
        return jsonify({'status': 'error', 'message': '用户名应为3-30位字母数字或-_'}), 400

    # 密码长度校验
    if len(raw_password) < 6:
        return jsonify({'status': 'error', 'message': '密码长度至少6位'}), 400

    # 角色校验
    if role not in ('admin', 'user'):
        return jsonify({'status': 'error', 'message': '角色无效'}), 400

    # 已存在检查
    if user_model.get_by_username(username):
        return jsonify({'status': 'error', 'message': '用户名已存在'}), 409

    # 存储哈希后的密码
    hashed = hashlib.md5(raw_password.encode()).hexdigest()
    success = user_model.add(username, hashed, role)
    if success:
        return jsonify({'status': 'success', 'message': '用户添加成功'}), 201
    return jsonify({'status': 'error', 'message': '添加失败'}), 500


# 大棚列表页
@app.route('/greenhouses')
@login_required
def greenhouses():
    houses = greenhouse_model.get_all()
    return render_template('greenhouses.html',
                           houses=houses,
                           username=session['username'],
                           role=session['role'])


# 大棚详情页（监控+种植记录）
@app.route('/greenhouse/<int:house_id>')
@login_required
def greenhouse_detail(house_id):
    house = greenhouse_model.get_by_id(house_id)
    if not house:
        return "大棚不存在", 404

    # 获取该大棚的传感器数据（修改传感器模型支持大棚ID）
    latest_data = sensor_model.get_latest_by_house(house_id)
    plantings = planting_model.get_by_greenhouse(house_id)

    return render_template('greenhouse_detail.html',
                           house=house,
                           latest_data=latest_data,
                           plantings=plantings,
                           username=session['username'],
                           role=session['role'])


@app.route('/api/sensor-data/<int:house_id>')
@login_required
def get_sensor_data_for_house(house_id):
    hours = request.args.get('hours', 24, type=int)
    data = sensor_model.get_by_time_range_and_house(hours, house_id)
    return jsonify({'status': 'success', 'data': data})


@app.route('/api/greenhouse/<int:house_id>/crops', methods=['GET', 'POST'])
@login_required
def manage_greenhouse_crops(house_id):
    if request.method == 'GET':
        crops = greenhouse_model.get_allowed_crops(house_id)
        return jsonify({'status': 'success', 'data': crops})

    # POST requires admin
    if session.get('role') != 'admin':
        return jsonify({'status': 'error', 'message': '权限不足'}), 403

    body = request.get_json() or {}
    selected_values = body.get('crops', [])
    catalog = {item['value']: item['name'] for item in Config.CROP_LIBRARY}
    prepared = [
        {'value': value, 'name': catalog.get(value, value)}
        for value in selected_values if value in catalog
    ]
    greenhouse_model.update_allowed_crops(house_id, prepared)
    return jsonify({'status': 'success'})


@app.route('/api/planting/add', methods=['POST'])
@admin_required
def add_planting():
    data = request.form
    try:
        greenhouse_id = int(data.get('greenhouse_id'))
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': '大棚ID无效'})

    if not data.get('plant_date'):
        return jsonify({'status': 'error', 'message': '种植日期必填'})

    # 严格校验种植日期格式 YYYY-MM-DD，防止用户只输入数字
    try:
        plant_date_str = data.get('plant_date')
        datetime.strptime(plant_date_str, '%Y-%m-%d')
    except Exception:
        return jsonify({'status': 'error', 'message': '种植日期格式应为 YYYY-MM-DD'}), 400

    payload = {
        'greenhouse_id': greenhouse_id,
        'crop_type': data.get('crop_type'),
        'variety': data.get('variety'),
        'plant_date': data.get('plant_date'),
        'expected_harvest': data.get('expected_harvest') or None,
        'notes': data.get('notes', '')
    }
    success = planting_model.add(payload)
    return jsonify({'status': 'success' if success else 'error'})


@app.route('/api/planting/<int:planting_id>/delete', methods=['POST'])
@admin_required
def delete_planting(planting_id):
    success = planting_model.delete(planting_id)
    return jsonify({'status': 'success' if success else 'error'})


@app.route('/api/planting/<int:planting_id>/care-log', methods=['POST'])
@login_required
def add_care_log(planting_id):
    planting = planting_model.get_by_id(planting_id)
    if not planting:
        return jsonify({'status': 'error', 'message': '记录不存在'}), 404

    payload = request.get_json() or {}
    action_type = payload.get('action_type')
    detail = payload.get('detail', '')
    if action_type not in ['watering', 'fertilizing', 'temperature', 'disease']:
        return jsonify({'status': 'error', 'message': '无效操作类型'}), 400

    success = planting_model.add_care_log(
        greenhouse_id=planting['greenhouse_id'],
        planting_id=planting_id,
        action_type=action_type,
        detail=detail,
        performed_by=session['username']
    )
    if success:
        care_logs = planting_model.get_care_logs(planting['greenhouse_id'])
        return jsonify({'status': 'success', 'logs': care_logs})
    return jsonify({'status': 'error'})


@app.route('/api/greenhouse/<int:house_id>/care-logs')
@login_required
def get_care_logs(house_id):
    logs = planting_model.get_care_logs(house_id, limit=30)
    return jsonify({'status': 'success', 'data': logs})


# 新增大棚API（管理员）
@app.route('/api/greenhouse/add', methods=['POST'])
@admin_required
def add_greenhouse():
    data = request.form
    name = data.get('name')
    location = data.get('location')
    area_raw = data.get('area')
    try:
        if area_raw is None or area_raw == '':
            raise ValueError('面积不能为空')
        area = float(area_raw)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'面积无效: {e}'}), 400

    # 去重检查：按 name 或者 code（如果有）检查已有大棚
    try:
        code = data.get('code') or None
        if code:
            exists = greenhouse_model.db.fetch_one(
                "SELECT id FROM greenhouses WHERE name = %s OR code = %s LIMIT 1",
                (name, code)
            )
        else:
            exists = greenhouse_model.db.fetch_one(
                "SELECT id FROM greenhouses WHERE name = %s LIMIT 1",
                (name,)
            )
        if exists:
            return jsonify({'status': 'error', 'message': '相同名称或编码的大棚已存在'}), 409

        success = greenhouse_model.add(name, location, area, code=code)
        return jsonify({'status': 'success' if success else 'error'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# 二维码登录相关接口已删除

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)