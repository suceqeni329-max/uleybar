from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PyQt6.QtCore import Qt
from .tab_bonus_journal import BonusJournalTab as JournalView
from .tab_promo_manager import PromotionsManagerTab

class BonusJournalTab(QWidget):
    """
    Контейнер, объединяющий Журнал Бонусов и Конструктор Акций.
    """
    def __init__(self, db, current_user):
        super().__init__()
        self.db = db
        self.current_user = current_user
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0; background: #fff; }
            QTabBar::tab { 
                height: 35px; 
                padding: 0 20px; 
                font-weight: bold; 
                color: #555;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                background: #f0f0f0;
                margin-right: 2px;
            }
            QTabBar::tab:selected { 
                color: #2E7D32; 
                background: #fff;
                border-top: 2px solid #2E7D32; 
            }
        """)
        
        # Вкладка 1: Журнал бонусов (как было)
        self.journal_tab = JournalView(self.db, self.current_user)
        self.tabs.addTab(self.journal_tab, "🎁 Журнал бонусов")
        
        # Вкладка 2: Менеджер Акций (ПОЛНОЦЕННЫЙ)
        self.promo_tab = PromotionsManagerTab(self.db, self.current_user)
        self.tabs.addTab(self.promo_tab, "🔥 Конструктор Акций")
        
        layout.addWidget(self.tabs)