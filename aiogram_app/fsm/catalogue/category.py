from aiogram import F, types, html
from aiogram.enums import ParseMode
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from create_bot import (
    bot,
    router,
    add_message_to_delete,
    log_message,
    delete_previous_messages
)
from database import session_factory
import traceback
from sqlalchemy import select
from models import Category
import html


async def get_category_keyboard(category_index):
    async with session_factory() as session:
        result = await session.execute(select(Category).order_by(Category.category_id))
        categories = result.scalars().all()

    if not categories:
        return None, None

    category = categories[category_index % len(categories)]
    prev_button = InlineKeyboardButton(
        text="<< предыдущая категория <<",
        callback_data=f"cat_prev|{category_index}"
    )
    category_button = InlineKeyboardButton(
        text=category.category_name,
        callback_data=f"choose_subcategory|{category_index}"
    )
    next_button = InlineKeyboardButton(
        text=">> следующая категория >>",
        callback_data=f"cat_next|{category_index}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [category_button],
        [prev_button, next_button]
    ])
    return categories, keyboard, category


@router.callback_query(lambda c: c.data.startswith('cat_prev') or c.data.startswith('cat_next'))
async def process_pagination_button(callback_query: types.CallbackQuery):
    try:
        data_parts = callback_query.data.split('|')
        if len(data_parts) < 2:
            await callback_query.answer("Некорректные данные кнопки.")
            return

        async with session_factory() as session:
            result = await session.execute(select(Category).order_by(Category.category_id))
            categories = result.scalars().all()

        direction = data_parts[0]
        category_index = int(data_parts[1])
        category_index = (category_index - 1) % len(categories) if direction == "cat_prev" \
            else (category_index + 1) % len(categories)

        categories, keyboard, category = await get_category_keyboard(category_index)
        category_name_escaped = html.escape(category.category_name)
        await bot.edit_message_text(
            message_id=callback_query.message.message_id,
            chat_id=callback_query.from_user.id,
            text=f'Пожалуйста выберите интересующую Вас категорию товаров, перемещаясь кнопками предыдущая / '
                 f'следующая категория.\n\nДля выбора текущей категории нажмите кнопку <b>{category_name_escaped}</b>',
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard)
    except Exception as e:
        log_message('error',
                    f'Ошибка пагинации: {e}',
                    callback_query.from_user.id,
                    traceback.extract_stack()[-1])


@router.callback_query(F.data == 'choose_category')
async def check_category(callback_query: CallbackQuery) -> None:
    await callback_query.answer()
    try:
        await delete_previous_messages(callback_query.from_user.id)
        categories, keyboard, category = await get_category_keyboard(0)
        category_name_escaped = html.escape(category.category_name)

        categories_listing = ''.join(f'\t{num + 1}) {cat.category_name}\n' for num, cat in enumerate(categories))

        d = await bot.send_message(
            chat_id=callback_query.from_user.id,
            text=f'В нашем магазине представлены следующие категории товаров:\n{categories_listing}',
            parse_mode=ParseMode.HTML,
        )
        await add_message_to_delete(callback_query.from_user.id, d.message_id)

        d = await bot.send_message(
            chat_id=callback_query.from_user.id,
            text=f'Пожалуйста выберите интересующую Вас категорию товаров, перемещаясь кнопками предыдущая / '
                 f'следующая категория.\n\nДля выбора текущей категории нажмите кнопку <b>{category_name_escaped}</b>',
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        await add_message_to_delete(callback_query.from_user.id, d.message_id)
    except Exception as e:
        log_message('error',
                    f'Ошибка показа категорий товаров: {e}',
                    callback_query.from_user.id,
                    traceback.extract_stack()[-1])
