from __future__ import annotations
from pathlib import Path
import os, subprocess, sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from settings import CONTRACTS_DIR, LABELS_DIR, PROTOCOLS_DIR
from utils import row_value, format_date, format_currency, file_label


class PDFGenerator:
    def __init__(self):
        self.font_regular, self.font_bold = self._register_fonts()

    def _register_fonts(self):
        candidates = [
            ('C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/arialbd.ttf'),
            ('C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/segoeuib.ttf'),
            ('C:/Windows/Fonts/calibri.ttf', 'C:/Windows/Fonts/calibrib.ttf'),
        ]
        for regular, bold in candidates:
            if Path(regular).exists() and Path(bold).exists():
                pdfmetrics.registerFont(TTFont('APP_REG', regular))
                pdfmetrics.registerFont(TTFont('APP_BOLD', bold))
                return 'APP_REG', 'APP_BOLD'
        return 'Helvetica', 'Helvetica-Bold'

    def get_contract_pdf_path(self, contract_number: str) -> Path:
        return CONTRACTS_DIR / f'{contract_number}.pdf'

    def get_protocol_pdf_path(self, prefix: str, number: str) -> Path:
        return PROTOCOLS_DIR / f'{prefix}_{number}.pdf'

    def get_label_pdf_path(self, inventory_number: str) -> Path:
        return LABELS_DIR / f'stitek_{inventory_number or "stroj"}.pdf'

    def open_any_pdf(self, path: Path):
        if not path.exists():
            return False, f'Soubor {path.name} nebyl nalezen.'
        try:
            if sys.platform.startswith('win'):
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', str(path)])
            else:
                subprocess.Popen(['xdg-open', str(path)])
            return True, str(path)
        except Exception as exc:
            return False, str(exc)

    def open_pdf(self, contract_number: str):
        return self.open_any_pdf(self.get_contract_pdf_path(contract_number))

    def _wrap(self, text, max_len=100):
        text = str(text or '').strip()
        if not text:
            return ['—']
        words = text.split()
        lines, current = [], ''
        for word in words:
            candidate = (current + ' ' + word).strip()
            if len(candidate) <= max_len:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or ['—']

    def _draw_signature(self, c, path_str, x, y, width_mm=50, height_mm=16):
        c.setStrokeColor(colors.HexColor('#cbd5e1'))
        c.roundRect(x, y - height_mm * mm, width_mm * mm, height_mm * mm, 2 * mm, fill=0, stroke=1)
        p = Path(str(path_str or ''))
        if p.exists():
            try:
                c.drawImage(str(p), x + 1.5 * mm, y - height_mm * mm + 1.5 * mm, width=(width_mm - 3) * mm, height=(height_mm - 3) * mm, preserveAspectRatio=True, mask='auto')
                return
            except Exception:
                pass
        c.setFont(self.font_regular, 8)
        c.setFillColor(colors.HexColor('#64748b'))
        c.drawCentredString(x + (width_mm * mm / 2), y - 9 * mm, 'Podpis není vložen')


    def _section_title(self, c, x, y, title, centered=False):
        c.setFont(self.font_bold, 11)
        c.setFillColor(colors.HexColor("#0f172a"))
        if centered:
            page_center_x = A4[0] / 2
            c.drawCentredString(page_center_x, y, title)
            line_width = 70 * mm
            c.setStrokeColor(colors.HexColor("#cbd5e1"))
            c.line(page_center_x - line_width / 2, y - 1.5 * mm, page_center_x + line_width / 2, y - 1.5 * mm)
        else:
            c.drawString(x, y, title)
            c.setStrokeColor(colors.HexColor("#cbd5e1"))
            c.line(x, y - 1.5 * mm, 192 * mm, y - 1.5 * mm)
        return y - 6 * mm

    def _info_box(self, c, x, y, width_mm, title, lines):
        lines = list(lines or ["—"])
        wrapped=[]
        for line in lines:
            wrapped.extend(self._wrap(line, 42))
        height_mm = max(18, 8 + len(wrapped) * 4.8)
        c.setStrokeColor(colors.HexColor("#cbd5e1"))
        c.setFillColor(colors.white)
        c.roundRect(x, y - height_mm * mm, width_mm * mm, height_mm * mm, 2 * mm, fill=1, stroke=1)
        c.setFont(self.font_bold, 10)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.drawString(x + 3 * mm, y - 5 * mm, title)
        c.setFont(self.font_regular, 8.8)
        c.setFillColor(colors.HexColor("#334155"))
        yy = y - 10 * mm
        for line in wrapped:
            c.drawString(x + 3 * mm, yy, str(line))
            yy -= 4.5 * mm
        return height_mm * mm

    def create_contract_pdf(self, contract, customer, machines, settings) -> Path:
        contract_number = row_value(contract, 'contract_number')
        path = self.get_contract_pdf_path(contract_number)
        c = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4
        x = 18 * mm
        y = height - 18 * mm

        # Header
        contract_title = settings.get('contract_title') or 'Smlouva o zápůjčce stroje'
        contract_subtitle = settings.get('contract_subtitle') or ''
        c.setFont(self.font_bold, 17)
        c.setFillColor(colors.HexColor('#0f172a'))
        c.drawString(x, y, contract_title)
        c.setFont(self.font_regular, 9)
        c.setFillColor(colors.HexColor('#475569'))
        subtitle_lines = []
        if contract_subtitle.strip():
            subtitle_lines = simpleSplit(contract_subtitle.strip(), self.font_regular, 9, 105 * mm)
            for i, line in enumerate(subtitle_lines[:3]):
                c.drawString(x, y - (5 + i * 4.2) * mm, line)
        right_y_top = y - 1 * mm
        c.drawRightString(width - 18 * mm, right_y_top, f'Číslo smlouvy: {contract_number}')
        c.drawRightString(width - 18 * mm, right_y_top - 5 * mm, f'Datum vystavení: {format_date(row_value(contract, "created_at"))}')
        subtitle_block_mm = 0
        if subtitle_lines:
            subtitle_block_mm = 5 + max(0, len(subtitle_lines[:3]) - 1) * 4.2
        y -= max(13, 8 + subtitle_block_mm) * mm

        # Parties
        landlord_lines = [
            settings.get('company_name', ''),
            settings.get('company_address', ''),
            f"IČO: {settings.get('company_ico', '')}" if settings.get('company_ico') else '',
            settings.get('company_phone', ''),
            settings.get('company_email', ''),
        ]
        customer_lines = [
            row_value(customer, 'name') or row_value(customer, 'full_name'),
            row_value(customer, 'company'),
            row_value(customer, 'address'),
            f"Telefon: {row_value(customer, 'phone')}" if row_value(customer, 'phone') else '',
            f"E-mail: {row_value(customer, 'email')}" if row_value(customer, 'email') else '',
            f"Číslo OP: {row_value(customer, 'id_card')}" if row_value(customer, 'id_card') else '',
            f"Č. ŘP: {row_value(customer, 'driver_license')}" if row_value(customer, 'driver_license') else '',
            f"Pas: {row_value(customer, 'passport')}" if row_value(customer, 'passport') else '',
        ]
        left_h = self._info_box(c, x, y, 82, 'Pronajímatel', [line for line in landlord_lines if line])
        right_h = self._info_box(c, 108 * mm, y, 84, 'Zákazník', [line for line in customer_lines if line])
        y -= max(left_h, right_h) + 6 * mm

        # Items table
        y = self._section_title(c, x, y, 'Předmět zápůjčky')
        col_x = [x, 72 * mm, 96 * mm, 118 * mm, 140 * mm]
        headers = ['Stroj / specifikace', 'Inv. číslo', 'Cena / den', 'Kauce', 'Příslušenství']
        c.setFillColor(colors.HexColor('#e2e8f0'))
        c.roundRect(x, y - 6 * mm, 174 * mm, 7 * mm, 2 * mm, fill=1, stroke=0)
        c.setFont(self.font_bold, 8.5)
        c.setFillColor(colors.HexColor('#334155'))
        for i, header in enumerate(headers):
            c.drawString(col_x[i] + 1.5 * mm, y - 3.8 * mm, header)
        y -= 9 * mm
        c.setFont(self.font_regular, 8.5)
        for machine in machines:
            acc_lines = self._wrap((row_value(machine, 'accessories_issued') or row_value(machine, 'accessories') or '—').replace('\n', ', '), 34)[:4]
            if not acc_lines:
                acc_lines = ['—']
            row_height = max(12 * mm, (9 + (len(acc_lines)-1) * 3.8) * mm)
            if y < max(60 * mm, row_height + 35):
                c.showPage()
                y = height - 18 * mm
                y = self._section_title(c, x, y, 'Předmět zápůjčky')
                c.setFillColor(colors.HexColor('#e2e8f0'))
                c.roundRect(x, y - 6 * mm, 174 * mm, 7 * mm, 2 * mm, fill=1, stroke=0)
                c.setFont(self.font_bold, 8.5)
                c.setFillColor(colors.HexColor('#334155'))
                for i, header in enumerate(headers):
                    c.drawString(col_x[i] + 1.5 * mm, y - 3.8 * mm, header)
                y -= 9 * mm
            c.setStrokeColor(colors.HexColor('#e5e7eb'))
            c.roundRect(x, y - row_height + 1 * mm, 174 * mm, row_height, 1.8 * mm, fill=0, stroke=1)
            name_line = row_value(machine, 'name') or '—'
            spec_parts = [v for v in [row_value(machine, 'model'), row_value(machine, 'serial_number')] if v]
            if row_value(machine, 'motohours') not in ('', None):
                spec_parts.append(f"Motohodiny: {row_value(machine, 'motohours')}")
            spec_line = ' / '.join(spec_parts)
            c.setFont(self.font_bold, 8.6)
            c.setFillColor(colors.HexColor('#0f172a'))
            c.drawString(col_x[0] + 1.5 * mm, y - 4.2 * mm, str(name_line)[:28])
            c.setFont(self.font_regular, 7.8)
            c.setFillColor(colors.HexColor('#64748b'))
            c.drawString(col_x[0] + 1.5 * mm, y - 8.3 * mm, str(spec_line or 'Bez specifikace')[:30])
            c.setFont(self.font_regular, 8.3)
            c.setFillColor(colors.HexColor('#334155'))
            c.drawString(col_x[1] + 1.5 * mm, y - 6.2 * mm, str(row_value(machine, 'inventory_number') or '—')[:10])
            c.drawString(col_x[2] + 1.5 * mm, y - 6.2 * mm, format_currency(row_value(machine, 'daily_rate', 0)).replace(' Kč', ''))
            c.drawString(col_x[3] + 1.5 * mm, y - 6.2 * mm, format_currency(row_value(machine, 'deposit', 0)).replace(' Kč', ''))
            acc_y = y - 4.6 * mm
            for line in acc_lines:
                c.drawString(col_x[4] + 1.5 * mm, acc_y, line)
                acc_y -= 3.8 * mm
            y -= row_height + 2.5 * mm

        # Rental and finance boxes
        y -= 1 * mm
        y = self._section_title(c, x, y, 'Termín a finanční ujednání')
        rental_lines = [
            f'Od: {format_date(row_value(contract, "rental_from"))}',
            f'Do: {format_date(row_value(contract, "rental_to"))}',
            f'Způsob platby: {row_value(contract, "payment_method") or "—"}',
        ]
        finance_lines = [
            f'Cena pronájmu: {format_currency(row_value(contract, "total_price", 0))}',
            f'Kauce: {format_currency(row_value(contract, "deposit", 0))}',
            f'Uhrazeno: {format_currency(row_value(contract, "paid_amount", 0))}',
        ]
        left_h = self._info_box(c, x, y, 82, 'Termín zápůjčky', rental_lines)
        right_h = self._info_box(c, 108 * mm, y, 84, 'Cenové podmínky', finance_lines)
        y -= max(left_h, right_h) + 5 * mm

        # Handover and notes
        y = self._section_title(c, x, y, 'Předání a poznámky')
        note_lines = [
            f'Stav při předání: {row_value(machines[0] if machines else contract, "issue_condition") or "—"}',
        ]
        for line in note_lines:
            c.setFont(self.font_regular, 9)
            c.setFillColor(colors.HexColor('#334155'))
            c.drawString(x, y, line)
            y -= 5 * mm
        y -= 1 * mm
        notes = self._wrap(row_value(contract, 'notes') or 'Bez zvláštních poznámek.', 110)
        for line in notes:
            if y < 55 * mm:
                c.showPage()
                y = height - 20 * mm
            c.drawString(x, y, line)
            y -= 4.5 * mm

        # Reserve bottom area for place/date + signatures on the same page
        sign_block_top = 34 * mm

        # Terms first (centered but wider)
        y -= 2 * mm
        y = self._section_title(c, x, y, 'Podmínky', centered=True)
        c.setFont(self.font_regular, 8.8)
        c.setFillColor(colors.HexColor('#334155'))
        terms_text = settings.get('contract_terms') or 'Zákazník potvrzuje převzetí stroje ve sjednaném stavu a zavazuje se jej vrátit v dohodnutém termínu.'
        page_center_x = width / 2
        max_chars = 125
        centered_lines = self._wrap(terms_text, max_chars)
        for line in centered_lines:
            if y < sign_block_top + 26 * mm:
                c.showPage()
                y = height - 20 * mm
                c.setFont(self.font_regular, 8.8)
                c.setFillColor(colors.HexColor('#334155'))
                y = self._section_title(c, x, y, 'Podmínky', centered=True)
            c.drawCentredString(page_center_x, y, line)
            y -= 4.6 * mm

        # Declaration after terms
        declaration_text = settings.get('contract_declaration') or ''
        if declaration_text.strip():
            y -= 3 * mm
            y = self._section_title(c, x, y, 'Prohlášení', centered=True)
            c.setFont(self.font_regular, 8.8)
            c.setFillColor(colors.HexColor('#334155'))
            declaration_lines = self._wrap(declaration_text, 118)
            for line in declaration_lines:
                if y < sign_block_top + 20 * mm:
                    c.showPage()
                    y = height - 20 * mm
                    c.setFont(self.font_regular, 8.8)
                    c.setFillColor(colors.HexColor('#334155'))
                    y = self._section_title(c, x, y, 'Prohlášení', centered=True)
                c.drawCentredString(page_center_x, y, line)
                y -= 4.6 * mm

        # Signatures stay on the same page near the bottom whenever there is space
        if y < sign_block_top + 14 * mm:
            c.showPage()
            y = height - 24 * mm
        sign_top = sign_block_top
        c.setFont(self.font_regular, 9)
        c.setFillColor(colors.HexColor('#0f172a'))
        place_line = (settings.get('contract_place') or 'V ____________') + ' dne ....................'
        c.drawString(x, sign_top + 8 * mm, place_line)
        c.drawString(x, sign_top + 1 * mm, 'Podpis pronajímatele')
        c.drawString(110 * mm, sign_top + 1 * mm, 'Podpis zákazníka')
        c.setStrokeColor(colors.HexColor('#94a3b8'))
        c.line(x, sign_top - 9 * mm, x + 58 * mm, sign_top - 9 * mm)
        c.line(110 * mm, sign_top - 9 * mm, 168 * mm, sign_top - 9 * mm)
        c.setFillColor(colors.HexColor('#64748b'))
        c.setFont(self.font_regular, 8)
        c.drawCentredString(width / 2, 10 * mm, f"{settings.get('company_name','')} · {settings.get('company_phone','')} · {settings.get('company_email','')}")
        c.save()
        return path

    def create_return_protocol_pdf(self, contract, customer, items, settings=None):
        settings = settings or {}
        number = row_value(contract, 'contract_number')
        path = self.get_protocol_pdf_path('vratka', number)
        c = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4
        x = 18 * mm
        y = height - 18 * mm

        c.setFont(self.font_bold, 17)
        c.setFillColor(colors.HexColor('#0f172a'))
        c.drawString(x, y, 'Vratný protokol')

        c.setFont(self.font_regular, 9)
        c.setFillColor(colors.HexColor('#475569'))
        company = settings.get('company_name', '').strip() or 'Půjčovna strojů'
        company_lines = [company]
        detail_parts = [p for p in [settings.get('company_address', '').strip(), f"IČO: {settings.get('company_ico', '').strip()}" if settings.get('company_ico', '').strip() else '', f"DIČ: {settings.get('company_dic', '').strip()}" if settings.get('company_dic', '').strip() else ''] if p]
        if detail_parts:
            company_lines.append(' · '.join(detail_parts))
        contact_parts = [p for p in [settings.get('company_phone', '').strip(), settings.get('company_email', '').strip()] if p]
        if contact_parts:
            company_lines.append(' · '.join(contact_parts))
        header_note = (settings.get('return_protocol_header_text') or '').strip()
        if header_note:
            company_lines.extend(simpleSplit(header_note, self.font_regular, 8.8, 112 * mm)[:3])

        for i, line in enumerate(company_lines[:5]):
            c.drawString(x, y - (5 + i * 4.2) * mm, line)

        right_y_top = y + 1 * mm
        c.drawRightString(width - 18 * mm, right_y_top, f'Číslo smlouvy: {number}')
        generated_date = row_value(contract, 'returned_at') or row_value(contract, 'return_date') or row_value(contract, 'rental_to')
        c.drawRightString(width - 18 * mm, right_y_top - 5 * mm, f'Datum vrácení: {format_date(generated_date)}')

        header_block_mm = 5 + max(0, len(company_lines[:5]) - 1) * 4.2
        y -= max(17, 8 + header_block_mm) * mm

        customer_lines = [
            row_value(customer, 'name') or row_value(customer, 'full_name') or '—',
            row_value(customer, 'company'),
            row_value(customer, 'address'),
            f"Telefon: {row_value(customer, 'phone')}" if row_value(customer, 'phone') else '',
            f"E-mail: {row_value(customer, 'email')}" if row_value(customer, 'email') else '',
        ]
        return_lines = [
            f"Datum vrácení: {format_date(row_value(contract, 'returned_at') or row_value(contract, 'return_date'))}",
            f"Stav smlouvy: {row_value(contract, 'status') or '—'}",
            f"Vrácená kauce: {format_currency(row_value(contract, 'deposit_returned', 0))}",
            f"Doplatek / škoda: {format_currency(row_value(contract, 'return_extra_charge', 0))}",
        ]
        left_h = self._info_box(c, x, y, 82, 'Zákazník', [line for line in customer_lines if line])
        right_h = self._info_box(c, 108 * mm, y, 84, 'Vrácení a finance', return_lines)
        y -= max(left_h, right_h) + 6 * mm

        y = self._section_title(c, x, y, 'Vrácené položky')
        col_x = [x, 84 * mm, 126 * mm, 162 * mm]
        headers = ['Stroj / inv. číslo', 'Stav při vrácení', 'Příslušenství', 'Poškození / pozn.']
        header_h = 7.5 * mm
        c.setFillColor(colors.HexColor('#e2e8f0'))
        c.roundRect(x, y - 6.4 * mm, 174 * mm, header_h, 2 * mm, fill=1, stroke=0)
        c.setFont(self.font_bold, 8.2)
        c.setFillColor(colors.HexColor('#334155'))
        for i, header in enumerate(headers):
            c.drawString(col_x[i] + 1.5 * mm, y - 4.1 * mm, header)
        y -= 9 * mm
        c.setFont(self.font_regular, 8.3)
        for item in items:
            damage_lines = self._wrap(row_value(item, 'damage_notes') or '—', 24)[:2]
            row_h = 15 * mm if len(damage_lines) > 1 else 11.5 * mm
            if y < 45 * mm:
                c.showPage()
                y = height - 18 * mm
                y = self._section_title(c, x, y, 'Vrácené položky')
                c.setFillColor(colors.HexColor('#e2e8f0'))
                c.roundRect(x, y - 6.4 * mm, 174 * mm, header_h, 2 * mm, fill=1, stroke=0)
                c.setFont(self.font_bold, 8.2)
                c.setFillColor(colors.HexColor('#334155'))
                for i, header in enumerate(headers):
                    c.drawString(col_x[i] + 1.5 * mm, y - 4.1 * mm, header)
                y -= 9 * mm
                c.setFont(self.font_regular, 8.3)
            c.setStrokeColor(colors.HexColor('#e5e7eb'))
            c.roundRect(x, y - row_h + 1 * mm, 174 * mm, row_h, 1.8 * mm, fill=0, stroke=1)
            c.setFillColor(colors.HexColor('#0f172a'))
            c.setFont(self.font_bold, 8.6)
            c.drawString(col_x[0] + 1.5 * mm, y - 4.2 * mm, str(row_value(item, 'name') or '—')[:28])
            c.setFont(self.font_regular, 7.8)
            c.setFillColor(colors.HexColor('#64748b'))
            c.drawString(col_x[0] + 1.5 * mm, y - 8.3 * mm, str(row_value(item, 'inventory_number') or 'bez čísla')[:18])
            c.setFont(self.font_regular, 8.3)
            c.setFillColor(colors.HexColor('#334155'))
            c.drawString(col_x[1] + 1.5 * mm, y - 6.2 * mm, str(row_value(item, 'return_condition') or '—')[:22])
            c.drawString(col_x[2] + 1.5 * mm, y - 6.2 * mm, str(row_value(item, 'accessories_returned') or '—')[:20])
            damage_y = y - 4.8 * mm
            for line in damage_lines:
                c.drawString(col_x[3] + 1.5 * mm, damage_y, line)
                damage_y -= 3.9 * mm
            y -= row_h + 2.5 * mm

        footer_text = (settings.get('return_protocol_footer') or '').strip()
        if footer_text:
            y -= 1 * mm
            y = self._section_title(c, x, y, 'Doplňující text')
            c.setFont(self.font_regular, 8.8)
            c.setFillColor(colors.HexColor('#334155'))
            for line in self._wrap(footer_text, 118):
                if y < 45 * mm:
                    c.showPage()
                    y = height - 20 * mm
                    y = self._section_title(c, x, y, 'Doplňující text')
                    c.setFont(self.font_regular, 8.8)
                    c.setFillColor(colors.HexColor('#334155'))
                c.drawString(x, y, line)
                y -= 4.6 * mm

        sign_block_top = 26 * mm
        if y < sign_block_top + 18 * mm:
            c.showPage()
            y = height - 24 * mm
            if footer_text:
                c.setFont(self.font_regular, 8.8)
                c.setFillColor(colors.HexColor('#334155'))
        sign_top = sign_block_top
        c.setStrokeColor(colors.HexColor('#94a3b8'))
        c.line(x, sign_top - 10 * mm, x + 58 * mm, sign_top - 10 * mm)
        c.line(110 * mm, sign_top - 10 * mm, 168 * mm, sign_top - 10 * mm)
        c.setFont(self.font_regular, 9)
        c.setFillColor(colors.HexColor('#0f172a'))
        place_line = (settings.get('contract_place') or 'V ____________') + ' dne ....................'
        c.drawString(x, sign_top + 8 * mm, place_line)
        c.drawString(x, sign_top + 1 * mm, 'Podpis pronajímatele')
        c.drawString(110 * mm, sign_top + 1 * mm, 'Podpis zákazníka')
        c.setFillColor(colors.HexColor('#64748b'))
        c.setFont(self.font_regular, 8)
        footer_company = ' · '.join([p for p in [settings.get('company_name',''), settings.get('company_phone',''), settings.get('company_email','')] if p])
        if footer_company:
            c.drawCentredString(width / 2, 10 * mm, footer_company)
        c.save()
        return path

    def create_service_protocol_pdf(self, machine, service):
        inv = row_value(machine, 'inventory_number') or row_value(machine, 'id')
        path = self.get_protocol_pdf_path('servis', str(inv))
        c = canvas.Canvas(str(path), pagesize=A4)
        w, h = A4
        x = 18 * mm
        y = h - 18 * mm
        c.setFont(self.font_bold, 18)
        c.drawString(x, y, 'Servisní protokol')
        y -= 12 * mm
        c.setFont(self.font_regular, 10)
        for line in [
            f"Stroj: {row_value(machine, 'name')}",
            f"Inventární číslo: {row_value(machine, 'inventory_number')}",
            f"Datum servisu: {format_date(row_value(service, 'service_date'))}",
            f"Typ servisu: {row_value(service, 'service_type')}",
            f"Cena servisu: {format_currency(row_value(service, 'cost', 0))}",
            f"Dodavatel servisu: {row_value(service, 'provider') or '—'}",
            f"Další servis: {format_date(row_value(service, 'next_service_date'))}",
        ]:
            c.drawString(x, y, line)
            y -= 6 * mm
        y -= 2 * mm
        c.setFont(self.font_bold, 11)
        c.drawString(x, y, 'Poznámka')
        y -= 6 * mm
        c.setFont(self.font_regular, 9)
        for line in self._wrap(row_value(service, 'notes') or '—', 110):
            c.drawString(x, y, line)
            y -= 4.5 * mm
        c.save()
        return path

    def create_machine_label_pdf(self, machine):
        path = self.get_label_pdf_path(row_value(machine, 'inventory_number'))
        c = canvas.Canvas(str(path), pagesize=(90 * mm, 55 * mm))
        c.setFont(self.font_bold, 14)
        c.drawString(8 * mm, 46 * mm, row_value(machine, 'name')[:22])
        c.setFont(self.font_regular, 9)
        c.drawString(8 * mm, 39 * mm, f"Inv. číslo: {row_value(machine, 'inventory_number')}")
        c.drawString(8 * mm, 33 * mm, f"Model: {row_value(machine, 'model') or '—'}")
        c.save()
        return path

    def _draw_qr(self, c, text, x, y, size_mm=24):
        return
