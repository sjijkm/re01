from database import Database
from datetime import datetime

class Alert:
    def __init__(self):
        self.db = Database()

    def insert(self, param, value, message):
        """插入新报警"""
        query = '''
        INSERT INTO alerts (param, value, message)
        VALUES (%s, %s, %s)
        '''
        return self.db.execute_query(query, (param, value, message))

    def get_all(self, limit=100):
        """获取所有报警"""
        query = '''
        SELECT * FROM alerts
        ORDER BY created_at DESC
        LIMIT %s
        '''
        return self.db.fetch_data(query, (limit,))

    def get_unhandled(self, limit=100):
        """获取未处理报警"""
        query = '''
        SELECT * FROM alerts
        WHERE status = 'unhandled'
        ORDER BY created_at DESC
        LIMIT %s
        '''
        return self.db.fetch_data(query, (limit,))

    def get_handled(self, limit=100):
        """获取已处理报警"""
        query = '''
        SELECT * FROM alerts
        WHERE status = 'handled'
        ORDER BY created_at DESC
        LIMIT %s
        '''
        return self.db.fetch_data(query, (limit,))

    def handle(self, alert_id, handler):
        """标记报警为已处理"""
        query = '''
        UPDATE alerts
        SET status = 'handled',
            handler = %s,
            handled_at = %s
        WHERE id = %s AND status = 'unhandled'
        '''
        return self.db.execute_query(
            query,
            (handler, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), alert_id)
        )