from __future__ import annotations
import csv
import getpass
import html
import json
import os
import socket
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import textwrap
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEasingCurve, QPoint, Property, QPropertyAnimation, QEventLoop, Qt, QTimer, Signal, QDate, QEvent, QSize
from PySide6.QtGui import QAction, QColor, QPainter, QFont, QFontMetrics, QIcon, QKeyEvent, QPixmap, QTextCharFormat, QBrush
from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QAbstractScrollArea, QAbstractSpinBox, QCheckBox, QComboBox, QDateEdit, QDialog,
    QFileDialog, QFormLayout, QFrame, QGraphicsOpacityEffect, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QPlainTextEdit, QScroller,
    QProgressDialog, QScrollArea, QSizePolicy, QSplitter, QStackedWidget, QTableWidget,
    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget, QCalendarWidget
)

from database import Database
from pdf_generator import PDFGenerator
from settings import APP_NAME, APP_VERSION, PHOTOS_DIR, RELEASE_ASSET_NAME, UPDATES_DIR, load_theme, save_theme

ACCENT = '#ff8a00'
ACCENT_2 = '#31c7ff'
BG = '#0c0f14'
PANEL = '#141922'
PANEL_2 = '#191f2a'
PANEL_3 = '#11161e'
TEXT = '#f4f7fb'
MUTED = '#95a1b3'
GRID = '#273140'
GOOD = '#27c26c'
WARN = '#f2b641'
BAD = '#ea5455'
APP_ICON_PATH = Path(__file__).resolve().parent / 'assets' / 'app_icon.ico'


def get_theme_palette(theme: str) -> dict[str, str]:
    if (theme or '').strip().lower() == 'light':
        return {
            'ACCENT': '#e67e22',
            'ACCENT_2': '#0f8ec7',
            'BG': '#eef3f8',
            'PANEL': '#ffffff',
            'PANEL_2': '#f4f8fc',
            'PANEL_3': '#e8eef5',
            'TEXT': '#13202b',
            'MUTED': '#5f7285',
            'GRID': '#c8d4df',
            'BORDER': '#cfd9e3',
            'BORDER_STRONG': '#b8c6d3',
            'TOPBAR': '#f7fafc',
            'RAIL': '#e9f0f6',
            'RAIL_METRIC': '#f4f8fc',
            'INPUT_BG': '#f8fbfe',
            'HEADER_BG': '#edf3f8',
            'SCROLL_BG': '#dde6ef',
            'SCROLL_HANDLE': '#b4c3d1',
            'SELECTION_BG': '#dbeafe',
            'PRIMARY_TEXT': '#0f1720',
            'PRIMARY_ON_ACCENT': '#ffffff',
            'NAV_HOVER_TEXT': '#13202b',
            'NAV_SELECTED_TEXT': '#13202b',
            'DIALOG_BADGE_BG': '#edf3f8',
        }
    return {
        'ACCENT': ACCENT,
        'ACCENT_2': ACCENT_2,
        'BG': BG,
        'PANEL': PANEL,
        'PANEL_2': PANEL_2,
        'PANEL_3': PANEL_3,
        'TEXT': TEXT,
        'MUTED': MUTED,
        'GRID': GRID,
        'BORDER': '#293648',
        'BORDER_STRONG': '#232e3d',
        'TOPBAR': '#11161e',
        'RAIL': '#0f131a',
        'RAIL_METRIC': '#10161f',
        'INPUT_BG': PANEL_3,
        'HEADER_BG': '#141b25',
        'SCROLL_BG': '#11161e',
        'SCROLL_HANDLE': '#2a3544',
        'SELECTION_BG': '#243041',
        'PRIMARY_TEXT': TEXT,
        'PRIMARY_ON_ACCENT': '#101010',
        'NAV_HOVER_TEXT': '#ffffff',
        'NAV_SELECTED_TEXT': '#ffffff',
        'DIALOG_BADGE_BG': '#1a2330',
    }


def sync_theme_globals(theme: str) -> dict[str, str]:
    palette = get_theme_palette(theme)
    globals()['ACCENT'] = palette['ACCENT']
    globals()['ACCENT_2'] = palette['ACCENT_2']
    globals()['BG'] = palette['BG']
    globals()['PANEL'] = palette['PANEL']
    globals()['PANEL_2'] = palette['PANEL_2']
    globals()['PANEL_3'] = palette['PANEL_3']
    globals()['TEXT'] = palette['TEXT']
    globals()['MUTED'] = palette['MUTED']
    globals()['GRID'] = palette['GRID']
    return palette


def build_stylesheet(theme: str) -> str:
    p = get_theme_palette(theme)
    return f"""
QWidget {{ background: {p['BG']}; color: {p['TEXT']}; font-family: "Segoe UI Variable Display", "Segoe UI", Arial; font-size: 14px; }}
QLabel {{ background: transparent; }}
#Rail {{ background: {p['RAIL']}; border-right: 1px solid {p['BORDER']}; }}
#Brand, #QuickPanel, #Panel, #StatCard, #ToolbarPanel, #Toast, #DialogHeader, #ActionItem, #SettingsHero, #DetailHero, #DetailMiniCard, #SelectionPanel, #StepChip, #KpiTile, #DashboardHero, #DetailSectionCard, #PhotoPreviewCard, #HeroChip {{ background: {p['PANEL']}; border: 1px solid {p['BORDER_STRONG']}; border-radius: 14px; }}
#Topbar {{ background: {p['TOPBAR']}; border-bottom: 1px solid {p['BORDER']}; }}
#DashboardHero {{ border-radius: 22px; }}
#DashboardHeroAccent {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {p['ACCENT']}, stop:1 {p['ACCENT_2']}); border-radius: 18px; }}
#DashboardHeroTitle {{ font-size: 28px; font-weight: 700; }}
#DashboardHeroSub {{ color: {p['MUTED']}; font-size: 13px; }}
#HeroChip {{ padding: 10px 12px; border-radius: 14px; }}
#HeroChipLabel {{ color: {p['MUTED']}; font-size: 11px; font-weight: 700; letter-spacing: 0.4px; }}
#HeroChipValue {{ color: {p['TEXT']}; font-size: 18px; font-weight: 700; }}
#PhotoPreviewCard:hover {{ border-color: {p['ACCENT_2']}; }}
#PhotoCaption {{ color: {p['MUTED']}; font-size: 12px; }}
#LightboxSurface {{ background: {p['PANEL']}; border: 1px solid {p['BORDER_STRONG']}; border-radius: 18px; }}
#LightboxTitle {{ font-size: 18px; font-weight: 700; }}
#LightboxHint {{ color: {p['MUTED']}; font-size: 12px; }}
#DetailSectionCard {{ border-radius: 18px; }}
#DetailSectionTitle {{ font-size: 15px; font-weight: 700; }}
#DetailSectionSub {{ color: {p['MUTED']}; font-size: 12px; }}
#CalendarBtn {{ min-width: 38px; max-width: 38px; min-height: 38px; max-height: 38px; padding: 0; border-radius: 12px; font-size: 16px; font-weight: 700; }}
#RailBadge {{ background: {p['PANEL_2']}; border: 1px solid {p['BORDER_STRONG']}; border-radius: 10px; padding: 4px 8px; color: {p['ACCENT_2']}; font-size: 11px; font-weight: 700; }}
#RailSection {{ color: {p['MUTED']}; font-size: 11px; font-weight: 700; letter-spacing: 1px; padding: 6px 2px 0 2px; }}
#BrandTitle {{ font-size: 24px; font-weight: 700; }}
#BrandSub, #CardSubtle, #PanelSubtle, #ActionSub, #DetailHeroSub, #DetailMiniLabel, #HintMuted {{ color: {p['MUTED']}; }}
#ActionTitle {{ font-size: 14px; font-weight: 700; }}
#TopTitle {{ font-size: 24px; font-weight: 700; }}
#PageTitle {{ font-size: 30px; font-weight: 700; }}
#PanelTitle {{ font-size: 16px; font-weight: 700; }}
#CardValue {{ font-size: 30px; font-weight: 700; }}
#Dialog, #Dialog * {{ background: {p['BG']}; }}
#DialogHeader {{ background: {p['PANEL']}; }}
#DialogTitle {{ font-size: 22px; font-weight: 700; }}
#SettingsHeroTitle, #DetailHeroTitle {{ font-size: 20px; font-weight: 700; }}
#DetailBadge {{ background: {p['DIALOG_BADGE_BG']}; border: 1px solid {p['BORDER_STRONG']}; padding: 6px 10px; color: {p['TEXT']}; font-size: 12px; font-weight: 700; }}
#DetailMiniValue {{ font-size: 18px; font-weight: 700; }}
#DetailKeyLabel {{ color: {p['MUTED']}; min-width: 140px; }}
#SelectionPanel {{ background: {p['PANEL_3']}; border: 1px solid {p['BORDER_STRONG']}; }}
#StepChip {{ padding: 8px 12px; font-size: 12px; font-weight: 700; background: {p['PANEL_3']}; border-radius: 999px; }}
#StepChipActive {{ padding: 8px 12px; font-size: 12px; font-weight: 700; background: {p['ACCENT']}; color: {p['PRIMARY_ON_ACCENT']}; border: 1px solid {p['ACCENT']}; }}
#KpiTile {{ background: {p['PANEL_3']}; padding: 10px; border-radius: 12px; }}
#SelectionTitle {{ font-size: 13px; font-weight: 700; color: {p['TEXT']}; }}
#DetailValueLabel {{ color: {p['TEXT']}; }}
#NavList {{ background: transparent; border: 0; outline: 0; }}
#NavList::item {{ padding: 12px 14px; margin: 1px 0; border: 1px solid transparent; border-radius: 8px; }}
#NavList::item:hover {{ background: {p['PANEL_2']}; border-color: {p['BORDER_STRONG']}; color: {p['NAV_HOVER_TEXT']}; }}
#NavList::item:selected {{ background: {p['PANEL_2']}; border-left: 4px solid {p['ACCENT']}; border-color: {p['BORDER_STRONG']}; font-weight: 700; color: {p['NAV_SELECTED_TEXT']}; }}
QListWidget#SettingsNav {{ background: transparent; border: 0; outline: 0; }}
QListWidget#SettingsNav::item {{ padding: 12px 10px; margin: 2px 0; border: 1px solid transparent; }}
QListWidget#SettingsNav::item:selected {{ background: {p['PANEL_2']}; border-left: 4px solid {p['ACCENT_2']}; font-weight: 700; }}
QListWidget#ActionList {{ background: transparent; border: 0; }}
QListWidget#ActionList::item {{ border: 0; margin: 0 0 3px 0; }}
#ActionItem:hover {{ border-color: {p['ACCENT_2']}; }}
#RailMetric {{ background: {p['RAIL_METRIC']}; border: 1px solid {p['BORDER_STRONG']}; border-radius: 10px; }}
#RailMetricLabel {{ color: {p['MUTED']}; font-size: 12px; font-weight: 600; }}
#RailMetricValue {{ color: {p['TEXT']}; font-size: 18px; font-weight: 700; }}
QGroupBox#FormGroup {{ border: 1px solid {p['BORDER_STRONG']}; margin-top: 10px; padding-top: 8px; background: {p['PANEL']}; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; top: -2px; padding: 0 6px; color: {p['TEXT']}; font-weight: 700; }}
QLineEdit, QComboBox, QDateEdit, QPlainTextEdit, QListWidget, QTabWidget::pane, QScrollArea, QStackedWidget#SettingsStack {{ background: {p['INPUT_BG']}; border: 1px solid {p['BORDER']}; border-radius: 12px; padding: 9px 11px; color: {p['TEXT']}; selection-background-color: {p['SELECTION_BG']}; }}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QPlainTextEdit:focus, QListWidget:focus {{ border-color: {p['ACCENT_2']}; }}
QDateEdit::drop-down, QComboBox::drop-down {{ border: 0; width: 24px; }}
QComboBox QAbstractItemView {{ background: {p['PANEL']}; border: 1px solid {p['BORDER']}; selection-background-color: {p['SELECTION_BG']}; }}
QPushButton {{ padding: 10px 14px; border: 1px solid {p['BORDER']}; border-radius: 12px; background: {p['PANEL_3']}; color: {p['TEXT']}; font-weight: 600; }}
QPushButton:hover {{ border-color: {p['ACCENT_2']}; }}
QPushButton#PrimaryBtn {{ background: {p['ACCENT']}; color: {p['PRIMARY_ON_ACCENT']}; border: 1px solid {p['ACCENT']}; font-weight: 700; }}
QPushButton#GhostBtn {{ background: {p['PANEL_3']}; color: {p['TEXT']}; border: 1px solid {p['BORDER']}; }}
QTableWidget {{ background: {p['INPUT_BG']}; border: 1px solid {p['BORDER']}; border-radius: 14px; gridline-color: {p['GRID']}; selection-background-color: {p['SELECTION_BG']}; selection-color: {p['TEXT']}; alternate-background-color: {p['PANEL']}; }}
QTableWidget::item {{ padding: 8px 10px; border: 0; }}
QHeaderView::section {{ background: {p['HEADER_BG']}; color: {p['TEXT']}; padding: 12px 10px; border: 0; border-right: 1px solid {p['GRID']}; border-bottom: 1px solid {p['BORDER']}; font-weight: 700; }}
QTableCornerButton::section {{ background: {p['HEADER_BG']}; border: 0; }}
QScrollBar:vertical {{ background: {p['SCROLL_BG']}; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {p['SCROLL_HANDLE']}; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QTabBar::tab {{ background: {p['PANEL_3']}; padding: 10px 14px; border: 1px solid {p['BORDER']}; border-top-left-radius: 10px; border-top-right-radius: 10px; }}
QTabBar::tab:selected {{ background: {p['PANEL']}; border-bottom: 1px solid {p['ACCENT']}; }}
QCalendarWidget QWidget {{ alternate-background-color: {p['PANEL']}; }}
QCalendarWidget QToolButton {{ color: {p['TEXT']}; border-radius: 10px; padding: 6px 10px; }}
QCalendarWidget QAbstractItemView:enabled {{ background: {p['INPUT_BG']}; selection-background-color: {p['SELECTION_BG']}; selection-color: {p['TEXT']}; }}
QToolTip {{ background: {p['PANEL']}; color: {p['TEXT']}; border: 1px solid {p['BORDER_STRONG']}; padding: 8px 10px; border-radius: 10px; }}
"""


def row_get(row: Any, key: str, default=''):
    try:
        return row[key]
    except Exception:
        try:
            return row.get(key, default)
        except Exception:
            return default


def as_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:
        out = {}
        for key in getattr(row, 'keys', lambda: [])():
            out[key] = row[key]
        return out


def parse_float(value: Any) -> float:
    try:
        txt = str(value).replace(' ', '').replace(',', '.')
        return float(txt or 0)
    except Exception:
        return 0.0


def fmt_money(v: Any) -> str:
    try:
        return f"{float(v or 0):,.0f} Kč".replace(',', ' ')
    except Exception:
        return '0 Kč'


def today_str() -> str:
    return date.today().strftime('%Y-%m-%d')


def parse_iso_date(value: Any) -> date | None:
    try:
        text = str(value or '').strip()
        if not text:
            return None
        return datetime.strptime(text[:10], '%Y-%m-%d').date()
    except Exception:
        return None


def fmt_date(value: Any) -> str:
    dt = parse_iso_date(value)
    if dt is None:
        return str(value or '')
    return dt.strftime('%d.%m.%Y')


def contains_date_hint(header: str) -> bool:
    h = str(header or '').strip().lower()
    return any(token in h for token in ['datum', 'od', 'do', 'vrác', 'vrat', 'servis'])


def format_display_value(header: str, value: Any) -> str:
    if contains_date_hint(header):
        formatted = fmt_date(value)
        return formatted if formatted else str(value or '')
    return str(value if value is not None else '')


def pricing_mode_label(mode: str) -> str:
    return {
        'day': 'Denní sazba',
        'weekend': 'Víkendová sazba',
        'week': 'Týdenní sazba',
        'manual': 'Ruční cena',
    }.get(str(mode or 'day'), 'Denní sazba')


def compute_rental_days(date_from: QDate, date_to: QDate) -> int:
    return max(1, int(date_from.daysTo(date_to) or 1))


def machine_rate_for_mode(machine: Any, pricing_mode: str) -> float:
    mode = str(pricing_mode or 'day')
    rate_map = {
        'day': parse_float(row_get(machine, 'daily_rate', 0)),
        'weekend': parse_float(row_get(machine, 'weekend_rate', 0)),
        'week': parse_float(row_get(machine, 'weekly_rate', 0)),
    }
    chosen = rate_map.get(mode, 0.0)
    if chosen > 0:
        return chosen
    return parse_float(row_get(machine, 'daily_rate', 0))


def normalize_version_tag(value: str) -> str:
    return str(value or '').strip().lstrip('vV')


def version_key(value: str) -> tuple[int, ...]:
    clean = normalize_version_tag(value)
    parts: list[int] = []
    for chunk in clean.replace('-', '.').split('.'):
        digits = ''.join(ch for ch in chunk if ch.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts or [0])


def github_latest_release(repo: str) -> dict[str, Any]:
    url = f'https://api.github.com/repos/{repo}/releases/latest'
    req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': f'{APP_NAME}/{APP_VERSION}'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode('utf-8'))


def load_preview_pixmap(path: str | Path, width: int = 148, height: int = 104) -> QPixmap:
    pixmap = QPixmap(str(path or ''))
    if pixmap.isNull():
        return QPixmap()
    return pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def build_photo_preview(path: str | Path, caption: str = '', width: int = 148, height: int = 104) -> QWidget:
    wrap = QFrame()
    wrap.setObjectName('PhotoPreviewCard')
    lay = QVBoxLayout(wrap)
    lay.setContentsMargins(10, 10, 10, 10)
    lay.setSpacing(8)
    img = QLabel()
    img.setAlignment(Qt.AlignCenter)
    img.setMinimumSize(width, height)
    img.setStyleSheet(f'background:{PANEL_3}; border:1px solid {GRID}; border-radius:10px;')
    pixmap = load_preview_pixmap(path, width, height)
    if pixmap.isNull():
        img.setText('Bez náhledu')
        img.setObjectName('HintMuted')
    else:
        img.setPixmap(pixmap)
    lay.addWidget(img)
    text = QLabel(caption or Path(str(path or '')).name)
    text.setWordWrap(True)
    text.setObjectName('PhotoCaption')
    lay.addWidget(text)
    return wrap


def set_click_handler(widget: QWidget, callback):
    widget.setCursor(Qt.PointingHandCursor)

    def _mouse_release(event):
        if getattr(event, 'button', lambda: None)() == Qt.LeftButton:
            callback()
        QWidget.mouseReleaseEvent(widget, event)

    widget.mouseReleaseEvent = _mouse_release


