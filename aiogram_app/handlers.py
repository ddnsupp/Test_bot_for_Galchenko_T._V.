from aiogram import Bot, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile,  CallbackQuery
from database import session_factory
from sqlalchemy.future import select
from create_bot import (
    bot,
    router,
    BOTNAME,
    LOG_FILENAME,
    XLSX_FILENAME,
    ADMINS,
    add_message_to_delete,
    get_common_user_keyboard,
    delete_previous_messages,
    log_message
)
from pathlib import Path
from dotenv import load_dotenv
from models import User
import traceback
from fsm import *

env_path = Path('..') / '.env'
load_dotenv(dotenv_path=env_path)


def is_subscriber(member_info):
    return member_info.status not in ['left', 'kicked']


@router.message(CommandStart())
async def start_command_handler(message: Message):
    await common_start_logic(message.from_user.id, message.bot)


# @router.callback_query(F.data == 'sub_confirmed')
@router.callback_query(F.data.startswith('sub_confirmed'))
async def subscription_confirmed_handler(query: CallbackQuery):
    _, message_to_delete = query.data.split('|')
    await common_start_logic(query.from_user.id, query.bot, message_to_delete)
    await query.answer()


async def common_start_logic(user_id: int, bot: Bot, delete_message: int = 0):
    if delete_message:
        await bot.delete_message(chat_id=user_id, message_id=delete_message)
    start_kb = get_common_user_keyboard()
    async with session_factory() as session:
        result = await session.execute(select(User).filter_by(t_id=user_id))
        user = result.scalars().first()
        if not user:
            new_user = User(
                t_id=user_id,
                username="",
                phone="",
                address=""
            )
            session.add(new_user)
            await session.commit()
            await delete_previous_messages(user_id)
            d = await bot.send_message(
                chat_id=user_id,
                text=f"🎉 Вы первый раз вошли в бот магазина {BOTNAME}, мы вас зарегистрировали.",
                reply_markup=start_kb.as_markup()
            )
        else:
            await delete_previous_messages(user_id)
            d = await bot.send_message(
                chat_id=user_id,
                text=f"🚀 Добро пожаловать в бот магазина {BOTNAME}!",
                reply_markup=start_kb.as_markup()
            )
        await add_message_to_delete(user_id, d.message_id)


@router.message(Command("log"))
async def log_handler(message: Message) -> None:
    try:
        current_file_path = Path(__file__).resolve()
        project_root_path = current_file_path.parent
        log_filename = str(project_root_path / LOG_FILENAME)
        file = FSInputFile(
            path=log_filename)
        await bot.send_document(message.from_user.id, document=file, )
    except Exception as e:
        await bot.send_message(message.from_user.id,
                               text='Не вижу файла логов на сервере.')
        log_message('error',
                    f'Пользователь не найден: {e}',
                    message.from_user.id,
                    traceback.extract_stack()[-1]
                    )


@router.message(Command("xls"))
async def xlsx_handler(message: Message) -> None:
    current_file_path = Path(__file__).resolve()
    project_root_path = current_file_path.parent
    log_filename = str(project_root_path / XLSX_FILENAME)
    file = FSInputFile(
        path=log_filename)
    await bot.send_document(message.from_user.id, document=file, )


@router.message(F.content_type == 'photo')
async def handle_photo(message: types.Message):
    if message.from_user.id in ADMINS:
        file_id = message.photo[-1].file_id
        await message.reply(f"File ID: {file_id}")
    else:
        await message.reply("Извините, вы не администратор.")


def register_handlers(dp):
    dp.include_router(router)
