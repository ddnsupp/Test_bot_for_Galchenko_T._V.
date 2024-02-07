from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import KeyboardBuilder
from aiohttp import web
from create_bot import (
    bot,
    dp,
    router,
    WEBHOOK_PATH,
    WEB_SERVER_HOST,
    WEB_SERVER_PORT,
    BASE_WEBHOOK_URL,
    TINKOFF_PAYMENT_URI,
    add_message_to_delete,
    log_message
)
import traceback
from database import session_factory
import re
import random
import string
from datetime import datetime
import time


# async def handle_payment_webhook(request: web.Request) -> web.Response:
#     payment_data = await request.json()
#     admins = db['users'].find({"user_type": "Admin"})
#     order = db["orders"].find_one({"receipt_data.0.PaymentId": str(payment_data['PaymentId'])})
#     chat_id = order.get("chat_id")
#     chat = db["chat_sessions"].find_one({"chat_id": chat_id})
#     participants = [participant.get('telegram_id') for participant in chat.get('participants', [])]
#     customer_tid = order.get("customer_id")
#
#     if payment_data['Status'] == 'CONFIRMED':
#         for user_id in participants:
#             confirm_message = ''
#             confirm_kb_builder = KeyboardBuilder(button_type=InlineKeyboardButton)
#             confirm_kb = {}
#             allows = []
#
#             user = db['users'].find_one({"telegram_id": user_id})
#             user_role = user.get('user_type')
#
#             if user_role == 'Admin':
#                 confirm_message = 'Платеж по текущему заказу прошел успешно'
#                 confirm_kb = {
#                     "Уточнить вопросы с заказчиком": f"ask_consumer|{chat_id}",
#                     # "Обратиться ко всем участникам": f"ask_participants|{chat_id}",
#                     "Покинуть текущий диалог": f"leave_current_chat|{chat_id}",
#                 }
#                 allows = ["Admin"]
#
#             elif user_role == 'Executor':
#                 confirm_message = (
#                     'Платеж по заказу прошел успешно, вы можете приступать к его выполнению.'
#                 )
#                 confirm_kb = {
#                     'Свернуть диалог': f'leave_current_chat|{chat_id}',
#                 }
#                 allows = ["Executor"]
#
#             elif user_role == 'Customer':
#                 confirm_message = (
#                     'Ваш платеж прошел успешно, мы уже уведомили исполнителя о необходимости приступить к выполнению '
#                     'задания.\n\n<i>Как только задание будет выполнено, пожалуйста нажмите кнопку "принять выполнение"'
#                     'ниже.\n\nФункция "Свернуть диалог" позволяет вернуться к основному функционалу бота не '
#                     'прерывая выполнение текущего задания.</i>'
#                 )
#                 confirm_kb = {'Принять выполнение': f'confirm_execution|{chat_id}',
#                               # 'Связаться с администратором': 'kb2',
#                               'Свернуть диалог': f'leave_current_chat|{chat_id}'}
#                 allows = ["Customer"]
#
#             for k, v in confirm_kb.items():
#                 confirm_kb_builder.row(types.InlineKeyboardButton(text=k, callback_data=v))
#             r = await bot.send_message(chat_id=user_id,
#                                        text='<b>[Система]</b>\n' + confirm_message,
#                                        reply_markup=confirm_kb_builder.as_markup()
#                                        )
#             await add_message_to_delete(user_id, r.message_id)
#
#             new_message_to_save = {
#                 "permissions": allows,
#                 "timestamp": int(time.mktime(datetime.now().timetuple())),
#                 "message_from_id": 0,
#                 "message_from_username": '',
#                 "sender_position": 'Система',
#                 "message_content": confirm_message,
#                 "content_type": "text"
#             }
#
#             db["chat_sessions"].update_one({"chat_id": chat_id}, {"$push": {"messages": new_message_to_save}})
#
#
#     elif payment_data['Status'] == 'REJECTED':
#         try:
#             receipt_data = order.get("receipt_data")
#             details = order.get("details")
#             invoice_data = create_invoice(
#                 amount=receipt_data[0]["price"],
#                 position_title=details[0]["description"],
#                 receipt_id=order['receipt_id'],
#                 phone=receipt_data[0]['phone'],
#                 email=receipt_data[0]['email']
#             )
#             new_payment_link = invoice_data["PaymentURL"]
#             message_if_reject = (
#                 f'К сожалению платеж был отклонен. Мы автоматически выставили новый счет на '
#                 f'оплату услуги: <b><a href="{new_payment_link}">Это ваша новая ссылка на оплату.</a></b>\n\n<i>'
#                 f'Пожалуйста, перед попыткой оплаты, убедитесь, что причина отклонения была устранена.</i>'
#             )
#             db["orders"].update_one(
#                 {"chat_id": chat_id},
#                 {"$set": {"receipt_data.0.PaymentId": invoice_data["PaymentId"],
#                           "receipt_data.0.PaymentURL": invoice_data["PaymentURL"]
#                           }
#                  }
#             )
#             r = await bot.send_message(
#                 customer_tid,
#                 '<b>[Система]</b>\n' + message_if_reject
#             )
#             await add_message_to_delete(customer_tid, r.message_id)
#
#             new_message_to_save = {
#                 "permissions": ["Customer"],
#                 "timestamp": int(time.mktime(datetime.now().timetuple())),
#                 "message_from_id": 0,
#                 "message_from_username": '',
#                 "sender_position": 'Система',
#                 "message_content": message_if_reject,
#                 "content_type": "text"
#             }
#
#             db["chat_sessions"].update_one({"chat_id": chat_id}, {"$push": {"messages": new_message_to_save}})
#
#
#         except Exception as e:
#             log_message('error',
#                         f'Ошибка выставления нового счета: {e}',
#                         customer_tid,
#                         traceback.extract_stack()[-1])
#
#     # elif payment_data['Status'] == 'AUTHORIZED':
#     #     confirm_message = ''
#     #     for user_id in participants:
#     #         user = db['users'].find({"telegram_id": user_id})
#     #         user_role = user.get('user_type')
#     #         if user_role == 'Admin':
#     #             confirm_message = '<b>[Система]</b>\nПлатеж по текущему заказу прошел успешно'
#     #
#     #         elif user_role == 'Executor':
#     #             confirm_message = (
#     #                 '<b>[Система]</b>\nПлатеж по заказу прошел успешно, вы можете преступать к его выполнению.'
#     #             )
#     #
#     #         elif user_role == 'Customer':
#     #             confirm_message = (
#     #                 '<b>[Система]</b>\nВаш платеж прошел успешно, мы уже уведомили исполнителя о необходимости '
#     #                 'приступить к выполнению задания.'
#     #             )
#     #
#     #         r = await bot.send_message(user_id, confirm_message)
#     #         await add_message_to_delete(user_id, r.message_id)
#
#     elif payment_data['Status'] == 'REFUNDED':
#         refund_message = (
#             'По текущему заказу был осуществлен частичный или полный возврат средств. Если это '
#             'произошло по ошибке, пожалуйста свяжитесь с администратором.'
#         )
#         for user_id in participants:
#             r = await bot.send_message(
#                 user_id,
#                 '<b>[Система]</b>\n' + refund_message
#             )
#             await add_message_to_delete(user_id, r.message_id)
#
#         new_message_to_save = {
#             "permissions": ["Customer"],
#             "timestamp": int(time.mktime(datetime.now().timetuple())),
#             "message_from_id": 0,
#             "message_from_username": '',
#             "sender_position": 'Система',
#             "message_content": refund_message,
#             "content_type": "text"
#         }
#
#         db["chat_sessions"].update_one({"chat_id": chat_id}, {"$push": {"messages": new_message_to_save}})
#
#     log_message('info',
#                 str(payment_data),
#                 0,
#                 traceback.extract_stack()[-1])
#
#     for admin in admins:
#         admin_tid = admin.get('telegram_id')
#         try:
#             await bot.send_message(admin_tid, text=f"New payment received: {payment_data}")
#         except Exception as e:
#             log_message('error',
#                         f'Ошибка обработки платежной информации {admin_tid}: {e}',
#                         0,
#                         traceback.extract_stack()[-1])
#
#     return web.Response(text="OK", status=200)

