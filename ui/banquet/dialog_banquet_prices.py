import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QDialog, QSpinBox, 
    QTabWidget, QScrollArea, QGridLayout, QDialogButtonBox, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt

class BanquetPricesDialog(QDialog):
    def __init__(self, db, current_prices, addons_bee, addons_owl, current_extra, current_seasonal, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("⚙️ Глобальная настройка цен (Ultimate)")
        self.resize(950, 750)
        
        self.prices = json.loads(json.dumps(current_prices))
        self.addons_bee = self._normalize_addons(addons_bee)
        self.addons_owl = self._normalize_addons(addons_owl)
        self.extra = json.loads(json.dumps(current_extra))
        self.seasonal = json.loads(json.dumps(current_seasonal)) if current_seasonal else []
        
        self.init_ui()
    
    def _normalize_addons(self, raw_list):
        """Приводит список услуг к формату [name, price_wd, price_we]"""
        normalized = []
        for item in raw_list:
            if len(item) == 2: normalized.append([item[0], item[1], item[1]])
            else: normalized.append(item)
        return normalized
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ccc; background: white; }
            QTabBar::tab { height: 35px; width: 150px; font-weight: bold; }
            QTabBar::tab:selected { background: #E3F2FD; border-bottom: 2px solid #2196F3; }
        """)
        layout.addWidget(tabs)
        
        tab_pkg = QWidget()
        self.init_packages_tab(tab_pkg)
        tabs.addTab(tab_pkg, "🏠 Пакеты")
        
        tab_bee = QWidget()
        self.table_bee = self.init_addons_tab(tab_bee, self.addons_bee)
        tabs.addTab(tab_bee, "🐝 Допы (Пчела)")
        
        tab_owl = QWidget()
        self.table_owl = self.init_addons_tab(tab_owl, self.addons_owl)
        tabs.addTab(tab_owl, "🦉 Допы (Сова)")
        
        tab_season = QWidget()
        self.init_seasonal_tab(tab_season)
        tabs.addTab(tab_season, "📅 Сезоны / Праздники")
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def init_packages_tab(self, widget):
        layout = QVBoxLayout(widget)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        g_layout = QGridLayout(content)
        g_layout.setVerticalSpacing(15)
        
        self.price_inputs = {} 
        
        row = 0
        g_layout.addWidget(QLabel("<b>БУДНИ</b>"), row, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        g_layout.addWidget(QLabel("<b>ВЫХОДНЫЕ</b>"), row, 2, alignment=Qt.AlignmentFlag.AlignCenter)
        row += 1
        
        for room_name in ["Дом Пчелы", "Дом Совы"]:
            lbl_room = QLabel(f"🏠 {room_name}")
            lbl_room.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 14px; margin-top: 10px;")
            g_layout.addWidget(lbl_room, row, 0, 1, 3)
            row += 1
            
            for pkg in ["Мини", "Стандарт", "VIP"]:
                g_layout.addWidget(QLabel(pkg), row, 0)
                
                s_wd = QSpinBox(); s_wd.setRange(0, 999999); s_wd.setSingleStep(100); s_wd.setSuffix(" ₽")
                val_wd = self.prices.get(room_name, {}).get("weekday", {}).get(pkg, 0)
                s_wd.setValue(val_wd)
                g_layout.addWidget(s_wd, row, 1)
                self.price_inputs[f"{room_name}|weekday|{pkg}"] = s_wd
                
                s_we = QSpinBox(); s_we.setRange(0, 999999); s_we.setSingleStep(100); s_we.setSuffix(" ₽")
                val_we = self.prices.get(room_name, {}).get("weekend", {}).get(pkg, 0)
                s_we.setValue(val_we)
                g_layout.addWidget(s_we, row, 2)
                self.price_inputs[f"{room_name}|weekend|{pkg}"] = s_we
                
                row += 1
                
        g_layout.addWidget(QLabel("-----------------"), row, 0, 1, 3); row+=1
        g_layout.addWidget(QLabel("<b>Доп. Гость (чел)</b>"), row, 0)
        
        self.spin_ex_wd = QSpinBox(); self.spin_ex_wd.setRange(0, 50000); self.spin_ex_wd.setSuffix(" ₽")
        self.spin_ex_wd.setValue(self.extra.get("weekday", 0))
        g_layout.addWidget(self.spin_ex_wd, row, 1)
        
        self.spin_ex_we = QSpinBox(); self.spin_ex_we.setRange(0, 50000); self.spin_ex_we.setSuffix(" ₽")
        self.spin_ex_we.setValue(self.extra.get("weekend", 0))
        g_layout.addWidget(self.spin_ex_we, row, 2)
        
        g_layout.setRowStretch(row+1, 1)
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def init_addons_tab(self, widget, data_source):
        layout = QVBoxLayout(widget)
        
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Услуга", "Цена (Будни)", "Цена (Вых)"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        table.setRowCount(len(data_source))
        for r, item in enumerate(data_source):
            name = item[0]
            p_wd = item[1]
            p_we = item[2] if len(item) > 2 else item[1]
            
            table.setItem(r, 0, QTableWidgetItem(name))
            table.setItem(r, 1, QTableWidgetItem(str(p_wd)))
            table.setItem(r, 2, QTableWidgetItem(str(p_we)))
            
        layout.addWidget(table)
        
        btn_box = QHBoxLayout()
        btn_add = QPushButton("➕ Добавить услугу")
        btn_add.clicked.connect(lambda: self.add_addon_row(table))
        
        btn_del = QPushButton("🗑 Удалить")
        btn_del.clicked.connect(lambda: self.del_addon_row(table))
        
        btn_box.addWidget(btn_add)
        btn_box.addWidget(btn_del)
        layout.addLayout(btn_box)
        
        return table

    def add_addon_row(self, table):
        r = table.rowCount()
        table.insertRow(r)
        table.setItem(r, 0, QTableWidgetItem("Новая услуга"))
        table.setItem(r, 1, QTableWidgetItem("0"))
        table.setItem(r, 2, QTableWidgetItem("0"))

    def del_addon_row(self, table):
        r = table.currentRow()
        if r >= 0: table.removeRow(r)

    def init_seasonal_tab(self, widget):
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Укажите периоды, когда цены на пакеты повышаются (например, Новый Год)"))
        
        self.season_table = QTableWidget()
        self.season_table.setColumnCount(4)
        self.season_table.setHorizontalHeaderLabels(["Название (Праздник)", "С (ДД.ММ)", "По (ДД.ММ)", "Наценка (Руб)"])
        self.season_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.season_table.setRowCount(len(self.seasonal))
        for r, item in enumerate(self.seasonal):
            self.season_table.setItem(r, 0, QTableWidgetItem(item.get("name", "")))
            self.season_table.setItem(r, 1, QTableWidgetItem(item.get("start", "")))
            self.season_table.setItem(r, 2, QTableWidgetItem(item.get("end", "")))
            self.season_table.setItem(r, 3, QTableWidgetItem(str(item.get("amount", 0))))
            
        layout.addWidget(self.season_table)
        
        btn_box = QHBoxLayout()
        btn_add = QPushButton("➕ Добавить период"); btn_add.clicked.connect(self.add_season_row)
        btn_del = QPushButton("🗑 Удалить"); btn_del.clicked.connect(self.del_season_row)
        btn_box.addWidget(btn_add)
        btn_box.addWidget(btn_del)
        layout.addLayout(btn_box)

    def add_season_row(self):
        r = self.season_table.rowCount()
        self.season_table.insertRow(r)
        self.season_table.setItem(r, 0, QTableWidgetItem("Новый Год"))
        self.season_table.setItem(r, 1, QTableWidgetItem("15.12"))
        self.season_table.setItem(r, 2, QTableWidgetItem("10.01"))
        self.season_table.setItem(r, 3, QTableWidgetItem("500"))

    def del_season_row(self):
        r = self.season_table.currentRow()
        if r >= 0: self.season_table.removeRow(r)

    def extract_addons_from_table(self, table):
        data = []
        for r in range(table.rowCount()):
            name_item = table.item(r, 0)
            if not name_item or not name_item.text().strip(): continue
            
            name = name_item.text().strip()
            try: pwd = int(float(table.item(r, 1).text()))
            except: pwd = 0
            try: pwe = int(float(table.item(r, 2).text()))
            except: pwe = 0
            data.append([name, pwd, pwe])
        return data

    def save_settings(self):
        for key, spin in self.price_inputs.items():
            room, day_type, pkg = key.split("|")
            if room not in self.prices: self.prices[room] = {}
            if day_type not in self.prices[room]: self.prices[room][day_type] = {}
            self.prices[room][day_type][pkg] = spin.value()
            
        self.extra["weekday"] = self.spin_ex_wd.value()
        self.extra["weekend"] = self.spin_ex_we.value()
        
        self.addons_bee = self.extract_addons_from_table(self.table_bee)
        self.addons_owl = self.extract_addons_from_table(self.table_owl)
        
        new_seasonal = []
        for r in range(self.season_table.rowCount()):
            name = self.season_table.item(r, 0).text()
            start = self.season_table.item(r, 1).text()
            end = self.season_table.item(r, 2).text()
            try: amt = int(float(self.season_table.item(r, 3).text()))
            except: amt = 0
            
            if len(start.split('.')) == 2 and len(end.split('.')) == 2:
                new_seasonal.append({"name": name, "start": start, "end": end, "amount": amt})
                
        self.seasonal = new_seasonal
        
        try:
            self.db.set_setting("banquet_prices_cfg", json.dumps(self.prices, ensure_ascii=False))
            self.db.set_setting("banquet_extra_guest_cfg", json.dumps(self.extra, ensure_ascii=False))
            self.db.set_setting("banquet_seasonal_cfg", json.dumps(self.seasonal, ensure_ascii=False))
            self.db.set_setting("banquet_addons_bee_cfg", json.dumps(self.addons_bee, ensure_ascii=False))
            self.db.set_setting("banquet_addons_owl_cfg", json.dumps(self.addons_owl, ensure_ascii=False))
            
            QMessageBox.information(self, "Успех", "Настройки цен сохранены!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")