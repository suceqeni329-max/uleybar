from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt

# === СТИЛИ ===
STYLES = {
    "card": """
        QFrame { 
            background-color: white; 
            border-radius: 12px; 
            border: 1px solid #e0e0e0;
        }
    """,
    "btn_income": """
        QPushButton { 
            background-color: #4CAF50; color: white; border-radius: 8px; 
            padding: 10px 20px; font-weight: bold; font-size: 13px; 
        }
        QPushButton:hover { background-color: #43A047; }
        QPushButton:pressed { background-color: #388E3C; }
    """,
    "btn_expense": """
        QPushButton { 
            background-color: #F44336; color: white; border-radius: 8px; 
            padding: 10px 20px; font-weight: bold; font-size: 13px; 
        }
        QPushButton:hover { background-color: #E53935; }
        QPushButton:pressed { background-color: #D32F2F; }
    """,
    "btn_filter": """
        QPushButton { 
            background-color: #fff; border: 1px solid #ddd; border-radius: 6px; 
            color: #555; padding: 6px 14px; font-weight: 500;
        }
        QPushButton:hover { background-color: #f5f5f5; color: #333; }
        QPushButton:checked { background-color: #E3F2FD; color: #1565C0; border: 1px solid #1976D2; }
    """,
    "table": """
        QTableWidget {
            background-color: #ffffff;
            border: 1px solid #dcdcdc;
            border-radius: 8px;
            font-size: 14px;
            gridline-color: transparent; 
            outline: none;
        }
        QHeaderView::section {
            background-color: #F8F9FA;
            padding: 12px 10px;
            border: none;
            border-bottom: 2px solid #E0E0E0;
            font-weight: 600;
            color: #5F6368;
            font-size: 13px;
            text-transform: uppercase;
        }
        QTableWidget::item {
            padding: 8px 10px;
            border-bottom: 1px solid #F1F3F4;
            color: #333;
        }
        QTableWidget::item:selected {
            background-color: #E3F2FD; 
            color: #1565C0; 
            border-bottom: 1px solid #BBDEFB;
        }
    """
}

class StatCard(QFrame):
    """Красивая карточка с KPI"""
    def __init__(self, title, value, color_hex, icon="💰", subtext=""):
        super().__init__()
        self.setStyleSheet(STYLES["card"])
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        l = QVBoxLayout(self)
        l.setContentsMargins(20, 15, 20, 15)
        l.setSpacing(2)
        
        top = QHBoxLayout()
        self.lbl_title = QLabel(title.upper()) 
        self.lbl_title.setStyleSheet("color: #9E9E9E; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")
        top.addWidget(self.lbl_title)
        top.addStretch()
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 18px;")
        top.addWidget(lbl_icon)
        l.addLayout(top)
        
        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(f"color: {color_hex}; font-size: 26px; font-weight: 800; font-family: 'Segoe UI', sans-serif; margin-top: 5px;")
        l.addWidget(self.lbl_value)
        
        self.lbl_sub = QLabel(subtext)
        self.lbl_sub.setStyleSheet("color: #757575; font-size: 11px; font-weight: 500; margin-top: 2px;")
        self.lbl_sub.setVisible(bool(subtext))
        l.addWidget(self.lbl_sub)

    def set_value(self, val, sub=None):
        self.lbl_value.setText(val)
        if sub is not None:
            self.lbl_sub.setText(sub)
            self.lbl_sub.setVisible(True)
        else:
            self.lbl_sub.setVisible(False)

class CategoryBar(QFrame):
    """Виджет полоски расхода по категории"""
    def __init__(self, name, amount, percent, color="#F44336"):
        super().__init__()
        self.setStyleSheet("""
            CategoryBar { 
                background-color: #FAFAFA; 
                border-radius: 6px; 
                border: 1px solid #EEEEEE;
            }
        """)
        self.setToolTip(f"Категория: {name}\nСумма: {amount:,.0f} ₽\nДоля: {percent:.1f}% от всех расходов")
        
        l = QVBoxLayout(self)
        l.setContentsMargins(10, 10, 10, 10)
        l.setSpacing(6)
        
        top = QHBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-weight: 600; color: #424242; font-size: 13px;")
        
        amt_lbl = QLabel(f"{amount:,.0f} ₽".replace(",", " "))
        amt_lbl.setStyleSheet("font-weight: bold; color: #212121; font-size: 13px;")
        
        top.addWidget(name_lbl)
        top.addStretch()
        top.addWidget(amt_lbl)
        l.addLayout(top)
        
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(percent))
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        bar.setStyleSheet(f"""
            QProgressBar {{ border: none; background: #E0E0E0; border-radius: 4px; }}
            QProgressBar::chunk {{ background: {color}; border-radius: 4px; }}
        """)
        l.addWidget(bar)
        
        percent_lbl = QLabel(f"{percent:.1f}% от общих расходов")
        percent_lbl.setStyleSheet("color: #9E9E9E; font-size: 11px;")
        percent_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        l.addWidget(percent_lbl)