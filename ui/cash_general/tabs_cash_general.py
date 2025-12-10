from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from .tab_cash_general_ops import LabyrinthOperationsTab
from .tab_cash_general_analytics import GeneralCashMainView

class GeneralCashTab(QWidget):
    """Главная вкладка-контейнер для раздела Главная Касса"""
    def __init__(self, db, current_user):
        super().__init__()
        self.db = db
        self.current_user = current_user
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ccc; background: white; }
            QTabBar::tab { 
                height: 40px; 
                padding: 0 20px; 
                font-weight: bold; 
                color: #555;
            }
            QTabBar::tab:selected { 
                color: #2E7D32; 
                border-bottom: 2px solid #2E7D32; 
                background-color: #f0f8f0;
            }
        """)
        
        # Вкладка 1: Ввод операций (Касса и Лабиринт)
        self.ops_view = LabyrinthOperationsTab(self.db, self.current_user)
        self.tabs.addTab(self.ops_view, "💵 Касса и Лабиринт")

        # Вкладка 2: Основная касса
        if self.current_user.can("can_manage_cash") or self.current_user.is_admin():
            self.main_view = GeneralCashMainView(self.db, self.current_user)
            self.tabs.addTab(self.main_view, "💰 Общий баланс и Аналитика")
        
        layout.addWidget(self.tabs)