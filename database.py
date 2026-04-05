from __future__ import annotations
import csv
import shutil
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Iterable

from settings import BACKUPS_DIR, DB_PATH, DEFAULT_COMPANY, EXPORTS_DIR, AUTO_BACKUPS_KEEP


class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        self._migrate_schema()
        self._ensure_default_settings()
        self._normalize_data()

    def _table_exists(self, table_name: str) -> bool:
        row = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone()
        return row is not None

    def _get_columns(self, table_name: str) -> set[str]:
        if not self._table_exists(table_name):
            return set()
        return {row['name'] for row in self.conn.execute(f"PRAGMA table_info({table_name})")}

    def _add_column_if_missing(self, table_name: str, column_name: str, sql_type: str) -> None:
        cols = self._get_columns(table_name)
        if column_name not in cols:
            self.conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}")

    def _copy_if_empty(self, table_name: str, target: str, source_candidates: list[str]) -> None:
        cols = self._get_columns(table_name)
        if target not in cols:
            return
        for source in source_candidates:
            if source in cols and source != target:
                self.conn.execute(f"UPDATE {table_name} SET {target}=COALESCE(NULLIF({target}, ''), {source}, '') WHERE COALESCE({target}, '')='' ")
                break

    def _create_tables(self) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                inventory_number TEXT UNIQUE,
                model TEXT,
                serial_number TEXT,
                daily_rate REAL DEFAULT 0,
                weekend_rate REAL DEFAULT 0,
                weekly_rate REAL DEFAULT 0,
                monthly_rate REAL DEFAULT 0,
                deposit REAL DEFAULT 0,
                status TEXT DEFAULT 'volný',
                notes TEXT DEFAULT '',
                photo_path TEXT DEFAULT '',
                accessories TEXT DEFAULT '',
                last_service_date TEXT DEFAULT '',
                next_service_date TEXT DEFAULT '',
                service_due_motohours REAL DEFAULT 0,
                motohours REAL DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                full_name TEXT DEFAULT '',
                company TEXT DEFAULT '',
                ico TEXT DEFAULT '',
                dic TEXT DEFAULT '',
                address TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                email TEXT DEFAULT '',
                id_card TEXT DEFAULT '',
                driver_license TEXT DEFAULT '',
                passport TEXT DEFAULT '',
                notes TEXT DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_number TEXT UNIQUE,
                customer_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                rental_from TEXT NOT NULL,
                rental_to TEXT NOT NULL,
                start_date TEXT DEFAULT '',
                end_date TEXT DEFAULT '',
                returned_at TEXT DEFAULT '',
                return_date TEXT DEFAULT '',
                total_price REAL DEFAULT 0,
                deposit REAL DEFAULT 0,
                paid_amount REAL DEFAULT 0,
                payment_method TEXT DEFAULT '',
                issue_signature TEXT DEFAULT '',
                return_signature TEXT DEFAULT '',
                issue_photo_path TEXT DEFAULT '',
                return_photo_path TEXT DEFAULT '',
                return_extra_charge REAL DEFAULT 0,
                deposit_returned REAL DEFAULT 0,
                status TEXT DEFAULT 'aktivní',
                notes TEXT DEFAULT '',
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contract_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER NOT NULL,
                machine_id INTEGER NOT NULL,
                issue_condition TEXT DEFAULT '',
                return_condition TEXT DEFAULT '',
                accessories_issued TEXT DEFAULT '',
                accessories_returned TEXT DEFAULT '',
                damage_notes TEXT DEFAULT '',
                FOREIGN KEY(contract_id) REFERENCES contracts(id),
                FOREIGN KEY(machine_id) REFERENCES machines(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reservation_number TEXT UNIQUE,
                customer_id INTEGER NOT NULL,
                created_at TEXT DEFAULT '',
                reserved_from TEXT NOT NULL,
                reserved_to TEXT NOT NULL,
                total_price REAL DEFAULT 0,
                deposit REAL DEFAULT 0,
                status TEXT DEFAULT 'rezervace',
                notes TEXT DEFAULT '',
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reservation_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reservation_id INTEGER NOT NULL,
                machine_id INTEGER NOT NULL,
                FOREIGN KEY(reservation_id) REFERENCES reservations(id),
                FOREIGN KEY(machine_id) REFERENCES machines(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS service_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                service_date TEXT NOT NULL,
                service_type TEXT DEFAULT '',
                cost REAL DEFAULT 0,
                provider TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                next_service_date TEXT DEFAULT '',
                service_motohours REAL DEFAULT 0,
                next_service_motohours REAL DEFAULT 0,
                status TEXT DEFAULT 'otevřený',
                completed_at TEXT DEFAULT '',
                FOREIGN KEY(machine_id) REFERENCES machines(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS machine_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                caption TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT '',
                FOREIGN KEY(machine_id) REFERENCES machines(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS machine_accessories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                accessory_name TEXT NOT NULL,
                accessory_price REAL DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT '',
                FOREIGN KEY(machine_id) REFERENCES machines(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS machine_accessory_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                preset_name TEXT NOT NULL,
                accessories_text TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT '',
                FOREIGN KEY(machine_id) REFERENCES machines(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT DEFAULT ''
            )
        """)
        self.conn.commit()

    def _migrate_schema(self) -> None:
        for name, sql_type in {
            'name':"TEXT DEFAULT ''",'category':"TEXT DEFAULT ''",'inventory_number':"TEXT DEFAULT ''",'model':"TEXT DEFAULT ''",
            'serial_number':"TEXT DEFAULT ''",'daily_rate':'REAL DEFAULT 0','deposit':'REAL DEFAULT 0','status':"TEXT DEFAULT 'volný'",
            'notes':"TEXT DEFAULT ''",'photo_path':"TEXT DEFAULT ''",'accessories':"TEXT DEFAULT ''",'last_service_date':"TEXT DEFAULT ''",'next_service_date':"TEXT DEFAULT ''",'service_due_motohours':'REAL DEFAULT 0','motohours':'REAL DEFAULT 0',
        }.items(): self._add_column_if_missing('machines', name, sql_type)
        for name, sql_type in {
            'weekend_rate': 'REAL DEFAULT 0',
            'weekly_rate': 'REAL DEFAULT 0',
            'monthly_rate': 'REAL DEFAULT 0',
        }.items():
            self._add_column_if_missing('machines', name, sql_type)
        self._copy_if_empty('machines','name',['machine_name','title'])
        self._copy_if_empty('machines','inventory_number',['inventory_no','inv_number','inventory'])
        self._copy_if_empty('machines','daily_rate',['price_per_day','price'])
        self._copy_if_empty('machines','notes',['note','description'])

        for name, sql_type in {
            'name':"TEXT DEFAULT ''",'full_name':"TEXT DEFAULT ''",'company':"TEXT DEFAULT ''",'ico':"TEXT DEFAULT ''",'dic':"TEXT DEFAULT ''",
            'address':"TEXT DEFAULT ''",'phone':"TEXT DEFAULT ''",'email':"TEXT DEFAULT ''",'id_card':"TEXT DEFAULT ''",'driver_license':"TEXT DEFAULT ''",'passport':"TEXT DEFAULT ''",'notes':"TEXT DEFAULT ''",
        }.items(): self._add_column_if_missing('customers', name, sql_type)
        self._copy_if_empty('customers','name',['full_name','customer_name','contact_name'])
        self._copy_if_empty('customers','full_name',['name','customer_name','contact_name'])
        self._copy_if_empty('customers','company',['company_name','firm'])
        self._copy_if_empty('customers','phone',['telephone','mobile'])

        for name, sql_type in {
            'contract_number':"TEXT DEFAULT ''",'customer_id':'INTEGER DEFAULT 0','created_at':"TEXT DEFAULT ''",
            'rental_from':"TEXT DEFAULT ''",'rental_to':"TEXT DEFAULT ''",'start_date':"TEXT DEFAULT ''",'end_date':"TEXT DEFAULT ''",
            'returned_at':"TEXT DEFAULT ''",'return_date':"TEXT DEFAULT ''",'total_price':'REAL DEFAULT 0','deposit':'REAL DEFAULT 0','paid_amount':'REAL DEFAULT 0',
            'payment_method':"TEXT DEFAULT ''",'issue_signature':"TEXT DEFAULT ''",'return_signature':"TEXT DEFAULT ''",'issue_photo_path':"TEXT DEFAULT ''",
            'return_photo_path':"TEXT DEFAULT ''",'return_extra_charge':'REAL DEFAULT 0','deposit_returned':'REAL DEFAULT 0','status':"TEXT DEFAULT 'aktivní'",'notes':"TEXT DEFAULT ''",
        }.items(): self._add_column_if_missing('contracts', name, sql_type)
        self._add_column_if_missing('contracts', 'pricing_mode', "TEXT DEFAULT 'day'")
        self._copy_if_empty('contracts','rental_from',['start_date','date_from'])
        self._copy_if_empty('contracts','rental_to',['end_date','date_to'])
        self._copy_if_empty('contracts','start_date',['rental_from'])
        self._copy_if_empty('contracts','end_date',['rental_to'])
        self._copy_if_empty('contracts','returned_at',['return_date'])
        self._copy_if_empty('contracts','return_date',['returned_at'])
        self._copy_if_empty('contracts','notes',['note','description'])

        for name, sql_type in {
            'issue_condition':"TEXT DEFAULT ''",'return_condition':"TEXT DEFAULT ''",'accessories_issued':"TEXT DEFAULT ''",'accessories_returned':"TEXT DEFAULT ''",'damage_notes':"TEXT DEFAULT ''",'accessories_total': 'REAL DEFAULT 0',
        }.items(): self._add_column_if_missing('contract_items', name, sql_type)
        for name, sql_type in {
            'machine_id':'INTEGER NOT NULL','accessory_name':"TEXT DEFAULT ''",'accessory_price':'REAL DEFAULT 0','sort_order':'INTEGER DEFAULT 0','created_at':"TEXT DEFAULT ''",
        }.items(): self._add_column_if_missing('machine_accessories', name, sql_type)

        for name, sql_type in {
            'reservation_number':"TEXT DEFAULT ''",'customer_id':'INTEGER DEFAULT 0','created_at':"TEXT DEFAULT ''",'reserved_from':"TEXT DEFAULT ''",'reserved_to':"TEXT DEFAULT ''",
            'total_price':'REAL DEFAULT 0','deposit':'REAL DEFAULT 0','status':"TEXT DEFAULT 'rezervace'",'notes':"TEXT DEFAULT ''",
        }.items(): self._add_column_if_missing('reservations', name, sql_type)

        for name, sql_type in {
            'service_date':"TEXT DEFAULT ''",'service_type':"TEXT DEFAULT ''",'cost':'REAL DEFAULT 0','provider':"TEXT DEFAULT ''",'notes':"TEXT DEFAULT ''",'next_service_date':"TEXT DEFAULT ''",'service_motohours':'REAL DEFAULT 0','next_service_motohours':'REAL DEFAULT 0','status':"TEXT DEFAULT 'otevřený'",'completed_at':"TEXT DEFAULT ''",
        }.items():
            self._add_column_if_missing('service_records', name, sql_type)

        for name, sql_type in {
            'machine_id':'INTEGER NOT NULL','path':"TEXT NOT NULL",'caption':"TEXT DEFAULT ''",'sort_order':'INTEGER DEFAULT 0','created_at':"TEXT DEFAULT ''",
        }.items():
            self._add_column_if_missing('machine_photos', name, sql_type)

        for name, sql_type in {
            'machine_id':'INTEGER NOT NULL','preset_name':"TEXT DEFAULT ''",'accessories_text':"TEXT DEFAULT ''",'sort_order':'INTEGER DEFAULT 0','created_at':"TEXT DEFAULT ''",
        }.items():
            self._add_column_if_missing('machine_accessory_presets', name, sql_type)

        if self._table_exists('machine_photos'):
            machines_with_photo = self.fetchall("SELECT id, photo_path FROM machines WHERE COALESCE(photo_path,'')<>''")
            for row in machines_with_photo:
                exists = self.fetchone("SELECT id FROM machine_photos WHERE machine_id=? AND path=?", (row['id'], row['photo_path']))
                if not exists:
                    self.conn.execute(
                        "INSERT INTO machine_photos(machine_id, path, caption, sort_order, created_at) VALUES (?, ?, '', 0, ?)",
                        (row['id'], row['photo_path'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                    )
        self.conn.commit()

    def _ensure_default_settings(self) -> None:
        for k, v in DEFAULT_COMPANY.items():
            self.conn.execute("INSERT OR IGNORE INTO app_settings(setting_key, setting_value) VALUES (?, ?)", (k, v))
        self.conn.commit()

    def _normalize_data(self) -> None:
        self.conn.execute("UPDATE customers SET full_name = name WHERE COALESCE(full_name,'')='' AND COALESCE(name,'')<>''")
        self.conn.execute("UPDATE customers SET name = full_name WHERE COALESCE(name,'')='' AND COALESCE(full_name,'')<>''")
        self.conn.execute("UPDATE contracts SET start_date = rental_from WHERE COALESCE(start_date,'')='' AND COALESCE(rental_from,'')<>''")
        self.conn.execute("UPDATE contracts SET end_date = rental_to WHERE COALESCE(end_date,'')='' AND COALESCE(rental_to,'')<>''")
        self.conn.execute("UPDATE contracts SET rental_from = start_date WHERE COALESCE(rental_from,'')='' AND COALESCE(start_date,'')<>''")
        self.conn.execute("UPDATE contracts SET rental_to = end_date WHERE COALESCE(rental_to,'')='' AND COALESCE(end_date,'')<>''")
        self.conn.commit()

    def fetchall(self, query: str, params: Iterable[Any] = ()): return self.conn.execute(query, tuple(params)).fetchall()
    def fetchone(self, query: str, params: Iterable[Any] = ()): return self.conn.execute(query, tuple(params)).fetchone()
    def execute(self, query: str, params: Iterable[Any] = ()) -> int:
        cur = self.conn.execute(query, tuple(params)); self.conn.commit(); return cur.lastrowid
    def close(self) -> None:
        self.conn.close()

    def backup_database(self) -> Path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S'); dst = BACKUPS_DIR / f'backup_{ts}.db'; self.conn.commit(); shutil.copy2(self.db_path, dst); return dst
    def get_settings(self) -> dict[str, str]: return {r['setting_key']: r['setting_value'] for r in self.fetchall('SELECT setting_key, setting_value FROM app_settings')}
    def save_settings(self, values: dict[str, str]) -> None:
        for k, v in values.items():
            self.execute('INSERT INTO app_settings(setting_key, setting_value) VALUES (?, ?) ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value', (k, v))

    def generate_contract_number(self) -> str:
        year = datetime.now().strftime('%Y')
        rows = self.fetchall(
            'SELECT contract_number FROM contracts WHERE contract_number LIKE ?',
            (f'{year}-%',)
        )
        used = set()
        for row in rows:
            value = (row['contract_number'] or '').strip()
            if not value.startswith(f'{year}-'):
                continue
            try:
                used.add(int(value.split('-')[-1]))
            except (ValueError, TypeError):
                continue
        next_num = 1
        while next_num in used:
            next_num += 1
        return f"{year}-{next_num:04d}"

    def generate_reservation_number(self) -> str:
        year = datetime.now().strftime('%Y')
        rows = self.fetchall(
            'SELECT reservation_number FROM reservations WHERE reservation_number LIKE ?',
            (f'R-{year}-%',)
        )
        used = set()
        for row in rows:
            value = (row['reservation_number'] or '').strip()
            if not value.startswith(f'R-{year}-'):
                continue
            try:
                used.add(int(value.split('-')[-1]))
            except (ValueError, TypeError):
                continue
        next_num = 1
        while next_num in used:
            next_num += 1
        return f"R-{year}-{next_num:04d}"

    def check_machine_conflicts(self, machine_id: int, date_from: str, date_to: str) -> list[str]:
        conflicts=[]; m=self.fetchone('SELECT * FROM machines WHERE id=?',(machine_id,))
        if not m: return ['Stroj nebyl nalezen.']
        if (m['status'] or '') in ('servis','blokovaný','vyřazený'): conflicts.append(f"{m['name']} je ve stavu {m['status']}.")
        rows=self.fetchall("""
            SELECT contract_number AS ref, rental_from AS d1, rental_to AS d2, 'smlouva' AS typ FROM contracts
            WHERE status='aktivní' AND id IN (SELECT contract_id FROM contract_items WHERE machine_id=?) AND NOT (COALESCE(rental_to, end_date, '') < ? OR COALESCE(rental_from, start_date, '') > ?)
            UNION ALL
            SELECT reservation_number AS ref, reserved_from AS d1, reserved_to AS d2, 'rezervace' AS typ FROM reservations
            WHERE status IN ('rezervace','potvrzeno') AND id IN (SELECT reservation_id FROM reservation_items WHERE machine_id=?) AND NOT (reserved_to < ? OR reserved_from > ?)
            ORDER BY d1
        """, (machine_id, date_from, date_to, machine_id, date_from, date_to))
        for r in rows: conflicts.append(f"{m['name']}: kolize s {r['typ']} {r['ref']} ({r['d1']} až {r['d2']})")
        return conflicts

    def get_dashboard_stats(self) -> dict[str, float]:
        today=date.today().strftime('%Y-%m-%d')
        soon=(date.today()+timedelta(days=14)).strftime('%Y-%m-%d')
        def count(q,p=()): row=self.fetchone(q,p); return float(row[0] if row else 0)
        service_due_date = count("SELECT COUNT(*) FROM machines WHERE COALESCE(next_service_date,'')<>'' AND next_service_date <= ?", (soon,))
        service_due_mh = count("SELECT COUNT(*) FROM machines WHERE COALESCE(service_due_motohours,0) > 0 AND COALESCE(motohours,0) >= COALESCE(service_due_motohours,0)")
        return {
            'machines_total': count("SELECT COUNT(*) FROM machines"),
            'machines_free': count("SELECT COUNT(*) FROM machines WHERE status='volný'"),
            'machines_rented': count("SELECT COUNT(*) FROM machines WHERE status='půjčený'"),
            'machines_service': count("SELECT COUNT(*) FROM machines WHERE status='servis'"),
            'contracts_active': count("SELECT COUNT(*) FROM contracts WHERE status='aktivní'"),
            'contracts_overdue': count("SELECT COUNT(*) FROM contracts WHERE status='po termínu' OR (status='aktivní' AND COALESCE(rental_to,end_date,'') < ?)", (today,)),
            'returns_today': count("SELECT COUNT(*) FROM contracts WHERE status='aktivní' AND COALESCE(rental_to,end_date,'') = ?", (today,)),
            'unpaid': count("SELECT COUNT(*) FROM contracts WHERE COALESCE(paid_amount,0) < (COALESCE(total_price,0)+COALESCE(deposit,0)+COALESCE(return_extra_charge,0)) AND status='aktivní'"),
            'reservations_active': count("SELECT COUNT(*) FROM reservations WHERE status IN ('rezervace','potvrzeno') AND reserved_to >= ?", (today,)),
            'month_revenue': count("SELECT COALESCE(SUM(total_price + return_extra_charge),0) FROM contracts WHERE substr(COALESCE(created_at,rental_from,''),1,7)=substr(date('now'),1,7)"),
            'service_due': service_due_date + service_due_mh,
            'service_due_by_date': service_due_date,
            'service_due_by_motohours': service_due_mh,
        }

    def get_recent_contracts(self, limit: int = 8):
        return self.fetchall("SELECT c.*, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name FROM contracts c LEFT JOIN customers cu ON cu.id=c.customer_id ORDER BY c.id DESC LIMIT ?", (limit,))

    def get_monthly_contract_counts(self, months: int = 6):
        rows=[]
        for i in range(months-1, -1, -1):
            d=(date.today().replace(day=1) - timedelta(days=1)).replace(day=1) if False else None
        # simple python aggregation for reliability
        data=self.fetchall("SELECT created_at, rental_from FROM contracts")
        from collections import Counter
        ctr=Counter()
        today=date.today().replace(day=1)
        labels=[]
        cur=today
        for i in range(months-1, -1, -1):
            y=cur.year; m=cur.month-i
        # build sequence manually
        y=today.year; m=today.month-months+1
        while m<=0:
            m+=12; y-=1
        seq=[]
        yy,mm=y,m
        for _ in range(months):
            seq.append((yy,mm))
            mm+=1
            if mm==13: mm=1; yy+=1
        for r in data:
            key=(str(r['created_at'] or r['rental_from'] or '')[:7])
            ctr[key]+=1
        out=[]
        for yy,mm in seq:
            ym=f"{yy:04d}-{mm:02d}"; out.append({'month_label':f"{mm:02d}/{yy}",'cnt':ctr.get(ym,0)})
        return out

    def get_upcoming_returns(self, limit:int=6):
        today=date.today().strftime('%Y-%m-%d')
        return self.fetchall("""SELECT c.*, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name, GROUP_CONCAT(m.name || ' (' || COALESCE(m.inventory_number,'') || ')', ', ') AS machines FROM contracts c LEFT JOIN customers cu ON cu.id=c.customer_id LEFT JOIN contract_items ci ON ci.contract_id=c.id LEFT JOIN machines m ON m.id=ci.machine_id WHERE c.status='aktivní' AND COALESCE(c.rental_to, c.end_date, '') >= ? GROUP BY c.id ORDER BY COALESCE(c.rental_to, c.end_date, '') ASC LIMIT ?""", (today,limit))
    def get_upcoming_reservations(self, limit:int=6):
        today=date.today().strftime('%Y-%m-%d')
        return self.fetchall("""SELECT r.*, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name, GROUP_CONCAT(m.name || ' (' || COALESCE(m.inventory_number,'') || ')', ', ') AS machines FROM reservations r LEFT JOIN customers cu ON cu.id=r.customer_id LEFT JOIN reservation_items ri ON ri.reservation_id=r.id LEFT JOIN machines m ON m.id=ri.machine_id WHERE r.status IN ('rezervace','potvrzeno') AND r.reserved_to >= ? GROUP BY r.id ORDER BY r.reserved_from ASC LIMIT ?""", (today,limit))
    def get_top_machines(self, limit:int=5): return self.fetchall("SELECT m.name, COUNT(ci.id) AS cnt FROM machines m LEFT JOIN contract_items ci ON ci.machine_id=m.id GROUP BY m.id, m.name ORDER BY cnt DESC, m.name ASC LIMIT ?", (limit,))
    def get_service_due_machines(self, limit:int=8): return self.fetchall("SELECT * FROM machines WHERE (COALESCE(next_service_date,'')<>'' AND next_service_date <= ?) OR (COALESCE(service_due_motohours,0) > 0 AND COALESCE(motohours,0) >= COALESCE(service_due_motohours,0)) ORDER BY CASE WHEN COALESCE(next_service_date,'')='' THEN '9999-12-31' ELSE next_service_date END ASC, id DESC LIMIT ?", ((date.today()+timedelta(days=30)).strftime('%Y-%m-%d'), limit))

    def get_deadline_alerts(self, limit: int = 14) -> list[sqlite3.Row]:
        today = date.today()
        today_str = today.strftime('%Y-%m-%d')
        soon = (today + timedelta(days=3)).strftime('%Y-%m-%d')
        return self.fetchall("""
            SELECT * FROM (
                SELECT
                    'contract_overdue' AS alert_type,
                    c.id AS source_id,
                    c.contract_number AS ref,
                    COALESCE(c.rental_to, c.end_date, '') AS event_date,
                    COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name,
                    GROUP_CONCAT(m.name || ' (' || COALESCE(m.inventory_number,'' ) || ')', ', ') AS machines,
                    NULL AS amount,
                    'contract' AS source_kind,
                    'Po terminu' AS title,
                    c.status AS status
                FROM contracts c
                LEFT JOIN customers cu ON cu.id=c.customer_id
                LEFT JOIN contract_items ci ON ci.contract_id=c.id
                LEFT JOIN machines m ON m.id=ci.machine_id
                WHERE c.status='po termínu' OR (c.status='aktivní' AND COALESCE(c.rental_to, c.end_date, '') <> '' AND COALESCE(c.rental_to, c.end_date, '') < ?)
                GROUP BY c.id
                UNION ALL
                SELECT
                    'contract_due_soon' AS alert_type,
                    c.id AS source_id,
                    c.contract_number AS ref,
                    COALESCE(c.rental_to, c.end_date, '') AS event_date,
                    COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name,
                    GROUP_CONCAT(m.name || ' (' || COALESCE(m.inventory_number,'' ) || ')', ', ') AS machines,
                    NULL AS amount,
                    'contract' AS source_kind,
                    'Blizi se vratka' AS title,
                    c.status AS status
                FROM contracts c
                LEFT JOIN customers cu ON cu.id=c.customer_id
                LEFT JOIN contract_items ci ON ci.contract_id=c.id
                LEFT JOIN machines m ON m.id=ci.machine_id
                WHERE c.status='aktivní' AND COALESCE(c.rental_to, c.end_date, '') BETWEEN ? AND ?
                GROUP BY c.id
                UNION ALL
                SELECT
                    'contract_unpaid' AS alert_type,
                    c.id AS source_id,
                    c.contract_number AS ref,
                    COALESCE(c.rental_to, c.end_date, '') AS event_date,
                    COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name,
                    GROUP_CONCAT(m.name || ' (' || COALESCE(m.inventory_number,'' ) || ')', ', ') AS machines,
                    (COALESCE(c.total_price,0)+COALESCE(c.deposit,0)+COALESCE(c.return_extra_charge,0)-COALESCE(c.paid_amount,0)) AS amount,
                    'contract' AS source_kind,
                    'Dluh k uhrade' AS title,
                    c.status AS status
                FROM contracts c
                LEFT JOIN customers cu ON cu.id=c.customer_id
                LEFT JOIN contract_items ci ON ci.contract_id=c.id
                LEFT JOIN machines m ON m.id=ci.machine_id
                WHERE c.status='aktivní' AND COALESCE(c.paid_amount,0) < (COALESCE(c.total_price,0)+COALESCE(c.deposit,0)+COALESCE(c.return_extra_charge,0))
                GROUP BY c.id
                UNION ALL
                SELECT
                    'reservation_soon' AS alert_type,
                    r.id AS source_id,
                    r.reservation_number AS ref,
                    COALESCE(r.reserved_from, '') AS event_date,
                    COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name,
                    GROUP_CONCAT(m.name || ' (' || COALESCE(m.inventory_number,'' ) || ')', ', ') AS machines,
                    NULL AS amount,
                    'reservation' AS source_kind,
                    'Blizi se rezervace' AS title,
                    r.status AS status
                FROM reservations r
                LEFT JOIN customers cu ON cu.id=r.customer_id
                LEFT JOIN reservation_items ri ON ri.reservation_id=r.id
                LEFT JOIN machines m ON m.id=ri.machine_id
                WHERE r.status IN ('rezervace','potvrzeno') AND COALESCE(r.reserved_from,'') BETWEEN ? AND ?
                GROUP BY r.id
            )
            ORDER BY
                CASE alert_type
                    WHEN 'contract_overdue' THEN 0
                    WHEN 'contract_unpaid' THEN 1
                    WHEN 'contract_due_soon' THEN 2
                    WHEN 'reservation_soon' THEN 3
                    ELSE 9
                END,
                CASE WHEN COALESCE(event_date,'')='' THEN '9999-12-31' ELSE event_date END ASC,
                source_id DESC
            LIMIT ?
        """, (today_str, today_str, soon, today_str, soon, limit))

    def get_customer_summary(self, customer_id:int) -> dict[str, Any]:
        customer=self.fetchone('SELECT * FROM customers WHERE id=?',(customer_id,))
        active=self.fetchall("SELECT c.*, GROUP_CONCAT(m.name || ' (' || COALESCE(m.inventory_number,'') || ')', ', ') AS machines, GROUP_CONCAT(CASE WHEN COALESCE(ci.accessories_issued,'')<>'' THEN m.name || ': ' || REPLACE(ci.accessories_issued, CHAR(10), ', ') END, ' | ') AS accessories_summary FROM contracts c LEFT JOIN contract_items ci ON ci.contract_id=c.id LEFT JOIN machines m ON m.id=ci.machine_id WHERE c.customer_id=? AND c.status='aktivní' GROUP BY c.id ORDER BY COALESCE(c.rental_to,c.end_date,'') ASC", (customer_id,))
        history=self.fetchall("SELECT c.*, GROUP_CONCAT(m.name || ' (' || COALESCE(m.inventory_number,'') || ')', ', ') AS machines, GROUP_CONCAT(CASE WHEN COALESCE(ci.accessories_issued,'')<>'' THEN m.name || ': ' || REPLACE(ci.accessories_issued, CHAR(10), ', ') END, ' | ') AS accessories_summary FROM contracts c LEFT JOIN contract_items ci ON ci.contract_id=c.id LEFT JOIN machines m ON m.id=ci.machine_id WHERE c.customer_id=? GROUP BY c.id ORDER BY c.id DESC", (customer_id,))
        reservations=self.fetchall("SELECT r.*, GROUP_CONCAT(m.name || ' (' || COALESCE(m.inventory_number,'' ) || ')', ', ') AS machines FROM reservations r LEFT JOIN reservation_items ri ON ri.reservation_id=r.id LEFT JOIN machines m ON m.id=ri.machine_id WHERE r.customer_id=? GROUP BY r.id ORDER BY r.id DESC", (customer_id,))
        stats=self.fetchone("SELECT COUNT(*) AS contracts_count, COALESCE(SUM(total_price + return_extra_charge),0) AS total_spent, MAX(COALESCE(rental_from,start_date,'')) AS last_rental, COALESCE(SUM(CASE WHEN status='aktivní' THEN 1 ELSE 0 END),0) AS active_count, COALESCE(SUM(CASE WHEN COALESCE(paid_amount,0) < (COALESCE(total_price,0)+COALESCE(deposit,0)+COALESCE(return_extra_charge,0)) THEN (COALESCE(total_price,0)+COALESCE(deposit,0)+COALESCE(return_extra_charge,0)-COALESCE(paid_amount,0)) ELSE 0 END),0) AS open_balance FROM contracts WHERE customer_id=?", (customer_id,))
        active_reservations = self.fetchone("SELECT COUNT(*) AS cnt FROM reservations WHERE customer_id=? AND status IN ('rezervace','potvrzeno')", (customer_id,))
        return {
            'customer': customer,
            'active': active,
            'history': history,
            'contracts': history,
            'reservations': reservations,
            'stats': stats,
            'active_contracts': int(stats['active_count'] or 0) if stats else 0,
            'active_reservations': int(active_reservations['cnt'] or 0) if active_reservations else 0,
            'revenue': float(stats['total_spent'] or 0) if stats else 0.0,
        }

    def get_machine_summary(self, machine_id:int) -> dict[str, Any]:
        machine=self.fetchone('SELECT * FROM machines WHERE id=?',(machine_id,))
        history=self.fetchall("SELECT c.*, ci.accessories_issued, ci.accessories_total, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name FROM contract_items ci JOIN contracts c ON c.id=ci.contract_id LEFT JOIN customers cu ON cu.id=c.customer_id WHERE ci.machine_id=? ORDER BY c.id DESC", (machine_id,))
        reservations=self.fetchall("SELECT r.*, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name FROM reservation_items ri JOIN reservations r ON r.id=ri.reservation_id LEFT JOIN customers cu ON cu.id=r.customer_id WHERE ri.machine_id=? ORDER BY r.id DESC", (machine_id,))
        services=self.fetchall("SELECT * FROM service_records WHERE machine_id=? ORDER BY service_date DESC", (machine_id,))
        stats=self.fetchone("SELECT COUNT(DISTINCT c.id) AS contracts_count, COALESCE(SUM(c.total_price + c.return_extra_charge),0) AS total_revenue, MAX(COALESCE(c.rental_to,c.end_date,'')) AS last_return FROM contract_items ci JOIN contracts c ON c.id=ci.contract_id WHERE ci.machine_id=?", (machine_id,))
        timeline=self.fetchall("""
            SELECT *
            FROM (
                SELECT
                    c.id AS source_id,
                    'contract' AS source_kind,
                    'Vypujcka' AS event_type,
                    COALESCE(c.rental_from, c.start_date, '') AS date_from,
                    COALESCE(c.rental_to, c.end_date, '') AS date_to,
                    COALESCE(cu.name, cu.full_name, cu.company, '') AS partner_name,
                    c.contract_number AS ref,
                    c.status AS status,
                    (COALESCE(c.total_price,0) + COALESCE(c.return_extra_charge,0)) AS amount,
                    COALESCE(ci.accessories_issued, '') AS note
                FROM contract_items ci
                JOIN contracts c ON c.id=ci.contract_id
                LEFT JOIN customers cu ON cu.id=c.customer_id
                WHERE ci.machine_id=?
                UNION ALL
                SELECT
                    r.id AS source_id,
                    'reservation' AS source_kind,
                    'Rezervace' AS event_type,
                    COALESCE(r.reserved_from, '') AS date_from,
                    COALESCE(r.reserved_to, '') AS date_to,
                    COALESCE(cu.name, cu.full_name, cu.company, '') AS partner_name,
                    r.reservation_number AS ref,
                    r.status AS status,
                    COALESCE(r.total_price,0) AS amount,
                    COALESCE(r.notes, '') AS note
                FROM reservation_items ri
                JOIN reservations r ON r.id=ri.reservation_id
                LEFT JOIN customers cu ON cu.id=r.customer_id
                WHERE ri.machine_id=?
                UNION ALL
                SELECT
                    s.id AS source_id,
                    'service' AS source_kind,
                    'Servis' AS event_type,
                    COALESCE(s.service_date, '') AS date_from,
                    COALESCE(s.next_service_date, '') AS date_to,
                    COALESCE(s.provider, '') AS partner_name,
                    COALESCE(s.service_type, 'Servis') AS ref,
                    s.status AS status,
                    COALESCE(s.cost,0) AS amount,
                    COALESCE(s.notes, '') AS note
                FROM service_records s
                WHERE s.machine_id=?
            )
            ORDER BY CASE WHEN COALESCE(date_from,'')='' THEN '9999-12-31' ELSE date_from END DESC, source_id DESC
        """, (machine_id, machine_id, machine_id))
        return {
            'machine': machine,
            'history': history,
            'contracts': history,
            'reservations': reservations,
            'services': services,
            'service_records': services,
            'stats': stats,
            'timeline': timeline,
        }

    def get_contract_detail(self, contract_id:int) -> dict[str, Any]:
        contract=self.fetchone("SELECT c.*, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name FROM contracts c LEFT JOIN customers cu ON cu.id=c.customer_id WHERE c.id=?", (contract_id,))
        items=self.fetchall("SELECT ci.*, m.*, m.name AS machine_name, m.category AS machine_category FROM contract_items ci LEFT JOIN machines m ON m.id=ci.machine_id WHERE ci.contract_id=? ORDER BY m.name", (contract_id,))
        return {'contract':contract,'items':items}


    def get_reservation_detail(self, reservation_id:int) -> dict[str, Any]:
        reservation=self.fetchone("SELECT r.*, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name FROM reservations r LEFT JOIN customers cu ON cu.id=r.customer_id WHERE r.id=?", (reservation_id,))
        items=self.fetchall("SELECT m.*, m.name AS machine_name, m.category AS machine_category FROM reservation_items ri LEFT JOIN machines m ON m.id=ri.machine_id WHERE ri.reservation_id=? ORDER BY m.name", (reservation_id,))
        return {'reservation':reservation,'items':items}

    def get_reservations(self):
        return self.fetchall("SELECT r.*, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name, GROUP_CONCAT(m.name || ' (' || COALESCE(m.inventory_number,'') || ')', ', ') AS machines FROM reservations r LEFT JOIN customers cu ON cu.id=r.customer_id LEFT JOIN reservation_items ri ON ri.reservation_id=r.id LEFT JOIN machines m ON m.id=ri.machine_id GROUP BY r.id ORDER BY r.id DESC")

    def get_calendar_events(self, start_date: str | None = None, end_date: str | None = None):
        start_date = start_date or date.today().strftime('%Y-%m-%d')
        end_date = end_date or (date.today()+timedelta(days=45)).strftime('%Y-%m-%d')
        return self.fetchall("""
            SELECT *
            FROM (
                SELECT
                    c.id,
                    'contract' AS kind,
                    'Vypujcka' AS typ,
                    c.contract_number AS ref,
                    COALESCE(c.rental_from, c.start_date, '') AS date_from,
                    COALESCE(c.rental_to, c.end_date, '') AS date_to,
                    c.status AS status,
                    COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name,
                    GROUP_CONCAT(m.name || ' (' || COALESCE(m.inventory_number,'' ) || ')', ', ') AS machines
                FROM contracts c
                LEFT JOIN customers cu ON cu.id=c.customer_id
                LEFT JOIN contract_items ci ON ci.contract_id=c.id
                LEFT JOIN machines m ON m.id=ci.machine_id
                WHERE COALESCE(c.rental_from, c.start_date, '') <= ?
                  AND COALESCE(c.rental_to, c.end_date, '') >= ?
                GROUP BY c.id
                UNION ALL
                SELECT
                    r.id,
                    'reservation' AS kind,
                    'Rezervace' AS typ,
                    r.reservation_number AS ref,
                    COALESCE(r.reserved_from, '') AS date_from,
                    COALESCE(r.reserved_to, '') AS date_to,
                    r.status AS status,
                    COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name,
                    GROUP_CONCAT(m.name || ' (' || COALESCE(m.inventory_number,'' ) || ')', ', ') AS machines
                FROM reservations r
                LEFT JOIN customers cu ON cu.id=r.customer_id
                LEFT JOIN reservation_items ri ON ri.reservation_id=r.id
                LEFT JOIN machines m ON m.id=ri.machine_id
                WHERE COALESCE(r.reserved_from, '') <= ?
                  AND COALESCE(r.reserved_to, '') >= ?
                  AND r.status IN ('rezervace','potvrzeno')
                GROUP BY r.id
            )
            ORDER BY date_from, date_to, id
        """, (end_date, start_date, end_date, start_date))

    def create_service_record(self, machine_id:int, service_date:str, service_type:str, cost:float, provider:str, notes:str, next_service_date:str, service_motohours:float|None=0, next_service_motohours:float|None=0):
        cols = self._get_columns('service_records')
        machine = self.fetchone('SELECT motohours, service_due_motohours FROM machines WHERE id=?', (machine_id,)) if {'service_due_motohours','motohours'}.issubset(self._get_columns('machines')) else None
        current_mh = float(machine['motohours'] or 0) if machine else 0
        current_due_mh = float(machine['service_due_motohours'] or 0) if machine else 0
        if service_motohours is None:
            service_motohours = current_mh
        if next_service_motohours is None:
            next_service_motohours = current_due_mh
        if {'service_type','provider','next_service_date','service_motohours','next_service_motohours','status','completed_at'}.issubset(cols):
            rid=self.execute("INSERT INTO service_records(machine_id, service_date, service_type, cost, provider, notes, next_service_date, service_motohours, next_service_motohours, status, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'otevřený', '')", (machine_id, service_date, service_type, cost, provider, notes, next_service_date, service_motohours, next_service_motohours))
        elif {'service_type','provider','next_service_date','status','completed_at'}.issubset(cols):
            rid=self.execute("INSERT INTO service_records(machine_id, service_date, service_type, cost, provider, notes, next_service_date, status, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'otevřený', '')", (machine_id, service_date, service_type, cost, provider, notes, next_service_date))
        elif {'service_type','provider','next_service_date'}.issubset(cols):
            rid=self.execute("INSERT INTO service_records(machine_id, service_date, service_type, cost, provider, notes, next_service_date) VALUES (?, ?, ?, ?, ?, ?, ?)", (machine_id, service_date, service_type, cost, provider, notes, next_service_date))
        else:
            rid=self.execute("INSERT INTO service_records(machine_id, service_date, cost, notes) VALUES (?, ?, ?, ?)", (machine_id, service_date, cost, notes))
        if {'service_due_motohours','motohours'}.issubset(self._get_columns('machines')):
            self.execute("UPDATE machines SET status='servis', last_service_date=?, next_service_date=?, motohours=?, service_due_motohours=? WHERE id=?", (service_date, next_service_date, service_motohours, next_service_motohours, machine_id))
        else:
            self.execute("UPDATE machines SET status='servis', last_service_date=?, next_service_date=? WHERE id=?", (service_date, next_service_date, machine_id))
        return rid

    def update_service_record(self, record_id:int, machine_id:int, service_date:str, service_type:str, cost:float, provider:str, notes:str, next_service_date:str, service_motohours:float=0, next_service_motohours:float=0):
        cols = self._get_columns('service_records')
        if {'service_type','provider','next_service_date','service_motohours','next_service_motohours'}.issubset(cols):
            self.execute("UPDATE service_records SET machine_id=?, service_date=?, service_type=?, cost=?, provider=?, notes=?, next_service_date=?, service_motohours=?, next_service_motohours=? WHERE id=?", (machine_id, service_date, service_type, cost, provider, notes, next_service_date, service_motohours, next_service_motohours, record_id))
        elif {'service_type','provider','next_service_date'}.issubset(cols):
            self.execute("UPDATE service_records SET machine_id=?, service_date=?, service_type=?, cost=?, provider=?, notes=?, next_service_date=? WHERE id=?", (machine_id, service_date, service_type, cost, provider, notes, next_service_date, record_id))
        else:
            self.execute("UPDATE service_records SET machine_id=?, service_date=?, cost=?, notes=? WHERE id=?", (machine_id, service_date, cost, notes, record_id))
        if {'service_due_motohours','motohours'}.issubset(self._get_columns('machines')):
            self.execute("UPDATE machines SET status='servis', last_service_date=?, next_service_date=?, motohours=?, service_due_motohours=? WHERE id=?", (service_date, next_service_date, service_motohours, next_service_motohours, machine_id))
        else:
            self.execute("UPDATE machines SET status='servis', last_service_date=?, next_service_date=? WHERE id=?", (service_date, next_service_date, machine_id))

    def finish_service(self, machine_id:int, record_id:int|None=None):
        cols = self._get_columns('service_records')
        if record_id is not None and {'status','completed_at'}.issubset(cols):
            self.execute("UPDATE service_records SET status='dokončeno', completed_at=? WHERE id=?", (datetime.now().strftime('%Y-%m-%d'), record_id))
        elif record_id is not None:
            self.execute("DELETE FROM service_records WHERE id=?", (record_id,))
        self.execute("UPDATE machines SET status='volný' WHERE id=?", (machine_id,))

    def get_machine_photos(self, machine_id:int):
        rows = []
        if self._table_exists('machine_photos'):
            rows = self.fetchall("SELECT * FROM machine_photos WHERE machine_id=? ORDER BY sort_order ASC, id ASC", (machine_id,))
        primary = self.fetchone('SELECT photo_path FROM machines WHERE id=?', (machine_id,))
        primary_path = (primary['photo_path'] if primary else '') or ''
        if primary_path and not any((r['path'] or '') == primary_path for r in rows):
            fallback = {'id': None, 'machine_id': machine_id, 'path': primary_path, 'caption': '', 'sort_order': -1, 'created_at': ''}
            rows = [fallback] + rows
        return rows

    def add_machine_photo(self, machine_id:int, path:str, caption:str='') -> int:
        path = (path or '').strip()
        if not path:
            return 0
        last = self.fetchone("SELECT COALESCE(MAX(sort_order), -1) AS max_sort FROM machine_photos WHERE machine_id=?", (machine_id,)) if self._table_exists('machine_photos') else None
        next_sort = int(last['max_sort'] or -1) + 1 if last else 0
        photo_id = self.execute(
            "INSERT INTO machine_photos(machine_id, path, caption, sort_order, created_at) VALUES (?, ?, ?, ?, ?)",
            (machine_id, path, caption.strip(), next_sort, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        )
        primary = self.fetchone('SELECT photo_path FROM machines WHERE id=?', (machine_id,))
        if primary and not (primary['photo_path'] or '').strip():
            self.execute('UPDATE machines SET photo_path=? WHERE id=?', (path, machine_id))
        return photo_id

    def delete_machine_photo(self, photo_id:int) -> None:
        row = self.fetchone("SELECT * FROM machine_photos WHERE id=?", (photo_id,))
        if not row:
            return
        machine_id = row['machine_id']
        path = row['path'] or ''
        self.execute("DELETE FROM machine_photos WHERE id=?", (photo_id,))
        primary = self.fetchone('SELECT photo_path FROM machines WHERE id=?', (machine_id,))
        if primary and (primary['photo_path'] or '') == path:
            replacement = self.fetchone("SELECT path FROM machine_photos WHERE machine_id=? ORDER BY sort_order ASC, id ASC LIMIT 1", (machine_id,))
            self.execute('UPDATE machines SET photo_path=? WHERE id=?', ((replacement['path'] if replacement else ''), machine_id))

    def set_primary_machine_photo(self, machine_id:int, path:str) -> None:
        self.execute('UPDATE machines SET photo_path=? WHERE id=?', ((path or '').strip(), machine_id))


    def get_machine_accessories(self, machine_id:int):
        if not self._table_exists('machine_accessories'):
            return []
        return self.fetchall("SELECT * FROM machine_accessories WHERE machine_id=? ORDER BY sort_order ASC, id ASC", (machine_id,))

    def add_machine_accessory(self, machine_id:int, accessory_name:str, accessory_price:float=0.0) -> int:
        accessory_name = (accessory_name or '').strip()
        if not accessory_name:
            return 0
        row = self.fetchone("SELECT COALESCE(MAX(sort_order), -1) AS max_sort FROM machine_accessories WHERE machine_id=?", (machine_id,))
        next_sort = int(row['max_sort'] or -1) + 1 if row else 0
        return self.execute(
            "INSERT INTO machine_accessories(machine_id, accessory_name, accessory_price, sort_order, created_at) VALUES (?, ?, ?, ?, ?)",
            (machine_id, accessory_name, float(accessory_price or 0), next_sort, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        )

    def update_machine_accessory(self, accessory_id:int, accessory_name:str, accessory_price:float=0.0) -> None:
        self.execute(
            "UPDATE machine_accessories SET accessory_name=?, accessory_price=? WHERE id=?",
            ((accessory_name or '').strip(), float(accessory_price or 0), accessory_id),
        )

    def delete_machine_accessory(self, accessory_id:int) -> None:
        self.execute("DELETE FROM machine_accessories WHERE id=?", (accessory_id,))

    def sync_machine_accessories_from_legacy_text(self, machine_id:int, accessories_text:str) -> None:
        if not self._table_exists('machine_accessories'):
            return
        existing = self.fetchall("SELECT accessory_name FROM machine_accessories WHERE machine_id=?", (machine_id,))
        if existing:
            return
        raw = (accessories_text or '').replace(';', '\n').replace(',', '\n')
        items = []
        seen = set()
        for part in raw.splitlines():
            name = part.strip(' -•	').strip()
            if not name:
                continue
            key = name.casefold()
            if key in seen:
                continue
            seen.add(key)
            items.append(name)
        for idx, name in enumerate(items):
            self.execute(
                "INSERT INTO machine_accessories(machine_id, accessory_name, accessory_price, sort_order, created_at) VALUES (?, ?, 0, ?, ?)",
                (machine_id, name, idx, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            )

    def get_machine_accessory_presets(self, machine_id:int):
        if not self._table_exists('machine_accessory_presets'):
            return []
        return self.fetchall("SELECT * FROM machine_accessory_presets WHERE machine_id=? ORDER BY sort_order ASC, id ASC", (machine_id,))

    def add_machine_accessory_preset(self, machine_id:int, preset_name:str, accessories_text:str) -> int:
        preset_name = (preset_name or '').strip()
        accessories_text = (accessories_text or '').strip()
        if not preset_name:
            return 0
        row = self.fetchone("SELECT COALESCE(MAX(sort_order), -1) AS max_sort FROM machine_accessory_presets WHERE machine_id=?", (machine_id,))
        next_sort = int(row['max_sort'] or -1) + 1 if row else 0
        return self.execute(
            "INSERT INTO machine_accessory_presets(machine_id, preset_name, accessories_text, sort_order, created_at) VALUES (?, ?, ?, ?, ?)",
            (machine_id, preset_name, accessories_text, next_sort, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        )

    def update_machine_accessory_preset(self, preset_id:int, preset_name:str, accessories_text:str) -> None:
        self.execute(
            "UPDATE machine_accessory_presets SET preset_name=?, accessories_text=? WHERE id=?",
            ((preset_name or '').strip(), (accessories_text or '').strip(), preset_id),
        )

    def delete_machine_accessory_preset(self, preset_id:int) -> None:
        self.execute("DELETE FROM machine_accessory_presets WHERE id=?", (preset_id,))

    def get_finance_overview(self) -> dict[str, float]:
        row = self.fetchone("SELECT COALESCE(SUM(total_price + return_extra_charge),0) AS revenue, COALESCE(SUM(deposit),0) AS deposits, COALESCE(SUM(CASE WHEN COALESCE(paid_amount,0) < (COALESCE(total_price,0)+COALESCE(deposit,0)+COALESCE(return_extra_charge,0)) THEN (COALESCE(total_price,0)+COALESCE(deposit,0)+COALESCE(return_extra_charge,0)-COALESCE(paid_amount,0)) ELSE 0 END),0) AS receivables FROM contracts")
        return {'revenue': float(row['revenue'] or 0), 'deposits': float(row['deposits'] or 0), 'receivables': float(row['receivables'] or 0)}

    def get_machine_revenue_rows(self, limit:int=10):
        return self.fetchall("SELECT m.id, m.name, m.inventory_number, COALESCE(SUM(c.total_price + c.return_extra_charge),0) AS revenue, COUNT(DISTINCT c.id) AS rentals FROM machines m LEFT JOIN contract_items ci ON ci.machine_id=m.id LEFT JOIN contracts c ON c.id=ci.contract_id GROUP BY m.id ORDER BY revenue DESC, rentals DESC LIMIT ?", (limit,))

    def get_calendar_events_filtered(self, kind: str='Vše'):
        rows = self.fetchall("""
            SELECT id, contract_number AS ref, rental_from AS date_from, rental_to AS date_to, 'Smlouva' AS typ, status FROM contracts WHERE COALESCE(rental_to,end_date,'') >= date('now')
            UNION ALL
            SELECT id, reservation_number AS ref, reserved_from AS date_from, reserved_to AS date_to, 'Rezervace' AS typ, status FROM reservations WHERE reserved_to >= date('now')
            UNION ALL
            SELECT id, CAST(machine_id AS TEXT) AS ref, service_date AS date_from, COALESCE(next_service_date, service_date) AS date_to, 'Servis' AS typ, 'servis' AS status FROM service_records WHERE COALESCE(next_service_date, service_date) >= date('now')
            ORDER BY date_from
        """)
        if kind and kind != 'Vše':
            rows = [r for r in rows if r['typ'] == kind]
        return rows


    def global_search(self, term: str, limit:int=8) -> dict[str, list[sqlite3.Row]]:
        q = f"%{(term or '').strip()}%"
        return {
            'machines': self.fetchall("SELECT id, name, inventory_number, category, status, daily_rate FROM machines WHERE COALESCE(name,'') LIKE ? OR COALESCE(inventory_number,'') LIKE ? OR COALESCE(category,'') LIKE ? OR COALESCE(model,'') LIKE ? OR COALESCE(serial_number,'') LIKE ? OR COALESCE(notes, note, '') LIKE ? ORDER BY status='volný' DESC, id DESC LIMIT ?", (q, q, q, q, q, q, limit)),
            'customers': self.fetchall("SELECT id, name, COALESCE(company, company_name, '') AS company, phone, email FROM customers WHERE COALESCE(name,'') LIKE ? OR COALESCE(full_name,'') LIKE ? OR COALESCE(company, company_name, '') LIKE ? OR COALESCE(phone,'') LIKE ? OR COALESCE(email,'') LIKE ? OR COALESCE(notes, note, '') LIKE ? ORDER BY id DESC LIMIT ?", (q, q, q, q, q, q, limit)),
            'contracts': self.fetchall("SELECT c.id, c.contract_number, COALESCE(cu.name, cu.full_name, cu.company, cu.company_name, '') AS customer_name, c.status, c.rental_from, c.rental_to FROM contracts c LEFT JOIN customers cu ON cu.id=c.customer_id WHERE COALESCE(c.contract_number,'') LIKE ? OR COALESCE(cu.name, cu.full_name, cu.company, cu.company_name, '') LIKE ? OR COALESCE(c.notes, c.handover_note, c.return_note, '') LIKE ? ORDER BY c.id DESC LIMIT ?", (q, q, q, limit)),
            'reservations': self.fetchall("SELECT r.id, r.reservation_number, COALESCE(cu.name, cu.full_name, cu.company, cu.company_name, '') AS customer_name, r.status, r.reserved_from, r.reserved_to FROM reservations r LEFT JOIN customers cu ON cu.id=r.customer_id WHERE COALESCE(r.reservation_number,'') LIKE ? OR COALESCE(cu.name, cu.full_name, cu.company, cu.company_name, '') LIKE ? OR COALESCE(r.notes,'') LIKE ? ORDER BY r.id DESC LIMIT ?", (q, q, q, limit)),
        }

    def delete_contract(self, contract_id: int) -> None:
        self.execute("DELETE FROM contract_items WHERE contract_id=?", (contract_id,))
        self.execute("DELETE FROM contracts WHERE id=?", (contract_id,))

    def delete_reservation(self, reservation_id: int) -> None:
        self.execute("DELETE FROM reservation_items WHERE reservation_id=?", (reservation_id,))
        self.execute("DELETE FROM reservations WHERE id=?", (reservation_id,))

    def export_table_to_csv(self, table_name:str, filename_prefix:str) -> Path:
        allowed_tables = {
            'app_settings',
            'contract_items',
            'contracts',
            'customers',
            'machine_accessories',
            'machine_accessory_presets',
            'machine_photos',
            'machines',
            'reservation_items',
            'reservations',
            'service_records',
        }
        if table_name not in allowed_tables:
            raise ValueError(f'Nepodporovaný export tabulky: {table_name}')
        rows=self.fetchall(f"SELECT * FROM {table_name}")
        ts=datetime.now().strftime('%Y%m%d_%H%M%S')
        path=EXPORTS_DIR / f"{filename_prefix}_{ts}.csv"
        with path.open('w', newline='', encoding='utf-8-sig') as f:
            if rows:
                writer=csv.writer(f); writer.writerow(rows[0].keys())
                for r in rows: writer.writerow([r[k] for k in r.keys()])
            else:
                f.write('')
        return path


def _db_check_machine_conflicts(self: Database, machine_id: int, date_from: str, date_to: str, exclude_contract_id: int | None = None, exclude_reservation_id: int | None = None) -> list[str]:
    conflicts=[]; m=self.fetchone('SELECT * FROM machines WHERE id=?',(machine_id,))
    if not m:
        return ['Stroj nebyl nalezen.']
    if (m['status'] or '') in ('servis','blokovaný','vyřazený'):
        conflicts.append(f"{m['name']} je ve stavu {m['status']}.")
    contract_exclude = " AND id<>?" if exclude_contract_id is not None else ""
    reservation_exclude = " AND id<>?" if exclude_reservation_id is not None else ""
    params: list[Any] = []
    if exclude_contract_id is not None:
        params.append(exclude_contract_id)
    params.extend([machine_id, date_from, date_to])
    if exclude_reservation_id is not None:
        params.append(exclude_reservation_id)
    params.extend([machine_id, date_from, date_to])
    rows=self.fetchall(f"""
        SELECT contract_number AS ref, rental_from AS d1, rental_to AS d2, 'smlouva' AS typ FROM contracts
        WHERE status='aktivní' {contract_exclude} AND id IN (SELECT contract_id FROM contract_items WHERE machine_id=?) AND NOT (COALESCE(rental_to, end_date, '') < ? OR COALESCE(rental_from, start_date, '') > ?)
        UNION ALL
        SELECT reservation_number AS ref, reserved_from AS d1, reserved_to AS d2, 'rezervace' AS typ FROM reservations
        WHERE status IN ('rezervace','potvrzeno') {reservation_exclude} AND id IN (SELECT reservation_id FROM reservation_items WHERE machine_id=?) AND NOT (reserved_to < ? OR reserved_from > ?)
        ORDER BY d1
    """, params)
    for r in rows:
        conflicts.append(f"{m['name']}: kolize s {r['typ']} {r['ref']} ({r['d1']} až {r['d2']})")
    return conflicts


def _db_recompute_machine_status(self: Database, machine_id: int) -> None:
    machine = self.fetchone("SELECT status FROM machines WHERE id=?", (machine_id,))
    if not machine:
        return
    if str(machine['status'] or '') == 'vyřazený':
        return
    has_open_service = self.fetchone("SELECT 1 FROM service_records WHERE machine_id=? AND COALESCE(status,'')!='dokončeno' LIMIT 1", (machine_id,))
    if has_open_service:
        self.conn.execute("UPDATE machines SET status='servis' WHERE id=?", (machine_id,))
        return
    has_active_contract = self.fetchone("""
        SELECT 1
        FROM contract_items ci
        JOIN contracts c ON c.id=ci.contract_id
        WHERE ci.machine_id=? AND c.status='aktivní'
        LIMIT 1
    """, (machine_id,))
    if has_active_contract:
        self.conn.execute("UPDATE machines SET status='půjčený' WHERE id=?", (machine_id,))
        return
    self.conn.execute("UPDATE machines SET status='volný' WHERE id=?", (machine_id,))


def _db_create_reservation_record(self: Database, customer_id: int, date_from: str, date_to: str, total_price: float, deposit: float, notes: str, machine_ids: list[int], reservation_id: int | None = None) -> int:
    if not customer_id or not machine_ids:
        raise ValueError('Vyber zákazníka a alespoň jeden stroj.')
    conflicts: list[str] = []
    for machine_id in machine_ids:
        conflicts.extend(self.check_machine_conflicts(machine_id, date_from, date_to, exclude_reservation_id=reservation_id))
    if conflicts:
        raise ValueError('\n'.join(conflicts[:8]))
    if reservation_id:
        try:
            self.conn.execute("BEGIN")
            self.conn.execute("UPDATE reservations SET customer_id=?, reserved_from=?, reserved_to=?, total_price=?, deposit=?, notes=? WHERE id=?", (customer_id, date_from, date_to, total_price, deposit, notes, reservation_id))
            self.conn.execute("DELETE FROM reservation_items WHERE reservation_id=?", (reservation_id,))
            for machine_id in machine_ids:
                self.conn.execute("INSERT INTO reservation_items(reservation_id, machine_id) VALUES (?, ?)", (reservation_id, machine_id))
            self.conn.commit()
            return reservation_id
        except Exception:
            self.conn.rollback()
            raise
    for _ in range(8):
        reservation_number = self.generate_reservation_number()
        try:
            self.conn.execute("BEGIN")
            cur = self.conn.execute(
                "INSERT INTO reservations(reservation_number, customer_id, created_at, reserved_from, reserved_to, total_price, deposit, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, 'rezervace', ?)",
                (reservation_number, customer_id, date.today().strftime('%Y-%m-%d'), date_from, date_to, total_price, deposit, notes),
            )
            rid = int(cur.lastrowid or 0)
            for machine_id in machine_ids:
                self.conn.execute("INSERT INTO reservation_items(reservation_id, machine_id) VALUES (?, ?)", (rid, machine_id))
            self.conn.commit()
            return rid
        except sqlite3.IntegrityError as exc:
            self.conn.rollback()
            if 'reservation_number' in str(exc):
                continue
            raise
        except Exception:
            self.conn.rollback()
            raise
    raise sqlite3.IntegrityError('Nepodařilo se vytvořit unikátní číslo rezervace.')


def _db_create_contract_record(self: Database, customer_id: int, rental_from: str, rental_to: str, total_price: float, deposit: float, paid_amount: float, payment_method: str, issue_photo_path: str, notes: str, machine_ids: list[int], issue_condition: str, selected_accessory_ids: list[int] | None = None, pricing_mode: str = 'day') -> int:
    if not customer_id or not machine_ids:
        raise ValueError('Vyber zákazníka a alespoň jeden stroj.')
    conflicts: list[str] = []
    for machine_id in machine_ids:
        conflicts.extend(self.check_machine_conflicts(machine_id, rental_from, rental_to))
    if conflicts:
        raise ValueError('\n'.join(conflicts[:8]))
    contract_cols = self._get_columns('contracts')
    selected_accessory_ids = set(selected_accessory_ids or [])
    for _ in range(8):
        contract_number = self.generate_contract_number()
        try:
            self.conn.execute("BEGIN")
            if 'start_date' in contract_cols and 'end_date' in contract_cols and 'pricing_mode' in contract_cols:
                cur = self.conn.execute(
                    "INSERT INTO contracts(contract_number, customer_id, created_at, rental_from, rental_to, start_date, end_date, total_price, deposit, paid_amount, pricing_mode, payment_method, issue_photo_path, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'aktivní', ?)",
                    (contract_number, customer_id, date.today().strftime('%Y-%m-%d'), rental_from, rental_to, rental_from, rental_to, total_price, deposit, paid_amount, pricing_mode, payment_method, issue_photo_path, notes),
                )
            elif 'start_date' in contract_cols and 'end_date' in contract_cols:
                cur = self.conn.execute(
                    "INSERT INTO contracts(contract_number, customer_id, created_at, rental_from, rental_to, start_date, end_date, total_price, deposit, paid_amount, payment_method, issue_photo_path, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'aktivní', ?)",
                    (contract_number, customer_id, date.today().strftime('%Y-%m-%d'), rental_from, rental_to, rental_from, rental_to, total_price, deposit, paid_amount, payment_method, issue_photo_path, notes),
                )
            elif 'pricing_mode' in contract_cols:
                cur = self.conn.execute(
                    "INSERT INTO contracts(contract_number, customer_id, created_at, rental_from, rental_to, total_price, deposit, paid_amount, pricing_mode, payment_method, issue_photo_path, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'aktivní', ?)",
                    (contract_number, customer_id, date.today().strftime('%Y-%m-%d'), rental_from, rental_to, total_price, deposit, paid_amount, pricing_mode, payment_method, issue_photo_path, notes),
                )
            else:
                cur = self.conn.execute(
                    "INSERT INTO contracts(contract_number, customer_id, created_at, rental_from, rental_to, total_price, deposit, paid_amount, payment_method, issue_photo_path, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'aktivní', ?)",
                    (contract_number, customer_id, date.today().strftime('%Y-%m-%d'), rental_from, rental_to, total_price, deposit, paid_amount, payment_method, issue_photo_path, notes),
                )
            contract_id = int(cur.lastrowid or 0)
            accessory_totals_sum = 0.0
            for machine_id in machine_ids:
                acc_rows = [dict(r) for r in self.get_machine_accessories(machine_id)]
                chosen_rows = [row for row in acc_rows if int(row.get('id') or 0) in selected_accessory_ids]
                acc_text = '\n'.join([f"{(row.get('accessory_name') or '')} ({row.get('accessory_price') or 0})" for row in chosen_rows])
                acc_total = sum(float(row.get('accessory_price') or 0) for row in chosen_rows)
                accessory_totals_sum += acc_total
                self.conn.execute("INSERT INTO contract_items(contract_id, machine_id, issue_condition, accessories_issued, accessories_total) VALUES (?, ?, ?, ?, ?)", (contract_id, machine_id, issue_condition, acc_text, acc_total))
                self.conn.execute("UPDATE machines SET status='půjčený' WHERE id=?", (machine_id,))
            if accessory_totals_sum:
                self.conn.execute("UPDATE contracts SET total_price=COALESCE(total_price,0)+? WHERE id=?", (accessory_totals_sum, contract_id))
            self.conn.commit()
            return contract_id
        except sqlite3.IntegrityError as exc:
            self.conn.rollback()
            if 'contract_number' in str(exc):
                continue
            raise
        except Exception:
            self.conn.rollback()
            raise
    raise sqlite3.IntegrityError('Nepodařilo se vytvořit unikátní číslo smlouvy.')


def _db_delete_contract(self: Database, contract_id: int) -> None:
    machine_ids = [int(row['machine_id']) for row in self.fetchall("SELECT machine_id FROM contract_items WHERE contract_id=?", (contract_id,))]
    self.conn.execute("BEGIN")
    try:
        self.conn.execute("DELETE FROM contract_items WHERE contract_id=?", (contract_id,))
        self.conn.execute("DELETE FROM contracts WHERE id=?", (contract_id,))
        for machine_id in machine_ids:
            self.recompute_machine_status(machine_id)
        self.conn.commit()
    except Exception:
        self.conn.rollback()
        raise


def _db_delete_reservation(self: Database, reservation_id: int) -> None:
    self.conn.execute("BEGIN")
    try:
        self.conn.execute("DELETE FROM reservation_items WHERE reservation_id=?", (reservation_id,))
        self.conn.execute("DELETE FROM reservations WHERE id=?", (reservation_id,))
        self.conn.commit()
    except Exception:
        self.conn.rollback()
        raise


def _db_finish_service(self: Database, machine_id: int, record_id: int | None = None):
    cols = self._get_columns('service_records')
    self.conn.execute("BEGIN")
    try:
        if record_id is not None and {'status','completed_at'}.issubset(cols):
            self.conn.execute("UPDATE service_records SET status='dokončeno', completed_at=? WHERE id=?", (datetime.now().strftime('%Y-%m-%d'), record_id))
        elif record_id is not None:
            self.conn.execute("DELETE FROM service_records WHERE id=?", (record_id,))
        self.recompute_machine_status(machine_id)
        self.conn.commit()
    except Exception:
        self.conn.rollback()
        raise


Database.check_machine_conflicts = _db_check_machine_conflicts
Database.recompute_machine_status = _db_recompute_machine_status
Database.create_reservation_record = _db_create_reservation_record
Database.create_contract_record = _db_create_contract_record
Database.delete_contract = _db_delete_contract
Database.delete_reservation = _db_delete_reservation
Database.finish_service = _db_finish_service
