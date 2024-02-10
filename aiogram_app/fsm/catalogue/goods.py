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
    InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto

)
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import KeyboardBuilder, InlineKeyboardBuilder
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import joinedload

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
from models import Category, Subcategory, Product, Cart, CartProduct, User
import html


@router.callback_query(lambda c: c.data.startswith('choose_item'))
async def show_goods(callback_query: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback_query.answer()
        await delete_previous_messages(callback_query.from_user.id)
        _, subcategory_id = callback_query.data.split('|')
        subcategory_id = int(subcategory_id)

        async with session_factory() as session:
            result = await session.execute(
                select(Product).distinct(Product.product_id)
                .options(joinedload(Product.photos))
                .where(Product.subcategory_id == subcategory_id)
            )
            products = result.scalars().unique().all()

        for product in products:
            goods_photos = [InputMediaPhoto(media=photo.file_id) for photo in product.photos]

            if goods_photos:
                media_messages = await bot.send_media_group(
                    chat_id=callback_query.from_user.id,
                    media=goods_photos
                )
                for media_message in media_messages:
                    await add_message_to_delete(callback_query.from_user.id, media_message.message_id)
            quantity = 1
            price_summ = quantity * int(product.price) / 100

            decrease_button = InlineKeyboardButton(
                text="Уменьшить количество",
                callback_data=f"decrease|{product.product_id}"
            )
            increase_button = InlineKeyboardButton(
                text="Увеличить количество",
                callback_data=f"increase|{product.product_id}"
            )
            cart_button_continue = InlineKeyboardButton(
                text="Добавить в корзину и продолжить покупки",
                callback_data=f"add_to_cart_continue|{product.product_id}"
            )
            cart_button_finish = InlineKeyboardButton(
                text="Добавить в корзину и перейти к оформлению",
                callback_data=f"add_to_cart_finish|{product.product_id}"
            )
            product_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [cart_button_continue],
                    [cart_button_finish],
                    [decrease_button, increase_button]
                ])

            description_message = (f'<b>{product.product_name}</b>\n\n'
                                   f'{product.description}\n\n'
                                   f'Выбрано: {quantity} единиц из {product.quantity} доступных.\n\n'
                                   f'Цена за выбранное количество: <b>{price_summ}</b> руб.')
            d = await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=description_message,
                parse_mode=ParseMode.HTML,
                reply_markup=product_keyboard
            )
            await add_message_to_delete(callback_query.from_user.id, d.message_id)

        go_to_cart = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="Перейти к оформлению без добавления новых товаров",
                    callback_data=f"check_cart"
                )]
            ])

        d = await bot.send_message(
            callback_query.from_user.id,
            "Хотите перейти в корзину без добавления новых товаров и оформить заказ?",
            reply_markup=go_to_cart
        )
        await add_message_to_delete(callback_query.from_user.id, d.message_id)

    except Exception as e:
        log_message('error',
                    f'Ошибка показа товаров: {e}',
                    callback_query.from_user.id,
                    traceback.extract_stack()[-1]
                    )


@router.callback_query(lambda c: c.data.startswith('increase') or c.data.startswith('decrease'))
async def change_quantity(callback_query: CallbackQuery, state: FSMContext):
    action, product_id = callback_query.data.split('|')
    product_id = int(product_id)
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id

    async with session_factory() as session:
        product = await session.get(Product, product_id)
        if not product:
            await callback_query.answer('Продукт не найден.', show_alert=True)
            return

        cart = await state.get_data()
        quantity_key = f"product_{product_id}_quantity"
        quantity = cart.get(quantity_key, 1)

        if action == 'increase':
            quantity += 1
        elif action == 'decrease' and quantity > 1:
            quantity -= 1

        await state.update_data({quantity_key: quantity})

        price_summ = quantity * int(product.price) / 100

        description_message = (f'<b>{product.product_name}</b>\n'
                               f'{product.description}\n\n'
                               f'Выбрано: {quantity} единиц из {product.quantity} доступных.\n\n'
                               f'Цена за выбранное количество: <b>{price_summ}</b> руб.')

        decrease_button = InlineKeyboardButton(
            text="Уменьшить количество",
            callback_data=f"decrease|{product_id}"
        )
        increase_button = InlineKeyboardButton(
            text="Увеличить количество",
            callback_data=f"increase|{product_id}"
        )
        cart_button_continue = InlineKeyboardButton(
            text="Добавить в корзину и продолжить покупки",
            callback_data=f"add_to_cart_continue|{product_id}"
        )
        cart_button_finish = InlineKeyboardButton(
            text="Добавить в корзину и перейти к оформлению",
            callback_data=f"add_to_cart_finish|{product_id}"
        )
        product_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [cart_button_continue],
                [cart_button_finish],
                [decrease_button, increase_button]
            ])

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=description_message,
            parse_mode=ParseMode.HTML,
            reply_markup=product_keyboard
        )
        await callback_query.answer('Количество обновлено.')


@router.callback_query(lambda c: c.data.startswith('add_to_cart_continue') or c.data.startswith('add_to_cart_finish'))
async def add_to_cart(callback_query: CallbackQuery, state: FSMContext):
    action, product_id = callback_query.data.split('|')
    product_id = int(product_id)
    chat_id = callback_query.from_user.id

    state_data = await state.get_data()
    quantity_key = f"product_{product_id}_quantity"
    quantity = state_data.get(quantity_key, 1)

    async with session_factory() as session:
        # Проверяем, есть ли у пользователя корзина
        user_query = select(User).where(User.t_id == chat_id)
        try:
            user = await session.execute(user_query)
            user = user.scalar_one()
        except NoResultFound as e:
            log_message('error',
                        f'Пользователь не найден: {e}',
                        callback_query.from_user.id,
                        traceback.extract_stack()[-1]
                        )
            return

        cart_query = select(Cart).where(Cart.user_id == user.user_id)
        try:
            cart = await session.execute(cart_query)
            cart = cart.scalar_one()
        except NoResultFound:
            cart = Cart(user_id=user.user_id)
            session.add(cart)
            await session.commit()

        cart_product_query = select(CartProduct).where(CartProduct.cart_id == cart.cart_id,
                                                       CartProduct.product_id == product_id)
        try:
            cart_product = await session.execute(cart_product_query)
            cart_product = cart_product.scalar_one()
            # Если товар найден, увеличиваем количество
            cart_product.quantity += quantity
        except NoResultFound:
            # Если товар не найден, добавляем новый
            cart_product = CartProduct(cart_id=cart.cart_id, product_id=product_id, quantity=quantity)
            session.add(cart_product)

        await session.commit()

        if action.startswith('add_to_cart_finish'):
            await bot.send_message(chat_id, "Переходим к оформлению заказа...")
        else:
            await callback_query.answer('Товар добавлен в корзину. Продолжайте покупки!', show_alert=True)



