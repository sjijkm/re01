from database import Database
from datetime import datetime, timedelta
class SensorData:
    def __init__(self):
        self.db = Database()

    def insert(self, temperature, humidity, light_intensity, co2_level):
        """插入传感器数据"""
        query = '''
        INSERT INTO sensor_data (temperature, humidity, light_intensity, co2_level)
        VALUES (%s, %s, %s, %s)
        '''
        return self.db.execute_query(query, (temperature, humidity, light_intensity, co2_level))

    def get_recent(self, limit=100):
        """获取最近的传感器数据"""
        query = '''
        SELECT * FROM sensor_data
        ORDER BY timestamp DESC
        LIMIT %s
        '''
        return self.db.fetch_data(query, (limit,))

    def get_by_time_range(self, hours):
        """按小时范围返回数据。若范围较大（>48 小时），按小时聚合平均值以减小点数便于绘图。"""
        hours = int(hours)
        if hours <= 48:
            query = '''
            SELECT timestamp, temperature, humidity, light_intensity, co2_level 
            FROM sensor_data 
            WHERE timestamp >= NOW() - INTERVAL %s HOUR 
            ORDER BY timestamp ASC
            '''
            return self.db.fetch_data(query, (hours,))
        else:
            # 按小时聚合，返回每小时的平均值，timestamp 使用小时起点
            query = '''
            SELECT DATE_FORMAT(timestamp, '%%Y-%%m-%%d %%H:00:00') AS timestamp,
                   AVG(temperature) AS temperature,
                   AVG(humidity) AS humidity,
                   AVG(light_intensity) AS light_intensity,
                   AVG(co2_level) AS co2_level
            FROM sensor_data
            WHERE timestamp >= NOW() - INTERVAL %s HOUR
            GROUP BY YEAR(timestamp), MONTH(timestamp), DAY(timestamp), HOUR(timestamp)
            ORDER BY timestamp ASC
            '''
            return self.db.fetch_data(query, (hours,))

    def get_latest(self):
        """获取最新的传感器数据"""
        query = '''
        SELECT * FROM sensor_data
        ORDER BY timestamp DESC
        LIMIT 1
        '''
        return self.db.fetch_one(query)

    # 在 SensorData 类中添加
    def get_latest_by_house(self, greenhouse_id):
        """获取指定大棚的最新数据"""
        query = '''
        SELECT * FROM sensor_data
        WHERE greenhouse_id = %s
        ORDER BY timestamp DESC
        LIMIT 1
        '''
        return self.db.fetch_one(query, (greenhouse_id,))

    def get_by_time_range_and_house(self, hours, greenhouse_id):
        """获取指定大棚的时间范围数据"""
        query = '''
        SELECT timestamp, temperature, humidity, light_intensity, co2_level 
        FROM sensor_data 
        WHERE greenhouse_id = %s AND timestamp >= NOW() - INTERVAL %s HOUR 
        ORDER BY timestamp ASC
        '''
        return self.db.fetch_data(query, (greenhouse_id, hours))