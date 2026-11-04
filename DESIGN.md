# Design Note: Product Service

**Stack:** Python, FastAPI, SQLAlchemy, Alembic, MySQL 8. Tests use SQLite in memory.

## Endpoints

Base path `/api/v1/products`

| Method | Path | Success | Errors |
|---|---|---|---|
| POST | `/` | 201 + Location | 400, 409 |
| GET | `/{id}` | 200 | 400, 404 |
| GET | `/` | 200 | 400 |
| PUT | `/{id}` | 200 | 400, 404, 409 |
| PATCH | `/{id}` | 200 | 400, 404, 409 |
| DELETE | `/{id}` | 204 | 400, 404 |
| GET | `/health` | 200 (503 if DB is down) | |

List: `page` (starts at **1**), `size` (default 10, max 100), `category`, `status`, `minPrice`, `maxPrice`, `sort=<field>,<asc|desc>`. Response: `items`, `page`, `size`, `totalItems`, `totalPages`.

## Data model (`products` table)

| Column | Type | Rule |
|---|---|---|
| id | INT auto-increment | set by the database |
| name | VARCHAR(100) | required, 2-100 chars, unique (case-insensitive) |
| description | VARCHAR(500) | optional, max 500 |
| price | DECIMAL(10,2) | required, > 0, max 2 decimals |
| quantity | INT | required, >= 0 |
| category | VARCHAR(50) | required, 2-50 chars, indexed |
| status | ENUM('ACTIVE','INACTIVE') | default ACTIVE |
| created_at | DATETIME (UTC) | set on insert |
| updated_at | DATETIME (UTC) | set on every update |

## Validation rules

- Missing required fields, wrong types and out-of-range values: 400 with field-level `details`
- Text fields are trimmed before length checks (so `"   "` is rejected)
- Duplicate name, ignoring case: 409 (checked in the service, plus a unique constraint as a safety net)
- Malformed id (e.g. `/products/abc`): 400; unknown id: 404
- Client-sent `id`, `createdAt`, `updatedAt` are ignored
- PUT needs every required field; PATCH accepts any subset but rejects `null` for required fields
- `minPrice` greater than `maxPrice`, or an unknown sort field: 400

## Layers

```
HTTP -> routers (controller) -> service (business rules) -> repository (SQL) -> MySQL
              ^ DTOs (schemas.py) in and out; entities stay below the service
```

## Folder structure

```
app/  main.py, config.py, database.py, models.py, schemas.py,
      repository.py, service.py, exceptions.py, errors.py, routers/
alembic/versions/   migrations
tests/              test_service.py (unit), test_api.py (API)
```