class PhotoLightboxDialog(QDialog):
    def __init__(self, parent: QWidget, photos: list[dict[str, Any]], start_index: int = 0, title: str = 'Fotogalerie'):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(1120, 860)
        self.setMinimumSize(920, 720)
        self.setObjectName('Dialog')
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(18, 18, 18, 18)
        self.root.setSpacing(12)
        self.photos = photos or []
        self.index = max(0, min(start_index, max(0, len(self.photos) - 1)))
        center_dialog(parent, self)
        self.cancel_btn.setText('Zavřít')

        shell = QFrame()
        shell.setObjectName('LightboxSurface')
        outer = QVBoxLayout(shell)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.photo_title = QLabel('')
        self.photo_title.setObjectName('LightboxTitle')
        self.photo_hint = QLabel('Klikni na šipky pro přechod mezi fotkami.')
        self.photo_hint.setObjectName('LightboxHint')
        titles.addWidget(self.photo_title)
        titles.addWidget(self.photo_hint)
        header.addLayout(titles, 1)
        self.open_external_btn = QPushButton('Otevřít originál')
        self.open_external_btn.setObjectName('GhostBtn')
        self.open_external_btn.clicked.connect(self.open_current_external)
        header.addWidget(self.open_external_btn)
        outer.addLayout(header)

        image_row = QHBoxLayout()
        image_row.setSpacing(12)
        self.prev_btn = QPushButton('←')
        self.prev_btn.setObjectName('GhostBtn')
        self.prev_btn.setFixedWidth(52)
        self.prev_btn.clicked.connect(lambda: self.step_photo(-1))
        image_row.addWidget(self.prev_btn, 0, Qt.AlignVCenter)

        self.image = QLabel()
        self.image.setMinimumSize(860, 560)
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setStyleSheet(f'background:{PANEL_3}; border:1px solid {GRID}; border-radius:16px;')
        image_row.addWidget(self.image, 1)

        self.next_btn = QPushButton('→')
        self.next_btn.setObjectName('GhostBtn')
        self.next_btn.setFixedWidth(52)
        self.next_btn.clicked.connect(lambda: self.step_photo(1))
        image_row.addWidget(self.next_btn, 0, Qt.AlignVCenter)
        outer.addLayout(image_row, 1)

        self.caption = QLabel('')
        self.caption.setObjectName('PanelSubtle')
        self.caption.setWordWrap(True)
        outer.addWidget(self.caption)

        self.thumb_row = QHBoxLayout()
        self.thumb_row.setSpacing(8)
        outer.addLayout(self.thumb_row)
        self.root.addWidget(shell)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.close_btn = QPushButton('Zav??t')
        self.close_btn.setObjectName('GhostBtn')
        self.close_btn.clicked.connect(self.accept)
        actions.addWidget(self.close_btn)
        self.root.addLayout(actions)

        self._render_thumb_strip()
        self.refresh_view()

    def _render_thumb_strip(self):
        while self.thumb_row.count():
            item = self.thumb_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for idx, photo in enumerate(self.photos[:6]):
            thumb = QPushButton()
            thumb.setObjectName('GhostBtn')
            thumb.setFixedSize(96, 72)
            pixmap = load_preview_pixmap(row_get(photo, 'path', ''), 84, 58)
            if not pixmap.isNull():
                thumb.setIcon(QIcon(pixmap))
                thumb.setIconSize(QSize(84, 58))
            thumb.clicked.connect(lambda _=False, value=idx: self.set_index(value))
            self.thumb_row.addWidget(thumb)
        self.thumb_row.addStretch(1)

    def set_index(self, index: int):
        if not self.photos:
            return
        self.index = max(0, min(index, len(self.photos) - 1))
        self.refresh_view()

    def step_photo(self, delta: int):
        if not self.photos:
            return
        self.index = (self.index + delta) % len(self.photos)
        self.refresh_view()

    def refresh_view(self):
        if not self.photos:
            self.photo_title.setText('Bez fotek')
            self.caption.setText('K tomuto záznamu zatím nejsou přidané žádné fotografie.')
            self.image.clear()
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            self.open_external_btn.setEnabled(False)
            return
        photo = self.photos[self.index]
        path = str(row_get(photo, 'path', ''))
        caption = str(row_get(photo, 'caption') or Path(path).name)
        self.photo_title.setText(f'{caption} ({self.index + 1}/{len(self.photos)})')
        self.caption.setText(path)
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.image.setText('Náhled není k dispozici.')
        else:
            scaled = pixmap.scaled(self.image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image.setPixmap(scaled)
        enabled = len(self.photos) > 1
        self.prev_btn.setEnabled(enabled)
        self.next_btn.setEnabled(enabled)
        self.open_external_btn.setEnabled(Path(path).exists())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_view()

    def open_current_external(self):
        if not self.photos:
            return
        path = str(row_get(self.photos[self.index], 'path', ''))
        if path and Path(path).exists():
            os.startfile(path)


def dashboard_tooltip_html(title: str, lines: list[str], empty_text: str = 'Bez položek.') -> str:
    safe_lines = [html.escape(str(line or '').strip()) for line in lines if str(line or '').strip()]
    content = '<br>'.join(f'• {line}' for line in safe_lines[:8]) if safe_lines else html.escape(empty_text)
    extra = ''
    if len(safe_lines) > 8:
        extra = f"<br><span style='color:{MUTED};'>… a další {len(safe_lines) - 8}</span>"
    return (
        f"<div style='min-width:320px;'>"
        f"<div style='font-weight:700; margin-bottom:6px;'>{html.escape(title)}</div>"
        f"<div>{content}{extra}</div>"
        f"</div>"
    )


class HoverPreview(QFrame):
    _active: 'HoverPreview | None' = None

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setObjectName('Panel')
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet(
            f"QFrame {{ background:{PANEL}; border:1px solid {GRID}; border-radius:16px; }}"
            f"QLabel {{ color:{TEXT}; background:transparent; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)
        self.title = QLabel('')
        self.title.setStyleSheet('font-size:13px; font-weight:700;')
        lay.addWidget(self.title)
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f'background:{GRID}; border:0;')
        lay.addWidget(divider)
        self.body = QLabel('')
        self.body.setWordWrap(True)
        self.body.setTextFormat(Qt.RichText)
        self.body.setStyleSheet(f'font-size:12px; line-height:1.45; color:{TEXT};')
        lay.addWidget(self.body)
        self.note = QLabel('')
        self.note.setStyleSheet(f'font-size:11px; color:{MUTED};')
        self.note.hide()
        lay.addWidget(self.note)
        self.setFixedWidth(360)

    @classmethod
    def show_for(cls, widget: QWidget, title: str, lines: list[str], empty_text: str):
        if cls._active is None:
            cls._active = HoverPreview()
        cls._active._show(widget, title, lines, empty_text)

    @classmethod
    def hide_active(cls):
        if cls._active is not None:
            cls._active.hide()

    def _show(self, widget: QWidget, title: str, lines: list[str], empty_text: str):
        safe_lines = [html.escape(str(line or '').strip()) for line in lines if str(line or '').strip()]
        visible_lines = safe_lines[:8]
        self.title.setText(html.escape(title))
        if visible_lines:
            self.body.setText('<br>'.join(f'• {line}' for line in visible_lines))
            remaining = len(safe_lines) - len(visible_lines)
            if remaining > 0:
                self.note.setText(f'… a další {remaining}')
                self.note.show()
            else:
                self.note.hide()
        else:
            self.body.setText(html.escape(empty_text))
            self.note.hide()
        self.adjustSize()
        target = widget.mapToGlobal(QPoint(widget.width() + 10, 0))
        screen = QApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            if target.x() + self.width() > available.right() - 12:
                target.setX(widget.mapToGlobal(QPoint(-self.width() - 10, 0)).x())
            if target.y() + self.height() > available.bottom() - 12:
                target.setY(max(available.top() + 12, available.bottom() - self.height() - 12))
        self.move(target)
        self.show()
        self.raise_()


def status_badge_stylesheet(value: Any) -> str:
    tone = status_tone(value)
    if not tone:
        return ''
    bg = soft_tone(tone, 52)
    return (
        f"background:{bg.name(QColor.HexArgb)};"
        f"border:1px solid {tone};"
        f"padding:6px 10px;"
        f"border-radius:12px;"
        f"color:{tone};"
        f"font-size:12px;"
        f"font-weight:700;"
    )


def iter_days(start_value: Any, end_value: Any):
    start = parse_iso_date(start_value)
    end = parse_iso_date(end_value) or start
    if start is None:
        return
    if end is None or end < start:
        end = start
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def center_dialog(parent: QWidget, dlg: QDialog):
    if parent is None:
        return
    geo = parent.frameGeometry()
    dlg_geo = dlg.frameGeometry()
    dlg_geo.moveCenter(geo.center())
    dlg.move(dlg_geo.topLeft())


def status_tone(value: Any) -> str:
    txt = str(value or '').strip().lower()
    if txt in {'volný', 'dostupný', 'aktivní', 'vráceno', 'hotovo', 'uhrazeno', 'ok'}:
        return GOOD
    if txt in {'rezervace', 'potvrzeno', 'čeká', 'čekající', 'po termínu', 'servis', 'upozornění'}:
        return WARN
    if txt in {'půjčený', 'aktivní smlouva', 'aktivní rezervace'}:
        return ACCENT_2
    if txt in {'neuhrazeno', 'blokovaný', 'vyřazený', 'zrušeno', 'problém'}:
        return BAD
    return ''


def contains_status_column(header: str) -> bool:
    h = str(header).lower()
    return any(x in h for x in ['stav', 'status'])


def contains_money_hint(header: str) -> bool:
    h = str(header or '').strip().lower()
    return any(token in h for token in ['cena', 'castka', 'částka', 'kauce', 'doplatek', 'dluh', 'uhrazeno', 'celkem', 'obrat'])


def contains_numeric_hint(header: str) -> bool:
    h = str(header or '').strip().lower()
    return any(token in h for token in ['pocet', 'počet', 'ks', 'kus', 'dni', 'dnů', 'dny', 'id'])


def resolve_table_alignment(header: str, value: Any, is_status: bool) -> Qt.AlignmentFlag:
    if is_status:
        return Qt.AlignCenter
    if contains_money_hint(header) or contains_numeric_hint(header):
        return Qt.AlignRight | Qt.AlignVCenter
    if contains_date_hint(header):
        return Qt.AlignCenter
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Qt.AlignRight | Qt.AlignVCenter
    return Qt.AlignLeft | Qt.AlignVCenter


def soft_tone(color: str, alpha: int = 52) -> QColor:
    q = QColor(color)
    q.setAlpha(alpha)
    return q


def enable_smooth_scroll(widget: QWidget):
    if isinstance(widget, QAbstractItemView):
        widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        widget.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    if isinstance(widget, QAbstractScrollArea):
        widget.verticalScrollBar().setSingleStep(18)
        widget.horizontalScrollBar().setSingleStep(18)
        target = widget.viewport()
    else:
        target = widget
    try:
        QScroller.grabGesture(target, QScroller.TouchGesture)
    except Exception:
        pass


def normalize_font_point_size(font, fallback: int = 10):
    font = QFont(font)
    if font.pointSize() > 0:
        return font
    if font.pixelSize() > 0:
        # Qt can return pointSize() == -1 for pixel-sized fonts.
        # Convert the pixel size into a usable point size once so later
        # font operations do not trip over an invalid point size.
        point_size = max(1, round(font.pixelSize() * 72 / 96))
        font.setPointSize(point_size)
        return font
    font.setPointSize(fallback)
    return font


def ensure_valid_font(item: QTableWidgetItem):
    return normalize_font_point_size(item.font())


def normalize_widget_font(widget: QWidget, fallback: int = 10):
    try:
        widget.setFont(normalize_font_point_size(widget.font(), fallback))
    except Exception:
        pass


class AppInstanceGuard:
    def __init__(self, lock_path: Path, stale_after_seconds: int = 180):
        self.lock_path = Path(lock_path)
        self.stale_after_seconds = stale_after_seconds
        self.owner = {
            'machine': socket.gethostname(),
            'user': getpass.getuser(),
            'pid': os.getpid(),
            'started_at': datetime.now().isoformat(timespec='seconds'),
        }
        self._owned = False

    def _build_payload(self) -> dict[str, Any]:
        payload = dict(self.owner)
        payload['heartbeat_at'] = datetime.now().isoformat(timespec='seconds')
        return payload

    def _read_payload(self) -> dict[str, Any] | None:
        try:
            return json.loads(self.lock_path.read_text(encoding='utf-8'))
        except Exception:
            return None

    def _write_payload(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.write_text(json.dumps(self._build_payload(), ensure_ascii=True, indent=2), encoding='utf-8')

    def _is_stale(self, payload: dict[str, Any] | None) -> bool:
        if not payload:
            return True
        heartbeat_raw = str(payload.get('heartbeat_at') or '').strip()
        if not heartbeat_raw:
            return True
        try:
            heartbeat = datetime.fromisoformat(heartbeat_raw)
        except ValueError:
            return True
        return (datetime.now() - heartbeat).total_seconds() > self.stale_after_seconds

    def _same_owner(self, payload: dict[str, Any] | None) -> bool:
        if not payload:
            return False
        return (
            str(payload.get('machine') or '') == self.owner['machine']
            and str(payload.get('user') or '') == self.owner['user']
            and int(payload.get('pid') or 0) == int(self.owner['pid'])
        )

    def acquire(self) -> tuple[bool, dict[str, Any] | None]:
        existing = self._read_payload()
        if existing and not self._is_stale(existing) and not self._same_owner(existing):
            return False, existing
        self._write_payload()
        self._owned = True
        return True, None

    def heartbeat(self):
        if not self._owned:
            return
        try:
            self._write_payload()
        except Exception:
            pass

    def release(self):
        if not self._owned:
            return
        try:
            existing = self._read_payload()
            if self._same_owner(existing):
                self.lock_path.unlink(missing_ok=True)
        except Exception:
            pass
        self._owned = False


def setup_date_edit(widget: QDateEdit):
    widget.setCalendarPopup(True)
    widget.setDisplayFormat('dd.MM.yyyy')
    widget.setButtonSymbols(QAbstractSpinBox.NoButtons)
    widget.setMinimumWidth(132)


def open_date_popup(widget: QDateEdit):
    def _show():
        try:
            widget.setFocus(Qt.MouseFocusReason)
            widget.showCalendarPopup()
        except Exception:
            pass
    QTimer.singleShot(0, _show)


def make_date_field(widget: QDateEdit) -> QWidget:
    wrap = QWidget()
    lay = QHBoxLayout(wrap)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    lay.addWidget(widget, 1)
    btn = QPushButton('📅')
    btn.setObjectName('CalendarBtn')
    btn.setFocusPolicy(Qt.NoFocus)
    btn.setToolTip('Otevřít kalendář')
    btn.clicked.connect(lambda *_: open_date_popup(widget))
    lay.addWidget(btn)
    return wrap


def make_date_range_field(start_widget: QDateEdit, end_widget: QDateEdit) -> QWidget:
    wrap = QWidget()
    lay = QHBoxLayout(wrap)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)
    lay.addWidget(start_widget, 1)
    start_btn = QPushButton('📅')
    start_btn.setObjectName('CalendarBtn')
    start_btn.setFocusPolicy(Qt.NoFocus)
    start_btn.setToolTip('Vybrat datum od')
    start_btn.clicked.connect(lambda *_: open_date_popup(start_widget))
    lay.addWidget(start_btn)
    arrow = QLabel('→')
    arrow.setObjectName('HintMuted')
    lay.addWidget(arrow)
    lay.addWidget(end_widget, 1)
    end_btn = QPushButton('📅')
    end_btn.setObjectName('CalendarBtn')
    end_btn.setFocusPolicy(Qt.NoFocus)
    end_btn.setToolTip('Vybrat datum do')
    end_btn.clicked.connect(lambda *_: open_date_popup(end_widget))
    lay.addWidget(end_btn)
    return wrap


class FadeMixin:
    def fade_in(self, duration: int = 180):
        eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(eff)
        self._fade_anim = QPropertyAnimation(eff, b'opacity', self)
        self._fade_anim.setDuration(duration)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.start()


class Toast(QFrame, FadeMixin):
    def __init__(self, parent: QWidget, text: str, tone: str = 'info'):
        super().__init__(parent)
        self.setObjectName('Toast')
        tone_color = {'info': ACCENT_2, 'ok': GOOD, 'warn': WARN, 'bad': BAD}.get(tone, ACCENT_2)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        bar = QFrame()
        bar.setFixedWidth(4)
        bar.setStyleSheet(f'background:{tone_color};')
        layout.addWidget(bar)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        layout.addWidget(lbl, 1)
        self.resize(360, 62)
        self.fade_in(140)
        QTimer.singleShot(2600, self.fade_out)

    def fade_out(self):
        eff = self.graphicsEffect()
        if not eff:
            self.deleteLater()
            return
        self._fade_anim = QPropertyAnimation(eff, b'opacity', self)
        self._fade_anim.setDuration(220)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self.deleteLater)
        self._fade_anim.start()


class StartupSplash(QDialog):
    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(False)
        self.resize(420, 260)

        shell = QFrame(self)
        shell.setObjectName('Panel')
        shell.setGeometry(0, 0, self.width(), self.height())
        shell.setStyleSheet(f'background:{PANEL}; border:1px solid {GRID}; border-radius:24px;')

        lay = QVBoxLayout(shell)
        lay.setContentsMargins(28, 28, 28, 28)
        lay.setSpacing(12)

        self.icon_wrap = QLabel()
        self.icon_wrap.setAlignment(Qt.AlignCenter)
        self.icon_wrap.setMinimumHeight(104)
        if APP_ICON_PATH.exists():
            self.icon_pixmap = QPixmap(str(APP_ICON_PATH))
        else:
            self.icon_pixmap = QPixmap()
        self._icon_size = 72
        self._set_icon_size(self._icon_size)
        lay.addWidget(self.icon_wrap, 0, Qt.AlignCenter)

        title = QLabel('P\u016fj\u010dovna stroj\u016f')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 28px; font-weight: 700; color: #f4f7fb;')
        lay.addWidget(title)

        subtitle = QLabel('Na\u010d\u00edt\u00e1m aplikaci a p\u0159ipravuji data...')
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet('font-size: 13px; color: #95a1b3;')
        lay.addWidget(subtitle)

        line = QFrame()
        line.setFixedHeight(6)
        line.setStyleSheet(f'background:{PANEL_3}; border-radius:3px;')
        line_l = QVBoxLayout(line)
        line_l.setContentsMargins(0, 0, 0, 0)
        self.line_fill = QFrame()
        self.line_fill.setStyleSheet(f'background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_2}); border-radius:3px;')
        self.line_fill.setMaximumWidth(0)
        line_l.addWidget(self.line_fill)
        lay.addWidget(line)

    def _set_icon_size(self, size: int):
        if self.icon_pixmap.isNull():
            self.icon_wrap.clear()
            return
        pix = self.icon_pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.icon_wrap.setPixmap(pix)

    def show_centered(self):
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(geo.center() - self.rect().center())
        self.show()
        QApplication.processEvents()

    def play(self, minimum_ms: int = 1100):
        self.show_centered()
        self.icon_anim = QPropertyAnimation(self, b'iconSize', self)
        self.icon_anim.setDuration(650)
        self.icon_anim.setStartValue(56)
        self.icon_anim.setEndValue(84)
        self.icon_anim.setEasingCurve(QEasingCurve.OutBack)
        self.icon_anim.start()

        self.opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity)
        self.fade_anim = QPropertyAnimation(self.opacity, b'opacity', self)
        self.fade_anim.setDuration(320)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.fade_anim.start()

        self.line_anim = QPropertyAnimation(self.line_fill, b'maximumWidth', self)
        self.line_anim.setDuration(820)
        self.line_anim.setStartValue(0)
        self.line_anim.setEndValue(360)
        self.line_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.line_anim.start()

        loop = QEventLoop()
        QTimer.singleShot(minimum_ms, loop.quit)
        loop.exec()

    def finish(self):
        if self.graphicsEffect() is None:
            self.close()
            return
        self.finish_anim = QPropertyAnimation(self.graphicsEffect(), b'opacity', self)
        self.finish_anim.setDuration(220)
        self.finish_anim.setStartValue(1.0)
        self.finish_anim.setEndValue(0.0)
        self.finish_anim.setEasingCurve(QEasingCurve.InCubic)
        self.finish_anim.finished.connect(self.close)
        self.finish_anim.start()

    def getIconSize(self):
        return self._icon_size

    def setIconSize(self, value):
        self._icon_size = int(value)
        self._set_icon_size(self._icon_size)

    iconSize = Property(int, getIconSize, setIconSize)


class CountLabel(QLabel):
    def __init__(self, text='0'):
        super().__init__(text)
        self._value = 0.0
        self._suffix = ''

    def getValue(self):
        return self._value

    def setValue(self, v):
        self._value = v
        if abs(v - round(v)) < 0.001:
            txt = str(int(round(v)))
        else:
            txt = f'{v:.1f}'
        self.setText(txt + self._suffix)

    value = Property(float, getValue, setValue)

    def animate_to(self, target: float, suffix: str = ''):
        self._suffix = suffix
        anim = QPropertyAnimation(self, b'value', self)
        anim.setDuration(550)
        anim.setStartValue(0)
        anim.setEndValue(float(target or 0))
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        self._anim = anim


class ClickableDateEdit(QDateEdit):
    def _open_calendar_popup(self):
        open_date_popup(self)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self._open_calendar_popup()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        QTimer.singleShot(0, self._open_calendar_popup)


class StatCard(QFrame):
    def __init__(self, title: str, accent: str = ACCENT):
        super().__init__()
        self.setObjectName('StatCard')
        self.setFixedHeight(128)
        self._title = title
        self._empty_tooltip = 'Momentalne bez polozek.'
        self._hover_lines: list[str] = []
        self._showing_preview = False
        self._swap_timer = QTimer(self)
        self._swap_timer.setSingleShot(True)
        self._swap_timer.timeout.connect(self._apply_pending_preview_mode)
        self._pending_preview_mode = False
        self.setToolTip('')
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)
        top = QHBoxLayout()
        top.setSpacing(8)
        badge = QFrame()
        badge.setFixedSize(12, 12)
        badge.setStyleSheet(f'background:{accent}; border-radius:6px;')
        top.addWidget(badge)
        ttl = QLabel(title)
        ttl.setObjectName('CardSubtle')
        top.addWidget(ttl)
        top.addStretch(1)
        lay.addLayout(top)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet('background: transparent; border: 0;')
        lay.addWidget(self.stack, 1)

        self.front = QWidget()
        front_lay = QVBoxLayout(self.front)
        front_lay.setContentsMargins(0, 0, 0, 0)
        front_lay.setSpacing(4)
        front_lay.addStretch(1)
        self.value = CountLabel('0')
        self.value.setObjectName('CardValue')
        front_lay.addWidget(self.value)
        self.sub = QLabel('')
        self.sub.setObjectName('CardSubtle')
        self.sub.setWordWrap(False)
        self.sub.setMaximumHeight(18)
        front_lay.addWidget(self.sub)
        front_lay.addStretch(1)

        self.back = QWidget()
        back_lay = QVBoxLayout(self.back)
        back_lay.setContentsMargins(0, 2, 0, 0)
        back_lay.setSpacing(4)
        self.preview = QLabel('')
        self.preview.setWordWrap(True)
        self.preview.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.preview.setStyleSheet(f'color:{TEXT}; font-size:12px; line-height:1.35;')
        back_lay.addWidget(self.preview, 1)

        self.stack.addWidget(self.front)
        self.stack.addWidget(self.back)
        self.stack.setCurrentWidget(self.front)

    def set_data(self, value: float | int, subtitle: str = '', suffix: str = ''):
        self.value.animate_to(float(value or 0), suffix)
        self.sub.setText(subtitle)

    def set_hover_items(self, lines: list[str], empty_text: str | None = None):
        self._empty_tooltip = empty_text or self._empty_tooltip
        self._hover_lines = [str(line or '').strip() for line in lines if str(line or '').strip()]
        self.setToolTip('')
        visible = self._hover_lines[:3]
        if visible:
            text = '\n'.join(f'- {line}' for line in visible)
            if len(self._hover_lines) > len(visible):
                text += f"\n... a dalsi {len(self._hover_lines) - len(visible)}"
        else:
            text = self._empty_tooltip
        self.preview.setText(text)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.setToolTip('')
        self._set_preview_mode(True)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._set_preview_mode(False)

    def _set_preview_mode(self, preview_mode: bool):
        if self._showing_preview == preview_mode:
            return
        self._pending_preview_mode = preview_mode
        self._swap_timer.start(70)

    def _apply_pending_preview_mode(self):
        self._showing_preview = self._pending_preview_mode
        self.stack.setCurrentWidget(self.back if self._showing_preview else self.front)

class Panel(QFrame):
    def __init__(self, title: str, subtitle: str = ''):
        super().__init__()
        self.setObjectName('Panel')
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        h = QHBoxLayout()
        ttl = QLabel(title); ttl.setObjectName('PanelTitle'); h.addWidget(ttl)
        h.addStretch(1)
        lay.addLayout(h)
        if subtitle:
            s = QLabel(subtitle); s.setObjectName('PanelSubtle'); s.setWordWrap(True); lay.addWidget(s)
        self.content = QVBoxLayout(); self.content.setSpacing(6)
        lay.addLayout(self.content, 1)

class ActionList(Panel):
    def __init__(self, title: str, subtitle: str = ''):
        super().__init__(title, subtitle)
        self.list = QListWidget()
        self.list.setObjectName('ActionList')
        self.list.setSpacing(2)
        enable_smooth_scroll(self.list)
        self.content.addWidget(self.list)

    def clear_items(self):
        self.list.clear()

    def add_item(self, title: str, subtitle: str = '', item_id: int | None = None, kind: str = 'contract', tone: str = ACCENT_2):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, {'id': item_id, 'kind': kind})
        w = QFrame()
        w.setObjectName('ActionItem')
        l = QVBoxLayout(w)
        l.setContentsMargins(8, 6, 8, 6)
        l.setSpacing(2)
        row = QHBoxLayout()
        row.setSpacing(5)
        dot = QFrame(); dot.setFixedSize(10, 10); dot.setStyleSheet(f'background:{tone}; border-radius:5px;')
        row.addWidget(dot)
        ttl = QLabel(title); ttl.setObjectName('ActionTitle'); row.addWidget(ttl)
        row.addStretch(1)
        l.addLayout(row)
        if subtitle:
            sub = QLabel(subtitle); sub.setObjectName('ActionSub'); sub.setWordWrap(True); l.addWidget(sub)
        item.setSizeHint(w.sizeHint())
        self.list.addItem(item)
        self.list.setItemWidget(item, w)


class MiniBarChart(QFrame):
    def __init__(self, title: str, accent: str = ACCENT, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName('Panel')
        self._accent = accent
        self._suffix = ''
        self._range_change_handler = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        header = QHBoxLayout()
        header.setSpacing(10)
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        self.title = QLabel(title); self.title.setObjectName('PanelTitle')
        self.subtitle = QLabel(''); self.subtitle.setObjectName('PanelSubtle'); self.subtitle.setWordWrap(True)
        title_box.addWidget(self.title)
        title_box.addWidget(self.subtitle)
        header.addLayout(title_box, 1)
        self.summary = QLabel('')
        self.summary.setObjectName('CardSubtle')
        self.summary.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self.summary)
        self.range_filter = QComboBox()
        self.range_filter.setMinimumWidth(118)
        self.range_filter.hide()
        header.addWidget(self.range_filter)
        self.canvas = _MiniBarCanvas(accent)
        lay.addLayout(header)
        lay.addWidget(self.canvas, 1)
        self.setMinimumHeight(232)

    def set_filter_options(self, options: list[tuple[str, str]], current_key: str, on_change):
        self.range_filter.blockSignals(True)
        self.range_filter.clear()
        for key, label in options:
            self.range_filter.addItem(label, key)
        idx = self.range_filter.findData(current_key)
        if idx >= 0:
            self.range_filter.setCurrentIndex(idx)
        self.range_filter.blockSignals(False)
        if self._range_change_handler is not None:
            try:
                self.range_filter.currentIndexChanged.disconnect(self._range_change_handler)
            except Exception:
                pass
        self._range_change_handler = on_change
        self.range_filter.currentIndexChanged.connect(self._range_change_handler)
        self.range_filter.setVisible(bool(options))

    def current_filter_key(self, fallback: str) -> str:
        return str(self.range_filter.currentData() or fallback)

    def set_data(self, items: list[tuple[str, float]], subtitle: str = '', suffix: str = '', summary: str = ''):
        self._suffix = suffix
        self.subtitle.setText(subtitle)
        self.summary.setText(summary)
        self.canvas.set_data(items, suffix)


class _MiniBarCanvas(QWidget):
    def __init__(self, accent: str):
        super().__init__()
        self.accent = accent
        self.data: list[tuple[str, float]] = []
        self.suffix = ''
        self.setMinimumHeight(170)

    def set_data(self, data: list[tuple[str, float]], suffix: str = ''):
        self.data = data
        self.suffix = suffix
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(12, 18, -12, -30)
        if not self.data:
            p.setPen(QColor(MUTED))
            p.drawText(self.rect(), Qt.AlignCenter, 'Zatím nejsou data')
            return
        maxv = max((v for _, v in self.data), default=1) or 1
        n = len(self.data)
        gap = 12
        bar_w = max(14, int((r.width() - (n - 1) * gap) / max(1, n)))
        p.setPen(QColor(soft_tone(MUTED, 64)))
        for step in range(4):
            y = r.top() + int((r.height() / 3) * step)
            p.drawLine(r.left(), y, r.right(), y)
        for i, (label, value) in enumerate(self.data):
            x = r.left() + i * (bar_w + gap)
            h = int((float(value) / maxv) * max(22, r.height() - 34))
            base_y = r.bottom() - h
            p.setPen(Qt.NoPen)
            p.setBrush(soft_tone(MUTED, 28))
            p.drawRoundedRect(x, r.top() + 6, bar_w, r.height() - 6, 7, 7)
            p.setBrush(QColor(self.accent))
            p.drawRoundedRect(x, base_y, bar_w, h, 7, 7)
            p.setPen(QColor(TEXT))
            p.drawText(x - 10, max(r.top() + 4, base_y - 18), bar_w + 20, 14, Qt.AlignCenter, f"{int(round(value))}{self.suffix}")
            p.setPen(QColor(MUTED))
            p.drawText(x - 10, r.bottom() + 10, bar_w + 20, 14, Qt.AlignHCenter | Qt.AlignTop, label[:7])


class AgendaCalendar(Panel):
    def __init__(self, title: str = 'Kalendář a agenda'):
        super().__init__(title, 'Plán na vybraný den')
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.content.addWidget(self.calendar)
        self.list = QListWidget(); self.list.setObjectName('ActionList')
        enable_smooth_scroll(self.list)
        self.content.addWidget(self.list)

    def set_items(self, selected: QDate, items: list[tuple[str, str, dict]]):
        self.calendar.setSelectedDate(selected)
        self.list.clear()
        for title, subtitle, payload in items:
            it = QListWidgetItem()
            it.setData(Qt.UserRole, payload)
            row = QFrame(); row.setObjectName('ActionItem')
            rl = QVBoxLayout(row); rl.setContentsMargins(8, 6, 8, 6); rl.setSpacing(2)
            t = QLabel(title); t.setObjectName('ActionTitle')
            s = QLabel(subtitle); s.setObjectName('ActionSub'); s.setWordWrap(True)
            rl.addWidget(t); rl.addWidget(s)
            it.setSizeHint(row.sizeHint())
            self.list.addItem(it)
            self.list.setItemWidget(it, row)


class ReservationAgendaCalendar(AgendaCalendar):
    def __init__(self, title: str = 'Rezervacni kalendar'):
        super().__init__(title)
        self._marked_dates: list[QDate] = []
        self.legend = QLabel('Oranzova = rezervace, modra = vypujcka, cervena = vice akci ve stejnem dni.')
        self.legend.setObjectName('PanelSubtle')
        self.legend.setWordWrap(True)
        self.content.insertWidget(1, self.legend)

    def set_day_markers(self, markers: dict[str, set[str]]):
        for qdate in self._marked_dates:
            self.calendar.setDateTextFormat(qdate, QTextCharFormat())
        self._marked_dates = []
        for day_str, kinds in markers.items():
            dt = parse_iso_date(day_str)
            if dt is None:
                continue
            qdate = QDate(dt.year, dt.month, dt.day)
            fmt = QTextCharFormat()
            fmt.setFontWeight(700)
            color = BAD if len(kinds) > 1 else (WARN if 'reservation' in kinds else ACCENT_2)
            fmt.setBackground(QBrush(soft_tone(color, 88)))
            fmt.setForeground(QBrush(QColor(TEXT)))
            self.calendar.setDateTextFormat(qdate, fmt)
            self._marked_dates.append(qdate)


AgendaCalendar = ReservationAgendaCalendar


class AnimatedDialog(QDialog, FadeMixin):
    saved = Signal()
    def __init__(self, parent: QWidget, title: str, width: int = 980, height: int = 780):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._initial_width = width
        self._initial_height = height
        self._content_fit_done = False
        self.resize(width, height)
        self.setModal(True)
        self.setMinimumSize(max(900, int(width * 0.9)), max(700, int(height * 0.88)))
        self.setObjectName('Dialog')
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0,0,0,0)
        self.root.setSpacing(0)
        header = QFrame(); header.setObjectName('DialogHeader')
        hh = QHBoxLayout(header); hh.setContentsMargins(18, 16, 18, 16)
        self.title_lbl = QLabel(title); self.title_lbl.setObjectName('DialogTitle')
        hh.addWidget(self.title_lbl)
        hh.addStretch(1)
        self.header_actions = QHBoxLayout()
        self.header_actions.setSpacing(8)
        hh.addLayout(self.header_actions)
        self.save_btn = QPushButton('Uložit'); self.save_btn.setObjectName('PrimaryBtn')
        self.cancel_btn = QPushButton('Zavřít'); self.cancel_btn.setObjectName('GhostBtn')
        self.cancel_btn.clicked.connect(self.reject)
        hh.addWidget(self.cancel_btn); hh.addWidget(self.save_btn)
        self.root.addWidget(header)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QScrollArea.NoFrame)
        enable_smooth_scroll(self.scroll)
        self.body = QWidget(); self.body_l = QVBoxLayout(self.body); self.body_l.setContentsMargins(18,18,18,18); self.body_l.setSpacing(16)
        self.scroll.setWidget(self.body)
        self.root.addWidget(self.scroll, 1)
        center_dialog(parent, self)
        self.fade_in(160)

    def clear_header_actions(self):
        while self.header_actions.count():
            item = self.header_actions.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def add_header_action(self, text: str, callback, object_name: str = 'GhostBtn') -> QPushButton:
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.clicked.connect(callback)
        self.header_actions.addWidget(button)
        return button

    def showEvent(self, event):
        super().showEvent(event)
        if not self._content_fit_done:
            self._content_fit_done = True
            QTimer.singleShot(0, self.fit_to_content)

    def fit_to_content(self):
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        max_width = max(960, available.width() - 80)
        max_height = max(720, available.height() - 80)
        hint = self.sizeHint().expandedTo(self.minimumSize())
        body_hint = self.body.sizeHint()
        target_width = max(self._initial_width, hint.width() + 20, body_hint.width() + 80)
        target_height = max(self._initial_height, hint.height() + 20, min(body_hint.height() + 180, max_height))
        self.resize(min(target_width, max_width), min(target_height, max_height))
        center_dialog(self.parentWidget(), self)


