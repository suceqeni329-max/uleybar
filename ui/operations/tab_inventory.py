from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QBrush

from database.db_manager import DatabaseManager
from core.utils import CurrentUser

class InventoryTab(QWidget):
    """Вкладка ИНВЕНТАРИЗАЦИЯ (Бар/Склад)"""
    def __init__(self, db: DatabaseManager, current_user: CurrentUser):
        super().__init__()
        self.db = db
        self.current_user = current_user
        self.init_ui()
    
    def showEvent(self, event):
        self.load_data()
        super().showEvent(event)

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        top = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Пересчитать остатки")
        refresh_btn.clicked.connect(self.load_data)
        
        save_btn = QPushButton("💾 Сохранить инвентаризацию (Внести корректировки)")
        save_btn.clicked.connect(self.save_inventory)
        save_btn.setStyleSheet("background-color: #ffcccc;")
        
        top.addWidget(refresh_btn)
        top.addStretch()
        top.addWidget(save_btn)
        layout.addLayout(top)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Товар", "Ед.", "Расчетный остаток", "Фактический остаток", "Разница"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Делаем колонку "Факт" редактируемой
        self.table.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.table)
        
    def load_data(self):
        self.table.blockSignals(True)
        # calc_stock теперь возвращает только товары НЕ ПРИЗЫ
        rows = self.db.calc_stock()
        self.table.setRowCount(0)
        
        # Фильтруем техкарты (инвентаризация только для реальных товаров)
        real_products = [r for r in rows if not r[8]]
        self.table.setRowCount(len(real_products))
        
        for r, row in enumerate(real_products):
            # row: id, name, uom, ..., stock, ...
            pid, name, uom, stock = row[0], row[1], row[2], row[6]
            
            self.table.setItem(r, 0, QTableWidgetItem(str(pid)))
            self.table.setItem(r, 1, QTableWidgetItem(name))
            self.table.setItem(r, 2, QTableWidgetItem(uom))
            
            stock_item = QTableWidgetItem(str(stock))
            stock_item.setFlags(Qt.ItemFlag.ItemIsEnabled) # Read only
            self.table.setItem(r, 3, stock_item)
            
            fact_item = QTableWidgetItem(str(stock)) # По умолчанию факт = расчет
            self.table.setItem(r, 4, fact_item)
            
            diff_item = QTableWidgetItem("0")
            diff_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, 5, diff_item)
            
        self.table.blockSignals(False)

    def on_item_changed(self, item):
        row = item.row()
        if item.column() == 4: # Если изменили факт
            try:
                calc = float(self.table.item(row, 3).text())
                fact = float(item.text().replace(",", "."))
                diff = fact - calc
                
                diff_item = self.table.item(row, 5)
                diff_item.setText(f"{diff:.3f}")
                
                if diff < 0: diff_item.setForeground(QBrush(QColor("red")))
                elif diff > 0: diff_item.setForeground(QBrush(QColor("green")))
                else: diff_item.setForeground(QBrush(QColor("black")))
            except: pass

    def save_inventory(self):
        reply = QMessageBox.question(self, "Подтверждение", 
                                     "Будут созданы операции списания/прихода для выравнивания остатков.\nПродолжить?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        
        date = QDate.currentDate()
        user_id = self.current_user.id
        
        for r in range(self.table.rowCount()):
            try:
                pid = int(self.table.item(r, 0).text())
                diff = float(self.table.item(r, 5).text().replace(",", "."))
                
                if diff == 0: continue
                
                if diff < 0:
                    # Недостача -> списание
                    qty = abs(diff)
                    self.db.add_stock_move(date, pid, qty, "недостача_инв", 
                                           comment="Инвентаризация (авто)", writeoff_type="недостача", user_id=user_id)
                else:
                    # Излишек -> приход
                    qty = diff
                    self.db.add_stock_move(date, pid, qty, "излишек_инв", unit_price=0, total=0,
                                           comment="Инвентаризация (авто)", user_id=user_id)
            except: continue
            
        QMessageBox.information(self, "Успех", "Корректировки внесены")
        self.load_data()