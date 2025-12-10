import urllib.request
import json
import time
import os
import uuid
from PyQt6.QtCore import QThread, pyqtSignal
from core.settings import TG_BOT_TOKEN, TG_CHAT_ID

class TelegramSender(QThread):
    """
    Фоновый поток для отправки сообщений и файлов в Telegram.
    Поддерживает массовую рассылку нескольким получателям.
    """
    finished_signal = pyqtSignal(bool, str) # success, message

    def __init__(self, message_text, recipients=None, files=None):
        super().__init__()
        self.message_text = message_text
        self.files = files if files else []
        
        # Если получатели переданы явно (список из БД), используем их.
        # Иначе берем дефолтный ID из настроек (как запасной вариант).
        if recipients and isinstance(recipients, list) and len(recipients) > 0:
            self.recipients = recipients
        elif TG_CHAT_ID:
            self.recipients = [TG_CHAT_ID]
        else:
            self.recipients = []
            
        self.api_url_msg = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        self.api_url_doc = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"

    def run(self):
        # Базовая проверка токена
        if not TG_BOT_TOKEN:
            self.finished_signal.emit(False, "Ошибка: Не настроен TG_BOT_TOKEN в settings.py")
            return

        if not self.recipients:
            self.finished_signal.emit(False, "Ошибка: Нет получателей (база пуста и TG_CHAT_ID не задан)")
            return

        success_count = 0
        errors = []

        # Проходим по всем получателям
        for chat_id in self.recipients:
            if not chat_id: continue
            
            try:
                # 1. Отправка текста
                data = {
                    "chat_id": chat_id,
                    "text": self.message_text,
                    "parse_mode": "HTML"
                }
                
                json_data = json.dumps(data).encode('utf-8')
                
                req = urllib.request.Request(
                    self.api_url_msg, 
                    data=json_data, 
                    headers={'Content-Type': 'application/json', 'User-Agent': 'BarUleyApp/3.0'}
                )
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        success_count += 1
                    else:
                        errors.append(f"Msg ID {chat_id}: код {response.status}")
                
                # 2. Отправка файлов (если есть)
                for file_path in self.files:
                    if os.path.exists(file_path):
                        self.send_file(chat_id, file_path)
                        time.sleep(1) # Пауза для тяжелых файлов
                
                # Пауза 0.3 сек между пользователями
                time.sleep(0.3)
                
            except Exception as e:
                errors.append(f"ID {chat_id}: {str(e)}")

        # Формируем итоговый отчет о рассылке
        if success_count > 0:
            msg = f"Отправлено: {success_count} из {len(self.recipients)} сотр."
            if self.files:
                msg += f" (+БД)"
            if errors: msg += f" (Ошибки: {len(errors)})"
            self.finished_signal.emit(True, msg)
        else:
            self.finished_signal.emit(False, f"Сбой рассылки: {'; '.join(errors[:3])}...")

    def send_file(self, chat_id, file_path):
        """Отправка файла через multipart/form-data"""
        boundary = uuid.uuid4().hex
        filename = os.path.basename(file_path)
        
        data = []
        # chat_id
        data.append(f'--{boundary}'.encode('utf-8'))
        data.append(f'Content-Disposition: form-data; name="chat_id"'.encode('utf-8'))
        data.append(''.encode('utf-8'))
        data.append(str(chat_id).encode('utf-8'))
        
        # file
        data.append(f'--{boundary}'.encode('utf-8'))
        data.append(f'Content-Disposition: form-data; name="document"; filename="{filename}"'.encode('utf-8'))
        data.append('Content-Type: application/octet-stream'.encode('utf-8'))
        data.append(''.encode('utf-8'))
        
        with open(file_path, 'rb') as f:
            data.append(f.read())
            
        data.append(f'--{boundary}--'.encode('utf-8'))
        data.append(''.encode('utf-8'))
        
        body = b'\r\n'.join(data)
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Content-Length': str(len(body)),
            'User-Agent': 'BarUleyApp/3.0'
        }
        
        try:
            req = urllib.request.Request(self.api_url_doc, data=body, headers=headers, method='POST')
            urllib.request.urlopen(req, timeout=60)
        except Exception as e:
            print(f"File send error: {e}")

def send_telegram_sync(text, recipients=None):
    """
    Синхронная функция отправки (для критических ошибок).
    """
    if not TG_BOT_TOKEN: return False
    
    targets = recipients if recipients else ([TG_CHAT_ID] if TG_CHAT_ID else [])
    
    for chat_id in targets:
        try:
            url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
            data = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=5)
        except:
            pass
    return True