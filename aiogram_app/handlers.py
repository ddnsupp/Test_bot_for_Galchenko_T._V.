import re

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, InputFile, FSInputFile
from aiogram.utils.keyboard import KeyboardBuilder
from aiogram.utils.markdown import hbold
from database import connect_to_postgres
import random
import string
from create_bot import (
    bot,
    dp,
    router,
    WEBHOOK_PATH,
    WEB_SERVER_HOST,
    WEB_SERVER_PORT,
    BASE_WEBHOOK_URL,
    add_message_to_delete,
    log_message
)
import traceback
import os
from pathlib import Path
from dotenv import load_dotenv  # Импортируем load_dotenv
from os import getenv
from utils import display_main_keyboard
from models import User


env_path = Path('..') / '.env'
load_dotenv(dotenv_path=env_path)


def generate_unique_id():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(18))


@router.message(CommandStart())
# @delete_messages_decorator
async def command_start_handler(message: Message, state: FSMContext) -> None:
    try:
        user_tid = message.from_user.id
        engine, session_maker = await connect_to_postgres()

        async with session_maker() as session:
            user = session.query(User).filter_by(telegram_id=user_tid).first()
            if not user:
                new_user = User(
                    telegram_id=user_tid,
                    username=message.from_user.username,
                )
                session.add(new_user)
                session.commit()

        await message.answer("Добро пожаловать!")

    except Exception as e:
        log_message('error',
                    f'Ошибка обработчика "/start": {e}',
                    message.from_user.id,
                    traceback.extract_stack()[-1])


@router.message(Command("log"))
async def log_handler(message: Message) -> None:
    current_file_path = Path(__file__).resolve()
    project_root_path = current_file_path.parent
    log_filename = str(project_root_path / str(getenv("LOG_FILENAME")))
    file = FSInputFile(
        path=log_filename)
    await bot.send_document(message.from_user.id, document=file, )


@router.message(Command("xls"))
async def log_handler(message: Message) -> None:
    ...