class FormGroup(QGroupBox):
    def __init__(self, title: str):
        super().__init__(title)
        self.setObjectName('FormGroup')
        self.form = QFormLayout(self)
        self.form.setContentsMargins(16, 18, 16, 16)
        self.form.setSpacing(12)
        self.form.setLabelAlignment(Qt.AlignLeft)


class SearchDialog(AnimatedDialog):
    def __init__(self, parent: 'MainWindow'):
        super().__init__(parent, 'Globální hledání', 1040, 760)
        self.shell = parent
        self.search = QLineEdit(); self.search.setPlaceholderText('Hledat')
        self.body_l.addWidget(self.search)
        self.tabs = QTabWidget(); self.body_l.addWidget(self.tabs, 1)
        self.tables = {}
        for name in ['Smlouvy', 'Rezervace', 'Zákazníci', 'Stroje']:
            table = parent.make_table([])
            panel = QWidget(); lay = QVBoxLayout(panel); lay.setContentsMargins(0,0,0,0); lay.addWidget(table)
            self.tabs.addTab(panel, name)
            self.tables[name] = table
        self.tables['Smlouvy'].setColumnCount(4); self.tables['Smlouvy'].setHorizontalHeaderLabels(['Číslo','Zákazník','Od','Do'])
        self.tables['Rezervace'].setColumnCount(4); self.tables['Rezervace'].setHorizontalHeaderLabels(['Číslo','Zákazník','Od','Do'])
        self.tables['Zákazníci'].setColumnCount(3); self.tables['Zákazníci'].setHorizontalHeaderLabels(['Jméno','Firma','Telefon'])
        self.tables['Stroje'].setColumnCount(4); self.tables['Stroje'].setHorizontalHeaderLabels(['Stroj','Kategorie','Stav','Cena'])
        self.save_btn.hide(); self.cancel_btn.setText('Zavřít')
        self.search.textChanged.connect(self.refresh)
        for t in self.tables.values():
            t.itemDoubleClicked.connect(self.open_selected)
        self.refresh()

    def refresh(self, term: str = ''):
        if term is None or not isinstance(term, str):
            term = self.search.text()
        elif term == '' and self.search.text().strip():
            term = self.search.text()
        res = self.shell.db.global_search(term.strip(), 12) if term.strip() else {'contracts': [], 'reservations': [], 'customers': [], 'machines': []}
        mapping = {
            'Smlouvy': ('contracts', lambda r: [row_get(r,'contract_number'), row_get(r,'customer_name'), row_get(r,'rental_from'), row_get(r,'rental_to')]),
            'Rezervace': ('reservations', lambda r: [row_get(r,'reservation_number'), row_get(r,'customer_name'), row_get(r,'reserved_from'), row_get(r,'reserved_to')]),
            'Zákazníci': ('customers', lambda r: [row_get(r,'name'), row_get(r,'company'), row_get(r,'phone')]),
            'Stroje': ('machines', lambda r: [row_get(r,'name'), row_get(r,'category'), row_get(r,'status'), fmt_money(row_get(r,'daily_rate'))]),
        }
        for tab_name, (key, fn) in mapping.items():
            rows = [as_dict(r) for r in res.get(key, [])]
            self.shell.fill_table(self.tables[tab_name], [fn(r) for r in rows], [int(row_get(r,'id',0) or 0) for r in rows])

    def open_selected(self):
        table = self.tables[self.tabs.tabText(self.tabs.currentIndex())]
        row_id = self.shell.current_table_id(table)
        if not row_id:
            return
        tab = self.tabs.tabText(self.tabs.currentIndex())
        if tab == 'Smlouvy':
            self.shell.open_contract_detail(row_id)
        elif tab == 'Rezervace':
            self.shell.open_reservation_detail(row_id)
        elif tab == 'Zákazníci':
            self.shell.open_customer_detail(row_id)
        else:
            self.shell.open_machine_detail(row_id)
        self.accept()


class CustomerDialog(AnimatedDialog):
    def __init__(self, shell: 'MainWindow', customer_id: int | None = None):
        super().__init__(shell, 'Zákazník' if customer_id else 'Přidat zákazníka', 1060, 840)
        self.shell = shell
        self.customer_id = customer_id
        self.data = as_dict(shell.db.fetchone('SELECT * FROM customers WHERE id=?', (customer_id,))) if customer_id else {}
        g1 = FormGroup('Základní údaje')
        self.name = QLineEdit(self.data.get('name',''))
        self.company = QLineEdit(self.data.get('company',''))
        self.full_name = QLineEdit(self.data.get('full_name',''))
        self.phone = QLineEdit(self.data.get('phone',''))
        self.email = QLineEdit(self.data.get('email',''))
        self.gico = QLineEdit(self.data.get('ico',''))
        self.dic = QLineEdit(self.data.get('dic',''))
        self.address = QPlainTextEdit(self.data.get('address','')); self.address.setFixedHeight(84)
        for lbl, widget in [('Jméno *', self.name), ('Celé jméno', self.full_name), ('Firma', self.company), ('Telefon', self.phone), ('E-mail', self.email), ('IČO', self.gico), ('DIČ', self.dic), ('Adresa', self.address)]:
            g1.form.addRow(lbl, widget)
        g2 = FormGroup('Doklady a poznámky')
        self.id_card = QLineEdit(self.data.get('id_card',''))
        self.driver = QLineEdit(self.data.get('driver_license',''))
        self.passport = QLineEdit(self.data.get('passport',''))
        self.notes = QPlainTextEdit(self.data.get('notes',''))
        self.notes.setFixedHeight(130)
        for lbl, widget in [('OP', self.id_card), ('ŘP', self.driver), ('Pas', self.passport), ('Poznámka', self.notes)]:
            g2.form.addRow(lbl, widget)
        self.body_l.addWidget(g1); self.body_l.addWidget(g2)
        self.save_btn.clicked.connect(self.save)

    def save(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, 'Chyba', 'Zadej jméno zákazníka.')
            return
        vals = (
            self.name.text().strip(), self.full_name.text().strip(), self.company.text().strip(), self.gico.text().strip(), self.dic.text().strip(),
            self.address.toPlainText().strip(), self.phone.text().strip(), self.email.text().strip(), self.id_card.text().strip(),
            self.driver.text().strip(), self.passport.text().strip(), self.notes.toPlainText().strip()
        )
        if self.customer_id:
            self.shell.db.execute("UPDATE customers SET name=?, full_name=?, company=?, ico=?, dic=?, address=?, phone=?, email=?, id_card=?, driver_license=?, passport=?, notes=? WHERE id=?", vals + (self.customer_id,))
        else:
            self.shell.db.execute("INSERT INTO customers(name, full_name, company, ico, dic, address, phone, email, id_card, driver_license, passport, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", vals)
        self.saved.emit(); self.accept()


class MachineDialog(AnimatedDialog):
    def __init__(self, shell: 'MainWindow', machine_id: int | None = None):
        super().__init__(shell, 'Stroj' if machine_id else 'Přidat stroj', 1280, 940)
        self.shell = shell
        self.machine_id = machine_id
        self.data = as_dict(shell.db.fetchone('SELECT * FROM machines WHERE id=?', (machine_id,))) if machine_id else {}
        settings = shell.db.get_settings()
        categories = [x.strip() for x in settings.get('machine_categories','').replace(';','\n').splitlines() if x.strip()]

        row = QHBoxLayout(); self.body_l.addLayout(row)
        left = QVBoxLayout(); right = QVBoxLayout(); row.addLayout(left, 2); row.addLayout(right, 1)

        g1 = FormGroup('Základní údaje')
        self.name = QLineEdit(self.data.get('name',''))
        self.category = QComboBox(); self.category.setEditable(True); self.category.addItems(categories); self.category.setCurrentText(self.data.get('category',''))
        self.inventory = QLineEdit(self.data.get('inventory_number',''))
        self.model = QLineEdit(self.data.get('model',''))
        self.serial = QLineEdit(self.data.get('serial_number',''))
        self.status = QComboBox(); self.status.addItems(['volný','půjčený','servis','vyřazený']); self.status.setCurrentText(self.data.get('status','volný') or 'volný')
        for lbl, widget in [('Název *', self.name), ('Kategorie', self.category), ('Inventární číslo', self.inventory), ('Model', self.model), ('Sériové číslo', self.serial), ('Stav', self.status)]:
            g1.form.addRow(lbl, widget)
        left.addWidget(g1)

        g2 = FormGroup('Finance a servis')
        self.daily_rate = QLineEdit(str(self.data.get('daily_rate','0') or '0'))
        self.weekend_rate = QLineEdit(str(self.data.get('weekend_rate','0') or '0'))
        self.weekly_rate = QLineEdit(str(self.data.get('weekly_rate','0') or '0'))
        self.monthly_rate = QLineEdit(str(self.data.get('monthly_rate','0') or '0'))
        self.deposit = QLineEdit(str(self.data.get('deposit','0') or '0'))
        self.motohours = QLineEdit(str(self.data.get('motohours','0') or '0'))
        self.last_service = ClickableDateEdit(); setup_date_edit(self.last_service); self._set_date(self.last_service, self.data.get('last_service_date',''))
        self.next_service = ClickableDateEdit(); setup_date_edit(self.next_service); self._set_date(self.next_service, self.data.get('next_service_date',''))
        last_service_wrap = make_date_field(self.last_service)
        next_service_wrap = make_date_field(self.next_service)
        self.service_due_mh = QLineEdit(str(self.data.get('service_due_motohours','0') or '0'))
        for lbl, widget in [('Denní sazba', self.daily_rate), ('Kauce', self.deposit), ('Motohodiny', self.motohours), ('Poslední servis', last_service_wrap), ('Další servis', next_service_wrap), ('Servis při MH', self.service_due_mh)]:
            g2.form.addRow(lbl, widget)
        g2.form.insertRow(1, 'Vikendova sazba', self.weekend_rate)
        g2.form.insertRow(2, 'Tydenni sazba', self.weekly_rate)
        left.addWidget(g2)

        g3 = FormGroup('Příslušenství a poznámka')
        self.accessories = QPlainTextEdit(self.data.get('accessories',''))
        self.notes = QPlainTextEdit(self.data.get('notes',''))
        self.accessories.setFixedHeight(120); self.notes.setFixedHeight(120)
        g3.form.addRow('Příslušenství', self.accessories)
        g3.form.addRow('Poznámka', self.notes)
        left.addWidget(g3)

        photo_group = Panel('Fotky stroje', 'Přidej více fotek a jednu nech jako hlavní.')
        self.photo_list = QListWidget(); photo_group.content.addWidget(self.photo_list)
        self.photo_list.setViewMode(QListWidget.IconMode)
        self.photo_list.setIconSize(QSize(148, 104))
        self.photo_list.setGridSize(QSize(170, 156))
        self.photo_list.setResizeMode(QListWidget.Adjust)
        self.photo_list.setMovement(QListWidget.Static)
        self.photo_list.setWordWrap(True)
        enable_smooth_scroll(self.photo_list)
        pb = QHBoxLayout()
        self.add_photo_btn = QPushButton('Přidat fotku'); self.add_photo_btn.setObjectName('GhostBtn')
        self.del_photo_btn = QPushButton('Smazat fotku'); self.del_photo_btn.setObjectName('GhostBtn')
        self.primary_photo_btn = QPushButton('Nastavit jako hlavní'); self.primary_photo_btn.setObjectName('GhostBtn')
        pb.addWidget(self.add_photo_btn); pb.addWidget(self.primary_photo_btn); pb.addWidget(self.del_photo_btn); pb.addStretch(1)
        photo_group.content.addLayout(pb)
        right.addWidget(photo_group)

        acc_group = Panel('Strukturované příslušenství', 'Položky příslušenství a ceny navíc k textovému poli.')
        self.acc_table = shell.make_table(['Název','Cena'])
        acc_group.content.addWidget(self.acc_table)
        ab = QHBoxLayout();
        self.acc_name = QLineEdit(); self.acc_name.setPlaceholderText('Název příslušenství')
        self.acc_price = QLineEdit(); self.acc_price.setPlaceholderText('Cena')
        self.add_acc_btn = QPushButton('Přidat'); self.add_acc_btn.setObjectName('PrimaryBtn')
        self.del_acc_btn = QPushButton('Smazat'); self.del_acc_btn.setObjectName('GhostBtn')
        ab.addWidget(self.acc_name, 1); ab.addWidget(self.acc_price); ab.addWidget(self.add_acc_btn); ab.addWidget(self.del_acc_btn)
        acc_group.content.addLayout(ab)
        right.addWidget(acc_group, 1)

        self.body_l.addStretch(1)
        self.add_photo_btn.clicked.connect(self.add_photo)
        self.del_photo_btn.clicked.connect(self.delete_photo)
        self.primary_photo_btn.clicked.connect(self.set_primary_photo)
        self.photo_list.itemDoubleClicked.connect(self.open_photo)
        self.add_acc_btn.clicked.connect(self.add_accessory)
        self.del_acc_btn.clicked.connect(self.delete_accessory)
        self.save_btn.clicked.connect(self.save)
        self.refresh_photos(); self.refresh_accessories()

    def _set_date(self, widget: QDateEdit, raw: str):
        if raw:
            try:
                dt = datetime.strptime(raw, '%Y-%m-%d').date()
                widget.setDate(QDate(dt.year, dt.month, dt.day))
                return
            except Exception:
                pass
        widget.setSpecialValueText('')
        widget.setDate(QDate.currentDate())

    def date_text(self, widget: QDateEdit) -> str:
        return widget.date().toPython().strftime('%Y-%m-%d')

    def refresh_photos(self):
        self.photo_list.clear()
        if not self.machine_id:
            return
        photos = [as_dict(r) for r in self.shell.db.get_machine_photos(self.machine_id)]
        for p in photos:
            path = str(row_get(p,'path',''))
            caption = str(row_get(p,'caption') or Path(path).name)
            item = QListWidgetItem(caption)
            pixmap = load_preview_pixmap(path)
            if not pixmap.isNull():
                item.setIcon(QIcon(pixmap))
            item.setToolTip(path)
            item.setData(Qt.UserRole, int(row_get(p,'id',0) or 0))
            item.setData(Qt.UserRole+1, path)
            self.photo_list.addItem(item)

    def open_photo(self, item: QListWidgetItem | None = None):
        item = item or self.photo_list.currentItem()
        if not item:
            return
        photos = [as_dict(r) for r in self.shell.db.get_machine_photos(self.machine_id)] if self.machine_id else []
        path = str(item.data(Qt.UserRole + 1) or '')
        current_index = 0
        for idx, photo in enumerate(photos):
            if str(row_get(photo, 'path', '')) == path:
                current_index = idx
                break
        dlg = PhotoLightboxDialog(self, photos, current_index, 'Fotky stroje')
        dlg.exec()
    def refresh_accessories(self):
        self.acc_table.setColumnCount(2); self.acc_table.setHorizontalHeaderLabels(['Název','Cena'])
        if not self.machine_id:
            self.acc_table.setRowCount(0)
            return
        rows = [as_dict(r) for r in self.shell.db.get_machine_accessories(self.machine_id)]
        self.shell.fill_table(self.acc_table, [[row_get(r,'accessory_name'), fmt_money(row_get(r,'accessory_price'))] for r in rows], [int(row_get(r,'id',0) or 0) for r in rows])

    def add_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Vyber fotku', '', 'Obrázky (*.png *.jpg *.jpeg *.webp)')
        if not path:
            return
        if not self.machine_id:
            QMessageBox.information(self, 'Ulož nejdřív stroj', 'Nejprve ulož stroj, pak můžeš přidat fotky.')
            return
        dst_dir = PHOTOS_DIR / f'machine_{self.machine_id}'
        dst_dir.mkdir(parents=True, exist_ok=True)
        src = Path(path); dst = dst_dir / src.name
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
        self.shell.db.add_machine_photo(self.machine_id, str(dst), src.stem)
        self.refresh_photos()

    def delete_photo(self):
        item = self.photo_list.currentItem()
        if not item:
            return
        self.shell.db.delete_machine_photo(int(item.data(Qt.UserRole)))
        self.refresh_photos()

    def set_primary_photo(self):
        item = self.photo_list.currentItem()
        if not item or not self.machine_id:
            return
        self.shell.db.set_primary_machine_photo(self.machine_id, str(item.data(Qt.UserRole+1)))
        self.shell.toast('Hlavní fotka nastavena.', 'ok')

    def add_accessory(self):
        if not self.machine_id:
            QMessageBox.information(self, 'Ulož nejdřív stroj', 'Nejprve ulož stroj, pak můžeš přidat příslušenství.')
            return
        name = self.acc_name.text().strip()
        if not name:
            return
        self.shell.db.add_machine_accessory(self.machine_id, name, parse_float(self.acc_price.text()))
        self.acc_name.clear(); self.acc_price.clear(); self.refresh_accessories()

    def delete_accessory(self):
        row_id = self.shell.current_table_id(self.acc_table)
        if row_id:
            self.shell.db.delete_machine_accessory(row_id); self.refresh_accessories()

    def save(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, 'Chyba', 'Zadej název stroje.')
            return
        vals = (
            self.name.text().strip(), self.category.currentText().strip(), self.inventory.text().strip(), self.model.text().strip(), self.serial.text().strip(),
            parse_float(self.daily_rate.text()), parse_float(self.weekend_rate.text()), parse_float(self.weekly_rate.text()), parse_float(self.monthly_rate.text()), parse_float(self.deposit.text()), self.status.currentText(), self.notes.toPlainText().strip(),
            self.data.get('photo_path',''), self.accessories.toPlainText().strip(), self.date_text(self.last_service), self.date_text(self.next_service),
            parse_float(self.service_due_mh.text()), parse_float(self.motohours.text())
        )
        if self.machine_id:
            self.shell.db.execute("UPDATE machines SET name=?, category=?, inventory_number=?, model=?, serial_number=?, daily_rate=?, weekend_rate=?, weekly_rate=?, monthly_rate=?, deposit=?, status=?, notes=?, photo_path=?, accessories=?, last_service_date=?, next_service_date=?, service_due_motohours=?, motohours=? WHERE id=?", vals + (self.machine_id,))
            self.shell.db.sync_machine_accessories_from_legacy_text(self.machine_id, self.accessories.toPlainText().strip())
        else:
            self.machine_id = self.shell.db.execute("INSERT INTO machines(name, category, inventory_number, model, serial_number, daily_rate, weekend_rate, weekly_rate, monthly_rate, deposit, status, notes, photo_path, accessories, last_service_date, next_service_date, service_due_motohours, motohours) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", vals)
            self.shell.db.sync_machine_accessories_from_legacy_text(self.machine_id, self.accessories.toPlainText().strip())
        self.saved.emit(); self.accept()


class ServiceDialog(AnimatedDialog):
    def __init__(self, shell: 'MainWindow', record_id: int | None = None, default_machine_id: int | None = None):
        super().__init__(shell, 'Servisní záznam' if record_id else 'Nový servis', 860, 720)
        self.shell = shell
        self.record_id = record_id
        self.data = as_dict(shell.db.fetchone('SELECT * FROM service_records WHERE id=?', (record_id,))) if record_id else {}
        machines = [as_dict(r) for r in shell.db.fetchall('SELECT id, name FROM machines ORDER BY name')]
        g = FormGroup('Servis')
        self.machine = QComboBox()
        for m in machines:
            self.machine.addItem(row_get(m,'name'), int(row_get(m,'id',0) or 0))
        if record_id:
            idx = self.machine.findData(int(self.data.get('machine_id',0) or 0))
            if idx >= 0: self.machine.setCurrentIndex(idx)
        elif default_machine_id:
            idx = self.machine.findData(default_machine_id)
            if idx >= 0: self.machine.setCurrentIndex(idx)
        self.service_date = ClickableDateEdit(); setup_date_edit(self.service_date); self._set_date(self.service_date, self.data.get('service_date', today_str()))
        self.service_type = QLineEdit(self.data.get('service_type',''))
        self.cost = QLineEdit(str(self.data.get('cost','0') or '0'))
        self.provider = QLineEdit(self.data.get('provider',''))
        self.mh = QLineEdit(str(self.data.get('service_motohours','0') or '0'))
        self.next_mh = QLineEdit(str(self.data.get('next_service_motohours','0') or '0'))
        self.next_date = ClickableDateEdit(); setup_date_edit(self.next_date); self._set_date(self.next_date, self.data.get('next_service_date', today_str()))
        service_date_wrap = make_date_field(self.service_date)
        next_date_wrap = make_date_field(self.next_date)
        self.status = QComboBox(); self.status.addItems(['otevřený', 'dokončený']); self.status.setCurrentText(self.data.get('status','otevřený') or 'otevřený')
        self.notes = QPlainTextEdit(self.data.get('notes','')); self.notes.setFixedHeight(180)
        for lbl, widget in [('Stroj *', self.machine), ('Datum', service_date_wrap), ('Typ', self.service_type), ('Cena', self.cost), ('Dodavatel', self.provider), ('MH při servisu', self.mh), ('Další servis MH', self.next_mh), ('Další servis datum', next_date_wrap), ('Stav', self.status), ('Poznámka', self.notes)]:
            g.form.addRow(lbl, widget)
        self.body_l.addWidget(g)
        self.save_btn.clicked.connect(self.save)

    def _set_date(self, widget: QDateEdit, raw: str):
        try:
            dt = datetime.strptime(raw, '%Y-%m-%d').date() if raw else date.today()
        except Exception:
            dt = date.today()
        widget.setDate(QDate(dt.year, dt.month, dt.day))

    def save(self):
        machine_id = self.machine.currentData()
        if not machine_id:
            QMessageBox.warning(self, 'Chyba', 'Vyber stroj.')
            return
        payload = (int(machine_id), self.service_date.date().toPython().strftime('%Y-%m-%d'), self.service_type.text().strip(), parse_float(self.cost.text()), self.provider.text().strip(), self.notes.toPlainText().strip(), self.next_date.date().toPython().strftime('%Y-%m-%d'), parse_float(self.mh.text()), parse_float(self.next_mh.text()))
        if self.record_id:
            self.shell.db.update_service_record(self.record_id, *payload)
            self.shell.db.execute('UPDATE service_records SET status=? WHERE id=?', (self.status.currentText(), self.record_id))
        else:
            rid = self.shell.db.create_service_record(*payload)
            if self.status.currentText() == 'dokončený':
                self.shell.db.finish_service(machine_id, rid)
        self.saved.emit(); self.accept()


class ReservationDialog(AnimatedDialog):
    def __init__(self, shell: 'MainWindow', reservation_id: int | None = None):
        super().__init__(shell, 'Rezervace', 980, 760)
        self.shell = shell
        self.reservation_id = reservation_id
        self.data = as_dict(shell.db.fetchone('SELECT * FROM reservations WHERE id=?', (reservation_id,))) if reservation_id else {}
        customers = [as_dict(r) for r in shell.db.fetchall('SELECT id, name, company FROM customers ORDER BY name')]
        machines = [as_dict(r) for r in shell.db.fetchall("SELECT * FROM machines WHERE status!='vyřazený' ORDER BY name")]
        g = FormGroup('Základ')
        self.customer = QComboBox();
        for c in customers: self.customer.addItem(f"{row_get(c,'name')} · {row_get(c,'company')}", int(row_get(c,'id',0) or 0))
        if reservation_id:
            idx=self.customer.findData(int(self.data.get('customer_id',0) or 0));
            if idx>=0: self.customer.setCurrentIndex(idx)
        self.from_date = ClickableDateEdit(); setup_date_edit(self.from_date); self._set_date(self.from_date, self.data.get('reserved_from', today_str()))
        self.to_date = ClickableDateEdit(); setup_date_edit(self.to_date); self._set_date(self.to_date, self.data.get('reserved_to', today_str()))
        date_range_wrap = make_date_range_field(self.from_date, self.to_date)
        self.total_price = QLineEdit(str(self.data.get('total_price','0') or '0'))
        self.deposit = QLineEdit(str(self.data.get('deposit','0') or '0'))
        self.notes = QPlainTextEdit(self.data.get('notes','')); self.notes.setFixedHeight(120)
        for lbl,w in [('Zákazník', self.customer), ('Období', date_range_wrap), ('Cena', self.total_price), ('Kauce', self.deposit), ('Poznámka', self.notes)]:
            g.form.addRow(lbl,w)
        self.body_l.addWidget(g)
        panel = Panel('Vybrané stroje')
        self.machine_table = shell.make_table(['Stroj','Kategorie','Stav','Cena']); panel.content.addWidget(self.machine_table)
        self.selected = QListWidget(); panel.content.addWidget(self.selected)
        enable_smooth_scroll(self.selected)
        self.body_l.addWidget(panel,1)
        self.machine_rows = machines
        self.selected_ids: set[int] = set()
        if reservation_id:
            for item in shell.db.fetchall('SELECT machine_id FROM reservation_items WHERE reservation_id=?', (reservation_id,)):
                self.selected_ids.add(int(row_get(item,'machine_id',0) or 0))
        self.refresh_machine_table()
        self.machine_table.itemDoubleClicked.connect(lambda *_: self.toggle_machine())
        self.save_btn.clicked.connect(self.save)

    def _set_date(self, widget: QDateEdit, raw: str):
        try:
            dt = datetime.strptime(raw, '%Y-%m-%d').date() if raw else date.today()
        except Exception:
            dt = date.today()
        widget.setDate(QDate(dt.year, dt.month, dt.day))

    def refresh_machine_table(self):
        rows=[]; ids=[]
        for m in self.machine_rows:
            rows.append([row_get(m,'name'), row_get(m,'category'), row_get(m,'status'), fmt_money(row_get(m,'daily_rate'))])
            ids.append(int(row_get(m,'id',0) or 0))
        self.shell.fill_table(self.machine_table, rows, ids)
        self.selected.clear()
        for m in self.machine_rows:
            mid=int(row_get(m,'id',0) or 0)
            if mid in self.selected_ids:
                self.selected.addItem(f"{row_get(m,'name')} · {row_get(m,'category')}")

    def toggle_machine(self):
        row_id=self.shell.current_table_id(self.machine_table)
        if not row_id: return
        if row_id in self.selected_ids: self.selected_ids.remove(row_id)
        else: self.selected_ids.add(row_id)
        self.refresh_machine_table()

    def save(self):
        cid=self.customer.currentData()
        d1=self.from_date.date().toPython().strftime('%Y-%m-%d')
        d2=self.to_date.date().toPython().strftime('%Y-%m-%d')
        if not cid or not self.selected_ids:
            QMessageBox.warning(self,'Chyba','Vyber zákazníka a alespoň jeden stroj.')
            return
        conflicts=[]
        for mid in self.selected_ids:
            conflicts.extend(self.shell.db.check_machine_conflicts(mid, d1, d2))
        if conflicts and QMessageBox.question(self,'Konflikty','Nalezeny konflikty rezervací/smluv. Přesto uložit?\n\n'+'\n'.join(conflicts[:8])) != QMessageBox.Yes:
            return
        if self.reservation_id:
            self.shell.db.execute("UPDATE reservations SET customer_id=?, reserved_from=?, reserved_to=?, total_price=?, deposit=?, notes=? WHERE id=?", (cid,d1,d2,parse_float(self.total_price.text()),parse_float(self.deposit.text()),self.notes.toPlainText().strip(),self.reservation_id))
            self.shell.db.execute('DELETE FROM reservation_items WHERE reservation_id=?',(self.reservation_id,))
            rid=self.reservation_id
        else:
            rid=self.shell.db.execute("INSERT INTO reservations(reservation_number, customer_id, created_at, reserved_from, reserved_to, total_price, deposit, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, 'rezervace', ?)", (self.shell.db.generate_reservation_number(), cid, today_str(), d1,d2,parse_float(self.total_price.text()),parse_float(self.deposit.text()),self.notes.toPlainText().strip()))
        for mid in self.selected_ids:
            self.shell.db.execute('INSERT INTO reservation_items(reservation_id, machine_id) VALUES (?, ?)', (rid, mid))
        self.saved.emit(); self.accept()


