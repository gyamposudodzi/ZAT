# Backend Explanation Guide

This document explains the backend in simple language. It is written so that someone without a computer science degree can still follow what the system does, why it exists, and how the different parts fit together.

## 1. What This Backend Is

Think of this backend as the "engine room" behind a finance dashboard.

A dashboard is usually the screen a user sees in a browser or app. The backend is the part that:

- stores the data
- checks whether a user is allowed to do something
- calculates totals and summaries
- sends information back when the frontend asks for it

In this project, the backend manages:

- users
- user roles
- financial records
- dashboard summary data

## 2. What Problem It Solves

Imagine a small finance team using one system.

Different people should have different levels of access:

- a `viewer` should only see summary information
- an `analyst` should be able to inspect records and trends
- an `admin` should be able to fully manage users and records

At the same time, the system should:

- store finance entries such as income and expenses
- allow searching and filtering
- calculate totals such as income, expense, and balance
- reject bad input
- stop unauthorized actions

That is exactly what this backend does.

## 3. The Main Ideas Behind The Design

The code is split into small parts so each part has a clear job.

### `app/server.py`

This is the entry point of the API.

It:

- receives HTTP requests
- checks which URL was called
- sends the request to the correct business logic
- returns JSON responses

You can think of it like a receptionist:

- it listens
- figures out what the visitor wants
- sends the visitor to the correct department

### `app/services.py`

This contains the business rules.

It:

- validates data
- decides what is allowed
- prepares filters and sorting
- creates dashboard summaries

You can think of this as the decision-making layer.

### `app/repositories.py`

This layer talks directly to the database.

It:

- saves records
- updates rows
- reads data
- runs totals and summary queries

You can think of it as the storage clerk.

### `app/auth.py`

This handles access control.

It:

- reads the token sent by the user
- checks who the user is
- confirms the user is active
- checks whether the user’s role allows the requested action

### `app/database.py`

This sets up the SQLite database and its tables.

It makes sure the database structure exists before the app starts serving requests.

### `app/docs.py`

This provides a lightweight OpenAPI document.

That document is like a machine-readable description of the API. Tools can use it to understand what endpoints exist.

## 4. What Database Is Used

This project uses `SQLite`.

SQLite is a small database stored in a file. It is useful for assessments and demos because:

- it does not need a separate server
- it is easy to run locally
- it still gives real data persistence

Persistence means the data does not disappear when the app stops.

## 5. What Data Is Stored

There are two main data groups.

### Users

A user has:

- `id`: unique number
- `name`: person’s name
- `email`: person’s email
- `role`: what they are allowed to do
- `status`: whether they are active or inactive
- `api_token`: a simple token used to identify them
- `created_at`: when they were added

### Financial Records

A financial record has:

- `id`: unique number
- `amount`: money value
- `type`: `income` or `expense`
- `category`: such as Salary, Rent, Travel
- `record_date`: the date of the transaction
- `notes`: extra explanation
- `created_by`: which user created it
- `updated_by`: which user last changed it
- `deleted_by`: which user deleted it
- `created_at`: when it was created
- `updated_at`: when it was last changed
- `deleted_at`: when it was soft deleted

## 6. What "Soft Delete" Means

When a record is deleted here, it is not fully erased from the database immediately.

Instead, the backend marks it as deleted using `deleted_at` and `deleted_by`.

This is called a `soft delete`.

Why this is useful:

- it is safer than permanent deletion
- it leaves an audit trail
- deleted records stop showing in normal API results

So from a user’s point of view, the record is gone. But from a system point of view, there is still history.

## 7. How Login Works In This Project

This project uses a simplified approach for authentication.

Instead of a full username/password login flow, each request sends a token in the request header:

```text
Authorization: Bearer admin-token
```

The backend then:

1. reads the token
2. finds the matching user
3. checks if the user is active
4. checks if the user has permission

This is intentionally simple because the assessment focuses on backend structure and logic.

## 8. Seeded Demo Users

The system automatically creates demo users the first time it starts.

### Admin

- email: `admin@finance.local`
- token: `admin-token`
- power: full access

### Analyst

- email: `analyst@finance.local`
- token: `analyst-token`
- power: can view records and dashboard summaries

### Viewer

- email: `viewer@finance.local`
- token: `viewer-token`
- power: can only view dashboard summaries

### Inactive Viewer

- email: `inactive@finance.local`
- token: `inactive-token`
- power: blocked because the account is inactive

## 9. How Access Control Works

Access control means deciding who is allowed to do what.

This backend uses role-based access control.

### Viewer

Allowed:

- read dashboard summary

Not allowed:

- read records
- create records
- update records
- delete records
- manage users

### Analyst

Allowed:

- read dashboard summary
- read records

Not allowed:

- create records
- update records
- delete records
- manage users

### Admin

Allowed:

- read dashboard summary
- read records
- create records
- update records
- delete records
- create users
- list users
- update users
- view individual user details

## 10. What An API Endpoint Is

An endpoint is a URL the frontend or a tool can call to ask the backend to do something.

Examples:

- "give me all records"
- "create a new user"
- "show me the dashboard totals"

Each endpoint usually has:

- a method such as `GET`, `POST`, `PATCH`, or `DELETE`
- a URL path such as `/records`

### Quick meaning of methods

- `GET`: fetch data
- `POST`: create new data
- `PATCH`: change existing data
- `DELETE`: remove data or mark it deleted

## 11. Endpoint-By-Endpoint Explanation

## `GET /health`

### Purpose

Checks whether the backend is running.

### Who can use it

Anyone.

### Why it matters

This is useful for quick checks, automated monitoring, or confirming the server started correctly.

### Example response

```json
{
  "status": "ok"
}
```

## `GET /openapi.json`

### Purpose

Returns a machine-readable description of the API.

### Who can use it

Anyone.

### Why it matters

This helps reviewers and tools understand the API structure without reading the code first.

## `GET /users`

### Purpose

Returns the list of users.

### Who can use it

Admin only.

### Why it matters

This lets admins manage who exists in the system and what their current role or status is.

### Example use case

An admin wants to check whether a person is active or inactive.

## `GET /users/{id}`

### Purpose

Returns one user by ID.

### Who can use it

Admin only.

### Why it matters

This is useful when a frontend wants to show a single user’s details page.

## `POST /users`

### Purpose

Creates a new user.

### Who can use it

Admin only.

### What information it expects

- `name`
- `email`
- `role`
- `status`

### What the backend checks

- all required fields are present
- the email looks valid
- the role is one of the allowed roles
- the status is valid
- the email is not already in use

### What happens after success

- a new user is saved
- an API token is generated if one is not provided

## `PATCH /users/{id}`

### Purpose

Updates part of a user’s information.

### Who can use it

Admin only.

### What can be updated

- name
- email
- role
- status
- token

### Why `PATCH` is used

Because it updates only the fields that need changing, instead of replacing everything.

## `GET /records`

### Purpose

Returns financial records.

### Who can use it

Analyst or admin.

### Supported filters

- `type`
- `category`
- `start_date`
- `end_date`

### Supported list controls

- `limit`: how many results to return
- `offset`: how many results to skip
- `sort_by`: how to sort the records
- `sort_direction`: ascending or descending

### Why this matters

Finance data is more useful when people can narrow it down.

For example:

- only expenses
- only travel entries
- only March transactions

### Example

```text
/records?type=expense&category=Travel&sort_by=amount&sort_direction=asc
```

### What the response includes

- `data`: the records
- `meta`: extra information such as count, total, limit, offset, and sorting

## `GET /records/{id}`

### Purpose

Returns one financial record by ID.

### Who can use it

Analyst or admin.

### Why it matters

This is useful when a frontend wants to show the full details of one selected record.

## `POST /records`

### Purpose

Creates a new financial record.

### Who can use it

Admin only.

### What information it expects

- `amount`
- `type`
- `category`
- `record_date`
- `notes` is optional

### What the backend checks

- amount is numeric
- amount is not negative
- type is either `income` or `expense`
- category is not empty
- date uses `YYYY-MM-DD`

### What happens after success

- the record is stored
- the `created_by` field is filled automatically from the current admin

## `PATCH /records/{id}`

### Purpose

Updates part of an existing financial record.

### Who can use it

Admin only.

### What happens after success

- changed fields are updated
- `updated_by` is saved
- `updated_at` is refreshed

## `DELETE /records/{id}`

### Purpose

Soft deletes a record.

