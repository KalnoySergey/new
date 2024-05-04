import logging
import asyncio
from datetime import datetime, timezone, timedelta
import aiogram
from aiogram.methods.get_me import GetMe
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ChatJoinRequest, User, CallbackQuery, error_event
from aiogram.filters import Command
from core.settings import settings
from core.utils.commands import set_commands
from core.classes.myClasses import Manager, Mailer, MyBotsList, MyBotsDict, tasks
from core.DB.database import BotDB
from core.utils.states import MyStates
from apscheduler.schedulers.asyncio import AsyncIOScheduler

dp = Dispatcher()
BotDB = BotDB('core/DB/mydb.db')


async def sub_check():
    for item in MyBotsList:
        me = await item.mybot.get_me()
        await BotDB.check_subscription_status(me.id)
async def start():
    # registration
    #await BotDB.del_all_from_users()
    #await BotDB.del_all_from_admins()
    #await BotDB.del_all_from_bots()
    #await BotDB.del_all_from_welcomes()
    #await BotDB.del_all_from_welcome_photos()
    #await BotDB.del_all_from_spams()
    await BotDB.admin_add_with_role(settings.bots.admin_id, 'God')
    await BotDB.admin_add_with_role(settings.bots.admin_id_2, 'MainAdmin')
    await BotDB.admin_add_with_role(settings.bots.admin_id_3, 'MainAdmin')

    manager = Manager(settings.bots.bot_token)
    me = await manager.mybot.get_me()
    MyBotsDict.update({'manager': manager})
    #scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(sub_check, 'cron', hour=0, minute=0, timezone='UTC')
    scheduler.start()
    await manager.start()
    #await set_commands(manager.mybot)
    dp.callback_query.register(Manager.select_welcome, F.data.startswith('Привітання'))
    dp.message.register(Manager.get_start, Command("start"))
    dp.callback_query.register(Manager.add, F.data.endswith('Add'))
    dp.callback_query.register(Manager.select_bot, F.data.lower().endswith('bot'))
    dp.callback_query.register(Manager.back, F.data.endswith('back'))
    dp.callback_query.register(Manager.update, F.data.endswith('update'))
    dp.callback_query.register(Manager.subscribe, F.data.endswith('subscribe'))
    dp.callback_query.register(Manager.back_to_menu, F.data.endswith('backtomenu'))
    dp.callback_query.register(Manager.settings, F.data.endswith('settings'))
    dp.callback_query.register(Manager.invite_switch, F.data.endswith('invite'))
    dp.callback_query.register(Manager.bot_delete, F.data.endswith('bot_delete'))
    dp.callback_query.register(Manager.bot_del_yes, F.data.endswith('bot_delete_yes'))
    dp.callback_query.register(Manager.bot_del_no, F.data.endswith('bot_delete_no'))
    dp.callback_query.register(Manager.welcomes, F.data.endswith('welcomes'))
    dp.callback_query.register(Manager.capcha, F.data.endswith('capcha'))
    dp.callback_query.register(Manager.capcha_back, F.data.endswith('welcomes_menu'))
    dp.callback_query.register(Manager.welcome_back, F.data.endswith('welcomes_menu2'))
    dp.callback_query.register(Manager.switch_capcha, F.data.endswith('switch_cap'))
    dp.callback_query.register(Manager.caphca_text, F.data.endswith('text_cap'))
    dp.callback_query.register(Manager.add_welcome, F.data.endswith('add_wel'))
    dp.callback_query.register(Manager.confirm, F.data.endswith('confirm'))
    dp.callback_query.register(Manager.welcome_delete, F.data.endswith('welcome_delete'))
    dp.callback_query.register(Manager.welcome_delete_yes, F.data.endswith('welcome_delete_yes'))
    dp.callback_query.register(Manager.welcome_delete_no, F.data.endswith('welcome_delete_no'))
    dp.callback_query.register(Manager.welcome_text_change, F.data.endswith('welcome_text_change'))
    dp.callback_query.register(Manager.welcome_buttons_change, F.data.endswith('welcome_buttons_change'))
    dp.callback_query.register(Manager.welcome_delay_change, F.data.endswith('welcome_delay_change'))
    dp.callback_query.register(Manager.welcome_delete_change, F.data.endswith('welcome_delete_change'))
    dp.callback_query.register(Manager.welcome_photo_change, F.data.endswith('welcome_photo_change'))
    dp.callback_query.register(Manager.spam_menu, F.data.endswith('spam_menu'))
    dp.callback_query.register(Manager.spam_start, F.data.endswith('spam_start'))
    dp.callback_query.register(Manager.solo_spam, F.data.endswith('solo_spam'))
    dp.callback_query.register(Manager.multi_spam, F.data.endswith('multi_spam'))

    dp.callback_query.register(Manager.admin_commands, F.data.endswith('admin_commands'))
    dp.callback_query.register(Manager.sub_off, F.data.endswith('sub_off'))
    dp.callback_query.register(Manager.sub_continue, F.data.endswith('sub_continue'))
    dp.callback_query.register(Manager.sub_transform, F.data.endswith('sub_transform'))

    dp.message.register(Manager.token_add, MyStates.ADDBOT)
    dp.message.register(Manager.sub_continue2, MyStates.SUB_CONTINUE)
    dp.message.register(Manager.sub_off2, MyStates.SUB_OFF)
    dp.message.register(Manager.sub_continue3, MyStates.SUB_MONTH)
    dp.message.register(Manager.sub_transform2, MyStates.SUB_TRANSFORM)
    dp.message.register(Manager.sub_transform3, MyStates.SUB_NEWADMIN)
    dp.message.register(Manager.new_capcha, MyStates.NEWCAPCHA)
    dp.message.register(Manager.new_welcome_text, MyStates.NEW_WELCOME_TEXT)
    dp.message.register(Manager.new_welcome_button, MyStates.NEW_WELCOME_BUTTON)
    dp.message.register(Manager.new_welcome_delay, MyStates.NEW_WELCOME_DELAY)
    dp.message.register(Manager.new_welcome_delete, MyStates.NEW_WELCOME_DELETE)
    dp.message.register(Manager.new_welcome_photo, MyStates.NEW_WELCOME_PHOTO)
    dp.message.register(Manager.welcome_text_change2, MyStates.СHANGE_WELCOME_TEXT)
    dp.message.register(Manager.welcome_buttons_change2, MyStates.СHANGE_WELCOME_BUTTONS)
    dp.message.register(Manager.welcome_delay_change2, MyStates.СHANGE_WELCOME_DELAY)
    dp.message.register(Manager.welcome_delete_change2, MyStates.CHANGE_WELCOME_DELETE)
    dp.message.register(Manager.welcome_photo_change2, MyStates.СHANGE_WELCOME_PHOTO)
    dp.message.register(Manager.new_spam_text, MyStates.NEW_SPAM_TEXT)
    dp.message.register(Manager.new_spam_button, MyStates.NEW_SPAM_BUTTON)
    dp.message.register(Manager.new_spam_delay, MyStates.NEW_SPAM_DELAY)
    dp.message.register(Manager.new_spam_photo, MyStates.NEW_SPAM_PHOTO)
    dp.message.register(Manager.new_spam_delete, MyStates.NEW_SPAM_DELETE)

    tasks.append(asyncio.create_task(dp.start_polling(manager.mybot)))
    try:
        await manager.mybot.delete_webhook(drop_pending_updates=True)
        await asyncio.gather(*tasks)
    finally:
        await BotDB.close_db()
        await manager.mybot.session.close()
        for item in MyBotsList:
            await item.mybot.session.close()

    # message logging
    # dp.startup.register(Manager.start_bot)
    # dp.shutdown.register(Manager.stop_bot)

    # logging.basicConfig(level=logging.INFO,
    #                     format="%(asctime)s - [%(levelname)s] - %(name)s - "
    #                            "(%(filename)s).%(funcName)s(%(lineno)d) - %(message)s")
    # hanlers + filters
if __name__ == "__main__":
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass
