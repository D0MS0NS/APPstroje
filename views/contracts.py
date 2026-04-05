from __future__ import annotations
from datetime import datetime, date, timedelta
import calendar as pycalendar
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import tkinter as tk
from utils import row_value, parse_date_input, format_date, display_period, format_currency, file_label, center_window, pick_date_for_entry, style_treeview, ModalFormWindow


def parse_accessory_options(raw: str) -> list[str]:
    text = (raw or '').replace(';', '\n').replace(',', '\n')
    items = []
    seen = set()
    for line in text.splitlines():
        item = line.strip(' \t\r\n-•').strip()
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    return items


def format_accessory_price(value) -> str:
    try:
        amount = float(value or 0)
    except Exception:
        amount = 0
    if amount <= 0:
        return 'v ceně'
    return format_currency(amount)

CZ_MONTHS = ['leden', 'únor', 'březen', 'duben', 'květen', 'červen', 'červenec', 'srpen', 'září', 'říjen', 'listopad', 'prosinec']
STATUS_TAGS = {
    'aktivní': ('#f59e0b', '#111827'),
    'vráceno': ('#22c55e', '#052e16'),
    'po termínu': ('#ef4444', '#111827'),
    'rezervace': ('#14b8a6', '#042f2e'),
    'potvrzeno': ('#3b82f6', '#111827'),
}


def apply_tree_tags(tree: ttk.Treeview):
    for status, (bg, fg) in STATUS_TAGS.items():
        tree.tag_configure(status, background=bg, foreground=fg)


