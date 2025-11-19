from database import Database

class Planting:
    def __init__(self):
        self.db = Database()

    def get_by_greenhouse(self, greenhouse_id):
        """获取指定大棚的种植记录"""
        return self.db.fetch_data(
            """SELECT * FROM plantings 
               WHERE greenhouse_id = %s 
               ORDER BY plant_date DESC""",
            (greenhouse_id,)
        )

    def add(self, data):
        """新增种植记录"""
        return self.db.execute_query(
            """INSERT INTO plantings 
               (greenhouse_id, crop_type, variety, plant_date, expected_harvest, notes)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (data['greenhouse_id'], data['crop_type'], data['variety'],
             data['plant_date'], data['expected_harvest'], data['notes'])
        )

    def update_record(self, planting_id, data):
        """更新种植记录"""
        return self.db.execute_query(
            """UPDATE plantings SET 
               crop_type = %s,
               variety = %s,
               plant_date = %s,
               expected_harvest = %s,
               status = %s,
               notes = %s
               WHERE id = %s""",
            (data['crop_type'], data['variety'], data['plant_date'],
             data['expected_harvest'], data['status'], data['notes'], planting_id)
        )

    def update_harvest(self, planting_id, actual_harvest, yield_kg, status='harvested'):
        """更新收获信息"""
        return self.db.execute_query(
            """UPDATE plantings 
               SET actual_harvest = %s, yield_kg = %s, status = %s 
               WHERE id = %s""",
            (actual_harvest, yield_kg, status, planting_id)
        )

    def delete(self, planting_id):
        """删除种植记录"""
        return self.db.execute_query(
            "DELETE FROM plantings WHERE id = %s",
            (planting_id,)
        )

    def get_by_id(self, planting_id):
        return self.db.fetch_one(
            "SELECT * FROM plantings WHERE id = %s",
            (planting_id,)
        )

    def add_care_log(self, greenhouse_id, action_type, detail, performed_by, planting_id=None):
        """新增养护记录"""
        return self.db.execute_query(
            """INSERT INTO plant_care_logs 
               (greenhouse_id, planting_id, action_type, detail, performed_by)
               VALUES (%s, %s, %s, %s, %s)""",
            (greenhouse_id, planting_id, action_type, detail, performed_by)
        )

    def get_care_logs(self, greenhouse_id, limit=20):
        """获取指定大棚的养护记录"""
        return self.db.fetch_data(
            """SELECT pcl.*, p.crop_type 
               FROM plant_care_logs pcl
               LEFT JOIN plantings p ON pcl.planting_id = p.id
               WHERE pcl.greenhouse_id = %s
               ORDER BY pcl.created_at DESC
               LIMIT %s""",
            (greenhouse_id, limit)
        )