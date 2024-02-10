from aiogram import BaseMiddleware
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from typing import Callable, Awaitable, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from os import getenv

env_path = Path('..') / '.env'
load_dotenv(dotenv_path=env_path)
botname = getenv('SERVICE_OFFICAIL_NAME')
subscription_group_id = getenv('SUBSCRIPTION_GROUP_ID')
subscription_group_url = getenv('SUBSCRIPTION_GROUP_URL')


class CheckIsSubscribed(BaseMiddleware):
    async def __call__(self,
                       handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
                       event: Message,
                       data: Dict[str, Any],
                       *args,
                       **kwargs
                       ) -> Any:
        group_member = await event.bot.get_chat_member(subscription_group_id, event.from_user.id)
        if group_member.status not in ['left', 'kicked']:
            return await handler(event, data)
        else:
            sub_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text='Подписаться',
                        url=subscription_group_url
                    )]])
            d = await event.answer(
                f"Пожалуйста подпишитесь на <b><a href='{subscription_group_url}'>нашу группу</a></b>, "
                f"чтобы продолжить работу с ботом.",
                reply_markup=sub_kb
            )
            sub_kb.inline_keyboard.append(
                    [InlineKeyboardButton(
                        text='Проверить подписку',
                        callback_data=f'sub_confirmed|{d.message_id}'
                    )]
            )

            await event.bot.edit_message_reply_markup(
                chat_id=event.chat.id,
                message_id=d.message_id,
                reply_markup=sub_kb
            )
