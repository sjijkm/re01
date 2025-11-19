from database import Database

class User:
    def __init__(self):
        self.db = Database()

    def get_by_username(self, username):
        """通过用户名获取用户信息"""
        query = '''
        SELECT * FROM users
        WHERE username = %s
        '''
        return self.db.fetch_one(query, (username,))

    def get_all(self):
        """获取所有用户"""
        query = '''
        SELECT id, username, role, created_at FROM users
        ORDER BY created_at DESC
        '''
        return self.db.fetch_data(query)

    def add(self, username, password, role='user'):
        """添加新用户"""
        query = '''
        INSERT INTO users (username, password, role)
        VALUES (%s, %s, %s)
        '''
        return self.db.execute_query(query, (username, password, role))

    def update_password(self, username, new_password):
        """更新用户密码"""
        query = '''
        UPDATE users
        SET password = %s
        WHERE username = %s
        '''
        return self.db.execute_query(query, (new_password, username))