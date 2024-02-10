from aiogram import F, types
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from create_bot import (
    bot,
    router,
    add_message_to_delete,
    log_message,
    delete_previous_messages,
    ADMINS,
    get_common_user_keyboard
)
import traceback


class ChatSessionAdmin(StatesGroup):
    message_to_admin = State()


@router.callback_query(F.data == 'leave_message_to_admin')
async def leave_direct_question_to_admin(callback_query: types.CallbackQuery, state: FSMContext):
    await delete_previous_messages(callback_query.from_user.id)
    await callback_query.answer()
    await state.set_state(ChatSessionAdmin.message_to_admin)
    d = await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=f'Пожалуйста введите свой вопрос в чат после получения этого сообщения. Наши модераторы рассмотрят '
             f'Ваше обращение и мы свяжемся с Вами либо в личных сообщениях в телеграмме, либо отправим Вам сообщение '
             f'с ответом прямо в этом боте.',
        parse_mode=ParseMode.HTML,
    )
    await add_message_to_delete(callback_query.from_user.id, d.message_id)


@router.message(ChatSessionAdmin.message_to_admin)
async def apply_direct_question_to_admin(message: types.Message):
    try:
        await delete_previous_messages(message.from_user.id)
        content_type = 'text'
        message_content = ''
        if message.text:
            message_content = message.text
            content_type = "text"

        elif message.document:
            message_content = message.document.file_id
            content_type = "document"
        header = f'Пришла обратная связь от пользователя: {message.from_user.id}\n\n'
        for admin in ADMINS:
            try:
                if content_type == "text":
                    await bot.send_message(admin, header + message.text)
                elif content_type == "document":
                    await bot.send_document(admin,
                                            message_content,
                                            caption=header + message.text)
            except Exception as e:
                log_message('error',
                            f'Ошибка отправки сообщения администратора в диалог: {e}',
                            message.from_user.id,
                            traceback.extract_stack()[-1])
        default_keyboard = get_common_user_keyboard()
        d = await bot.send_message(
            chat_id=message.from_user.id,
            text=f'Спасибо за Ваше обращение. Мы рассмотрим его и свяжемся с Вами в этом боте или в личных сообщениях.',
            parse_mode=ParseMode.HTML,
            reply_markup=default_keyboard.as_markup()
        )
        await add_message_to_delete(message.from_user.id, d.message_id)
    except Exception as e:
        log_message('error',
                    f'Ошибка отправки сообщения администратора в диалог: {e}',
                    message.from_user.id,
                    traceback.extract_stack()[-1])