class ContractDialog(AnimatedDialog):
    def __init__(self, shell: 'MainWindow'):
        super().__init__(shell, 'Nová smlouva', 1460, 1020)
        self.shell = shell
        customers = [as_dict(r) for r in shell.db.fetchall('SELECT id, name, company FROM customers ORDER BY name')]
        machines = [as_dict(r) for r in shell.db.fetchall("SELECT * FROM machines WHERE status='volný' ORDER BY name")]
        self.machine_rows = machines
        self.selected_ids: set[int] = set()
        self.selected_accessory_ids: set[int] = set()
        self.issue_photo_path = ''

        steps = QHBoxLayout()
        for idx, name in enumerate(['1 · Zákazník', '2 · Stroje', '3 · Cena a kauce', '4 · Uložit']):
            lab = QLabel(name)
            lab.setObjectName('StepChipActive' if idx == 0 else 'StepChip')
            steps.addWidget(lab)
        steps.addStretch(1)
        self.body_l.addLayout(steps)

        self.customer = QComboBox()
        for c in customers:
            label = f"{row_get(c,'name')}" + (f" · {row_get(c,'company')}" if row_get(c,'company') else '')
            self.customer.addItem(label, int(row_get(c,'id',0) or 0))
        self.rental_from = ClickableDateEdit(); setup_date_edit(self.rental_from); self.rental_from.setDate(QDate.currentDate())
        self.rental_to = ClickableDateEdit(); setup_date_edit(self.rental_to); self.rental_to.setDate(QDate.currentDate().addDays(1))
        self.total_price = QLineEdit('0')
        self.deposit = QLineEdit('0')
        self.paid_amount = QLineEdit('0')
        self.pricing_mode = QComboBox()
        self.pricing_mode.addItem('Denni sazba', 'day')
        self.pricing_mode.addItem('Vikendova sazba', 'weekend')
        self.pricing_mode.addItem('Tydenni sazba', 'week')
        self.payment_method = QComboBox(); self.payment_method.addItems(['Hotově','Kartou','Převodem','Nezadáno'])
        self.manual_price = QCheckBox('Ruční cena a kauce')
        self.notes = QPlainTextEdit(); self.notes.setFixedHeight(120)
        self.issue_condition = QPlainTextEdit(); self.issue_condition.setFixedHeight(100)
        self.issue_photo_btn = QPushButton('Vybrat fotku výdeje'); self.issue_photo_btn.setObjectName('GhostBtn')
        self.issue_photo_lbl = QLabel('Bez fotky')
        self.issue_photo_btn.clicked.connect(self.pick_issue_photo)
        photo_wrap = QWidget(); pw = QHBoxLayout(photo_wrap); pw.setContentsMargins(0,0,0,0); pw.addWidget(self.issue_photo_btn); pw.addWidget(self.issue_photo_lbl); pw.addStretch(1)

        summary_panel = QFrame(); summary_panel.setObjectName('DetailStatStrip')
        sg = QGridLayout(summary_panel); sg.setContentsMargins(0,0,0,0); sg.setHorizontalSpacing(12); sg.setVerticalSpacing(12)
        self.sum_selected = QLabel('0'); self.sum_selected.setObjectName('DetailMiniValue')
        self.sum_days = QLabel('1'); self.sum_days.setObjectName('DetailMiniValue')
        self.sum_total = QLabel(fmt_money(0)); self.sum_total.setObjectName('DetailMiniValue')
        self.sum_deposit = QLabel(fmt_money(0)); self.sum_deposit.setObjectName('DetailMiniValue')
        for idx, (label, widget) in enumerate([('Stroje', self.sum_selected), ('Dní', self.sum_days), ('Cena', self.sum_total), ('Kauce', self.sum_deposit)]):
            card = QFrame(); card.setObjectName('DetailMiniCard')
            cl = QVBoxLayout(card); cl.setContentsMargins(14,12,14,12); cl.setSpacing(4)
            l1 = QLabel(label); l1.setObjectName('DetailMiniLabel'); cl.addWidget(l1); cl.addWidget(widget)
            sg.addWidget(card, 0, idx)
        self.body_l.addWidget(summary_panel)

        split = QSplitter(Qt.Horizontal); self.body_l.addWidget(split, 1)
        left_wrap = QWidget(); left = QVBoxLayout(left_wrap); left.setContentsMargins(0,0,0,0); left.setSpacing(16)
        right_wrap = QWidget(); right = QVBoxLayout(right_wrap); right.setContentsMargins(0,0,0,0); right.setSpacing(16)
        split.addWidget(left_wrap); split.addWidget(right_wrap); split.setSizes([930, 440])

        g = FormGroup('Smluvní údaje')
        date_wrap = make_date_range_field(self.rental_from, self.rental_to)
        money_wrap = QWidget(); mw = QHBoxLayout(money_wrap); mw.setContentsMargins(0,0,0,0); mw.addWidget(self.total_price); mw.addWidget(self.deposit)
        for lbl,w in [('Zákazník', self.customer), ('Období', date_wrap), ('Cena / Kauce', money_wrap), ('Uhrazeno', self.paid_amount), ('Platba', self.payment_method), ('Stav při výdeji', self.issue_condition), ('Foto při výdeji', photo_wrap), ('Poznámka', self.notes), ('Režim ceny', self.manual_price)]:
            g.form.addRow(lbl,w)
        g.form.insertRow(2, 'Typ sazby', self.pricing_mode)
        left.addWidget(g)

        panel = Panel('Dostupné stroje')
        self.machine_search = QLineEdit(); self.machine_search.setPlaceholderText('Filtrovat stroje podle názvu nebo kategorie...')
        panel.content.addWidget(self.machine_search)
        self.machine_table = shell.make_table(['Stroj','Kategorie','Cena','Kauce'])
        panel.content.addWidget(self.machine_table)
        row_btn = QHBoxLayout()
        self.add_machine_btn = QPushButton('Přidat / odebrat'); self.add_machine_btn.setObjectName('PrimaryBtn')
        self.remove_machine_btn = QPushButton('Odebrat vybraný'); self.remove_machine_btn.setObjectName('GhostBtn')
        row_btn.addWidget(self.add_machine_btn); row_btn.addWidget(self.remove_machine_btn); row_btn.addStretch(1)
        panel.content.addLayout(row_btn)
        left.addWidget(panel,1)
        self.machine_table.itemDoubleClicked.connect(lambda *_: self.toggle_machine())
        self.machine_search.textChanged.connect(lambda _=None: self.refresh_machine_table())
        self.add_machine_btn.clicked.connect(self.toggle_machine)
        self.remove_machine_btn.clicked.connect(self.remove_selected_machine)

        sel_panel = Panel('Vybrané stroje')
        self.selected = QListWidget(); sel_panel.content.addWidget(self.selected)
        enable_smooth_scroll(self.selected)
        self.selected.itemDoubleClicked.connect(lambda *_: self.remove_selected_machine())
        right.addWidget(sel_panel,1)

        self.accessory_panel = Panel('Příslušenství ke smlouvě', 'Zaškrtni jen položky, které chceš opravdu vydat se strojem.')
        self.accessory_hint = QLabel('Po výběru stroje se tady zobrazí dostupné příslušenství.')
        self.accessory_hint.setObjectName('HintMuted')
        self.accessory_hint.setWordWrap(True)
        self.accessory_list = QListWidget()
        enable_smooth_scroll(self.accessory_list)
        self.accessory_list.itemChanged.connect(lambda *_: self.on_accessory_changed())
        self.accessory_panel.content.addWidget(self.accessory_hint)
        self.accessory_panel.content.addWidget(self.accessory_list)
        right.addWidget(self.accessory_panel, 1)

        self.validation_panel = Panel('Kontrola')
        self.validation_hint = QLabel('Vyber zákazníka a alespoň jeden stroj.')
        self.validation_hint.setObjectName('HintMuted'); self.validation_hint.setWordWrap(True)
        self.conflict_list = QListWidget(); self.conflict_list.setObjectName('ActionList')
        enable_smooth_scroll(self.conflict_list)
        self.validation_panel.content.addWidget(self.validation_hint)
        self.validation_panel.content.addWidget(self.conflict_list)
        right.addWidget(self.validation_panel)

        self.rental_from.dateChanged.connect(self.update_contract_summary)
        self.rental_to.dateChanged.connect(self.update_contract_summary)
        self.pricing_mode.currentIndexChanged.connect(lambda *_: (self.refresh_machine_table(), self.refresh_selected()))
        self.manual_price.toggled.connect(self.update_contract_summary)
        self.customer.currentIndexChanged.connect(self.update_contract_summary)
        self.refresh_machine_table(); self.refresh_selected(); self.update_contract_summary()
        self.save_btn.clicked.connect(self.save)

    def pick_issue_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Vyber fotku', '', 'Obrázky (*.png *.jpg *.jpeg *.webp)')
        if path:
            self.issue_photo_path = path
            self.issue_photo_lbl.setText(Path(path).name)

    def refresh_machine_table(self):
        rows=[]; ids=[]
        term = self.machine_search.text().strip().lower() if hasattr(self, 'machine_search') else ''
        pricing_mode = self.pricing_mode.currentData() if hasattr(self, 'pricing_mode') else 'day'
        for m in self.machine_rows:
            vals=[row_get(m,'name'), row_get(m,'category'), fmt_money(machine_rate_for_mode(m, pricing_mode)), fmt_money(row_get(m,'deposit'))]
            if term and term not in ' '.join(map(str, vals)).lower():
                continue
            rows.append(vals)
            ids.append(int(row_get(m,'id',0) or 0))
        self.shell.fill_table(self.machine_table, rows, ids)

    def refresh_selected(self):
        self.selected.clear()
        for m in self.machine_rows:
            mid=int(row_get(m,'id',0) or 0)
            if mid in self.selected_ids:
                accs=[as_dict(r) for r in self.shell.db.get_machine_accessories(mid)]
                selected_accs=[a for a in accs if int(row_get(a,'id',0) or 0) in self.selected_accessory_ids]
                extra=sum(parse_float(row_get(a,'accessory_price',0)) for a in selected_accs)
                acc_text=', '.join([str(row_get(a,'accessory_name')) for a in selected_accs]) if selected_accs else 'bez příslušenství'
                item_text=f"{row_get(m,'name')} · {fmt_money(row_get(m,'daily_rate'))} · přísl. {fmt_money(extra)} · {acc_text}"
                self.selected.addItem(item_text)
        self.refresh_accessory_options()
        self.update_contract_summary()

    def refresh_accessory_options(self):
        accessory_rows: list[dict[str, Any]] = []
        valid_ids: set[int] = set()
        for m in self.machine_rows:
            mid = int(row_get(m, 'id', 0) or 0)
            if mid not in self.selected_ids:
                continue
            for acc in self.shell.db.get_machine_accessories(mid):
                row = as_dict(acc)
                row['_machine_name'] = row_get(m, 'name')
                accessory_rows.append(row)
                valid_ids.add(int(row_get(row, 'id', 0) or 0))
        self.selected_accessory_ids.intersection_update(valid_ids)
        self.accessory_list.blockSignals(True)
        self.accessory_list.clear()
        if not accessory_rows:
            self.accessory_hint.setText('Po výběru stroje se tady zobrazí dostupné příslušenství.')
        else:
            self.accessory_hint.setText('Zaškrtnuté položky se připočítají do smlouvy i PDF.')
            for row in accessory_rows:
                accessory_id = int(row_get(row, 'id', 0) or 0)
                machine_name = str(row_get(row, '_machine_name'))
                acc_name = str(row_get(row, 'accessory_name'))
                acc_price = parse_float(row_get(row, 'accessory_price', 0))
                item = QListWidgetItem(f"{machine_name} · {acc_name} · {fmt_money(acc_price)}")
                item.setData(Qt.UserRole, accessory_id)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if accessory_id in self.selected_accessory_ids else Qt.Unchecked)
                self.accessory_list.addItem(item)
        self.accessory_list.blockSignals(False)

    def on_accessory_changed(self):
        selected_ids: set[int] = set()
        for idx in range(self.accessory_list.count()):
            item = self.accessory_list.item(idx)
            if item.checkState() == Qt.Checked:
                selected_ids.add(int(item.data(Qt.UserRole) or 0))
        self.selected_accessory_ids = selected_ids
        self.refresh_selected()

    def remove_selected_machine(self):
        current=self.selected.currentItem()
        if current is None:
            row_id=self.shell.current_table_id(self.machine_table)
            if row_id and row_id in self.selected_ids:
                self.selected_ids.remove(row_id)
                self.refresh_selected()
            return
        text=current.text()
        for m in self.machine_rows:
            mid=int(row_get(m,'id',0) or 0)
            if text.startswith(str(row_get(m,'name'))) and mid in self.selected_ids:
                self.selected_ids.remove(mid)
                break
        self.refresh_selected()

    def update_contract_summary(self):
        days = compute_rental_days(self.rental_from.date(), self.rental_to.date())
        pricing_mode = self.pricing_mode.currentData() if hasattr(self, 'pricing_mode') else 'day'
        total=0.0; deposit=0.0
        conflicts=[]
        for m in self.machine_rows:
            mid=int(row_get(m,'id',0) or 0)
            if mid in self.selected_ids:
                accs=[as_dict(r) for r in self.shell.db.get_machine_accessories(mid)]
                selected_accs=[a for a in accs if int(row_get(a,'id',0) or 0) in self.selected_accessory_ids]
                extra=sum(parse_float(row_get(a,'accessory_price',0)) for a in selected_accs)
                machine_price = machine_rate_for_mode(m, pricing_mode)
                total += (machine_price * days if pricing_mode == 'day' else machine_price) + extra
                deposit += parse_float(row_get(m,'deposit',0))
                conflicts.extend(self.shell.db.check_machine_conflicts(mid, self.rental_from.date().toPython().strftime('%Y-%m-%d'), self.rental_to.date().toPython().strftime('%Y-%m-%d')))
        self.sum_selected.setText(str(len(self.selected_ids)))
        self.sum_days.setText(str(days))
        self.sum_total.setText(fmt_money(total))
        self.sum_deposit.setText(fmt_money(deposit))
        if not self.manual_price.isChecked():
            self.total_price.setText(str(int(round(total))))
            self.deposit.setText(str(int(round(deposit))))
        self.conflict_list.clear()
        if not self.selected_ids:
            self.validation_hint.setText('Vyber alespoň jeden stroj.')
        elif conflicts:
            self.validation_hint.setText('Pozor na konflikty nebo nedostupné stroje.')
            for msg in conflicts[:8]:
                self.conflict_list.addItem(msg)
        else:
            self.validation_hint.setText(f'Připraveno k uložení · {days} dní · {len(self.selected_ids)} strojů.')

    def toggle_machine(self):
        row_id=self.shell.current_table_id(self.machine_table)
        if not row_id: return
        if row_id in self.selected_ids: self.selected_ids.remove(row_id)
        else: self.selected_ids.add(row_id)
        self.refresh_selected()

    def save(self):
        cid=self.customer.currentData(); rental_from=self.rental_from.date().toPython().strftime('%Y-%m-%d'); rental_to=self.rental_to.date().toPython().strftime('%Y-%m-%d')
        if not cid or not self.selected_ids:
            QMessageBox.warning(self,'Chyba','Vyber zákazníka a alespoň jeden stroj.')
            return
        conflicts=[]
        for mid in self.selected_ids:
            conflicts.extend(self.shell.db.check_machine_conflicts(mid, rental_from, rental_to))
        if conflicts and QMessageBox.question(self,'Konflikty','Nalezeny konflikty. Přesto uložit?\n\n'+'\n'.join(conflicts[:8])) != QMessageBox.Yes:
            return
        total_price=parse_float(self.total_price.text()); deposit=parse_float(self.deposit.text()); paid=parse_float(self.paid_amount.text())
        contract_number=self.shell.db.generate_contract_number()
        cols=self.shell.db._get_columns('contracts')
        issue_photo=self.issue_photo_path
        if issue_photo:
            dst_dir=PHOTOS_DIR / f'contract_{contract_number}'
            dst_dir.mkdir(parents=True, exist_ok=True)
            src=Path(issue_photo); dst=dst_dir / src.name
            if src.exists() and src.resolve()!=dst.resolve():
                shutil.copy2(src,dst)
            issue_photo=str(dst)
        if 'start_date' in cols and 'end_date' in cols:
            contract_id = self.shell.db.execute("INSERT INTO contracts(contract_number, customer_id, created_at, rental_from, rental_to, start_date, end_date, total_price, deposit, paid_amount, payment_method, issue_photo_path, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'aktivní', ?)", (contract_number,cid,today_str(),rental_from,rental_to,rental_from,rental_to,total_price,deposit,paid,self.payment_method.currentText(),issue_photo,self.notes.toPlainText().strip()))
        else:
            contract_id = self.shell.db.execute("INSERT INTO contracts(contract_number, customer_id, created_at, rental_from, rental_to, total_price, deposit, paid_amount, payment_method, issue_photo_path, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'aktivní', ?)", (contract_number,cid,today_str(),rental_from,rental_to,total_price,deposit,paid,self.payment_method.currentText(),issue_photo,self.notes.toPlainText().strip()))
        accessory_totals_sum=0.0
        for mid in self.selected_ids:
            acc_rows=[as_dict(r) for r in self.shell.db.get_machine_accessories(mid)]
            acc_text='\n'.join([f"{row_get(a,'accessory_name')} ({fmt_money(row_get(a,'accessory_price'))})" for a in acc_rows])
            acc_total=sum(parse_float(row_get(a,'accessory_price',0)) for a in acc_rows)
            accessory_totals_sum += acc_total
            self.shell.db.execute("INSERT INTO contract_items(contract_id, machine_id, issue_condition, accessories_issued, accessories_total) VALUES (?, ?, ?, ?, ?)", (contract_id, mid, self.issue_condition.toPlainText().strip(), acc_text, acc_total))
            self.shell.db.execute("UPDATE machines SET status='půjčený' WHERE id=?", (mid,))
        if accessory_totals_sum:
            self.shell.db.execute("UPDATE contracts SET total_price=COALESCE(total_price,0)+? WHERE id=?", (accessory_totals_sum, contract_id))
        try:
            detail=self.shell.db.get_contract_detail(contract_id); customer=self.shell.db.fetchone('SELECT * FROM customers WHERE id=?',(cid,))
            self.shell.pdf.create_contract_pdf(detail['contract'], customer, detail['items'], self.shell.db.get_settings())
            self.shell.toast('Smlouva vytvořena a PDF připraveno.', 'ok')
        except Exception as exc:
            self.shell.toast(f'PDF smlouvy se nepodařilo vytvořit: {exc}', 'warn')
        self.saved.emit(); self.accept()


class BasePage(QWidget, FadeMixin):
    title = ''
    def __init__(self, shell: 'MainWindow'):
        super().__init__()
        self.shell = shell

    def refresh(self):
        pass


class DashboardPage(BasePage):
    title = 'Přehled'
    def __init__(self, shell: 'MainWindow'):
        super().__init__(shell)
        root = QVBoxLayout(self); root.setContentsMargins(24,24,24,24); root.setSpacing(18)
        cards = QGridLayout(); cards.setSpacing(10)
        self.c_active=StatCard('Aktivní smlouvy', ACCENT); cards.addWidget(self.c_active,0,0)
        self.c_returns=StatCard('Dnes vratky', WARN); cards.addWidget(self.c_returns,0,1)
        self.c_due=StatCard('Po termínu', BAD); cards.addWidget(self.c_due,0,2)
        self.kpi_service = StatCard('Servis čeká', WARN); cards.addWidget(self.kpi_service,0,3)
        self.kpi_res = StatCard('Rezervace', ACCENT_2); cards.addWidget(self.kpi_res,0,4)
        self.kpi_unpaid = StatCard('Neuhrazené', BAD); cards.addWidget(self.kpi_unpaid,0,5)
        for i in range(6):
            cards.setColumnStretch(i,1)
        root.addLayout(cards)

        upper_grid=QGridLayout(); upper_grid.setSpacing(12)
        self.attention=ActionList('Co řešit teď', 'Urgentní termíny, dluhy a servis.')
        self.today=ActionList('Dnes a zítra', 'Nejbližší vratky a rezervace.')
        self.calendar_panel=AgendaCalendar('Kalendář a agenda')
        upper_grid.addWidget(self.attention,0,0)
        upper_grid.addWidget(self.today,1,0)
        upper_grid.addWidget(self.calendar_panel,0,1,2,1)
        upper_grid.setColumnStretch(0,3); upper_grid.setColumnStretch(1,2)
        upper_grid.setRowStretch(0,1); upper_grid.setRowStretch(1,1)
        root.addLayout(upper_grid, 1)

        charts_grid=QGridLayout(); charts_grid.setSpacing(12)
        self.chart_activity=MiniBarChart('Půjčení za posledních 7 dní', ACCENT_2)
        self.chart_revenue=MiniBarChart('Tržba za posledních 6 měsíců', GOOD)
        self.chart_activity.set_filter_options(
            [('7d', '7 dní'), ('14d', '14 dní'), ('30d', '30 dní')],
            '7d',
            lambda *_: self.refresh(),
        )
        self.chart_revenue.set_filter_options(
            [('3m', '3 měsíce'), ('6m', '6 měsíců'), ('12m', '12 měsíců')],
            '6m',
            lambda *_: self.refresh(),
        )
        charts_grid.addWidget(self.chart_activity,0,0)
        charts_grid.addWidget(self.chart_revenue,0,1)
        charts_grid.setColumnStretch(0,1); charts_grid.setColumnStretch(1,1)
        root.addLayout(charts_grid)

        bottom_grid=QGridLayout(); bottom_grid.setSpacing(12)
        self.recent=self.shell.make_table(['Smlouva','Zákazník','Od','Do','Stav','Cena'])
        self.returns=self.shell.make_table(['Smlouva','Zákazník','Do','Stroje'])
        p1=Panel('Naposledy vytvořené smlouvy', 'Rychlý přehled čerstvě založených výpůjček.')
        p1.content.addWidget(self.recent)
        p2=Panel('Nejbližší plánované vratky', 'Co se má vracet v nejbližším období.')
        p2.content.addWidget(self.returns)
        bottom_grid.addWidget(p1,0,0)
        bottom_grid.addWidget(p2,0,1)
        bottom_grid.setColumnStretch(0,1); bottom_grid.setColumnStretch(1,1)
        root.addLayout(bottom_grid,1)

        self.recent.itemDoubleClicked.connect(lambda *_: self.shell.open_contract_detail(self.shell.current_table_id(self.recent)))
        self.returns.itemDoubleClicked.connect(lambda *_: self.shell.open_contract_detail(self.shell.current_table_id(self.returns)))
        self.attention.list.itemDoubleClicked.connect(self._open_action_item)
        self.today.list.itemDoubleClicked.connect(self._open_action_item)
        self.calendar_panel.list.itemDoubleClicked.connect(self._open_action_item)
        self.calendar_panel.calendar.selectionChanged.connect(self.refresh_calendar_items)

    def _make_hero_chip(self, label: str, value: str):
        chip = QFrame(); chip.setObjectName('HeroChip')
        lay = QVBoxLayout(chip); lay.setContentsMargins(14,12,14,12); lay.setSpacing(2)
        lbl = QLabel(label); lbl.setObjectName('HeroChipLabel')
        val = QLabel(value); val.setObjectName('HeroChipValue'); val.setWordWrap(True)
        lay.addWidget(lbl); lay.addWidget(val)
        return chip, val

    def _open_action_item(self, item):
        data=item.data(Qt.UserRole) or {}
        item_id=data.get('id')
        kind=data.get('kind')
        if not item_id:
            return
        if kind=='contract':
            self.shell.open_contract_detail(item_id)
        elif kind=='reservation':
            self.shell.open_reservation_detail(item_id)
        elif kind=='service':
            self.shell.open_service_detail(item_id)
        elif kind=='machine':
            self.shell.open_machine_detail(item_id)

    def refresh_calendar_items(self):
        day=self.calendar_panel.calendar.selectedDate().toPython().strftime('%Y-%m-%d')
        items=[]
        returns=[as_dict(r) for r in self.shell.db.fetchall("SELECT c.id, c.contract_number, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name FROM contracts c LEFT JOIN customers cu ON cu.id=c.customer_id WHERE COALESCE(c.rental_to,c.end_date,'')=? ORDER BY c.contract_number", (day,))]
        for r in returns:
            items.append((f"Vratka · {row_get(r,'contract_number')}", f"{row_get(r,'customer_name')}", {'id': int(row_get(r,'id',0) or 0), 'kind': 'contract'}))
        reservations=[as_dict(r) for r in self.shell.db.fetchall("SELECT r.id, r.reservation_number, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name FROM reservations r LEFT JOIN customers cu ON cu.id=r.customer_id WHERE COALESCE(r.reserved_from,'')=? ORDER BY r.reservation_number", (day,))]
        for r in reservations:
            items.append((f"Rezervace · {row_get(r,'reservation_number')}", f"{row_get(r,'customer_name')}", {'id': int(row_get(r,'id',0) or 0), 'kind': 'reservation'}))
        if not items:
            items=[('Bez položek', 'Na tento den nic není naplánované.', {})]
        self.calendar_panel.set_items(self.calendar_panel.calendar.selectedDate(), items)

    def refresh(self):
        stats=self.shell.db.get_dashboard_stats()
        self.c_active.set_data(int(stats.get('contracts_active',0)), 'Právě běží')
        self.c_returns.set_data(int(stats.get('returns_today',0)), 'Na dnešek')
        self.c_due.set_data(int(stats.get('contracts_overdue',0)), 'Potřebuje kontrolu')
        self.kpi_service.set_data(int(stats.get('service_due',0)), 'Termín nebo motohodiny')
        self.kpi_res.set_data(int(stats.get('reservations_active',0)), 'Čekají v kalendáři')
        self.kpi_unpaid.set_data(int(stats.get('unpaid',0)), 'K doplacení')

        recent=[as_dict(r) for r in self.shell.db.get_recent_contracts(12)]
        self.shell.fill_table(self.recent, [[row_get(r,'contract_number'), row_get(r,'customer_name'), row_get(r,'rental_from'), row_get(r,'rental_to'), row_get(r,'status'), fmt_money(row_get(r,'total_price'))] for r in recent], [int(row_get(r,'id',0) or 0) for r in recent])
        due=[as_dict(r) for r in self.shell.db.get_upcoming_returns(12)]
        self.shell.fill_table(self.returns, [[row_get(r,'contract_number'), row_get(r,'customer_name'), row_get(r,'rental_to') or row_get(r,'end_date'), row_get(r,'machines')] for r in due], [int(row_get(r,'id',0) or 0) for r in due])

        self.attention.clear_items()
        overdue=[as_dict(r) for r in self.shell.db.fetchall("SELECT c.id, c.contract_number, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name, COALESCE(c.rental_to,c.end_date,'') AS due_date FROM contracts c LEFT JOIN customers cu ON cu.id=c.customer_id WHERE c.status='po termínu' OR (c.status='aktivní' AND COALESCE(c.rental_to,c.end_date,'') < ?) ORDER BY COALESCE(c.rental_to,c.end_date,'') ASC LIMIT 8", (today_str(),))]
        for r in overdue:
            self.attention.add_item(f"Po termínu · {row_get(r,'contract_number')}", f"{row_get(r,'customer_name')} · do {row_get(r,'due_date')}", int(row_get(r,'id',0) or 0), 'contract', BAD)
        unpaid=[as_dict(r) for r in self.shell.db.fetchall("SELECT c.id, c.contract_number, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name, (COALESCE(c.total_price,0)+COALESCE(c.deposit,0)+COALESCE(c.return_extra_charge,0)-COALESCE(c.paid_amount,0)) AS due_amount FROM contracts c LEFT JOIN customers cu ON cu.id=c.customer_id WHERE COALESCE(c.paid_amount,0) < (COALESCE(c.total_price,0)+COALESCE(c.deposit,0)+COALESCE(c.return_extra_charge,0)) AND c.status='aktivní' ORDER BY c.id DESC LIMIT 6") ]
        for r in unpaid:
            self.attention.add_item(f"Neuhrazené · {row_get(r,'contract_number')}", f"{row_get(r,'customer_name')} · doplatek {fmt_money(row_get(r,'due_amount'))}", int(row_get(r,'id',0) or 0), 'contract', WARN)
        service_due=[as_dict(r) for r in self.shell.db.get_service_due_machines(6)]
        for r in service_due:
            subtitle = f"{row_get(r,'category')}"
            if row_get(r,'next_service_date'):
                subtitle += f" · termín {row_get(r,'next_service_date')}"
            if row_get(r,'service_due_motohours'):
                subtitle += f" · MH {row_get(r,'motohours')}/{row_get(r,'service_due_motohours')}"
            self.attention.add_item(f"Servis · {row_get(r,'name')}", subtitle, int(row_get(r,'id',0) or 0), 'machine', ACCENT_2)
        if self.attention.list.count()==0:
            self.attention.add_item('Bez urgentních úkolů', 'Dnes nic nekřičí červeně.', None, 'contract', GOOD)

        self.today.clear_items()
        today_rows=[as_dict(r) for r in self.shell.db.get_upcoming_returns(8)]
        for r in today_rows[:6]:
            self.today.add_item(f"Vratka · {row_get(r,'contract_number')}", f"{row_get(r,'customer_name')} · {row_get(r,'rental_to') or row_get(r,'end_date')} · {row_get(r,'machines')}", int(row_get(r,'id',0) or 0), 'contract', WARN)
        reservations=[as_dict(r) for r in self.shell.db.get_upcoming_reservations(8)]
        for r in reservations[:6]:
            self.today.add_item(f"Rezervace · {row_get(r,'reservation_number')}", f"{row_get(r,'customer_name')} · od {row_get(r,'reserved_from')} · {row_get(r,'machines')}", int(row_get(r,'id',0) or 0), 'reservation', ACCENT_2)
        if self.today.list.count()==0:
            self.today.add_item('Nic naplánovaného', 'Dnes ani zítra nejsou plánované vratky nebo rezervace.', None, 'contract', GOOD)

        activity=[]
        for i in range(6, -1, -1):
            d=date.today()-timedelta(days=i)
            row=self.shell.db.fetchone("SELECT COUNT(*) AS c FROM contracts WHERE created_at LIKE ?", (f"{d.strftime('%Y-%m-%d')}%",))
            activity.append((d.strftime('%d.%m'), int(row_get(as_dict(row),'c',0) or 0)))
        self.chart_activity.set_data(activity, 'Kolik smluv vzniklo v posledním týdnu')

        months=[]
        m=date.today().replace(day=1)
        for _ in range(6):
            months.append(m)
            m=(m.replace(day=1)-timedelta(days=1)).replace(day=1)
        months=list(reversed(months))
        revenue=[]
        for m in months:
            start=m.strftime('%Y-%m-01')
            end=(date(m.year+1,1,1) if m.month==12 else date(m.year,m.month+1,1)).strftime('%Y-%m-%d')
            row=self.shell.db.fetchone("SELECT COALESCE(SUM(total_price),0) AS s FROM contracts WHERE created_at >= ? AND created_at < ?", (start,end))
            revenue.append((m.strftime('%m/%y'), float(row_get(as_dict(row),'s',0) or 0)))
        self.chart_revenue.set_data(revenue, 'Součet cen smluv po měsících', ' Kč')
        self.refresh_calendar_items()


