# Bookstore API

This is a FastAPI application for managing a bookstore database using MariaDB.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set up MariaDB database:
   - Create database `book_store`
   - Create table `it_book` with fields: id (auto-increment), book_name, authore, price, cover_image

3. Update `db_connection.py` with your MariaDB credentials.

## Running the API

Run the server:
```
uvicorn api:app --reload
```

The API will be available at http://127.0.0.1:8000

## Endpoints

- GET /books: Get all books
- GET /books/{id}: Get book by ID
- POST /books: Create a new book
- PUT /books/{id}: Update a book
- DELETE /books/{id}: Delete a book

## Troubleshooting

- Ensure MariaDB is running and credentials are correct.
- Check table schema matches the fields.

## Mobile App (Flet)

A simple Flet-based mobile/web page is provided in `mobile_app.py` that fetches all books from the API and displays them in a single-column list.

1. Install the additional dependency:
   ```
   pip install flet requests
   ```
2. Start the FastAPI server as described above.
3. Run the Flet app:
   ```
   python mobile_app.py
   ```
4. The app will open in your browser (or mobile if using `view=ft.MOBILE`) and show the book list. Press **Refresh** to reload data.
