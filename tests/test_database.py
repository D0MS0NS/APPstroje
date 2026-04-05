from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import database as database_module
from database import Database


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_app.db"
        self.db = Database(self.db_path)

    def tearDown(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def _create_customer(self, name: str = "Test Customer") -> int:
        return self.db.execute(
            "INSERT INTO customers(name, full_name, company) VALUES (?, ?, ?)",
            (name, name, "Acme"),
        )

    def _create_machine(self, name: str = "Minibagr", status: str = "volny") -> int:
        return self.db.execute(
            "INSERT INTO machines(name, inventory_number, category, status, daily_rate, deposit) VALUES (?, ?, ?, ?, ?, ?)",
            (name, f"INV-{name}", "Technika", status, 1500, 5000),
        )

    def test_generate_contract_number_skips_used_numbers(self) -> None:
        year = datetime.now().strftime("%Y")
        customer_id = self._create_customer()
        self.db.execute(
            """
            INSERT INTO contracts(contract_number, customer_id, created_at, rental_from, rental_to)
            VALUES (?, ?, ?, ?, ?)
            """,
            (f"{year}-0001", customer_id, "2026-04-01", "2026-04-02", "2026-04-03"),
        )
        self.db.execute(
            """
            INSERT INTO contracts(contract_number, customer_id, created_at, rental_from, rental_to)
            VALUES (?, ?, ?, ?, ?)
            """,
            (f"{year}-0003", customer_id, "2026-04-01", "2026-04-04", "2026-04-05"),
        )

        self.assertEqual(self.db.generate_contract_number(), f"{year}-0002")

    def test_check_machine_conflicts_returns_contract_and_reservation_hits(self) -> None:
        customer_id = self._create_customer()
        machine_id = self._create_machine()
        contract_id = self.db.execute(
            """
            INSERT INTO contracts(contract_number, customer_id, created_at, rental_from, rental_to, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("2026-0001", customer_id, "2026-04-01", "2026-04-10", "2026-04-12", "aktivn\u00ed"),
        )
        self.db.execute(
            "INSERT INTO contract_items(contract_id, machine_id) VALUES (?, ?)",
            (contract_id, machine_id),
        )
        reservation_id = self.db.execute(
            """
            INSERT INTO reservations(reservation_number, customer_id, created_at, reserved_from, reserved_to, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("R-2026-0001", customer_id, "2026-04-01", "2026-04-11", "2026-04-13", "rezervace"),
        )
        self.db.execute(
            "INSERT INTO reservation_items(reservation_id, machine_id) VALUES (?, ?)",
            (reservation_id, machine_id),
        )

        conflicts = self.db.check_machine_conflicts(machine_id, "2026-04-11", "2026-04-11")

        self.assertTrue(any("2026-0001" in item for item in conflicts))
        self.assertTrue(any("R-2026-0001" in item for item in conflicts))

    def test_create_reservation_record_blocks_overlapping_machine(self) -> None:
        customer_id = self._create_customer()
        machine_id = self._create_machine()
        self.db.create_reservation_record(customer_id, "2026-04-10", "2026-04-12", 1000, 500, "Prvni rezervace", [machine_id])

        with self.assertRaises(ValueError):
            self.db.create_reservation_record(customer_id, "2026-04-11", "2026-04-13", 1000, 500, "Kolize", [machine_id])

    def test_edit_reservation_ignores_its_own_interval_when_rechecking(self) -> None:
        customer_id = self._create_customer()
        machine_id = self._create_machine()
        reservation_id = self.db.create_reservation_record(customer_id, "2026-04-10", "2026-04-12", 1000, 500, "Puvodni", [machine_id])

        updated_id = self.db.create_reservation_record(
            customer_id,
            "2026-04-10",
            "2026-04-12",
            1200,
            500,
            "Upraveno",
            [machine_id],
            reservation_id=reservation_id,
        )

        self.assertEqual(updated_id, reservation_id)
        self.assertEqual(
            self.db.fetchone("SELECT total_price FROM reservations WHERE id=?", (reservation_id,))["total_price"],
            1200,
        )

    def test_create_contract_record_sets_machine_to_rented(self) -> None:
        customer_id = self._create_customer()
        machine_id = self._create_machine()

        contract_id = self.db.create_contract_record(
            customer_id,
            "2026-04-20",
            "2026-04-22",
            2000,
            500,
            0,
            "Hotove",
            "",
            "Test",
            [machine_id],
            "OK",
        )

        self.assertIsNotNone(self.db.fetchone("SELECT id FROM contracts WHERE id=?", (contract_id,)))
        self.assertEqual(
            self.db.fetchone("SELECT status FROM machines WHERE id=?", (machine_id,))["status"],
            "p\u016fj\u010den\u00fd",
        )

    def test_delete_contract_removes_parent_and_items(self) -> None:
        customer_id = self._create_customer()
        machine_id = self._create_machine()
        contract_id = self.db.execute(
            """
            INSERT INTO contracts(contract_number, customer_id, created_at, rental_from, rental_to)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("2026-0010", customer_id, "2026-04-01", "2026-04-02", "2026-04-03"),
        )
        self.db.execute(
            "INSERT INTO contract_items(contract_id, machine_id) VALUES (?, ?)",
            (contract_id, machine_id),
        )

        self.db.delete_contract(contract_id)

        self.assertIsNone(self.db.fetchone("SELECT id FROM contracts WHERE id=?", (contract_id,)))
        self.assertEqual(len(self.db.fetchall("SELECT id FROM contract_items WHERE contract_id=?", (contract_id,))), 0)

    def test_delete_contract_recomputes_machine_status_to_free(self) -> None:
        customer_id = self._create_customer()
        machine_id = self._create_machine()
        contract_id = self.db.create_contract_record(
            customer_id,
            "2026-04-20",
            "2026-04-22",
            2000,
            500,
            0,
            "Hotove",
            "",
            "Test",
            [machine_id],
            "OK",
        )

        self.db.delete_contract(contract_id)

        self.assertEqual(
            self.db.fetchone("SELECT status FROM machines WHERE id=?", (machine_id,))["status"],
            "voln\u00fd",
        )

    def test_recompute_machine_status_prefers_service_over_free(self) -> None:
        machine_id = self._create_machine()
        self.db.execute(
            """
            INSERT INTO service_records(machine_id, service_date, service_type, cost, provider, notes, next_service_date, status, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (machine_id, "2026-04-01", "Kontrola", 0, "", "", "2026-05-01", "otev\u0159en\u00fd", ""),
        )

        self.db.recompute_machine_status(machine_id)

        self.assertEqual(
            self.db.fetchone("SELECT status FROM machines WHERE id=?", (machine_id,))["status"],
            "servis",
        )

    def test_finish_service_sets_machine_to_free_when_no_active_contract(self) -> None:
        machine_id = self._create_machine(status="servis")
        record_id = self.db.execute(
            """
            INSERT INTO service_records(machine_id, service_date, service_type, cost, provider, notes, next_service_date, status, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (machine_id, "2026-04-01", "Kontrola", 0, "", "", "2026-05-01", "otev\u0159en\u00fd", ""),
        )

        self.db.finish_service(machine_id, record_id)

        self.assertEqual(
            self.db.fetchone("SELECT status FROM machines WHERE id=?", (machine_id,))["status"],
            "voln\u00fd",
        )

    def test_export_table_to_csv_rejects_unknown_table(self) -> None:
        with self.assertRaises(ValueError):
            self.db.export_table_to_csv("contracts; DROP TABLE contracts", "bad")

    def test_export_table_to_csv_writes_header_and_rows(self) -> None:
        self._create_customer("Alice")
        export_dir = Path(self.temp_dir.name) / "exports"
        export_dir.mkdir()

        with patch.object(database_module, "EXPORTS_DIR", export_dir):
            path = self.db.export_table_to_csv("customers", "customers")

        self.assertTrue(path.exists())
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        self.assertGreaterEqual(len(rows), 2)
        self.assertIn("name", rows[0])
        self.assertEqual(rows[1][1], "Alice")


if __name__ == "__main__":
    unittest.main()
