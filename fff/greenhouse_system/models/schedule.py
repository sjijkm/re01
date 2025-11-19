from database import Database

class ScheduledTask:
    def __init__(self):
        self.db = Database()

    def add_task(self, device_name, action, schedule_time):
        query = '''
        INSERT INTO scheduled_tasks (device_name, action, schedule_time)
        VALUES (%s, %s, %s)
        '''
        return self.db.execute_query(query, (device_name, action, schedule_time))

    def get_all_tasks(self):
        return self.db.fetch_data("SELECT * FROM scheduled_tasks ORDER BY schedule_time")

    def toggle_task_status(self, task_id):
        query = "UPDATE scheduled_tasks SET enabled = NOT enabled WHERE id = %s"
        return self.db.execute_query(query, (task_id,))

    def delete_task(self, task_id):
        return self.db.execute_query("DELETE FROM scheduled_tasks WHERE id = %s", (task_id,))