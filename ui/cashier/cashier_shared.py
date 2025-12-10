from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt

# ===== СТИЛИ =====
STYLE_PRODUCT_BTN = """
    QPushButton {
        background-color: #f8f8f8; 
        border: 2px solid #ddd; 
        border-radius: 12px;
        font-size: 13px;
        font-weight: bold;
        padding: 10px 6px;
        text-align: center;
    }
    QPushButton:hover { 
        background-color: #FFE5B4; 
        border-color: #FFA500;
        border-width: 3px;
    }
    QPushButton:pressed { 
        background-color: #FFA500; 
        color: white;
    }
"""

STYLE_WRITEOFF_BTN = """
    QPushButton {
        background-color: #f8f8f8; 
        border: 2px solid #ddd; 
        border-radius: 10px;
        font-size: 12px;
        font-weight: bold;
        padding: 8px 5px;
        text-align: center;
    }
    QPushButton:hover { 
        background-color: #FFE5B4; 
        border-color: #FFA500;
        border-width: 3px;
    }
    QPushButton:pressed { 
        background-color: #FFA500; 
        color: white;
    }
"""

STYLE_CATEGORY_BTN = """
    QTabBar::tab {
        background: #e0e0e0;
        color: black;
        padding: 12px 24px;
        font-size: 15px;
        font-weight: bold;
        margin-right: 3px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }
    QTabBar::tab:selected {
        background: #FFA500;
        color: white;
    }
    QTabBar::tab:hover:!selected {
        background: #FFE5B4;
    }
"""

def wrap_text_auto(text: str, max_len: int = 15) -> str:
    """Автоматический перенос длинного текста на несколько строк"""
    if len(text) <= max_len:
        return text
    
    words = text.split()
    if not words:
        return text
    
    lines = []
    current_line = []
    current_len = 0
    
    for word in words:
        word_len = len(word)
        if word_len > max_len:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = []
                current_len = 0
            lines.append(word[:max_len])
            if len(word) > max_len:
                word = word[max_len:]
                current_line = [word] if word else []
                current_len = len(word) if word else 0
        else:
            needed_len = current_len + word_len + (1 if current_line else 0)
            if needed_len <= max_len:
                current_line.append(word)
                current_len = needed_len
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_len = word_len
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return '\n'.join(lines[:3])

class ProductButton(QPushButton):
    def __init__(self, pid, name, price, uom, callback):
        self.pid = pid
        self.name = name
        self.price = price
        self.uom = uom
        
        display_name = wrap_text_auto(name.strip(), max_len=18)
        price_text = f"{price:.0f} ₽"
        
        super().__init__(f"{display_name}\n\n{price_text}")
        self.setFixedSize(165, 115)
        self.setStyleSheet(STYLE_PRODUCT_BTN)
        self.clicked.connect(lambda: callback(self.pid, self.name, self.price))