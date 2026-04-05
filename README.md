# Finance Data Processing and Access Control Backend

This repository contains a compact backend implementation for the finance dashboard assessment. It focuses on clear API design, SQLite persistence, role-based access control, validation, summary analytics, and maintainable backend structure without unnecessary framework complexity.

## Tech Stack

- Python 3.12
- Standard library HTTP server (`http.server`)
- SQLite (`sqlite3`)
- `unittest` for API verification

## Why This Approach

The assignment emphasizes backend thinking more than framework choice. I used the Python standard library plus SQLite so the project stays easy to run and review while still demonstrating:

- separation between transport, service, and persistence layers
- role-based authorization rules
- data validation and structured error responses
- aggregate dashboard logic beyond CRUD
- persistent storage without external setup

## Project Structure

```text
app/
  auth.py
  config.py
  database.py
  docs.py
  errors.py
  repositories.py
  services.py
  server.py
tests/
  test_api.py
```

## Features Implemented

### User and Role Management

- create users
- list users
- get user detail
- update user role, status, email, name, or token
- roles:
  - `viewer`: dashboard only
  - `analyst`: dashboard and records read access
  - `admin`: full user and record management

### Financial Records Management

- create, list, update, and delete records
- get record detail
- filter by `type`, `category`, `start_date`, and `end_date`
- supports `limit`, `offset`, `sort_by`, and `sort_direction`
- delete is implemented as soft delete
- audit fields are tracked for `created_by`, `updated_by`, and `deleted_by`

### Dashboard Summary API

`GET /dashboard/summary` returns:

- total income
- total expenses
- net balance
- category totals
- monthly trends
- recent activity

### Access Control

- viewer cannot access `/records`
- analyst can read records and summaries
- admin can manage users and records
- inactive users are blocked even with a valid token

### Validation and Error Handling

- required field checks
- enum validation for roles, statuses, and record types
- date validation with `YYYY-MM-DD`
- numeric validation for amounts
- JSON error responses with appropriate status codes

### API Documentation

- `GET /openapi.json` returns a lightweight OpenAPI 3.0 document for the backend

## Running the API

```bash
python -m app.server
```

Or on Windows PowerShell:

```powershell
.\start_backend.ps1
```

Server URL:

```text
http://127.0.0.1:8000
```

## Seeded Demo Users

| Role | Email | Token |
|------|-------|-------|
| Admin | `admin@finance.local` | `admin-token` |
| Analyst | `analyst@finance.local` | `analyst-token` |
| Viewer | `viewer@finance.local` | `viewer-token` |
| Inactive Viewer | `inactive@finance.local` | `inactive-token` |

The app also seeds a handful of financial records for immediate testing.

## API Endpoints

### Health

- `GET /health`

### Users

- `GET /users` admin only
- `GET /users/{id}` admin only
- `POST /users` admin only
- `PATCH /users/{id}` admin only

Example:

```bash
curl -X POST http://127.0.0.1:8000/users \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Jane Doe\",\"email\":\"jane@finance.local\",\"role\":\"analyst\",\"status\":\"active\"}"
```

### Records

- `GET /records` analyst or admin
- `GET /records/{id}` analyst or admin
- `POST /records` admin only
- `PATCH /records/{id}` admin only
- `DELETE /records/{id}` admin only

Example filter:

```text
GET /records?type=expense&category=Software&start_date=2026-02-01&end_date=2026-03-31&limit=20&offset=0&sort_by=amount&sort_direction=asc
```

### Dashboard

- `GET /dashboard/summary` viewer, analyst, or admin

### Docs

- `GET /openapi.json`

Example:

```bash
curl http://127.0.0.1:8000/dashboard/summary \
  -H "Authorization: Bearer viewer-token"
```

## Example Error Response

```json
{
  "error": "Record amount must be zero or greater.",
  "details": {}
}
```

## Testing

```bash
python -m unittest discover -s tests -v
```

To run an end-to-end API smoke test against a running server:

```powershell
.\test_api.ps1
```

Suggested flow:

1. Start the API with `.\start_backend.ps1`
2. In a second PowerShell window run `.\test_api.ps1`

## Assumptions and Tradeoffs

- authentication is simplified to bearer tokens stored on the user record
- SQLite is used to keep setup minimal while still providing persistence
- a lightweight built-in HTTP server is used to keep the focus on backend logic
- record deletion is soft delete so summaries and list endpoints exclude deleted rows
- analysts are read-only users with record and dashboard access

## Possible Next Improvements

- JWT or session-based authentication
- Docker support
- richer OpenAPI schema details and examples
- more edge-case tests
