"""API HTTP educacional de estoque. Use apenas em ambiente local."""
import argparse
import json
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class Inventory:
    def __init__(self, path):
        self.path = path
        with closing(self.connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity>=0),
                price_cents INTEGER NOT NULL CHECK(price_cents>=0))""")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def validate(data):
        if not isinstance(data, dict) or set(data) != {"name", "quantity", "price_cents"}:
            raise ValueError("Envie exatamente name, quantity e price_cents.")
        name = data["name"]
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
            raise ValueError("name deve ter entre 1 e 120 caracteres.")
        for field in ("quantity", "price_cents"):
            if type(data[field]) is not int or not 0 <= data[field] <= 1_000_000_000:
                raise ValueError(f"{field} deve ser inteiro entre 0 e 1000000000.")
        return (name.strip(), data["quantity"], data["price_cents"])

    def list(self):
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute("SELECT * FROM products ORDER BY id")]

    def get(self, product_id):
        with closing(self.connect()) as db:
            row = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if row is None:
            raise LookupError("Produto não encontrado.")
        return dict(row)

    def save(self, data, product_id=None):
        values = self.validate(data)
        with closing(self.connect()) as db, db:
            if product_id is None:
                product_id = db.execute(
                    "INSERT INTO products(name,quantity,price_cents) VALUES (?,?,?)", values
                ).lastrowid
            else:
                cursor = db.execute("UPDATE products SET name=?,quantity=?,price_cents=? WHERE id=?",
                                    (*values, product_id))
                if not cursor.rowcount:
                    raise LookupError("Produto não encontrado.")
            row = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            return dict(row)

    def delete(self, product_id):
        with closing(self.connect()) as db, db:
            if not db.execute("DELETE FROM products WHERE id=?", (product_id,)).rowcount:
                raise LookupError("Produto não encontrado.")

    def summary(self):
        with closing(self.connect()) as db:
            return dict(db.execute("""SELECT COUNT(*) AS products,
                COALESCE(SUM(quantity),0) AS units,
                COALESCE(SUM(quantity*price_cents),0) AS total_value_cents FROM products""").fetchone())


def make_handler(inventory):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, data=None):
            body = b"" if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def read_json(self):
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Content-Type deve ser application/json.")
            if self.headers.get("Transfer-Encoding"):
                raise ValueError("Transfer-Encoding não suportado.")
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise ValueError("Content-Length inválido.") from None
            if not 1 <= size <= 16384:
                raise ValueError("O corpo deve ter entre 1 e 16384 bytes.")
            try:
                return json.loads(self.rfile.read(size).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ValueError("JSON inválido.") from None

        def route(self):
            path = urlsplit(self.path).path.rstrip("/") or "/"
            method = self.command
            try:
                if path == "/health" and method == "GET":
                    return self.respond(200, {"status": "ok"})
                if path == "/summary" and method == "GET":
                    return self.respond(200, inventory.summary())
                if path == "/products":
                    if method == "GET":
                        return self.respond(200, inventory.list())
                    if method == "POST":
                        return self.respond(201, inventory.save(self.read_json()))
                    return self.respond(405, {"error": "Método não permitido."})
                parts = path.split("/")
                if len(parts) == 3 and parts[1] == "products" and parts[2].isascii() and parts[2].isdigit() and len(parts[2]) <= 18:
                    product_id = int(parts[2])
                    if method == "GET":
                        return self.respond(200, inventory.get(product_id))
                    if method == "PUT":
                        return self.respond(200, inventory.save(self.read_json(), product_id))
                    if method == "DELETE":
                        inventory.delete(product_id)
                        return self.respond(204)
                    return self.respond(405, {"error": "Método não permitido."})
                return self.respond(404, {"error": "Rota não encontrada."})
            except ValueError as error:
                self.respond(400, {"error": str(error)})
            except LookupError as error:
                self.respond(404, {"error": str(error)})
            except sqlite3.Error:
                self.respond(503, {"error": "Banco indisponível. Tente novamente."})

        do_GET = do_POST = do_PUT = do_DELETE = route

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="estoque.db")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(Inventory(args.db)))
    print(f"API local em http://127.0.0.1:{args.port}; Ctrl+C para encerrar.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
