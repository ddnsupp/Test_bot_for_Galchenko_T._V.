from aiogram import types
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import KeyboardBuilder

from create_bot import (
    bot,
    add_message_to_delete,
    convert_epoch_to_moscow
)
from database import connect_to_postgres
from create_bot import log_message
import traceback
from models import User

db = connect_to_postgres()


async def delete_marked_messages(user_tid):
    engine, session_maker = await connect_to_postgres()
    async with session_maker() as session:
        try:
            # Находим пользователя в базе данных по его телеграмм айди
            user = session.query(User).filter_by(t_id=user_tid).first()

            if user and user.messages_to_delete:  # Проверяем, что пользователь существует и имеет messages_to_delete
                messages_to_delete = user.messages_to_delete
                for message_id in messages_to_delete:
                    try:
                        # Удаляем сообщение по его идентификатору
                        await bot.delete_message(chat_id=user_tid, message_id=message_id)
                    except Exception as e:
                        log_message('error', f'Ошибка при удалении сообщения: {e}', user_tid,
                                    traceback.extract_stack()[-1])

                # После удаления всех сообщений очищаем массив messages_to_delete у пользователя
                user.messages_to_delete = []
                session.commit()

        except Exception as e:
            # Обработка ошибок
            log_message('error', f'Ошибка при выполнении SQL-запросов: {e}', user_tid, traceback.extract_stack()[-1])
        finally:
            await engine.dispose()


async def display_main_keyboard(user_tid):
    engine, session_maker = await connect_to_postgres()
    async with session_maker() as session:
        try:
            user = session.query(User).filter_by(telegram_id=user_tid).first()

            if user:
                start_keyboard_builder = KeyboardBuilder(button_type=InlineKeyboardButton)
                start_keyboard = {}

                if user.user_type == "Customer":
                    if user.active_order_id:
                        basic_keyboard = {
                            'Вернуться в диалог по текущему заказу': 'user_return_to_chat',
                        }
                    else:
                        basic_keyboard = {
                            'Оставить заказ': 'make_new_request',
                        }
                    add_keyboard = {
                        'Получить журнал логов': 'admin_get_log',
                        'Получить таблицу заказов': 'admin_get_xls',
                    }
                    start_keyboard = {**basic_keyboard, **add_keyboard}

                elif user.user_type == "Admin":
                    start_keyboard = {
                        'Посмотреть новые заказы': 'admin_check_available_orders|new',
                    }

                for k, v in start_keyboard.items():
                    start_keyboard_builder.row(types.InlineKeyboardButton(text=k, callback_data=v))

                return start_keyboard_builder

        except Exception as e:
            log_message('error', f'Ошибка при выполнении SQL-запросов: {e}', user_tid, traceback.extract_stack()[-1])
        finally:
            await engine.dispose()
