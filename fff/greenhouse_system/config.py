import os


class Config:
    # 数据库配置
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASSWORD = '123456'  # 替换为你的MySQL密码
    DB_NAME = 'greenhouse'
    DB_PORT = 3306

    # Flask配置
    # 优先从环境变量读取 SECRET_KEY（生产环境应在环境中固定该值），否则回退到随机值（重启会话会失效）
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    DEBUG = True

    # 系统配置
    UPDATE_INTERVAL = 5  # 数据更新间隔(秒)
    # 传感器数据保留天数（超过将被定期清理）
    SENSOR_RETENTION_DAYS = 7

    # 环境参数阈值
    THRESHOLDS = {
        'temp_min': 18.0,
        'temp_max': 28.0,
        'humidity_min': 50.0,
        'humidity_max': 80.0,
        'light_min': 3000.0,
        'light_max': 8000.0,
        'co2_min': 400.0,
        'co2_max': 1000.0
    }

    # 可选作物清单（用于大棚作物管理）
    CROP_LIBRARY = [
        {'name': '小番茄', 'value': 'tomato'},
        {'name': '黄瓜', 'value': 'cucumber'},
        {'name': '生菜', 'value': 'lettuce'},
        {'name': '草莓', 'value': 'strawberry'},
        {'name': '辣椒', 'value': 'pepper'},
        {'name': '西兰花', 'value': 'broccoli'},
        {'name': '菠菜', 'value': 'spinach'}
    ]

    # 控制是否在初始化时删除旧的 sensor_calibration 表（默认 False）
    # 可通过环境变量 REMOVE_CALIBRATION_TABLE=1 或 True 启用
    REMOVE_CALIBRATION_TABLE = os.environ.get('REMOVE_CALIBRATION_TABLE', '0').lower() in ('1', 'true', 'yes')