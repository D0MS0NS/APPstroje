from __future__ import annotations
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from PIL import Image
from utils import row_value, format_currency, format_date, parse_date_input, center_window, pick_date_for_entry, style_treeview, ModalFormWindow


def parse_machine_categories(raw: str) -> list[str]:
    items: list[str] = []
    for line in (raw or '').replace(';', '\n').splitlines():
        value = line.strip()
        if value and value not in items:
            items.append(value)
    return items


def machine_categories_from_app(app) -> list[str]:
    try:
        settings = app.db.get_settings()
        return parse_machine_categories(settings.get('machine_categories', ''))
    except Exception:
        return []


class MachinesView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(fg_color='transparent')
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, corner_radius=24, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047"))
        top.grid(row=0, column=0, sticky='ew', padx=22, pady=(22, 12))
        top.grid_columnconfigure(1, weight=1)
        left = ctk.CTkFrame(top, fg_color='transparent')
        left.grid(row=0, column=0, sticky='w', padx=18, pady=16)
        ctk.CTkLabel(left, text='Stroje', font=ctk.CTkFont(size=28, weight='bold')).pack(anchor='w')
        ctk.CTkLabel(left, text='Přehled techniky, dostupnosti, cen a motohodin', text_color=("#64748b", "#94a3b8")).pack(anchor='w', pady=(2,0))
        ctk.CTkButton(top, text='Přidat stroj', height=40, corner_radius=14, command=self.open_add).grid(row=0, column=2, sticky='e', padx=18, pady=16)

        summary = ctk.CTkFrame(self, corner_radius=22, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047"))
        summary.grid(row=1, column=0, sticky='ew', padx=22, pady=(0, 12))
        self.total_lbl = ctk.CTkLabel(summary, text='Stroje: 0', font=ctk.CTkFont(size=16, weight='bold'))
        self.total_lbl.pack(side='left', padx=16, pady=14)
        self.status_summary_lbl = ctk.CTkLabel(summary, text='Volné: 0 • Půjčené: 0 • Servis: 0', text_color=("#64748b", "#94a3b8"))
        self.status_summary_lbl.pack(side='left', padx=8, pady=14)
        self.selection_lbl = ctk.CTkLabel(summary, text='Vybraný stroj: žádný', text_color=("#64748b", "#94a3b8"))
        self.selection_lbl.pack(side='right', padx=16, pady=14)

        toolbar = ctk.CTkFrame(self, corner_radius=22, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047"))
        toolbar.grid(row=2, column=0, sticky='ew', padx=22, pady=(0, 12))
        toolbar.grid_columnconfigure(0, weight=1)
        self.search = ctk.CTkEntry(toolbar, placeholder_text='Hledat podle názvu / inventárního čísla / příslušenství', height=40, corner_radius=14)
        self.search.grid(row=0, column=0, sticky='ew', padx=14, pady=14)
        self.search.bind('<KeyRelease>', lambda e: self.refresh())
        self.status_filter = ctk.CTkComboBox(toolbar, values=['Vše', 'volný', 'půjčený', 'servis', 'blokovaný', 'vyřazený'], width=170, height=40, command=lambda _=None: self.refresh())
        self.status_filter.grid(row=0, column=1, padx=(0, 10), pady=14)
        self.status_filter.set('Vše')
        self.category_filter = ctk.CTkComboBox(toolbar, values=['Všechny kategorie'], width=220, height=40, command=lambda _=None: self.refresh())
        self.category_filter.grid(row=0, column=2, padx=(0, 14), pady=14)
        self.category_filter.set('Všechny kategorie')
        ctk.CTkButton(toolbar, text='Reset', width=84, height=40, corner_radius=14, command=self.reset_filters).grid(row=0, column=3, padx=(0,14), pady=14)

        frame = ctk.CTkFrame(self, corner_radius=22, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047"))
        frame.grid(row=3, column=0, sticky='nsew', padx=22, pady=(0, 22))
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(frame, fg_color='transparent')
        head.grid(row=0, column=0, columnspan=2, sticky='ew', padx=14, pady=(14, 8))
        ctk.CTkLabel(head, text='Seznam strojů', font=ctk.CTkFont(size=18, weight='bold')).pack(side='left')
        ctk.CTkLabel(head, text='Dvojklik otevře detail stroje', text_color=("#64748b", "#94a3b8")).pack(side='left', padx=(10,0))
        cols = ('id', 'name', 'category', 'inventory', 'status', 'motohours', 'daily_rate', 'deposit', 'accessories')
        self.tree = ttk.Treeview(frame, columns=cols, show='headings')
        style_treeview(self.tree, 'Machines')
        for status, bg in [('volný', '#dcfce7'), ('půjčený', '#fef3c7'), ('servis', '#e0e7ff'), ('blokovaný', '#fecaca'), ('vyřazený', '#e5e7eb')]:
            self.tree.tag_configure(status, background=bg)
        for col, title, width in [
            ('id', 'ID', 50), ('name', 'Název', 230), ('category', 'Kategorie', 150), ('inventory', 'Inventární číslo', 150),
            ('status', 'Stav', 110), ('motohours', 'Motohodiny', 110), ('daily_rate', 'Cena/den', 100), ('deposit', 'Kauce', 100), ('accessories', 'Příslušenství', 240)
        ]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor='w')
        self.tree.grid(row=1, column=0, sticky='nsew', padx=(14,0), pady=(0,0))
        self.tree.bind('<Double-1>', lambda e: self.open_detail())
        self.tree.bind('<<TreeviewSelect>>', lambda e: self.update_selection_label())
        scroll = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky='ns', padx=(0,14), pady=(0,0))

        actions = ctk.CTkFrame(frame, fg_color='transparent')
        actions.grid(row=2, column=0, columnspan=2, sticky='w', padx=14, pady=14)
        self.detail_btn = ctk.CTkButton(actions, text='Detail stroje', height=38, corner_radius=14, command=self.open_detail, state='disabled')
        self.detail_btn.pack(side='left')

    def reset_filters(self):
        self.search.delete(0, 'end')
        self.status_filter.set('Vše')
        self.category_filter.set('Všechny kategorie')
        self.refresh()

    def update_selection_label(self):
        sel = self.tree.selection()
        if sel:
            vals = self.tree.item(sel[0], 'values')
            self.selection_lbl.configure(text=f'Vybraný stroj: {vals[1]}')
            self.detail_btn.configure(state='normal')
        else:
            self.selection_lbl.configure(text='Vybraný stroj: žádný')
            self.detail_btn.configure(state='disabled')

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        q = self.search.get().strip().lower()
        status_filter = self.status_filter.get()
        categories = machine_categories_from_app(self.app)
        current_cat = self.category_filter.get() if hasattr(self, 'category_filter') else 'Všechny kategorie'
        cat_values = ['Všechny kategorie'] + categories
        try:
            self.category_filter.configure(values=cat_values)
            self.category_filter.set(current_cat if current_cat in cat_values else 'Všechny kategorie')
            current_cat = self.category_filter.get()
        except Exception:
            current_cat = 'Všechny kategorie'

        rows = self.app.db.fetchall('SELECT * FROM machines ORDER BY id DESC')
        shown = 0
        counts = {'volný': 0, 'půjčený': 0, 'servis': 0}
        for r in rows:
            name = str(row_value(r, 'name'))
            inventory = str(row_value(r, 'inventory_number'))
            category = str(row_value(r, 'category'))
            accessories = str(row_value(r, 'accessories'))
            status = row_value(r, 'status', 'volný')
            counts[status] = counts.get(status, 0) + 1
            if q and q not in (name + ' ' + inventory + ' ' + accessories + ' ' + category).lower():
                continue
            if status_filter != 'Vše' and status != status_filter:
                continue
            if current_cat != 'Všechny kategorie' and category != current_cat:
                continue
            self.tree.insert('', 'end', values=(
                row_value(r, 'id'), name, category, inventory, status, row_value(r, 'motohours', 0),
                format_currency(row_value(r, 'daily_rate', 0)), format_currency(row_value(r, 'deposit', 0)), accessories
            ), tags=(status,))
            shown += 1

        self.total_lbl.configure(text=f'Stroje: {shown}')
        self.status_summary_lbl.configure(text=f"Volné: {counts.get('volný', 0)} • Půjčené: {counts.get('půjčený', 0)} • Servis: {counts.get('servis', 0)}")
        self.update_selection_label()

    def _selected_id(self):
        selected = self.tree.selection()
        return int(self.tree.item(selected[0], 'values')[0]) if selected else None

    def open_add(self):
        MachineEditor(self, self.app, None, self.refresh)

    def open_edit(self):
        machine_id = self._selected_id()
        if machine_id is None:
            return
        row = self.app.db.fetchone('SELECT * FROM machines WHERE id=?', (machine_id,))
        MachineEditor(self, self.app, row, self.refresh)

    def open_detail(self):
        machine_id = self._selected_id()
        if machine_id is None:
            return
        self.app.open_machine_detail(machine_id)

    def delete_selected(self):
        machine_id = self._selected_id()
        if machine_id is None:
            messagebox.showwarning('Nic není vybráno', 'Nejdřív vyber stroj, který chceš smazat.')
            return
        row = self.app.db.fetchone('SELECT * FROM machines WHERE id=?', (machine_id,))
        if not row:
            messagebox.showerror('Chyba', 'Vybraný stroj se nepodařilo načíst.')
            return
        status = row_value(row, 'status', 'volný')
        if status in ('půjčený', 'servis', 'blokovaný'):
            messagebox.showerror('Nelze smazat', 'Stroj nelze smazat, protože je právě půjčený, v servisu nebo blokovaný.')
            return
        used = self.app.db.fetchone('SELECT COUNT(*) AS cnt FROM contract_items WHERE machine_id=?', (machine_id,))
        if used and int(used['cnt']) > 0:
            ok = messagebox.askyesno('Potvrzení', 'Stroj má historii ve smlouvách. Opravdu chceš záznam stroje smazat?')
            if not ok:
                return
        else:
            ok = messagebox.askyesno('Potvrzení', 'Opravdu chceš smazat vybraný stroj?')
            if not ok:
                return
        self.app.db.execute('DELETE FROM machines WHERE id=?', (machine_id,))
        self.refresh()
        self.app.refresh_all()


class MachineEditor(ModalFormWindow):
    def __init__(self, master, app, row, on_saved):
        super().__init__(master, 'Stroj', 1040, 860, 'Uložit stroj', self.save, subtitle='Základní údaje, servis, foto i příslušenství stroje na jednom místě')
        self.app = app
        self.row = row
        self.on_saved = on_saved

        fields = [
            ('Název', 'name'), ('Inventární číslo', 'inventory_number'), ('Model', 'model'), ('Sériové číslo', 'serial_number'),
            ('Cena za den', 'daily_rate'), ('Kauce', 'deposit'), ('Motohodiny', 'motohours'), ('Servis při MH', 'service_due_motohours'), ('Příslušenství stroje', 'accessories'), ('Poslední servis', 'last_service_date'),
            ('Příští servis', 'next_service_date'), ('Fotka stroje', 'photo_path')
        ]
        self.entries = {}
        form = ctk.CTkFrame(self.body, corner_radius=18)
        form.grid(row=0, column=0, sticky='ew')
        form.grid_columnconfigure(1, weight=1)

        categories = machine_categories_from_app(self.app)
        ctk.CTkLabel(form, text='Kategorie').grid(row=0, column=0, padx=16, pady=10, sticky='w')
        self.category_var = ctk.CTkComboBox(form, values=categories if categories else [''], width=460)
        self.category_var.grid(row=0, column=1, padx=16, pady=10, sticky='ew')
        current_category = str(row_value(row, 'category', '') or '') if row else ''
        if current_category and current_category not in categories:
            categories = categories + [current_category]
            self.category_var.configure(values=categories)
        self.category_var.set(current_category if current_category else (categories[0] if categories else ''))

        defaults = self.app.db.get_settings()
        for i, (label, key) in enumerate(fields, start=1):
            ctk.CTkLabel(form, text=label).grid(row=i, column=0, padx=16, pady=10, sticky='w')
            ent = ctk.CTkEntry(form, width=460, height=38)
            ent.grid(row=i, column=1, padx=16, pady=10, sticky='ew')
            if row:
                value = row_value(row, key, '')
                if key in ('last_service_date', 'next_service_date'):
                    value = format_date(value) if value else ''
                ent.insert(0, str(value))
            self.entries[key] = ent
            if key in ('last_service_date', 'next_service_date'):
                ctk.CTkButton(form, text='📅', width=42, command=lambda e=ent: pick_date_for_entry(self, e)).grid(row=i, column=2, padx=6, pady=8)
            if key == 'photo_path':
                ctk.CTkButton(form, text='Vybrat soubor', width=120, command=self.browse_photo).grid(row=i, column=2, padx=10, pady=8)
            if key == 'accessories':
                ctk.CTkLabel(form, text='Piš položky po řádcích nebo oddělené čárkou. Tyto položky se pak ve smlouvě zobrazí jako checkboxy.', text_color=('gray35','gray70'), wraplength=260, justify='left').grid(row=i, column=2, padx=10, pady=8, sticky='w')

        self.preview_label = ctk.CTkLabel(form, text='Bez náhledu', width=220, height=150)
        self.preview_label.grid(row=0, column=3, rowspan=6, padx=(10, 16), pady=12, sticky='n')
        self._preview_image = None
        ctk.CTkButton(form, text='Otevřít fotku', width=120, command=self.open_photo).grid(row=6, column=3, padx=(10, 0), pady=(4, 8), sticky='n')
        if row:
            ctk.CTkButton(form, text='Galerie v detailu', width=120, command=lambda: self.app.open_machine_detail(row['id'])).grid(row=7, column=3, padx=(10, 0), pady=(0, 8), sticky='n')
            ctk.CTkButton(form, text='Spravovat příslušenství', width=150, command=self.open_accessory_presets).grid(row=8, column=3, padx=(10, 0), pady=(0, 8), sticky='n')
        else:
            ctk.CTkLabel(form, text='Další fotky přidáš po uložení v detailu stroje.', text_color=('gray35','gray70'), wraplength=220, justify='left').grid(row=7, column=3, padx=(10, 16), pady=(0, 8), sticky='n')
            ctk.CTkLabel(form, text='Cenové položky příslušenství nastavíš po prvním uložení stroje.', text_color=('gray35','gray70'), wraplength=220, justify='left').grid(row=8, column=3, padx=(10, 16), pady=(0, 8), sticky='n')
        self.update_preview()

        ctk.CTkLabel(form, text='Stav').grid(row=len(fields) + 1, column=0, padx=16, pady=10, sticky='w')
        self.status = ctk.CTkComboBox(form, values=['volný', 'půjčený', 'servis', 'blokovaný', 'vyřazený'])
        self.status.grid(row=len(fields) + 1, column=1, padx=16, pady=10, sticky='w')
        self.status.set(row_value(row, 'status', 'volný') if row else 'volný')

        ctk.CTkLabel(form, text='Poznámka').grid(row=len(fields) + 2, column=0, padx=16, pady=10, sticky='nw')
        self.notes = ctk.CTkTextbox(form, width=460, height=120)
        self.notes.grid(row=len(fields) + 2, column=1, padx=16, pady=(10, 18), sticky='ew')
        if row:
            self.notes.insert('1.0', row_value(row, 'notes', ''))

    def open_accessory_presets(self):
        if not self.row:
            messagebox.showinfo('Příslušenství stroje', 'Nejdřív ulož stroj, potom můžeš spravovat položky příslušenství a jejich ceny.')
            return
        AccessoryPresetManager(self, self.app, int(self.row['id']))

    def browse_photo(self):
        path = filedialog.askopenfilename(title='Vyber fotku stroje', filetypes=[('Obrázky', '*.png;*.jpg;*.jpeg;*.webp;*.bmp'), ('Všechny soubory', '*.*')])
        if not path:
            return
        self.entries['photo_path'].delete(0, 'end')
        self.entries['photo_path'].insert(0, path)
        self.update_preview()

    def open_photo(self):
        self.app.open_image_file(self.entries['photo_path'].get().strip())

    def update_preview(self):
        path = self.entries['photo_path'].get().strip()
        if not path:
            self.preview_label.configure(text='Bez náhledu', image=None)
            return
        try:
            img = Image.open(path)
            img.thumbnail((220, 150))
            self._preview_image = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            self.preview_label.configure(text='', image=self._preview_image)
        except Exception:
            self.preview_label.configure(text='Náhled nelze zobrazit', image=None)

    def save(self):
        data = {k: e.get().strip() for k, e in self.entries.items()}
        data['notes'] = self.notes.get('1.0', 'end').strip()
        data['status'] = self.status.get()
        data['category'] = self.category_var.get().strip()
        try:
            daily_rate = float(data['daily_rate'] or 0)
            deposit = float(data['deposit'] or 0)
            motohours = float((data.get('motohours') or '0').replace(',', '.'))
            service_due_mh = float((data.get('service_due_motohours') or '0').replace(',', '.')) if data.get('service_due_motohours') else 0
        except ValueError:
            messagebox.showerror('Chyba', 'Cena, kauce a motohodiny musí být číslo.')
            return
        try:
            last_service = parse_date_input(data['last_service_date']) if data['last_service_date'] else ''
            next_service = parse_date_input(data['next_service_date']) if data['next_service_date'] else ''
        except ValueError as exc:
            messagebox.showerror('Chyba', str(exc))
            return

        inventory_number = data['inventory_number']
        if inventory_number:
            existing = self.app.db.fetchone('SELECT id, name FROM machines WHERE inventory_number=?', (inventory_number,))
            if existing and (not self.row or int(existing['id']) != int(self.row['id'])):
                messagebox.showerror('Duplicitní inventární číslo', f"Stroj s inventárním číslem '{inventory_number}' už existuje. Zvol jiné číslo nebo uprav existující záznam.")
                self.entries['inventory_number'].focus_set()
                return

        params = (data['name'], data['category'], data['inventory_number'], data['model'], data['serial_number'], daily_rate, deposit, motohours, service_due_mh, data['status'], data['notes'], data['photo_path'], data['accessories'], last_service, next_service)
        try:
            if self.row:
                self.app.db.execute('UPDATE machines SET name=?, category=?, inventory_number=?, model=?, serial_number=?, daily_rate=?, deposit=?, motohours=?, service_due_motohours=?, status=?, notes=?, photo_path=?, accessories=?, last_service_date=?, next_service_date=? WHERE id=?', params + (self.row['id'],))
            else:
                self.app.db.execute('INSERT INTO machines(name, category, inventory_number, model, serial_number, daily_rate, deposit, motohours, service_due_motohours, status, notes, photo_path, accessories, last_service_date, next_service_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', params)
        except Exception as exc:
            msg = str(exc)
            if 'UNIQUE constraint failed: machines.inventory_number' in msg:
                messagebox.showerror('Duplicitní inventární číslo', f"Stroj s inventárním číslem '{inventory_number}' už existuje. Zvol jiné číslo nebo uprav existující záznam.")
                self.entries['inventory_number'].focus_set()
                return
            messagebox.showerror('Chyba při ukládání', msg)
            return

        self.on_saved()
        self.app.refresh_all()
        self.destroy()


class AccessoryPresetEditor(ModalFormWindow):
    def __init__(self, master, app, machine_id:int, row, on_saved):
        super().__init__(master, 'Položka příslušenství', 720, 360, 'Uložit položku', self.save, subtitle='U každé položky můžeš nastavit název a volitelnou cenu do smlouvy')
        self.app = app
        self.machine_id = machine_id
        self.row = row
        self.on_saved = on_saved
        wrap = ctk.CTkFrame(self.body, corner_radius=18)
        wrap.grid(row=0, column=0, sticky='ew')
        wrap.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(wrap, text='Název příslušenství').grid(row=0, column=0, padx=16, pady=12, sticky='w')
        self.name_ent = ctk.CTkEntry(wrap, height=38)
        self.name_ent.grid(row=0, column=1, padx=16, pady=12, sticky='ew')
        ctk.CTkLabel(wrap, text='Cena příslušenství').grid(row=1, column=0, padx=16, pady=12, sticky='w')
        self.price_ent = ctk.CTkEntry(wrap, height=38)
        self.price_ent.grid(row=1, column=1, padx=16, pady=12, sticky='ew')
        ctk.CTkLabel(wrap, text='Tip: zadej 0, pokud je příslušenství v ceně půjčení.', text_color=('gray35','gray70')).grid(row=2, column=1, padx=16, pady=(0, 14), sticky='w')
        if row:
            self.name_ent.insert(0, row_value(row, 'accessory_name'))
            self.price_ent.insert(0, str(row_value(row, 'accessory_price', 0)))

    def save(self):
        name = self.name_ent.get().strip()
        if not name:
            messagebox.showerror('Chyba', 'Zadej název příslušenství.')
            return
        try:
            price = float(self.price_ent.get().strip().replace(',', '.') or 0)
        except ValueError:
            messagebox.showerror('Chyba', 'Cena příslušenství musí být číslo.')
            return
        if self.row:
            self.app.db.update_machine_accessory(int(self.row['id']), name, price)
        else:
            self.app.db.add_machine_accessory(self.machine_id, name, price)
        self.on_saved()
        self.destroy()


class AccessoryPresetManager(ctk.CTkToplevel):
    def __init__(self, master, app, machine_id:int):
        super().__init__(master)
        self.app = app
        self.machine_id = machine_id
        self.title('Příslušenství stroje')
        self.geometry('920x620')
        self.minsize(860, 560)
        self.grab_set()
        center_window(self, 920, 620)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        machine = self.app.db.fetchone('SELECT name, inventory_number FROM machines WHERE id=?', (machine_id,))
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("#f8fafc", "#0f172a"))
        header.grid(row=0, column=0, sticky='ew')
        header.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(header, fg_color='transparent')
        left.grid(row=0, column=0, sticky='w', padx=18, pady=14)
        ctk.CTkLabel(left, text='Příslušenství stroje', font=ctk.CTkFont(size=22, weight='bold')).pack(anchor='w')
        ctk.CTkLabel(left, text=f"{row_value(machine,'name')} • {row_value(machine,'inventory_number') or 'bez inv. čísla'}", text_color=("#64748b", "#94a3b8")).pack(anchor='w', pady=(3,0))
        actions = ctk.CTkFrame(header, fg_color='transparent')
        actions.grid(row=0, column=1, sticky='e', padx=18, pady=14)
        ctk.CTkButton(actions, text='Nová položka', command=self.add_preset).pack(side='left')
        ctk.CTkButton(actions, text='Zavřít', width=96, fg_color=("#e5e7eb", "#1f2937"), hover_color=("#d1d5db", "#374151"), text_color=("#111827", "#f9fafb"), command=self.destroy).pack(side='left', padx=(10,0))
        body = ctk.CTkFrame(self, corner_radius=18)
        body.grid(row=1, column=0, sticky='nsew', padx=18, pady=18)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(body, columns=('name','price'), show='headings')
        self.tree.heading('name', text='Příslušenství')
        self.tree.heading('price', text='Cena')
        self.tree.column('name', width=620, anchor='w')
        self.tree.column('price', width=180, anchor='w')
        style_treeview(self.tree, 'AccessoryItems')
        self.tree.grid(row=0, column=0, sticky='nsew', padx=(12,0), pady=12)
        self.tree.bind('<Double-1>', lambda e: self.edit_selected())
        scroll = ttk.Scrollbar(body, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky='ns', pady=12, padx=(0,12))
        btns = ctk.CTkFrame(body, fg_color='transparent')
        btns.grid(row=1, column=0, sticky='w', padx=12, pady=(0,12))
        ctk.CTkButton(btns, text='Upravit', command=self.edit_selected).pack(side='left')
        ctk.CTkButton(btns, text='Smazat', fg_color='#dc2626', hover_color='#b91c1c', command=self.delete_selected).pack(side='left', padx=8)
        self.refresh()

    def reset_filters(self):
        self.search.delete(0, 'end')
        self.status_filter.set('Vše')
        self.category_filter.set('Všechny kategorie')
        self.refresh()

    def update_selection_label(self):
        sel = self.tree.selection()
        if sel:
            vals = self.tree.item(sel[0], 'values')
            self.selection_lbl.configure(text=f'Vybraný stroj: {vals[1]}')
            self.detail_btn.configure(state='normal')
        else:
            self.selection_lbl.configure(text='Vybraný stroj: žádný')
            self.detail_btn.configure(state='disabled')

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.app.db.get_machine_accessories(self.machine_id):
            self.tree.insert('', 'end', iid=str(row['id']), values=(row_value(row, 'accessory_name'), format_currency(row_value(row, 'accessory_price', 0))))

    def _selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def add_preset(self):
        AccessoryPresetEditor(self, self.app, self.machine_id, None, self.refresh)

    def edit_selected(self):
        accessory_id = self._selected_id()
        if accessory_id is None:
            messagebox.showwarning('Příslušenství', 'Nejdřív vyber položku příslušenství.')
            return
        row = self.app.db.fetchone('SELECT * FROM machine_accessories WHERE id=?', (accessory_id,))
        if row:
            AccessoryPresetEditor(self, self.app, self.machine_id, row, self.refresh)

    def delete_selected(self):
        accessory_id = self._selected_id()
        if accessory_id is None:
            messagebox.showwarning('Příslušenství', 'Nejdřív vyber položku příslušenství.')
            return
        if not messagebox.askyesno('Potvrzení', 'Opravdu chceš tuto položku příslušenství smazat?'):
            return
        self.app.db.delete_machine_accessory(accessory_id)
        self.refresh()
