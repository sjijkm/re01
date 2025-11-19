from database import Database

class DeviceStatus:
    def __init__(self):
        self.db = Database()
        self.initialize_devices()

    def initialize_devices(self):
        """初始化设备（如不存在则创建）"""
        devices = [
            'heater', 'cooler', 'fan', 'light', 'co2_generator', 'water_pump'
        ]
        for device in devices:
            # 检查设备是否已存在
            result = self.db.fetch_one(
                "SELECT id FROM device_status WHERE device_name = %s ORDER BY timestamp DESC LIMIT 1",
                (device,)
            )
            if not result:
                # 初始状态设为OFF
                self.db.execute_query(
                    "INSERT INTO device_status (device_name, status) VALUES (%s, 'OFF')",
                    (device,)
                )

    def update(self, device_name, status):
        """更新设备状态"""
        query = '''
        INSERT INTO device_status (device_name, status)
        VALUES (%s, %s)
        '''
        return self.db.execute_query(query, (device_name, status))

    def get_all(self):
        """获取所有设备的最新状态"""
        query = '''
        SELECT d1.* FROM device_status d1
        INNER JOIN (
            SELECT device_name, MAX(timestamp) AS max_time
            FROM device_status
            GROUP BY device_name
        ) d2 ON d1.device_name = d2.device_name AND d1.timestamp = d2.max_time
        ORDER BY d1.device_name
        '''
        return self.db.fetch_data(query)

    def get_by_name(self, device_name):
        """获取指定设备的最新状态"""
        query = '''
        SELECT * FROM device_status
        WHERE device_name = %s
        ORDER BY timestamp DESC
        LIMIT 1
        '''
        return self.db.fetch_one(query, (device_name,))