class StatChip(ctk.CTkFrame):
    def __init__(self, master, title: str, accent: str):
        super().__init__(master, corner_radius=18, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047"))
        self.configure(width=170)
        dot = ctk.CTkFrame(self, width=10, height=10, corner_radius=5, fg_color=accent)
        dot.pack(anchor='w', padx=14, pady=(12, 6))
        self.value = ctk.CTkLabel(self, text='0', font=ctk.CTkFont(size=24, weight='bold'))
        self.value.pack(anchor='w', padx=14)
        self.title = ctk.CTkLabel(self, text=title, text_color=("#64748b", "#94a3b8"))
        self.title.pack(anchor='w', padx=14, pady=(2, 12))
    def set(self, value):
        self.value.configure(text=str(value))


class ContractsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.current_month = date.today().replace(day=1)

        top = ctk.CTkFrame(self, corner_radius=24, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047"))
        top.grid(row=0, column=0, sticky='ew', padx=22, pady=(22, 12))
        top.grid_columnconfigure(1, weight=1)
        left = ctk.CTkFrame(top, fg_color='transparent')
        left.grid(row=0, column=0, sticky='w', padx=18, pady=16)
        ctk.CTkLabel(left, text='Smlouvy, rezervace a kalendář', font=ctk.CTkFont(size=28, weight='bold')).pack(anchor='w')
        ctk.CTkLabel(left, text='Celý obchodní tok od rezervace až po vrácení a PDF dokumenty', text_color=("#64748b", "#94a3b8")).pack(anchor='w', pady=(2,0))
        actions = ctk.CTkFrame(top, fg_color='transparent')
        actions.grid(row=0, column=2, sticky='e', padx=18, pady=16)
        ctk.CTkButton(actions, text='Nová smlouva', height=40, corner_radius=14, command=self.open_add).pack(side='left')
        ctk.CTkButton(actions, text='Nová rezervace', height=40, corner_radius=14, command=self.open_reservation).pack(side='left', padx=(8, 0))

        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=1, column=0, sticky='nsew', padx=22, pady=(0, 22))
        for name in ('Smlouvy', 'Rezervace', 'Kalendář'):
            self.tabs.add(name)

        self._build_contract_tab()
        self._build_reservation_tab()
        self._build_calendar_tab()

    def _build_contract_tab(self):
        tab = self.tabs.tab('Smlouvy')
        tab.grid_rowconfigure(2, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        summary = ctk.CTkFrame(tab, fg_color='transparent')
        summary.grid(row=0, column=0, sticky='ew', padx=12, pady=(12, 8))
        for i in range(4):
            summary.grid_columnconfigure(i, weight=1)
        self.contract_total_chip = StatChip(summary, 'Zobrazené smlouvy', '#2563eb')
        self.contract_total_chip.grid(row=0, column=0, sticky='ew', padx=4)
        self.contract_active_chip = StatChip(summary, 'Aktivní', '#f59e0b')
        self.contract_active_chip.grid(row=0, column=1, sticky='ew', padx=4)
        self.contract_overdue_chip = StatChip(summary, 'Po termínu', '#ef4444')
        self.contract_overdue_chip.grid(row=0, column=2, sticky='ew', padx=4)
        self.contract_returned_chip = StatChip(summary, 'Vrácené', '#22c55e')
        self.contract_returned_chip.grid(row=0, column=3, sticky='ew', padx=4)

        toolbar = ctk.CTkFrame(tab, corner_radius=20, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047"))
        toolbar.grid(row=1, column=0, sticky='ew', padx=12, pady=(0, 8))
        toolbar.grid_columnconfigure(0, weight=1)
        self.search = ctk.CTkEntry(toolbar, placeholder_text='Hledat číslo smlouvy / zákazníka', height=40, corner_radius=14)
        self.search.grid(row=0, column=0, sticky='ew', padx=14, pady=14)
        self.search.bind('<KeyRelease>', lambda e: self.refresh_contracts())
        self.contract_filter = ctk.CTkComboBox(toolbar, values=['Vše', 'aktivní', 'po termínu', 'vráceno'], width=160, command=lambda _=None: self.refresh_contracts())
        self.contract_filter.grid(row=0, column=1, padx=(0,10), pady=14)
        self.contract_filter.set('Vše')
        ctk.CTkButton(toolbar, text='Reset', width=84, height=40, corner_radius=14, command=self.reset_contract_filters).grid(row=0, column=2, padx=(0,14), pady=14)

        self.tree = ttk.Treeview(tab, columns=('id', 'number', 'customer', 'from', 'to', 'status', 'price'), show='headings')
        for col, title, width in [('id', 'ID', 50), ('number', 'Číslo smlouvy', 130), ('customer', 'Zákazník', 220), ('from', 'Od', 110), ('to', 'Do', 110), ('status', 'Stav', 110), ('price', 'Cena', 100)]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor='w')
        style_treeview(self.tree, 'Contracts')
        apply_tree_tags(self.tree)
        self.tree.grid(row=2, column=0, sticky='nsew', padx=(12, 0), pady=(2, 12))
        self.tree.bind('<Double-1>', lambda e: self.open_detail())
        self.tree.bind('<<TreeviewSelect>>', lambda e: self._update_contract_actions())
        scroll = ttk.Scrollbar(tab, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=2, column=1, sticky='ns', pady=(0, 12), padx=(0, 12))
        btns = ctk.CTkFrame(tab, fg_color='transparent')
        btns.grid(row=3, column=0, sticky='ew', padx=12, pady=(0, 12))
        self.contract_selection_lbl = ctk.CTkLabel(btns, text='Vybraná smlouva: žádná', text_color=("#64748b", "#94a3b8"))
        self.contract_selection_lbl.pack(side='left')
        actions = ctk.CTkFrame(btns, fg_color='transparent')
        actions.pack(side='right')
        self.btn_return = ctk.CTkButton(actions, text='Vrácení stroje', command=self.open_return, state='disabled')
        self.btn_return.pack(side='left', padx=4)
        self.btn_detail = ctk.CTkButton(actions, text='Detail', command=self.open_detail, state='disabled')
        self.btn_detail.pack(side='left', padx=4)
        self.btn_pdf = ctk.CTkButton(actions, text='PDF', command=self.open_pdf, state='disabled')
        self.btn_pdf.pack(side='left', padx=4)
        self.btn_delete_contract = ctk.CTkButton(actions, text='Smazat', fg_color='#dc2626', hover_color='#b91c1c', command=self.delete_contract, state='disabled')
        self.btn_delete_contract.pack(side='left', padx=(4,0))

    def _build_reservation_tab(self):
        tab = self.tabs.tab('Rezervace')
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        summary = ctk.CTkFrame(tab, fg_color='transparent')
        summary.grid(row=0, column=0, sticky='ew', padx=12, pady=(12, 8))
        for i in range(3):
            summary.grid_columnconfigure(i, weight=1)
        self.res_total_chip = StatChip(summary, 'Zobrazené rezervace', '#14b8a6')
        self.res_total_chip.grid(row=0, column=0, sticky='ew', padx=4)
        self.res_pending_chip = StatChip(summary, 'Rezervace', '#14b8a6')
        self.res_pending_chip.grid(row=0, column=1, sticky='ew', padx=4)
        self.res_confirmed_chip = StatChip(summary, 'Potvrzené', '#3b82f6')
        self.res_confirmed_chip.grid(row=0, column=2, sticky='ew', padx=4)
        toolbar = ctk.CTkFrame(tab, corner_radius=20, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047"))
        toolbar.grid(row=1, column=0, sticky='ew', padx=12, pady=(0, 8))
        toolbar.grid_columnconfigure(0, weight=1)
        self.res_search = ctk.CTkEntry(toolbar, placeholder_text='Hledat číslo rezervace / zákazníka', height=40, corner_radius=14)
        self.res_search.grid(row=0, column=0, sticky='ew', padx=14, pady=14)
        self.res_search.bind('<KeyRelease>', lambda e: self.refresh_reservations())
        self.res_filter = ctk.CTkComboBox(toolbar, values=['Vše', 'rezervace', 'potvrzeno'], width=160, command=lambda _=None: self.refresh_reservations())
        self.res_filter.grid(row=0, column=1, padx=(0,10), pady=14)
        self.res_filter.set('Vše')
        ctk.CTkButton(toolbar, text='Reset', width=84, height=40, corner_radius=14, command=self.reset_reservation_filters).grid(row=0, column=2, padx=(0,14), pady=14)
        self.res_tree = ttk.Treeview(tab, columns=('id', 'number', 'customer', 'from', 'to', 'status', 'machines'), show='headings')
        for col, title, width in [('id', 'ID', 50), ('number', 'Číslo rezervace', 150), ('customer', 'Zákazník', 220), ('from', 'Od', 110), ('to', 'Do', 110), ('status', 'Stav', 100), ('machines', 'Stroje', 300)]:
            self.res_tree.heading(col, text=title)
            self.res_tree.column(col, width=width, anchor='w')
        style_treeview(self.res_tree, 'Reservations')
        apply_tree_tags(self.res_tree)
        self.res_tree.grid(row=2, column=0, sticky='nsew', padx=(12, 0), pady=(2, 12))
        self.res_tree.bind('<Double-1>', lambda e: self.open_reservation_detail())
        self.res_tree.bind('<<TreeviewSelect>>', lambda e: self._update_reservation_actions())
        scroll = ttk.Scrollbar(tab, orient='vertical', command=self.res_tree.yview)
        self.res_tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=2, column=1, sticky='ns', padx=(0, 12), pady=(0, 12))
        action_wrap = ctk.CTkFrame(tab, fg_color='transparent')
        action_wrap.grid(row=3, column=0, sticky='ew', padx=12, pady=(0, 12))
        self.res_selection_lbl = ctk.CTkLabel(action_wrap, text='Vybraná rezervace: žádná', text_color=("#64748b", "#94a3b8"))
        self.res_selection_lbl.pack(side='left')
        res_actions = ctk.CTkFrame(action_wrap, fg_color='transparent')
        res_actions.pack(side='right')
        self.btn_res_detail = ctk.CTkButton(res_actions, text='Detail rezervace', command=self.open_reservation_detail, state='disabled')
        self.btn_res_detail.pack(side='left', padx=4)
        self.btn_res_delete = ctk.CTkButton(res_actions, text='Smazat', fg_color='#dc2626', hover_color='#b91c1c', command=self.delete_reservation, state='disabled')
        self.btn_res_delete.pack(side='left', padx=(4,0))

    def _build_calendar_tab(self):
        tab = self.tabs.tab('Kalendář')
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        controls = ctk.CTkFrame(tab, fg_color='transparent')
        controls.grid(row=0, column=0, sticky='ew', padx=12, pady=12)
        ctk.CTkButton(controls, text='←', width=36, command=self.prev_month).pack(side='left')
        self.month_label = ctk.CTkLabel(controls, text='', font=ctk.CTkFont(size=18, weight='bold'))
        self.month_label.pack(side='left', padx=12)
        ctk.CTkButton(controls, text='→', width=36, command=self.next_month).pack(side='left')
        ctk.CTkButton(controls, text='Dnes', width=70, command=self.goto_today).pack(side='left', padx=(8, 0))
        ctk.CTkLabel(controls, text='Filtr:').pack(side='right', padx=(0, 8))
        self.calendar_filter = ctk.CTkComboBox(controls, values=['Vše', 'Smlouva', 'Rezervace', 'Servis'], width=150, command=lambda _=None: self.refresh_calendar())
        self.calendar_filter.pack(side='right')
        self.calendar_filter.set('Vše')
        self.calendar_scroll = ctk.CTkScrollableFrame(tab, corner_radius=16)
        self.calendar_scroll.grid(row=1, column=0, sticky='nsew', padx=12, pady=(0, 12))
        self.calendar_scroll.grid_columnconfigure(tuple(range(7)), weight=1)

    def refresh(self):
        self.refresh_contracts(); self.refresh_reservations(); self.refresh_calendar()

    def refresh_contracts(self):
        q = self.search.get().strip().lower()
        current_filter = self.contract_filter.get()
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = self.app.db.fetchall("SELECT c.*, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name FROM contracts c LEFT JOIN customers cu ON cu.id=c.customer_id ORDER BY c.id DESC")
        counts = {'aktivní':0,'po termínu':0,'vráceno':0}
        shown = 0
        for row in rows:
            hay = f"{row_value(row, 'contract_number')} {row_value(row, 'customer_name')}".lower()
            status = row_value(row, 'status')
            counts[status] = counts.get(status,0)+1
            if q and q not in hay:
                continue
            if current_filter != 'Vše' and status != current_filter:
                continue
            self.tree.insert('', 'end', values=(row_value(row, 'id'), row_value(row, 'contract_number'), row_value(row, 'customer_name'), format_date(row_value(row, 'rental_from')), format_date(row_value(row, 'rental_to')), status, format_currency(row_value(row, 'total_price', 0))), tags=(status,))
            shown += 1

        self.contract_total_chip.set(shown)
        self.contract_active_chip.set(counts.get('aktivní', 0))
        self.contract_overdue_chip.set(counts.get('po termínu', 0))
        self.contract_returned_chip.set(counts.get('vráceno', 0))
        self._update_contract_actions()

    def refresh_reservations(self):
        q = self.res_search.get().strip().lower()
        current_filter = self.res_filter.get()
        for item in self.res_tree.get_children():
            self.res_tree.delete(item)
        shown = 0
        counts = {'rezervace': 0, 'potvrzeno': 0}
        for row in self.app.db.get_reservations():
            hay = f"{row_value(row, 'reservation_number')} {row_value(row, 'customer_name')} {row_value(row, 'machines')}".lower()
            status = row_value(row, 'status')
            counts[status] = counts.get(status, 0) + 1
            if q and q not in hay:
                continue
            if current_filter != 'Vše' and status != current_filter:
                continue
            self.res_tree.insert('', 'end', values=(row_value(row, 'id'), row_value(row, 'reservation_number'), row_value(row, 'customer_name'), format_date(row_value(row, 'reserved_from')), format_date(row_value(row, 'reserved_to')), status, row_value(row, 'machines')), tags=(status,))
            shown += 1

        self.res_total_chip.set(shown)
        self.res_pending_chip.set(counts.get('rezervace', 0))
        self.res_confirmed_chip.set(counts.get('potvrzeno', 0))
        self._update_reservation_actions()


    def reset_contract_filters(self):
        self.search.delete(0, 'end')
        self.contract_filter.set('Vše')
        self.refresh_contracts()

    def reset_reservation_filters(self):
        self.res_search.delete(0, 'end')
        self.res_filter.set('Vše')
        self.refresh_reservations()

    def _update_contract_actions(self):
        sel = self.tree.selection()
        state = 'normal' if sel else 'disabled'
        for btn in (self.btn_return, self.btn_detail, self.btn_pdf, self.btn_delete_contract):
            btn.configure(state=state)
        if sel:
            values = self.tree.item(sel[0], 'values')
            self.contract_selection_lbl.configure(text=f'Vybraná smlouva: {values[1]} · {values[2]}')
        else:
            self.contract_selection_lbl.configure(text='Vybraná smlouva: žádná')

    def _update_reservation_actions(self):
        sel = self.res_tree.selection()
        state = 'normal' if sel else 'disabled'
        for btn in (self.btn_res_detail, self.btn_res_delete):
            btn.configure(state=state)
        if sel:
            values = self.res_tree.item(sel[0], 'values')
            self.res_selection_lbl.configure(text=f'Vybraná rezervace: {values[1]} · {values[2]}')
        else:
            self.res_selection_lbl.configure(text='Vybraná rezervace: žádná')

    def _selected_contract_id(self):
        sel = self.tree.selection()
        return int(self.tree.item(sel[0], 'values')[0]) if sel else None

    def _selected_reservation_id(self):
        sel = self.res_tree.selection()
        return int(self.res_tree.item(sel[0], 'values')[0]) if sel else None

    def open_add(self): ContractEditor(self, self.app, self.refresh)
    def open_reservation(self): ReservationEditor(self, self.app, self.refresh)
    def open_detail(self):
        cid = self._selected_contract_id()
        if cid is not None:
            self.app.open_contract_detail(cid)
    def open_reservation_detail(self):
        rid = self._selected_reservation_id()
        if rid is not None:
            self.app.open_reservation_detail(rid)
    def open_pdf(self):
        cid = self._selected_contract_id()
        if cid is None:
            return
        detail = self.app.db.get_contract_detail(cid)
        self.app.open_contract_pdf(row_value(detail['contract'], 'contract_number'))
    def open_return(self):
        cid = self._selected_contract_id()
        if cid is not None:
            ReturnDialog(self, self.app, cid, self.refresh)

    def prev_month(self):
        y, m = self.current_month.year, self.current_month.month - 1
        if m == 0: y, m = y - 1, 12
        self.current_month = date(y, m, 1); self.refresh_calendar()
    def next_month(self):
        y, m = self.current_month.year, self.current_month.month + 1
        if m == 13: y, m = y + 1, 1
        self.current_month = date(y, m, 1); self.refresh_calendar()
    def goto_today(self):
        self.current_month = date.today().replace(day=1); self.refresh_calendar()

    def refresh_calendar(self):
        for child in self.calendar_scroll.winfo_children(): child.destroy()
        self.month_label.configure(text=f"{CZ_MONTHS[self.current_month.month-1].capitalize()} {self.current_month.year}")
        for idx, name in enumerate(['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne']):
            ctk.CTkLabel(self.calendar_scroll, text=name, font=ctk.CTkFont(weight='bold')).grid(row=0, column=idx, sticky='ew', padx=4, pady=(4, 8))
        cal = pycalendar.Calendar(firstweekday=0)
        weeks = cal.monthdatescalendar(self.current_month.year, self.current_month.month)
        month_start, month_end = weeks[0][0], weeks[-1][-1]
        events = self.app.db.get_calendar_events_filtered(self.calendar_filter.get())
        by_day = {}
        for event in events:
            try:
                d1 = datetime.strptime(row_value(event, 'date_from'), '%Y-%m-%d').date()
                d2 = datetime.strptime(row_value(event, 'date_to'), '%Y-%m-%d').date()
            except Exception:
                continue
            cur, end = max(d1, month_start), min(d2, month_end)
            while cur <= end:
                by_day.setdefault(cur, []).append(event)
                cur += timedelta(days=1)
        today = date.today()
        for r, week in enumerate(weeks, start=1):
            self.calendar_scroll.grid_rowconfigure(r, weight=1)
            for c, day in enumerate(week):
                in_month = day.month == self.current_month.month
                cell = ctk.CTkFrame(self.calendar_scroll, corner_radius=14, fg_color='transparent' if in_month else ('#f3f4f6', '#111827'))
                cell.grid(row=r, column=c, sticky='nsew', padx=4, pady=4)
                header = ctk.CTkFrame(cell, fg_color='transparent')
                header.pack(fill='x', padx=8, pady=(8, 4))
                ctk.CTkLabel(header, text=str(day.day), font=ctk.CTkFont(size=15, weight='bold'), text_color='#2563eb' if day == today else None).pack(side='left')
                for event in by_day.get(day, [])[:4]:
                    typ = row_value(event, 'typ')
                    color = '#8b5cf6' if typ == 'Smlouva' else ('#14b8a6' if typ == 'Rezervace' else '#6366f1')
                    subtitle = 'S' if typ == 'Smlouva' else ('R' if typ == 'Rezervace' else 'V')
                    btn = ctk.CTkButton(cell, text=f"{subtitle} · {row_value(event, 'ref')}", fg_color=color, hover_color=color, height=24, anchor='w', command=lambda e=event: self._open_event(e))
                    btn.pack(fill='x', padx=6, pady=2)

    def _open_event(self, event):
        if row_value(event, 'typ') == 'Smlouva':
            self.app.open_contract_detail(int(row_value(event, 'id')))
        elif row_value(event, 'typ') == 'Rezervace':
            self.app.open_reservation_detail(int(row_value(event, 'id')))
        else:
            self.app.show_view('services')



    def delete_contract(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Výběr', 'Nejprve vyber smlouvu.')
            return
        contract_id = self.tree.item(sel[0], 'values')[0]
        detail = self.app.db.get_contract_detail(int(contract_id))
        contract = detail.get('contract')
        if not contract:
            messagebox.showerror('Chyba', 'Smlouva nebyla nalezena.')
            return
        if row_value(contract, 'status') == 'aktivní':
            if not messagebox.askyesno('Smazat smlouvu', 'Tato smlouva je aktivní. Opravdu ji chceš smazat? Stroje budou vráceny do stavu volný.'):
                return
        else:
            if not messagebox.askyesno('Smazat smlouvu', 'Opravdu chceš smazat vybranou smlouvu?'):
                return
        for item in detail.get('items', []):
            mid = row_value(item, 'id')
            if mid:
                self.app.db.execute("UPDATE machines SET status='volný' WHERE id=?", (mid,))
        self.app.db.execute('DELETE FROM contract_items WHERE contract_id=?', (contract_id,))
        self.app.db.execute('DELETE FROM contracts WHERE id=?', (contract_id,))
        self.app.refresh_all()

    def delete_reservation(self):
        sel = self.res_tree.selection()
        if not sel:
            messagebox.showwarning('Výběr', 'Nejprve vyber rezervaci.')
            return
        reservation_id = self.res_tree.item(sel[0], 'values')[0]
        if not messagebox.askyesno('Smazat rezervaci', 'Opravdu chceš smazat vybranou rezervaci?'):
            return
        self.app.db.execute('DELETE FROM reservation_items WHERE reservation_id=?', (reservation_id,))
        self.app.db.execute('DELETE FROM reservations WHERE id=?', (reservation_id,))
        self.app.refresh_all()

class ContractEditor(ModalFormWindow):
    def __init__(self, master, app, on_saved):
        super().__init__(master, 'Nová smlouva', 1700, 1180, 'Vytvořit smlouvu', self.save, subtitle='')
        self.body.destroy()
        self.body = ctk.CTkFrame(self, corner_radius=0, fg_color='transparent')
        self.body.grid(row=1, column=0, sticky='nsew', padx=18, pady=(18, 18))
        self.body.grid_columnconfigure(0, weight=1)
        self.app = app
        self.on_saved = on_saved
        customers = self.app.db.fetchall('SELECT id, name, company FROM customers ORDER BY name')
        machines = self.app.db.fetchall("SELECT * FROM machines WHERE status='volný' ORDER BY name")
        if not customers:
            messagebox.showerror('Chyba', 'Nejdřív přidej zákazníka.'); self.destroy(); return
        if not machines:
            messagebox.showerror('Chyba', 'Nejdřív přidej stroj.'); self.destroy(); return
        self.customer_map = {f"{row_value(c,'name')} | {row_value(c,'company')}": c['id'] for c in customers}
        self.machines = machines
        for _machine in self.machines:
            self.app.db.sync_machine_accessories_from_legacy_text(int(_machine['id']), row_value(_machine, 'accessories', ''))
        self.item_rows = {}

        root = ctk.CTkFrame(self.body, fg_color='transparent')
        root.grid(row=0, column=0, sticky='nsew')
        root.grid_columnconfigure(0, weight=5)
        root.grid_columnconfigure(1, weight=4)

        intro = ctk.CTkFrame(root, corner_radius=18)
        intro.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        intro.grid_columnconfigure((0,1,2), weight=1)
        self.summary_customer = ctk.CTkLabel(intro, text='Zákazník: —', font=ctk.CTkFont(size=16, weight='bold'))
        self.summary_customer.grid(row=0, column=0, sticky='w', padx=16, pady=(12, 4))
        self.summary_period = ctk.CTkLabel(intro, text='Termín: —', font=ctk.CTkFont(size=16, weight='bold'))
        self.summary_period.grid(row=0, column=1, sticky='w', padx=16, pady=(12, 4))
        self.summary_count = ctk.CTkLabel(intro, text='Vybrané stroje: 0', font=ctk.CTkFont(size=16, weight='bold'))
        self.summary_count.grid(row=0, column=2, sticky='w', padx=16, pady=12)

        left = ctk.CTkFrame(root, corner_radius=18)
        left.grid(row=1, column=0, sticky='nsew', padx=(0, 10))
        left.grid_columnconfigure(0, weight=1)
        right = ctk.CTkFrame(root, corner_radius=18)
        right.grid(row=1, column=1, sticky='nsew', padx=(10, 0))
        right.grid_columnconfigure(0, weight=1)

        basic = ctk.CTkFrame(left, fg_color='transparent')
        basic.grid(row=0, column=0, sticky='ew', padx=16, pady=(16, 8))
        basic.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(basic, text='Zákazník a termín', font=ctk.CTkFont(size=18, weight='bold')).grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 10))
        ctk.CTkLabel(basic, text='Zákazník').grid(row=1, column=0, padx=(0, 12), pady=8, sticky='w')
        self.customer_cb = ctk.CTkComboBox(basic, values=list(self.customer_map.keys()), height=38)
        self.customer_cb.grid(row=1, column=1, columnspan=2, sticky='ew', pady=8)
        self.customer_cb.set(list(self.customer_map.keys())[0])
        self.customer_cb.configure(command=lambda _=None: self.update_summary())

        defaults = {
            'rental_from': format_date(date.today().strftime('%Y-%m-%d')),
            'rental_to': format_date(date.today().strftime('%Y-%m-%d')),
            'total_price': '0',
            'deposit': '0',
            'paid_amount': '0',
            'issue_photo_path': '',
            'issue_condition': 'V pořádku',
        }
        self.entries = {}

        date_fields = [('Od', 'rental_from'), ('Do', 'rental_to')]
        for row_idx, (label, key) in enumerate(date_fields, start=2):
            ctk.CTkLabel(basic, text=label).grid(row=row_idx, column=0, padx=(0, 12), pady=8, sticky='w')
            ent = ctk.CTkEntry(basic, height=38)
            ent.grid(row=row_idx, column=1, sticky='ew', pady=8)
            ent.insert(0, defaults[key])
            ent.bind('<KeyRelease>', lambda e: self.update_summary())
            self.entries[key] = ent
            ctk.CTkButton(basic, text='📅', width=42, command=lambda e=ent: (pick_date_for_entry(self, e), self.update_summary())).grid(row=row_idx, column=2, padx=(8, 0), pady=8)

        finance = ctk.CTkFrame(left, fg_color='transparent')
        finance.grid(row=1, column=0, sticky='ew', padx=16, pady=8)
        finance.grid_columnconfigure(1, weight=1)
        finance.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(finance, text='Finance a předání', font=ctk.CTkFont(size=18, weight='bold')).grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 10))
        fields = [
            ('Cena celkem', 'total_price', 1, 0), ('Kauce', 'deposit', 1, 2),
            ('Uhrazeno', 'paid_amount', 2, 0), ('Stav při předání', 'issue_condition', 2, 2),
        ]
        for label, key, r, c in fields:
            ctk.CTkLabel(finance, text=label).grid(row=r, column=c, padx=(0, 12), pady=8, sticky='w')
            ent = ctk.CTkEntry(finance, height=38)
            ent.grid(row=r, column=c+1, sticky='ew', pady=8)
            ent.insert(0, defaults[key])
            self.entries[key] = ent
        ctk.CTkLabel(finance, text='Platba').grid(row=3, column=0, padx=(0, 12), pady=8, sticky='w')
        self.payment_method = ctk.CTkComboBox(finance, values=['hotově', 'kartou', 'převodem'], height=38)
        self.payment_method.grid(row=3, column=1, sticky='ew', pady=8)
        self.payment_method.set('hotově')
        ctk.CTkLabel(finance, text='Fotka při předání').grid(row=3, column=2, padx=(18, 12), pady=8, sticky='w')
        photo_wrap = ctk.CTkFrame(finance, fg_color='transparent')
        photo_wrap.grid(row=3, column=3, sticky='ew', pady=8)
        photo_wrap.grid_columnconfigure(0, weight=1)
        self.entries['issue_photo_path'] = ctk.CTkEntry(photo_wrap, height=38)
        self.entries['issue_photo_path'].grid(row=0, column=0, sticky='ew')
        self.entries['issue_photo_path'].insert(0, defaults['issue_photo_path'])
        ctk.CTkButton(photo_wrap, text='Vybrat', width=90, command=self.browse_issue_photo).grid(row=0, column=1, padx=(8, 0))

        notes_wrap = ctk.CTkFrame(left, fg_color='transparent')
        notes_wrap.grid(row=2, column=0, sticky='ew', padx=16, pady=(8, 16))
        notes_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(notes_wrap, text='Poznámka ke smlouvě', font=ctk.CTkFont(size=18, weight='bold')).grid(row=0, column=0, sticky='w', pady=(0, 10))
        self.notes = ctk.CTkTextbox(notes_wrap, height=120)
        self.notes.grid(row=1, column=0, sticky='ew')

        select_wrap = ctk.CTkFrame(right, fg_color='transparent')
        select_wrap.grid(row=0, column=0, sticky='nsew', padx=16, pady=(16, 8))
        select_wrap.grid_columnconfigure(0, weight=1)
        select_wrap.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(select_wrap, text='Výběr strojů', font=ctk.CTkFont(size=18, weight='bold')).grid(row=0, column=0, sticky='w', pady=(0, 8))

        list_wrap = ctk.CTkFrame(select_wrap, corner_radius=16)
        list_wrap.grid(row=1, column=0, sticky='nsew')
        list_wrap.grid_columnconfigure(0, weight=1)
        list_wrap.grid_rowconfigure(1, weight=1)

        self.machine_search = ctk.CTkEntry(list_wrap, height=38, placeholder_text='Hledat stroj…')
        self.machine_search.grid(row=0, column=0, sticky='ew', padx=12, pady=(12, 8))
        self.machine_search.bind('<KeyRelease>', lambda e: self.refresh_machine_list())

        list_inner = ctk.CTkFrame(list_wrap, fg_color='transparent')
        list_inner.grid(row=1, column=0, sticky='nsew', padx=12, pady=(0, 12))
        list_inner.grid_columnconfigure(0, weight=1)
        list_inner.grid_rowconfigure(0, weight=1)

        self.machine_listbox = tk.Listbox(
            list_inner,
            selectmode=tk.EXTENDED,
            activestyle='none',
            exportselection=False,
            height=18,
            font=('Segoe UI', 11),
            borderwidth=0,
            highlightthickness=0,
        )
        self.machine_listbox.grid(row=0, column=0, sticky='nsew')
        machine_scroll = ttk.Scrollbar(list_inner, orient='vertical', command=self.machine_listbox.yview)
        machine_scroll.grid(row=0, column=1, sticky='ns')
        self.machine_listbox.configure(yscrollcommand=machine_scroll.set)
        self.machine_listbox.bind('<<ListboxSelect>>', lambda e: self.refresh_selected_items())

        self.machine_list_index_map = []
        self.machine_vars = []
        self.refresh_machine_list()

        selected_wrap = ctk.CTkFrame(right, fg_color='transparent')
        selected_wrap.grid(row=1, column=0, sticky='nsew', padx=16, pady=(8, 16))
        selected_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(selected_wrap, text='Příslušenství k vybraným strojům', font=ctk.CTkFont(size=18, weight='bold')).grid(row=0, column=0, sticky='w', pady=(0, 8))
        self.selected_items_frame = ctk.CTkScrollableFrame(selected_wrap, height=620)
        self.selected_items_frame.grid(row=1, column=0, sticky='nsew')
        self.selected_items_frame.grid_columnconfigure(0, weight=1)

        self.refresh_selected_items()
        self.update_summary()

    def browse_issue_photo(self):
        path = filedialog.askopenfilename(
            title='Vyber fotku při předání',
            filetypes=[('Obrázky', '*.png;*.jpg;*.jpeg;*.webp;*.bmp'), ('Všechny soubory', '*.*')]
        )
        if not path:
            return
        self.entries['issue_photo_path'].delete(0, 'end')
        self.entries['issue_photo_path'].insert(0, path)

    def refresh_machine_list(self):
        query = (self.machine_search.get().strip().lower() if hasattr(self, 'machine_search') else '')
        selected_ids = {int(m['id']) for m in self._selected_machines()} if hasattr(self, 'machine_listbox') else set()
        self.machine_listbox.delete(0, 'end')
        self.machine_list_index_map = []
        for machine in self.machines:
            title = f"{row_value(machine,'name')}"
            inv = row_value(machine, 'inventory_number') or 'bez inv. čísla'
            rate = f"{format_currency(row_value(machine,'daily_rate',0))}/den"
            hay = f"{title} {inv} {rate}".lower()
            if query and query not in hay:
                continue
            self.machine_list_index_map.append(machine)
            self.machine_listbox.insert('end', f"{title}   •   {inv}   •   {rate}")
        for idx, machine in enumerate(self.machine_list_index_map):
            if int(machine['id']) in selected_ids:
                self.machine_listbox.selection_set(idx)

    def _selected_machines(self):
        selected = []
        if not hasattr(self, 'machine_listbox'):
            return selected
        for idx in self.machine_listbox.curselection():
            if 0 <= idx < len(self.machine_list_index_map):
                selected.append(self.machine_list_index_map[idx])
        return selected

    def update_summary(self):
        customer = self.customer_cb.get().strip() or '—'
        self.summary_customer.configure(text=f'Zákazník: {customer}')
        self.summary_period.configure(text=f'Termín: {self.entries["rental_from"].get().strip() or "—"} → {self.entries["rental_to"].get().strip() or "—"}')
        self.summary_count.configure(text=f'Vybrané stroje: {len(self._selected_machines())}')

    def refresh_selected_items(self):
        selected = self._selected_machines()
        self.update_summary()
        for child in self.selected_items_frame.winfo_children():
            child.destroy()
        self.item_rows = {}
        if not selected:
            empty = ctk.CTkFrame(self.selected_items_frame, corner_radius=14)
            empty.grid(row=0, column=0, sticky='ew', padx=4, pady=4)
            ctk.CTkLabel(empty, text='Vyber stroj ze seznamu.', font=ctk.CTkFont(size=15, weight='bold')).pack(anchor='w', padx=12, pady=10)
            return
        for idx, machine in enumerate(selected):
            machine_id = int(machine['id'])
            card = ctk.CTkFrame(self.selected_items_frame, corner_radius=16)
            card.grid(row=idx, column=0, sticky='ew', padx=4, pady=3)
            card.grid_columnconfigure(0, weight=1)
            header = ctk.CTkFrame(card, fg_color='transparent')
            header.grid(row=0, column=0, sticky='ew', padx=12, pady=(6, 3))
            header.grid_columnconfigure(0, weight=1)
            title = f"{row_value(machine,'name')}"
            meta = f"{row_value(machine,'inventory_number') or 'bez inv. čísla'} • {format_currency(row_value(machine,'daily_rate',0))}/den"
            ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=15, weight='bold')).grid(row=0, column=0, sticky='w')
            ctk.CTkLabel(header, text=meta, text_color=('gray35','gray70')).grid(row=1, column=0, sticky='w')

            checks_wrap = ctk.CTkFrame(card, fg_color='transparent')
            checks_wrap.grid(row=1, column=0, sticky='ew', padx=12, pady=(0, 6))
            check_vars = []
            accessory_rows = self.app.db.get_machine_accessories(machine_id)
            if accessory_rows:
                checks_wrap.grid_columnconfigure((0, 1), weight=1)
                for opt_idx, acc in enumerate(accessory_rows):
                    var = ctk.BooleanVar(value=True)
                    price = float(row_value(acc, 'accessory_price', 0) or 0)
                    box = ctk.CTkFrame(checks_wrap, corner_radius=12, fg_color=('gray92','gray18'))
                    r = opt_idx // 2
                    c = opt_idx % 2
                    box.grid(row=r, column=c, sticky='ew', padx=(0, 5) if c == 0 else (5, 0), pady=2)
                    box.grid_columnconfigure(0, weight=1)
                    ctk.CTkCheckBox(box, text=row_value(acc, 'accessory_name'), variable=var, command=self._update_selected_totals).grid(row=0, column=0, sticky='w', padx=10, pady=5)
                    ctk.CTkLabel(box, text=format_accessory_price(price), text_color=('gray35','gray70')).grid(row=0, column=1, sticky='e', padx=10, pady=5)
                    check_vars.append({'name': row_value(acc, 'accessory_name'), 'price': price, 'var': var})
            else:
                info = ctk.CTkFrame(checks_wrap, corner_radius=12, fg_color=('gray92','gray18'))
                info.grid(row=0, column=0, sticky='ew')
                ctk.CTkLabel(info, text='Tento stroj zatím nemá nastavené žádné položky příslušenství.', text_color=('gray35','gray70')).pack(anchor='w', padx=10, pady=10)

            custom_wrap = ctk.CTkFrame(card, fg_color='transparent')
            custom_wrap.grid(row=2, column=0, sticky='ew', padx=12, pady=(0, 10))
            custom_wrap.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(custom_wrap, text='Další položky').grid(row=0, column=0, sticky='w', pady=(0, 3))
            entry = ctk.CTkTextbox(custom_wrap, height=44)
            entry.grid(row=1, column=0, sticky='ew')
            total_label = ctk.CTkLabel(custom_wrap, text='Příslušenství navíc: 0 Kč', text_color=('gray35','gray70'))
            total_label.grid(row=2, column=0, sticky='e', pady=(6, 0))
            try:
                entry.bind('<KeyRelease>', lambda e: self._update_selected_totals())
            except Exception:
                pass
            self.item_rows[machine_id] = {'entry': entry, 'check_vars': check_vars, 'machine': machine, 'total_label': total_label}
            self._refresh_machine_accessory_total(machine_id)
        self._update_selected_totals()

    def _refresh_machine_accessory_total(self, machine_id:int):
        cfg = self.item_rows.get(machine_id)
        if not cfg:
            return
        total = sum(float(item.get('price', 0) or 0) for item in cfg.get('check_vars', []) if bool(item['var'].get()))
        cfg['total_label'].configure(text=f'Příslušenství navíc: {format_currency(total)}')

    def _update_selected_totals(self):
        for machine_id in list(self.item_rows.keys()):
            self._refresh_machine_accessory_total(machine_id)

    def _collect_machine_accessories_text(self, machine_id:int) -> str:
        cfg = self.item_rows.get(machine_id)
        if not cfg:
            return ''
        selected_lines = []
        for item in cfg.get('check_vars', []):
            if bool(item['var'].get()):
                selected_lines.append(f"{item['name']} ({format_accessory_price(item['price'])})")
        custom_text = cfg['entry'].get('1.0', 'end').strip()
        if custom_text:
            custom_lines = parse_accessory_options(custom_text)
            if custom_lines:
                selected_lines.extend(custom_lines)
            else:
                selected_lines.append(custom_text)
        return '\n'.join(selected_lines).strip()

    def _collect_machine_accessories_total(self, machine_id:int) -> float:
        cfg = self.item_rows.get(machine_id)
        if not cfg:
            return 0.0
        return sum(float(item.get('price', 0) or 0) for item in cfg.get('check_vars', []) if bool(item['var'].get()))

    def save(self):
        try:
            total_price = float(self.entries['total_price'].get().strip().replace(',', '.') or 0)
            deposit = float(self.entries['deposit'].get().strip().replace(',', '.') or 0)
            paid_amount = float(self.entries['paid_amount'].get().strip().replace(',', '.') or 0)
            rental_from = parse_date_input(self.entries['rental_from'].get())
            rental_to = parse_date_input(self.entries['rental_to'].get())
        except ValueError as exc:
            messagebox.showerror('Chyba', str(exc)); return
        customer_id = self.customer_map[self.customer_cb.get()]
        selected = self._selected_machines()
        if not selected:
            messagebox.showerror('Chyba', 'Vyber aspoň jeden stroj.'); return
        conflicts = []
        for machine in selected:
            conflicts.extend(self.app.db.check_machine_conflicts(machine['id'], rental_from, rental_to))
        if conflicts:
            messagebox.showerror('Kolize termínů', 'Vybrané stroje mají v tomto termínu kolizi\n\n' + '\n'.join(f'• {c}' for c in conflicts)); return
        contract_number = self.app.db.generate_contract_number()
        created_at = datetime.now().strftime('%Y-%m-%d')
        notes = self.notes.get('1.0', 'end').strip()
        cols = self.app.db._get_columns('contracts')
        if 'start_date' in cols and 'end_date' in cols:
            contract_id = self.app.db.execute(
                "INSERT INTO contracts(contract_number, customer_id, created_at, rental_from, rental_to, start_date, end_date, total_price, deposit, paid_amount, payment_method, issue_photo_path, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'aktivní', ?)",
                (contract_number, customer_id, created_at, rental_from, rental_to, rental_from, rental_to, total_price, deposit, paid_amount, self.payment_method.get(), self.entries['issue_photo_path'].get().strip(), notes)
            )
        else:
            contract_id = self.app.db.execute(
                "INSERT INTO contracts(contract_number, customer_id, created_at, rental_from, rental_to, total_price, deposit, paid_amount, payment_method, issue_photo_path, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'aktivní', ?)",
                (contract_number, customer_id, created_at, rental_from, rental_to, total_price, deposit, paid_amount, self.payment_method.get(), self.entries['issue_photo_path'].get().strip(), notes)
            )
        issue_condition = self.entries['issue_condition'].get().strip()
        accessory_totals_sum = 0.0
        for machine in selected:
            machine_id = int(machine['id'])
            accessories_text = self._collect_machine_accessories_text(machine_id)
            if not accessories_text:
                accessories_text = row_value(machine, 'accessories', '')
            accessories_total = self._collect_machine_accessories_total(machine_id)
            accessory_totals_sum += accessories_total
            self.app.db.execute(
                "INSERT INTO contract_items(contract_id, machine_id, issue_condition, accessories_issued, accessories_total) VALUES (?, ?, ?, ?, ?)",
                (contract_id, machine_id, issue_condition, accessories_text, accessories_total)
            )
            self.app.db.execute("UPDATE machines SET status='půjčený' WHERE id=?", (machine_id,))
        if accessory_totals_sum:
            self.app.db.execute("UPDATE contracts SET total_price=COALESCE(total_price,0)+? WHERE id=?", (accessory_totals_sum, contract_id))
        detail = self.app.db.get_contract_detail(contract_id)
        customer = self.app.db.fetchone('SELECT * FROM customers WHERE id=?', (customer_id,))
        self.app.pdf.create_contract_pdf(detail['contract'], customer, detail['items'], self.app.db.get_settings())
        self.on_saved(); self.app.refresh_all(); self.destroy()

