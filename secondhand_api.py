import pymysql
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymysql.cursors import DictCursor
from starlette.concurrency import run_in_threadpool

app = FastAPI(title="SecondHand API")

# อนุญาตให้แอป Flet เชื่อมต่อข้ามเครื่องได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ข้อมูลเชื่อมต่อ MariaDB (IP: 172.20.127.86)
DB_CONFIG = {
    "host": "172.27.189.98",
    "port": 3306,
    "user": "root",
    "password": "P@ssw0rd",
    "db": "secondhand_shop",
    "cursorclass": DictCursor
}


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    full_name: str = Field(..., min_length=1)
    phone: str = ""
    user_role: str = Field(default="buyer")


class LogoutRequest(BaseModel):
    username: str = ""


class InquiryRequest(BaseModel):
    product_id: int
    buyer_username: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class SellerReviewRequest(BaseModel):
    reviewer_username: str = Field(..., min_length=1)
    rating: float = Field(..., ge=1, le=5)
    comment: str = ""


class ProductUpsertRequest(BaseModel):
    product_name: str = Field(..., min_length=1)
    price: float = Field(..., ge=0)
    description: str = ""
    image_url: str = ""
    condition_label: str = "มือสอง"
    category: str = "อื่นๆ"
    seller_username: str = Field(..., min_length=1)
    seller_rating: float = Field(default=0, ge=0, le=5)


class ProductSoldRequest(BaseModel):
    is_sold: bool


