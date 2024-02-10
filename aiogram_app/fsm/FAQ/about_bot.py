
from aiogram import F, types
from aiogram.enums import ParseMode

from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup
)
from create_bot import (
    bot,
    router,
    add_message_to_delete,
    log_message,
    delete_previous_messages
)
import traceback


faq_content = {
    'where': ['Где располагается наш магазин?', 'Наш основной офис располагается в Москве, но сеть складов по всей '
                                                'России позволяет нам обеспечивать лучшее время доставки для наших '
                                                'клиентов.'],
    'guarantee': [
        'Какая гарантия, что мы доставим товар?', 'Мы являемся компанией с 10 летним опытом розничной торговли и '
                                                  'специализируемся на сложном кейтеринге. Этот магазиин '
                                                  'специализируется на товарах для чайной церемонии. Кроме того при '
                                                  'оставлении заказа мы выдаем фискальный документ от имени юрлица '
                                                  'официально и открыто действующего на территории России.'],
    'discount': [
        'Есть ли в магазине скидки?', 'Да, у нас есть гибкая система скидок и подарков, которая зависитне только от '
                                      'размера покупки но и от длительности  сотрудничества с клиентом, а также от '
                                      'активности наших клиентов на мероприятиях компании'],
}


def get_faq_message_and_keyboard(parameter=None):
    faq_keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    if parameter:
        for k, v in faq_content.items():
            if k != parameter:
                faq_keyboard.inline_keyboard.append([InlineKeyboardButton(
                    text=v[0],
                    callback_data=f"FAQ|{k}"
                )])
        faq_message = f'<b>{faq_content[parameter][0]}</b>\n\n{faq_content[parameter][1]}'
    else:
        for k, v in faq_content.items():
            faq_keyboard.inline_keyboard.append([InlineKeyboardButton(
                text=v[0],
                callback_data=f"FAQ|{k}"
            )])
        faq_message = ('Мы всегда рады помочь каждому клиенту с любым вопросом, будто он часть нашей собственной '
                       'команды. Наше гостеприимство и теплота - это то, что делает наше обслуживание особенным. Если '
                       'ниже отсутствует интересующий Вас вопрос, нажмите "Задать другой вопрос" чтобы оставить прямое '
                       'сообщение для наших модераторов. Мы рассматриваем все пожелания и советы наших клиентов.')
    return faq_keyboard, faq_message


@router.callback_query(F.data.startswith('FAQ'))
async def process_pagination_button(callback_query: types.CallbackQuery):
    _, parameter = callback_query.data.split('|')
    await delete_previous_messages(callback_query.from_user.id)
    await callback_query.answer()
    try:
        faq_keyboard, faq_message = get_faq_message_and_keyboard(parameter)
        faq_keyboard.inline_keyboard.append([InlineKeyboardButton(
                text='Задать другой вопрос',
                callback_data=f"leave_message_to_admin"
            )])

        d = await bot.send_message(
            chat_id=callback_query.from_user.id,
            text=faq_message,
            parse_mode=ParseMode.HTML,
            reply_markup=faq_keyboard
        )
        await add_message_to_delete(callback_query.from_user.id, d.message_id)
    except Exception as e:
        log_message('error',
                    f'Ошибка показа справки о боте при выбранном параметре {parameter}: {e}',
                    callback_query.from_user.id,
                    traceback.extract_stack()[-1])