class ReservationEditor(ModalFormWindow):
    def __init__(self, master, app, on_saved):
        super().__init__(master, 'Nová rezervace', 1020, 820, 'Vytvořit rezervaci', self.save, subtitle='Rezervuj stroje dopředu bez vytvoření aktivní smlouvy')
        self.app = app; self.on_saved = on_saved
        customers = self.app.db.fetchall('SELECT id, name, company FROM customers ORDER BY name')
        machines = self.app.db.fetchall("SELECT * FROM machines WHERE status!='vyřazený' ORDER BY name")
        if not customers:
            messagebox.showerror('Chyba', 'Nejdřív přidej zákazníka.'); self.destroy(); return
        self.customer_map = {f"{row_value(c,'name')} | {row_value(c,'company')}": c['id'] for c in customers}
        form = ctk.CTkFrame(self.body, corner_radius=18)
        form.grid(row=0, column=0, sticky='ew')
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(form, text='Zákazník').grid(row=0, column=0, padx=16, pady=10, sticky='w')
        self.customer_cb = ctk.CTkComboBox(form, values=list(self.customer_map.keys()), width=420)
        self.customer_cb.grid(row=0, column=1, padx=16, pady=10, sticky='ew')
        self.customer_cb.set(list(self.customer_map.keys())[0])
        self.entries = {}
        defaults = {'reserved_from': format_date((date.today() + timedelta(days=1)).strftime('%Y-%m-%d')), 'reserved_to': format_date((date.today() + timedelta(days=1)).strftime('%Y-%m-%d')), 'total_price': '0', 'deposit': '0'}
        for i, (label, key) in enumerate([('Od', 'reserved_from'), ('Do', 'reserved_to'), ('Cena celkem', 'total_price'), ('Kauce', 'deposit')], start=1):
            ctk.CTkLabel(form, text=label).grid(row=i, column=0, padx=16, pady=10, sticky='w')
            ent = ctk.CTkEntry(form, width=220, height=38); ent.grid(row=i, column=1, padx=16, pady=10, sticky='w'); ent.insert(0, defaults[key]); self.entries[key] = ent
            if key in ('reserved_from', 'reserved_to'):
                ctk.CTkButton(form, text='📅', width=42, command=lambda e=ent: pick_date_for_entry(self, e)).grid(row=i, column=2, padx=6, pady=10)
        ctk.CTkLabel(form, text='Stroje').grid(row=5, column=0, padx=16, pady=10, sticky='nw')
        self.machine_box = ctk.CTkScrollableFrame(form, width=600, height=280)
        self.machine_box.grid(row=5, column=1, padx=16, pady=10, sticky='ew')
        self.machine_vars = []
        for machine in machines:
            var = ctk.StringVar(value='0')
            ctk.CTkCheckBox(self.machine_box, text=f"{row_value(machine,'name')} | {row_value(machine,'inventory_number')} | stav: {row_value(machine,'status')}", variable=var, onvalue='1', offvalue='0').pack(anchor='w', pady=4)
            self.machine_vars.append((machine, var))
        ctk.CTkLabel(form, text='Poznámka').grid(row=6, column=0, padx=16, pady=10, sticky='nw')
        self.notes = ctk.CTkTextbox(form, width=600, height=110)
        self.notes.grid(row=6, column=1, padx=16, pady=(10, 18), sticky='ew')

    def save(self):
        try:
            total_price = float(self.entries['total_price'].get().strip().replace(',', '.') or 0)
            deposit = float(self.entries['deposit'].get().strip().replace(',', '.') or 0)
            d1 = parse_date_input(self.entries['reserved_from'].get())
            d2 = parse_date_input(self.entries['reserved_to'].get())
        except ValueError as exc:
            messagebox.showerror('Chyba', str(exc)); return
        customer_id = self.customer_map[self.customer_cb.get()]
        selected = [m for m, var in self.machine_vars if var.get() == '1']
        if not selected:
            messagebox.showerror('Chyba', 'Vyber aspoň jeden stroj.'); return
        conflicts = []
        for machine in selected:
            conflicts.extend(self.app.db.check_machine_conflicts(machine['id'], d1, d2))
        if conflicts:
            messagebox.showerror('Kolize termínů', 'Vybrané stroje mají v tomto termínu kolizi:\n\n' + '\n'.join(f'• {c}' for c in conflicts)); return
        rid = self.app.db.execute("INSERT INTO reservations(reservation_number, customer_id, created_at, reserved_from, reserved_to, total_price, deposit, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, 'rezervace', ?)", (self.app.db.generate_reservation_number(), customer_id, datetime.now().strftime('%Y-%m-%d'), d1, d2, total_price, deposit, self.notes.get('1.0', 'end').strip()))
        for machine in selected:
            self.app.db.execute('INSERT INTO reservation_items(reservation_id, machine_id) VALUES (?, ?)', (rid, machine['id']))
        self.on_saved(); self.app.refresh_all(); self.destroy()

