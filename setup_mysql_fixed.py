import pymysql
from pathlib import Path

passwords_to_try = ["P@ssw0rd", "", "password", "123456", "root"]
conn = None

for pwd in passwords_to_try:
    try:
        conn = pymysql.connect(
            host="127.0.0.1",
            user="root",
            password=pwd,
            port=3306,
            autocommit=False
        )
        print(f"Connected to MySQL Server with password: {'(empty)' if not pwd else pwd}")
        break
    except Exception as e:
        continue

if not conn:
    print("Failed to connect to MySQL with any password")
    exit(1)

sql_file = Path(__file__).parent / "setup_mysql.sql"

with open(sql_file, 'r', encoding='utf-8') as f:
    sql_content = f.read()

cursor = conn.cursor()
statement_count = 0
for statement in sql_content.split(';'):
    statement = statement.strip()
    if statement and not statement.startswith('--'):
        try:
            cursor.execute(statement)
            statement_count += 1
            print(f"Executed statement {statement_count}: {statement[:60]}...")
        except Exception as e:
            print(f"Error executing statement: {e}")

conn.commit()
conn.close()
print(f"Database setup completed! Executed {statement_count} statements.")