def _dashboard_refresh_calendar_items(self: DashboardPage):
    day = self.calendar_panel.calendar.selectedDate().toPython().strftime('%Y-%m-%d')
    items = []
    events = [as_dict(r) for r in self.shell.db.get_calendar_events(day, day)]
    for r in events:
        label = 'Rezervace' if row_get(r, 'kind') == 'reservation' else 'Vypujcka'
        subtitle = f"{row_get(r,'customer_name')} · {row_get(r,'machines')} · {row_get(r,'date_from')} az {row_get(r,'date_to')}"
        items.append((f"{label} · {row_get(r,'ref')}", subtitle, {'id': int(row_get(r,'id',0) or 0), 'kind': row_get(r,'kind')}))
    if not items:
        items = [('Bez polozek', 'Na tento den neni nic naplanovane.', {})]
    self.calendar_panel.set_items(self.calendar_panel.calendar.selectedDate(), items)


def _dashboard_refresh_calendar_markers(self: DashboardPage):
    selected = self.calendar_panel.calendar.selectedDate()
    start = selected.addDays(-15).toPython().strftime('%Y-%m-%d')
    end = selected.addDays(45).toPython().strftime('%Y-%m-%d')
    events = [as_dict(r) for r in self.shell.db.get_calendar_events(start, end)]
    markers: dict[str, set[str]] = {}
    for event in events:
        for day in iter_days(row_get(event, 'date_from'), row_get(event, 'date_to')):
            key = day.strftime('%Y-%m-%d')
            markers.setdefault(key, set()).add(str(row_get(event, 'kind')))
    self.calendar_panel.set_day_markers(markers)


def _dashboard_refresh(self: DashboardPage):
    return _dashboard_refresh_clean(self)


DashboardPage.refresh_calendar_items = _dashboard_refresh_calendar_items
DashboardPage.refresh_calendar_markers = _dashboard_refresh_calendar_markers
DashboardPage.refresh = _dashboard_refresh


class EntityPage(BasePage):
    def __init__(self, shell: 'MainWindow', title: str, subtitle: str, columns: list[str]):
        super().__init__(shell)
        self.title = title
        self.subtitle = subtitle
        root=QVBoxLayout(self); root.setContentsMargins(24,24,24,24); root.setSpacing(16)
        header=QHBoxLayout()
        header.addStretch(1)
        self.actions=QHBoxLayout(); header.addLayout(self.actions)
        root.addLayout(header)

        toolbar=QFrame(); toolbar.setObjectName('ToolbarPanel'); tl=QHBoxLayout(toolbar); tl.setContentsMargins(12,12,12,12)
        self.search=QLineEdit(); self.search.setPlaceholderText('Hledat...'); self.search.textChanged.connect(lambda _=None: self.refresh())
        self.quick_filter = QComboBox()
        self.quick_filter.setMinimumWidth(180)
        self.quick_filter.currentIndexChanged.connect(lambda _=None: self.refresh())
        self.info=QLabel(''); self.info.setObjectName('PanelSubtle')
        self.export_btn=QPushButton('Export CSV'); self.export_btn.setObjectName('GhostBtn'); self.export_btn.clicked.connect(self.export_csv)
        tl.addWidget(self.search,1); tl.addWidget(self.quick_filter); tl.addWidget(self.export_btn); tl.addWidget(self.info)
        root.addWidget(toolbar)

        self.table=shell.make_table(columns); root.addWidget(self.table,1)
        self.selection_panel = QFrame(); self.selection_panel.setObjectName('SelectionPanel')
        sl = QHBoxLayout(self.selection_panel); sl.setContentsMargins(14,12,14,12); sl.setSpacing(10)
        self.selection_label = QLabel(''); self.selection_label.setObjectName('SelectionTitle')
        sl.addWidget(self.selection_label)
        sl.addStretch(1)
        self.selection_actions = QHBoxLayout(); sl.addLayout(self.selection_actions)
        self.selection_panel.hide()
        root.addWidget(self.selection_panel)
        self.table.itemSelectionChanged.connect(self.update_selection_state)
        self.quick_filter.hide()

    def export_csv(self):
        self.shell.export_current_page(self)

    def set_quick_filters(self, items: list[tuple[str, str]], current: str | None = None):
        self.quick_filter.blockSignals(True)
        self.quick_filter.clear()
        for label, value in items:
            self.quick_filter.addItem(label, value)
        target = current or (items[0][1] if items else None)
        idx = self.quick_filter.findData(target)
        if idx >= 0:
            self.quick_filter.setCurrentIndex(idx)
        self.quick_filter.blockSignals(False)
        self.quick_filter.setVisible(bool(items))

    def current_filter(self) -> str:
        return str(self.quick_filter.currentData() or '')

    def clear_selection_actions(self):
        while self.selection_actions.count():
            item=self.selection_actions.takeAt(0)
            w=item.widget()
            if w is not None:
                w.deleteLater()

    def set_selection_actions(self, label: str, actions: list[tuple[str, Any, str]]):
        self.selection_label.setText(label)
        self.clear_selection_actions()
        for text_btn, callback, style in actions:
            b=QPushButton(text_btn)
            b.setObjectName(style)
            b.clicked.connect(callback)
            self.selection_actions.addWidget(b)
        self.selection_panel.setVisible(bool(actions))

    def update_selection_state(self):
        row_id = self.shell.current_table_id(self.table)
        if not row_id:
            self.selection_panel.hide()
            self.clear_selection_actions()
            return
        self.on_row_selected(row_id)

    def on_row_selected(self, row_id: int):
        self.selection_panel.hide()


class CustomersPage(EntityPage):
    def __init__(self, shell: 'MainWindow'):
        super().__init__(shell, 'Zákazníci', 'Kontakty a historie.', ['Jméno','Firma','Telefon','E-mail'])
        b=QPushButton('Přidat zákazníka'); b.setObjectName('PrimaryBtn'); b.clicked.connect(shell.new_customer); self.actions.addWidget(b)
        self.set_quick_filters([
            ('Všichni zákazníci', 'all'),
            ('S aktivní smlouvou', 'active'),
            ('Firmy', 'company'),
            ('Soukromé osoby', 'private'),
        ], 'all')
        self.table.itemDoubleClicked.connect(lambda *_: self.open_selected())

    def refresh(self):
        term=self.search.text().strip().lower()
        filter_mode = self.current_filter()
        rows=[as_dict(r) for r in self.shell.db.fetchall('SELECT * FROM customers ORDER BY name')]
        data=[]; ids=[]
        for r in rows:
            active_count = self.shell.db.fetchone("SELECT COUNT(*) AS c FROM contracts WHERE customer_id=? AND status='aktivní'", (int(row_get(r,'id',0) or 0),))
            has_active = int(row_get(as_dict(active_count), 'c', 0) or 0) > 0
            is_company = bool(str(row_get(r,'company','')).strip())
            if filter_mode == 'active' and not has_active:
                continue
            if filter_mode == 'company' and not is_company:
                continue
            if filter_mode == 'private' and is_company:
                continue
            vals=[row_get(r,'name'), row_get(r,'company'), row_get(r,'phone'), row_get(r,'email')]
            if term and term not in ' '.join(map(str,vals)).lower() and term not in str(row_get(r,'notes','')).lower():
                continue
            data.append(vals); ids.append(int(row_get(r,'id',0) or 0))
        self.shell.fill_table(self.table, data, ids); self.info.setText(f'Zobrazeno {len(data)} zákazníků')
        self.update_selection_state()

    def on_row_selected(self, row_id: int):
        row = as_dict(self.shell.db.fetchone('SELECT * FROM customers WHERE id=?', (row_id,)))
        name = row_get(row, 'name') or 'Vybraný zákazník'
        self.set_selection_actions(name, [('Detail', self.open_selected, 'PrimaryBtn'), ('Upravit', self.edit_selected, 'GhostBtn'), ('Smazat', self.delete_selected, 'GhostBtn')])

    def edit_selected(self):
        row_id=self.shell.current_table_id(self.table)
        if row_id: self.shell.edit_customer(row_id)

    def open_selected(self):
        row_id=self.shell.current_table_id(self.table)
        if row_id: self.shell.open_customer_detail(row_id)

    def delete_selected(self):
        row_id=self.shell.current_table_id(self.table)
        if not row_id: return
        if QMessageBox.question(self,'Smazat','Opravdu smazat zákazníka?')==QMessageBox.Yes:
            self.shell.db.execute('DELETE FROM customers WHERE id=?',(row_id,)); self.refresh(); self.shell.dashboard.refresh(); self.shell.toast('Zákazník smazán.','ok')


class MachinesPage(EntityPage):
    def __init__(self, shell: 'MainWindow'):
        super().__init__(shell, 'Stroje', 'Dostupnost a servis.', ['Stroj','Kategorie','Stav','Cena','MH'])
        b=QPushButton('Přidat stroj'); b.setObjectName('PrimaryBtn'); b.clicked.connect(shell.new_machine); self.actions.addWidget(b)
        self.set_quick_filters([
            ('Všechny stroje', 'all'),
            ('Volné', 'volný'),
            ('Půjčené', 'půjčený'),
            ('V servisu', 'servis'),
            ('Blokované', 'blocked'),
        ], 'all')
        self.table.itemDoubleClicked.connect(lambda *_: self.open_selected())

    def refresh(self):
        term=self.search.text().strip().lower()
        filter_mode = self.current_filter()
        rows=[as_dict(r) for r in self.shell.db.fetchall('SELECT * FROM machines ORDER BY name')]
        data=[]; ids=[]
        for r in rows:
            status = str(row_get(r,'status',''))
            if filter_mode == 'volný' and status != 'volný':
                continue
            if filter_mode == 'půjčený' and status != 'půjčený':
                continue
            if filter_mode == 'servis' and status != 'servis':
                continue
            if filter_mode == 'blocked' and status not in {'blokovaný', 'vyřazený'}:
                continue
            vals=[row_get(r,'name'), row_get(r,'category'), row_get(r,'status'), fmt_money(row_get(r,'daily_rate')), str(row_get(r,'motohours','0'))]
            if term and term not in ' '.join(map(str,vals)).lower() and term not in str(row_get(r,'notes','')).lower():
                continue
            data.append(vals); ids.append(int(row_get(r,'id',0) or 0))
        self.shell.fill_table(self.table, data, ids); self.info.setText(f'Zobrazeno {len(data)} strojů')
        self.update_selection_state()

    def on_row_selected(self, row_id: int):
        row = as_dict(self.shell.db.fetchone('SELECT * FROM machines WHERE id=?', (row_id,)))
        title = f"{row_get(row,'name')} · {row_get(row,'status')}"
        self.set_selection_actions(title, [('Detail', self.open_selected, 'PrimaryBtn'), ('Upravit', self.edit_selected, 'GhostBtn'), ('PDF štítek', self.make_label, 'GhostBtn'), ('Smazat', self.delete_selected, 'GhostBtn')])

    def edit_selected(self):
        row_id=self.shell.current_table_id(self.table)
        if row_id: self.shell.edit_machine(row_id)

    def open_selected(self):
        row_id=self.shell.current_table_id(self.table)
        if row_id: self.shell.open_machine_detail(row_id)

    def make_label(self):
        row_id=self.shell.current_table_id(self.table)
        if row_id: self.shell.create_machine_label(row_id)

    def delete_selected(self):
        row_id=self.shell.current_table_id(self.table)
        if not row_id: return
        if QMessageBox.question(self,'Smazat','Opravdu smazat stroj?')==QMessageBox.Yes:
            self.shell.db.execute('DELETE FROM machines WHERE id=?',(row_id,)); self.refresh(); self.shell.dashboard.refresh(); self.shell.toast('Stroj smazán.','ok')


class ContractsPage(EntityPage):
    def __init__(self, shell: 'MainWindow'):
        super().__init__(shell, 'Smlouvy a rezervace', 'Aktivní výdeje a budoucí rezervace.', ['Číslo','Zákazník','Od','Do','Stav','Cena'])
        self.mode=QComboBox(); self.mode.addItems(['Smlouvy','Rezervace']); self.mode.currentTextChanged.connect(lambda _=None: self.refresh())
        self.actions.addWidget(self.mode)
        for text_btn, cb in [('Nová smlouva', shell.new_contract), ('Nová rezervace', shell.new_reservation)]:
            b=QPushButton(text_btn); b.setObjectName('PrimaryBtn' if text_btn=='Nová smlouva' else 'GhostBtn'); b.clicked.connect(cb); self.actions.addWidget(b)
        self.table.itemDoubleClicked.connect(lambda *_: self.open_selected())

    def refresh(self):
        term=self.search.text().strip().lower(); mode=self.mode.currentText()
        current_filter = self.current_filter()
        if mode == 'Smlouvy':
            self.set_quick_filters([
                ('Všechny smlouvy', 'all'),
                ('Aktivní', 'active'),
                ('Dnes vratit', 'today'),
                ('Po termínu', 'overdue'),
                ('Neuhrazené', 'unpaid'),
            ], current_filter if current_filter in {'all','active','today','overdue','unpaid'} else 'all')
        else:
            self.set_quick_filters([
                ('Všechny rezervace', 'all'),
                ('Aktivní rezervace', 'active'),
                ('Začínají dnes', 'today'),
                ('Potvrzené', 'confirmed'),
            ], current_filter if current_filter in {'all','active','today','confirmed'} else 'all')
        current_filter = self.current_filter()
        if mode=='Smlouvy':
            rows=[as_dict(r) for r in self.shell.db.fetchall("SELECT c.*, cu.name AS customer_name FROM contracts c LEFT JOIN customers cu ON cu.id=c.customer_id ORDER BY c.id DESC")]
            data=[]; ids=[]
            for r in rows:
                due_date = str(row_get(r,'rental_to') or row_get(r,'end_date') or '')
                unpaid = parse_float(row_get(r,'paid_amount')) < (parse_float(row_get(r,'total_price')) + parse_float(row_get(r,'deposit')) + parse_float(row_get(r,'return_extra_charge')))
                if current_filter == 'active' and row_get(r,'status') != 'aktivní':
                    continue
                if current_filter == 'today' and due_date != today_str():
                    continue
                if current_filter == 'overdue' and not (row_get(r,'status') == 'po termínu' or (row_get(r,'status') == 'aktivní' and due_date and due_date < today_str())):
                    continue
                if current_filter == 'unpaid' and not unpaid:
                    continue
                vals=[row_get(r,'contract_number'), row_get(r,'customer_name'), row_get(r,'rental_from'), row_get(r,'rental_to'), row_get(r,'status'), fmt_money(row_get(r,'total_price'))]
                if term and term not in ' '.join(map(str,vals)).lower(): continue
                data.append(vals); ids.append(int(row_get(r,'id',0) or 0))
            self.shell.fill_table(self.table, data, ids)
            self.info.setText(f'Zobrazeno {len(data)} smluv')
        else:
            rows=[as_dict(r) for r in self.shell.db.fetchall("SELECT r.*, cu.name AS customer_name FROM reservations r LEFT JOIN customers cu ON cu.id=r.customer_id ORDER BY r.id DESC")]
            data=[]; ids=[]
            for r in rows:
                if current_filter == 'active' and row_get(r,'status') not in {'rezervace', 'potvrzeno'}:
                    continue
                if current_filter == 'today' and row_get(r,'reserved_from') != today_str():
                    continue
                if current_filter == 'confirmed' and row_get(r,'status') != 'potvrzeno':
                    continue
                vals=[row_get(r,'reservation_number'), row_get(r,'customer_name'), row_get(r,'reserved_from'), row_get(r,'reserved_to'), row_get(r,'status'), fmt_money(row_get(r,'total_price'))]
                if term and term not in ' '.join(map(str,vals)).lower(): continue
                data.append(vals); ids.append(int(row_get(r,'id',0) or 0))
            self.shell.fill_table(self.table, data, ids)
            self.info.setText(f'Zobrazeno {len(data)} rezervací')
        self.update_selection_state()

    def on_row_selected(self, row_id: int):
        if self.mode.currentText()=='Smlouvy':
            row = as_dict(self.shell.db.fetchone('SELECT * FROM contracts WHERE id=?', (row_id,)))
            title = f"{row_get(row,'contract_number')} · {row_get(row,'status')}"
            actions=[('Detail', self.open_selected, 'PrimaryBtn')]
            if row_get(row,'status')!='vráceno':
                actions.append(('Vrácení', self.return_selected, 'GhostBtn'))
            actions.extend([('Vratný protokol', self.return_protocol_selected, 'GhostBtn'), ('Smazat', self.delete_selected, 'GhostBtn')])
        else:
            row = as_dict(self.shell.db.fetchone('SELECT * FROM reservations WHERE id=?', (row_id,)))
            title = f"{row_get(row,'reservation_number')} · {row_get(row,'status')}"
            actions=[('Detail', self.open_selected, 'PrimaryBtn'), ('Smazat', self.delete_selected, 'GhostBtn')]
        self.set_selection_actions(title, actions)

    def open_selected(self):
        row_id=self.shell.current_table_id(self.table)
        if not row_id: return
        if self.mode.currentText()=='Smlouvy': self.shell.open_contract_detail(row_id)
        else: self.shell.open_reservation_detail(row_id)

    def return_selected(self):
        row_id=self.shell.current_table_id(self.table)
        if row_id and self.mode.currentText()=='Smlouvy': self.shell.return_contract(row_id)

    def return_protocol_selected(self):
        row_id=self.shell.current_table_id(self.table)
        if row_id and self.mode.currentText()=='Smlouvy':
            self.shell.open_return_protocol(row_id)

    def delete_selected(self):
        row_id=self.shell.current_table_id(self.table)
        if not row_id: return
        if QMessageBox.question(self,'Smazat','Opravdu smazat záznam?')!=QMessageBox.Yes: return
        if self.mode.currentText()=='Smlouvy':
            self.shell.db.delete_contract(row_id)
            self.shell.toast('Smlouva smazána.','ok')
        else:
            self.shell.db.delete_reservation(row_id)
            self.shell.toast('Rezervace smazána.','ok')
        self.refresh(); self.shell.dashboard.refresh()


class ServicesPage(EntityPage):
    def __init__(self, shell: 'MainWindow'):
        super().__init__(shell, 'Servis', 'Termíny, náklady a uzavření servisu.', ['Stroj','Datum','Typ','Cena','Stav','Další servis'])
        b=QPushButton('Nový servis'); b.setObjectName('PrimaryBtn'); b.clicked.connect(shell.new_service); self.actions.addWidget(b)
        self.set_quick_filters([
            ('Všechny záznamy', 'all'),
            ('Otevřené', 'open'),
            ('Dokončené', 'done'),
            ('S termínem', 'planned'),
        ], 'all')
        self.table.itemDoubleClicked.connect(lambda *_: self.open_selected())

    def refresh(self):
        term=self.search.text().strip().lower()
        filter_mode = self.current_filter()
        rows=[as_dict(r) for r in self.shell.db.fetchall("SELECT s.*, m.name AS machine_name FROM service_records s LEFT JOIN machines m ON m.id=s.machine_id ORDER BY s.id DESC")]
        data=[]; ids=[]
        for r in rows:
            status = str(row_get(r,'status',''))
            if filter_mode == 'open' and status == 'dokončeno':
                continue
            if filter_mode == 'done' and status != 'dokončeno':
                continue
            if filter_mode == 'planned' and not str(row_get(r,'next_service_date','')).strip():
                continue
            vals=[row_get(r,'machine_name'), row_get(r,'service_date'), row_get(r,'service_type'), fmt_money(row_get(r,'cost')), row_get(r,'status'), row_get(r,'next_service_date')]
            if term and term not in ' '.join(map(str,vals)).lower() and term not in str(row_get(r,'notes','')).lower(): continue
            data.append(vals); ids.append(int(row_get(r,'id',0) or 0))
        self.shell.fill_table(self.table, data, ids); self.info.setText(f'Zobrazeno {len(data)} servisních záznamů')
        self.update_selection_state()

    def on_row_selected(self, row_id: int):
        row = as_dict(self.shell.db.fetchone('SELECT * FROM service_records WHERE id=?', (row_id,)))
        title = f"{row_get(row,'service_type')} · {row_get(row,'status')}"
        actions=[('Detail', self.open_selected, 'PrimaryBtn'), ('Upravit', self.edit_selected, 'GhostBtn')]
        if row_get(row,'status')!='dokončeno':
            actions.append(('Dokončit', self.finish_selected, 'GhostBtn'))
        self.set_selection_actions(title, actions)

    def edit_selected(self):
        row_id=self.shell.current_table_id(self.table)
        if row_id: self.shell.edit_service(row_id)

    def finish_selected(self):
        row_id=self.shell.current_table_id(self.table)
        if not row_id: return
        rec=as_dict(self.shell.db.fetchone('SELECT * FROM service_records WHERE id=?',(row_id,)))
        self.shell.db.finish_service(int(row_get(rec,'machine_id',0) or 0), row_id)
        self.refresh(); self.shell.dashboard.refresh(); self.shell.toast('Servis dokončen.','ok')

    def open_selected(self):
        row_id=self.shell.current_table_id(self.table)
        if row_id: self.shell.open_service_detail(row_id)


