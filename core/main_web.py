import os
import logging
import datetime as dt
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from core.reminder.general import scheduler
from core.settings import settings
from core.handlers.basic import *
from core.administrate import router_admin
from core.handlers import main_router

REDIS_DSN = "redis://127.0.0.1:6379"

bot = Bot(token=settings.bots.bot_token, parse_mode='HTML')
storage = RedisStorage.from_url(REDIS_DSN, key_builder=DefaultKeyBuilder(with_bot_id=True),
                                    data_ttl=dt.timedelta(days=1.0), state_ttl=dt.timedelta(days=1.0))
dp = Dispatcher(storage=storage)

MAIN_BOT_PATH = f"/MAIN"
BASE_URL = f"https://<ip>{MAIN_BOT_PATH}"
WEB_SERVER_HOST = "127.0.0.1"
WEB_SERVER_PORT = 8000

dp.include_routers(main_router, router_admin)
dp.message.filter(F.chat.type == 'private')

home = os.path.dirname(__file__)

if not os.path.exists(f"{home}/logging"):
    os.makedirs(f"{home}/logging")
if not os.path.exists(f"{home}/core/statistics/data"):
    os.makedirs(f"{home}/core/statistics/data")


# Для отладки локально разкоментить
# logging.basicConfig(level=logging.INFO)
#
# #Для отладки локально закоментить
logger = logging.getLogger()
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(f"{home}/logging/{dt.date.today()}.log", "a+", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)

logging.debug("Сообщения уровня DEBUG, необходимы при отладке ")
logging.info("Сообщения уровня INFO, полезная информация при работе программы")
logging.warning("Сообщения уровня WARNING, не критичны, но проблема может повторится")
logging.error("Сообщения уровня ERROR, программа не смогла выполнить какую-либо функцию")
logging.critical("Сообщения уровня CRITICAL, серьезная ошибка нарушающая дальнейшую работу")


async def on_startup():
    logger.error("Снятие и установка webhook")
    scheduler.start()
    await bot.delete_webhook()
    await bot.set_webhook(
            url=BASE_URL,
            certificate=types.FSInputFile("/etc/ssl/certs/Bot.crt"),  # Путь до сертификата
            drop_pending_updates=True)

    await bot.send_message(settings.bots.chat_id, "Бот запущен")
    return


async def on_shutdown():
    logging.warning('Выключение бота')
    await bot.delete_webhook()
    await bot.send_message(settings.bots.chat_id, "Бот выключен")
    return


dp.startup.register(on_startup)
dp.shutdown.register(on_shutdown)


def main():
    logger.error("Запуск веб-сервера")
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=MAIN_BOT_PATH)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)
    return


if __name__ == "__main__":
    main()
