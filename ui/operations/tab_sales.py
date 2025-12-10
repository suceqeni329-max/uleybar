import os
import webbrowser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QComboBox, QSpinBox, QDateEdit, QMessageBox, 
    QCheckBox, QHeaderView, QSplitter
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QBrush, QTextCharFormat

from database.db_manager import DatabaseManager
from core.utils import CurrentUser

class SalesTab(QWidget):
    """Вкладка ПРОДАЖИ (Админ/Офис)"""
    def __init__(self, db: DatabaseManager, current_user: CurrentUser):
        super().__init__()
        self.db, self.current_user = db, current_user
        self.init_ui()

    def showEvent(self, event):
        self.refresh()
        super().showEvent(event)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(["ID", "№", "Товар", "Цена", "Кол-во", "Ед", "Сумма", "Оплата", "Сотр", "Комм", "PID"])
        self.table.setColumnHidden(0, True); self.table.setColumnHidden(10, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.currentCellChanged.connect(self.on_select)
        top_layout.addWidget(self.table)
        splitter.addWidget(top_widget)
        
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(QLabel("Выручка по дням:"))
        self.rev_table = QTableWidget()
        self.rev_table.setColumnCount(2)
        self.rev_table.setHorizontalHeaderLabels(["Дата", "Выручка"])
        self.rev_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        bottom_layout.addWidget(self.rev_table)
        splitter.addWidget(bottom_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        form = QHBoxLayout()
        self.range_check = QCheckBox("За период")
        self.range_check.toggled.connect(self.toggle_range_mode)
        self.date_edit = QDateEdit(QDate.currentDate()); self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.load_data)
        
        self.date_end_edit = QDateEdit(QDate.currentDate()); self.date_end_edit.setCalendarPopup(True)
        self.date_end_edit.dateChanged.connect(self.load_data)
        self.date_end_edit.setVisible(False)
        self.lbl_to = QLabel("по"); self.lbl_to.setVisible(False)
        
        self.prod_box = QComboBox()
        self.prod_box.setMinimumWidth(300)
        self.prod_box.view().setMinimumWidth(450)
        self.prod_box.setMaxVisibleItems(15)
        self.prod_box.currentIndexChanged.connect(self.on_prod_change)
        
        self.qty_spin = QSpinBox(); self.qty_spin.setRange(1, 10000); self.qty_spin.valueChanged.connect(self.calc)
        self.price_edit = QLineEdit(); self.price_edit.textChanged.connect(self.calc)
        self.sum_lbl = QLabel("0.00")
        self.uom_lbl = QLabel("шт")
        self.pay_box = QComboBox(); self.pay_box.addItems(["нал", "безнал"])
        
        self.emp_edit = QLineEdit()
        self.emp_edit.setText(self.current_user.full_name)
        if self.current_user.role != "admin":
            self.emp_edit.setReadOnly(True)

        self.comm_edit = QLineEdit(); self.comm_edit.setPlaceholderText("Комментарий")

        btns = [QPushButton("Продать"), QPushButton("Изменить"), QPushButton("Удалить"), QPushButton("Отчет")]
        btns[0].clicked.connect(self.add); btns[1].clicked.connect(self.update)
        btns[2].clicked.connect(self.delete); btns[3].clicked.connect(self.export)
        
        if not self.current_user.can("can_add_sales"): btns[0].setEnabled(False); btns[1].setEnabled(False)
        if not self.current_user.can("can_delete"): btns[2].setEnabled(False)

        form.addWidget(self.range_check)
        form.addWidget(QLabel("Дата"))
        form.addWidget(self.date_edit)
        form.addWidget(self.lbl_to)
        form.addWidget(self.date_end_edit)
        
        form.addWidget(QLabel("Товар"))
        form.addWidget(self.prod_box)
        form.addWidget(QLabel("Кол-во"))
        form.addWidget(self.qty_spin)
        form.addWidget(QLabel("Ед."))
        form.addWidget(self.uom_lbl)
        form.addWidget(QLabel("Цена"))
        form.addWidget(self.price_edit)
        form.addWidget(QLabel("Сумма"))
        form.addWidget(self.sum_lbl)
        form.addWidget(QLabel("Оплата"))
        form.addWidget(self.pay_box)
        form.addWidget(QLabel("Сотр."))
        form.addWidget(self.emp_edit)
        form.addWidget(self.comm_edit)
        
        for b in btns: form.addWidget(b)
        main_layout.addLayout(form)

    def toggle_range_mode(self, checked):
        self.lbl_to.setVisible(checked)
        self.date_end_edit.setVisible(checked)
        self.load_data()

    def refresh(self):
        curr_id = self.prod_box.currentData()
        self.prod_box.blockSignals(True)
        self.prod_box.clear()
        
        # Только товары (без игрушек)
        for pid, name, *_ in self.db.fetch_products_by_type("товар"): 
            self.prod_box.addItem(name, pid)
            
        if curr_id is not None:
            idx = self.prod_box.findData(curr_id)
            if idx >= 0: self.prod_box.setCurrentIndex(idx)
        self.prod_box.blockSignals(False)
        
        self.on_prod_change()
        self.load_data()
        self.mark_dates()
        self.load_rev()
        if self.current_user.role != "admin":
            self.emp_edit.setText(self.current_user.full_name)

    def load_data(self):
        d1 = self.date_edit.date().toString("yyyy-MM-dd")
        if self.range_check.isChecked():
            d2 = self.date_end_edit.date().toString("yyyy-MM-dd")
            rows = self.db.fetch_sales_for_range(d1, d2)
        else:
            rows = self.db.fetch_sales_for_date_full(d1)
            
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            mid, pid, name, pr, qty, uom, tot, pay, emp, com = row[:10]
            self.table.setItem(r, 0, QTableWidgetItem(str(mid)))
            num_or_date = row[10] if len(row) > 10 else str(r+1)
            self.table.setItem(r, 1, QTableWidgetItem(str(num_or_date)))
            self.table.setItem(r, 2, QTableWidgetItem(name))
            self.table.setItem(r, 3, QTableWidgetItem(str(pr)))
            self.table.setItem(r, 4, QTableWidgetItem(str(qty)))
            self.table.setItem(r, 5, QTableWidgetItem(uom))
            self.table.setItem(r, 6, QTableWidgetItem(str(tot)))
            self.table.setItem(r, 7, QTableWidgetItem(pay))
            self.table.setItem(r, 8, QTableWidgetItem(emp))
            self.table.setItem(r, 9, QTableWidgetItem(com))
            self.table.setItem(r, 10, QTableWidgetItem(str(pid)))

    def load_rev(self):
        rows = self.db.fetch_revenue_by_date()
        self.rev_table.setRowCount(len(rows))
        for r, (d, rev) in enumerate(rows):
            self.rev_table.setItem(r, 0, QTableWidgetItem(d))
            self.rev_table.setItem(r, 1, QTableWidgetItem(str(rev)))

    def on_prod_change(self):
        if self.prod_box.count() == 0: return
        p = self.db.get_product(self.prod_box.currentData())
        if p:
            self.uom_lbl.setText(p[3]); self.price_edit.setText(str(p[5]))
            self.calc()

    def calc(self):
        try: self.sum_lbl.setText(f"{(self.qty_spin.value() * float(self.price_edit.text() or 0)):.2f}")
        except: pass

    def on_select(self, r, c, pr, pc):
        if r < 0: return
        try:
            pid = int(self.table.item(r, 10).text())
            idx = self.prod_box.findData(pid)
            if idx >= 0: self.prod_box.setCurrentIndex(idx)
            
            self.qty_spin.setValue(int(float(self.table.item(r, 4).text())))
            self.price_edit.setText(self.table.item(r, 3).text())
            self.pay_box.setCurrentText(self.table.item(r, 7).text())
            self.emp_edit.setText(self.table.item(r, 8).text())
            self.comm_edit.setText(self.table.item(r, 9).text())
        except: pass

    def get_data(self):
        return (self.date_edit.date(), self.prod_box.currentData(), self.qty_spin.value(),
                float(self.price_edit.text() or 0), float(self.sum_lbl.text()),
                self.pay_box.currentText(), self.emp_edit.text(), self.comm_edit.text())

    def add(self):
        d = self.get_data()
        self.db.add_stock_move(d[0], d[1], d[2], "продажа", d[3], d[4], employee=d[6], comment=d[7], payment_type=d[5], user_id=self.current_user.id)
        self.db.consume_ingredients_for_sale(d[0], d[1], d[2], self.current_user.id)
        self.refresh()

    def update(self):
        r = self.table.currentRow()
        if r < 0: return
        mid = int(self.table.item(r, 0).text())
        d = self.get_data()
        self.db.update_sales_move(mid, d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7], self.current_user.id)
        self.refresh()

    def delete(self):
        r = self.table.currentRow()
        if r < 0: return
        mid = int(self.table.item(r, 0).text())
        if QMessageBox.question(self, "?", "Удалить?", QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.db.delete_move(mid, self.current_user.id)
            self.refresh()

    def mark_dates(self):
        fmt = QTextCharFormat(); fmt.setBackground(QBrush(QColor("#fff2a8")))
        for d in self.db.fetch_dates_with_sales():
            self.date_edit.calendarWidget().setDateTextFormat(QDate.fromString(d, "yyyy-MM-dd"), fmt)

    def export(self):
        d = self.date_edit.date()
        if self.range_check.isChecked():
            html = self.db.build_sales_report_range_html(d, self.date_end_edit.date())
            folder = os.path.join("reports", "продажи_диапазон", d.toString("yyyy-MM"))
            os.makedirs(folder, exist_ok=True)
            fn = os.path.join(folder, f"продажи_{d.toString('yyyyMMdd')}_{self.date_end_edit.date().toString('yyyyMMdd')}.html")
        else:
            html = self.db.build_daily_report_html(d)
            folder = os.path.join("reports", "дневные_отчёты", d.toString("yyyy-MM"))
            os.makedirs(folder, exist_ok=True)
            fn = os.path.join(folder, f"отчёт_{d.toString('yyyyMMdd')}.html")
            
        with open(fn, "w", encoding="utf-8") as f: f.write(html)
        webbrowser.open(os.path.abspath(fn))