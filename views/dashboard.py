from __future__ import annotations
from datetime import date, datetime, timedelta
import customtkinter as ctk
from utils import row_value, format_date, display_period, format_currency

CZ_MONTHS = ['leden','únor','březen','duben','květen','červen','červenec','srpen','září','říjen','listopad','prosinec']


def _safe_float(v):
    try:
        return float(v or 0)
    except Exception:
        return 0.0


class KpiCard(ctk.CTkFrame):
    def __init__(self, master, title: str, subtitle: str, accent: str):
        super().__init__(master, corner_radius=20, border_width=1, border_color=("#e5e7eb", "#273244"))
        self.configure(fg_color=("#ffffff", "#0f172a"))
        top = ctk.CTkFrame(self, fg_color='transparent')
        top.pack(fill='x', padx=16, pady=(14, 6))
        dot = ctk.CTkFrame(top, width=12, height=12, corner_radius=6, fg_color=accent)
        dot.pack(side='left', padx=(0, 8))
        ctk.CTkLabel(top, text=title, font=ctk.CTkFont(size=14, weight='bold')).pack(side='left')
        self.value = ctk.CTkLabel(self, text='0', font=ctk.CTkFont(size=32, weight='bold'))
        self.value.pack(anchor='w', padx=16)
        self.subtitle = ctk.CTkLabel(self, text=subtitle, text_color=("#6b7280", "#94a3b8"))
        self.subtitle.pack(anchor='w', padx=16, pady=(2, 14))

    def set_value(self, value, subtitle: str | None = None):
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        self.value.configure(text=str(value))
        if subtitle is not None:
            self.subtitle.configure(text=subtitle)


class Panel(ctk.CTkFrame):
    def __init__(self, master, title: str, subtitle: str = ''):
        super().__init__(master, corner_radius=20, border_width=1, border_color=("#e5e7eb", "#273244"))
        self.configure(fg_color=("#ffffff", "#0f172a"))
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=16, pady=(14, 8))
        left = ctk.CTkFrame(header, fg_color='transparent')
        left.pack(side='left', fill='x', expand=True)
        ctk.CTkLabel(left, text=title, font=ctk.CTkFont(size=18, weight='bold')).pack(anchor='w')
        if subtitle:
            ctk.CTkLabel(left, text=subtitle, text_color=("#6b7280", "#94a3b8")).pack(anchor='w')
        self.body = ctk.CTkFrame(self, fg_color='transparent')
        self.body.pack(fill='both', expand=True, padx=16, pady=(0, 16))


class TrendChart(Panel):
    def __init__(self, master):
        super().__init__(master, 'Vývoj za posledních 6 měsíců', 'Smlouvy a obrat v čase')
        controls = ctk.CTkFrame(self.body, fg_color='transparent')
        controls.pack(fill='x', pady=(0, 10))
        self.mode = ctk.StringVar(value='contracts')
        self.btn_contracts = ctk.CTkSegmentedButton(controls, values=['Počet smluv', 'Obrat'], command=self._switch)
        self.btn_contracts.pack(side='left')
        self.btn_contracts.set('Počet smluv')
        self.chart_area = ctk.CTkFrame(self.body, fg_color='transparent')
        self.chart_area.pack(fill='both', expand=True)
        self.rows = []

    def _switch(self, value: str):
        self.mode.set('contracts' if value == 'Počet smluv' else 'revenue')
        self.render()

    def set_data(self, rows):
        self.rows = rows
        self.render()

    def render(self):
        for w in self.chart_area.winfo_children():
            w.destroy()
        rows = self.rows or []
        if not rows:
            ctk.CTkLabel(self.chart_area, text='Zatím nejsou data pro graf.', text_color=("#6b7280", "#94a3b8")).pack(anchor='w')
            return
        metric = 'cnt' if self.mode.get() == 'contracts' else 'revenue'
        values = [_safe_float(r.get(metric)) for r in rows]
        max_value = max(values) if max(values) > 0 else 1
        wrap = ctk.CTkFrame(self.chart_area, fg_color='transparent')
        wrap.pack(fill='both', expand=True)
        for idx, row in enumerate(rows):
            col = ctk.CTkFrame(wrap, fg_color='transparent')
            col.grid(row=0, column=idx, sticky='nsew', padx=6)
            wrap.grid_columnconfigure(idx, weight=1)
            ctk.CTkLabel(col, text=row['month_label'], text_color=("#6b7280", "#94a3b8")).pack(side='bottom', pady=(6, 0))
            val = _safe_float(row.get(metric))
            label = f"{int(val)}" if metric == 'cnt' else f"{int(val):,} Kč".replace(',', ' ')
            ctk.CTkLabel(col, text=label, font=ctk.CTkFont(weight='bold')).pack(side='bottom', pady=(0, 4))
            holder = ctk.CTkFrame(col, width=52, height=170, corner_radius=16, fg_color=("#eef2ff", "#111827"))
            holder.pack(side='bottom', pady=(0, 6), fill='y')
            holder.pack_propagate(False)
            ctk.CTkFrame(holder, fg_color='transparent').pack(side='top', fill='both', expand=True)
            height = max(14, int(140 * val / max_value))
            color = '#2563eb' if metric == 'cnt' else '#10b981'
            ctk.CTkFrame(holder, width=52, height=height, corner_radius=16, fg_color=color).pack(side='bottom', fill='x')


