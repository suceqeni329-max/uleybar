from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtGui import QColor

# =================================================================================
# КОНСТАНТЫ И СТИЛИ
# =================================================================================

STYLE_CARD = """
    QFrame {
        background-color: white;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
    QLabel#Title {
        color: #757575;
        font-size: 12px;
        font-weight: bold;
        text-transform: uppercase;
    }
    QLabel#Value {
        color: #333;
        font-size: 22px;
        font-weight: 800;
        margin-top: 5px;
    }
    QLabel#Sub {
        color: #9E9E9E;
        font-size: 11px;
    }
"""

STYLE_BTN_ADD = """
    QPushButton {
        background-color: #4CAF50; 
        color: white; 
        font-weight: bold; 
        border-radius: 6px;
        padding: 10px 20px;
        font-size: 14px;
    }
    QPushButton:hover { background-color: #43A047; }
    QPushButton:pressed { background-color: #388E3C; }
"""

STYLE_BTN_ACTION = """
    QPushButton {
        background-color: #fff; 
        border: 1px solid #ccc; 
        border-radius: 4px;
        padding: 5px 10px;
        color: #333;
    }
    QPushButton:hover { background-color: #f0f0f0; border-color: #bbb; }
"""

COLORS = {
    "cert": QColor("#E0F7FA"),      # Сертификат (Голубой)
    "fail": QColor("#FFEBEE"),      # Сбой (Розовый)
    "loyal": QColor("#FFF9C4"),     # Лояльность (Желтый)
    "promo": QColor("#E1BEE7"),     # Розыгрыш (Фиолетовый)
    "return": QColor("#F5F5F5"),    # Возврат (Серый)
    "tickets": QColor("#E0F2F1"),   # Тикеты (Бирюзовый)
    "playground": QColor("#E8F5E9"),# Игровая (Зеленоватый)
    "default": QColor("#FFFFFF")    # Обычный
}

class StatCard(QFrame):
    """Красивая карточка со статистикой для дашборда"""
    def __init__(self, title, icon="📊", parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLE_CARD)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumWidth(180)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        header = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("Title")
        self.lbl_icon = QLabel(icon)
        self.lbl_icon.setStyleSheet("font-size: 18px;")
        
        header.addWidget(self.lbl_title)
        header.addStretch()
        header.addWidget(self.lbl_icon)
        
        self.lbl_value = QLabel("0")
        self.lbl_value.setObjectName("Value")
        
        self.lbl_sub = QLabel("-")
        self.lbl_sub.setObjectName("Sub")
        
        layout.addLayout(header)
        layout.addWidget(self.lbl_value)
        layout.addWidget(self.lbl_sub)
        
    def update_value(self, value, subtext="", color=None):
        self.lbl_value.setText(str(value))
        self.lbl_sub.setText(str(subtext))
        if color:
            self.lbl_value.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: 800; margin-top: 5px;")