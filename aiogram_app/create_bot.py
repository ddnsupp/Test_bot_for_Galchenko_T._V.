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
from functools import wraps
from zoneinfo import ZoneInfo
from datetime import datetime
import asyncpg
from models import User
from database import session_factory
from sqlalchemy import select, func, update
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.exc import SQLAlchemyError


router = Router()

env_path = Path('..') / '.env'
load_dotenv(dotenv_path=env_path)

TOKEN = getenv("TELEGRAM_BOT_TOKEN")
WEB_SERVER_HOST = getenv("TELEGRAM_WEB_SERVER_HOST")
WEB_SERVER_PORT = int(getenv("TELEGRAM_WEB_SERVER_PORT"))
WEBHOOK_PATH = getenv("TELEGRAM_WEBHOOK_PATH")
BASE_WEBHOOK_URL = getenv("TELEGRAM_WEBHOOK_URL")
BOTNAME = getenv('SERVICE_OFFICAIL_NAME')
SUBSCRIPTION_GROUP_ID = getenv('SUBSCRIPTION_GROUP_ID')
SUBSCRIPTION_GROUP_URL = getenv('SUBSCRIPTION_GROUP_URL')
XLSX_FILENAME = str(getenv("XLSX_FILENAME"))
LOG_FILENAME = str(getenv("LOG_FILENAME"))
admins_str = os.getenv('ADMINS', '')
ADMINS = [int(admin) for admin in admins_str.split(',') if admin.isdigit()]
UKASSA_TOKEN = str(os.getenv('UKASSA_TOKEN'))


storage = MemoryStorage()
dp = Dispatcher(storage=storage)
bot = Bot(TOKEN, parse_mode=ParseMode.HTML)


async def add_message_to_delete(user_telegram_id, message_id):
    async with session_factory() as session:
        try:
            stmt = update(User).where(User.t_id == user_telegram_id). \
                values({User.messages_to_delete: func.array_append(User.messages_to_delete, message_id)}). \
                returning(User.messages_to_delete)

            result = await session.execute(stmt)
            await session.commit()

        except Exception as e:
            log_message('error',
                        f'Ошибка при выполнении SQL-запросов: {e}',
                        user_telegram_id,
                        traceback.extract_stack()[-1]
                        )


async def delete_previous_messages(user_telegram_id):
    async with session_factory() as session:
        try:
            result = await session.execute(select(User).filter_by(t_id=user_telegram_id))
            user = result.scalars().first()
            if user and user.messages_to_delete:
                for message_id in user.messages_to_delete:
                    try:
                        await bot.delete_message(chat_id=user_telegram_id, message_id=message_id)
                    except Exception as e:
                        ...

                stmt = update(User).where(User.t_id == user_telegram_id).values(
                    messages_to_delete=func.array_remove(User.messages_to_delete, message_id)
                )
                await session.execute(stmt)
                await session.commit()
        except SQLAlchemyError as e:
            log_message('error',
                        f"Ошибка при обновлении пользователя {user_telegram_id}: {e}",
                        user_telegram_id,
                        traceback.extract_stack()[-1]
                        )



current_file_path = Path(__file__).resolve()
project_root_path = current_file_path.parent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_filename = project_root_path / LOG_FILENAME
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
        '🛍️ Каталог': 'choose_category',
        '🛒 Корзина': 'check_cart',
        '📌 FAQ': 'FAQ|',
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

