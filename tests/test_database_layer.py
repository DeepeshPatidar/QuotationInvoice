import os
import tempfile
import unittest

from app.database import Database


class DatabaseLayerTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.db = Database(self.path)

    def tearDown(self):
        self.db.conn.close()
        try:
            os.remove(self.path)
        except PermissionError:
            pass

    def test_migrations_and_customer_repository(self):
        self.assertGreaterEqual(
            self.db.conn.execute("PRAGMA user_version").fetchone()[0], 1
        )
        customer_id = self.db.add_customer("Layered Customer")

        customer = self.db.get_customer(customer_id)

        self.assertEqual(customer["name"], "Layered Customer")
        self.db.delete_customer(customer_id)
        self.assertIsNone(self.db.get_customer(customer_id))


if __name__ == "__main__":
    unittest.main()