def _sync_bootstrap_schema():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_login (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL,
                    full_name VARCHAR(150) NULL,
                    phone VARCHAR(50) NULL,
                    user_role VARCHAR(20) NOT NULL DEFAULT 'buyer',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    product_name VARCHAR(255) NOT NULL,
                    price DECIMAL(10,2) NOT NULL DEFAULT 0,
                    description TEXT NULL,
                    image_url TEXT NULL,
                    condition_label VARCHAR(100) NULL,
                    category VARCHAR(100) NULL,
                    seller_username VARCHAR(100) NULL,
                    seller_rating DECIMAL(3,2) NULL,
                    is_sold TINYINT(1) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS inquiries (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    product_id INT NOT NULL,
                    buyer_username VARCHAR(100) NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS seller_reviews (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    seller_username VARCHAR(100) NOT NULL,
                    reviewer_username VARCHAR(100) NOT NULL,
                    rating DECIMAL(3,2) NOT NULL,
                    comment TEXT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            cur.execute("SHOW COLUMNS FROM products")
            product_cols = {row["Field"] for row in cur.fetchall()}
            alter_sql = {
                "description": "ALTER TABLE products ADD COLUMN description TEXT NULL",
                "image_url": "ALTER TABLE products ADD COLUMN image_url TEXT NULL",
                "condition_label": "ALTER TABLE products ADD COLUMN condition_label VARCHAR(100) NULL",
                "category": "ALTER TABLE products ADD COLUMN category VARCHAR(100) NULL",
                "seller_username": "ALTER TABLE products ADD COLUMN seller_username VARCHAR(100) NULL",
                "seller_rating": "ALTER TABLE products ADD COLUMN seller_rating DECIMAL(3,2) NULL",
                "is_sold": "ALTER TABLE products ADD COLUMN is_sold TINYINT(1) NOT NULL DEFAULT 0",
                "created_at": "ALTER TABLE products ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            }
            for col_name, sql in alter_sql.items():
                if col_name not in product_cols:
                    cur.execute(sql)

            cur.execute("SHOW COLUMNS FROM user_login")
            login_cols = {row["Field"] for row in cur.fetchall()}
            if "full_name" not in login_cols:
                cur.execute("ALTER TABLE user_login ADD COLUMN full_name VARCHAR(150) NULL")
            if "phone" not in login_cols:
                cur.execute("ALTER TABLE user_login ADD COLUMN phone VARCHAR(50) NULL")
            if "user_role" not in login_cols:
                cur.execute("ALTER TABLE user_login ADD COLUMN user_role VARCHAR(20) NOT NULL DEFAULT 'Buyer'")
        conn.commit()
    finally:
        conn.close()

def _sync_exec(query: str, params=None, *, fetchone=False, fetchall=False, commit=False):
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            if commit: conn.commit()
            if fetchone: return cur.fetchone()
            if fetchall: return cur.fetchall()
            return {"lastrowid": cur.lastrowid}
    finally:
        conn.close()

async def db_exec(query: str, params=None, **kwargs):
    return await run_in_threadpool(_sync_exec, query, params, **kwargs)


async def table_exists(table_name: str) -> bool:
    row = await db_exec(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
        """,
        (DB_CONFIG["db"], table_name),
        fetchone=True,
    )
    return bool(row and int(row.get("cnt", 0)) > 0)


async def resolve_user_identity(user_key: str):
    normalized = (user_key or "").strip()
    user_row = await db_exec(
        """
        SELECT id, username, COALESCE(full_name, '') AS full_name, COALESCE(user_role, 'Seller') AS user_role
        FROM user_login
        WHERE LOWER(TRIM(username)) = LOWER(TRIM(%s))
           OR LOWER(TRIM(COALESCE(full_name, ''))) = LOWER(TRIM(%s))
        LIMIT 1
        """,
        (normalized, normalized),
        fetchone=True,
    )

    aliases = [normalized]
    if user_row:
        username = (user_row.get("username") or "").strip()
        full_name = (user_row.get("full_name") or "").strip()
        if username:
            aliases.append(username)
        if full_name:
            aliases.append(full_name)

    dedup_aliases = []
    seen = set()
    for value in aliases:
        key = value.strip().lower()
        if key and key not in seen:
            seen.add(key)
            dedup_aliases.append(value.strip())

    canonical = user_row["username"].strip() if user_row and user_row.get("username") else normalized
    return canonical, dedup_aliases, user_row


async def resolve_seller_identity(seller_key: str):
    return await resolve_user_identity(seller_key)


@app.on_event("startup")
async def startup_bootstrap_schema():
    await run_in_threadpool(_sync_bootstrap_schema)

# --- API สำหรับ Login ---
@app.post("/login")
async def login(request: LoginRequest):
    # ค้นหาข้อมูลผู้ใช้รวมถึงฟิลด์ใหม่ (full_name, user_role)
    row = await db_exec(
        "SELECT password, full_name, user_role FROM user_login WHERE username=%s",
        (request.username,),
        fetchone=True
    )
    
    if not row or row["password"] != request.password:
        # แสดงข้อความ Error ตามรูปภาพที่คุณแจ้ง
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    
    role_value = (row.get("user_role") or "Buyer").strip()
    return {
        "success": True,
        "username": request.username,
        "full_name": row["full_name"] if row["full_name"] else request.username,
        "role": role_value,
    }


@app.post("/register")
async def register(request: RegisterRequest):
    username = request.username.strip()
    password = request.password.strip()
    full_name = request.full_name.strip()
    phone = request.phone.strip()
    user_role = request.user_role.strip().lower()

    if user_role not in {"buyer", "seller"}:
        raise HTTPException(status_code=400, detail="role ต้องเป็น buyer หรือ seller")

    existing = await db_exec(
        "SELECT id FROM user_login WHERE LOWER(TRIM(username)) = LOWER(TRIM(%s))",
        (username,),
        fetchone=True,
    )
    if existing:
        raise HTTPException(status_code=409, detail="ชื่อผู้ใช้นี้ถูกใช้งานแล้ว")

    result = await db_exec(
        """
        INSERT INTO user_login (username, password, full_name, phone, user_role)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (username, password, full_name, phone, user_role.title()),
        commit=True,
    )

    return {
        "success": True,
        "username": username,
        "full_name": full_name,
        "role": user_role.title(),
        "id": result["lastrowid"],
    }


@app.post("/logout")
async def logout(request: LogoutRequest):
    return {
        "success": True,
        "message": "ออกจากระบบสำเร็จ",
        "username": request.username,
    }

# --- API สำหรับดึงข้อมูลสินค้า ---
@app.get("/products")
async def get_products(
    search: str = Query(default=""),
    category: str = Query(default=""),
    include_sold: bool = Query(default=False),
):
    where = []
    params = []

    if not include_sold:
        where.append("COALESCE(is_sold, 0) = 0")
    if search:
        where.append(
            "(" \
            "LOWER(TRIM(product_name)) LIKE %s OR " \
            "LOWER(TRIM(COALESCE(description, ''))) LIKE %s OR " \
            "LOWER(TRIM(COALESCE(category, ''))) LIKE %s OR " \
            "LOWER(TRIM(COALESCE(seller_username, ''))) LIKE %s" \
            ")"
        )
        search_value = f"%{search.strip().lower()}%"
        params.extend([search_value, search_value, search_value, search_value])
    if category:
        where.append("LOWER(TRIM(COALESCE(category, ''))) = LOWER(TRIM(%s))")
        params.append(category.strip())

    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    return await db_exec(
        """
        SELECT
            id,
            product_name,
            price,
            COALESCE(description, '') AS description,
            COALESCE(image_url, '') AS image_url,
            COALESCE(condition_label, 'มือสอง') AS condition_label,
            COALESCE(category, 'อื่นๆ') AS category,
            COALESCE(seller_username, 'unknown') AS seller_username,
            COALESCE(seller_rating, 0) AS seller_rating,
            COALESCE(is_sold, 0) AS is_sold,
            created_at
        FROM products
        """
        + where_sql
        + " ORDER BY id DESC",
        tuple(params),
        fetchall=True,
    )


@app.get("/products/{product_id}")
async def get_product_detail(product_id: int):
    row = await db_exec(
        """
        SELECT
            id,
            product_name,
            price,
            COALESCE(description, '') AS description,
            COALESCE(image_url, '') AS image_url,
            COALESCE(condition_label, 'มือสอง') AS condition_label,
            COALESCE(category, 'อื่นๆ') AS category,
            COALESCE(seller_username, 'unknown') AS seller_username,
            COALESCE(seller_rating, 0) AS seller_rating,
            COALESCE(is_sold, 0) AS is_sold,
            created_at
        FROM products
        WHERE id=%s
        """,
        (product_id,),
        fetchone=True,
    )
    if not row:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    return row


@app.get("/sellers/{seller_username}")
async def get_seller_profile(seller_username: str):
    canonical, aliases, user_row = await resolve_seller_identity(seller_username)
    alias_placeholders = ",".join(["%s"] * len(aliases))
    alias_lower = tuple(alias.lower() for alias in aliases)

    product_stats = await db_exec(
        f"SELECT COUNT(*) AS product_count FROM products WHERE TRIM(LOWER(seller_username)) IN ({alias_placeholders})",
        alias_lower,
        fetchone=True,
    )

    seller_reviews_stats = await db_exec(
        f"""
        SELECT
            COUNT(*) AS review_count,
            COALESCE(AVG(rating), 0) AS average_rating
        FROM seller_reviews
        WHERE TRIM(LOWER(seller_username)) IN ({alias_placeholders})
        """,
        alias_lower,
        fetchone=True,
    )
    total_review_count = int((seller_reviews_stats or {}).get("review_count", 0))
    avg_rating_total = float((seller_reviews_stats or {}).get("average_rating", 0) or 0)

    if not user_row and int(product_stats["product_count"]) == 0 and total_review_count == 0:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ขาย")

    return {
        "username": canonical,
        "full_name": user_row["full_name"] if user_row and user_row["full_name"] else canonical,
        "user_role": user_row["user_role"] if user_row and user_row["user_role"] else "Seller",
        "product_count": int(product_stats["product_count"]),
        "review_count": int(total_review_count),
        "average_rating": float(avg_rating_total),
    }


@app.get("/sellers/{seller_username}/reviews")
async def get_seller_reviews(seller_username: str):
    _, aliases, _ = await resolve_seller_identity(seller_username)
    alias_placeholders = ",".join(["%s"] * len(aliases))
    return await db_exec(
        f"""
        SELECT
            id,
            seller_username,
            reviewer_username,
            rating,
            COALESCE(comment, '') AS comment,
            created_at
        FROM seller_reviews
        WHERE TRIM(LOWER(seller_username)) IN ({alias_placeholders})
        ORDER BY id DESC
        """,
        tuple(alias.lower() for alias in aliases),
        fetchall=True,
    )


@app.post("/sellers/{seller_username}/reviews")
async def create_seller_review(seller_username: str, request: SellerReviewRequest):
    canonical, aliases, user_row = await resolve_seller_identity(seller_username)
    alias_placeholders = ",".join(["%s"] * len(aliases))

    reviewer_username = request.reviewer_username.strip()
    if not reviewer_username:
        raise HTTPException(status_code=400, detail="กรุณาระบุผู้รีวิว")

    reviewer_canonical, _, reviewer_row = await resolve_user_identity(reviewer_username)
    if reviewer_canonical.lower() == canonical.lower():
        raise HTTPException(status_code=400, detail="ไม่สามารถรีวิวตัวเองได้")

    seller_product = await db_exec(
        f"SELECT id FROM products WHERE TRIM(LOWER(seller_username)) IN ({alias_placeholders}) LIMIT 1",
        tuple(alias.lower() for alias in aliases),
        fetchone=True,
    )
    if not user_row and not seller_product and not canonical:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ขาย")

    await db_exec(
        """
        INSERT INTO seller_reviews (seller_username, reviewer_username, rating, comment)
        VALUES (%s, %s, %s, %s)
        """,
        (canonical or seller_username.strip(), reviewer_canonical or reviewer_username, request.rating, request.comment.strip()),
        commit=True,
    )
    return {"success": True, "message": "บันทึกรีวิวเรียบร้อย"}


@app.get("/categories")
async def get_categories():
    rows = await db_exec(
        """
        SELECT DISTINCT TRIM(category) AS category
        FROM products
        WHERE category IS NOT NULL AND TRIM(category) <> ''
        ORDER BY TRIM(category)
        """,
        fetchall=True,
    )
    return [r["category"] for r in rows]


@app.post("/inquiries")
async def create_inquiry(request: InquiryRequest):
    product = await db_exec(
        "SELECT id FROM products WHERE id=%s",
        (request.product_id,),
        fetchone=True,
    )
    if not product:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้าที่ต้องการสอบถาม")

    await db_exec(
        "INSERT INTO inquiries (product_id, buyer_username, message) VALUES (%s, %s, %s)",
        (request.product_id, request.buyer_username, request.message),
        commit=True,
    )
    return {"success": True, "message": "ส่งข้อความสอบถามเรียบร้อย"}


@app.get("/seller/inquiries/{seller_username}")
async def get_seller_inquiries(seller_username: str):
    return await db_exec(
        """
        SELECT
            i.id,
            i.product_id,
            p.product_name,
            i.buyer_username,
            i.message,
            i.created_at
        FROM inquiries i
        INNER JOIN products p ON p.id = i.product_id
        WHERE p.seller_username = %s
        ORDER BY i.id DESC
        """,
        (seller_username,),
        fetchall=True,
    )


@app.get("/seller/products/{seller_username}")
async def get_seller_products(seller_username: str):
    _, aliases, _ = await resolve_seller_identity(seller_username)
    alias_placeholders = ",".join(["%s"] * len(aliases))
    return await db_exec(
        f"""
        SELECT
            id,
            product_name,
            price,
            COALESCE(description, '') AS description,
            COALESCE(image_url, '') AS image_url,
            COALESCE(condition_label, 'มือสอง') AS condition_label,
            COALESCE(category, 'อื่นๆ') AS category,
            COALESCE(seller_username, 'unknown') AS seller_username,
            COALESCE(seller_rating, 0) AS seller_rating,
            COALESCE(is_sold, 0) AS is_sold,
            created_at
        FROM products
        WHERE TRIM(LOWER(seller_username)) IN ({alias_placeholders})
        ORDER BY id DESC
        """,
        tuple(alias.lower() for alias in aliases),
        fetchall=True,
    )


@app.post("/seller/products")
async def create_product(request: ProductUpsertRequest):
    seller_row = await db_exec(
        "SELECT id FROM user_login WHERE username=%s",
        (request.seller_username,),
        fetchone=True,
    )
    if not seller_row:
        raise HTTPException(status_code=400, detail="ไม่พบผู้ขายในระบบ")

    try:
        result = await db_exec(
            """
            INSERT INTO products
                (seller_id, product_name, price, description, image_url, condition_label, category, seller_username, seller_rating, is_sold)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
            """,
            (
                seller_row["id"],
                request.product_name,
                request.price,
                request.description,
                request.image_url,
                request.condition_label,
                request.category,
                request.seller_username,
                request.seller_rating,
            ),
            commit=True,
        )
    except pymysql.MySQLError as ex:
        # Fallback for databases that do not have seller_id column.
        if getattr(ex, "args", [None])[0] != 1054:
            raise HTTPException(status_code=500, detail=f"DB error: {str(ex)}")
        try:
            result = await db_exec(
                """
                INSERT INTO products
                    (product_name, price, description, image_url, condition_label, category, seller_username, seller_rating, is_sold)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, 0)
                """,
                (
                    request.product_name,
                    request.price,
                    request.description,
                    request.image_url,
                    request.condition_label,
                    request.category,
                    request.seller_username,
                    request.seller_rating,
                ),
                commit=True,
            )
        except pymysql.MySQLError as ex2:
            raise HTTPException(status_code=500, detail=f"DB error: {str(ex2)}")
    return {"success": True, "id": result["lastrowid"]}


@app.put("/seller/products/{product_id}")
async def update_product(product_id: int, request: ProductUpsertRequest):
    existing = await db_exec("SELECT id FROM products WHERE id=%s", (product_id,), fetchone=True)
    if not existing:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")

    await db_exec(
        """
        UPDATE products
        SET
            product_name=%s,
            price=%s,
            description=%s,
            image_url=%s,
            condition_label=%s,
            category=%s,
            seller_username=%s,
            seller_rating=%s
        WHERE id=%s
        """,
        (
            request.product_name,
            request.price,
            request.description,
            request.image_url,
            request.condition_label,
            request.category,
            request.seller_username,
            request.seller_rating,
            product_id,
        ),
        commit=True,
    )
    return {"success": True}


@app.patch("/seller/products/{product_id}/sold")
async def mark_product_sold(product_id: int, request: ProductSoldRequest):
    existing = await db_exec("SELECT id FROM products WHERE id=%s", (product_id,), fetchone=True)
    if not existing:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    await db_exec(
        "UPDATE products SET is_sold=%s WHERE id=%s",
        (1 if request.is_sold else 0, product_id),
        commit=True,
    )
    return {"success": True}


@app.delete("/seller/products/{product_id}")
async def delete_product(product_id: int):
    existing = await db_exec("SELECT id FROM products WHERE id=%s", (product_id,), fetchone=True)
    if not existing:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    await db_exec("DELETE FROM products WHERE id=%s", (product_id,), commit=True)
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    # รันที่ IP เดียวกับที่ mobile app เรียกใช้งาน
    uvicorn.run(app, host="172.20.127.86", port=2500)