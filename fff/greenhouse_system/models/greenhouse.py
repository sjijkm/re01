from database import Database

class Greenhouse:
    def __init__(self):
        self.db = Database()

    def get_all(self):
        """获取所有大棚"""
        return self.db.fetch_data("SELECT * FROM greenhouses ORDER BY id")

    def get_by_id(self, greenhouse_id):
        """通过ID获取大棚"""
        return self.db.fetch_one(
            "SELECT * FROM greenhouses WHERE id = %s",
            (greenhouse_id,)
        )

    def add(self, name, location, area, code=None, purpose=None):
        """新增大棚"""
        return self.db.execute_query(
            "INSERT INTO greenhouses (name, location, area, code, purpose) VALUES (%s, %s, %s, %s, %s)",
            (name, location, area, code, purpose)
        )

    def update_status(self, greenhouse_id, status):
        """更新大棚状态"""
        return self.db.execute_query(
            "UPDATE greenhouses SET status = %s WHERE id = %s",
            (status, greenhouse_id)
        )

    def update_info(self, greenhouse_id, name, location, area, code=None, purpose=None):
        """更新大棚基础信息"""
        return self.db.execute_query(
            """UPDATE greenhouses 
               SET name = %s, location = %s, area = %s, code = %s, purpose = %s 
               WHERE id = %s""",
            (name, location, area, code, purpose, greenhouse_id)
        )

    def delete(self, greenhouse_id):
        """删除大棚"""
        return self.db.execute_query(
            "DELETE FROM greenhouses WHERE id = %s",
            (greenhouse_id,)
        )

    def get_allowed_crops(self, greenhouse_id):
        """获取指定大棚允许种植的作物列表"""
        rows = self.db.fetch_data(
            "SELECT crop_value, crop_name FROM greenhouse_crops WHERE greenhouse_id = %s ORDER BY crop_name",
            (greenhouse_id,)
        )
        return rows or []

    def update_allowed_crops(self, greenhouse_id, crops):
        """更新大棚允许种植的作物"""
        self.db.execute_query("DELETE FROM greenhouse_crops WHERE greenhouse_id = %s", (greenhouse_id,))
        for crop in crops:
            self.db.execute_query(
                "INSERT INTO greenhouse_crops (greenhouse_id, crop_value, crop_name) VALUES (%s, %s, %s)",
                (greenhouse_id, crop['value'], crop['name'])
            )
        return True