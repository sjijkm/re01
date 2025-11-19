from database import Database

class SensorCalibration:
    def __init__(self):
        self.db = Database()

    def get_calibration(self, sensor_type):
        return self.db.fetch_one('''
        SELECT offset, scale FROM sensor_calibration WHERE sensor_type = %s
        ''', (sensor_type,))

    def update_calibration(self, sensor_type, offset, scale):
        return self.db.execute_query('''
        UPDATE sensor_calibration SET offset = %s, scale = %s WHERE sensor_type = %s
        ''', (offset, scale, sensor_type))

    def get_all_calibrations(self):
        return self.db.fetch_data("SELECT * FROM sensor_calibration")

    def reset_calibration(self, sensor_type):
        """重置指定传感器的校准参数为默认值（offset=0, scale=1）"""
        return self.db.execute_query('''
        UPDATE sensor_calibration SET offset = 0.0, scale = 1.0 WHERE sensor_type = %s
        ''', (sensor_type,))