from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTableWidget, QTableWidgetItem, QFrame, QMessageBox, 
    QGroupBox, QHeaderView
)
from PyQt6.QtCore import Qt, QDate

from database.db_manager import DatabaseManager
from core.utils import CurrentUser, format_quantity_display
import webbrowser
import os
import json

class CashierReportTab(QWidget):
    def __init__(self, db: DatabaseManager, current_user: CurrentUser):
        super().__init__()
        self.db = db
        self.current_user = current_user
        self.init_ui()

    def showEvent(self, event):
        self.refresh() 
        super().showEvent(event)

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>📊 Отчет за смену (Сегодня)</h2>"))
        btn_update = QPushButton("🔄 Обновить")
        btn_update.clicked.connect(self.refresh)
        header.addStretch()
        header.addWidget(btn_update)
        layout.addLayout(header)
        
        # === ОБНОВЛЕННЫЕ КАРТОЧКИ ===
        self.cards_layout = QHBoxLayout()
        self.card_card = self.create_card("💳 Безнал (Банк)", "#e3f2fd", "#1565C0")
        self.card_cash = self.create_card("💵 Выручка (Нал)", "#e8f5e9", "#2E7D32")
        self.card_total = self.create_card("💰 ИТОГО В КАССЕ (НАЛ)", "#fff3e0", "#E65100")
        
        self.cards_layout.addWidget(self.card_card)
        self.cards_layout.addWidget(self.card_cash)
        self.cards_layout.addWidget(self.card_total)
        layout.addLayout(self.cards_layout)
        
        layout.addSpacing(20)
        
        self.upcoming_expiry_group = QGroupBox("⚠️ Скоро истекают (ближайшие 3 дня)")
        self.upcoming_expiry_group.setStyleSheet("""
            QGroupBox { font-weight: bold; color: #E65100; border: 1px solid #E65100; border-radius: 5px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
        """)
        ue_layout = QVBoxLayout(self.upcoming_expiry_group)
        self.upcoming_list_lbl = QLabel("Загрузка...")
        self.upcoming_list_lbl.setWordWrap(True)
        ue_layout.addWidget(self.upcoming_list_lbl)
        self.upcoming_expiry_group.setVisible(False)
        layout.addWidget(self.upcoming_expiry_group)
        
        reports_layout = QHBoxLayout()
        btn_salary_report = QPushButton("📄 Отчет по питанию (HTML)")
        btn_salary_report.setMinimumHeight(40)
        btn_salary_report.setStyleSheet("background-color: #fff9c4; border: 1px solid #fbc02d; font-weight: bold;")
        btn_salary_report.clicked.connect(self.open_salary_report)
        reports_layout.addWidget(btn_salary_report)
        reports_layout.addStretch()
        layout.addLayout(reports_layout)

        layout.addWidget(QLabel("<h3>📉 Списания за смену (для проверки):</h3>"))
        self.writeoff_table = QTableWidget()
        self.writeoff_table.setColumnCount(5)
        self.writeoff_table.setHorizontalHeaderLabels(["Товар", "Кол-во", "Причина", "Кто списал", "ЗП (если есть)"])
        self.writeoff_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.writeoff_table)
        
        btn_z = QPushButton("🖨️ Закрыть смену / Z-отчет")
        btn_z.setMinimumHeight(60)
        btn_z.setStyleSheet("background-color: #2196F3; color: white; font-size: 16px; font-weight: bold; border-radius: 8px;")
        btn_z.clicked.connect(self.print_z_report)
        layout.addWidget(btn_z)

    def create_card(self, title, bg_color, text_color):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {bg_color}; border-radius: 10px; border: 1px solid #ccc;")
        l = QVBoxLayout(frame)
        lbl_t = QLabel(title)
        lbl_v = QLabel("0 ₽")
        lbl_v.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {text_color};")
        lbl_v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(lbl_t)
        l.addWidget(lbl_v)
        return frame

    def refresh(self):
        date_str = QDate.currentDate().toString("yyyy-MM-dd")
        cash, cashless, total = self.db.calc_payment_totals_for_date(date_str)
        
        self.card_card.layout().itemAt(1).widget().setText(f"{cashless:,.0f} ₽".replace(",", " "))
        self.card_cash.layout().itemAt(1).widget().setText(f"{cash:,.0f} ₽".replace(",", " "))
        self.card_total.layout().itemAt(1).widget().setText(f"{cash:,.0f} ₽".replace(",", " "))
        
        rows = self.db.fetch_writeoffs_for_date(date_str)
        self.writeoff_table.setRowCount(len(rows))
        
        for r, (_id, _pid, name, qty, uom, wtype, emp, sal, com, _expiry) in enumerate(rows):
            self.writeoff_table.setItem(r, 0, QTableWidgetItem(name))
            self.writeoff_table.setItem(r, 1, QTableWidgetItem(f"{qty} {uom}"))
            self.writeoff_table.setItem(r, 2, QTableWidgetItem(wtype))
            self.writeoff_table.setItem(r, 3, QTableWidgetItem(emp))
            self.writeoff_table.setItem(r, 4, QTableWidgetItem(sal or "-"))
            
        self.load_upcoming_expiry()

    def load_upcoming_expiry(self):
        items = self.db.check_expiring_goods(days_warning=3)
        today = QDate.currentDate()
        
        upcoming = []
        for it in items:
            exp_date = QDate.fromString(it['expiry'], "yyyy-MM-dd")
            days_left = today.daysTo(exp_date)
            
            if 1 <= days_left <= 3:
                date_pretty = exp_date.toString("dd.MM")
                qty_str = format_quantity_display(it['qty'], it['uom'])
                upcoming.append(f"• {date_pretty}: {it['name']} ({qty_str})")
                
        if upcoming:
            self.upcoming_list_lbl.setText("\n".join(upcoming))
            self.upcoming_expiry_group.setVisible(True)
        else:
            self.upcoming_expiry_group.setVisible(False)

    def open_salary_report(self):
        d = QDate.currentDate()
        html = self.db.build_salary_report_html(d, d)
        
        os.makedirs("reports", exist_ok=True)
        fn = f"reports/salary_report_SHIFT_{d.toString('yyyyMMdd')}.html"
        
        try:
            with open(fn, "w", encoding="utf-8") as f: f.write(html)
            webbrowser.open(os.path.abspath(fn))
            self.db.log_action(self.current_user.id, "create", "reports", None, None, 
                               json.dumps({"action": "salary_report_generated", "date": d.toString("yyyy-MM-dd")}, ensure_ascii=False))
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть отчет:\n{e}")

    def print_z_report(self):
        d = QDate.currentDate()
        date_str = d.toString("yyyy-MM-dd")
        
        try:
            html = self.db.build_daily_report_html(d)
            os.makedirs("reports", exist_ok=True)
            fn = f"reports/z_report_{d.toString('yyyyMMdd')}.html"
            
            with open(fn, "w", encoding="utf-8") as f: f.write(html)
            webbrowser.open(os.path.abspath(fn))
            
            self.db.log_action(self.current_user.id, "create", "reports", None, None, 
                               json.dumps({"action": "z_report_generated", "date": date_str}, ensure_ascii=False))
            
            cash, cashless, total = self.db.calc_payment_totals_for_date(date_str)
            
            msg_lines = ["Смена закрыта."]
            if cash > 0:
                msg_lines.append(f"💵 Нал: {cash:,.0f} ₽".replace(",", " "))
            if cashless > 0:
                msg_lines.append(f"💳 Безнал: {cashless:,.0f} ₽".replace(",", " "))
            
            if total > 0:
                msg_lines.append("\nПеренести эти суммы в Главную Кассу?")
                reply = QMessageBox.question(
                    self, 
                    "Сдача выручки", 
                    "\n".join(msg_lines),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    if cash > 0:
                        self.db.add_cash_transaction(
                            date=date_str,
                            op_type="income",
                            cat="Бар (Выручка)",
                            amt=cash,
                            desc=f"Закрытие смены {d.toString('dd.MM.yyyy')} ({self.current_user.full_name})",
                            pay="cash",
                            uid=self.current_user.id
                        )
                    
                    if cashless > 0:
                        self.db.add_cash_transaction(
                            date=date_str,
                            op_type="income",
                            cat="Бар (Выручка)",
                            amt=cashless,
                            desc=f"БЕЗНАЛ МРК {d.toString('dd.MM.yyyy')} ({self.current_user.full_name})",
                            pay="cashless",
                            uid=self.current_user.id
                        )
                    
                    QMessageBox.information(self, "Успех", "Выручка успешно внесена в Главную Кассу.")
            else:
                QMessageBox.information(self, "Инфо", "Смена закрыта. Выручки за смену нет.")
                
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось выполнить закрытие смены:\n{e}")