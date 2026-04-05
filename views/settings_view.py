from __future__ import annotations
import customtkinter as ctk
from tkinter import messagebox
from settings import load_theme, save_theme


class SettingsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.entries = {}
        self.data = self.app.db.get_settings()

        self._build_header()
        self._build_body()

    def _build_header(self):
        header = ctk.CTkFrame(self, corner_radius=24, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047"))
        header.grid(row=0, column=0, padx=20, pady=(20, 14), sticky='ew')
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text='Nastavení', font=ctk.CTkFont(size=26, weight='bold')).grid(row=0, column=0, padx=18, pady=(14, 2), sticky='w')
        ctk.CTkLabel(header, text='Firma, dokumenty, provoz aplikace a rychlé akce na jednom místě', text_color=('gray35', 'gray75')).grid(row=1, column=0, padx=18, pady=(0, 14), sticky='w')
        ctk.CTkButton(header, text='Uložit nastavení', height=40, command=self.save).grid(row=0, column=1, rowspan=2, padx=18, pady=14, sticky='e')

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.grid(row=1, column=0, padx=20, pady=(0, 20), sticky='nsew')
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        tabs = ctk.CTkTabview(body)
        tabs.grid(row=0, column=0, sticky='nsew')
        for name in ('Firma', 'Dokumenty', 'Provoz aplikace', 'Rychlé akce'):
            tabs.add(name)
            tabs.tab(name).grid_columnconfigure(0, weight=1)

        self._build_company_tab(tabs.tab('Firma'))
        self._build_documents_tab(tabs.tab('Dokumenty'))
        self._build_operations_tab(tabs.tab('Provoz aplikace'))
        self._build_actions_tab(tabs.tab('Rychlé akce'))

    def _card(self, parent, title, subtitle=''):
        card = ctk.CTkFrame(parent, corner_radius=20, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047"))
        card.pack(fill='x', padx=6, pady=8)
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=17, weight='bold')).grid(row=0, column=0, columnspan=2, padx=16, pady=(14, 2), sticky='w')
        if subtitle:
            ctk.CTkLabel(card, text=subtitle, text_color=('gray35', 'gray75')).grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 10), sticky='w')
            start_row = 2
        else:
            start_row = 1
        return card, start_row

    def _add_entry_row(self, parent, row, label, key, width=520, password=False):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, padx=16, pady=8, sticky='w')
        ent = ctk.CTkEntry(parent, width=width, height=38, show='*' if password else None)
        ent.grid(row=row, column=1, padx=16, pady=8, sticky='ew')
        ent.insert(0, self.data.get(key, ''))
        self.entries[key] = ent
        return ent

    def _build_company_tab(self, tab):
        card, row = self._card(tab, 'Firemní údaje', 'Tyto údaje se používají v dokumentech a PDF výstupech')
        for label, key in [
            ('Název firmy', 'company_name'),
            ('Adresa', 'company_address'),
            ('Telefon', 'company_phone'),
            ('E-mail', 'company_email'),
            ('IČO', 'company_ico'),
            ('DIČ', 'company_dic'),
        ]:
            self._add_entry_row(card, row, label, key)
            row += 1

    def _build_documents_tab(self, tab):
        contract_card, row = self._card(tab, 'Smlouvy', 'Nastavení vzhledu a obsahu smluvních dokumentů')
        for label, key in [
            ('Název smlouvy', 'contract_title'),
            ('Krátký text pod názvem', 'contract_subtitle'),
            ('Místo podpisu', 'contract_place'),
        ]:
            self._add_entry_row(contract_card, row, label, key)
            row += 1

        ctk.CTkLabel(contract_card, text='Text smlouvy / podmínky').grid(row=row, column=0, padx=16, pady=8, sticky='nw')
        self.terms = ctk.CTkTextbox(contract_card, height=140)
        self.terms.grid(row=row, column=1, padx=16, pady=8, sticky='ew')
        self.terms.insert('1.0', self.data.get('contract_terms', ''))
        row += 1

        ctk.CTkLabel(contract_card, text='Prohlášení').grid(row=row, column=0, padx=16, pady=8, sticky='nw')
        self.declaration = ctk.CTkTextbox(contract_card, height=110)
        self.declaration.grid(row=row, column=1, padx=16, pady=(8, 16), sticky='ew')
        self.declaration.insert('1.0', self.data.get('contract_declaration', ''))

        protocol_card, row = self._card(tab, 'Vratný protokol', 'Vlastní texty a hlavička vratného protokolu')
        ctk.CTkLabel(protocol_card, text='Krátký text pod názvem').grid(row=row, column=0, padx=16, pady=8, sticky='nw')
        self.return_protocol_header_text = ctk.CTkTextbox(protocol_card, height=78)
        self.return_protocol_header_text.grid(row=row, column=1, padx=16, pady=8, sticky='ew')
        self.return_protocol_header_text.insert('1.0', self.data.get('return_protocol_header_text', ''))
        row += 1

        ctk.CTkLabel(protocol_card, text='Text ve spodní části protokolu').grid(row=row, column=0, padx=16, pady=8, sticky='nw')
        self.return_protocol_footer = ctk.CTkTextbox(protocol_card, height=110)
        self.return_protocol_footer.grid(row=row, column=1, padx=16, pady=(8, 16), sticky='ew')
        self.return_protocol_footer.insert('1.0', self.data.get('return_protocol_footer', ''))

    def _build_operations_tab(self, tab):
        machine_card, row = self._card(tab, 'Stroje a servis', 'Výchozí hodnoty a pomocné seznamy pro provoz aplikace')
        self._add_entry_row(machine_card, row, 'Upozornění na servis za kolik MH', 'default_service_interval_mh')
        row += 1
        ctk.CTkLabel(machine_card, text='Kategorie strojů').grid(row=row, column=0, padx=16, pady=8, sticky='nw')
        self.categories = ctk.CTkTextbox(machine_card, height=130)
        self.categories.grid(row=row, column=1, padx=16, pady=8, sticky='ew')
        self.categories.insert('1.0', self.data.get('machine_categories', ''))
        row += 1
        ctk.CTkLabel(machine_card, text='Jedna kategorie na řádek', text_color=('gray35', 'gray75')).grid(row=row, column=1, padx=16, pady=(0, 14), sticky='w')

        security_card, row = self._card(tab, 'Aplikace', 'Základní chování aplikace a vzhled prostředí')
        self._add_entry_row(security_card, row, 'PIN pro spuštění', 'pin_code', password=True)
        row += 1
        ctk.CTkLabel(security_card, text='Motiv').grid(row=row, column=0, padx=16, pady=(8, 16), sticky='w')
        self.theme = ctk.CTkComboBox(security_card, values=['dark', 'light'], width=180)
        self.theme.grid(row=row, column=1, padx=16, pady=(8, 16), sticky='w')
        self.theme.set(load_theme())

    def _build_actions_tab(self, tab):
        actions, _ = self._card(tab, 'Rychlé akce', 'Nástroje pro export a správu dat aplikace')
        btns = ctk.CTkFrame(actions, fg_color='transparent')
        btns.grid(row=1, column=0, columnspan=2, padx=12, pady=(4, 16), sticky='ew')
        for col in range(2):
            btns.grid_columnconfigure(col, weight=1)
        buttons = [
            ('Otevřít data', self.app.open_data_dir),
            ('Export strojů CSV', lambda: self.app.export_csv('machines', 'stroje')),
            ('Export zákazníků CSV', lambda: self.app.export_csv('customers', 'zakaznici')),
            ('Export smluv CSV', lambda: self.app.export_csv('contracts', 'smlouvy')),
            ('Záloha databáze', self.app.backup_db),
        ]
        ctk.CTkLabel(actions, text='Doporučení: po větších změnách udělej zálohu databáze.', text_color=('gray35', 'gray75')).grid(row=2, column=0, columnspan=2, padx=16, pady=(0, 12), sticky='w')
        for i, (label, cmd) in enumerate(buttons):
            r, c = divmod(i, 2)
            ctk.CTkButton(btns, text=label, height=40, command=cmd).grid(row=r, column=c, padx=8, pady=8, sticky='ew')

    def refresh(self):
        pass

    def save(self):
        values = {k: e.get().strip() for k, e in self.entries.items()}
        values['contract_terms'] = self.terms.get('1.0', 'end').strip()
        values['contract_declaration'] = self.declaration.get('1.0', 'end').strip()
        values['machine_categories'] = self.categories.get('1.0', 'end').strip()
        values['return_protocol_header_text'] = self.return_protocol_header_text.get('1.0', 'end').strip()
        values['return_protocol_footer'] = self.return_protocol_footer.get('1.0', 'end').strip()
        self.app.db.save_settings(values)
        save_theme(self.theme.get())
        messagebox.showinfo('Hotovo', 'Nastavení uloženo. Motiv i PIN se projeví po restartu.')
