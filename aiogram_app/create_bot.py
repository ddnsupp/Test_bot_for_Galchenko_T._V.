import logging
from logging import getLogger
from logging.handlers import RotatingFileHandler
import traceback
import os
from pathlib import Path

from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import KeyboardBuilder
from dotenv import load_dotenv
from os import getenv
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.markdown import hbold
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from database import session_factory
from functools import wraps
from zoneinfo import ZoneInfo
from datetime import datetime
import asyncpg
from models import User

router = Router()

env_path = Path('..') / '.env'
load_dotenv(dotenv_path=env_path)

TOKEN = getenv("TELEGRAM_BOT_TOKEN")
WEB_SERVER_HOST = getenv("TELEGRAM_WEB_SERVER_HOST")
WEB_SERVER_PORT = int(getenv("TELEGRAM_WEB_SERVER_PORT"))
WEBHOOK_PATH = getenv("TELEGRAM_WEBHOOK_PATH")
BASE_WEBHOOK_URL = getenv("TELEGRAM_WEBHOOK_URL")
TINKOFF_PAYMENT_URI = getenv("TINKOFF_PAYMENT_URI")
# All handlers should be attached to the Router (or Dispatcher)


storage = MemoryStorage()
dp = Dispatcher(storage=storage)
bot = Bot(TOKEN, parse_mode=ParseMode.HTML)



async def add_message_to_delete(user_telegram_id, message_id):
    async with session_factory() as session:
        try:
            user = session.query(User).filter_by(telegram_id=user_telegram_id).first()
            if user:
                if not user.messages_to_delete:
                    user.messages_to_delete = [message_id]
                else:
                    user.messages_to_delete.append(message_id)
                session.commit()

        except Exception as e:
            # Обработка ошибок
            log_message('error', f'Ошибка при выполнении SQL-запросов: {e}', user_telegram_id, traceback.extract_stack()[-1])



current_file_path = Path(__file__).resolve()
project_root_path = current_file_path.parent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_filename = project_root_path / str(getenv("LOG_FILENAME"))
log_max_size = 10 * 1024 * 1024  # DS: 10 МБ размер файла логов
log_backup_count = 10  # DS: 10 файлов бекапа
log_handler = RotatingFileHandler(log_filename, maxBytes=log_max_size, backupCount=log_backup_count)
log_handler.setLevel(logging.INFO)
logging.getLogger('aiogram').setLevel(logging.WARNING)  # DS: ограничение технических сообщений от aiogram
formatter = logging.Formatter('[%(asctime)s %(levelname)s, %(tid)s] %(traceback)s] %(message)s')
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)
logger.propagate = False

project_dir = os.getcwd()


def log_message(log_type: str, message: str, tid: int, traceback_info):
    traceback_info = str(traceback_info).replace(project_dir, '').replace(r"<FrameSummary file ", "")
    if log_type == 'info' or log_type == 'message':
        logger.info(message, extra={'tid': tid, 'traceback': traceback_info})

    elif log_type == 'warning':
        logger.warning(message, extra={'tid': tid, 'traceback': traceback_info})

    elif log_type == 'error':
        logger.error(message, extra={'tid': tid, 'traceback': traceback_info})


def convert_epoch_to_moscow(epoch_time):
    moscow_datetime = datetime.fromtimestamp(epoch_time, tz=ZoneInfo("Europe/Moscow"))
    formatted_datetime = moscow_datetime.strftime('%Y-%m-%d %H:%M:%S')
    return formatted_datetime


def get_common_user_keyboard():
    keyboard_builder = KeyboardBuilder(button_type=InlineKeyboardButton)
    keyboard = {
        'Каталог': 'catalogue',
        'Корзина': 'cart',
        'FAQ': 'about',
    }
    for k, v in keyboard.items():
        keyboard_builder.row(types.InlineKeyboardButton(text=k, callback_data=v))
    return keyboard_builder


def get_state_cancel_keyboard(param):
    keyboard_builder = KeyboardBuilder(button_type=InlineKeyboardButton)
    keyboard = {
        'Прекратить ввод': f'cancel_state_{param}',
    }
    for k, v in keyboard.items():
        keyboard_builder.row(types.InlineKeyboardButton(text=k, callback_data=v))
    return keyboard_builder

