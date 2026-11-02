import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from app import Inventory, make_handler


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.inventory = Inventory(Path(self.directory.name) / "test.db")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.inventory))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def request(self, method, path, body=None, raw=None):
        connection = HTTPConnection(*self.server.server_address, timeout=3)
        try:
            payload = raw if raw is not None else json.dumps(body) if body is not None else None
            connection.request(method, path, payload, {"Content-Type": "application/json"})
            response = connection.getresponse()
            data = response.read()
            return response.status, json.loads(data) if data else None
        finally:
            connection.close()

    def test_full_http_lifecycle(self):
        self.assertEqual(self.request("GET", "/health"), (200, {"status": "ok"}))
        product = {"name": "Caderno", "quantity": 3, "price_cents": 1250}
        status, created = self.request("POST", "/products", product)
        self.assertEqual(status, 201)
        path = f'/products/{created["id"]}'
        self.assertEqual(self.request("GET", path)[1]["name"], "Caderno")
        self.assertEqual(len(self.request("GET", "/products")[1]), 1)
        self.assertEqual(self.request("GET", "/summary")[1]["total_value_cents"], 3750)
        product["quantity"] = 2
        self.assertEqual(self.request("PUT", path, product)[1]["quantity"], 2)
        self.assertEqual(self.request("DELETE", path), (204, None))
        self.assertEqual(self.request("GET", path)[0], 404)
        self.assertEqual(self.request("GET", "/summary")[1]["units"], 0)

    def test_rejects_invalid_inputs_without_writes(self):
        for body in [[], {}, {"name": "a", "quantity": -1, "price_cents": 1},
                     {"name": " ", "quantity": 1, "price_cents": 1},
                     {"name": "a", "quantity": True, "price_cents": 1},
                     {"name": "a", "quantity": 1, "price_cents": 1.5}]:
            self.assertEqual(self.request("POST", "/products", body)[0], 400)
        self.assertEqual(self.request("POST", "/products", raw="{broken")[0], 400)
        self.assertEqual(self.inventory.list(), [])

    def test_missing_routes_methods_and_products(self):
        self.assertEqual(self.request("GET", "/unknown")[0], 404)
        self.assertEqual(self.request("PUT", "/products", {})[0], 405)
        self.assertEqual(self.request("DELETE", "/products/999")[0], 404)
        self.assertEqual(self.request("GET", "/products/" + "9" * 100)[0], 404)

    def test_persistence_and_parameterized_queries(self):
        name = "'); DROP TABLE products; --"
        created = self.inventory.save({"name": name, "quantity": 1, "price_cents": 100})
        reopened = Inventory(self.inventory.path)
        self.assertEqual(reopened.get(created["id"])["name"], name)


if __name__ == "__main__":
    unittest.main()
