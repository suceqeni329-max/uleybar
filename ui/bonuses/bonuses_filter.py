from PyQt6.QtWidgets import (
    QGroupBox, QGridLayout, QDateEdit, QPushButton, QLabel, 
    QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal

class FilterPanel(QGroupBox):
    """Панель расширенных фильтров"""
    filter_changed = pyqtSignal() # Сигнал для быстрой фильтрации (поиск, комбобоксы)
    date_range_changed = pyqtSignal() # Сигнал для перезагрузки БД (даты)

    def __init__(self, db, parent=None):
        super().__init__("🔍 Фильтрация и Поиск", parent)
        self.db = db
        self.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                border: 1px solid #aaa; 
                border-radius: 8px; 
                margin-top: 10px; 
                background-color: #fafafa;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #555; }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout(self)
        layout.setSpacing(10)
        
        # Ряд 1: Даты + Кнопка Применить
        self.date_from = QDateEdit(QDate.currentDate().addDays(-7))
        self.date_from.setCalendarPopup(True)
        # Отключаем авто-обновление при смене даты, чтобы не спамить запросами
        
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        
        self.btn_apply_dates = QPushButton("📅 Показать отчет за период")
        self.btn_apply_dates.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply_dates.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; color: white; font-weight: bold; 
                border-radius: 4px; padding: 5px 15px;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.btn_apply_dates.clicked.connect(self.date_range_changed.emit)
        
        layout.addWidget(QLabel("Период с:"), 0, 0)
        layout.addWidget(self.date_from, 0, 1)
        layout.addWidget(QLabel("по:"), 0, 2)
        layout.addWidget(self.date_to, 0, 3)
        layout.addWidget(self.btn_apply_dates, 0, 4)
        
        # Ряд 2: Параметры (фильтруем на лету)
        self.combo_user = QComboBox()
        self.combo_user.addItem("Все сотрудники", None)
        self.load_users()
        self.combo_user.currentIndexChanged.connect(self.filter_changed.emit)
        
        self.combo_reason = QComboBox()
        self.combo_reason.addItems(["Все причины", "Сертификат", "Не дал игру", "Лояльность", "Розыгрыш", "Игровая площадка", "Ручные тикеты", "Возврат", "Прочее"])
        self.combo_reason.currentIndexChanged.connect(self.filter_changed.emit)
        
        layout.addWidget(QLabel("Сотрудник:"), 1, 0)
        layout.addWidget(self.combo_user, 1, 1)
        layout.addWidget(QLabel("Причина:"), 1, 2)
        layout.addWidget(self.combo_reason, 1, 3, 1, 2)
        
        # Ряд 3: Поиск и Сброс
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по № карты или комментарию...")
        self.search_edit.textChanged.connect(self.filter_changed.emit)
        
        self.btn_reset = QPushButton("Сбросить фильтры")
        self.btn_reset.setStyleSheet("color: #D32F2F; border: 1px solid #D32F2F; background: white; border-radius: 4px;")
        self.btn_reset.clicked.connect(self.reset_filters)
        
        layout.addWidget(QLabel("Поиск:"), 2, 0)
        layout.addWidget(self.search_edit, 2, 1, 1, 2)
        layout.addWidget(self.btn_reset, 2, 3, 1, 2)

    def load_users(self):
        try:
            users = self.db.fetch_users()
            for u in users:
                # u = (id, username, fullname, role, ...)
                if len(u) >= 3:
                    name = u[2] if u[2] else u[1]
                    self.combo_user.addItem(name, u[0])
        except: pass

    def reset_filters(self):
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_to.setDate(QDate.currentDate())
        self.combo_user.setCurrentIndex(0)
        self.combo_reason.setCurrentIndex(0)
        self.search_edit.clear()
        self.date_range_changed.emit() # Перезагружаем данные за дефолтный период

    def get_filters(self):
        return {
            "d1": self.date_from.date().toString("yyyy-MM-dd"),
            "d2": self.date_to.date().toString("yyyy-MM-dd"),
            "user_id": self.combo_user.currentData(),
            "reason": self.combo_reason.currentText(),
            "search": self.search_edit.text().strip().lower()
        }