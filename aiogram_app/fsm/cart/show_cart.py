from typing import Optional
from aiogram import F
from aiogram.enums import ParseMode
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.future import select
from create_bot import (
    bot,
    router,
    add_message_to_delete,
    log_message,
    delete_previous_messages
)
from database import session_factory
import traceback
from models import User, Cart, CartProduct, Product
from aiogram import types


class CartCallbackFactory(CallbackData, prefix="cart"):
    action: str
    product_id: int
    value: Optional[int] = None


def get_cart_keyboard_fab(product_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="-1 ед.", callback_data=CartCallbackFactory(action="change", product_id=product_id, value=-1)
    )
    builder.button(
        text="Удалить товар", callback_data=CartCallbackFactory(action="delete", product_id=product_id)
    )
    builder.button(
        text="+1 ед", callback_data=CartCallbackFactory(action="change", product_id=product_id, value=1)
    )
    builder.adjust(3)
    return builder.as_markup()


@router.callback_query(CartCallbackFactory.filter())
async def handle_cart_action(callback_query: CallbackQuery, callback_data: CartCallbackFactory, state: FSMContext):
    try:
        action = callback_data.action
        product_id = int(callback_data.product_id)
        value = int(callback_data.value) if callback_data.value is not None else 0

        chat_id = callback_query.from_user.id
        async with session_factory() as session:
            cart = await ensure_user_cart_exists(session, chat_id)
            if not cart:
                await callback_query.answer("Ошибка: Корзина не найдена.", show_alert=True)
                return

            if action == "change":
                success = await change_product_quantity(session, product_id, value, cart.cart_id, chat_id)
            elif action == "delete":
                success = await delete_product_from_cart(session, product_id, cart.cart_id, chat_id)

            if success:
                product_id = int(callback_data.product_id)
                message_id = await get_message_id_for_product(state, product_id)
                if message_id:
                    # await update_cart_message(callback_query.from_user.id, message_id, product_id, session, cart.cart_id)
                    await callback_query.answer("Корзина обновлена.", show_alert=True)
                # message_id = callback_query.message.message_id
                # await update_cart_message(chat_id, message_id, product_id, session_factory)
                # await callback_query.answer("Корзина обновлена.", show_alert=True)
            else:
                await callback_query.answer("Не удалось обновить корзину.", show_alert=True)

    except Exception as e:
        log_message('error',
                    f'Ошибка: {e}',
                    callback_query.from_user.id,
                    traceback.extract_stack()[-1])


async def ensure_user_cart_exists(session, user_telegram_id):
    try:
        user_stmt = select(User).where(User.t_id == user_telegram_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalars().first()

        if user:
            cart_stmt = select(Cart).where(Cart.user_id == user.user_id)
            cart_result = await session.execute(cart_stmt)
            cart = cart_result.scalars().first()

            if not cart:
                new_cart = Cart(user_id=user.user_id)
                session.add(new_cart)
                await session.commit()
                return new_cart
            else:
                return cart
        else:
            return None
    except Exception as e:
        log_message('error',
                    f'Ошибка при проверке существования корзины : {e}',
                    user_telegram_id,
                    traceback.extract_stack()[-1])


async def get_user_cart(user_telegram_id: int):
    try:
        async with session_factory() as session:
            user_result = await session.execute(select(User).filter(User.t_id == user_telegram_id))
            user = user_result.scalars().first()
            if user:
                cart_result = await session.execute(select(Cart).filter(Cart.user_id == user.user_id))
                cart = cart_result.scalars().first()
                if cart:
                    cart_products_result = await session.execute(
                        select(CartProduct, Product)
                        .join(Product, CartProduct.product_id == Product.product_id)
                        .filter(CartProduct.cart_id == cart.cart_id)
                    )
                    cart_products = cart_products_result.all()
                    return cart, cart_products
        return None, None
    except Exception as e:
        log_message('error',
                    f'Ошибка: {e}',
                    user_telegram_id,
                    traceback.extract_stack()[-1])


@router.callback_query(F.data == 'check_cart')
async def show_user_cart(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_telegram_id = callback_query.from_user.id
        await delete_previous_messages(user_telegram_id)
        await callback_query.answer()

        cart, cart_products_info = await get_user_cart(user_telegram_id)
        if not cart_products_info:
            await bot.send_message(user_telegram_id, "Ваша корзина пуста.", parse_mode=ParseMode.HTML)
            return

        pre_message = f"В вашей корзине сейчас находятся следующие товары:"
        d = await bot.send_message(user_telegram_id, pre_message, parse_mode=ParseMode.HTML)
        await add_message_to_delete(callback_query.from_user.id, d.message_id)
        total_sum = 0
        for cart_product, product in cart_products_info:
            item_total = cart_product.quantity * product.price / 100
            total_sum += item_total
            item_text = (f"🛒 <b>{product.product_name}</b> - {cart_product.quantity} шт. "
                         f"по {product.price / 100:.2f} руб. (Подытог: <b>{item_total:.2f} руб.</b>)")

            d = await bot.send_message(chat_id=user_telegram_id,
                                       text=item_text,
                                       reply_markup=get_cart_keyboard_fab(product.product_id),
                                       parse_mode=ParseMode.HTML)
            await add_message_to_delete(callback_query.from_user.id, d.message_id)
            await save_message_id_for_product(state, product.product_id, d.message_id)

        summary_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="Продолжить оформление заказа",
                    callback_data=f"proceeding_order")]
            ])
        summary_message = f"<b>Всего товаров в корзине на {total_sum:.2f} руб.</b>"
        d = await bot.send_message(
            chat_id=user_telegram_id,
            text=summary_message,
            parse_mode=ParseMode.HTML,
            reply_markup=summary_kb
        )
        await add_message_to_delete(callback_query.from_user.id, d.message_id)
    except Exception as e:
        log_message('error',
                    f'Ошибка: {e}',
                    callback_query.from_user.id,
                    traceback.extract_stack()[-1])


