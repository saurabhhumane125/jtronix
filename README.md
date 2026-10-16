# Employee REST API

A small Python/Flask API for the Jtronix backend internship assessment. It covers all three questions using the same employee store and starts with the three employees from the assessment.

## Run locally

Requires Python 3.10 or newer. No database, API key, or environment variables are needed.

Windows PowerShell, from the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

The API runs at `http://127.0.0.1:5000`. Open `http://127.0.0.1:5000/employees` in a browser to see the sample data. Stop the server with Ctrl+C.

If port 5000 is busy, use `.\.venv\Scripts\python.exe -m flask --app app run --port 5001` and use port 5001 in the request URLs. This is a local development server.

## Endpoints

| Method | Path | Success | Purpose |
| --- | --- | --- | --- |
| GET | `/employees` | 200 | List employees |
| GET | `/employees?department=Engineering` | 200 | Filter by department |
| GET | `/employees/1` | 200 | Retrieve one employee |
| POST | `/employees` | 201 | Create an employee |
| PATCH | `/employees/1/status` | 200 | Change status |
| GET | `/health` | 200 | Check the server is running |

Employee JSON uses lowercase keys: `id`, `name`, `department`, `status`.

### Retrieve an employee

`GET /employees/1` returns `200 OK`:

```json
{"id": 1, "name": "Rahul Sharma", "department": "Engineering", "status": "Active"}
```

`GET /employees?department=Engineering` returns a JSON array containing Rahul Sharma and Amit Verma. An unknown department returns `[]`.

### Create an employee

`POST /employees`, with `Content-Type: application/json`:

```json
{"name": "Neha Singh", "department": "Sales"}
```

Response: `201 Created`, with a `Location: /employees/4` header on a fresh server:

```json
{"id": 4, "name": "Neha Singh", "department": "Sales", "status": "Active"}
```

### Update status

`PATCH /employees/4/status`, with `Content-Type: application/json`:

```json
{"status": "Inactive"}
```

Response: `200 OK`:

```json
{"id": 4, "name": "Neha Singh", "department": "Sales", "status": "Inactive"}
```

### Error examples

Missing employee: `404 Not Found`.

```json
{"error": "Employee not found."}
```

Empty or missing name/department, or a value that is not a string: `400 Bad Request`.

```json
{"error": "Validation failed.", "fields": {"name": "Must be a non-empty string."}}
```

Invalid status: `400 Bad Request`.

```json
{"error": "Status must be either Active or Inactive."}
```

Malformed JSON and bodies that are not JSON objects return `400`. Requests without a JSON content type return `415`. Unsupported methods return `405`. Non-numeric, zero, negative, or unknown employee IDs return `404`. All these errors use JSON.

## Try it in Postman

Import `postman/Employee_API.postman_collection.json` into Postman. Start the API, then run the collection in order. The `base_url` collection variable defaults to `http://127.0.0.1:5000`; change it if you use a different port.

The 12 requests demonstrate retrieval, filtering, creation, status updates, and error responses. Each request includes response checks. The create request saves the generated ID as `employee_id` for subsequent requests, so run it first when sending those requests individually.

## Try it from PowerShell

With the server running, open a second terminal and send these requests. The PATCH example assumes a fresh server where the newly created employee has ID 4; otherwise use the ID from the POST response.

```powershell
Invoke-RestMethod http://127.0.0.1:5000/employees
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/employees -ContentType 'application/json' -Body '{"name":"Neha Singh","department":"Sales"}'
Invoke-RestMethod -Method Patch -Uri http://127.0.0.1:5000/employees/4/status -ContentType 'application/json' -Body '{"status":"Inactive"}'
```

## Run the tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

On macOS/Linux use `.venv/bin/python` instead. No running server is needed. Tests cover the sample data, create/read/update flow, filtering, validation, error responses, independent stores, and concurrent ID allocation.

## Implementation and choices

- `app.py`: Employee dataclass, in-memory store, request validation, and routes.
- `tests/test_api.py`: Endpoint tests using Python's built-in unittest and Flask's test client.
- `postman/Employee_API.postman_collection.json`: Example requests with response checks.

Flask keeps this small API in one readable file. An Employee dataclass defines the four required fields; `asdict()` converts each employee to a JSON-ready dictionary. Employees are stored in a dictionary keyed by ID. IDs increase from 4, and a lock protects reads and writes within one server process.

Names and departments are trimmed before saving. Department filtering is an exact match ignoring case and surrounding spaces. A blank department filter is rejected. Status accepts exactly `Active` or `Inactive`. On creation, the server always assigns the ID and Active status; extra input fields are ignored. PATCH only changes status and leaves other fields alone. For PATCH, a missing employee is checked before the request body.

Small extras: health check, case-insensitive filtering, a Location header after creation, consistent JSON errors, and automated tests.

## Limitations

All assessment features are implemented. Data resets when the process restarts. Different server processes would have separate stores, so this version is intended to run as one process. There is no authentication, persistent database, pagination, or employee deletion. The assessment allows an in-memory collection; SQLite and authentication would be reasonable next steps for a larger application.

Framework reference: [Flask quickstart](https://flask.palletsprojects.com/en/stable/quickstart/) and [testing documentation](https://flask.palletsprojects.com/en/stable/testing/).
