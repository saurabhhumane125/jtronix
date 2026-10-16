"""A small Employee REST API for the Jtronix backend assessment."""

from dataclasses import asdict, dataclass
from threading import Lock

from flask import Flask, jsonify, request, url_for
from werkzeug.exceptions import BadRequest, HTTPException


@dataclass
class Employee:
    id: int
    name: str
    department: str
    status: str = "Active"


def create_app():
    app = Flask(__name__)
    # Each app starts with its own data, which also keeps tests independent.
    employees = {
        1: Employee(1, "Rahul Sharma", "Engineering"),
        2: Employee(2, "Priya Patel", "HR"),
        3: Employee(3, "Amit Verma", "Engineering", "Inactive"),
    }
    next_id = 4
    store_lock = Lock()

    def error(message, status_code, fields=None):
        body = {"error": message}
        if fields:
            body["fields"] = fields
        return jsonify(body), status_code

    def read_body():
        if not request.is_json:
            return None, error("Use Content-Type: application/json.", 415)
        try:
            body = request.get_json()
        except BadRequest:
            return None, error("Request body must contain valid JSON.", 400)
        if not isinstance(body, dict):
            return None, error("Request body must be a JSON object.", 400)
        return body, None

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/employees")
    def list_employees():
        department = request.args.get("department")
        if department is not None and not department.strip():
            return error("Department filter must not be empty.", 400)
        with store_lock:
            result = [
                asdict(employee)
                for employee in employees.values()
                if department is None
                or employee.department.casefold() == department.strip().casefold()
            ]
        return jsonify(result)

    @app.get("/employees/<int:employee_id>")
    def get_employee(employee_id):
        with store_lock:
            employee = employees.get(employee_id)
            if employee is None:
                return error("Employee not found.", 404)
            return jsonify(asdict(employee))

    @app.post("/employees")
    def add_employee():
        nonlocal next_id
        body, body_error = read_body()
        if body_error is not None:
            return body_error
        fields = {}
        for field in ("name", "department"):
            value = body.get(field)
            if not isinstance(value, str) or not value.strip():
                fields[field] = "Must be a non-empty string."
        if fields:
            return error("Validation failed.", 400, fields)
        # Hold the lock across ID allocation and insertion to avoid duplicate IDs.
        with store_lock:
            employee = Employee(next_id, body["name"].strip(), body["department"].strip())
            employees[employee.id] = employee
            next_id += 1
            response = jsonify(asdict(employee))
        response.status_code = 201
        response.headers["Location"] = url_for("get_employee", employee_id=employee.id)
        return response

    @app.patch("/employees/<int:employee_id>/status")
    def update_status(employee_id):
        with store_lock:
            employee = employees.get(employee_id)
            if employee is None:
                return error("Employee not found.", 404)
            body, body_error = read_body()
            if body_error is not None:
                return body_error
            status = body.get("status")
            if status not in ("Active", "Inactive"):
                return error("Status must be either Active or Inactive.", 400)
            employee.status = status
            return jsonify(asdict(employee))

    @app.errorhandler(HTTPException)
    def handle_http_error(exception):
        # Keep routing errors JSON too, including malformed IDs and wrong methods.
        response = exception.get_response()
        response.data = app.json.dumps({"error": exception.description})
        response.content_type = "application/json"
        return response

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
