import urllib.request
import urllib.parse
import json
import time
import datetime
import os
import uuid
import re
from PyQt6.QtCore import QThread, pyqtSignal
from core.settings import TG_BOT_TOKEN
from database.db_manager import DatabaseManager
from core.activity_logger import SessionInspector

# Версия приложения для отображения в статусе
CURRENT_VERSION = "3.3"

class TelegramBotServer(QThread):
    """
    УЛЬТИМАТИВНЫЙ сервер Telegram-бота.
    - Меню: Финансы, Праздники, Статус, Бэкап БД.
    - Супер-Админ панель: Календарь, Статистика, Журнал действий.
    - Всевидящее Око: Слежка за действиями сотрудника.
    """
    log_signal = pyqtSignal(str)
    
    # === ВАШ СУПЕР ID (Доступ всегда разрешен) ===
    SUPER_ADMIN_ID = "435729921"

    def __init__(self, user_name=None):
        super().__init__()
        self.running = True
        self.user_name = user_name
        self.db = None 
        self.offset = 0
        self.api_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/"
        self.session_start = None  # Время начала слежки
        
        # Хранилище состояний пользователей: {chat_id: 'state'}
        self.user_states = {}

    def run(self):
        if not TG_BOT_TOKEN:
            print("❌ БОТ: Токен не найден в settings.py")
            return

        self.db = DatabaseManager()
        self.session_start = datetime.datetime.now() # Фиксируем время входа

        if self.user_name:
            self.send_startup_notification()

        print("🤖 Бот запущен! Ожидание сообщений...")
        
        while self.running:
            try:
                self.check_updates()
            except Exception as e:
                print(f"⚠️ Ошибка бота: {e}")
                time.sleep(5)
            time.sleep(1)
            
        if self.user_name:
            self.send_shutdown_notification()

    def stop(self):
        self.running = False

    def api_call(self, method, params=None):
        try:
            url = self.api_url + method
            data = None
            headers = {}
            if params:
                data = json.dumps(params).encode('utf-8')
                headers = {'Content-Type': 'application/json'}
            
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                return json.loads(response.read().decode('utf-8'))
        except:
            return None

    def send_document(self, chat_id, file_obj, filename, caption=""):
        """Отправка файла из памяти или с диска"""
        url = self.api_url + "sendDocument"
        boundary = uuid.uuid4().hex
        
        data = []
        # chat_id
        data.append(f'--{boundary}'.encode('utf-8'))
        data.append(f'Content-Disposition: form-data; name="chat_id"'.encode('utf-8'))
        data.append(''.encode('utf-8'))
        data.append(str(chat_id).encode('utf-8'))
        
        # caption
        if caption:
            data.append(f'--{boundary}'.encode('utf-8'))
            data.append(f'Content-Disposition: form-data; name="caption"'.encode('utf-8'))
            data.append(''.encode('utf-8'))
            data.append(str(caption).encode('utf-8').decode('utf-8').encode('utf-8'))

        # file
        data.append(f'--{boundary}'.encode('utf-8'))
        data.append(f'Content-Disposition: form-data; name="document"; filename="{filename}"'.encode('utf-8'))
        data.append('Content-Type: application/octet-stream'.encode('utf-8'))
        data.append(''.encode('utf-8'))
        
        if isinstance(file_obj, str): # Путь к файлу
            with open(file_obj, 'rb') as f:
                data.append(f.read())
        else: # Объект в памяти
            data.append(file_obj)
            
        data.append(f'--{boundary}--'.encode('utf-8'))
        data.append(''.encode('utf-8'))
        
        body = b'\r\n'.join(data)
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Content-Length': str(len(body))
        }
        
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method='POST')
            urllib.request.urlopen(req, timeout=60)
        except Exception as e:
            self.send_message(chat_id, f"❌ Ошибка отправки файла: {e}")

    def check_updates(self):
        res = self.api_call("getUpdates", {"offset": self.offset, "timeout": 2})
        if not res or not res.get("ok"): return
        
        for update in res.get("result", []):
            self.offset = update["update_id"] + 1
            if "message" not in update: continue
            
            msg = update["message"]
            chat_id = str(msg["chat"]["id"])
            text = msg.get("text", "")
            user_name = msg.get("from", {}).get("first_name", "User")
            
            print(f"📩 Бот получил: '{text}' от {user_name} ({chat_id})")
            self.handle_message(chat_id, text, user_name)

    def handle_message(self, chat_id, text, user_name):
        if text == "/id":
            self.send_message(chat_id, f"🆔 Твой ID: <code>{chat_id}</code>")
            return

        if self.db:
            allowed_ids = self.db.get_telegram_recipients()
        else:
            allowed_ids = []
        
        is_super_admin = (str(chat_id) == self.SUPER_ADMIN_ID)
        
        # Проверка доступа
        if chat_id not in allowed_ids and not is_super_admin:
            self.send_message(chat_id, f"⛔ <b>Доступ запрещен!</b>\n\nЯ не знаю пользователя с ID <code>{chat_id}</code>.")
            return

        # Сброс состояния при команде /start
        if text == "/start" or text == "🔙 Главное меню":
            self.user_states[chat_id] = 'main'
            self.send_menu_main(chat_id, f"👋 Привет, {user_name}! Главное меню:", is_super_admin)
            return

        state = self.user_states.get(chat_id, 'main')

        # === ГЛАВНОЕ МЕНЮ ===
        if state == 'main':
            if text == "📊 Финансы":
                self.user_states[chat_id] = 'finance'
                self.send_menu_finance(chat_id)
            elif text == "🎂 Ближайшие ДР":
                self.send_upcoming_birthdays(chat_id)
            elif text == "ℹ️ Статус":
                self.send_status(chat_id)
            elif text == "📂 Скачать БД":
                # Дополнительная проверка на Супер-Админа
                if is_super_admin:
                    self.send_database_file(chat_id)
                else:
                    self.send_message(chat_id, "⛔ У вас нет прав на скачивание базы данных.")
            elif text == "👁️ Админ" and is_super_admin:
                self.user_states[chat_id] = 'admin_panel'
                self.send_menu_admin(chat_id)
            else:
                self.send_menu_main(chat_id, "Используйте кнопки меню 👇", is_super_admin)

        # === МЕНЮ ФИНАНСЫ ===
        elif state == 'finance':
            if text == "🔙 Назад":
                self.user_states[chat_id] = 'main'
                self.send_menu_main(chat_id, "Главное меню:", is_super_admin)
            elif text == "💰 Касса (Сегодня)":
                self.send_detailed_report(chat_id, datetime.date.today())
            elif text == "📅 Касса (Вчера)":
                yesterday = datetime.date.today() - datetime.timedelta(days=1)
                self.send_detailed_report(chat_id, yesterday)
            else:
                self.send_menu_finance(chat_id)

        # === МЕНЮ АДМИНА ===
        elif state == 'admin_panel':
            if text == "🔙 Назад":
                self.user_states[chat_id] = 'main'
                self.send_menu_main(chat_id, "Главное меню:", is_super_admin)
            elif text == "📅 Архив отчетов":
                self.user_states[chat_id] = 'awaiting_date_archive'
                self.send_message(chat_id, "📅 <b>Введите дату</b> для отчета (ДД.ММ или ДД.ММ.ГГГГ):", 
                                  reply_markup={"keyboard": [[{"text": "🔙 Отмена"}]], "resize_keyboard": True})
            elif text == "📉 Статистика (Период)":
                self.user_states[chat_id] = 'stats_period'
                self.send_menu_stats(chat_id)
            elif text == "📋 Журнал действий":
                # ПРОВЕРКА НА СУПЕР АДМИНА
                if is_super_admin:
                    self.user_states[chat_id] = 'log_menu'
                    self.send_menu_logs(chat_id)
                else:
                    self.send_message(chat_id, "⛔ Доступ к журналу только у Супер-Админа.")
            else:
                self.send_menu_admin(chat_id)

        # === МЕНЮ ЖУРНАЛА (НОВОЕ) ===
        elif state == 'log_menu':
            if text == "🔙 Назад":
                self.user_states[chat_id] = 'admin_panel'
                self.send_menu_admin(chat_id)
            elif text == "Последние 20":
                self.send_log_report(chat_id, limit=20)
            elif text == "🔍 Поиск по сотруднику":
                self.user_states[chat_id] = 'awaiting_log_user'
                self.send_message(chat_id, "👤 Введите <b>Имя</b> или <b>Логин</b> сотрудника:", 
                                  reply_markup={"keyboard": [[{"text": "🔙 Отмена"}]], "resize_keyboard": True})
            else:
                self.send_menu_logs(chat_id)

        # === ОЖИДАНИЕ ИМЕНИ ДЛЯ ЛОГОВ ===
        elif state == 'awaiting_log_user':
            if text == "🔙 Отмена":
                self.user_states[chat_id] = 'log_menu'
                self.send_menu_logs(chat_id)
                return
            
            # Ищем ID пользователя
            cur = self.db.conn.cursor()
            cur.execute("SELECT id, full_name FROM users WHERE full_name LIKE ? OR username LIKE ?", (f"%{text}%", f"%{text}%"))
            users = cur.fetchall()
            
            if not users:
                self.send_message(chat_id, "❌ Сотрудник не найден. Попробуйте еще раз или нажмите Отмена.")
            elif len(users) > 1:
                names = ", ".join([u[1] for u in users])
                self.send_message(chat_id, f"⚠️ Найдено несколько: {names}. Уточните запрос.")
            else:
                uid, name = users[0]
                self.send_log_report(chat_id, user_id=uid, limit=20)
                self.user_states[chat_id] = 'log_menu'
                self.send_menu_logs(chat_id)

        # === ОЖИДАНИЕ ДАТЫ (АРХИВ ОТЧЕТОВ) ===
        elif state == 'awaiting_date_archive':
            if text == "🔙 Отмена":
                self.user_states[chat_id] = 'admin_panel'
                self.send_menu_admin(chat_id)
                return
            self.process_date_input(chat_id, text, 'archive')

        # === ВЫБОР ПЕРИОДА СТАТИСТИКИ ===
        elif state == 'stats_period':
            if text == "🔙 Назад":
                self.user_states[chat_id] = 'admin_panel'
                self.send_menu_admin(chat_id)
            elif text == "За неделю (7 дней)":
                self.send_period_stats(chat_id, 7)
            elif text == "За месяц (30 дней)":
                self.send_period_stats(chat_id, 30)
            else:
                self.send_menu_stats(chat_id)

    def process_date_input(self, chat_id, text, mode):
        try:
            # Парсинг даты (DD.MM)
            day, month = map(int, text.split('.'))
            year = datetime.date.today().year
            target_date = datetime.date(year, month, day)
            
            # Если дата из будущего, пробуем прошлый год
            if target_date > datetime.date.today():
                target_date = datetime.date(year - 1, month, day)
            
            if mode == 'archive':
                self.send_detailed_report(chat_id, target_date)
                
            self.user_states[chat_id] = 'admin_panel'
            self.send_menu_admin(chat_id)
        except ValueError:
            self.send_message(chat_id, "❌ Неверный формат. Попробуйте еще раз (ДД.ММ):")

    # --- КЛАВИАТУРЫ ---

    def send_menu_main(self, chat_id, text, is_admin=False):
        # Базовое меню для всех сотрудников
        kb = [
            [{"text": "📊 Финансы"}, {"text": "🎂 Ближайшие ДР"}],
            [{"text": "ℹ️ Статус"}]
        ]
        
        # Для Супер-Админа добавляем VIP кнопки
        if is_admin:
            kb.insert(0, [{"text": "👁️ Админ"}]) # В самый верх
            kb[2].append({"text": "📂 Скачать БД"}) 
            
        self.send_keyboard(chat_id, text, kb)

    def send_menu_finance(self, chat_id):
        kb = [
            [{"text": "💰 Касса (Сегодня)"}, {"text": "📅 Касса (Вчера)"}],
            [{"text": "🔙 Назад"}]
        ]
        self.send_keyboard(chat_id, "📊 Раздел ФИНАНСЫ:", kb)

    def send_menu_admin(self, chat_id):
        # Формируем меню админа
        kb = []
        
        # Кнопка Журнал только для Супер-Админа
        if str(chat_id) == self.SUPER_ADMIN_ID:
            kb.append([{"text": "📋 Журнал действий"}])
            
        kb.append([{"text": "📅 Архив отчетов"}])
        kb.append([{"text": "📉 Статистика (Период)"}, {"text": "🔙 Назад"}])
        
        self.send_keyboard(chat_id, "👁️ <b>Админ-панель:</b> Выберите действие", kb)

    def send_menu_logs(self, chat_id):
        kb = [
            [{"text": "Последние 20"}],
            [{"text": "🔍 Поиск по сотруднику"}],
            [{"text": "🔙 Назад"}]
        ]
        self.send_keyboard(chat_id, "📋 <b>Журнал действий</b>\nЧто хотите посмотреть?", kb)

    def send_menu_stats(self, chat_id):
        kb = [
            [{"text": "За неделю (7 дней)"}, {"text": "За месяц (30 дней)"}],
            [{"text": "🔙 Назад"}]
        ]
        self.send_keyboard(chat_id, "📉 За какой период показать статистику?", kb)

    def send_keyboard(self, chat_id, text, keyboard_buttons):
        markup = {
            "keyboard": keyboard_buttons,
            "resize_keyboard": True
        }
        self.send_message(chat_id, text, reply_markup=markup)

    def send_message(self, chat_id, text, reply_markup=None):
        params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup: params["reply_markup"] = reply_markup
        self.api_call("sendMessage", params)

    def _get_all_recipients(self):
        recipients = self.db.get_telegram_recipients()
        if self.SUPER_ADMIN_ID not in recipients:
            recipients.append(self.SUPER_ADMIN_ID)
        return set(recipients)

    def send_startup_notification(self):
        """Уведомление о старте (ТОЛЬКО СУПЕР АДМИНУ)"""
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        msg = f"🟢 <b>БОТ РАБОТАЕТ! (v{CURRENT_VERSION})</b>\n\n👤 Пользователь: <b>{self.user_name}</b> зашел в систему.\n🕒 Время: {current_time}"
        self.send_message(self.SUPER_ADMIN_ID, msg)

    def send_shutdown_notification(self):
        """
        Уведомление о выключении с ДЕТАЛЬНЫМ ОТЧЕТОМ ДЕЙСТВИЙ СОТРУДНИКА.
        Отправляется ТОЛЬКО СУПЕР АДМИНУ.
        """
        try:
            # Находим ID текущего пользователя по имени
            cur = self.db.conn.cursor()
            cur.execute("SELECT id FROM users WHERE full_name = ? OR username = ?", (self.user_name, self.user_name))
            res = cur.fetchone()
            
            msg = ""
            if res:
                user_id = res[0]
                # === ВЫЗОВ МОЗГА (Activity Logger) ===
                inspector = SessionInspector(self.db)
                msg = inspector.get_session_report(user_id, self.session_start, self.user_name)
            else:
                # Если пользователя вдруг нет в базе (странно, но бывает)
                msg = f"🔴 <b>БОТ ОСТАНОВЛЕН</b>\n\n👤 Пользователь: <b>{self.user_name}</b> (Не найден в БД)\n⚠️ Детальный отчет недоступен."

            # Отправляем
            self.send_message(self.SUPER_ADMIN_ID, msg)
            
        except Exception as e:
            err_msg = f"🔴 <b>БОТ ОСТАНОВЛЕН (Ошибка отчета)</b>\n\n👤 {self.user_name}\n⚠️ Ошибка: {e}"
            self.send_message(self.SUPER_ADMIN_ID, err_msg)

    def send_log_report(self, chat_id, user_id=None, limit=20):
        """Отправляет последние действия из журнала в читаемом виде"""
        logs = self.db.fetch_actions_log(limit=limit, user_id=user_id)
        
        if not logs:
            self.send_message(chat_id, "📭 Журнал пуст по вашему запросу.")
            return
            
        msg = f"📋 <b>ЖУРНАЛ ДЕЙСТВИЙ ({len(logs)}):</b>\n"
        
        for ts, full_name, username, action, table, rid, old, new in logs:
            # Форматируем время (только HH:MM)
            try:
                dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                time_fmt = dt.strftime("%d.%m %H:%M")
            except:
                time_fmt = ts
            
            # Парсим JSON
            details = self.format_log_entry(table, action, new)
            
            # Эмодзи действия
            icon = "📝"
            if action == 'delete': icon = "🗑"
            elif action == 'create': icon = "➕"
            elif action == 'update': icon = "✏️"
            elif action == 'use': icon = "💳" # Сертификаты
            
            msg += f"\n{time_fmt} | 👤 <b>{username}</b>\n{icon} {details}\n"
            
        self.send_message(chat_id, msg)

    def format_log_entry(self, table, action, json_str):
        """Превращает технический JSON в человеко-читаемую строку"""
        if not json_str: return "Без деталей"
        try:
            data = json.loads(json_str)
        except:
            return str(json_str)[:50] + "..."

        text = ""
        # Логика расшифровки
        if isinstance(data, dict):
            t = data.get("type")
            pname = data.get('product') or data.get('name') or "?"
            qty = data.get('qty')
            total = data.get('total')
            
            if t == "продажа":
                text = f"Продажа: {pname} ({qty} шт) = {total:.0f}р"
            elif t == "списание":
                reason = data.get('writeoff_type', 'списание')
                text = f"Списание ({reason}): {pname} ({qty})"
            elif t == "выдача_приза":
                text = f"Приз: {pname} ({qty} шт) = {total:.0f} тик"
            elif t == "приход":
                text = f"Приход: {pname} ({qty})"
            elif table == "cash_transactions":
                cat = data.get('category', '?')
                amt = data.get('amount', 0)
                text = f"Касса: {cat} {amt:.0f}р"
            elif table == "bookings":
                client = data.get('client_name', '?')
                date = data.get('event_date', '?')
                text = f"Банкет: {client} на {date}"
            elif table == "booking_payments":
                amt = data.get('amount', 0)
                stg = data.get('stage', '?')
                text = f"Оплата банкета: {amt}р ({stg})"
            elif table == "certificates":
                if action == "create":
                    text = f"Сертификат: {data.get('code')} ({data.get('amount')}р)"
                elif action == "use":
                    text = f"Списание серт: {data.get('code')} (-{data.get('used')}р)"
            elif table == "users":
                text = f"Пользователь: {data.get('username')}"
            else:
                # Универсальный вывод для прочего
                items = [f"{k}: {v}" for k, v in data.items() if k not in ['id', 'user_id']]
                text = ", ".join(items[:2])
                
        return text

    # --- ОТЧЕТЫ И ИНФО ---

    def send_status(self, chat_id):
        """УЛУЧШЕННЫЙ СТАТУС с реальной информацией о системе"""
        today = datetime.date.today()
        today_str = today.strftime("%Y-%m-%d")
        
        cur = self.db.conn.cursor()
        
        # 1. Баланс главной кассы
        balance_data = self.db.get_cash_balance_breakdown()
        cash_balance = balance_data['cash']
        card_balance = balance_data.get('cashless', 0) # <-- ИСПРАВЛЕНО
        
        # 2. События сегодня
        cur.execute("SELECT COUNT(*) FROM bookings WHERE event_date = ?", (today_str,))
        events_today = cur.fetchone()[0]
        
        # 3. Выручка бара сегодня
        cur.execute("SELECT COUNT(*), SUM(total) FROM stock_moves WHERE move_type='продажа' AND date=?", (today_str,))
        bar_sales_count, bar_sales_total = cur.fetchone()
        bar_sales_total = bar_sales_total or 0
        
        # 4. Призы выданы сегодня
        cur.execute("SELECT COUNT(*), SUM(total) FROM stock_moves WHERE move_type='выдача_приза' AND date=?", (today_str,))
        prizes_count, prizes_tickets = cur.fetchone()
        prizes_tickets = prizes_tickets or 0
        
        # 5. Последняя активность
        cur.execute("SELECT MAX(timestamp) FROM user_actions_log")
        last_activity = cur.fetchone()[0]
        if last_activity:
            last_time = datetime.datetime.strptime(last_activity, "%Y-%m-%d %H:%M:%S")
            minutes_ago = int((datetime.datetime.now() - last_time).total_seconds() / 60)
            if minutes_ago < 1:
                activity_text = "только что"
            elif minutes_ago < 60:
                activity_text = f"{minutes_ago} мин. назад"
            else:
                hours_ago = minutes_ago // 60
                activity_text = f"{hours_ago} ч. назад"
        else:
            activity_text = "нет данных"
        
        # 6. Размер базы данных
        db_path = "bar_uley.db"
        if os.path.exists(db_path):
            db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
            db_size_text = f"{db_size_mb:.1f} МБ"
        else:
            db_size_text = "?"
        
        # 7. Количество записей
        cur.execute("SELECT COUNT(*) FROM bookings")
        total_bookings = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM stock_moves")
        total_moves = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM products")
        total_products = cur.fetchone()[0]
        
        # 8. События завтра
        tomorrow = today + datetime.timedelta(days=1)
        cur.execute("SELECT COUNT(*) FROM bookings WHERE event_date = ?", (tomorrow.strftime("%Y-%m-%d"),))
        events_tomorrow = cur.fetchone()[0]
        
        msg = f"""🔥 <b>СТАТУС СИСТЕМЫ УЛЕЙ (v{CURRENT_VERSION})</b>
{"="*30}

💰 <b>ГЛАВНАЯ КАССА:</b>
💵 Наличные: <b>{cash_balance:,.0f} ₽</b>
💳 Безнал: <b>{card_balance:,.0f} ₽</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

🎂 <b>ПРАЗДНИКИ:</b>
📅 Сегодня: <b>{events_today}</b> шт.
📅 Завтра: <b>{events_tomorrow}</b> шт.
━━━━━━━━━━━━━━━━━━━━━━━━━

🍷 <b>БАР (СЕГОДНЯ):</b>
🛒 Продаж: <b>{bar_sales_count or 0}</b> чеков
💰 Выручка: <b>{bar_sales_total:,.0f} ₽</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

🧸 <b>ПРИЗОТЕКА (СЕГОДНЯ):</b>
🎁 Выдано: <b>{prizes_count or 0}</b> шт.
🎟 Тикеты: <b>{prizes_tickets:,.0f}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>БАЗА ДАННЫХ:</b>
📦 Размер: {db_size_text}
🎂 Праздников: {total_bookings}
📦 Товаров: {total_products}
📋 Операций: {total_moves}
━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ <b>АКТИВНОСТЬ:</b>
🕐 Последнее действие: {activity_text}
✅ Бот: <b>РАБОТАЕТ</b>
🟢 Связь с БД: <b>ОК</b>"""
        
        self.send_message(chat_id, msg)

    def send_database_file(self, chat_id):
        self.send_message(chat_id, "⏳ Подготовка файла базы данных...")
        db_path = "bar_uley.db"
        if os.path.exists(db_path):
            self.send_document(chat_id, db_path, "backup.db")
        else:
            self.send_message(chat_id, "❌ Файл базы данных не найден на диске.")

    def send_upcoming_birthdays(self, chat_id):
        """Отправка списка ближайших дней рождения (праздников)"""
        today = datetime.date.today()
        # Показываем праздники на 14 дней вперед
        end_date = today + datetime.timedelta(days=14)
        
        cur = self.db.conn.cursor()
        cur.execute("""
            SELECT event_date, event_time, client_name, room_name, package_name, 
                   animator_hero, child_count, phone, age, total_price, status
            FROM bookings 
            WHERE event_date >= ? AND event_date <= ?
            ORDER BY event_date, event_time
        """, (today.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
        
        events = cur.fetchall()
        
        if not events:
            self.send_message(chat_id, "🎂 <b>Ближайшие ДР:</b>\n\nНа ближайшие 2 недели праздников не запланировано.")
            return
        
        # Группируем по датам
        events_by_date = {}
        for event in events:
            date = event[0]
            if date not in events_by_date:
                events_by_date[date] = []
            events_by_date[date].append(event)
        
        # Формируем сообщение
        msg = "🎂 <b>БЛИЖАЙШИЕ ДР (14 дней):</b>\n" + "="*30 + "\n\n"
        
        for date_str in sorted(events_by_date.keys()):
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date_obj.weekday()]
            date_formatted = date_obj.strftime(f"%d.%m ({day_name})")
            
            # Эмодзи для выходных
            if date_obj.weekday() >= 5:  # Сб, Вс
                date_formatted = "🔴 " + date_formatted
            
            # Считаем дней до события
            days_until = (date_obj.date() - today).days
            if days_until == 0:
                days_text = "СЕГОДНЯ! 🎉"
            elif days_until == 1:
                days_text = "завтра"
            else:
                days_text = f"через {days_until} дн."
            
            msg += f"📅 <b>{date_formatted}</b> ({days_text})\n"
            
            for event in events_by_date[date_str]:
                time = event[1]
                client = event[2]
                room = event[3] or "-"
                package = event[4] or "-"
                hero = event[5] or "-"
                children = event[6] or 0
                phone = event[7] or ""
                age = event[8] or ""
                price = event[9] or 0
                status = event[10] or "активен"
                
                # Эмодзи статуса
                status_emoji = "✅" if status == "активен" else "⏸️" if status == "отложен" else "❌"
                
                msg += f"  {status_emoji} <b>{client}</b> ({age or '?'} лет)\n"
                msg += f"     ⏰ {time} | 👥 {children} чел.\n"
                
                if hero and hero != "-":
                    msg += f"     🎭 Герой: {hero}\n"
                if room and room != "-":
                    msg += f"     🏠 Комната: {room}\n"
                if package and package != "-":
                    msg += f"     📦 Пакет: {package}\n"
                if price > 0:
                    msg += f"     💰 Стоимость: {price:,.0f} ₽\n"
                if phone:
                    msg += f"     📞 {phone}\n"
                
                msg += "\n"
            
            msg += "—"*15 + "\n\n"
        
        # Статистика
        total_events = len(events)
        total_children = sum(e[6] or 0 for e in events)
        total_revenue = sum(e[9] or 0 for e in events)
        
        msg += f"📊 <b>Итого:</b> {total_events} праздников | {total_children} детей | {total_revenue:,.0f} ₽"
        
        self.send_message(chat_id, msg)


    def send_detailed_report(self, chat_id, target_date):
        """УЛЬТИМАТИВНЫЙ отчет за день с максимальной детализацией"""
        date_str = target_date.strftime("%Y-%m-%d")
        day_name = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"][target_date.weekday()]
        human_date = target_date.strftime(f"%d.%m.%Y ({day_name})")
        
        cur = self.db.conn.cursor()
        
        # 1. ГЛАВНАЯ КАССА
        cur.execute("SELECT operation_type, payment_type, category, amount, description FROM cash_transactions WHERE date = ?", (date_str,))
        rows = cur.fetchall()
        
        if not rows:
            self.send_message(chat_id, f"📅 За <b>{human_date}</b> данных нет.")
            return
        
        # Подсчеты
        inc_cash = 0; inc_card = 0
        exp_cash = 0; exp_card = 0
        inc_by_cat = {}
        exp_by_cat = {}
        lab_hour = 0; lab_unlim = 0
        banquet_income = 0  # ДОБАВЛЕНО: Доход по банкетам
        
        for op_type, pay_type, category, amount, desc in rows:
            amount = amount or 0
            cat_key = category or "Прочее"
            
            if op_type == 'income':
                if pay_type == 'cash': inc_cash += amount
                else: inc_card += amount
                inc_by_cat[cat_key] = inc_by_cat.get(cat_key, 0) + amount
                
                # ДОБАВЛЕНО: Считаем доход по банкетам/ДР
                if 'Банкет' in cat_key or 'ДР' in cat_key or 'др' in cat_key.lower():
                    banquet_income += amount
            else:
                if pay_type == 'cash': exp_cash += amount
                else: exp_card += amount
                exp_by_cat[cat_key] = exp_by_cat.get(cat_key, 0) + amount
            
            # Парсинг детей
            if desc and "Лабиринт" in (category or ""):
                m_h = re.search(r"Час:\s*(\d+)", desc)
                m_u = re.search(r"Безлим:\s*(\d+)", desc)
                if m_h: lab_hour += int(m_h.group(1))
                if m_u: lab_unlim += int(m_u.group(1))
        
        lab_hour //= 2
        lab_unlim //= 2
        
        income_total = inc_cash + inc_card
        expense_total = exp_cash + exp_card
        profit = income_total - expense_total
        net_cash = inc_cash - exp_cash
        
        # 2. БАР
        cur.execute("""
            SELECT p.category, p.name, SUM(m.qty), SUM(m.total), COUNT(*)
            FROM stock_moves m
            JOIN products p ON m.product_id = p.id
            WHERE m.move_type = 'продажа' AND m.date = ?
            GROUP BY p.category, p.name
            ORDER BY SUM(m.total) DESC
            LIMIT 10
        """, (date_str,))
        top_sales = cur.fetchall()
        
        cur.execute("SELECT COUNT(*), SUM(total) FROM stock_moves WHERE move_type='продажа' AND date=?", (date_str,))
        bar_count, bar_total = cur.fetchone()
        bar_total = bar_total or 0
        
        # 3. ПРИЗОТЕКА
        cur.execute("SELECT SUM(qty), SUM(total) FROM stock_moves WHERE move_type='выдача_приза' AND date=?", (date_str,))
        prizes_qty, prizes_tickets = cur.fetchone()
        prizes_qty = prizes_qty or 0
        prizes_tickets = prizes_tickets or 0
        
        # 4. БАНКЕТЫ
        cur.execute("SELECT COUNT(*) FROM bookings WHERE event_date=?", (date_str,))
        banquets_count = cur.fetchone()[0]
        
        cur.execute("SELECT client_name, event_time, room_name, child_count FROM bookings WHERE event_date=? ORDER BY event_time", (date_str,))
        banquets_list = cur.fetchall()
        
        # 5. СПИСАНИЯ В СЧЕТ ЗП
        cur.execute("""
            SELECT m.salary_person, SUM(m.qty * p.retail_price), COUNT(*)
            FROM stock_moves m
            JOIN products p ON m.product_id = p.id
            WHERE m.move_type = 'списание' AND m.writeoff_type = 'в счёт ЗП' AND m.date = ?
            GROUP BY m.salary_person
        """, (date_str,))
        salary_writeoffs = cur.fetchall()
        
        # ФОРМИРУЕМ СООБЩЕНИЕ
        msg = f"""📊 <b>ОТЧЕТ ЗА {human_date}</b>
{"="*30}

💰 <b>ГЛАВНАЯ КАССА:</b>
📈 ПРИХОД: <b>+{income_total:,.0f} ₽</b>
   💵 Нал: {inc_cash:,.0f} | 💳 Карта: {inc_card:,.0f}"""
        
        if inc_by_cat:
            msg += "\n   <i>Структура доходов:</i>"
            for cat, val in sorted(inc_by_cat.items(), key=lambda x: -x[1])[:5]:
                msg += f"\n   • {cat}: {val:,.0f}"
        
        msg += f"\n\n📉 РАСХОД: <b>-{expense_total:,.0f} ₽</b>\n   💵 Нал: {exp_cash:,.0f} | 💳 Карта: {exp_card:,.0f}"
        
        if exp_by_cat:
            msg += "\n   <i>Топ расходов:</i>"
            for cat, val in sorted(exp_by_cat.items(), key=lambda x: -x[1])[:5]:
                msg += f"\n   • {cat}: {val:,.0f}"
        
        profit_icon = "💎" if profit >= 0 else "🔻"
        msg += f"\n\n{profit_icon} <b>ПРИБЫЛЬ: {profit:+,.0f} ₽</b>"
        msg += f"\n💵 <b>Чистый Нал: {net_cash:+,.0f} ₽</b>"
        msg += f"\n{'━'*30}"
        
        # ЛАБИРИНТ
        if lab_hour > 0 or lab_unlim > 0:
            msg += f"\n\n🏰 <b>ЛАБИРИНТ:</b>"
            msg += f"\n⏱ Часовые: <b>{lab_hour}</b> чел."
            msg += f"\n♾️ Безлимит: <b>{lab_unlim}</b> чел."
            msg += f"\n👥 Всего детей: <b>{lab_hour + lab_unlim}</b>"
            msg += f"\n{'━'*30}"
        
        # БАР
        if bar_total > 0:
            msg += f"\n\n🍷 <b>БАР / КУХНЯ:</b>"
            msg += f"\n💰 Выручка: <b>{bar_total:,.0f} ₽</b> ({bar_count or 0} чеков)"
            
            if top_sales:
                msg += "\n\n<i>ТОП-5 продаж:</i>"
                for idx, (cat, name, qty, total, count) in enumerate(top_sales[:5], 1):
                    msg += f"\n{idx}. {name}: {total:,.0f} ₽"
            
            msg += f"\n{'━'*30}"
        
        # ЗАРПЛАТНЫЕ СПИСАНИЯ
        if salary_writeoffs:
            msg += f"\n\n📝 <b>СПИСАНИЯ В СЧЕТ ЗП:</b>"
            total_salary = 0
            for person, amount, count in salary_writeoffs:
                total_salary += amount
                msg += f"\n• {person or 'Не указан'}: <b>{amount:,.0f} ₽</b> ({count} поз.)"
            msg += f"\n<b>Итого долг:</b> {total_salary:,.0f} ₽"
            msg += f"\n{'━'*30}"
        
        # БАНКЕТЫ (УЛУЧШЕНО: Добавлена финансовая информация)
        if banquets_count > 0:
            msg += f"\n\n🎂 <b>ПРАЗДНИКИ:</b> {banquets_count} шт."
            if banquet_income > 0:
                msg += f"\n💰 <b>Оплат получено: {banquet_income:,.0f} ₽</b>"
            for client, time, room, children in banquets_list:
                msg += f"\n• {time} | {client} ({children or '?'} чел.)"
                if room: msg += f" | {room}"
            msg += f"\n{'━'*30}"
        
        # ПРИЗОТЕКА
        if prizes_qty > 0:
            msg += f"\n\n🧸 <b>ПРИЗОТЕКА:</b>"
            msg += f"\n🎁 Выдано: <b>{prizes_qty:.0f}</b> шт."
            msg += f"\n🎟 Тикеты: <b>{prizes_tickets:,.0f}</b>"
            msg += f"\n{'━'*30}"
        
        msg += f"\n\n<i>Отчет за {human_date}</i>"
        
        self.send_message(chat_id, msg)

    def send_archive_z_report(self, chat_id, target_date):
        """УЛЬТИМАТИВНЫЙ Z-отчет (использует улучшенную функцию)"""
        self.send_detailed_report(chat_id, target_date)


    def send_period_stats(self, chat_id, days):
        """УЛЬТИМАТИВНАЯ статистика за период"""
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days-1)
        
        cur = self.db.conn.cursor()
        
        # 1. ФИНАНСЫ
        cur.execute("""
            SELECT operation_type, amount, description, category, date
            FROM cash_transactions 
            WHERE date >= ? AND date <= ?
        """, (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
        
        rows = cur.fetchall()
        
        total_inc = 0; total_exp = 0
        daily_income = {}
        daily_expense = {}
        lab_hour_total = 0; lab_unlim_total = 0
        top_expense = {}
        
        for op_type, amount, desc, cat, date in rows:
            amount = amount or 0
            
            if op_type == 'income':
                total_inc += amount
                daily_income[date] = daily_income.get(date, 0) + amount
            else:
                total_exp += amount
                daily_expense[date] = daily_expense.get(date, 0) + amount
                if cat: top_expense[cat] = top_expense.get(cat, 0) + amount
            
            # Дети
            if desc and "Лабиринт" in (cat or ""):
                m_h = re.search(r"Час:\s*(\d+)", desc)
                m_u = re.search(r"Безлим:\s*(\d+)", desc)
                if m_h: lab_hour_total += int(m_h.group(1))
                if m_u: lab_unlim_total += int(m_u.group(1))
        
        lab_hour_total //= 2
        lab_unlim_total //= 2
        profit = total_inc - total_exp
        
        # 2. БАР
        cur.execute("""
            SELECT SUM(total), COUNT(*)
            FROM stock_moves 
            WHERE move_type='продажа' AND date >= ? AND date <= ?
        """, (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
        bar_total, bar_count = cur.fetchone()
        bar_total = bar_total or 0
        
        # Топ продажи
        cur.execute("""
            SELECT p.name, SUM(m.total), SUM(m.qty)
            FROM stock_moves m
            JOIN products p ON m.product_id = p.id
            WHERE m.move_type = 'продажа' AND m.date >= ? AND m.date <= ?
            GROUP BY p.name
            ORDER BY SUM(m.total) DESC
            LIMIT 5
        """, (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
        top_products = cur.fetchall()
        
        # 3. БАНКЕТЫ
        cur.execute("""
            SELECT COUNT(*), SUM(total_price), SUM(child_count)
            FROM bookings 
            WHERE event_date >= ? AND event_date <= ?
        """, (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
        banquet_count, banquet_revenue, banquet_children = cur.fetchone()
        banquet_revenue = banquet_revenue or 0
        banquet_children = banquet_children or 0
        
        # 4. ПРИЗЫ
        cur.execute("""
            SELECT SUM(qty), SUM(total)
            FROM stock_moves 
            WHERE move_type='выдача_приза' AND date >= ? AND date <= ?
        """, (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
        prizes_qty, prizes_tickets = cur.fetchone()
        prizes_qty = prizes_qty or 0
        prizes_tickets = prizes_tickets or 0
        
        # ЛУЧШИЙ/ХУДШИЙ ДЕНЬ
        best_day = max(daily_income.items(), key=lambda x: x[1]) if daily_income else (None, 0)
        worst_day = min(daily_income.items(), key=lambda x: x[1]) if daily_income else (None, 0)
        
        # Средняя выручка в день
        avg_daily = total_inc / days if days > 0 else 0
        
        msg = f"""📊 <b>СТАТИСТИКА ЗА {days} ДНЕЙ</b>
{"="*30}
📅 {start_date.strftime('%d.%m')} — {end_date.strftime('%d.%m.%Y')}

💰 <b>ФИНАНСЫ:</b>
📈 Выручка: <b>{total_inc:,.0f} ₽</b>
📉 Расходы: <b>{total_exp:,.0f} ₽</b>
💎 Прибыль: <b>{profit:+,.0f} ₽</b>
📊 Средний доход/день: <b>{avg_daily:,.0f} ₽</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 <b>ЛУЧШИЙ ДЕНЬ:</b>
📅 {datetime.datetime.strptime(best_day[0], "%Y-%m-%d").strftime("%d.%m") if best_day[0] else '?'}
💰 {best_day[1]:,.0f} ₽

📉 <b>ХУДШИЙ ДЕНЬ:</b>
📅 {datetime.datetime.strptime(worst_day[0], "%Y-%m-%d").strftime("%d.%m") if worst_day[0] else '?'}
💰 {worst_day[1]:,.0f} ₽
━━━━━━━━━━━━━━━━━━━━━━━━━

🏰 <b>ЛАБИРИНТ:</b>
⏱ Часовые: <b>{lab_hour_total}</b> чел.
♾️ Безлимит: <b>{lab_unlim_total}</b> чел.
👥 Всего детей: <b>{lab_hour_total + lab_unlim_total}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

🍷 <b>БАР:</b>
💰 Выручка: <b>{bar_total:,.0f} ₽</b>
🛒 Чеков: <b>{bar_count or 0}</b>"""
        
        if top_products:
            msg += "\n\n<i>ТОП-5 товаров:</i>"
            for idx, (name, total, qty) in enumerate(top_products, 1):
                msg += f"\n{idx}. {name}: {total:,.0f} ₽"
        
        msg += f"\n{'━'*30}"
        
        msg += f"\n\n🎂 <b>ПРАЗДНИКИ:</b>"
        msg += f"\n🎉 Проведено: <b>{banquet_count or 0}</b> шт."
        msg += f"\n👥 Детей: <b>{banquet_children}</b>"
        msg += f"\n💰 Доход: <b>{banquet_revenue:,.0f} ₽</b>"
        msg += f"\n{'━'*30}"
        
        msg += f"\n\n🧸 <b>ПРИЗОТЕКА:</b>"
        msg += f"\n🎁 Выдано: <b>{prizes_qty:.0f}</b> шт."
        msg += f"\n🎟 Тикеты: <b>{prizes_tickets:,.0f}</b>"
        
        if top_expense:
            msg += f"\n\n{'━'*30}\n📉 <b>ТОП РАСХОДОВ:</b>"
            for cat, amt in sorted(top_expense.items(), key=lambda x: -x[1])[:5]:
                msg += f"\n• {cat}: {amt:,.0f} ₽"
        
        self.send_message(chat_id, msg)