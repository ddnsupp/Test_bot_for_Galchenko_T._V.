from os import getenv
from typing import Any, Dict, Union

from aiogram import Bot, Dispatcher, F, types, Router, html
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup

)
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import KeyboardBuilder, InlineKeyboardBuilder
from create_bot import (
    bot,
    dp,
    router,
    WEBHOOK_PATH,
    WEB_SERVER_HOST,
    WEB_SERVER_PORT,
    BASE_WEBHOOK_URL,
    add_message_to_delete,
    log_message,
    get_common_user_keyboard,
    get_state_cancel_keyboard,
    delete_previous_messages
)
import re
import random
import string
from datetime import datetime
import time
from database import session_factory
import traceback
from sqlalchemy import select
from models import Category, Subcategory
import html



async def get_subcategory_keyboard(category_id, subcategory_index=0):
    async with session_factory() as session:
        result = await session.execute(select(Subcategory).where(Subcategory.category_id == category_id).order_by(Subcategory.subcategory_id))
        subcategories = result.scalars().all()
    log_message('info',
                f'{category_id=} {subcategory_index=}',
                0,
                traceback.extract_stack()[-1])
    if not subcategories:
        return None, None, None

    if subcategory_index < 0 or subcategory_index >= len(subcategories):
        subcategory_index = 0

    if subcategory_index == 0:
        subcategory = subcategories[0]
    else:
        subcategory = subcategories[subcategory_index]

    prev_index = (subcategory_index - 1) % len(subcategories)
    next_index = (subcategory_index + 1) % len(subcategories)

    prev_button = InlineKeyboardButton(
        text="<< предыдущая подкатегория <<",
        callback_data=f"subcat_prev|{category_id}|{prev_index}"
    )
    subcategory_button = InlineKeyboardButton(
        text=subcategory.subcategory_name,
        callback_data=f"choose_item|{subcategory.subcategory_id}"
    )
    next_button = InlineKeyboardButton(
        text=">> следующая подкатегория >>",
        callback_data=f"subcat_next|{category_id}|{next_index}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [subcategory_button],
        [prev_button, next_button]
    ])

    return subcategories, keyboard, subcategory


@router.callback_query(lambda c: c.data.startswith('subcat_prev') or c.data.startswith('subcat_next'))
async def process_subcategory_pagination_button(callback_query: types.CallbackQuery):
    try:
        data_parts = callback_query.data.split('|')
        if len(data_parts) < 3:
            log_message('error',
                        f'Некорректные данные кнопки: {data_parts}',
                        callback_query.from_user.id,
                        traceback.extract_stack()[-1])
            return

        async with session_factory() as session:
            result = await session.execute(select(Category).order_by(Category.category_id))
            categories = result.scalars().all()

        direction, category_id, subcategory_id = data_parts
        category_id = int(category_id)
        subcategory_id = int(subcategory_id)
        subcategories, keyboard, subcategory = await get_subcategory_keyboard(
            category_id=category_id,
            subcategory_index=subcategory_id
        )
        if not subcategories and not keyboard and not subcategory:
            log_message('error',
                        f'Категория отсутствует для педеданных: {category_id=} и {subcategory_id=}',
                        callback_query.from_user.id,
                        traceback.extract_stack()[-1])

        subcategory_index = (subcategory_id - 1) % len(subcategories) if direction == "subcat_prev" else (subcategory_id + 1) % len(subcategories)


        subcategory_name_escaped = html.escape(subcategory.subcategory_name)
        await bot.edit_message_text(
            message_id=callback_query.message.message_id,
            chat_id=callback_query.from_user.id,
            text=f'Пожалуйста выберите интересующую Вас подкатегорию товаров, перемещаясь кнопками предыдущая / '
                 f'следующая подкатегория.'
                 f'\n\nДля выбора текущей подкатегории нажмите кнопку <b>{subcategory_name_escaped}</b>',
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard)
    except Exception as e:
        log_message('error',
                    f'Ошибка пагинации по подкатегориям: {e}',
                    callback_query.from_user.id,
                    traceback.extract_stack()[-1])


@router.callback_query(lambda c: c.data.startswith('choose_subcategory'))
async def check_subcategories(callback_query: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback_query.answer()
        await delete_previous_messages(callback_query.from_user.id)
        _, category_id = callback_query.data.split('|')
        category_id = int(category_id)
        async with session_factory() as session:
            result = await session.execute(select(Category).filter_by(category_id=category_id))
            category = result.scalars().first()

        await delete_previous_messages(callback_query.from_user.id)
        subcategories, keyboard, subcategory = await get_subcategory_keyboard(
            category_id=category_id,
            subcategory_index=0
        )
        if subcategory is None:
            # Обработайте случай, когда подкатегории отсутствуют
            # Например, отправьте сообщение пользователю об отсутствии подкатегорий
            await callback_query.answer(f"В этой категории нет подкатегорий.\n{subcategories, keyboard, subcategory}\n{category_id}")
            return


        category_name_escaped = html.escape(subcategory.subcategory_name)

        subcategories_listing = ''.join(f'\t{num + 1}) {subcat.subcategory_name}\n' for num, subcat in enumerate(subcategories))


        d = await bot.send_message(
            chat_id=callback_query.from_user.id,
            text=f'Вы выбрали категорию товаров: <b>{category.category_name}</b>, внутри нее доступны подкатегории:'
                 f'\n{subcategories_listing}',
            parse_mode=ParseMode.HTML,
        )
        await add_message_to_delete(callback_query.from_user.id, d.message_id)

        d = await bot.send_message(
            chat_id=callback_query.from_user.id,
            text=f'Пожалуйста выберите интересующую Вас подкатегорию товаров, перемещаясь кнопками предыдущая / '
                 f'следующая подкатегория.'
                 f'\n\nДля выбора текущей подкатегории нажмите кнопку <b>{category_name_escaped}</b>',
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        await add_message_to_delete(callback_query.from_user.id, d.message_id)
    except Exception as e:
        log_message('error',
                    f'Ошибка показа подкатегорий товаров: {e}',
                    callback_query.from_user.id,
                    traceback.extract_stack()[-1])



