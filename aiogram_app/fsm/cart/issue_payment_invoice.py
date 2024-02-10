from aiogram import F, types
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import PreCheckoutQuery, Message
from create_bot import (
    bot,
    router,
    add_message_to_delete,
    log_message,
    delete_previous_messages,
    ADMINS,
    get_common_user_keyboard,
    UKASSA_TOKEN
)
import traceback
from aiogram.types import LabeledPrice
from fsm.cart.show_cart import get_user_cart

@router.callback_query(F.data == 'issue_payment_invoice')
async def issue_payment_invoice(callback_query: types.CallbackQuery, state: FSMContext):
    await delete_previous_messages(callback_query.from_user.id)
    data = await state.get_data()
    user_telegram_id = data.get('telegram_id')
    cart, cart_products_info = await get_user_cart(user_telegram_id)
    if cart_products_info:
        name = data.get('name')
        phone = data.get('phone')
        address = data.get('address')
        # d = await callback_query.message.answer(
        #     text=f'{telegram_id=} {name=} {phone=} {address=}')
        d = await callback_query.message.answer(
            text='Для оплаты можете использовать реквизиты тестовой карты:\n\n'
                 '<pre>1111 1111 1111 1026</pre><pre>12/22</pre><pre>000</pre>',
            parse_mode=ParseMode.HTML
        )
        prices = []
        for cart_product, product in cart_products_info:
            item_total = cart_product.quantity * product.price  # цена в копейках
            prices.append(LabeledPrice(label=f"{product.product_name} x {cart_product.quantity}", amount=item_total))

        # Создание инвойса с перечислением всех товаров
        await bot.send_invoice(
            chat_id=user_telegram_id,
            title='Оплата заказа',
            description='Оплата товаров чайного магазина',
            payload='Уникальный_идентификатор_платежа',
            provider_token=UKASSA_TOKEN,
            currency='RUB',
            prices=prices,
            start_parameter='payment-teashop',
            request_timeout=30,
        )

        # await add_message_to_delete(callback_query.from_user.id, d.message_id)
        # prices = [LabeledPrice(label='Тестовый платеж', amount=10000)]
        # await bot.send_invoice(
        #     chat_id=callback_query.from_user.id,
        #     title='Название платежа',
        #     description='Описание платежа',
        #     payload='Уникальный_идентификатор_платежа',
        #     provider_token=UKASSA_TOKEN,
        #     currency='RUB',
        #     prices=prices,
        #     start_parameter='payment-example',
        #     request_timeout=30,
        # )


async def payment_handler(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


async def payment_confirm(message: Message):
    log_message('error',
                f'{message}',
                0,
                traceback.extract_stack()[-1])
    await message.answer("Спасибо за вашу оплату!")
