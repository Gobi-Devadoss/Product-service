# Product Service

A REST service that manages products for an online store. Built with **FastAPI**, **MySQL**, **SQLAlchemy** and **Alembic**.

## Prerequisites

- Python 3.11 or newer
- MySQL 8 (local install, or Docker using the included `docker-compose.yml`)

## 1. Install

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure

```bash
cp .env.example .env             # Windows: copy .env.example .env
```

Edit `.env` and set your passwords. `DATABASE_URL` is the only required setting:

```
DATABASE_URL=mysql+pymysql://<user>:<password>@<host>:3306/<database>
```

## 3. Start MySQL

**Option A, Docker:**

```bash
docker compose up -d
```

**Option B, your own MySQL:** create the database and user that match `DATABASE_URL`:

```sql
CREATE DATABASE product_db;
CREATE USER 'product_user'@'%' IDENTIFIED BY 'change_me';
GRANT ALL PRIVILEGES ON product_db.* TO 'product_user'@'%';
```

## 4. Create the tables (migrations)

```bash
alembic upgrade head
```

## 5. Run

```bash
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000/api/v1/products
- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Run the tests

```bash
pytest
```

Tests use an in-memory SQLite database, so MySQL is not needed for them. The command also prints coverage.

## Endpoints

| Method | Path | Purpose | Success |
|---|---|---|---|
| POST | `/api/v1/products` | Create a product | 201 + `Location` header |
| GET | `/api/v1/products/{id}` | Get one product | 200 |
| GET | `/api/v1/products` | List products | 200 |
| PUT | `/api/v1/products/{id}` | Replace a product (all fields) | 200 |
| PATCH | `/api/v1/products/{id}` | Update only the fields sent | 200 |
| DELETE | `/api/v1/products/{id}` | Delete a product | 204 |
| GET | `/health` | Health check (also checks the database) | 200 |

### List parameters

| Param | Default | Notes |
|---|---|---|
| `page` | 1 | **Pages start at 1** |
| `size` | 10 | 1 to 100 |
| `category` | | case-insensitive match |
| `status` | | `ACTIVE` or `INACTIVE` |
| `minPrice`, `maxPrice` | | inclusive |
| `sort` | `id,asc` | `<field>,<asc or desc>`; fields: `id`, `name`, `price`, `quantity`, `createdAt` |

## Example requests

```bash
# Create
curl -i -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Wireless Mouse","price":799.50,"quantity":25,"category":"Electronics"}'

# Get one
curl http://localhost:8000/api/v1/products/1

# List: page 1, 5 per page, electronics between 500 and 5000, cheapest first
curl "http://localhost:8000/api/v1/products?page=1&size=5&category=Electronics&minPrice=500&maxPrice=5000&sort=price,asc"

# Replace
curl -X PUT http://localhost:8000/api/v1/products/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Gaming Mouse","price":1999,"quantity":10,"category":"Electronics","status":"ACTIVE"}'

# Partial update
curl -X PATCH http://localhost:8000/api/v1/products/1 \
  -H "Content-Type: application/json" -d '{"quantity":5}'

# Delete
curl -i -X DELETE http://localhost:8000/api/v1/products/1
```

A ready-made Postman collection is in `postman_collection.json` and the OpenAPI spec is in `openapi.json`.

## Error format

Every error has the same shape:

```json
{
  "timestamp": "2026-11-02T10:15:30Z",
  "status": 400,
  "error": "Bad Request",
  "message": "Validation failed",
  "path": "/api/v1/products",
  "details": [{ "field": "price", "issue": "Input should be greater than 0" }]
}
```

| Situation | Status |
|---|---|
| Validation failure, malformed JSON, malformed id | 400 |
| Product not found | 404 |
| Duplicate product name (case-insensitive) | 409 |
| Unsupported method | 405 |
| Unexpected error (details only in the log) | 500 |

## Project structure

```
app/
  main.py            app setup, request logging
  config.py          settings from environment / .env
  database.py        engine and session
  models.py          database entity
  schemas.py         request/response DTOs and validation
  repository.py      data access
  service.py         business rules
  exceptions.py      app error types
  errors.py          global error handlers
  routers/
    products.py      product endpoints (HTTP only)
    health.py        health check
alembic/versions/    database migrations
tests/               unit (service) and API tests
```

## Design decisions and known limitations

- `id`, `createdAt` and `updatedAt` sent by the client are ignored, never stored.
- DELETE is a hard delete. To hide a product without deleting it, PATCH `status` to `INACTIVE`.
- Prices are returned as JSON numbers and stored as `DECIMAL(10,2)`.
- Timestamps are stored and returned in UTC.
