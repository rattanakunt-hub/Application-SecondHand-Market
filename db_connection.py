import pymysql

def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='P@ssw0rd',  # Replace with your actual password
        database='book_store',
        cursorclass=pymysql.cursors.DictCursor
    )