class ActionList(Panel):
    def __init__(self, master, title: str, subtitle: str = ''):
        super().__init__(master, title, subtitle)
        self.scroll = ctk.CTkScrollableFrame(self.body, fg_color='transparent')
        self.scroll.pack(fill='both', expand=True)

    def clear(self):
        for w in self.scroll.winfo_children():
            w.destroy()


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_rowconfigure(4, weight=1)

        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(row=0, column=0, columnspan=3, sticky='ew', padx=22, pady=(18, 10))
        header.grid_columnconfigure(1, weight=1)
        left = ctk.CTkFrame(header, fg_color='transparent')
        left.grid(row=0, column=0, sticky='w')
        ctk.CTkLabel(left, text='Přehled', font=ctk.CTkFont(size=28, weight='bold')).pack(anchor='w')
        ctk.CTkLabel(left, text='Co je důležité, co je potřeba řešit a rychlé akce na jednom místě', text_color=("#6b7280", "#94a3b8")).pack(anchor='w')
        actions = ctk.CTkFrame(header, fg_color='transparent')
        actions.grid(row=0, column=2, sticky='e')
        for text, cmd in [
            ('Nová smlouva', lambda: self.app.open_new_contract()),
            ('Nová rezervace', lambda: self.app.open_new_reservation()),
            ('Přidat zákazníka', lambda: self.app.open_new_customer()),
            ('Přidat stroj', lambda: self.app.open_new_machine()),
        ]:
            ctk.CTkButton(actions, text=text, height=38, corner_radius=14, command=cmd).pack(side='left', padx=(0, 8))

        self.kpi_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.kpi_frame.grid(row=1, column=0, columnspan=3, sticky='ew', padx=22)
        for i in range(7):
            self.kpi_frame.grid_columnconfigure(i, weight=1)
        kpis = [
            ('Volné stroje', 'Okamžitě k dispozici', 'machines_free', '#22c55e'),
            ('Půjčené stroje', 'Aktuálně mimo sklad', 'machines_rented', '#f59e0b'),
            ('Rezervace', 'Budoucí blokace termínů', 'reservations_active', '#14b8a6'),
            ('Dnes vrátit', 'Smlouvy končící dnes', 'returns_today', '#06b6d4'),
            ('Po termínu', 'Vyžaduje okamžitou pozornost', 'contracts_overdue', '#ef4444'),
            ('V servisu', 'Stroje čekající na údržbu', 'machines_service', '#64748b'),
            ('Obrat za měsíc', 'Jen pronájmy a doplatky', 'month_revenue', '#8b5cf6'),
        ]
        self.cards = {}
        for idx, (title, subtitle, key, accent) in enumerate(kpis):
            card = KpiCard(self.kpi_frame, title, subtitle, accent)
            card.grid(row=0, column=idx, sticky='nsew', padx=7, pady=(0, 10))
            self.cards[key] = card

        self.attention = ActionList(self, 'Co vyžaduje pozornost', 'Nejdůležitější položky k řešení')
        self.attention.grid(row=2, column=0, sticky='nsew', padx=(22, 10), pady=(0, 12))
        self.chart = TrendChart(self)
        self.chart.grid(row=2, column=1, columnspan=2, sticky='nsew', padx=(10, 22), pady=(0, 12))

        self.upcoming = ActionList(self, 'Nejbližší vratky a rezervace', 'Klikni rovnou do detailu nebo PDF')
        self.upcoming.grid(row=3, column=0, sticky='nsew', padx=(22, 10), pady=(0, 12))
        self.today = ActionList(self, 'Dnes a zítra', 'Rychlý operativní přehled')
        self.today.grid(row=3, column=1, sticky='nsew', padx=10, pady=(0, 12))
        self.recent = ActionList(self, 'Poslední smlouvy', 'Nejnovější vytvořené záznamy')
        self.recent.grid(row=3, column=2, sticky='nsew', padx=(10, 22), pady=(0, 12))

        self.topmachines = Panel(self, 'Nejpůjčovanější stroje', 'Co se půjčuje nejčastěji')
        self.topmachines.grid(row=4, column=0, columnspan=3, sticky='nsew', padx=22, pady=(0, 22))
        self.topmachines.body.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

    def refresh(self):
        stats = self.app.db.get_dashboard_stats()
        self.cards['machines_free'].set_value(stats.get('machines_free', 0), 'Okamžitě k dispozici')
        self.cards['machines_rented'].set_value(stats.get('machines_rented', 0), 'Aktuálně mimo sklad')
        self.cards['reservations_active'].set_value(stats.get('reservations_active', 0), 'Budoucí blokace termínů')
        self.cards['returns_today'].set_value(stats.get('returns_today', 0), 'Smlouvy končící dnes')
        self.cards['contracts_overdue'].set_value(stats.get('contracts_overdue', 0), 'Vyžaduje okamžitou pozornost')
        self.cards['machines_service'].set_value(stats.get('machines_service', 0), 'Stroje čekající na údržbu')
        revenue = int(_safe_float(stats.get('month_revenue', 0)))
        self.cards['month_revenue'].set_value(f"{revenue:,} Kč".replace(',', ' '), 'Jen pronájmy a doplatky')

        self.chart.set_data(self._build_trend_rows())
        self._render_attention(stats)
        self._render_upcoming()
        self._render_today()
        self._render_recent()
        self._render_topmachines()

    def _build_trend_rows(self):
        counts = self.app.db.get_monthly_contract_counts(6)
        rows = []
        contracts = self.app.db.fetchall("SELECT created_at, rental_from, total_price, return_extra_charge FROM contracts")
        revenue_map = {}
        for r in contracts:
            ym = str(row_value(r, 'created_at') or row_value(r, 'rental_from') or '')[:7]
            revenue_map[ym] = revenue_map.get(ym, 0) + _safe_float(row_value(r, 'total_price', 0)) + _safe_float(row_value(r, 'return_extra_charge', 0))
        for r in counts:
            label = row_value(r, 'month_label')
            month_num, year = label.split('/')
            ym = f"{year}-{month_num}"
            rows.append({'month_label': label, 'cnt': row_value(r, 'cnt', 0), 'revenue': revenue_map.get(ym, 0)})
        return rows

    def _add_list_item(self, parent, title, subtitle='', badge=None, badge_color='#2563eb', buttons=None):
        item = ctk.CTkFrame(parent, corner_radius=16, fg_color=("#f8fafc", "#111827"), border_width=1, border_color=("#e5e7eb", "#1f2937"))
        item.pack(fill='x', pady=6)
        row = ctk.CTkFrame(item, fg_color='transparent')
        row.pack(fill='x', padx=12, pady=(10, 6))
        text = ctk.CTkFrame(row, fg_color='transparent')
        text.pack(side='left', fill='x', expand=True)
        ctk.CTkLabel(text, text=title, font=ctk.CTkFont(weight='bold')).pack(anchor='w')
        if subtitle:
            ctk.CTkLabel(text, text=subtitle, text_color=("#6b7280", "#94a3b8")).pack(anchor='w')
        if badge:
            ctk.CTkLabel(item, text=badge, fg_color=badge_color, text_color='white', corner_radius=999, padx=10, pady=3).pack(anchor='ne', padx=12, pady=(0, 6))
        if buttons:
            actions = ctk.CTkFrame(item, fg_color='transparent')
            actions.pack(anchor='w', padx=12, pady=(0, 10))
            for text, cmd in buttons:
                ctk.CTkButton(actions, text=text, width=94, height=32, corner_radius=12, command=cmd).pack(side='left', padx=(0, 8))

    def _render_attention(self, stats):
        self.attention.clear()
        overdue = int(_safe_float(stats.get('contracts_overdue', 0)))
        if overdue:
            self._add_list_item(self.attention.scroll, f'Smlouvy po termínu: {overdue}', 'Zkontroluj a případně kontaktuj zákazníka.', 'Priorita', '#dc2626', [('Smlouvy', lambda: self.app.show_view('contracts'))])
        returns_today = int(_safe_float(stats.get('returns_today', 0)))
        if returns_today:
            self._add_list_item(self.attention.scroll, f'Verátit dnes: {returns_today}', 'Dnešní plánované ukončení smluv.', 'Dnes', '#0ea5e9', [('Smlouvy', lambda: self.app.show_view('contracts'))])
        reservations = int(_safe_float(stats.get('reservations_active', 0)))
        if reservations:
            self._add_list_item(self.attention.scroll, f'Budoucí rezervace: {reservations}', 'Zkontroluj připravenost strojů na následující dny.', 'Rezervace', '#14b8a6', [('Kalendář', lambda: self.app.show_view('contracts'))])
        unpaid = int(_safe_float(stats.get('unpaid', 0)))
        if unpaid:
            self._add_list_item(self.attention.scroll, f'Nezaplacené smlouvy: {unpaid}', 'V aktivních smlouvách chybí platba nebo kauce.', 'Finance', '#f59e0b', [('Smlouvy', lambda: self.app.show_view('contracts'))])
        service_due = int(_safe_float(stats.get('service_due', 0)))
        service_due_mh = int(_safe_float(stats.get('service_due_by_motohours', 0)))
        if service_due:
            due_rows = self.app.db.get_service_due_machines(6)
            if due_rows:
                details = []
                for m in due_rows[:3]:
                    reason = 'MH limit' if _safe_float(row_value(m, 'service_due_motohours', 0)) and _safe_float(row_value(m, 'motohours', 0)) >= _safe_float(row_value(m, 'service_due_motohours', 0)) else f"termín {format_date(row_value(m, 'next_service_date'))}"
                    details.append(f"{row_value(m, 'name')} ({row_value(m, 'inventory_number') or 'bez čísla'}) – {reason}")
                subtitle = ' • '.join(details)
                if service_due > len(details):
                    subtitle += f" • a další {service_due - len(details)}"
            else:
                subtitle = 'Naplánuj prohlídku nebo odstavení stroje.' if not service_due_mh else f'{service_due_mh} strojů je už na limitu motohodin.'
            self._add_list_item(self.attention.scroll, f'Servis k řešení: {service_due}', subtitle, 'Servis', '#6366f1', [('Servis', lambda: self.app.show_view('services'))])
        if not any([overdue, returns_today, reservations, unpaid, service_due]):
            self._add_list_item(self.attention.scroll, 'Vypadá to dobře', 'Aktuálně není nic kritického, co by vyžadovalo okamžitou akci.', 'OK', '#22c55e')

    def _render_upcoming(self):
        self.upcoming.clear()
        merged = [('Vratka', r) for r in self.app.db.get_upcoming_returns(5)] + [('Rezervace', r) for r in self.app.db.get_upcoming_reservations(5)]
        merged = sorted(merged, key=lambda x: row_value(x[1], 'rental_to' if x[0] == 'Vratka' else 'reserved_from'))[:8]
        if not merged:
            self._add_list_item(self.upcoming.scroll, 'Žádné blížící se akce', 'V nejbližších dnech nejsou plánované vratky ani rezervace.', 'Klid', '#22c55e')
            return
        for typ, row in merged:
            date_text = format_date(row_value(row, 'rental_to') if typ == 'Vratka' else row_value(row, 'reserved_from'))
            ref = row_value(row, 'contract_number') if typ == 'Vratka' else row_value(row, 'reservation_number')
            badge_color = '#8b5cf6' if typ == 'Vratka' else '#14b8a6'
            buttons = [('Detail', lambda cid=row_value(row, 'id'), t=typ: self.app.open_contract_detail(cid) if t == 'Vratka' else self.app.show_view('contracts'))]
            if typ == 'Vratka':
                buttons.append(('PDF', lambda num=row_value(row, 'contract_number'): self.app.open_contract_pdf(num)))
            self._add_list_item(self.upcoming.scroll, f'{typ} · {date_text} · {ref}', f"{row_value(row, 'customer_name')} · {row_value(row, 'machines')}", typ, badge_color, buttons)

    def _render_today(self):
        self.today.clear()
        upcoming_returns = self.app.db.get_upcoming_returns(20)
        upcoming_res = self.app.db.get_upcoming_reservations(20)
        today = date.today().strftime('%Y-%m-%d')
        tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        sections = [
            ('Dnes – vratky', [r for r in upcoming_returns if row_value(r, 'rental_to') == today], '#0ea5e9'),
            ('Dnes – rezervace', [r for r in upcoming_res if row_value(r, 'reserved_from') == today], '#14b8a6'),
            ('Zítra – vratky', [r for r in upcoming_returns if row_value(r, 'rental_to') == tomorrow], '#38bdf8'),
            ('Zítra – rezervace', [r for r in upcoming_res if row_value(r, 'reserved_from') == tomorrow], '#2dd4bf'),
        ]
        any_item = False
        for title, items, color in sections:
            if not items:
                continue
            any_item = True
            ctk.CTkLabel(self.today.scroll, text=title, font=ctk.CTkFont(weight='bold')).pack(anchor='w', pady=(4, 6))
            for row in items[:3]:
                ref = row_value(row, 'contract_number') or row_value(row, 'reservation_number')
                self._add_list_item(self.today.scroll, ref, f"{row_value(row, 'customer_name')} · {row_value(row, 'machines')}", None, color, [('Přejít', lambda: self.app.show_view('contracts'))])
        if not any_item:
            self._add_list_item(self.today.scroll, 'Dnes a zítra bez událostí', 'Žádné vratky ani rezervace v nejbližších dvou dnech.', 'Volno', '#22c55e')

    def _render_recent(self):
        self.recent.clear()
        rows = self.app.db.get_recent_contracts(6)
        if not rows:
            self._add_list_item(self.recent.scroll, 'Zatím nejsou vytvořené smlouvy', 'Jakmile vytvoříš první smlouvu, objeví se tady.', 'Info', '#64748b')
            return
        for row in rows:
            self._add_list_item(
                self.recent.scroll,
                f"{row_value(row, 'contract_number')} · {row_value(row, 'customer_name')}",
                f"{display_period(row_value(row, 'rental_from'), row_value(row, 'rental_to'))} · {format_currency(row_value(row, 'total_price', 0))}",
                row_value(row, 'status', 'smlouva'),
                '#2563eb',
                [
                    ('Detail', lambda cid=row_value(row, 'id'): self.app.open_contract_detail(cid)),
                    ('PDF', lambda num=row_value(row, 'contract_number'): self.app.open_contract_pdf(num)),
                ]
            )

    def _render_topmachines(self):
        for w in self.topmachines.body.winfo_children():
            w.destroy()
        rows = self.app.db.get_top_machines(5)
        if not rows:
            ctk.CTkLabel(self.topmachines.body, text='Zatím nejsou žádná data o zápůjčkách.', text_color=("#6b7280", "#94a3b8")).grid(row=0, column=0, sticky='w')
            return
        for idx, row in enumerate(rows):
            card = ctk.CTkFrame(self.topmachines.body, corner_radius=18, fg_color=("#f8fafc", "#111827"), border_width=1, border_color=("#e5e7eb", "#1f2937"))
            card.grid(row=0, column=idx, sticky='nsew', padx=6, pady=4)
            ctk.CTkLabel(card, text=f"#{idx + 1}", font=ctk.CTkFont(size=22, weight='bold'), text_color='#2563eb').pack(anchor='w', padx=14, pady=(12, 4))
            ctk.CTkLabel(card, text=row_value(row, 'name'), font=ctk.CTkFont(weight='bold')).pack(anchor='w', padx=14)
            ctk.CTkLabel(card, text=f"Počet zápůjček: {row_value(row, 'cnt', 0)}", text_color=("#6b7280", "#94a3b8")).pack(anchor='w', padx=14, pady=(2, 12))
