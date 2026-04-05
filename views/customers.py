from __future__ import annotations
import customtkinter as ctk
from tkinter import ttk, messagebox
from utils import row_value, center_window, style_treeview, ModalFormWindow


class CustomersView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(fg_color='transparent')
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, corner_radius=24, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047"))
        top.grid(row=0, column=0, sticky="ew", padx=22, pady=(22, 12))
        top.grid_columnconfigure(1, weight=1)
        left = ctk.CTkFrame(top, fg_color='transparent')
        left.grid(row=0, column=0, sticky='w', padx=18, pady=16)
        ctk.CTkLabel(left, text="Zákazníci", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor='w')
        ctk.CTkLabel(left, text="Klienti, jejich historie a aktivní zápůjčky v jednom přehledu", text_color=("#64748b", "#94a3b8")).pack(anchor='w', pady=(2,0))
        ctk.CTkButton(top, text="Přidat zákazníka", height=40, corner_radius=14, command=self.open_add).grid(row=0, column=2, sticky="e", padx=18, pady=16)

        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 12))
        cards.grid_columnconfigure((0,1,2), weight=1)
        self.total_card = self._make_card(cards, 0, "Celkem zákazníků")
        self.active_card = self._make_card(cards, 1, "Aktivní zákazníci")
        self.contracts_card = self._make_card(cards, 2, "Aktivní smlouvy")

        toolbar = ctk.CTkFrame(self, corner_radius=22, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047"))
        toolbar.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 12))
        toolbar.grid_columnconfigure(0, weight=1)
        self.search = ctk.CTkEntry(toolbar, placeholder_text="Hledat jméno / firmu / telefon / e-mail", height=40, corner_radius=14)
        self.search.grid(row=0, column=0, sticky="ew", padx=14, pady=14)
        self.search.bind("<KeyRelease>", lambda e: self.refresh())
        self.filter_mode = ctk.CTkComboBox(toolbar, values=["Vše", "Pouze aktivní"], width=180, height=40, command=lambda _=None: self.refresh())
        self.filter_mode.grid(row=0, column=1, padx=(0,14), pady=14)
        self.filter_mode.set("Vše")
        ctk.CTkButton(toolbar, text='Reset', width=84, height=40, corner_radius=14, command=self.reset_filters).grid(row=0, column=2, padx=(0,14), pady=14)

        table_wrap = ctk.CTkFrame(self, corner_radius=22, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047"))
        table_wrap.grid(row=3, column=0, sticky="nsew", padx=22, pady=(0, 22))
        table_wrap.grid_rowconfigure(1, weight=1)
        table_wrap.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(table_wrap, fg_color='transparent')
        head.grid(row=0, column=0, columnspan=2, sticky='ew', padx=14, pady=(14, 8))
        ctk.CTkLabel(head, text="Seznam zákazníků", font=ctk.CTkFont(size=18, weight='bold')).pack(side='left')
        ctk.CTkLabel(head, text="Dvojklik otevře detail zákazníka", text_color=("#64748b", "#94a3b8")).pack(side='left', padx=(10,0))

        self.tree = ttk.Treeview(table_wrap, columns=("id", "name", "company", "phone", "email", "active"), show="headings")
        for col, title, width in [("id", "ID", 60), ("name", "Jméno", 210), ("company", "Firma", 220), ("phone", "Telefon", 150), ("email", "E-mail", 280), ("active", "Aktivní smlouvy", 130)]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w")
        style_treeview(self.tree, 'Customers')
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(14,0), pady=(0,0))
        self.tree.bind("<Double-1>", lambda e: self.open_detail())
        self.tree.bind('<<TreeviewSelect>>', lambda e: self.update_selection_label())
        scroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky="ns", padx=(0,14), pady=(0,0))

        actions = ctk.CTkFrame(table_wrap, fg_color="transparent")
        actions.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=14)
        self.selection_lbl = ctk.CTkLabel(actions, text='Vybraný zákazník: žádný', text_color=("#64748b", "#94a3b8"))
        self.selection_lbl.pack(side='left')
        self.detail_btn = ctk.CTkButton(actions, text="Detail zákazníka", height=38, corner_radius=14, command=self.open_detail, state='disabled')
        self.detail_btn.pack(side="right")

    def reset_filters(self):
        self.search.delete(0, 'end')
        self.filter_mode.set('Vše')
        self.refresh()

    def update_selection_label(self):
        sel = self.tree.selection()
        if sel:
            vals = self.tree.item(sel[0], 'values')
            self.selection_lbl.configure(text=f'Vybraný zákazník: {vals[1]}')
            self.detail_btn.configure(state='normal')
        else:
            self.selection_lbl.configure(text='Vybraný zákazník: žádný')
            self.detail_btn.configure(state='disabled')

    def _make_card(self, master, column, title):
        card = ctk.CTkFrame(master, corner_radius=20, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047"))
        card.grid(row=0, column=column, sticky="ew", padx=6)
        ctk.CTkLabel(card, text=title, text_color=("#64748b", "#94a3b8"), font=ctk.CTkFont(size=13, weight='bold')).pack(anchor="w", padx=16, pady=(14,4))
        value = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=24, weight="bold"))
        value.pack(anchor="w", padx=16, pady=(0,12))
        return value

    def refresh(self):
        q = self.search.get().strip().lower()
        only_active = self.filter_mode.get() == "Pouze aktivní"
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = self.app.db.fetchall("""
            SELECT cu.*, 
                   (SELECT COUNT(*) FROM contracts c WHERE c.customer_id = cu.id AND c.status = 'aktivní') AS active_contracts
            FROM customers cu
            ORDER BY cu.id DESC
        """)
        shown = 0
        active_customers = 0
        active_contracts_total = 0
        for r in rows:
            active_contracts = int(row_value(r, 'active_contracts', 0) or 0)
            hay = f"{row_value(r,'name')} {row_value(r,'company')} {row_value(r,'phone')} {row_value(r,'email')}".lower()
            if q and q not in hay:
                continue
            if only_active and active_contracts == 0:
                continue
            if active_contracts > 0:
                active_customers += 1
            active_contracts_total += active_contracts
            self.tree.insert("", "end", values=(row_value(r, "id"), row_value(r, "name"), row_value(r, "company"), row_value(r, "phone"), row_value(r, "email"), active_contracts))
            shown += 1

        self.total_card.configure(text=str(shown))
        self.active_card.configure(text=str(active_customers))
        self.contracts_card.configure(text=str(active_contracts_total))
        self.update_selection_label()

    def open_add(self):
        CustomerEditor(self, self.app, None, self.refresh)

    def open_edit(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Nejdřív vyber zákazníka.")
            return
        cid = self.tree.item(selected[0], "values")[0]
        row = self.app.db.fetchone("SELECT * FROM customers WHERE id=?", (cid,))
        CustomerEditor(self, self.app, row, self.refresh)

    def open_detail(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Nejdřív vyber zákazníka.")
            return
        cid = int(self.tree.item(selected[0], "values")[0])
        self.app.open_customer_detail(cid)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Nejdřív vyber zákazníka.")
            return
        cid = int(self.tree.item(selected[0], "values")[0])
        if self.app.delete_customer(cid):
            self.refresh()


class CustomerEditor(ModalFormWindow):
    def __init__(self, master, app, row, on_saved):
        super().__init__(master, 'Zákazník', 820, 700, 'Uložit', self.save, subtitle='Přehledný formulář pro nového i existujícího zákazníka')
        self.app = app
        self.row = row
        self.on_saved = on_saved

        fields = [("Jméno", "name"), ("Firma", "company"), ("IČO", "ico"), ("DIČ", "dic"), ("Adresa", "address"), ("Telefon", "phone"), ("E-mail", "email"), ("Číslo OP", "id_card"), ("Č. ŘP", "driver_license"), ("Pas", "passport")]
        self.entries = {}
        form = ctk.CTkFrame(self.body, corner_radius=18)
        form.grid(row=0, column=0, sticky='ew')
        form.grid_columnconfigure(1, weight=1)
        for i, (label, key) in enumerate(fields):
            ctk.CTkLabel(form, text=label).grid(row=i, column=0, padx=16, pady=8, sticky="w")
            ent = ctk.CTkEntry(form, width=480, height=38)
            ent.grid(row=i, column=1, padx=16, pady=8, sticky="ew")
            if row:
                ent.insert(0, str(row_value(row, key, "") or ""))
            self.entries[key] = ent
        ctk.CTkLabel(form, text="Poznámka").grid(row=len(fields), column=0, padx=16, pady=8, sticky="nw")
        self.notes = ctk.CTkTextbox(form, width=480, height=150)
        self.notes.grid(row=len(fields), column=1, padx=16, pady=(8, 16), sticky="ew")
        if row:
            self.notes.insert("1.0", row_value(row, "notes", "") or "")

    def save(self):
        data = {k: e.get().strip() for k, e in self.entries.items()}
        notes = self.notes.get("1.0", "end").strip()
        if not data["name"]:
            messagebox.showerror("Chyba", "Jméno je povinné.")
            return
        full_name = data["name"]
        cols = self.app.db._get_columns("customers")
        if self.row:
            if "full_name" in cols:
                self.app.db.execute(
                    "UPDATE customers SET name=?, full_name=?, company=?, ico=?, dic=?, address=?, phone=?, email=?, id_card=?, driver_license=?, passport=?, notes=? WHERE id=?",
                    (data["name"], full_name, data["company"], data["ico"], data["dic"], data["address"], data["phone"], data["email"], data["id_card"], data["driver_license"], data["passport"], notes, self.row["id"]),
                )
            else:
                self.app.db.execute(
                    "UPDATE customers SET name=?, company=?, ico=?, dic=?, address=?, phone=?, email=?, id_card=?, driver_license=?, passport=?, notes=? WHERE id=?",
                    (data["name"], data["company"], data["ico"], data["dic"], data["address"], data["phone"], data["email"], data["id_card"], data["driver_license"], data["passport"], notes, self.row["id"]),
                )
        else:
            if "full_name" in cols:
                self.app.db.execute(
                    "INSERT INTO customers(name, full_name, company, ico, dic, address, phone, email, id_card, driver_license, passport, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (data["name"], full_name, data["company"], data["ico"], data["dic"], data["address"], data["phone"], data["email"], data["id_card"], data["driver_license"], data["passport"], notes),
                )
            else:
                self.app.db.execute(
                    "INSERT INTO customers(name, company, ico, dic, address, phone, email, id_card, driver_license, passport, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (data["name"], data["company"], data["ico"], data["dic"], data["address"], data["phone"], data["email"], data["id_card"], data["driver_license"], data["passport"], notes),
                )
        self.on_saved()
        self.app.refresh_all()
        self.destroy()
