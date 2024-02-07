import logging
import sys
from pathlib import Path  # Добавляем pathlib для работы с путями
from dotenv import load_dotenv  # Импортируем load_dotenv
from os import getenv
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from database import session_factory
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
import handlers
import fsm
import traceback
from payment_handler import handle_payment_webhook


async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}")


def main() -> None:
    dp.include_router(router)
    app = web.Application()

    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    # app.router.add_post(f'/{TINKOFF_PAYMENT_URI}', handle_payment_webhook)

    log_message('info', 'бот запущен', 0, traceback.extract_stack()[-1])
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main()
