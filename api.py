from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import db_connection

app = FastAPI()

class Book(BaseModel):
    book_name: str
    authore: str
    price: float
    cover_image: str

@app.get("/books")
def get_books():
    conn = db_connection.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM it_book")
            books = cursor.fetchall()
        return books
    finally:
        conn.close()

@app.get("/books/{book_id}")
def get_book(book_id: int):
    conn = db_connection.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM it_book WHERE id = %s", (book_id,))
            book = cursor.fetchone()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return book
    finally:
        conn.close()

@app.post("/books")
def create_book(book: Book):
    conn = db_connection.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO it_book (book_name, authore, price, cover_image) VALUES (%s, %s, %s, %s)",
                           (book.book_name, book.authore, book.price, book.cover_image))
            conn.commit()
            book_id = cursor.lastrowid
        return {"id": book_id, **book.dict()}
    finally:
        conn.close()

@app.put("/books/{book_id}")
def update_book(book_id: int, book: Book):
    conn = db_connection.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE it_book SET book_name=%s, authore=%s, price=%s, cover_image=%s WHERE id=%s",
                           (book.book_name, book.authore, book.price, book.cover_image, book_id))
            conn.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Book not found")
        return {"id": book_id, **book.dict()}
    finally:
        conn.close()

@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    conn = db_connection.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM it_book WHERE id=%s", (book_id,))
            conn.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Book not found")
        return {"message": "Book deleted"}
    finally:
        conn.close()