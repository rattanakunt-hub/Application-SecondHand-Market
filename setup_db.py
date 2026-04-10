"""
Script to set up user_login table and add test data
"""
import sqlite3

conn = sqlite3.connect("book_store.db")

cur = conn.cursor()

# Create user_login table if not exists
cur.execute("""
    CREATE TABLE IF NOT EXISTS user_login (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
print("✅ Table 'user_login' created/exists")

# Add test users
test_users = [
    ("admin", "admin123"),
    ("user", "password"),
    ("test", "test123"),
]

for username, password in test_users:
    try:
        cur.execute(
            "INSERT INTO user_login (username, password) VALUES (?, ?)",
            (username, password)
        )
        print(f"✅ Added user: {username}")
    except sqlite3.IntegrityError:
        print(f"⚠️  User {username} already exists")

conn.commit()
conn.close()

print("✅ Database setup complete!")