### Who can use it

Admin only.

### What happens after success

- the record stops appearing in normal record lists
- it stops contributing to dashboard totals
- `deleted_by` and `deleted_at` are saved

## `GET /dashboard/summary`

### Purpose

Returns a summary for the finance dashboard.

### Who can use it

Viewer, analyst, or admin.

### What it returns

- total income
- total expenses
- net balance
- category totals
- monthly trends
- recent activity

### Why it matters

This endpoint shows the bigger picture instead of raw rows only.

A dashboard usually needs both:

- detailed records
- high-level summaries

## 12. What The Dashboard Summary Means

### Total Income

The sum of all active income records.

### Total Expenses

The sum of all active expense records.

### Net Balance

This is:

```text
total income - total expenses
```

If the number is positive, income is greater than expense.

If the number is negative, expenses are higher than income.

### Category Totals

This shows how much money was grouped under categories such as:

- Salary
- Rent
- Travel
- Software

### Monthly Trends

This shows how income and expenses change over time month by month.

That helps users notice patterns.

### Recent Activity

This shows the most recent records added to the system.

## 13. What Validation Means

Validation means checking if the data makes sense before accepting it.

Examples:

- an amount should not be negative
- a date should be in the correct format
- a role should be one of the allowed values
- a request should contain required fields

Without validation, the database can quickly fill with broken or confusing data.

## 14. What Error Handling Means

Error handling means the backend does not just fail silently.

Instead, it returns clear responses when something goes wrong.

Examples:

- `400 Bad Request`: the user sent invalid data
- `401 Unauthorized`: login token is missing or invalid
- `403 Forbidden`: user is known but not allowed to do this
- `404 Not Found`: the requested record or user does not exist
- `500 Internal Server Error`: something unexpected happened in the server

### Example

If a user tries to create a record with a negative amount, the backend rejects it instead of storing bad data.

## 15. What Happens During A Typical Request

Here is a simple example using `POST /records`.

1. A client sends a request to create a record.
2. The request includes a bearer token.
3. The backend reads the token.
4. The backend finds the matching user.
5. The backend checks if that user is active.
6. The backend checks if the role is allowed to create records.
7. The backend validates the request data.
8. The service layer prepares the clean data.
9. The repository layer saves it in SQLite.
10. The server returns a JSON success response.

This same basic pattern is used across the application.

## 16. What JSON Means

JSON is the format used to send data in and out of the backend.

It looks like this:

```json
{
  "amount": 1200,
  "type": "expense",
  "category": "Rent",
  "record_date": "2026-04-05"
}
```

It is popular because it is easy for both humans and software to read.

## 17. How To Start The Project

Use:

```powershell
.\start_backend.ps1
```

This starts the backend server locally at:

```text
http://127.0.0.1:8000
```

## 18. How To Test The API Quickly

Use:

```powershell
.\test_api.ps1
```

This script checks:

- server health
- documentation endpoint
- access control rules
- user endpoints
- record endpoints
- validation errors
- soft delete behavior

## 19. Why This Project Is Good For The Assessment

This project demonstrates:

- backend structure
- API design
- database usage
- access control
- validation
- aggregation logic
- documentation
- testing

It is intentionally simple enough to review quickly, but still strong enough to show real backend thinking.

## 20. Current Tradeoffs

Every project makes tradeoffs.

This one keeps some things simple on purpose.

### Simplified Authentication

It uses tokens instead of a full password login flow.

This keeps focus on the backend logic required by the assessment.

### SQLite Instead Of A Larger Database Server

This makes local setup much easier.

For an assessment, that is a practical choice.

### Lightweight HTTP Server

A bigger framework like FastAPI or Django could have been used, but the assignment did not require that.

The current version keeps the code direct and easier to inspect.

## 21. If This Were Expanded Later

Possible future improvements:

- real login with passwords and JWT
- Docker support
- Swagger UI
- audit history screen
- search by note text
- export to CSV
- restore deleted records
- more detailed tests

## 22. Final Summary

In simple terms, this backend is a secure finance data manager.

It:

- stores finance records
- controls who can see or change them
- calculates dashboard totals
- rejects bad input
- keeps a simple audit trail

That makes it a good fit for the assessment because it shows both practical coding and clear backend thinking.