class SettingsPage(BasePage):
    title='Nastavení'
    def __init__(self, shell: 'MainWindow'):
        super().__init__(shell)
        root=QVBoxLayout(self); root.setContentsMargins(24,24,24,24); root.setSpacing(16)
        header=QHBoxLayout()
        header.addStretch(1)
        self.save_btn=QPushButton('Uložit nastavení'); self.save_btn.setObjectName('PrimaryBtn'); self.save_btn.clicked.connect(self.save); header.addWidget(self.save_btn)
        root.addLayout(header)

        content=QSplitter(Qt.Horizontal)
        content.setChildrenCollapsible(False)
        content.setHandleWidth(1)

        nav_panel=Panel('Kategorie', 'Sekce')
        self.cat_list=QListWidget(); self.cat_list.setObjectName('SettingsNav')
        enable_smooth_scroll(self.cat_list)
        for name in ['Firma', 'Dokumenty', 'Smlouvy a rezervace', 'Vratný protokol', 'Vzhled', 'Data a zálohy']:
            self.cat_list.addItem(name)
        self.cat_list.setCurrentRow(0)
        nav_panel.content.addWidget(self.cat_list)
        nav_wrap=QWidget(); nav_l=QVBoxLayout(nav_wrap); nav_l.setContentsMargins(0,0,0,0); nav_l.addWidget(nav_panel)

        self.stack_wrap=QStackedWidget(); self.stack_wrap.setObjectName('SettingsStack')
        self.entries={}
        self.data=shell.db.get_settings()

        def add_page(title: str, subtitle: str, sections: list[tuple[str, list[tuple[str,str]]]], extra_builder=None):
            page=QWidget()
            page_l=QVBoxLayout(page); page_l.setContentsMargins(0,0,0,0); page_l.setSpacing(16)
            scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame)
            wrap=QWidget(); lay=QVBoxLayout(wrap); lay.setContentsMargins(0,0,0,0); lay.setSpacing(16)
            intro = QLabel(subtitle)
            intro.setObjectName('PanelSubtle')
            intro.setWordWrap(True)
            lay.addWidget(intro)
            for group_title, fields in sections:
                g=FormGroup(group_title)
                for key,label in fields:
                    if key in {'company_address','contract_declaration','contract_terms','return_protocol_header_text','return_protocol_footer','machine_categories'}:
                        w=QPlainTextEdit(self.data.get(key,'')); w.setMinimumHeight(110)
                    else:
                        w=QLineEdit(self.data.get(key,''))
                    self.entries[key]=w
                    g.form.addRow(label, w)
                lay.addWidget(g)
            if extra_builder:
                extra_builder(lay)
            lay.addStretch(1)
            scroll.setWidget(wrap)
            page_l.addWidget(scroll,1)
            self.stack_wrap.addWidget(page)

        add_page('Firemní údaje', 'Hlavičky dokumentů a kontakty společnosti.', [('Firma', [('company_name','Název firmy'),('company_address','Adresa'),('company_phone','Telefon'),('company_email','E-mail'),('company_ico','IČO'),('company_dic','DIČ')])])
        add_page('Dokumenty', 'Texty a hlavičky smluv.', [('Smlouva', [('contract_title','Název smlouvy'),('contract_subtitle','Podtitulek'),('contract_place','Místo podpisu')]), ('Smluvní texty', [('contract_terms','Podmínky'), ('contract_declaration','Prohlášení')])])
        add_page('Smlouvy a rezervace', 'Provozní nastavení a číselníky.', [('Provoz', [('pin_code','PIN aplikace'), ('default_service_interval_mh','Servis za kolik MH'), ('machine_categories','Kategorie strojů (po řádcích)')])])
        add_page('Vratný protokol', 'Texty pro PDF vratného protokolu.', [('Vratný protokol', [('return_protocol_header_text','Horní text'), ('return_protocol_footer','Text dole')])])

        theme_page=QWidget()
        theme_l=QVBoxLayout(theme_page); theme_l.setContentsMargins(0,0,0,0); theme_l.setSpacing(16)
        theme_intro = QLabel('Motiv a vizuální volby aplikace.')
        theme_intro.setObjectName('PanelSubtle')
        theme_intro.setWordWrap(True)
        theme_l.addWidget(theme_intro)
        fg=FormGroup('Motiv')
        self.theme=QComboBox(); self.theme.addItems(['dark','light']); self.theme.setCurrentText(load_theme())
        fg.form.addRow('Téma', self.theme)
        theme_l.addWidget(fg)
        theme_l.addStretch(1)
        self.stack_wrap.addWidget(theme_page)

        data_page=QWidget()
        data_l=QVBoxLayout(data_page); data_l.setContentsMargins(0,0,0,0); data_l.setSpacing(16)
        data_intro = QLabel('Exporty a správa dat aplikace.')
        data_intro.setObjectName('PanelSubtle')
        data_intro.setWordWrap(True)
        data_l.addWidget(data_intro)
        tools=FormGroup('Rychlé akce')
        grid_wrap=QWidget()
        grid=QGridLayout(grid_wrap); grid.setContentsMargins(0,0,0,0); grid.setHorizontalSpacing(10); grid.setVerticalSpacing(10)
        actions=[('Otevřít data', shell.open_data_dir), ('Export strojů CSV', lambda: shell.db.export_table_to_csv('machines','stroje')), ('Export zákazníků CSV', lambda: shell.db.export_table_to_csv('customers','zakaznici')), ('Export smluv CSV', lambda: shell.db.export_table_to_csv('contracts','smlouvy')), ('Záloha databáze', shell.backup_db)]
        for i,(label,cb) in enumerate(actions):
            b=QPushButton(label); b.setObjectName('GhostBtn'); b.clicked.connect(cb)
            grid.addWidget(b, i//2, i%2)
        tools.form.addRow(grid_wrap)
        data_l.addWidget(tools)

        updates=FormGroup('Aktualizace')
        self.entries['github_repo'] = QLineEdit(self.data.get('github_repo', ''))
        self.entries['github_asset_name'] = QLineEdit(self.data.get('github_asset_name', RELEASE_ASSET_NAME))
        updates.form.addRow('GitHub repo', self.entries['github_repo'])
        updates.form.addRow('Název souboru', self.entries['github_asset_name'])
        version_row = QWidget()
        version_l = QHBoxLayout(version_row)
        version_l.setContentsMargins(0, 0, 0, 0)
        version_l.setSpacing(10)
        version_l.addWidget(QLabel(f'Aktuální verze: {APP_VERSION}'))
        check_btn = QPushButton('Zkontrolovat aktualizaci')
        check_btn.setObjectName('PrimaryBtn')
        check_btn.clicked.connect(shell.check_for_updates)
        version_l.addWidget(check_btn)
        version_l.addStretch(1)
        updates.form.addRow(version_row)
        data_l.addWidget(updates)
        data_l.addStretch(1)
        self.stack_wrap.addWidget(data_page)

        self.cat_list.currentRowChanged.connect(self.stack_wrap.setCurrentIndex)
        content.addWidget(nav_wrap)
        content.addWidget(self.stack_wrap)
        content.setStretchFactor(0, 0)
        content.setStretchFactor(1, 1)
        content.setSizes([260, 980])
        root.addWidget(content,1)

    def save(self):
        values={k:(w.toPlainText().strip() if isinstance(w,QPlainTextEdit) else w.text().strip()) for k,w in self.entries.items()}
        self.shell.db.save_settings(values)
        save_theme(self.theme.currentText())
        self.shell.apply_theme(self.theme.currentText())
        self.shell.toast('Nastavení uloženo.','ok')


class DetailDialog(AnimatedDialog):

    def __init__(self, shell: 'MainWindow', title: str):
        super().__init__(shell, title, 1360, 960)
        self.save_btn.hide(); self.cancel_btn.setText('Zavřít')
        self.cancel_btn.setObjectName('GhostBtn')

        self.hero = QFrame(); self.hero.setObjectName('DetailHero')
        hero_l = QVBoxLayout(self.hero); hero_l.setContentsMargins(18,18,18,18); hero_l.setSpacing(8)
        self.hero_title = QLabel(title); self.hero_title.setObjectName('DetailHeroTitle')
        self.hero_sub = QLabel('')
        self.hero_sub.setObjectName('DetailHeroSub')
        self.hero_sub.setWordWrap(True)
        hero_l.addWidget(self.hero_title)
        hero_l.addWidget(self.hero_sub)
        self.badges_row = QHBoxLayout(); self.badges_row.setSpacing(8)
        hero_l.addLayout(self.badges_row)
        self.body_l.insertWidget(0, self.hero)

    def set_summary(self, text: str, badges: list[str] | None = None):
        self.hero_sub.setText(text)
        while self.badges_row.count():
            item = self.badges_row.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for badge in badges or []:
            lab = QLabel(badge)
            lab.setObjectName('DetailBadge')
            normalize_widget_font(lab)
            badge_text = str(badge or '')
            if ':' in badge_text:
                badge_value = badge_text.split(':', 1)[1].strip()
                badge_style = status_badge_stylesheet(badge_value)
                if badge_style:
                    lab.setStyleSheet(badge_style)
            self.badges_row.addWidget(lab)
        self.badges_row.addStretch(1)

    def add_stat_strip(self, items: list[tuple[str, Any]]):
        wrap = QFrame(); wrap.setObjectName('DetailStatStrip')
        grid = QGridLayout(wrap); grid.setContentsMargins(0,0,0,0); grid.setHorizontalSpacing(12); grid.setVerticalSpacing(12)
        for idx, (label, value) in enumerate(items):
            card = QFrame(); card.setObjectName('DetailMiniCard')
            cl = QVBoxLayout(card); cl.setContentsMargins(14,12,14,12); cl.setSpacing(4)
            l1 = QLabel(label); l1.setObjectName('DetailMiniLabel')
            l2 = QLabel(format_display_value(label, value)); l2.setObjectName('DetailMiniValue'); l2.setWordWrap(True)
            normalize_widget_font(l1)
            normalize_widget_font(l2)
            cl.addWidget(l1); cl.addWidget(l2)
            grid.addWidget(card, idx // 3, idx % 3)
        self.body_l.addWidget(wrap)

    def add_section_card(self, title: str, subtitle: str = '') -> QVBoxLayout:
        card = QFrame()
        card.setObjectName('DetailSectionCard')
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)
        header = QVBoxLayout()
        header.setSpacing(2)
        ttl = QLabel(title)
        ttl.setObjectName('DetailSectionTitle')
        header.addWidget(ttl)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName('DetailSectionSub')
            sub.setWordWrap(True)
            header.addWidget(sub)
        lay.addLayout(header)
        self.body_l.addWidget(card)
        return lay

    def add_kv_panel(self, title: str, mapping: list[tuple[str, Any]]):
        wrap = self.add_section_card(title)
        g=FormGroup(title)
        g.setTitle('')
        g.form.setContentsMargins(0, 0, 0, 0)
        g.setStyleSheet(f'QGroupBox#FormGroup {{ border: 0; margin-top: 0px; padding-top: 0px; background: transparent; }}')
        for label, value in mapping:
            val=QLabel(format_display_value(label, value)); val.setWordWrap(True); val.setObjectName('DetailValueLabel')
            lab=QLabel(label); lab.setObjectName('DetailKeyLabel')
            normalize_widget_font(val)
            normalize_widget_font(lab)
            g.form.addRow(lab, val)
        wrap.addWidget(g)


class ReturnDialog(AnimatedDialog):
    def __init__(self, shell: 'MainWindow', contract_id: int):
        super().__init__(shell, 'Vrácení strojů', 1180, 860)
        self.shell = shell
        self.contract_id = contract_id
        self.detail = shell.db.get_contract_detail(contract_id)
        self.contract = as_dict(self.detail.get('contract'))
        self.items = [as_dict(i) for i in self.detail.get('items', [])]
        self.item_inputs: list[dict[str, Any]] = []
        self.return_photo_path = ''

        self.return_date = ClickableDateEdit(); setup_date_edit(self.return_date); self.return_date.setDate(QDate.currentDate())
        self.return_date_wrap = make_date_field(self.return_date)
        self.deposit_returned = QLineEdit(str(int(round(parse_float(row_get(self.contract, 'deposit', 0))))))
        self.extra_charge = QLineEdit(str(int(round(parse_float(row_get(self.contract, 'return_extra_charge', 0))))))
        self.notes = QPlainTextEdit(str(row_get(self.contract, 'notes', '')))
        self.notes.setFixedHeight(90)

        top = FormGroup('Uzavření smlouvy')
        top.form.addRow('Datum vrácení', self.return_date_wrap)
        top.form.addRow('Vrácená kauce', self.deposit_returned)
        top.form.addRow('Doplatek / škoda', self.extra_charge)
        top.form.addRow('Poznámka ke smlouvě', self.notes)
        self.body_l.addWidget(top)

        for item in self.items:
            panel = FormGroup(f"{row_get(item, 'machine_name') or row_get(item, 'name')} · {row_get(item, 'inventory_number') or 'bez čísla'}")
            return_condition = QLineEdit(str(row_get(item, 'return_condition', '')))
            accessories_returned = QPlainTextEdit(str(row_get(item, 'accessories_returned', row_get(item, 'accessories_issued', ''))))
            accessories_returned.setFixedHeight(70)
            damage_notes = QPlainTextEdit(str(row_get(item, 'damage_notes', '')))
            damage_notes.setFixedHeight(70)
            panel.form.addRow('Stav při vrácení', return_condition)
            panel.form.addRow('Vrácené příslušenství', accessories_returned)
            panel.form.addRow('Poškození / poznámka', damage_notes)
            self.body_l.addWidget(panel)
            self.item_inputs.append({
                'contract_item_id': int(row_get(item, 'id', 0) or 0),
                'machine_id': int(row_get(item, 'machine_id', 0) or 0),
                'return_condition': return_condition,
                'accessories_returned': accessories_returned,
                'damage_notes': damage_notes,
            })

        self.save_btn.setText('Uložit vrácení')
        self.save_btn.clicked.connect(self.save)

    def save(self):
        returned_at = self.return_date.date().toPython().strftime('%Y-%m-%d')
        deposit_returned = parse_float(self.deposit_returned.text())
        extra_charge = parse_float(self.extra_charge.text())
        self.shell.db.conn.execute("BEGIN")
        try:
            self.shell.db.conn.execute(
                "UPDATE contracts SET returned_at=?, return_date=?, deposit_returned=?, return_extra_charge=?, status='vráceno', notes=? WHERE id=?",
                (returned_at, returned_at, deposit_returned, extra_charge, self.notes.toPlainText().strip(), self.contract_id),
            )
            for row in self.item_inputs:
                self.shell.db.conn.execute(
                    "UPDATE contract_items SET return_condition=?, accessories_returned=?, damage_notes=? WHERE id=?",
                    (
                        row['return_condition'].text().strip(),
                        row['accessories_returned'].toPlainText().strip(),
                        row['damage_notes'].toPlainText().strip(),
                        row['contract_item_id'],
                    ),
                )
                self.shell.db.recompute_machine_status(int(row['machine_id']))
            self.shell.db.conn.commit()
        except Exception:
            self.shell.db.conn.rollback()
            raise
        self.saved.emit()
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.pdf = PDFGenerator()
        self.current_theme = load_theme()
        sync_theme_globals(self.current_theme)
        self.setWindowTitle('Půjčovna strojů · Qt Full')
        self.resize(1780, 1060)
        self.setMinimumSize(1440, 900)
        self.setStyleSheet(build_stylesheet(self.current_theme))
        central=QWidget(); self.setCentralWidget(central)
        root=QHBoxLayout(central); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        rail=QFrame(); rail.setObjectName('Rail'); rail.setFixedWidth(260)
        rl=QVBoxLayout(rail); rl.setContentsMargins(18,18,18,18); rl.setSpacing(12)
        brand=QFrame(); brand.setObjectName('Brand'); bl=QVBoxLayout(brand); bl.setContentsMargins(16,16,16,16); bl.setSpacing(6)
        self.rail_date = QLabel('')
        self.rail_date.setObjectName('BrandTitle')
        self.rail_tasks = QLabel('')
        self.rail_tasks.setObjectName('BrandSub')
        self.rail_tasks.setWordWrap(True)
        bl.addWidget(self.rail_date)
        bl.addWidget(self.rail_tasks)
        rl.addWidget(brand)
        sec_nav = QLabel('NAVIGACE')
        sec_nav.setObjectName('RailSection')
        rl.addWidget(sec_nav)
        self.nav=QListWidget(); self.nav.setObjectName('NavList')
        enable_smooth_scroll(self.nav)
        for name in ['Přehled','Stroje','Zákazníci','Smlouvy','Servis','Nastavení']:
            self.nav.addItem(name)
        self.nav.currentRowChanged.connect(self.switch_page)
        rl.addWidget(self.nav,1)
        root.addWidget(rail)

        main=QWidget(); ml=QVBoxLayout(main); ml.setContentsMargins(0,0,0,0); ml.setSpacing(0)
        top=QFrame(); top.setObjectName('Topbar'); tl=QHBoxLayout(top); tl.setContentsMargins(22,18,22,18)
        self.title_lbl=QLabel('Přehled'); self.title_lbl.setObjectName('TopTitle'); tl.addWidget(self.title_lbl)
        tl.addStretch(1)
        self.search_global=QLineEdit(); self.search_global.setPlaceholderText('Ctrl+K · hledání'); self.search_global.returnPressed.connect(self.open_search); self.search_global.setMinimumWidth(280)
        tl.addWidget(self.search_global)
        self.header_actions = QHBoxLayout(); self.header_actions.setSpacing(8)
        for text_btn, cb in [('Nová smlouva', self.new_contract), ('Nový zákazník', self.new_customer), ('Nový stroj', self.new_machine), ('Nový servis', self.new_service)]:
            btn=QPushButton(text_btn)
            btn.setObjectName('PrimaryBtn' if text_btn=='Nová smlouva' else 'GhostBtn')
            btn.clicked.connect(cb)
            self.header_actions.addWidget(btn)
        tl.addLayout(self.header_actions)
        ml.addWidget(top)
        self.stack=QStackedWidget(); ml.addWidget(self.stack,1)
        root.addWidget(main,1)

        self.dashboard=DashboardPage(self)
        self.pages=[self.dashboard, MachinesPage(self), CustomersPage(self), ContractsPage(self), ServicesPage(self), SettingsPage(self)]
        for p in self.pages: self.stack.addWidget(p)
        self.nav.setCurrentRow(0)
        self.refresh_rail_overview()
        action=QAction(self); action.setShortcut('Ctrl+K'); action.triggered.connect(self.open_search); self.addAction(action)
        self.normalize_ui_fonts()

    def apply_theme(self, theme: str | None = None):
        self.current_theme = (theme or self.current_theme or 'dark').strip().lower()
        if self.current_theme not in {'dark', 'light'}:
            self.current_theme = 'dark'
        sync_theme_globals(self.current_theme)
        self.setStyleSheet(build_stylesheet(self.current_theme))
        self.normalize_ui_fonts()
        self.update()
        if hasattr(self, 'pages'):
            for page in self.pages:
                page.update()

    def normalize_ui_fonts(self):
        normalize_widget_font(self)
        for widget in self.findChildren(QWidget):
            normalize_widget_font(widget)

    def make_table(self, columns: list[str]) -> QTableWidget:
        tbl=QTableWidget(0, len(columns))
        if columns:
            tbl.setHorizontalHeaderLabels(columns)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        tbl.verticalHeader().setVisible(False)
        tbl.verticalHeader().setDefaultSectionSize(42)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        tbl.setShowGrid(True)
        tbl.setGridStyle(Qt.SolidLine)
        tbl.setAlternatingRowColors(True)
        tbl.setFocusPolicy(Qt.NoFocus)
        tbl.setWordWrap(False)
        enable_smooth_scroll(tbl)
        return tbl

    def fill_table(self, table: QTableWidget, rows: list[list[Any]], ids: list[int] | None = None):
        table.setRowCount(0)
        ids = ids or [0] * len(rows)
        status_cols = [i for i in range(table.columnCount()) if contains_status_column(table.horizontalHeaderItem(i).text() if table.horizontalHeaderItem(i) else '')]
        for r, row in enumerate(rows):
            table.insertRow(r)
            for c, val in enumerate(row):
                header_text = table.horizontalHeaderItem(c).text() if table.horizontalHeaderItem(c) else ''
                item = QTableWidgetItem(format_display_value(header_text, val))
                if c == 0:
                    item.setData(Qt.UserRole, ids[r])
                if c == 0:
                    font = ensure_valid_font(item)
                    font.setBold(True)
                    item.setFont(font)
                item.setTextAlignment(resolve_table_alignment(header_text, val, c in status_cols))
                if c in status_cols:
                    tone = status_tone(val)
                    if tone:
                        font = ensure_valid_font(item)
                        font.setBold(True)
                        item.setFont(font)
                        item.setBackground(soft_tone(tone))
                        item.setForeground(QColor(tone))
                elif c > 0:
                    item.setForeground(QColor(TEXT))
                table.setItem(r, c, item)

    def current_table_id(self, table: QTableWidget) -> int | None:
        items = table.selectedItems()
        if not items:
            return None
        item = table.item(items[0].row(), 0)
        return int(item.data(Qt.UserRole) or 0) if item else None

    def switch_page(self, idx: int):
        if idx < 0: return
        self.stack.setCurrentIndex(idx)
        page=self.pages[idx]
        self.title_lbl.setText(page.title)
        try:
            page.refresh()
        except Exception as exc:
            self.toast(f'Obnovení stránky selhalo: {exc}','warn')
        page.fade_in(150)
        self.refresh_rail_overview()

    def refresh_all(self):
        for p in self.pages:
            try: p.refresh()
            except Exception: pass
        self.refresh_rail_overview()
        self.toast('Data obnovena.','ok')

    def refresh_rail_overview(self):
        today = date.today()
        self.rail_date.setText(today.strftime('%d.%m.%Y'))
        try:
            returns_today = int(float(self.db.get_dashboard_stats().get('returns_today', 0) or 0))
            reservations_today = int(
                self.db.fetchone(
                    "SELECT COUNT(*) AS c FROM reservations WHERE COALESCE(reserved_from,'')=? AND status IN ('rezervace','potvrzeno')",
                    (today.strftime('%Y-%m-%d'),),
                )['c'] or 0
            )
        except Exception:
            returns_today = 0
            reservations_today = 0
        total = returns_today + reservations_today
        if total == 0:
            self.rail_tasks.setText('Dnes bez plánovaných vratek a rezervací.')
        else:
            self.rail_tasks.setText(f'{returns_today} vratek · {reservations_today} rezervací')

    def toast(self, text: str, tone: str = 'info'):
        t=Toast(self.centralWidget(), text, tone)
        area=self.centralWidget().rect(); t.move(area.width()-t.width()-20, area.height()-t.height()-20); t.show()

    def open_data_dir(self):
        try:
            folder = Path(self.db.db_path).parent if hasattr(self.db, 'db_path') else Path.cwd()
            QMessageBox.information(self, 'Data aplikace', str(folder))
        except Exception as exc:
            QMessageBox.warning(self, 'Data aplikace', str(exc))

    def backup_db(self):
        try:
            path=self.db.backup_database(); self.toast(f'Záloha vytvořena: {Path(path).name}','ok')
        except Exception as exc:
            QMessageBox.critical(self,'Chyba',str(exc))

    def _update_settings(self) -> dict[str, str]:
        try:
            return self.db.get_settings()
        except Exception:
            return {}

    def _update_repo(self) -> str:
        return str(self._update_settings().get('github_repo', '')).strip().strip('/')

    def _update_asset_name(self) -> str:
        return str(self._update_settings().get('github_asset_name', '')).strip() or RELEASE_ASSET_NAME

    def _current_binary_path(self) -> Path | None:
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).resolve()
        return None

    def _write_update_script(self, current_exe: Path, downloaded_exe: Path) -> Path:
        script_path = UPDATES_DIR / 'apply_update.cmd'
        script = textwrap.dedent(f"""
            @echo off
            setlocal
            set "SRC={downloaded_exe}"
            set "DST={current_exe}"
            ping 127.0.0.1 -n 3 > nul
            :retry
            copy /Y "%SRC%" "%DST%" > nul
            if errorlevel 1 (
                ping 127.0.0.1 -n 2 > nul
                goto retry
            )
            start "" "%DST%"
            del "%SRC%" > nul 2> nul
            del "%~f0" > nul 2> nul
        """).strip()
        script_path.write_text(script, encoding='utf-8')
        return script_path

    def _download_update_with_progress(self, download_url: str, target_path: Path) -> None:
        req = urllib.request.Request(download_url, headers={'User-Agent': f'{APP_NAME}/{APP_VERSION}'})
        progress = QProgressDialog('Stahuji aktualizaci...', None, 0, 100, self)
        progress.setWindowTitle('Aktualizace')
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setCancelButton(None)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        try:
            with urllib.request.urlopen(req, timeout=60) as response, target_path.open('wb') as fh:
                total_bytes = int(response.headers.get('Content-Length') or 0)
                downloaded = 0
                chunk_size = 1024 * 256
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if total_bytes > 0:
                        percent = min(100, int(downloaded * 100 / total_bytes))
                        progress.setLabelText(f'Stahuji aktualizaci... {percent} %')
                        progress.setValue(percent)
                    else:
                        spinner = 5 + (downloaded // chunk_size) % 90
                        progress.setLabelText('Stahuji aktualizaci...')
                        progress.setValue(int(spinner))
                    QApplication.processEvents()
            progress.setLabelText('Dokončuji instalaci...')
            progress.setValue(100)
            QApplication.processEvents()
        finally:
            progress.close()

    def check_for_updates(self):
        repo = self._update_repo()
        if not repo:
            QMessageBox.information(self, 'Aktualizace', 'Nejdřív v nastavení vyplň GitHub repo ve tvaru uzivatel/repozitar.')
            return
        try:
            release = github_latest_release(repo)
        except urllib.error.HTTPError as exc:
            QMessageBox.warning(self, 'Aktualizace', f'Kontrola aktualizace selhala: {exc.code}')
            return
        except Exception as exc:
            QMessageBox.warning(self, 'Aktualizace', f'Kontrola aktualizace selhala: {exc}')
            return

        latest_version = normalize_version_tag(str(release.get('tag_name') or ''))
        if version_key(latest_version) <= version_key(APP_VERSION):
            self.toast('Používáš aktuální verzi aplikace.', 'ok')
            return

        asset_name = self._update_asset_name()
        asset = next((a for a in release.get('assets', []) if str(a.get('name') or '') == asset_name), None)
        if not asset:
            QMessageBox.warning(self, 'Aktualizace', f'Ve verzi {latest_version} nebyl nalezen soubor {asset_name}.')
            return

        current_exe = self._current_binary_path()
        if current_exe is None:
            QMessageBox.information(self, 'Aktualizace', 'Automatická aktualizace funguje z finálního .exe buildu, ne při spuštění ze zdrojáku.')
            return

        if QMessageBox.question(
            self,
            'Aktualizace',
            f'Je dostupná verze {latest_version}.\\n\\nAktuální verze: {APP_VERSION}\\nStáhnout a nainstalovat aktualizaci teď?'
        ) != QMessageBox.Yes:
            return

        download_url = str(asset.get('browser_download_url') or '').strip()
        if not download_url:
            QMessageBox.warning(self, 'Aktualizace', 'Release neobsahuje platný odkaz ke stažení.')
            return

        try:
            tmp_dir = Path(tempfile.mkdtemp(prefix='pujcovna_update_', dir=str(UPDATES_DIR)))
            downloaded_exe = tmp_dir / asset_name
            self._download_update_with_progress(download_url, downloaded_exe)
            script_path = self._write_update_script(current_exe, downloaded_exe)
            subprocess.Popen(['cmd', '/c', str(script_path)], close_fds=True)
            QMessageBox.information(self, 'Aktualizace', 'Aktualizace je stažená. Aplikace se teď zavře a spustí novou verzi.')
            QApplication.instance().quit()
        except Exception as exc:
            QMessageBox.warning(self, 'Aktualizace', f'Stažení aktualizace selhalo: {exc}')

    def export_current_page(self, page: EntityPage):
        if isinstance(page, MachinesPage): table='machines'
        elif isinstance(page, CustomersPage): table='customers'
        elif isinstance(page, ServicesPage): table='service_records'
        elif isinstance(page, ContractsPage): table='contracts' if page.mode.currentText()=='Smlouvy' else 'reservations'
        else: return
        try:
            path=self.db.export_table_to_csv(table, table)
            self.toast(f'Export vytvořen: {Path(path).name}','ok')
        except Exception as exc:
            QMessageBox.critical(self,'Chyba exportu',str(exc))

    def open_search(self):
        SearchDialog(self).exec()

    def new_customer(self):
        dlg=CustomerDialog(self); dlg.saved.connect(self.refresh_all); dlg.exec()

    def edit_customer(self, customer_id: int):
        dlg=CustomerDialog(self, customer_id); dlg.saved.connect(self.refresh_all); dlg.exec()

    def open_customer_detail(self, customer_id: int):
        customer=as_dict(self.db.fetchone('SELECT * FROM customers WHERE id=?',(customer_id,)))
        summary=self.db.get_customer_summary(customer_id)
        dlg=DetailDialog(self,'Detail zákazníka')
        dlg.set_summary(f"{row_get(customer,'full_name') or row_get(customer,'name')} · {row_get(customer,'company') or 'Soukromá osoba'}", [f"Aktivní smlouvy: {summary.get('active_contracts',0)}", f"Rezervace: {summary.get('active_reservations',0)}", f"Tržby: {fmt_money(summary.get('revenue',0))}"])
        dlg.add_header_action('Upravit zákazníka', lambda: (dlg.accept(), self.edit_customer(customer_id)), 'PrimaryBtn')
        dlg.add_kv_panel('Základ', [('Jméno', row_get(customer,'name')), ('Celé jméno', row_get(customer,'full_name')), ('Firma', row_get(customer,'company')), ('Telefon', row_get(customer,'phone')), ('E-mail', row_get(customer,'email')), ('Adresa', row_get(customer,'address')), ('Poznámka', row_get(customer,'notes'))])
        dlg.add_stat_strip([('Aktivní smlouvy', summary.get('active_contracts',0)), ('Aktivní rezervace', summary.get('active_reservations',0)), ('Celkové tržby', fmt_money(summary.get('revenue',0)))])
        table=self.make_table(['Smlouva/Rez.','Od','Do','Stav','Cena'])
        rows=[]; ids=[]
        for r in [as_dict(x) for x in summary.get('contracts',[])]: rows.append([row_get(r,'contract_number'), row_get(r,'rental_from'), row_get(r,'rental_to'), row_get(r,'status'), fmt_money(row_get(r,'total_price'))]); ids.append(int(row_get(r,'id',0) or 0))
        for r in [as_dict(x) for x in summary.get('reservations',[])]: rows.append([row_get(r,'reservation_number'), row_get(r,'reserved_from'), row_get(r,'reserved_to'), row_get(r,'status'), fmt_money(row_get(r,'total_price'))]); ids.append(int(row_get(r,'id',0) or 0))
        self.fill_table(table, rows, ids)
        table.itemDoubleClicked.connect(lambda *_: (self.open_contract_detail(self.current_table_id(table)) if 'PS-' in (table.item(table.currentRow(),0).text() if table.currentRow()>=0 else '') else self.open_reservation_detail(self.current_table_id(table))))
        panel=Panel('Historie'); panel.content.addWidget(table); dlg.body_l.addWidget(panel)
        dlg.exec()

    def new_machine(self):
        dlg=MachineDialog(self); dlg.saved.connect(self.refresh_all); dlg.exec()

    def edit_machine(self, machine_id: int):
        dlg=MachineDialog(self, machine_id); dlg.saved.connect(self.refresh_all); dlg.exec()

    def open_machine_detail(self, machine_id: int):
        machine=as_dict(self.db.fetchone('SELECT * FROM machines WHERE id=?',(machine_id,)))
        summary=self.db.get_machine_summary(machine_id)
        dlg=DetailDialog(self,'Detail stroje')
        dlg.set_summary(f"{row_get(machine,'name')} · {row_get(machine,'category')}", [f"Stav: {row_get(machine,'status')}", f"Denní sazba: {fmt_money(row_get(machine,'daily_rate'))}", f"Kauce: {fmt_money(row_get(machine,'deposit'))}"])
        dlg.add_header_action('Upravit stroj', lambda: (dlg.accept(), self.edit_machine(machine_id)), 'PrimaryBtn')
        dlg.add_header_action('Nový servis', lambda: (dlg.accept(), self.new_service(machine_id)), 'GhostBtn')
        rows=[]; ids=[]
        for r in [as_dict(x) for x in summary.get('contracts',[])]: rows.append([row_get(r,'contract_number'), row_get(r,'rental_from'), row_get(r,'rental_to'), row_get(r,'status'), fmt_money(row_get(r,'total_price'))]); ids.append(int(row_get(r,'id',0) or 0))
        hist=self.make_table(['Smlouva','Od','Do','Stav','Cena']); self.fill_table(hist, rows, ids)
        hist.itemDoubleClicked.connect(lambda *_: self.open_contract_detail(self.current_table_id(hist)))
        p=Panel('Historie zápůjček'); p.content.addWidget(hist); dlg.body_l.addWidget(p)
        srows=[]; sids=[]
        for r in [as_dict(x) for x in summary.get('service_records',[])]: srows.append([row_get(r,'service_date'), row_get(r,'service_type'), fmt_money(row_get(r,'cost')), row_get(r,'status')]); sids.append(int(row_get(r,'id',0) or 0))
        st=self.make_table(['Datum','Typ','Cena','Stav']); self.fill_table(st, srows, sids)
        st.itemDoubleClicked.connect(lambda *_: self.open_service_detail(self.current_table_id(st)))
        p2=Panel('Servisní historie'); p2.content.addWidget(st); dlg.body_l.addWidget(p2)
        photos=[as_dict(r) for r in self.db.get_machine_photos(machine_id)]
        if photos:
            p3=Panel('Fotky')
            for ph in photos[:8]: p3.content.addWidget(QLabel(f"{row_get(ph,'caption') or Path(row_get(ph,'path')).name} · {row_get(ph,'path')}"))
            dlg.body_l.addWidget(p3)
        dlg.exec()

    def new_service(self, machine_id: int | None = None):
        dlg=ServiceDialog(self, None, machine_id); dlg.saved.connect(self.refresh_all); dlg.exec()

    def edit_service(self, record_id: int):
        dlg=ServiceDialog(self, record_id); dlg.saved.connect(self.refresh_all); dlg.exec()

    def open_service_detail(self, record_id: int):
        rec=as_dict(self.db.fetchone("SELECT s.*, m.name AS machine_name FROM service_records s LEFT JOIN machines m ON m.id=s.machine_id WHERE s.id=?", (record_id,)))
        dlg=DetailDialog(self,'Servisní záznam')
        dlg.set_summary(f"{row_get(rec,'machine_name')} · {row_get(rec,'service_type') or 'Servis'}", [f"Datum: {row_get(rec,'service_date')}", f"Stav: {row_get(rec,'status')}", f"Cena: {fmt_money(row_get(rec,'cost'))}"])
        dlg.add_header_action('Upravit', lambda: (dlg.accept(), self.edit_service(record_id)), 'PrimaryBtn')
        dlg.add_header_action('PDF protokol', lambda: self._create_service_pdf(rec), 'GhostBtn')
        dlg.add_kv_panel('Servis', [('Stroj', row_get(rec,'machine_name')), ('Datum', row_get(rec,'service_date')), ('Typ', row_get(rec,'service_type')), ('Cena', fmt_money(row_get(rec,'cost'))), ('Dodavatel', row_get(rec,'provider')), ('Stav', row_get(rec,'status')), ('MH při servisu', row_get(rec,'service_motohours')), ('Další servis datum', row_get(rec,'next_service_date')), ('Další servis MH', row_get(rec,'next_service_motohours')), ('Poznámka', row_get(rec,'notes'))])
        dlg.exec()

    def _create_service_pdf(self, rec: dict[str, Any]):
        try:
            machine=self.db.fetchone('SELECT * FROM machines WHERE id=?',(row_get(rec,'machine_id'),))
            self.pdf.create_service_protocol_pdf(machine, rec)
            self.toast('PDF servisu vytvořeno.','ok')
        except Exception as exc:
            self.toast(f'Vytvoření PDF servisu selhalo: {exc}','warn')

    def new_reservation(self):
        dlg=ReservationDialog(self); dlg.saved.connect(self.refresh_all); dlg.exec()

    def new_contract(self):
        dlg=ContractDialog(self); dlg.saved.connect(self.refresh_all); dlg.exec()

    def open_contract_detail(self, contract_id: int | None):
        if not contract_id: return
        detail=self.db.get_contract_detail(contract_id); contract=as_dict(detail['contract']); items=[as_dict(i) for i in detail['items']]
        dlg=DetailDialog(self,'Detail smlouvy')
        dlg.set_summary(f"{row_get(contract,'contract_number')} · {row_get(contract,'customer_name')}", [f"Stav: {row_get(contract,'status')}", f"Cena: {fmt_money(row_get(contract,'total_price'))}", f"Uhrazeno: {fmt_money(row_get(contract,'paid_amount'))}"])
        if row_get(contract,'status')!='vráceno':
            dlg.add_header_action('Vrátit stroje', lambda: (dlg.accept(), self.return_contract(contract_id)), 'PrimaryBtn')
        dlg.add_header_action('Otevřít PDF', lambda: self.pdf.open_pdf(row_get(contract,'contract_number')), 'GhostBtn')
        dlg.add_header_action('Vratný protokol', lambda: self.open_return_protocol(contract_id), 'GhostBtn')
        dlg.add_header_action('Smazat', lambda: (self.delete_contract_record(contract_id), dlg.accept()), 'GhostBtn')
        dlg.add_stat_strip([('Od', row_get(contract,'rental_from')), ('Do', row_get(contract,'rental_to')), ('Kauce', fmt_money(row_get(contract,'deposit')))])
        dlg.add_kv_panel('Smlouva', [('Číslo', row_get(contract,'contract_number')), ('Zákazník', row_get(contract,'customer_name')), ('Od', row_get(contract,'rental_from')), ('Do', row_get(contract,'rental_to')), ('Typ sazby', pricing_mode_label(str(row_get(contract,'pricing_mode') or 'day'))), ('Stav', row_get(contract,'status')), ('Cena', fmt_money(row_get(contract,'total_price'))), ('Kauce', fmt_money(row_get(contract,'deposit'))), ('Uhrazeno', fmt_money(row_get(contract,'paid_amount'))), ('Vráceno', row_get(contract,'returned_at')), ('Poznámka', row_get(contract,'notes'))])
        table=self.make_table(['Stroj','Kategorie','Stav výdeje','Stav vrácení','Příslušenství'])
        self.fill_table(table, [[row_get(i,'machine_name'), row_get(i,'category'), row_get(i,'issue_condition'), row_get(i,'return_condition'), row_get(i,'accessories_issued')] for i in items], [int(row_get(i,'machine_id',0) or 0) for i in items])
        p=Panel('Položky smlouvy'); p.content.addWidget(table); dlg.body_l.addWidget(p)
        dlg.exec()

    def open_reservation_detail(self, reservation_id: int | None):
        if not reservation_id: return
        detail=self.db.get_reservation_detail(reservation_id); reservation=as_dict(detail['reservation']); items=[as_dict(i) for i in detail['items']]
        dlg=DetailDialog(self,'Detail rezervace')
        dlg.set_summary(f"{row_get(reservation,'reservation_number')} · {row_get(reservation,'customer_name')}", [f"Stav: {row_get(reservation,'status')}", f"Cena: {fmt_money(row_get(reservation,'total_price'))}", f"Kauce: {fmt_money(row_get(reservation,'deposit'))}"])
        dlg.add_header_action('Smazat rezervaci', lambda: (self.delete_reservation_record(reservation_id), dlg.accept()), 'GhostBtn')
        dlg.add_stat_strip([('Od', row_get(reservation,'reserved_from')), ('Do', row_get(reservation,'reserved_to')), ('Počet položek', len(items))])
        dlg.add_kv_panel('Rezervace', [('Číslo', row_get(reservation,'reservation_number')), ('Zákazník', row_get(reservation,'customer_name')), ('Od', row_get(reservation,'reserved_from')), ('Do', row_get(reservation,'reserved_to')), ('Stav', row_get(reservation,'status')), ('Cena', fmt_money(row_get(reservation,'total_price'))), ('Kauce', fmt_money(row_get(reservation,'deposit'))), ('Poznámka', row_get(reservation,'notes'))])
        table=self.make_table(['Stroj','Kategorie','Cena']); self.fill_table(table, [[row_get(i,'machine_name'), row_get(i,'category'), fmt_money(row_get(i,'daily_rate'))] for i in items], [int(row_get(i,'machine_id',0) or 0) for i in items])
        p=Panel('Rezervované stroje'); p.content.addWidget(table); dlg.body_l.addWidget(p)
        dlg.exec()

    def delete_contract_record(self, contract_id: int):
        if QMessageBox.question(self,'Smazat','Opravdu smazat smlouvu?')!=QMessageBox.Yes:
            return
        self.db.delete_contract(contract_id)
        self.refresh_all(); self.toast('Smlouva smazána.','ok')

    def delete_reservation_record(self, reservation_id: int):
        if QMessageBox.question(self,'Smazat','Opravdu smazat rezervaci?')!=QMessageBox.Yes:
            return
        self.db.delete_reservation(reservation_id)
        self.refresh_all(); self.toast('Rezervace smazána.','ok')

    def return_contract(self, contract_id: int):
        dlg=ReturnDialog(self, contract_id); dlg.saved.connect(self.refresh_all); dlg.exec()


    def create_machine_label(self, machine_id: int):
        if not machine_id:
            return
        try:
            machine = as_dict(self.db.fetchone('SELECT * FROM machines WHERE id=?', (machine_id,)))
            if not machine:
                self.toast('Stroj nebyl nalezen.', 'warn')
                return
            path = self.pdf.create_machine_label_pdf(machine)
            self.pdf.open_any_pdf(path)
            self.toast('PDF štítek vytvořen.', 'ok')
        except Exception as exc:
            self.toast(f'Vytvoření PDF štítku selhalo: {exc}', 'warn')

    def open_return_protocol(self, contract_id: int | None):
        if not contract_id:
            return
        try:
            detail=self.db.get_contract_detail(contract_id)
            contract=as_dict(detail['contract'])
            customer=self.db.fetchone('SELECT * FROM customers WHERE id=?', (row_get(contract,'customer_id'),))
            path=self.pdf.create_return_protocol_pdf(detail['contract'], customer, detail['items'], self.db.get_settings())
            self.pdf.open_any_pdf(path)
            self.toast('Vratný protokol vytvořen.','ok')
        except Exception as exc:
            self.toast(f'Vytvoření vratného protokolu selhalo: {exc}','warn')


def _open_machine_detail_with_history(self: MainWindow, machine_id: int):
    machine = as_dict(self.db.fetchone('SELECT * FROM machines WHERE id=?', (machine_id,)))
    summary = self.db.get_machine_summary(machine_id)
    stats = as_dict(summary.get('stats'))
    dlg = DetailDialog(self, 'Detail stroje')
    dlg.set_summary(
        f"{row_get(machine, 'name')} | {row_get(machine, 'category')}",
        [
            f"Stav: {row_get(machine, 'status')}",
            f"Denni sazba: {fmt_money(row_get(machine, 'daily_rate'))}",
            f"Kauce: {fmt_money(row_get(machine, 'deposit'))}",
        ],
    )
    dlg.add_header_action('Upravit stroj', lambda: (dlg.accept(), self.edit_machine(machine_id)), 'PrimaryBtn')
    dlg.add_header_action('Novy servis', lambda: (dlg.accept(), self.new_service(machine_id)), 'GhostBtn')
    dlg.add_kv_panel('Zaklad', [
        ('Nazev', row_get(machine, 'name')),
        ('Kategorie', row_get(machine, 'category')),
        ('Inventarni cislo', row_get(machine, 'inventory_number')),
        ('Model', row_get(machine, 'model')),
        ('Seriove cislo', row_get(machine, 'serial_number')),
        ('Stav', row_get(machine, 'status')),
        ('Denni sazba', fmt_money(row_get(machine, 'daily_rate'))),
        ('Kauce', fmt_money(row_get(machine, 'deposit'))),
        ('Motohodiny', row_get(machine, 'motohours')),
        ('Servis pri MH', row_get(machine, 'service_due_motohours')),
        ('Dalsi servis', row_get(machine, 'next_service_date')),
        ('Poznamka', row_get(machine, 'notes')),
    ])
    dlg.add_stat_strip([
        ('Pocet vypujcek', row_get(stats, 'contracts_count', 0)),
        ('Trzby', fmt_money(row_get(stats, 'total_revenue', 0))),
        ('Posledni vratka', row_get(stats, 'last_return') or '-'),
    ])

    timeline_table = self.make_table(['Typ', 'Od', 'Do', 'Partner', 'Stav', 'Castka'])
    timeline_rows = []
    timeline_ids = []
    timeline_kinds: list[str] = []
    for r in [as_dict(x) for x in summary.get('timeline', [])]:
        timeline_rows.append([
            row_get(r, 'event_type'),
            row_get(r, 'date_from'),
            row_get(r, 'date_to'),
            row_get(r, 'partner_name'),
            row_get(r, 'status'),
            fmt_money(row_get(r, 'amount')),
        ])
        timeline_ids.append(int(row_get(r, 'source_id', 0) or 0))
        timeline_kinds.append(str(row_get(r, 'source_kind')))
    self.fill_table(timeline_table, timeline_rows, timeline_ids)

    def _open_timeline_row():
        row = timeline_table.currentRow()
        if row < 0 or row >= len(timeline_kinds):
            return
        item_id = self.current_table_id(timeline_table)
        kind = timeline_kinds[row]
        if kind == 'contract':
            self.open_contract_detail(item_id)
        elif kind == 'reservation':
            self.open_reservation_detail(item_id)
        elif kind == 'service':
            self.open_service_detail(item_id)

    timeline_table.itemDoubleClicked.connect(lambda *_: _open_timeline_row())
    timeline_panel = Panel('Historie stroje', 'Kompletní časová osa půjčení, rezervací a servisních zásahů.')
    timeline_panel.content.addWidget(timeline_table)
    dlg.body_l.addWidget(timeline_panel)

    reservations_table = self.make_table(['Rezervace', 'Od', 'Do', 'Zakaznik', 'Stav'])
    reservation_rows = []
    reservation_ids = []
    for r in [as_dict(x) for x in summary.get('reservations', [])]:
        reservation_rows.append([
            row_get(r, 'reservation_number'),
            row_get(r, 'reserved_from'),
            row_get(r, 'reserved_to'),
            row_get(r, 'customer_name'),
            row_get(r, 'status'),
        ])
        reservation_ids.append(int(row_get(r, 'id', 0) or 0))
    self.fill_table(reservations_table, reservation_rows, reservation_ids)
    reservations_table.itemDoubleClicked.connect(lambda *_: self.open_reservation_detail(self.current_table_id(reservations_table)))
    reservations_panel = Panel('Rezervace stroje')
    reservations_panel.content.addWidget(reservations_table)
    dlg.body_l.addWidget(reservations_panel)

    photos = [as_dict(r) for r in self.db.get_machine_photos(machine_id)]
    if photos:
        p3 = Panel('Fotky')
        for ph in photos[:8]:
            p3.content.addWidget(QLabel(f"{row_get(ph, 'caption') or Path(row_get(ph, 'path')).name} | {row_get(ph, 'path')}"))
        dlg.body_l.addWidget(p3)
    dlg.exec()


MainWindow.open_machine_detail = _open_machine_detail_with_history


_machine_dialog_save_original = MachineDialog.save
_reservation_dialog_init_original = ReservationDialog.__init__


def _safe_machine_dialog_save(self: MachineDialog):
    try:
        _machine_dialog_save_original(self)
    except sqlite3.IntegrityError as exc:
        message = str(exc)
        if 'inventory_number' in message:
            QMessageBox.warning(self, 'Duplicitni inventarni cislo', 'Stroj s timto inventarnim cislem uz existuje.')
            return
        raise


def _safe_reservation_dialog_init(self: ReservationDialog, shell: 'MainWindow', reservation_id: int | None = None):
    _reservation_dialog_init_original(self, shell, reservation_id)
    self.from_date.dateChanged.connect(lambda *_: self.refresh_machine_table())
    self.to_date.dateChanged.connect(lambda *_: self.refresh_machine_table())


def _safe_reservation_refresh_machine_table(self: ReservationDialog):
    rows=[]; ids=[]
    d1=self.from_date.date().toPython().strftime('%Y-%m-%d')
    d2=self.to_date.date().toPython().strftime('%Y-%m-%d')
    for m in self.machine_rows:
        mid=int(row_get(m,'id',0) or 0)
        conflicts = self.shell.db.check_machine_conflicts(mid, d1, d2, exclude_reservation_id=self.reservation_id)
        if conflicts and mid not in self.selected_ids:
            continue
        rows.append([row_get(m,'name'), row_get(m,'category'), row_get(m,'status'), fmt_money(row_get(m,'daily_rate'))])
        ids.append(mid)
    self.shell.fill_table(self.machine_table, rows, ids)
    self.selected.clear()
    for m in self.machine_rows:
        mid=int(row_get(m,'id',0) or 0)
        if mid in self.selected_ids:
            self.selected.addItem(f"{row_get(m,'name')} · {row_get(m,'category')}")


def _safe_reservation_toggle_machine(self: ReservationDialog):
    row_id=self.shell.current_table_id(self.machine_table)
    if not row_id:
        return
    if row_id in self.selected_ids:
        self.selected_ids.remove(row_id)
        self.refresh_machine_table()
        return
    d1=self.from_date.date().toPython().strftime('%Y-%m-%d')
    d2=self.to_date.date().toPython().strftime('%Y-%m-%d')
    conflicts = self.shell.db.check_machine_conflicts(row_id, d1, d2, exclude_reservation_id=self.reservation_id)
    if conflicts:
        QMessageBox.warning(self, 'Kolize rezervace', '\n'.join(conflicts[:8]))
        return
    self.selected_ids.add(row_id)
    self.refresh_machine_table()


def _safe_reservation_save(self: ReservationDialog):
    cid=self.customer.currentData()
    d1=self.from_date.date().toPython().strftime('%Y-%m-%d')
    d2=self.to_date.date().toPython().strftime('%Y-%m-%d')
    if not cid or not self.selected_ids:
        QMessageBox.warning(self,'Chyba','Vyber zákazníka a alespoň jeden stroj.')
        return
    try:
        self.shell.db.create_reservation_record(
            int(cid),
            d1,
            d2,
            parse_float(self.total_price.text()),
            parse_float(self.deposit.text()),
            self.notes.toPlainText().strip(),
            sorted(self.selected_ids),
            self.reservation_id,
        )
    except ValueError as exc:
        QMessageBox.warning(self, 'Kolize rezervace', str(exc))
        return
    except sqlite3.IntegrityError as exc:
        QMessageBox.warning(self, 'Ulozeni selhalo', str(exc))
        return
    self.saved.emit(); self.accept()


def _safe_contract_save(self: ContractDialog):
    cid=self.customer.currentData(); rental_from=self.rental_from.date().toPython().strftime('%Y-%m-%d'); rental_to=self.rental_to.date().toPython().strftime('%Y-%m-%d')
    if not cid or not self.selected_ids:
        QMessageBox.warning(self,'Chyba','Vyber zákazníka a alespoň jeden stroj.')
        return
    issue_photo=self.issue_photo_path
    if issue_photo:
        dst_dir=PHOTOS_DIR / f'contract_issue_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        dst_dir.mkdir(parents=True, exist_ok=True)
        src=Path(issue_photo); dst=dst_dir / src.name
        if src.exists() and src.resolve()!=dst.resolve():
            shutil.copy2(src,dst)
        issue_photo=str(dst)
    try:
        contract_id = self.shell.db.create_contract_record(
            int(cid),
            rental_from,
            rental_to,
            parse_float(self.total_price.text()),
            parse_float(self.deposit.text()),
            parse_float(self.paid_amount.text()),
            self.payment_method.currentText(),
            issue_photo,
            self.notes.toPlainText().strip(),
            sorted(self.selected_ids),
            self.issue_condition.toPlainText().strip(),
            sorted(self.selected_accessory_ids),
            str(self.pricing_mode.currentData() or 'day'),
        )
    except ValueError as exc:
        QMessageBox.warning(self, 'Kolize smlouvy', str(exc))
        return
    except sqlite3.IntegrityError as exc:
        QMessageBox.warning(self, 'Ulozeni selhalo', str(exc))
        return
    try:
        detail=self.shell.db.get_contract_detail(contract_id); customer=self.shell.db.fetchone('SELECT * FROM customers WHERE id=?',(cid,))
        self.shell.pdf.create_contract_pdf(detail['contract'], customer, detail['items'], self.shell.db.get_settings())
        self.shell.toast('Smlouva vytvořena a PDF připraveno.', 'ok')
    except Exception as exc:
        self.shell.toast(f'PDF smlouvy se nepodařilo vytvořit: {exc}', 'warn')
    self.saved.emit(); self.accept()


MachineDialog.save = _safe_machine_dialog_save
ReservationDialog.__init__ = _safe_reservation_dialog_init
ReservationDialog.refresh_machine_table = _safe_reservation_refresh_machine_table
ReservationDialog.toggle_machine = _safe_reservation_toggle_machine
ReservationDialog.save = _safe_reservation_save
ContractDialog.save = _safe_contract_save


def _fmt_money_clean(v: Any) -> str:
    try:
        return f"{float(v or 0):,.0f} K\u010d".replace(',', ' ')
    except Exception:
        return '0 K\u010d'


def _status_tone_clean(value: Any) -> str:
    txt = str(value or '').strip().lower()
    if txt in {'voln\u00fd', 'dostupn\u00fd', 'aktivn\u00ed', 'vr\u00e1ceno', 'hotovo', 'uhrazeno', 'zaplaceno', 'ok', 'dokon\u010deno'}:
        return GOOD
    if txt in {'rezervace', 'potvrzeno', '\u010dek\u00e1', '\u010dekaj\u00edc\u00ed', 'po term\u00ednu', 'servis', 'upozorn\u011bn\u00ed', 'otev\u0159en\u00fd'}:
        return WARN
    if txt in {'p\u016fj\u010den\u00fd', 'aktivn\u00ed smlouva', 'aktivn\u00ed rezervace'}:
        return ACCENT_2
    if txt in {'neuhrazeno', 'blokovan\u00fd', 'vy\u0159azen\u00fd', 'zru\u0161eno', 'storno', 'probl\u00e9m'}:
        return BAD
    return ''


def _dashboard_refresh_clean(self: DashboardPage):
    stats = self.shell.db.get_dashboard_stats()
    self.c_active.set_data(int(stats.get('contracts_active', 0)), 'Pr\u00e1v\u011b b\u011b\u017e\u00ed')
    self.c_returns.set_data(int(stats.get('returns_today', 0)), 'Na dne\u0161ek')
    self.c_due.set_data(int(stats.get('contracts_overdue', 0)), 'Pot\u0159ebuje kontrolu')
    self.kpi_service.set_data(int(stats.get('service_due', 0)), 'Term\u00edn nebo motohodiny')
    self.kpi_res.set_data(int(stats.get('reservations_active', 0)), '\u010cekaj\u00ed v kalend\u00e1\u0159i')
    self.kpi_unpaid.set_data(int(stats.get('unpaid', 0)), 'K doplacen\u00ed')
    if hasattr(self, 'hero_chip_tasks'):
        self.hero_chip_tasks[1].setText(f"{int(stats.get('contracts_overdue', 0)) + int(stats.get('service_due', 0))} polo\u017eek")
        self.hero_chip_money[1].setText(fmt_money(stats.get('unpaid_amount', 0) or 0))
        self.hero_chip_week[1].setText(f"{int(stats.get('returns_today', 0))} dne\u0161ek / {int(stats.get('reservations_active', 0))} rezervace")
    if hasattr(self, 'hero_focus'):
        if int(stats.get('contracts_overdue', 0)) > 0:
            self.hero_focus.setText('Pot\u0159eba dot\u00e1hnout opo\u017ed\u011bn\u00e9 vratky.')
        elif int(stats.get('unpaid', 0)) > 0:
            self.hero_focus.setText('Pohl\u00eddej otev\u0159en\u00e9 finance.')
        elif int(stats.get('service_due', 0)) > 0:
            self.hero_focus.setText('Servis chce dne\u0161n\u00ed pozornost.')
        else:
            self.hero_focus.setText('Provoz je dnes v klidn\u00e9m rytmu.')

    active_contract_rows = [as_dict(r) for r in self.shell.db.fetchall(
        """
        SELECT c.contract_number, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name,
               COALESCE(c.rental_to, c.end_date, '') AS due_date,
               GROUP_CONCAT(m.name, ', ') AS machines
        FROM contracts c
        LEFT JOIN customers cu ON cu.id=c.customer_id
        LEFT JOIN contract_items ci ON ci.contract_id=c.id
        LEFT JOIN machines m ON m.id=ci.machine_id
        WHERE c.status='aktivní'
        GROUP BY c.id
        ORDER BY CASE WHEN COALESCE(c.rental_to, c.end_date, '')='' THEN '9999-12-31' ELSE COALESCE(c.rental_to, c.end_date, '') END ASC, c.id DESC
        LIMIT 8
        """
    )]
    self.c_active.set_hover_items(
        [f"{row_get(r, 'contract_number')} · {row_get(r, 'customer_name')} · do {fmt_date(row_get(r, 'due_date'))} · {row_get(r, 'machines')}" for r in active_contract_rows],
        'Žádné aktivní smlouvy.',
    )

    return_rows = [as_dict(r) for r in self.shell.db.fetchall(
        """
        SELECT c.contract_number, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name,
               GROUP_CONCAT(m.name, ', ') AS machines
        FROM contracts c
        LEFT JOIN customers cu ON cu.id=c.customer_id
        LEFT JOIN contract_items ci ON ci.contract_id=c.id
        LEFT JOIN machines m ON m.id=ci.machine_id
        WHERE c.status='aktivní' AND COALESCE(c.rental_to, c.end_date, '')=?
        GROUP BY c.id
        ORDER BY c.contract_number
        LIMIT 8
        """,
        (today_str(),),
    )]
    self.c_returns.set_hover_items(
        [f"{row_get(r, 'contract_number')} · {row_get(r, 'customer_name')} · {row_get(r, 'machines')}" for r in return_rows],
        'Na dnešek není plánovaná žádná vratka.',
    )

    overdue_rows = [as_dict(r) for r in self.shell.db.fetchall(
        """
        SELECT c.contract_number, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name,
               COALESCE(c.rental_to, c.end_date, '') AS due_date,
               GROUP_CONCAT(m.name, ', ') AS machines
        FROM contracts c
        LEFT JOIN customers cu ON cu.id=c.customer_id
        LEFT JOIN contract_items ci ON ci.contract_id=c.id
        LEFT JOIN machines m ON m.id=ci.machine_id
        WHERE c.status='po termínu' OR (c.status='aktivní' AND COALESCE(c.rental_to, c.end_date, '') <> '' AND COALESCE(c.rental_to, c.end_date, '') < ?)
        GROUP BY c.id
        ORDER BY COALESCE(c.rental_to, c.end_date, '') ASC, c.id DESC
        LIMIT 8
        """,
        (today_str(),),
    )]
    self.c_due.set_hover_items(
        [f"{row_get(r, 'contract_number')} · {row_get(r, 'customer_name')} · do {fmt_date(row_get(r, 'due_date'))} · {row_get(r, 'machines')}" for r in overdue_rows],
        'Nic není po termínu.',
    )

    service_hover_rows = [as_dict(r) for r in self.shell.db.get_service_due_machines(8)]
    self.kpi_service.set_hover_items(
        [
            ' · '.join(
                part for part in [
                    row_get(r, 'name'),
                    row_get(r, 'category'),
                    f"termín {fmt_date(row_get(r, 'next_service_date'))}" if row_get(r, 'next_service_date') else '',
                    f"MH {row_get(r, 'motohours')}/{row_get(r, 'service_due_motohours')}" if row_get(r, 'service_due_motohours') else '',
                ] if part
            )
            for r in service_hover_rows
        ],
        'Žádný stroj teď nečeká na servis.',
    )

    reservation_rows = [as_dict(r) for r in self.shell.db.fetchall(
        """
        SELECT r.reservation_number, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name,
               COALESCE(r.reserved_from, '') AS reserved_from,
               GROUP_CONCAT(m.name, ', ') AS machines
        FROM reservations r
        LEFT JOIN customers cu ON cu.id=r.customer_id
        LEFT JOIN reservation_items ri ON ri.reservation_id=r.id
        LEFT JOIN machines m ON m.id=ri.machine_id
        WHERE r.status IN ('rezervace','potvrzeno')
        GROUP BY r.id
        ORDER BY COALESCE(r.reserved_from, '') ASC, r.id DESC
        LIMIT 8
        """
    )]
    self.kpi_res.set_hover_items(
        [f"{row_get(r, 'reservation_number')} · {row_get(r, 'customer_name')} · od {fmt_date(row_get(r, 'reserved_from'))} · {row_get(r, 'machines')}" for r in reservation_rows],
        'Žádné aktivní rezervace.',
    )

    unpaid_rows = [as_dict(r) for r in self.shell.db.fetchall(
        """
        SELECT c.contract_number, COALESCE(cu.name, cu.full_name, cu.company, '') AS customer_name,
               (COALESCE(c.total_price,0)+COALESCE(c.deposit,0)+COALESCE(c.return_extra_charge,0)-COALESCE(c.paid_amount,0)) AS due_amount
        FROM contracts c
        LEFT JOIN customers cu ON cu.id=c.customer_id
        WHERE c.status='aktivní'
          AND COALESCE(c.paid_amount,0) < (COALESCE(c.total_price,0)+COALESCE(c.deposit,0)+COALESCE(c.return_extra_charge,0))
        ORDER BY due_amount DESC, c.id DESC
        LIMIT 8
        """
    )]
    self.kpi_unpaid.set_hover_items(
        [f"{row_get(r, 'contract_number')} · {row_get(r, 'customer_name')} · dluh {fmt_money(row_get(r, 'due_amount'))}" for r in unpaid_rows],
        'Všechny aktivní smlouvy jsou uhrazené.',
    )

    recent = [as_dict(r) for r in self.shell.db.get_recent_contracts(12)]
    self.shell.fill_table(
        self.recent,
        [[row_get(r, 'contract_number'), row_get(r, 'customer_name'), row_get(r, 'rental_from'), row_get(r, 'rental_to'), row_get(r, 'status'), fmt_money(row_get(r, 'total_price'))] for r in recent],
        [int(row_get(r, 'id', 0) or 0) for r in recent],
    )
    due = [as_dict(r) for r in self.shell.db.get_upcoming_returns(12)]
    self.shell.fill_table(
        self.returns,
        [[row_get(r, 'contract_number'), row_get(r, 'customer_name'), row_get(r, 'rental_to') or row_get(r, 'end_date'), row_get(r, 'machines')] for r in due],
        [int(row_get(r, 'id', 0) or 0) for r in due],
    )

    self.attention.clear_items()
    alerts = [as_dict(r) for r in self.shell.db.get_deadline_alerts(12)]
    for r in alerts:
        alert_type = str(row_get(r, 'alert_type'))
        if alert_type == 'contract_overdue':
            subtitle = f"{row_get(r, 'customer_name')} \u00b7 do {row_get(r, 'event_date')} \u00b7 {row_get(r, 'machines')}"
            self.attention.add_item(f"Po term\u00ednu \u00b7 {row_get(r, 'ref')}", subtitle, int(row_get(r, 'source_id', 0) or 0), 'contract', BAD)
        elif alert_type == 'contract_unpaid':
            subtitle = f"{row_get(r, 'customer_name')} \u00b7 dluh {fmt_money(row_get(r, 'amount'))}"
            self.attention.add_item(f"Neuhrazeno \u00b7 {row_get(r, 'ref')}", subtitle, int(row_get(r, 'source_id', 0) or 0), 'contract', WARN)
        elif alert_type == 'contract_due_soon':
            subtitle = f"{row_get(r, 'customer_name')} \u00b7 vratka {row_get(r, 'event_date')}"
            self.attention.add_item(f"Bl\u00ed\u017e\u00ed se vratka \u00b7 {row_get(r, 'ref')}", subtitle, int(row_get(r, 'source_id', 0) or 0), 'contract', ACCENT_2)
        elif alert_type == 'reservation_soon':
            subtitle = f"{row_get(r, 'customer_name')} \u00b7 start {row_get(r, 'event_date')} \u00b7 {row_get(r, 'machines')}"
            self.attention.add_item(f"Bl\u00ed\u017e\u00ed se rezervace \u00b7 {row_get(r, 'ref')}", subtitle, int(row_get(r, 'source_id', 0) or 0), 'reservation', ACCENT)
    service_due = [as_dict(r) for r in self.shell.db.get_service_due_machines(4)]
    for r in service_due:
        subtitle = f"{row_get(r, 'category')}"
        if row_get(r, 'next_service_date'):
            subtitle += f" \u00b7 term\u00edn {row_get(r, 'next_service_date')}"
        if row_get(r, 'service_due_motohours'):
            subtitle += f" \u00b7 MH {row_get(r, 'motohours')}/{row_get(r, 'service_due_motohours')}"
        self.attention.add_item(f"Servis \u00b7 {row_get(r, 'name')}", subtitle, int(row_get(r, 'id', 0) or 0), 'machine', ACCENT_2)
    if self.attention.list.count() == 0:
        self.attention.add_item('Bez urgentn\u00edch \u00fakol\u016f', 'Term\u00edny i dluhy jsou pod kontrolou.', None, 'contract', GOOD)

    self.today.clear_items()
    today_rows = [as_dict(r) for r in self.shell.db.get_upcoming_returns(8)]
    for r in today_rows[:6]:
        self.today.add_item(
            f"Vratka \u00b7 {row_get(r, 'contract_number')}",
            f"{row_get(r, 'customer_name')} \u00b7 {row_get(r, 'rental_to') or row_get(r, 'end_date')} \u00b7 {row_get(r, 'machines')}",
            int(row_get(r, 'id', 0) or 0),
            'contract',
            WARN,
        )
    reservations = [as_dict(r) for r in self.shell.db.get_upcoming_reservations(8)]
    for r in reservations[:6]:
        self.today.add_item(
            f"Rezervace \u00b7 {row_get(r, 'reservation_number')}",
            f"{row_get(r, 'customer_name')} \u00b7 od {row_get(r, 'reserved_from')} \u00b7 {row_get(r, 'machines')}",
            int(row_get(r, 'id', 0) or 0),
            'reservation',
            ACCENT_2,
        )
    if self.today.list.count() == 0:
        self.today.add_item('Nic napl\u00e1novan\u00e9ho', 'Dnes ani z\u00edtra nejsou pl\u00e1novan\u00e9 vratky nebo rezervace.', None, 'contract', GOOD)

    activity_key = self.chart_activity.current_filter_key('7d')
    activity_days = {'7d': 7, '14d': 14, '30d': 30}.get(activity_key, 7)
    self.chart_activity.title.setText(f"Nov\u00e9 smlouvy za {activity_days} dn\u00ed")
    activity = []
    for i in range(activity_days - 1, -1, -1):
        d = date.today() - timedelta(days=i)
        row = self.shell.db.fetchone("SELECT COUNT(*) AS c FROM contracts WHERE created_at LIKE ?", (f"{d.strftime('%Y-%m-%d')}%",))
        activity.append((d.strftime('%d.%m'), int(row_get(as_dict(row), 'c', 0) or 0)))
    activity_total = sum(value for _, value in activity)
    self.chart_activity.set_data(
        activity,
        f"Nov\u011b vytvo\u0159en\u00e9 smlouvy za posledn\u00edch {activity_days} dn\u00ed.",
        summary=f"Celkem {activity_total}",
    )

    revenue_key = self.chart_revenue.current_filter_key('6m')
    revenue_months = {'3m': 3, '6m': 6, '12m': 12}.get(revenue_key, 6)
    self.chart_revenue.title.setText(f"Tr\u017eba za {revenue_months} m\u011bs\u00edc\u016f")
    months = []
    month_cursor = date.today().replace(day=1)
    for _ in range(revenue_months):
        months.append(month_cursor)
        month_cursor = (month_cursor.replace(day=1) - timedelta(days=1)).replace(day=1)
    months = list(reversed(months))
    revenue = []
    for month_start in months:
        start = month_start.strftime('%Y-%m-01')
        end = (date(month_start.year + 1, 1, 1) if month_start.month == 12 else date(month_start.year, month_start.month + 1, 1)).strftime('%Y-%m-%d')
        row = self.shell.db.fetchone("SELECT COALESCE(SUM(total_price),0) AS s FROM contracts WHERE created_at >= ? AND created_at < ?", (start, end))
        revenue.append((month_start.strftime('%m/%y'), float(row_get(as_dict(row), 's', 0) or 0)))
    revenue_total = sum(value for _, value in revenue)
    self.chart_revenue.set_data(
        revenue,
        f"Sou\u010det cen smluv za posledn\u00edch {revenue_months} m\u011bs\u00edc\u016f.",
        ' K\u010d',
        summary=f"Celkem {fmt_money(revenue_total)}",
    )
    _dashboard_refresh_calendar_markers(self)
    _dashboard_refresh_calendar_items(self)


def _open_machine_detail_clean(self: MainWindow, machine_id: int):
    machine = as_dict(self.db.fetchone('SELECT * FROM machines WHERE id=?', (machine_id,)))
    summary = self.db.get_machine_summary(machine_id)
    stats = as_dict(summary.get('stats'))
    dlg = DetailDialog(self, 'Detail stroje')
    dlg.set_summary(
        f"{row_get(machine, 'name')} \u00b7 {row_get(machine, 'category')}",
        [
            f"Stav: {row_get(machine, 'status')}",
            f"Denn\u00ed sazba: {fmt_money(row_get(machine, 'daily_rate'))}",
            f"Kauce: {fmt_money(row_get(machine, 'deposit'))}",
        ],
    )
    dlg.add_header_action('Upravit stroj', lambda: (dlg.accept(), self.edit_machine(machine_id)), 'PrimaryBtn')
    dlg.add_header_action('Nov\u00fd servis', lambda: (dlg.accept(), self.new_service(machine_id)), 'GhostBtn')
    dlg.add_kv_panel('Z\u00e1klad', [
        ('N\u00e1zev', row_get(machine, 'name')),
        ('Kategorie', row_get(machine, 'category')),
        ('Invent\u00e1rn\u00ed \u010d\u00edslo', row_get(machine, 'inventory_number')),
        ('Model', row_get(machine, 'model')),
        ('S\u00e9riov\u00e9 \u010d\u00edslo', row_get(machine, 'serial_number')),
        ('Stav', row_get(machine, 'status')),
        ('Denn\u00ed sazba', fmt_money(row_get(machine, 'daily_rate'))),
        ('Kauce', fmt_money(row_get(machine, 'deposit'))),
        ('Motohodiny', row_get(machine, 'motohours')),
        ('Servis p\u0159i MH', row_get(machine, 'service_due_motohours')),
        ('Dal\u0161\u00ed servis', row_get(machine, 'next_service_date')),
        ('Pozn\u00e1mka', row_get(machine, 'notes')),
    ])
    dlg.add_stat_strip([
        ('Po\u010det v\u00fdp\u016fj\u010dek', row_get(stats, 'contracts_count', 0)),
        ('Tr\u017eby', fmt_money(row_get(stats, 'total_revenue', 0))),
        ('Posledn\u00ed vratka', row_get(stats, 'last_return') or '-'),
    ])

    timeline_table = self.make_table(['Typ', 'Od', 'Do', 'Partner', 'Stav', '\u010c\u00e1stka'])
    timeline_rows = []
    timeline_ids = []
    timeline_kinds: list[str] = []
    for r in [as_dict(x) for x in summary.get('timeline', [])]:
        timeline_rows.append([
            row_get(r, 'event_type'),
            row_get(r, 'date_from'),
            row_get(r, 'date_to'),
            row_get(r, 'partner_name'),
            row_get(r, 'status'),
            fmt_money(row_get(r, 'amount')),
        ])
        timeline_ids.append(int(row_get(r, 'source_id', 0) or 0))
        timeline_kinds.append(str(row_get(r, 'source_kind')))
    self.fill_table(timeline_table, timeline_rows, timeline_ids)

    def _open_timeline_row():
        row = timeline_table.currentRow()
        if row < 0 or row >= len(timeline_kinds):
            return
        item_id = self.current_table_id(timeline_table)
        kind = timeline_kinds[row]
        if kind == 'contract':
            self.open_contract_detail(item_id)
        elif kind == 'reservation':
            self.open_reservation_detail(item_id)
        elif kind == 'service':
            self.open_service_detail(item_id)

    timeline_table.itemDoubleClicked.connect(lambda *_: _open_timeline_row())
    timeline_panel = Panel('Historie stroje')
    timeline_panel.content.addWidget(timeline_table)
    dlg.body_l.addWidget(timeline_panel)

    reservations_table = self.make_table(['Rezervace', 'Od', 'Do', 'Z\u00e1kazn\u00edk', 'Stav'])
    reservation_rows = []
    reservation_ids = []
    for r in [as_dict(x) for x in summary.get('reservations', [])]:
        reservation_rows.append([
            row_get(r, 'reservation_number'),
            row_get(r, 'reserved_from'),
            row_get(r, 'reserved_to'),
            row_get(r, 'customer_name'),
            row_get(r, 'status'),
        ])
        reservation_ids.append(int(row_get(r, 'id', 0) or 0))
    self.fill_table(reservations_table, reservation_rows, reservation_ids)
    reservations_table.itemDoubleClicked.connect(lambda *_: self.open_reservation_detail(self.current_table_id(reservations_table)))
    reservations_panel = Panel('Rezervace stroje', 'Plánované blokace a potvrzené termíny pro tento stroj.')
    reservations_panel.content.addWidget(reservations_table)
    dlg.body_l.addWidget(reservations_panel)

    photos = [as_dict(r) for r in self.db.get_machine_photos(machine_id)]
    if photos:
        p3 = Panel('Fotky', 'Klikni na náhled pro větší zobrazení nebo otevření originálu.')
        grid_wrap = QWidget()
        grid = QGridLayout(grid_wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        for idx, ph in enumerate(photos[:8]):
            path = str(row_get(ph, 'path', ''))
            caption = str(row_get(ph, 'caption') or Path(path).name)
            preview = build_photo_preview(path, caption, 180, 120)
            set_click_handler(preview, lambda value=idx: PhotoLightboxDialog(dlg, photos, value, 'Fotky stroje').exec())
            grid.addWidget(preview, idx // 2, idx % 2)
        p3.content.addWidget(grid_wrap)
        dlg.body_l.addWidget(p3)
    dlg.exec()


def _safe_machine_dialog_save_clean(self: MachineDialog):
    try:
        _machine_dialog_save_original(self)
    except sqlite3.IntegrityError as exc:
        message = str(exc)
        if 'inventory_number' in message:
            QMessageBox.warning(self, 'Duplicitn\u00ed invent\u00e1rn\u00ed \u010d\u00edslo', 'Stroj s t\u00edmto invent\u00e1rn\u00edm \u010d\u00edslem u\u017e existuje.')
            return
        raise


fmt_money = _fmt_money_clean
status_tone = _status_tone_clean
DashboardPage.refresh = _dashboard_refresh_clean
MainWindow.open_machine_detail = _open_machine_detail_clean
MachineDialog.save = _safe_machine_dialog_save_clean


def main():
    app = QApplication(sys.argv)
    app_font = normalize_font_point_size(app.font())
    app.setFont(app_font)
    app.setApplicationName('P\u016fj\u010dovna stroj\u016f Qt Full')
    if APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    splash = StartupSplash()
    splash.play()
    win = MainWindow()
    if APP_ICON_PATH.exists():
        win.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    win.showMaximized()
    splash.finish()
    sys.exit(app.exec())

STYLESHEET = f"""
QWidget {{ background: {BG}; color: {TEXT}; font-family: Segoe UI, Inter, Arial; font-size: 14px; }}
QLabel {{ background: transparent; }}
#Rail {{ background: #0f131a; border-right: 1px solid #1f2835; }}
#Brand, #QuickPanel, #Panel, #StatCard, #ToolbarPanel, #Toast, #DialogHeader, #ActionItem, #SettingsHero, #DetailHero, #DetailMiniCard, #SelectionPanel, #StepChip, #KpiTile {{ background: {PANEL}; border: 1px solid #232e3d; }}
#Topbar {{ background: #11161e; border-bottom: 1px solid #1f2835; }}
#RailBadge {{ background: #1f2835; border: 1px solid #314051; border-radius: 10px; padding: 4px 8px; color: {ACCENT_2}; font-size: 11px; font-weight: 700; }}
#RailSection {{ color: {MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 1px; padding: 6px 2px 0 2px; }}
#BrandTitle {{ font-size: 24px; font-weight: 700; }}
#BrandSub, #CardSubtle, #PanelSubtle, #ActionSub, #DetailHeroSub, #DetailMiniLabel, #HintMuted {{ color: {MUTED}; }}
#ActionTitle {{ font-size: 14px; font-weight: 700; }}
#TopTitle {{ font-size: 24px; font-weight: 700; }}
#PageTitle {{ font-size: 30px; font-weight: 700; }}
#PanelTitle {{ font-size: 16px; font-weight: 700; }}
#CardValue {{ font-size: 30px; font-weight: 700; }}
#Dialog, #Dialog * {{ background: {BG}; }}
#DialogHeader {{ background: {PANEL}; }}
#DialogTitle {{ font-size: 22px; font-weight: 700; }}
#SettingsHeroTitle, #DetailHeroTitle {{ font-size: 20px; font-weight: 700; }}
#DetailBadge {{ background: #1a2330; border: 1px solid #2d3a4e; padding: 6px 10px; color: {TEXT}; font-size: 12px; font-weight: 700; }}
#DetailMiniValue {{ font-size: 18px; font-weight: 700; }}
#DetailKeyLabel {{ color: {MUTED}; min-width: 140px; }}
#SelectionPanel {{ background: #10161f; border: 1px solid #2c394a; }}
#StepChip {{ padding: 8px 12px; font-size: 12px; font-weight: 700; background: #10161f; }}
#StepChipActive {{ padding: 8px 12px; font-size: 12px; font-weight: 700; background: {ACCENT}; color: #111; border: 1px solid {ACCENT}; }}
#KpiTile {{ background: #10161f; padding: 10px; }}
#SelectionTitle {{ font-size: 13px; font-weight: 700; color: {TEXT}; }}

#DetailValueLabel {{ color: {TEXT}; }}
#NavList {{ background: transparent; border: 0; outline: 0; }}
#NavList::item {{ padding: 12px 14px; margin: 1px 0; border: 1px solid transparent; border-radius: 8px; }}
#NavList::item:hover {{ background: #171d27; border-color: #33465b; color: #ffffff; }}
#NavList::item:selected {{ background: {PANEL_2}; border-left: 4px solid {ACCENT}; border-color: #344356; font-weight: 700; color: #ffffff; }}
QListWidget#SettingsNav {{ background: transparent; border: 0; outline: 0; }}
QListWidget#SettingsNav::item {{ padding: 12px 10px; margin: 2px 0; border: 1px solid transparent; }}
QListWidget#SettingsNav::item:selected {{ background: {PANEL_2}; border-left: 4px solid {ACCENT_2}; font-weight: 700; }}
QListWidget#ActionList {{ background: transparent; border: 0; }}
QListWidget#ActionList::item {{ border: 0; margin: 0 0 6px 0; }}
#ActionItem:hover {{ border-color: #3b4c63; }}
#RailMetric {{ background: #10161f; border: 1px solid #2c394a; border-radius: 10px; }}
#RailMetricLabel {{ color: {MUTED}; font-size: 12px; font-weight: 600; }}
#RailMetricValue {{ color: {TEXT}; font-size: 18px; font-weight: 700; }}
QGroupBox#FormGroup {{ border: 1px solid #253142; margin-top: 10px; padding-top: 8px; background: {PANEL}; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; top: -2px; padding: 0 6px; color: {TEXT}; font-weight: 700; }}
QLineEdit, QComboBox, QDateEdit, QPlainTextEdit, QListWidget, QTabWidget::pane, QScrollArea, QStackedWidget#SettingsStack {{ background: {PANEL_3}; border: 1px solid #293648; padding: 8px 10px; color: {TEXT}; selection-background-color: #243041; }}
QDateEdit::drop-down, QComboBox::drop-down {{ border: 0; width: 22px; }}
QPushButton {{ padding: 10px 14px; border: 1px solid #293648; background: {PANEL_3}; color: {TEXT}; }}
QPushButton:hover {{ border-color: {ACCENT_2}; }}
QPushButton#PrimaryBtn {{ background: {ACCENT}; color: #101010; border: 1px solid {ACCENT}; font-weight: 700; }}
QPushButton#GhostBtn {{ background: {PANEL_3}; color: {TEXT}; border: 1px solid #293648; }}
QTableWidget {{ background: {PANEL_3}; border: 1px solid #293648; gridline-color: {GRID}; selection-background-color: #243041; selection-color: {TEXT}; }}
QHeaderView::section {{ background: #141b25; color: #d4dbe4; padding: 10px; border: 0; border-bottom: 1px solid #293648; }}
QTableCornerButton::section {{ background: #141b25; border: 0; }}
QScrollBar:vertical {{ background: #11161e; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #2a3544; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QTabBar::tab {{ background: {PANEL_3}; padding: 10px 14px; border: 1px solid #293648; }}
QTabBar::tab:selected {{ background: {PANEL}; border-bottom: 1px solid {ACCENT}; }}
"""


if __name__ == '__main__':
    main()
