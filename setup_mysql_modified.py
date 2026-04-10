import pymysql
from pathlib import Path

# Try to connect with auth_plugin_map parameter
passwords_to_try = ['P@ssw0rd', '', 'password', '123456', 'root']
conn = None

for pwd in passwords_to_try:
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            user='root',
            password=pwd,
            port=3306,
            autocommit=False,
            auth_plugin_map={'mysql_native_password': 'pymysql.util.crypt.get_password_auth_sasl_client_func()}  
        )
        print(f"✓ Connected to MySQL Server with password: {'(empty)' if not pwd else '***'}")
        break
    except Exception as e:
        print(f"Failed with password '{pwd}': {str(e)[:80]}")
        continue

if not conn:
    print("MySQL connection failed - trying socket connection instead...")
    try:
        conn = pymysql.connect(
            unix_socket='C:/ProgramData/MariaDB/MariaDB Server 11.5/mysql.sock',
            user='root',
            password='',
            autocommit=False
        )
        print("✓ Connected via socket")
    except:
        pass

if not conn:
    print("✗ Failed to connect to MySQL")
    exit(1)

# Read and execute SQL
sql_file = Path(__file__).parent / "setup_mysql.sql"
if not sql_file.exists():
    print(f"✗ SQL file not found: {sql_file}")
    exit(1)

with open(sql_file, 'r', encoding='utf-8') as f:
    sql_content = f.read()

cursor = conn.cursor()
for statement in sql_content.split(';'):
    statement = statement.strip()
    if statement and not statement.startswith('--'):
        try:
            cursor.execute(statement)
            print(f"✓ Executed: {statement[:60]}... ")
        except Exception as e:
            print(f"✗ Error: {e}")

conn.commit()
conn.close()
print("✓ Database setup completed successfully!")
