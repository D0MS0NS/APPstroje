from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import customtkinter as ctk


def row_value(row, key, default=""):
    try:
        value = row[key]
        return default if value is None else value
    except Exception:
        return default


def parse_date_input(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError("Datum zadej ve formátu dd.mm.rrrr")


def format_date(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "—"
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).strftime("%d.%m.%Y")
        except ValueError:
            continue
    return value


def today_display() -> str:
    return date.today().strftime("%d.%m.%Y")


def display_period(date_from: str, date_to: str) -> str:
    return f"{format_date(date_from)} → {format_date(date_to)}"


def format_currency(value) -> str:
    try:
        amount = float(value or 0)
    except Exception:
        amount = 0
    if amount.is_integer():
        return f"{int(amount):,} Kč".replace(",", " ")
    return f"{amount:,.2f} Kč".replace(",", " ").replace(".", ",")


def file_label(path: str) -> str:
    if not path:
        return "—"
    return Path(path).name



def center_window(win, width: int | None = None, height: int | None = None):
    try:
        win.update_idletasks()
        if width is None or height is None:
            geo = win.geometry().split('+')[0]
            if 'x' in geo:
                w, h = geo.split('x', 1)
                width = width or int(w)
                height = height or int(h)
            else:
                width = width or win.winfo_width() or 800
                height = height or win.winfo_height() or 600
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2 - 20)
        win.geometry(f"{width}x{height}+{x}+{y}")
    except Exception:
        pass




class ModalFormWindow(ctk.CTkToplevel):
    def __init__(self, master, title: str, width: int, height: int, primary_text: str, primary_command, *, subtitle: str | None = None):
        super().__init__(master)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.grab_set()
        center_window(self, width, height)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.header = ctk.CTkFrame(self, corner_radius=0, fg_color=("#f8fafc", "#0f172a"))
        self.header.grid(row=0, column=0, sticky='ew')
        self.header.grid_columnconfigure(0, weight=1)
        title_wrap = ctk.CTkFrame(self.header, fg_color='transparent')
        title_wrap.grid(row=0, column=0, sticky='w', padx=18, pady=14)
        ctk.CTkLabel(title_wrap, text=title, font=ctk.CTkFont(size=22, weight='bold')).pack(anchor='w')
        if subtitle:
            ctk.CTkLabel(title_wrap, text=subtitle, text_color=("#64748b", "#94a3b8")).pack(anchor='w', pady=(3, 0))

        actions = ctk.CTkFrame(self.header, fg_color='transparent')
        actions.grid(row=0, column=1, sticky='e', padx=18, pady=14)
        self.primary_button = ctk.CTkButton(actions, text=primary_text, height=38, corner_radius=12, command=primary_command)
        self.primary_button.pack(side='left')
        self.cancel_button = ctk.CTkButton(actions, text='Zavřít', height=38, width=96, corner_radius=12, fg_color=("#e5e7eb", "#1f2937"), hover_color=("#d1d5db", "#374151"), text_color=("#111827", "#f9fafb"), command=self.destroy)
        self.cancel_button.pack(side='left', padx=(10, 0))

        self.body = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color='transparent')
        self.body.grid(row=1, column=0, sticky='nsew', padx=18, pady=(18, 18))
        self.body.grid_columnconfigure(0, weight=1)

class DatePickerDialog:
    def __init__(self, master, initial_value: str = ''):
        import customtkinter as ctk
        import tkinter as tk
        import calendar as pycalendar
        from datetime import datetime, date
        self.ctk = ctk
        self.tk = tk
        self.pycalendar = pycalendar
        self.value = None
        try:
            initial = datetime.strptime(parse_date_input(initial_value) if initial_value else date.today().strftime('%Y-%m-%d'), '%Y-%m-%d').date()
        except Exception:
            initial = date.today()
        self.current = initial.replace(day=1)
        self.top = ctk.CTkToplevel(master)
        self.top.title('Výběr data')
        self.top.resizable(False, False)
        self.top.grab_set()
        self.header = ctk.CTkFrame(self.top, fg_color='transparent')
        self.header.pack(fill='x', padx=12, pady=(12, 6))
        ctk.CTkButton(self.header, text='◀', width=36, command=self.prev_month).pack(side='left')
        self.title_lbl = ctk.CTkLabel(self.header, text='')
        self.title_lbl.pack(side='left', expand=True)
        ctk.CTkButton(self.header, text='▶', width=36, command=self.next_month).pack(side='right')
        self.body = ctk.CTkFrame(self.top)
        self.body.pack(padx=12, pady=8)
        btns = ctk.CTkFrame(self.top, fg_color='transparent')
        btns.pack(fill='x', padx=12, pady=(0, 12))
        ctk.CTkButton(btns, text='Dnes', command=self.pick_today).pack(side='left')
        ctk.CTkButton(btns, text='Zrušit', command=self.top.destroy).pack(side='right')
        self._draw()
        center_window(self.top, 320, 340)

    def _draw(self):
        for w in self.body.winfo_children():
            w.destroy()
        self.title_lbl.configure(text=self.current.strftime('%B %Y'))
        weekdays = ['Po','Út','St','Čt','Pá','So','Ne']
        for i, d in enumerate(weekdays):
            self.ctk.CTkLabel(self.body, text=d, width=40).grid(row=0, column=i, padx=2, pady=2)
        cal = self.pycalendar.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(self.current.year, self.current.month)
        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    self.ctk.CTkLabel(self.body, text='', width=40).grid(row=r, column=c, padx=2, pady=2)
                else:
                    self.ctk.CTkButton(self.body, text=str(day), width=40, height=32,
                                       command=lambda dd=day: self.pick(dd)).grid(row=r, column=c, padx=2, pady=2)

    def prev_month(self):
        from datetime import date
        y = self.current.year
        m = self.current.month - 1
        if m == 0:
            m = 12; y -= 1
        self.current = self.current.replace(year=y, month=m, day=1)
        self._draw()

    def next_month(self):
        y = self.current.year
        m = self.current.month + 1
        if m == 13:
            m = 1; y += 1
        self.current = self.current.replace(year=y, month=m, day=1)
        self._draw()

    def pick(self, day: int):
        self.value = f"{day:02d}.{self.current.month:02d}.{self.current.year:04d}"
        self.top.destroy()

    def pick_today(self):
        from datetime import date
        d = date.today()
        self.value = d.strftime('%d.%m.%Y')
        self.top.destroy()


def pick_date_for_entry(master, entry_widget):
    dlg = DatePickerDialog(master, entry_widget.get().strip())
    master.wait_window(dlg.top)
    if dlg.value:
        entry_widget.delete(0, 'end')
        entry_widget.insert(0, dlg.value)



def style_treeview(tree, style_name: str = 'AppTreeview'):
    import tkinter as tk
    from tkinter import ttk
    style = ttk.Style()
    try:
        style.theme_use('default')
    except Exception:
        pass
    style.configure(f'{style_name}.Treeview',
                    rowheight=38,
                    font=('Segoe UI', 10),
                    background='#ffffff',
                    fieldbackground='#ffffff',
                    foreground='#0f172a',
                    borderwidth=0,
                    relief='flat')
    style.map(f'{style_name}.Treeview',
              background=[('selected', '#dbeafe')],
              foreground=[('selected', '#0f172a')])
    style.configure(f'{style_name}.Treeview.Heading',
                    font=('Segoe UI Semibold', 10),
                    background='#eef2f7',
                    foreground='#0f172a',
                    borderwidth=0,
                    relief='flat',
                    padding=(12, 11))
    tree.configure(style=f'{style_name}.Treeview')
