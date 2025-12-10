from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QDateTimeEdit, QLineEdit, 
    QSpinBox, QComboBox, QDialogButtonBox
)
from PyQt6.QtCore import QDateTime

class BonusEditDialog(QDialog):
    """Диалог редактирования записи бонуса"""
    def __init__(self, row_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Редактирование записи #{row_data['id']}")
        self.setFixedWidth(400)
        self.data = row_data
        self.result_data = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Используем QDateTimeEdit для редактирования даты и времени
        try:
            # Пробуем распарсить полную дату-время
            dt = QDateTime.fromString(self.data['date'], "yyyy-MM-dd HH:mm:ss")
            if not dt.isValid():
                # Если не вышло (старый формат), пробуем только дату
                dt = QDateTime.fromString(self.data['date'], "yyyy-MM-dd")
                if not dt.isValid():
                    dt = QDateTime.currentDateTime()
        except:
            dt = QDateTime.currentDateTime()

        self.date_edit = QDateTimeEdit(dt)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        
        self.card_edit = QLineEdit(self.data['card'])
        
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(1, 100000)
        self.amount_spin.setValue(int(self.data['amount']))
        
        self.reason_combo = QComboBox()
        reasons = [
            "Не дал игру (Сбой)", 
            "Лояльность / Подарок", 
            "Розыгрыш", 
            "Игровая площадка",
            "Ручные тикеты",
            "Возврат", 
            "Прочее"
        ]
        
        # Добавляем текущую причину, если её нет в списке
        current_reason = self.data['reason']
        is_custom = True
        for r in reasons:
            if r in current_reason:
                self.reason_combo.addItem(r)
                self.reason_combo.setCurrentText(r)
                is_custom = False
                break
        
        # Остальные причины
        for r in reasons:
            if self.reason_combo.findText(r) == -1:
                self.reason_combo.addItem(r)
                
        if is_custom:
             self.reason_combo.insertItem(0, current_reason)
             self.reason_combo.setCurrentIndex(0)
        
        self.comment_edit = QLineEdit(self.data['comment'])
        
        form.addRow("Дата и Время:", self.date_edit)
        form.addRow("№ Карты:", self.card_edit)
        form.addRow("Сумма / Кол-во:", self.amount_spin)
        form.addRow("Причина:", self.reason_combo)
        form.addRow("Примечание:", self.comment_edit)
        
        layout.addLayout(form)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def save(self):
        # Сохраняем в формате datetime
        self.result_data = {
            "date": self.date_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            "card": self.card_edit.text(),
            "amount": self.amount_spin.value(),
            "reason": self.reason_combo.currentText(),
            "comment": self.comment_edit.text()
        }
        self.accept()