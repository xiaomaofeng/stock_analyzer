# -*- coding: utf-8 -*-
"""Modern UI Theme - macOS / Windows 11 Style"""

COLORS = {
    'primary': '#007AFF',
    'secondary': '#5856D6',
    'success': '#34C759',
    'warning': '#FF9500',
    'danger': '#FF3B30',
    'background': '#F5F5F7',
    'surface': '#FFFFFF',
    'card': '#FFFFFF',
    'text': '#1D1D1F',
    'text_secondary': '#86868B',
    'border': '#E5E5E5',
    'hover': '#F0F0F0',
}

MODERN_STYLE = f"""
QMainWindow {{ background-color: {COLORS['background']}; border: none; }}

QWidget {{ 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
    font-size: 13px;
    color: {COLORS['text']};
}}

QGroupBox {{
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    margin-top: 12px;
    padding: 16px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    font-size: 14px;
}}

QPushButton {{
    background-color: {COLORS['primary']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 500;
    min-height: 36px;
}}

QPushButton:hover {{ background-color: #0056D4; }}
QPushButton:pressed {{ background-color: #004494; }}
QPushButton:disabled {{ background-color: #C7C7CC; color: #8E8E93; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 20px;
}}

QLineEdit:focus, QComboBox:focus {{
    border: 2px solid {COLORS['primary']};
    padding: 7px 11px;
}}

QLabel#metric {{ 
    font-size: 24px; 
    font-weight: 700; 
    color: {COLORS['primary']}; 
}}

QLabel#metric_label {{ 
    font-size: 11px; 
    color: {COLORS['text_secondary']}; 
}}

QProgressBar {{
    background-color: #E5E5EA;
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {COLORS['primary']};
    border-radius: 4px;
}}

QTableWidget {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
}}

QHeaderView::section {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_secondary']};
    padding: 12px;
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    font-weight: 600;
    font-size: 12px;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {COLORS['text_secondary']};
    padding: 12px 24px;
    border: none;
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:selected {{
    color: {COLORS['primary']};
    border-bottom: 2px solid {COLORS['primary']};
}}

QMenuBar {{
    background-color: {COLORS['surface']};
    border-bottom: 1px solid {COLORS['border']};
}}

QStatusBar {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_secondary']};
    border-top: 1px solid {COLORS['border']};
}}
"""
