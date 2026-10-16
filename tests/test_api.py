import unittest
from concurrent.futures import ThreadPoolExecutor

from app import create_app


class EmployeeApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_sample_employees(self):
        response = self.client.get("/employees")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [
            {"id": 1, "name": "Rahul Sharma", "department": "Engineering", "status": "Active"},
            {"id": 2, "name": "Priya Patel", "department": "HR", "status": "Active"},
            {"id": 3, "name": "Amit Verma", "department": "Engineering", "status": "Inactive"},
        ])

    def test_get_employee_and_missing_employee(self):
        response = self.client.get("/employees/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["name"], "Rahul Sharma")
        response = self.client.get("/employees/999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"error": "Employee not found."})

    def test_department_filter(self):
        for department in ("Engineering", "engineering", " Engineering "):
            with self.subTest(department=department):
                response = self.client.get("/employees", query_string={"department": department})
                self.assertEqual(response.status_code, 200)
                self.assertEqual([e["id"] for e in response.get_json()], [1, 3])
        self.assertEqual(self.client.get("/employees?department=Unknown").get_json(), [])
        self.assertEqual(self.client.get("/employees?department=%20").status_code, 400)

    def test_create_then_retrieve_and_update(self):
        response = self.client.post("/employees", json={"name": " Neha Singh ", "department": " Sales "})
        self.assertEqual(response.status_code, 201)
        employee = response.get_json()
        self.assertEqual(employee, {"id": 4, "name": "Neha Singh", "department": "Sales", "status": "Active"})
        self.assertEqual(response.headers["Location"], "/employees/4")
        self.assertEqual(self.client.get(response.headers["Location"]).get_json(), employee)
        response = self.client.patch("/employees/4/status", json={"status": "Inactive"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {**employee, "status": "Inactive"})
        self.assertEqual(self.client.get("/employees/4").get_json()["status"], "Inactive")
        self.assertEqual(self.client.get("/employees?department=Sales").get_json(), [response.get_json()])

    def test_invalid_employee_fields_do_not_create_records(self):
        for field in ("name", "department"):
            for value in (None, "", "   ", 12, True, [], {}):
                with self.subTest(field=field, value=value):
                    body = {"name": "Neha", "department": "Sales", field: value}
                    response = self.client.post("/employees", json=body)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(field, response.get_json()["fields"])
        self.assertEqual(self.client.post("/employees", json={}).status_code, 400)
        self.assertEqual(len(self.client.get("/employees").get_json()), 3)
        response = self.client.post("/employees", json={"name": "Neha", "department": "Sales"})
        self.assertEqual(response.get_json()["id"], 4)

    def test_create_ignores_client_id_and_status(self):
        response = self.client.post("/employees", json={
            "id": 1, "name": "Neha", "department": "Sales", "status": "Inactive",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["id"], 4)
        self.assertEqual(response.get_json()["status"], "Active")

    def test_status_transitions_and_repeated_update(self):
        for status in ("Inactive", "Inactive", "Active"):
            response = self.client.patch("/employees/1/status", json={"status": status})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.client.get("/employees/1").get_json()["status"], status)

    def test_invalid_status_does_not_change_employee(self):
        for value in (None, "", "active", "Pending", 1, True, [], {}):
            with self.subTest(value=value):
                response = self.client.patch("/employees/1/status", json={"status": value})
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())
        self.assertEqual(self.client.patch("/employees/1/status", json={}).status_code, 400)
        self.assertEqual(self.client.get("/employees/1").get_json()["status"], "Active")

    def test_update_missing_employee(self):
        response = self.client.patch("/employees/999/status", json={"status": "Inactive"})
        self.assertEqual(response.status_code, 404)

    def test_invalid_request_bodies(self):
        for method, path in (("POST", "/employees"), ("PATCH", "/employees/1/status")):
            for raw in ("{", "null", "[]", '"text"', "42", ""):
                with self.subTest(method=method, raw=raw):
                    response = self.client.open(path, method=method, data=raw, content_type="application/json")
                    self.assertEqual(response.status_code, 400)
                    self.assertIn("error", response.get_json())
            response = self.client.open(path, method=method, data="name=Neha")
            self.assertEqual(response.status_code, 415)

    def test_routing_errors_are_json(self):
        for path in ("/employees/abc", "/employees/-1", "/employees/0", "/missing"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertIn("error", response.get_json())
        response = self.client.delete("/employees/1")
        self.assertEqual(response.status_code, 405)
        self.assertIn("GET", response.headers["Allow"])

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_concurrent_creates_have_unique_ids(self):
        def create_employee(number):
            with self.app.test_client() as client:
                response = client.post("/employees", json={"name": f"Employee {number}", "department": "QA"})
                self.assertEqual(response.status_code, 201)
                return response.get_json()["id"]

        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(create_employee, range(20)))
        self.assertEqual(sorted(ids), list(range(4, 24)))
        self.assertEqual(len(self.client.get("/employees").get_json()), 23)

    def test_separate_apps_have_fresh_data(self):
        self.client.post("/employees", json={"name": "Neha", "department": "Sales"})
        self.assertEqual(len(create_app().test_client().get("/employees").get_json()), 3)


if __name__ == "__main__":
    unittest.main()
