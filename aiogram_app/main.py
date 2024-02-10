import logging
import sys
from aiogram import Bot
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from handlers import register_handlers
from middlware import CheckIsSubscribed
import traceback
from create_bot import (
    bot,
    router,
    log_message,
    dp,
    BASE_WEBHOOK_URL,
    WEBHOOK_PATH,
    WEB_SERVER_HOST,
    WEB_SERVER_PORT
)
from fsm import *


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

    log_message('info', 'бот запущен', 0, traceback.extract_stack()[-1])
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


def register_all_middlewares(dp):
    dp.message.middleware(CheckIsSubscribed())


def register_all_handlers(dp):
    register_handlers(dp)


if __name__ == "__main__":
    register_all_middlewares(dp)
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main()
