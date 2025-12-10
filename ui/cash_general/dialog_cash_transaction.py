from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit, 
    QDoubleSpinBox, QComboBox, QLineEdit, QPushButton, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import QDate, Qt
from core.settings import CASH_CATEGORIES_INCOME, CASH_CATEGORIES_EXPENSE

class CashTransactionDialog(QDialog):
    def __init__(self, op_type, parent=None, edit_data=None):
        super().__init__(parent)
        self.op_type = op_type
        self.edit_data = edit_data
        
        mode_str = "Приход" if op_type == "income" else "Расход"
        title = f"✏️ Редактирование: {mode_str}" if edit_data else f"➕ Новый {mode_str}"
        self.setWindowTitle(title)
        self.setFixedWidth(400)
        
        color = "#4CAF50" if op_type == "income" else "#F44336"
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: white; }}
            QLabel {{ font-weight: bold; color: #555; margin-top: 10px; font-size: 13px; }}
            QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox {{ 
                padding: 8px; border: 1px solid #ccc; border-radius: 6px; background: #f9f9f9; font-size: 14px; color: #333;
            }}
            QLineEdit:focus, QComboBox:focus {{ border: 2px solid {color}; background: #fff; }}
            
            QComboBox QAbstractItemView {{
                background-color: white;
                color: #333;
                selection-background-color: #E3F2FD;
                selection-color: #1565C0;
                border: 1px solid #ccc;
                outline: none;
            }}
            
            QPushButton {{ background-color: {color}; color: white; padding: 12px; font-weight: bold; border-radius: 6px; font-size: 14px; border: none; }}
            QPushButton:hover {{ opacity: 0.9; }}
            
            QRadioButton {{ font-size: 14px; font-weight: 500; color: #333; }}
            QRadioButton::indicator {{ width: 16px; height: 16px; }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        
        row1 = QHBoxLayout()
        
        date_l = QVBoxLayout()
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        if edit_data: self.date_edit.setDate(QDate.fromString(edit_data['date'], "yyyy-MM-dd"))
        date_l.addWidget(QLabel("ДАТА"))
        date_l.addWidget(self.date_edit)
        row1.addLayout(date_l)
        
        pay_l = QVBoxLayout()
        pay_l.addWidget(QLabel("СПОСОБ"))
        
        self.pay_group = QButtonGroup(self)
        self.rb_cash = QRadioButton("💵 Наличные")
        self.rb_card = QRadioButton("💳 Безнал")
        self.pay_group.addButton(self.rb_cash)
        self.pay_group.addButton(self.rb_card)
        
        if edit_data and edit_data.get('payment_type') == 'cashless':
            self.rb_card.setChecked(True)
        else:
            self.rb_cash.setChecked(True)
            
        pay_row = QHBoxLayout()
        pay_row.addWidget(self.rb_cash)
        pay_row.addWidget(self.rb_card)
        pay_l.addLayout(pay_row)
        row1.addLayout(pay_l)
        
        layout.addLayout(row1)
        
        self.cat_combo = QComboBox()
        cats = CASH_CATEGORIES_INCOME if op_type == "income" else CASH_CATEGORIES_EXPENSE
        self.cat_combo.addItems(cats)
        if edit_data: self.cat_combo.setCurrentText(edit_data['category'])
        layout.addWidget(QLabel("КАТЕГОРИЯ"))
        layout.addWidget(self.cat_combo)
        
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 10000000)
        self.amount_spin.setSingleStep(100)
        self.amount_spin.setGroupSeparatorShown(True)
        self.amount_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        if edit_data: self.amount_spin.setValue(edit_data['amount'])
        layout.addWidget(QLabel("СУММА (₽)"))
        layout.addWidget(self.amount_spin)
        
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Например: От Иванова И.И.")
        if edit_data: self.desc_edit.setText(edit_data['desc'])
        layout.addWidget(QLabel("КОММЕНТАРИЙ"))
        layout.addWidget(self.desc_edit)
        
        layout.addSpacing(20)
        btn_save = QPushButton("💾 СОХРАНИТЬ")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self.accept)
        layout.addWidget(btn_save)

    def get_data(self):
        return {
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "category": self.cat_combo.currentText(),
            "amount": self.amount_spin.value(),
            "desc": self.desc_edit.text(),
            "payment_type": "cash" if self.rb_cash.isChecked() else "cashless"
        }