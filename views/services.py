from __future__ import annotations
from datetime import date
import customtkinter as ctk
from tkinter import ttk, messagebox
from utils import row_value, format_date, parse_date_input, format_currency, center_window, pick_date_for_entry, style_treeview, ModalFormWindow

class ServicesView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master); self.app=app; self.configure(fg_color='transparent'); self.grid_rowconfigure(3, weight=1); self.grid_columnconfigure(0, weight=1)
        top=ctk.CTkFrame(self, corner_radius=24, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047")); top.grid(row=0,column=0,sticky='ew',padx=22,pady=(22,12)); top.grid_columnconfigure(1, weight=1)
        left=ctk.CTkFrame(top, fg_color='transparent'); left.grid(row=0,column=0,sticky='w',padx=18,pady=16)
        ctk.CTkLabel(left,text='Servis',font=ctk.CTkFont(size=28,weight='bold')).pack(anchor='w')
        ctk.CTkLabel(left,text='Otevřené servisní zásahy, termíny a náklady přehledně na jednom místě', text_color=("#64748b", "#94a3b8")).pack(anchor='w', pady=(2,0))
        actions=ctk.CTkFrame(top, fg_color='transparent'); actions.grid(row=0,column=2,sticky='e', padx=18, pady=16)
        ctk.CTkButton(actions,text='Nový servisní záznam', height=40, corner_radius=14, command=self.open_add).pack(side='left')
        ctk.CTkButton(actions,text='Upravit servis', height=40, corner_radius=14, command=self.open_edit).pack(side='left', padx=8)
        ctk.CTkButton(actions,text='Označit servis dokončen', height=40, corner_radius=14, command=self.finish_service).pack(side='left', padx=8)
        summary=ctk.CTkFrame(self, corner_radius=22, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047")); summary.grid(row=1,column=0,sticky='ew',padx=22,pady=(0,12))
        self.total_lbl=ctk.CTkLabel(summary,text='Otevřený servis: 0', font=ctk.CTkFont(size=16, weight='bold')); self.total_lbl.pack(side='left', padx=16, pady=14)
        self.cost_lbl=ctk.CTkLabel(summary,text='Náklady otevřeného servisu: 0 Kč', text_color=("#64748b", "#94a3b8")); self.cost_lbl.pack(side='left', padx=10, pady=14)
        self.selection_lbl=ctk.CTkLabel(summary,text='Vybraný servis: žádný', text_color=("#64748b", "#94a3b8")); self.selection_lbl.pack(side='right', padx=16, pady=14)
        toolbar=ctk.CTkFrame(self, corner_radius=22, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047")); toolbar.grid(row=2,column=0,sticky='ew',padx=22,pady=(0,12)); toolbar.grid_columnconfigure(0, weight=1)
        self.search=ctk.CTkEntry(toolbar, placeholder_text='Hledat stroj / datum / typ servisu / MH', height=40, corner_radius=14); self.search.grid(row=0,column=0,sticky='ew', padx=14, pady=14); self.search.bind('<KeyRelease>', lambda e:self.refresh())
        ctk.CTkButton(toolbar, text='Reset', width=84, height=40, corner_radius=14, command=self.reset_filters).grid(row=0, column=1, padx=(0,14), pady=14)
        frame=ctk.CTkFrame(self, corner_radius=22, fg_color=("#ffffff", "#111827"), border_width=1, border_color=("#dbe3ef", "#223047")); frame.grid(row=3,column=0,sticky='nsew',padx=22,pady=(0,22)); frame.grid_rowconfigure(1,weight=1); frame.grid_columnconfigure(0,weight=1)
        head=ctk.CTkFrame(frame, fg_color='transparent'); head.grid(row=0,column=0,columnspan=2,sticky='ew',padx=14,pady=(14,8))
        ctk.CTkLabel(head, text='Aktivní servisní záznamy', font=ctk.CTkFont(size=18, weight='bold')).pack(side='left')
        ctk.CTkLabel(head, text='Dvojklik otevře servisní protokol', text_color=("#64748b", "#94a3b8")).pack(side='left', padx=(10,0))
        cols=('id','machine','date','type','mh','cost','provider','nextmh','next')
        self.tree=ttk.Treeview(frame, columns=cols, show='headings'); style_treeview(self.tree, 'Services')
        for col,title,width in [('id','ID',50),('machine','Stroj',210),('date','Datum',100),('type','Typ',150),('mh','MH',90),('cost','Cena',90),('provider','Dodavatel',150),('nextmh','Další MH',90),('next','Další servis',110)]:
            self.tree.heading(col,text=title); self.tree.column(col,width=width,anchor='w')
        self.tree.grid(row=1,column=0,sticky='nsew', padx=(14,0), pady=(0,0)); ttk.Scrollbar(frame,orient='vertical',command=self.tree.yview).grid(row=1,column=1,sticky='ns', padx=(0,14), pady=(0,0))
        self.tree.bind('<Double-1>', lambda e:self.open_protocol())
        self.tree.bind('<<TreeviewSelect>>', lambda e:self.update_selection_label())
        actions=ctk.CTkFrame(frame, fg_color='transparent'); actions.grid(row=2,column=0,columnspan=2,sticky='ew', padx=14, pady=14)
        self.protocol_btn=ctk.CTkButton(actions, text='Detail servisu', height=38, corner_radius=14, command=self.open_protocol, state='disabled')
        self.protocol_btn.pack(side='right')
    def reset_filters(self):
        self.search.delete(0, 'end')
        self.refresh()

    def update_selection_label(self):
        sel=self.tree.selection()
        if sel:
            vals=self.tree.item(sel[0], 'values')
            self.selection_lbl.configure(text=f'Vybraný servis: {vals[1]}')
            self.protocol_btn.configure(state='normal')
        else:
            self.selection_lbl.configure(text='Vybraný servis: žádný')
            self.protocol_btn.configure(state='disabled')

    def refresh(self):
        q=self.search.get().strip().lower()
        for item in self.tree.get_children(): self.tree.delete(item)
        rows=self.app.db.fetchall("SELECT s.*, m.name AS machine_name, m.inventory_number FROM service_records s LEFT JOIN machines m ON m.id=s.machine_id WHERE COALESCE(s.status, 'otevřený') <> 'dokončeno' ORDER BY s.service_date DESC, s.id DESC")
        total_cost = 0
        shown = 0
        for r in rows:
            hay=f"{row_value(r,'machine_name')} {format_date(row_value(r,'service_date'))} {row_value(r,'service_type')} {row_value(r,'provider')} {row_value(r,'service_motohours')} {row_value(r,'next_service_motohours')}".lower()
            if q and q not in hay: continue
            self.tree.insert('', 'end', iid=str(r['id']), values=(r['id'], f"{row_value(r,'machine_name')} ({row_value(r,'inventory_number')})", format_date(row_value(r,'service_date')), row_value(r,'service_type'), row_value(r,'service_motohours') or '—', format_currency(row_value(r,'cost',0)), row_value(r,'provider'), row_value(r,'next_service_motohours') or '—', format_date(row_value(r,'next_service_date'))))
            shown += 1
            total_cost += float(row_value(r,'cost',0) or 0)
        self.total_lbl.configure(text=f'Otevřený servis: {shown}')
        self.cost_lbl.configure(text=f'Náklady otevřeného servisu: {format_currency(total_cost)}')
        self.update_selection_label()
    def open_add(self): ServiceEditor(self,self.app,self.refresh)
    def open_edit(self):
        selected=self.tree.selection()
        if not selected: return
        record=self.app.db.fetchone('SELECT * FROM service_records WHERE id=?',(int(selected[0]),))
        if not record: return
        ServiceEditor(self,self.app,self.refresh,record=record)
    def finish_service(self):
        selected=self.tree.selection();
        if not selected: return
        record=self.app.db.fetchone('SELECT * FROM service_records WHERE id=?',(int(selected[0]),))
        if not record: return
        self.app.db.finish_service(record['machine_id'], record['id']); self.app.refresh_all(); self.refresh(); messagebox.showinfo('Servis','Servis byl označen jako dokončený a stroj byl přepnut do stavu volný.')
    def open_protocol(self):
        selected=self.tree.selection();
        if not selected: return
        service=self.app.db.fetchone('SELECT * FROM service_records WHERE id=?',(int(selected[0]),))
        if not service: return
        machine=self.app.db.fetchone('SELECT * FROM machines WHERE id=?',(service['machine_id'],))
        path=self.app.pdf.create_service_protocol_pdf(machine, service); self.app.pdf.open_any_pdf(path)

class ServiceEditor(ModalFormWindow):
    def __init__(self, master, app, on_saved, record=None):
        self.record=record
        is_edit = record is not None
        super().__init__(master, 'Upravit servisní záznam' if is_edit else 'Nový servisní záznam', 920, 780, 'Uložit změny' if is_edit else 'Uložit servis', self.save, subtitle='Zapiš servis, motohodiny a případný další termín')
        self.app=app; self.on_saved=on_saved
        machines=self.app.db.fetchall("SELECT id, name, inventory_number FROM machines ORDER BY name")
        self.machine_map={f"{row_value(m,'name')} ({row_value(m,'inventory_number')})":m['id'] for m in machines}
        form=ctk.CTkFrame(self.body, corner_radius=18); form.grid(row=0,column=0,sticky='ew'); form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(form,text='Stroj').grid(row=0,column=0,padx=16,pady=10,sticky='w')
        self.machine_cb=ctk.CTkComboBox(form, values=list(self.machine_map.keys()), width=420); self.machine_cb.grid(row=0,column=1,padx=16,pady=10,sticky='ew')
        selected_machine_text = list(self.machine_map.keys())[0] if self.machine_map else ''
        if self.record:
            for text_val, mid in self.machine_map.items():
                if mid == self.record['machine_id']:
                    selected_machine_text = text_val
                    break
        if selected_machine_text: self.machine_cb.set(selected_machine_text)
        self.entries={}
        defaults={'service_date':format_date(date.today().strftime('%Y-%m-%d')),'service_type':'Pravidelný servis','service_motohours':'','cost':'0','provider':'','next_service_motohours':'','next_service_date':''}
        if self.record:
            defaults.update({'service_date': format_date(row_value(self.record,'service_date')), 'service_type': row_value(self.record,'service_type') or 'Pravidelný servis', 'service_motohours': str(row_value(self.record,'service_motohours') or ''), 'cost': str(row_value(self.record,'cost') or 0), 'provider': row_value(self.record,'provider') or '', 'next_service_motohours': str(row_value(self.record,'next_service_motohours') or ''), 'next_service_date': format_date(row_value(self.record,'next_service_date')) if row_value(self.record,'next_service_date') else ''})
        for i,(label,key) in enumerate([('Datum servisu','service_date'),('Typ servisu','service_type'),('Motohodiny při servisu','service_motohours'),('Cena','cost'),('Dodavatel servisu','provider'),('Další servis při MH','next_service_motohours'),('Další servis','next_service_date')], start=1):
            ctk.CTkLabel(form,text=label).grid(row=i,column=0,padx=16,pady=10,sticky='w')
            ent=ctk.CTkEntry(form,width=420,height=38); ent.grid(row=i,column=1,padx=16,pady=10,sticky='ew'); ent.insert(0,defaults[key]); self.entries[key]=ent
            if key in ('service_date','next_service_date'):
                ctk.CTkButton(form, text='📅', width=42, command=lambda e=ent: pick_date_for_entry(self, e)).grid(row=i, column=2, padx=6, pady=10)
        ctk.CTkLabel(form,text='Poznámka').grid(row=8,column=0,padx=16,pady=10,sticky='nw')
        self.notes=ctk.CTkTextbox(form,width=420,height=130); self.notes.grid(row=8,column=1,padx=16,pady=(10,18),sticky='ew')
        if self.record and row_value(self.record,'notes'):
            self.notes.insert('1.0', row_value(self.record,'notes'))
        
    def save(self):
        try:
            cost=float(self.entries['cost'].get().strip().replace(',', '.') or 0)
            service_date=parse_date_input(self.entries['service_date'].get().strip())
            next_service=parse_date_input(self.entries['next_service_date'].get().strip()) if self.entries['next_service_date'].get().strip() else ''
            service_mh=float(self.entries['service_motohours'].get().strip().replace(',', '.') or 0)
            next_service_mh=float(self.entries['next_service_motohours'].get().strip().replace(',', '.') or 0)
        except ValueError as exc:
            messagebox.showerror('Chyba', str(exc)); return
        if not self.machine_map: return
        machine_id=self.machine_map[self.machine_cb.get()]
        if self.record:
            self.app.db.update_service_record(self.record['id'], machine_id, service_date, self.entries['service_type'].get().strip(), cost, self.entries['provider'].get().strip(), self.notes.get('1.0','end').strip(), next_service, service_mh, next_service_mh)
        else:
            self.app.db.create_service_record(machine_id, service_date, self.entries['service_type'].get().strip(), cost, self.entries['provider'].get().strip(), self.notes.get('1.0','end').strip(), next_service, service_mh, next_service_mh)
        self.on_saved(); self.app.refresh_all(); self.destroy()