class ReturnDialog(ModalFormWindow):
    def __init__(self, master, app, contract_id: int, on_saved):
        super().__init__(master, 'Vrácení stroje', 940, 860, 'Uložit vrácení', self.save, subtitle='Ukončení smlouvy a založení následného servisu')
        self.app = app; self.contract_id = contract_id; self.on_saved = on_saved
        detail = self.app.db.get_contract_detail(contract_id)
        self.contract = detail['contract']; self.items = detail['items']
        ctk.CTkLabel(self.body, text=f"Vrácení smlouvy {row_value(self.contract, 'contract_number')}", font=ctk.CTkFont(size=18, weight='bold')).grid(row=0, column=0, sticky='w', pady=(0, 10))
        form = ctk.CTkFrame(self.body, corner_radius=18); form.grid(row=1, column=0, sticky='ew')
        form.grid_columnconfigure(1, weight=1)
        self.entries = {}
        defaults = {'returned_at': format_date(datetime.now().strftime('%Y-%m-%d')), 'return_photo_path': '', 'deposit_returned': str(row_value(self.contract, 'deposit', 0)), 'return_extra_charge': '0', 'return_condition': 'Vráceno v pořádku', 'accessories_returned': '', 'damage_notes': ''}
        fields = [('Datum vrácení', 'returned_at'), ('Fotografie při vrácení', 'return_photo_path'), ('Vrácená kauce', 'deposit_returned'), ('Doplatek / škoda', 'return_extra_charge'), ('Stav při vrácení', 'return_condition'), ('Vrácené příslušenství', 'accessories_returned'), ('Poškození', 'damage_notes')]
        for i, (label, key) in enumerate(fields):
            ctk.CTkLabel(form, text=label).grid(row=i, column=0, padx=16, pady=10, sticky='w')
            ent = ctk.CTkEntry(form, width=420, height=38); ent.grid(row=i, column=1, padx=16, pady=10, sticky='ew'); ent.insert(0, defaults[key]); self.entries[key] = ent
            if key == 'returned_at':
                ctk.CTkButton(form, text='📅', width=42, command=lambda e=ent: pick_date_for_entry(self, e)).grid(row=i, column=2, padx=6, pady=10)
            if key == 'return_photo_path':
                ctk.CTkButton(form, text='Vybrat soubor', width=120, command=self.browse_return_photo).grid(row=i, column=2, padx=10, pady=10)

    def browse_return_photo(self):
        path = filedialog.askopenfilename(
            title='Vyber fotku při vrácení',
            filetypes=[('Obrázky', '*.png;*.jpg;*.jpeg;*.webp;*.bmp'), ('Všechny soubory', '*.*')]
        )
        if not path:
            return
        self.entries['return_photo_path'].delete(0, 'end')
        self.entries['return_photo_path'].insert(0, path)

    def save(self):
        try:
            dep = float(self.entries['deposit_returned'].get().strip().replace(',', '.') or 0)
            extra = float(self.entries['return_extra_charge'].get().strip().replace(',', '.') or 0)
            returned_at = parse_date_input(self.entries['returned_at'].get())
        except ValueError as exc:
            messagebox.showerror('Chyba', str(exc)); return
        self.app.db.execute("UPDATE contracts SET status='vráceno', returned_at=?, return_date=?, return_photo_path=?, deposit_returned=?, return_extra_charge=? WHERE id=?", (returned_at, returned_at, self.entries['return_photo_path'].get().strip(), dep, extra, self.contract_id))
        for item in self.items:
            machine_id = row_value(item, 'machine_id') or row_value(item, 'id')
            self.app.db.execute("UPDATE contract_items SET return_condition=?, accessories_returned=?, damage_notes=? WHERE contract_id=? AND machine_id=?", (self.entries['return_condition'].get().strip(), self.entries['accessories_returned'].get().strip(), self.entries['damage_notes'].get().strip(), self.contract_id, machine_id))
            current_mh = row_value(item, 'motohours', None)
            current_due_mh = row_value(item, 'service_due_motohours', None)
            self.app.db.create_service_record(int(machine_id), returned_at, 'Pravidelná údržba po vrácení', 0, '', f"Automaticky vytvořeno po vrácení smlouvy {row_value(self.contract, 'contract_number')}", '', current_mh, current_due_mh)
        customer = self.app.db.fetchone('SELECT * FROM customers WHERE id=?', (self.contract['customer_id'],))
        detail = self.app.db.get_contract_detail(self.contract_id)
        self.app.pdf.create_return_protocol_pdf(detail['contract'], customer, detail['items'], self.app.db.get_settings())
        messagebox.showinfo('Vrácení', 'Smlouva byla ukončena a stroj byl přesunut do servisu jako pravidelná údržba po vrácení. Po dokončení údržby ho označ v Servisu jako dokončený a vrátí se do stavu volný.')
        self.on_saved(); self.app.refresh_all(); self.destroy()
