from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QDateEdit, QSpinBox, 
    QComboBox, QLineEdit, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QMessageBox, QWidget, QHBoxLayout
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QBrush

class PaymentDialog(QDialog):
    def __init__(self, db, bid, client_name, current_user, parent=None):
        super().__init__(parent)
        self.db = db
        self.bid = bid
        self.client_name = client_name  # Сохраняем имя клиента
        self.current_user = current_user
        self.setWindowTitle(f"Оплата: {client_name}")
        self.resize(380, 480) # Немного увеличил высоту
        
        self.allow_backdate = self.db.get_setting("allow_backdated_payments", "0") == "1"
        
        l = QVBoxLayout(self)
        l.addWidget(QLabel("Дата платежа (В кассу):"))
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        
        if not self.allow_backdate:
            self.date_edit.setEnabled(False)
            self.date_edit.setStyleSheet("background-color: #f0f0f0; color: #555;")
        else:
            self.date_edit.setStyleSheet("background-color: #fff; color: #000; font-weight: bold;")
            
        l.addWidget(self.date_edit)
        
        self.amount_spin = QSpinBox(); self.amount_spin.setRange(1, 100000); self.amount_spin.setSingleStep(500); self.amount_spin.setSuffix(" ₽")
        self.amount_spin.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        self.type_combo = QComboBox()
        # Добавлен пункт "Старый сертификат (Без проверки)"
        self.type_combo.addItems(["Наличные", "Перевод", "Безнал (Терминал)", "Сертификат", "Старый сертификат (Без проверки)"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        
        # === Блок сертификата (скрыт по умолчанию) ===
        self.cert_container = QWidget()
        cert_layout = QVBoxLayout(self.cert_container)
        cert_layout.setContentsMargins(0, 0, 0, 0)
        
        # Группа проверки (для обычных сертификатов)
        self.check_group = QWidget()
        check_l = QHBoxLayout(self.check_group)
        check_l.setContentsMargins(0, 0, 0, 0)
        
        self.cert_input = QLineEdit()
        self.cert_input.setPlaceholderText("Введите код сертификата")
        self.btn_check = QPushButton("🔍")
        self.btn_check.setFixedWidth(40)
        self.btn_check.clicked.connect(self.check_certificate)
        
        check_l.addWidget(self.cert_input)
        check_l.addWidget(self.btn_check)
        cert_layout.addWidget(self.check_group)
        
        self.lbl_cert_info = QLabel("")
        self.lbl_cert_info.setStyleSheet("font-size: 11px; font-weight: bold;")
        cert_layout.addWidget(self.lbl_cert_info)
        
        # Поле для старого сертификата (просто текст)
        self.old_cert_input = QLineEdit()
        self.old_cert_input.setPlaceholderText("№ Старого сертификата (для истории)")
        self.old_cert_input.setVisible(False)
        cert_layout.addWidget(self.old_cert_input)
        
        self.cert_container.setVisible(False)
        # =============================================

        self.stage_combo = QComboBox(); self.stage_combo.addItems(["Аванс", "Расчет", "Полная оплата"])
        self.comment = QLineEdit(); self.comment.setPlaceholderText("Комментарий к платежу")
        
        l.addWidget(QLabel("Сумма:"))
        l.addWidget(self.amount_spin)
        l.addWidget(QLabel("Тип:"))
        l.addWidget(self.type_combo)
        l.addWidget(self.cert_container) # Вставляем блок сертификата
        l.addWidget(QLabel("Этап:"))
        l.addWidget(self.stage_combo)
        l.addWidget(self.comment)
        
        btn = QPushButton("✅ Внести и Синхронизировать с КАССОВЫМ ОТЧЕТОМ")
        btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        btn.clicked.connect(self.save)
        l.addWidget(btn)
        
        self.history_list = QTableWidget(); self.history_list.setColumnCount(3); self.history_list.setHorizontalHeaderLabels(["Дата", "Сумма", "Тип"])
        self.history_list.verticalHeader().setVisible(False); self.history_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        l.addWidget(QLabel("История:")); l.addWidget(self.history_list)
        self.load_history()
    
    def on_type_changed(self, text):
        is_cert = (text == "Сертификат")
        is_old_cert = (text == "Старый сертификат (Без проверки)")
        
        self.cert_container.setVisible(is_cert or is_old_cert)
        
        # Показываем проверку только для новых сертификатов
        self.check_group.setVisible(is_cert)
        self.lbl_cert_info.setVisible(is_cert)
        
        # Показываем простое поле для старых
        self.old_cert_input.setVisible(is_old_cert)
        
        if not is_cert:
            self.lbl_cert_info.clear()
            self.cert_input.clear()

    def check_certificate(self):
        code = self.cert_input.text().strip()
        if not code: return
        
        cert = self.db.get_certificate_by_code(code)
        if not cert:
            self.lbl_cert_info.setText("❌ Не найден")
            self.lbl_cert_info.setStyleSheet("color: red")
            return
            
        if cert['status'] != 'active':
            self.lbl_cert_info.setText(f"❌ Статус: {cert['status']}")
            self.lbl_cert_info.setStyleSheet("color: red")
            return
            
        self.lbl_cert_info.setText(f"✅ Активен. Баланс: {cert['balance']:.0f}")
        self.lbl_cert_info.setStyleSheet("color: green")
        
        # Если сумма ввода больше баланса сертификата, корректируем её
        current_val = self.amount_spin.value()
        if current_val > cert['balance']:
            self.amount_spin.setValue(int(cert['balance']))
            QMessageBox.information(self, "Инфо", f"Сумма скорректирована под баланс сертификата ({cert['balance']:.0f})")

    def load_history(self):
        payments = self.db.fetch_payments_for_booking(self.bid)
        self.history_list.setRowCount(len(payments))
        for r, row in enumerate(payments):
            self.history_table_item(r, row)

    def history_table_item(self, r, row):
        self.history_list.setItem(r, 0, QTableWidgetItem(row[1]))
        self.history_list.setItem(r, 1, QTableWidgetItem(f"{row[2]:.0f}"))
        self.history_list.setItem(r, 2, QTableWidgetItem(row[3]))

    def save(self):
        payment_date = self.date_edit.date().toString("yyyy-MM-dd")
        ptype = self.type_combo.currentText()
        amount = self.amount_spin.value()
        comment = self.comment.text()
        
        # Логика списания НОВОГО сертификата (с проверкой)
        if ptype == "Сертификат":
            code = self.cert_input.text().strip()
            if not code:
                QMessageBox.warning(self, "Ошибка", "Введите код сертификата")
                return
            
            # Получаем дату мероприятия для красивой истории в сертификате
            try:
                booking = self.db.get_booking_by_id(self.bid)
                event_date = booking.get('date', '?') if booking else '?'
            except:
                event_date = '?'

            # Пытаемся списать с нормальным комментарием
            note = f"Банкет: {self.client_name} на {event_date}. {comment}"
            success, msg = self.db.use_certificate_balance(code, amount, self.current_user.id, note)
            
            if not success:
                QMessageBox.critical(self, "Ошибка списания", msg)
                return
            
            # Добавляем код сертификата в комментарий для истории платежей банкета
            comment = f"Сертификат {code}. {comment}"

        # Логика для СТАРОГО сертификата (без проверки)
        elif ptype == "Старый сертификат (Без проверки)":
            old_code = self.old_cert_input.text().strip()
            if old_code:
                comment = f"Старый Серт. №{old_code}. {comment}"
            else:
                comment = f"Старый Серт. (б/н). {comment}"
            
            # Меняем тип платежа на просто "Сертификат" для красоты в истории
            ptype = "Сертификат (Старый)"

        # Сохраняем платеж (если сертификат списался успешно или это обычный платеж)
        self.db.add_booking_payment(
            self.bid, 
            payment_date, 
            amount, 
            ptype, 
            self.stage_combo.currentText(), 
            comment,
            uid=self.current_user.id,
            sync_cash=True 
        )
        
        if ptype == "Сертификат":
            QMessageBox.information(self, "Успех", f"Сертификат списан, оплата проведена.")
        elif "Старый" in ptype:
             QMessageBox.information(self, "Успех", f"Оплата старым сертификатом учтена.")
            
        self.accept()