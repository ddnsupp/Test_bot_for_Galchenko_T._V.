from typing import Optional, Any, Dict, Union

from aiogram import F
from aiogram.enums import ParseMode
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, KeyboardBuilder
from sqlalchemy.orm import selectinload, joinedload

from create_bot import (
    bot,
    router,
    add_message_to_delete,
    log_message,
    delete_previous_messages,
    get_state_cancel_keyboard,
    get_common_user_keyboard,
    UKASSA_TOKEN,
)
from data_validation import validate_cyrillic_words, validate_phone_number, serialize_phone
import traceback
from aiogram import types


cancel_kb = get_state_cancel_keyboard('request')


class Order(StatesGroup):
    telegram_id = State()
    name = State()
    phone = State()
    address = State()


@router.callback_query(F.data == 'proceeding_order')
async def require_name(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_telegram_id = callback_query.from_user.id
        await delete_previous_messages(user_telegram_id)
        await callback_query.answer()
        await state.clear()
        r = await callback_query.message.answer(
            text='Пожалуйста, укажите как к вам можно обращаться (Фамилия, Имя, Отчество / Фамилия, Имя) используя '
                 'кириллицу. Это необходимо для улучшения работы службы доставки',
            reply_markup=cancel_kb.as_markup())
        await add_message_to_delete(callback_query.from_user.id, r.message_id)
        await state.set_state(Order.name)
    except Exception as e:
        log_message('error',
                    f'Ошибка при проверке существования корзины : {e}',
                    callback_query.from_user.id,
                    traceback.extract_stack()[-1])


@router.callback_query(lambda c: c.data == "cancel_state_request")
async def cancel_handler(event: Union[Message, CallbackQuery], state: FSMContext) -> None:
    if isinstance(event, CallbackQuery):
        message = event.message
        user_id = event.from_user.id
        await event.answer()
    else:
        message = event
        user_id = message.from_user.id

    try:
        await delete_previous_messages(event.from_user.id)
        current_state = await state.get_state()
        if current_state is None:
            return
        kb = get_common_user_keyboard()
        await state.clear()
        d = await bot.send_message(
            user_id,
            "Ввод данных прекращен. Введенные данные не были сохранены и (или) обработаны.",
            reply_markup=kb.as_markup(),
        )
        await add_message_to_delete(user_id, d.message_id)

    except Exception as e:
        log_message('error',
                    f'Ошибка: {e}',
                    message.from_user.id,
                    traceback.extract_stack()[-1])


@router.message(Order.name)
async def process_name(message: Message, state: FSMContext) -> None:
    try:
        await delete_previous_messages(message.from_user.id)
        if validate_cyrillic_words(message.text):
            await state.update_data(telegram_id=message.from_user.id)
            await state.update_data(name=message.text)
            d = await message.answer(
                'Укажите ваш телефон. Допустимо использование цифр, пробелов и знаков "+", "-".',
                reply_markup=cancel_kb.as_markup())
            await state.set_state(Order.phone)
        else:
            d = await message.answer("Имя может состоять из 1-3 слов на русском языке без дополнительных символов. "
                                     "Пожалуйста повторите ввод корректно.", reply_markup=cancel_kb.as_markup())
            await state.set_state(Order.name)
        await add_message_to_delete(message.from_user.id, d.message_id)

    except Exception as e:
        log_message('error',
                    f'Ошибка: {e}',
                    message.from_user.id,
                    traceback.extract_stack()[-1])



@router.message(Order.phone)
async def process_phone(message: Message, state: FSMContext) -> None:
    try:
        await delete_previous_messages(message.from_user.id)
        if validate_phone_number(message.text):
            await state.update_data(phone=serialize_phone(message.text))
            d = await message.answer(
                text="Введите ваш почтовый адрес для расчета стоимости доставки и прогноза ее сроков",
                reply_markup=cancel_kb.as_markup()
            )
            await state.set_state(Order.address)
        else:
            d = await message.answer(
                "Номер телефона может состоять только из цифр и математических символов. Пожалуйста повторите ввод"
                , reply_markup=cancel_kb.as_markup())
            await state.set_state(Order.phone)
        await add_message_to_delete(message.from_user.id, d.message_id)

    except Exception as e:
        log_message('error',
                    f'Ошибка: {e}',
                    message.from_user.id,
                    traceback.extract_stack()[-1])


@router.message(Order.address)
async def process_address(message: Message, state: FSMContext) -> None:
    try:
        await delete_previous_messages(message.from_user.id)
        await state.update_data(address=message.text)
        user_data = await state.get_data()
        confirm_request_data_kb_builder = KeyboardBuilder(button_type=InlineKeyboardButton)
        confirm_request_data_keyboard = {
            'Завершить оформление заказа': 'issue_payment_invoice',
            'Прекратить оформление заказа': 'cancel_state_request'
        }
        for k, v in confirm_request_data_keyboard.items():
            confirm_request_data_kb_builder.row(types.InlineKeyboardButton(text=k, callback_data=v))
        r = await message.answer(f'<b>{user_data["name"]}</b>, вы ввели корректный номер телефона: '
                                 f'<b>{user_data["phone"]}</b> и адрес для доставки: {user_data["address"]}.\n\n '
                                 f'Пожалуйста проверьте данные и нажмите на кнопку "Завершить оформление заказа".',
                                 reply_markup=confirm_request_data_kb_builder.as_markup())
        await add_message_to_delete(message.from_user.id, r.message_id)

    except Exception as e:
        log_message('error',
                    f'Ошибка: {e}',
                    message.from_user.id,
                    traceback.extract_stack()[-1])