async def change_product_quantity(session, product_id: int, value: int, cart_id: int, uid: int):
    try:
        cart_product_result = await session.execute(
            select(CartProduct).filter_by(cart_id=cart_id, product_id=product_id)
        )
        cart_product = cart_product_result.scalars().first()

        if cart_product:
            new_quantity = cart_product.quantity + value
            if new_quantity > 0:
                cart_product.quantity = new_quantity
            else:
                await session.delete(cart_product)
            await session.commit()
            return True
        return False
    except Exception as e:
        log_message('error',
                    f'Ошибка: {e}',
                    0,
                    traceback.extract_stack()[-1])


async def delete_product_from_cart(session, product_id: int, cart_id: int, uid: int):
    try:
        cart_product_result = await session.execute(
            select(CartProduct).filter_by(cart_id=cart_id, product_id=product_id)
        )
        cart_product = cart_product_result.scalars().first()

        if cart_product:
            await session.delete(cart_product)
            await session.commit()
            return True
        return False
    except Exception as e:
        log_message('error',
                    f'Ошибка: {e}',
                    0,
                    traceback.extract_stack()[-1])

async def get_product_info(session, cart_id: int, product_id: int) -> str:
    try:
        cart_product_result = await session.execute(
            select(CartProduct.quantity, Product.product_name, Product.price)
            .join(Product, CartProduct.product_id == Product.product_id)
            .filter(CartProduct.cart_id == cart_id, CartProduct.product_id == product_id)
        )
        cart_product_info = cart_product_result.first()
        if cart_product_info:
            quantity, product_name, price = cart_product_info
            item_total = quantity * price / 100
            return f"🛒 <b>{product_name}</b> - {quantity} шт. по {price / 100:.2f} руб. (Подытог: <b>{item_total:.2f} руб.</b>)"
        else:
            return "Товар не найден в корзине."
    except Exception as e:
        log_message('error',
                    f'Ошибка: {e}',
                    0,
                    traceback.extract_stack()[-1])


async def update_cart_message(user_telegram_id: int, message_id: int, product_id: int, session, cart_id):
    try:
        product_info = await get_product_info(session, cart_id, product_id)
        await bot.edit_message_text(chat_id=user_telegram_id,
                                    message_id=message_id,
                                    text=product_info,
                                    parse_mode=ParseMode.HTML
                                    )
    except Exception as e:
        log_message('error',
                    f'Ошибка: {e}',
                    user_telegram_id,
                    traceback.extract_stack()[-1])


async def save_message_id_for_product(state: FSMContext, product_id: int, message_id: int):
    try:
        user_data = await state.get_data()
        cart_messages = user_data.get("cart_messages", {})
        cart_messages[product_id] = message_id
        await state.update_data(cart_messages=cart_messages)
    except Exception as e:
        log_message('error',
                    f'Ошибка: {e}',
                    0,
                    traceback.extract_stack()[-1])


async def get_message_id_for_product(state: FSMContext, product_id: int) -> Optional[int]:
    try:
        user_data = await state.get_data()
        cart_messages = user_data.get("cart_messages", {})
        return cart_messages.get(product_id)
    except Exception as e:
        log_message('error',
                    f'Ошибка: {e}',
                    0,
                    traceback.extract_stack()[-1])