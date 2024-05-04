import io
import gc
import asyncio
import functools
import tempfile
import time
import re
import aiogram.exceptions
from aiogram import Bot, types, Dispatcher, Router, F
from core.settings import settings
from core.utils.commands import set_commands
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import Message, ChatJoinRequest, CallbackQuery, InputFile
from aiogram.types.input_file import InputFile
from core.DB.database import BotDB
from aiogram.fsm.context import FSMContext
from core.utils.states import MyStates
from aiogram.methods.get_me import GetMe
from aiogram.enums.parse_mode import ParseMode
from prettytable import PrettyTable
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone, timedelta

BotDB = BotDB('core/DB/mydb.db')
tasks = []
MyBotsList = []
MyBotsDict = {}
MyBotsDisp = {}
tempBOT = None

class Buttons:

    buttons:InlineKeyboardBuilder

    def __init__(self):
        self.buttons = InlineKeyboardBuilder()

class Mailer:
    mybot = None # объект бота
    name = None # юзернейм
    token = None # токен

    capchaButton: ReplyKeyboardBuilder


    WelcomesDict = {}

    spam_builder = {}

    join = False

    def __init__(self, token):
        self.token = token
        self.mybot = Bot(self.token)
        self.capchaButton = ReplyKeyboardBuilder()
        self.capchaButton.button(text=f"Підтвердити ✅")
        self.capchaButton.adjust(1, False)
        self.WelcomesList = []

    async def set_name(self,name):
        self.name = name
    async def chat_join_request_handler(self, chat_join_request: ChatJoinRequest, bot: Bot):
        me = await bot.get_me()
        bot_id = me.id
        user_id = chat_join_request.from_user.id
        chat_id = chat_join_request.chat.id
        cap = await BotDB.bot_get_capcha(bot_id)
        if await BotDB.capcha_is_active(bot_id):
            if not await BotDB.user_exist(bot_id, user_id):
                await bot.send_message(user_id, cap, parse_mode='Markdown', reply_markup=self.capchaButton.as_markup(resize_keyboard=True))
        if self.join:
            await bot.approve_chat_join_request(chat_id, user_id)
    async def switch_mode(self):
        if self.join == True:
            self.join = False
        else:
            self.join = True
    async def get_mode(self):
        return self.join
    async def mailer_start(self, message: Message):
        await message.answer(f"Привет, я {self.name}")
    async def confirm(self, message: Message, bot: Bot):

        me = await bot.get_me()
        bot_id = me.id
        if not await BotDB.user_exist(bot_id, message.from_user.id):
            scheduler = AsyncIOScheduler()
            bot_name = await BotDB.bot_get_name(bot_id)
            user_id = message.from_user.id
            user_lang = message.from_user.language_code
            await BotDB.user_add(bot_id, user_id, user_lang)
            mybot = MyBotsDict.get(bot_name)
            timenow = datetime.now()
            await bot.delete_message(user_id, message.message_id - 1)
            await bot.delete_message(user_id, message.message_id)
            for welcome in mybot.WelcomesList:
                welcome_id = await BotDB.get_welcome_id_by_name(welcome, bot_id)
                delay_time = await BotDB.get_welcome_delay(welcome_id)
                if delay_time == 'now':
                    timenow += timedelta(seconds=1)
                else:
                    h, m, s = await Manager.parse_time_input(delay_time)
                    timenow += timedelta(hours=h, minutes=m, seconds=s)
                scheduler.add_job(Mailer.send_message, trigger='date',
                                  run_date=timenow,
                                  kwargs={'bot_name': bot_name, 'welcome': welcome, 'user': user_id})
            scheduler.start()
    async def send_message(bot_name, welcome, user):
        scheduler = AsyncIOScheduler()
        bot = MyBotsDict.get(bot_name)
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        welcome_id = await BotDB.get_welcome_id_by_name(welcome, bot_id)
        text_template = await BotDB.get_welcome_text(welcome_id)
        button = bot.WelcomesDict.get(welcome)
        builder = button.buttons
        welcome_photo = await BotDB.get_welcome_photo(welcome_id)

        myuser = await bot.mybot.get_chat(user)
        user_info = {
            'id': myuser.id,
            'username': myuser.username,
            'first_name': myuser.first_name,
            'last_name': myuser.last_name
        }
        text = await Manager.replace_placeholders(text_template, user_info)

        if welcome_photo == '0':
            mes = await bot.mybot.send_message(chat_id=user, text=text, parse_mode='Markdown', reply_markup=builder.as_markup())
        else:
            photo_data = await BotDB.get_welcome_photo2(welcome_id)
            photo = types.BufferedInputFile(file=photo_data,filename='name')
            mes = await bot.mybot.send_photo(chat_id=user, photo=photo, caption=text, parse_mode='Markdown', reply_markup=builder.as_markup())
        if await BotDB.welcome_del_is_active(welcome_id):
            delete_time = await BotDB.get_welcome_delete(welcome_id)
            h, m, s = await Manager.parse_time_input(delete_time)
            scheduler.add_job(Mailer.delete_message, trigger='date', run_date=datetime.now() + timedelta(hours=h, minutes=m, seconds=s), kwargs={'message':mes})
        scheduler.start()
    async def delete_message(message: Message):
        await message.delete()

class Manager:
    mybot = None # объект бота
    name = None # юзернейм
    token = None # токен
    bots = []

    def __init__(self, token):
        self.token = token
        self.mybot = Bot(token=self.token)
    async def set_name(self,name):
        self.name = name

    async def menu(user_id):
        builder = InlineKeyboardBuilder()
        if await BotDB.admin_exist(admin_id=user_id):
            pass
        else:
            await BotDB.admin_add(admin_id=user_id)
        bot_names = await BotDB.get_bot_names_by_admin(admin_id=user_id)
        for bot_name in bot_names:
            builder.button(text=f"{bot_name}", callback_data=bot_name)

        builder.button(text=f"Додати бота", callback_data="Add")
        if await BotDB.admin_get_role(user_id) != 'Admin':
            builder.button(text=f"Команди адміна", callback_data="admin_commands")
        builder.adjust(1, 1)
        return builder
    async def get_start(message: Message, state: FSMContext):
        user_id = message.from_user.id
        builder = await Manager.menu(user_id)
        mes = await message.answer(f"⚡️Мультифункціональний бот для керування вашим трафіком у Телеграм. \n\n Питання щодо співпраці/оплати - @ne_ckam \n\n оберіть бота, або додайте нового⤵️", reply_markup=builder.as_markup())
        await state.update_data(todelete=mes)
        await state.set_state(MyStates.START)
    async def add(call: CallbackQuery, state: FSMContext):
        builder = InlineKeyboardBuilder()
        data = await state.get_data()
        mes1 = data.get('todelete')
        builder.button(text=f"Відміна", callback_data="back")
        mes = await call.message.answer("⚡️Будь ласка, відправ мені токен твого персонального бота. \n\n 📌 Щоб створити такого бота: \n 1. Відкрий BotFather — @BotFather \n 2. Створи нового бота (/newbot команда) \n 3. Скопіюй і відправ мені API токен, який ти отримаєш від BotFather, наприклад 123456789:AATTcDT-abU0IYzQsftg458Wjqt9APmUGU4 \n\n ⚠️ Не добавляй свого бота до інших сервісів чи ботів!", parse_mode='Markdown', reply_markup=builder.as_markup())
        await mes1.delete()
        await state.update_data(todelete=mes)
        await call.answer()
        await state.set_state(MyStates.ADDBOT)
    async def token_add(message: Message, state: FSMContext):
        data = await state.get_data()
        mes1 = data.get('todelete')
        dp2 = Dispatcher()
        mytoken = message.text
        bot = Mailer(token=mytoken)
        me = await bot.mybot.get_me()
        await bot.set_name(me.username)
        MyBotsList.append(bot)
        MyBotsDict.update({me.username:bot})
        await message.answer(f"Бот успішно доданий")
        await BotDB.bot_add(message.from_user.id,me.id,mytoken, me.username)
        dp2.message.register(bot.mailer_start, Command("start"))
        dp2.chat_join_request.register(bot.chat_join_request_handler)
        dp2.message.register(bot.confirm, F.text.startswith('Підтвердити'))

        MyBotsDisp.update({me.username: dp2})
        await Manager.get_start(message, state)
        await mes1.delete()
        await dp2.start_polling(bot.mybot)
    async def dele(message: Message):
        await message.delete()
    async def select_bot(call: CallbackQuery, state: FSMContext):
        bot_name =  call.data.split('*')[0]
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        #await BotDB.del_spam_by_bot_id(bot_id)
        all = await BotDB.get_user_count(bot_id)
        today = await BotDB.user_added_today(bot_id)
        yesterday = await BotDB.user_added_yesterday(bot_id)
        week = await BotDB.user_added_last_week(bot_id)

        uk = await BotDB.get_user_uk_count(bot_id)
        ru = await BotDB.get_user_ru_count(bot_id)
        en = await BotDB.get_user_en_count(bot_id)
        other = all - uk - ru - en

        if all != 0:
            _uk = float((uk*100)/all)
            _ru = float((ru*100)/all)
            _en = float((en*100)/all)
            _other = float((other*100)/all)
        else:
            _uk = 0
            _ru = 0
            _en = 0
            _other = 0
        table = PrettyTable()
        table.field_names = ["Юзери", "Кількість"]
        table.add_row(["", ""])
        table.add_row(["Всі", all])
        table.add_row(["Сьогодні", today])
        table.add_row(["Вчора", yesterday])
        table.add_row(["Тиждень", week])
        table.add_row(["укр", f'{uk} ({_uk:.1f}%)'])
        table.add_row(["рос", f'{ru} ({_ru:.1f}%)'])
        table.add_row(["англ", f'{en} ({_en:.1f}%)'])
        table.add_row(["інші", f'{other} ({_other:.1f}%)'])

        builder = InlineKeyboardBuilder()

        builder.button(text=f"Привітання👋", callback_data=f"{bot_name}*welcomes")
        builder.button(text=f"Розсилка✉️", callback_data=f"{bot_name}*spam_menu")
        builder.button(text=f"Налаштування️⚙️", callback_data=f"{bot_name}*settings")
        builder.button(text=f"Підписка️🗓️", callback_data=f"{bot_name}*subscribe")
        builder.button(text=f"Оновити", callback_data=f"{bot_name}*update")
        builder.button(text=f"Назад", callback_data="back")
        builder.adjust(2, 2)
        status = ''
        if await BotDB.subscribe_is_active(bot_id):
            status = 'Активний'
        else:
            status = 'Неактивний'
        await call.message.edit_text(f"Статистика по боту: \n\n Назва: \t{bot_name} \n ID: \t`{bot_id}` \n Статус: \t`{status}` \n\n`{str(table)}`", parse_mode='Markdown', reply_markup=builder.as_markup())
        await call.answer()
        await state.set_state(MyStates.BOTSELECT)
    async def back(call: CallbackQuery, state: FSMContext):

        user_id = call.from_user.id
        builder = await Manager.menu(user_id)
        await call.answer()
        await call.message.edit_text(f"⚡️Мультифункціональний бот для керування вашим трафіком у Телеграм. \n\n Питання щодо співпраці/оплати - @ne_ckam \n\n оберіть бота, або додайте нового⤵️", reply_markup=builder.as_markup())

        await state.set_state(MyStates.START)
    async def update(call: CallbackQuery, state: FSMContext):
        bot_name =  call.data.split('*')[0]

        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        all = await BotDB.get_user_count(bot_id)
        today = await BotDB.user_added_today(bot_id)
        yesterday = await BotDB.user_added_yesterday(bot_id)
        week = await BotDB.user_added_last_week(bot_id)

        uk = await BotDB.get_user_uk_count(bot_id)
        ru = await BotDB.get_user_ru_count(bot_id)
        en = await BotDB.get_user_en_count(bot_id)
        other = all - uk - ru - en

        if all != 0:
            _uk = float((uk * 100) / all)
            _ru = float((ru * 100) / all)
            _en = float((en * 100) / all)
            _other = float((other * 100) / all)
        else:
            _uk = 0
            _ru = 0
            _en = 0
            _other = 0
        table = PrettyTable()
        table.field_names = ["Юзери", "Кількість"]
        table.add_row(["", ""])
        table.add_row(["Всі", all])
        table.add_row(["Сьогодні", today])
        table.add_row(["Вчора", yesterday])
        table.add_row(["Тиждень", week])
        table.add_row(["укр", f'{uk} ({_uk:.1f}%)'])
        table.add_row(["рос", f'{ru} ({_ru:.1f}%)'])
        table.add_row(["англ", f'{en} ({_en:.1f}%)'])
        table.add_row(["інші", f'{other} ({_other:.1f}%)'])

        builder = InlineKeyboardBuilder()

        builder.button(text=f"Привітання👋", callback_data=f"{bot_name}*welcomes")
        builder.button(text=f"Розсилка✉️", callback_data=f"{bot_name}*spam_menu")
        builder.button(text=f"Налаштування️⚙️", callback_data=f"{bot_name}*settings")
        builder.button(text=f"Підписка️🗓️", callback_data=f"{bot_name}*subscribe")
        builder.button(text=f"Оновити", callback_data=f"{bot_name}*update")
        builder.button(text=f"Назад", callback_data="back")
        builder.adjust(2, 2)
        status = ''
        if await BotDB.subscribe_is_active(bot_id):
            status = 'Активний'
        else:
            status = 'Неактивний'

        await call.message.edit_text(f"Статистика по боту: \n\n Hазва: \t{bot_name} \n ID: \t`{bot_id}`  \n Статус: \t`{status}` \n\n`{str(table)}`", parse_mode='Markdown', reply_markup=builder.as_markup())
        await call.message.edit_text(f"Статистика по боту: \n\n Назва: \t{bot_name} \n ID: \t`{bot_id}`  \n Статус: \t`{status}` \n\n`{str(table)}`", parse_mode='Markdown', reply_markup=builder.as_markup())
        await call.answer()
        await BotDB.check_subscription_status(bot_id)
    async def welcomes(call: CallbackQuery, state: FSMContext):
        bot_name = call.data.split('*')[0]
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        if await BotDB.subscribe_is_active(bot_id):
            bot = MyBotsDict.get(bot_name)
            builder = InlineKeyboardBuilder()

            builder.button(text=f"Капча", callback_data=f"{bot_name}*capcha")
            list = await BotDB.get_all_welcomes_name(bot_id)
            for button in list:
                builder.button(text=f"{button}", callback_data=f"{button}*{bot_name}*")
            builder.button(text=f"➕Додати привітання", callback_data=f"{bot_name}*add_wel")
            builder.button(text=f"Назад", callback_data=f"{bot_name}*backtomenu")
            builder.adjust(1, 1)
            await call.message.edit_text(f"----------------------| Привітання |----------------------",
                                         parse_mode='Markdown', reply_markup=builder.as_markup())
        else:
            await call.answer("Підписка неактивна")
    async def add_welcome(call: CallbackQuery, state: FSMContext):
        await call.answer()
        bot_name = call.data.split('*')[0]
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        mes = await call.message.edit_text(f"Введіть текст нового привітання:")
        await state.update_data(bot_name=bot_name, todelete=mes)
        await state.set_state(MyStates.NEW_WELCOME_TEXT)
    async def new_welcome_text(message: Message, state: FSMContext):
        newtext = message.text
        data = await state.get_data()
        bot_name = data.get('bot_name')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        bot = MyBotsDict.get(bot_name)
        mes = data.get('todelete')

        welcome = "Привітання " + str(len(bot.WelcomesList) + 1)
        await BotDB.add_welcome(bot_id, welcome, newtext)
        bot.WelcomesList.append(welcome)
        mes1 = await message.answer(f'Додайте кнопки в форматі:\n\n'
                            f'Кнопка 1 - http://example1.com | Кнопка 2 - http://example2.com\n'
                            f'Кнопка 3 - http://example3.com | Кнопка 4 - http://example4.com\n'
                            f'Кнопка 1 і Кнопка 2 знаходяться в одному рядку, Кнопка 1 і Кнопка 3 в одному стовпці. Щоб не додавати кнопки, відправте 0', parse_mode='Markdown')
        await mes.delete()
        await state.update_data(bot_name=bot_name, newwelcome=welcome, todelete=mes1)
        await state.set_state(MyStates.NEW_WELCOME_BUTTON)
    async def new_welcome_button(message: Message, state: FSMContext):
        newtext = message.text
        data = await state.get_data()
        bot_name = data.get('bot_name')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        bot = MyBotsDict.get(bot_name)
        welcome = data.get('newwelcome')
        button = Buttons()
        bot.WelcomesDict.update({welcome: button})
        builder = button.buttons
        welcome_id = await BotDB.get_welcome_id_by_name(welcome, bot_id)
        if newtext != '0':
            alltext = newtext.split('\n')
            buttons = []
            nums = []
            for allt in alltext:
                text = allt.split(' | ')
                for txt in text:
                    buttons.append(txt)
            for button1 in buttons:
                newbutton = button1.split(' - ')
                await BotDB.add_button(welcome_id, newbutton[0], newbutton[1])
                builder.button(text=newbutton[0], url=newbutton[1])
            for txt in alltext:
                nums.append(len(txt.split(' | ')))

            strnums= ','.join(map(str, nums))

            await BotDB.set_welcome_adjust(welcome_id, strnums)
            builder.adjust(*nums)

        mes1 = await message.answer(f'Введіть затримку відправки у форматі  10h10m10s\n'
                             f'Щоб відправити одразу введіть 0', parse_mode='Markdown')
        mes = data.get('todelete')
        await mes.delete()
        await state.update_data(bot_name=bot_name, newwelcome=welcome,todelete=mes1)
        await state.set_state(MyStates.NEW_WELCOME_DELAY)
    async def new_welcome_delay(message: Message, state: FSMContext):
        newtext = message.text
        data = await state.get_data()
        bot_name = data.get('bot_name')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        welcome = data.get('newwelcome')
        welcome_id = await BotDB.get_welcome_id_by_name(welcome,bot_id)

        if newtext == '0':
            await BotDB.set_welcome_delay(welcome_id, "now")

            mes = data.get('todelete')
            mes1 = await message.answer(f'Введіть час, через який видалиться привітання у форматі 10h10m10s\n'
                                        f'Щоб не видаляти привітання введіть 0', parse_mode='Markdown')
            await mes.delete()
            await state.update_data(bot_name=bot_name, newwelcome=welcome, todelete=mes1)
            await state.set_state(MyStates.NEW_WELCOME_DELETE)
        else:
            await BotDB.set_welcome_delay(welcome_id, newtext)

            mes = data.get('todelete')
            mes1 = await message.answer(f'Введіть час, через який видалиться привітання у форматі 10h10m10s\n'
                                        f'Щоб не видаляти привітання введіть 0', parse_mode='Markdown')
            await mes.delete()
            await state.update_data(bot_name=bot_name, newwelcome=welcome, todelete=mes1)
            await state.set_state(MyStates.NEW_WELCOME_DELETE)
    async def new_welcome_delete(message: Message, state: FSMContext):
        newtext = message.text
        data = await state.get_data()
        bot_name = data.get('bot_name')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        welcome = data.get('newwelcome')
        welcome_id = await BotDB.get_welcome_id_by_name(welcome, bot_id)

        if newtext == '0':
            await BotDB.delete_off(welcome_id)
            await BotDB.set_welcome_delete(welcome_id, "0:0:0")

            mes = data.get('todelete')
            mes1 = await message.answer(f'Відправте картинку для привітання, щоб не додавати картинку відправте 0', parse_mode='Markdown')
            await mes.delete()
            await state.update_data(bot_name=bot_name, newwelcome=welcome, todelete=mes1)
            await state.set_state(MyStates.NEW_WELCOME_PHOTO)
        else:
            await BotDB.delete_on(welcome_id)
            await BotDB.set_welcome_delete(welcome_id, newtext)

            mes = data.get('todelete')
            mes1 = await message.answer(f'Відправте картинку для привітання, щоб не додавати картинку відправте 0',
                                        parse_mode='Markdown')
            await mes.delete()
            await state.update_data(bot_name=bot_name, newwelcome=welcome, todelete=mes1)
            await state.set_state(MyStates.NEW_WELCOME_PHOTO)
    async def new_welcome_photo(message: Message, state: FSMContext):
        data = await state.get_data()
        bot_name = data.get('bot_name')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        welcome = data.get('newwelcome')
        welcome_id = await BotDB.get_welcome_id_by_name(welcome, bot_id)
        await BotDB.add_welcome_photo(welcome_id)

        if message.text == '0':
            photo = '0'
            await BotDB.set_welcome_photo(welcome_id, photo)
            builder = InlineKeyboardBuilder()
            builder.button(text='Продовжити', callback_data=f'{bot_name}*welcomes')
            await message.answer(f'Привітання успішно настроєно',parse_mode='Markdown', reply_markup=builder.as_markup())
            mes = data.get('todelete')
            await mes.delete()
            await state.set_state(MyStates.WELCOME_SELECT)
        else:
            try:
                bot = MyBotsDict.get('manager')
                photo = message.photo[-1].file_id
                file_info = await bot.mybot.get_file(photo)
                photo_url = file_info.file_path
                photo_data = await bot.mybot.download_file(photo_url)
                if isinstance(photo_data, io.BytesIO):
                    photo_data = photo_data.read()
                await BotDB.set_welcome_photo2(photo_data, welcome_id)
                await BotDB.set_welcome_photo(welcome_id, photo)
                builder = InlineKeyboardBuilder()
                builder.button(text='Продовжити', callback_data=f'{bot_name}*welcomes')
                await message.answer(f'Привітання успішно настроєно',parse_mode='Markdown', reply_markup=builder.as_markup())
                mes = data.get('todelete')
                await mes.delete()
                await state.set_state(MyStates.WELCOME_SELECT)
            except:
                mes1 = await message.answer(f'Неправильний формат повідомлення, ще раз відправте картинку для привітання, щоб не додавати картинку відправте 0',parse_mode='Markdown')
                mes = data.get('todelete')
                await mes.delete()
                await state.update_data(bot_name=bot_name, newwelcome=welcome, todelete=mes1)
    async def capcha(call: CallbackQuery, state: FSMContext):
        await call.answer()
        bot_name = call.data.split('*')[0]
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        bot = MyBotsDict.get(bot_name)
        builder = InlineKeyboardBuilder()
        cap = await BotDB.bot_get_capcha(bot_id)
        message1 = await call.message.edit_text(f"Так зараз виглядає капча:")
        message2 = await call.message.answer(cap, parse_mode='Markdown')

        await state.update_data(todelete1=message1)
        await state.update_data(todelete2=message2)

        builder.button(text=f"Змінити повідомлення", callback_data=f"{bot_name}*text_cap")
        if await BotDB.capcha_is_active(bot_id):
            builder.button(text=f"Вимкнути капчу", callback_data=f"{bot_name}*switch_cap")
        else:
            builder.button(text=f"Увімкнути капчу", callback_data=f"{bot_name}*switch_cap")
        builder.button(text=f"Назад", callback_data=f"{bot_name}*welcomes_menu")
        builder.adjust(1, 1)
        await call.message.answer(f"---------------| Налаштування капчі |---------------", parse_mode='Markdown', reply_markup=builder.as_markup())
        await state.set_state(MyStates.CAPCHA)
    async def caphca_text(call: CallbackQuery, state: FSMContext):
        await call.answer()
        bot_name = call.data.split('*')[0]

        data = await state.get_data()
        mes1 = data.get('todelete1')
        mes2 = data.get('todelete2')

        mes = await call.message.edit_text('Введіть нове повідомлення:')

        await mes1.delete()
        await mes2.delete()
        await state.update_data(name=bot_name, todelete=mes)
        await state.set_state(MyStates.NEWCAPCHA)
    async def new_capcha(message: Message, state: FSMContext):
        data = await state.get_data()
        bot_name = data.get('name')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        mes = data.get('todelete')
        
        bot = MyBotsDict.get(bot_name)
        text = message.text

        builder = InlineKeyboardBuilder()
        builder.button(text=f"Продовжити", callback_data=f"{bot_name}*capcha")
        await BotDB.set_capha(bot_id, text)
        await message.answer(f'Текст успішно змінено', parse_mode='Markdown', reply_markup=builder.as_markup())
        await mes.delete()
        await state.set_state(MyStates.CAPCHA)
    async def switch_capcha(call: CallbackQuery, state: FSMContext):
        await call.answer()
        bot_name = call.data.split('*')[0]
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        bot = MyBotsDict[bot_name]
        me = await bot.mybot.get_me()
        await BotDB.switch_capcha(bot_id)

        builder = InlineKeyboardBuilder()

        builder.button(text=f"Змінити повідомлення", callback_data=f"{bot_name}*text_cap")
        if await BotDB.capcha_is_active(bot_id):
            builder.button(text=f"Вимкнути капчу", callback_data=f"{bot_name}*switch_cap")
        else:
            builder.button(text=f"Увімкнути капчу", callback_data=f"{bot_name}*switch_cap")
        builder.button(text=f"Назад", callback_data=f"{bot_name}*welcomes_menu")
        builder.adjust(1, 1)
        await call.message.edit_text(f"---------------| Нaлаштування капчі |---------------", parse_mode='Markdown', reply_markup=builder.as_markup())
        await call.message.edit_text(f"---------------| Налаштування капчі |---------------", parse_mode='Markdown', reply_markup=builder.as_markup())
    async def capcha_back(call: CallbackQuery, state: FSMContext):
        await call.answer()
        data = await state.get_data()

        await Manager.welcomes(call, state)

        mes1 = data.get('todelete1')
        mes2 = data.get('todelete2')

        await mes1.delete()
        await mes2.delete()
    async def welcome_back(call: CallbackQuery, state: FSMContext):
        await call.answer()
        data = await state.get_data()

        await Manager.welcomes(call, state)

        mes = data.get('todelete')
        await mes.delete()
    async def subscribe(call: CallbackQuery, state: FSMContext):
        bot_name =  call.data.split('*')[0]
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        builder = InlineKeyboardBuilder()
        builder.button(text=f"Назад", callback_data=f"{bot_name}*backtomenu")
        builder.adjust(1, 1)
        await call.answer()
        admin_id = await BotDB.bot_get_admin(bot_id)
        final_date = await BotDB.get_subscription_end_date(bot_id)

        if await BotDB.admin_exist(admin_id):
            if await BotDB.admin_get_role(admin_id) == 'Admin':
                if await BotDB.check_subscription_status(bot_id):
                    await call.message.edit_text(f"Підписка дійсна до: \n\n {final_date} UTC", parse_mode='Markdown', reply_markup=builder.as_markup())
                else:
                    await call.message.edit_text(f"Підписка закінчилась\n\nЗверніться до @ne_ckam для її продовження", parse_mode='Markdown', reply_markup=builder.as_markup())
            else: await call.message.edit_text(f"Ти головний босс цієї качалки\n\nТвоя підписка безкінечна😎", parse_mode='Markdown', reply_markup=builder.as_markup())
        else: await call.message.edit_text(f"Підписка дійсна до: \n\n {final_date} UTC", parse_mode='Markdown', reply_markup=builder.as_markup())
    async def back_to_menu(call: CallbackQuery, state: FSMContext):
        await Manager.select_bot(call, state)
    async def settings(call: CallbackQuery, state: FSMContext):
        bot_name = call.data.split('*')[0]
        builder = InlineKeyboardBuilder()
        bot = MyBotsDict[bot_name]
        if bot.join:
            builder.button(text=f"Автоприйом (увімкнений)", callback_data=f"{bot_name}*invite")
        else:
            builder.button(text=f"Автоприйом (вимкнений)", callback_data=f"{bot_name}*invite")

        builder.button(text=f"Видалити бота", callback_data=f"{bot_name}*bot_delete")
        builder.button(text=f"Назад", callback_data=f"{bot_name}*backtomenu")
        builder.adjust(1, 1)
        await call.message.edit_text(f"---------------------| Hалаштування |---------------------", parse_mode='Markdown', reply_markup=builder.as_markup())
        await call.message.edit_text(f"---------------------| Налаштування |---------------------", parse_mode='Markdown', reply_markup=builder.as_markup())
    async def invite_switch(call: CallbackQuery, state: FSMContext):
        bot_name = call.data.split('*')[0]
        bot = MyBotsDict[bot_name]
        me = await bot.mybot.get_me()
        if await BotDB.subscribe_is_active(me.id):
            await bot.switch_mode()
            await Manager.settings(call, state)
            await call.answer()
        else:
            await call.answer("Підписка неактивна")
    async def bot_delete(call: CallbackQuery, state: FSMContext):
        bot_name = call.data.split('*')[0]
        builder = InlineKeyboardBuilder()
        builder.button(text=f"Так", callback_data=f"{bot_name}*bot_delete_yes")
        builder.button(text=f"Ні", callback_data=f"{bot_name}*bot_delete_no")
        await call.message.edit_text(f"Ви впевнені, що хочете видалити бота?", parse_mode='Markdown', reply_markup=builder.as_markup())
    async def bot_del_yes(call: CallbackQuery, state: FSMContext):
        bot_name = call.data.split('*')[0]
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        bot = MyBotsDict[bot_name]
        bot_dp = MyBotsDisp[bot_name]
        bot_index = MyBotsList.index(bot)

        bot.chat_join_request_handler = functools.partial(lambda *args, **kwargs: None)
        bot.mailer_start = functools.partial(lambda *args, **kwargs: None)
        bot.confirm = functools.partial(lambda *args, **kwargs: None)
        MyBotsList.pop(bot_index)
        MyBotsDict.pop(bot_name, None)
        await bot_dp.stop_polling()
        MyBotsDisp.pop(bot_name, None)
        await BotDB.bot_delete(bot_id)
        del bot
        del bot_dp
        await call.answer()
        await Manager.back(call, state)
    async def bot_del_no(call: CallbackQuery, state: FSMContext):
        await call.answer()
        await Manager.settings(call, state)
    async def admin_commands(call: CallbackQuery, state: FSMContext):
        builder = InlineKeyboardBuilder()

        builder.button(text=f"Вимкнути підписку", callback_data="sub_off")
        builder.button(text=f"Продовжити підписку", callback_data="sub_continue")
        builder.button(text=f"Перенести обліковий запис", callback_data="sub_transform")
        builder.button(text=f"Назад", callback_data="back")
        builder.adjust(1,1)
        await call.message.edit_text("-------------------| Команди адміна |-------------------", parse_mode='Markdown', reply_markup=builder.as_markup())
        await call.answer()
        await state.set_state(MyStates.ADMIN_COMMANDS)
    async def sub_off(call: CallbackQuery, state: FSMContext):
        await call.answer()
        await call.message.answer(f"Введіть юзернейм бота, якому хочете вимкнути підписку (без символа @):")
        await state.set_state(MyStates.SUB_OFF)
    async def sub_off2(message: Message, state: FSMContext):
        bot_name = message.text
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        if await BotDB.bot_exist(bot_id):
            await BotDB.subscribe_off(bot_id)
            await BotDB.set_bot_days_0(bot_id)
            await message.answer(f'Підписка для бота `{bot_name}` вимкнена', parse_mode='Markdown')
            await Manager.get_start(message, state)
        else:
            await message.answer('Такого бота нема у нашій базі, спробуйте ще раз')
    async def sub_continue(call: CallbackQuery, state: FSMContext):
        await call.answer()
        await call.message.answer(f"Введіть юзернейм бота, якому хочете продовжити підписку (без символа @):")
        await state.set_state(MyStates.SUB_CONTINUE)
    async def sub_continue2(message: Message, state: FSMContext):
        bot_name = message.text
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        if await BotDB.bot_exist(bot_id):
            await message.answer(f"Введіть кількість місяців, на скільки хочете продовжити підписку:")
            await state.update_data(id=bot_id)
            await state.set_state(MyStates.SUB_MONTH)
        else:
            await message.answer('Такого бота нема у нашій базі, спробуйте ще раз')
    async def sub_continue3(message: Message, state: FSMContext):
        data = await state.get_data()
        month = int(message.text)
        if month > 0:
            await BotDB.continue_subscribe(data.get('id'), month)
            name = await BotDB.bot_get_name(data.get('id'))
            await message.answer(f'Підписка для бота {name} успішно продовжена на {month} місяців')
            await Manager.get_start(message, state)
        else:
            await message.answer('Невірне число (меньше або дорівнює 0), спробуйте ще раз')
    async def sub_transform(call: CallbackQuery, state: FSMContext):
        await call.answer()
        await call.message.answer(f"Введіть старий id користувача, якого хочете перенести:")
        await state.set_state(MyStates.SUB_TRANSFORM)
    async def sub_transform2(message: Message, state: FSMContext):
        admin1 = int(message.text)
        if await BotDB.admin_exist(admin1):
            await message.answer(f"Введіть новий id користувача, якого хочете перенести:")
            await state.update_data(admin=admin1)
            await state.set_state(MyStates.SUB_NEWADMIN)
        else:
            await message.answer('Такого користувача нема у нашій базі, спробуйте ще раз')
    async def sub_transform3(message: Message, state: FSMContext):
        data = await state.get_data()
        admin1 = data.get('admin')
        admin2 = int(message.text)
        await BotDB.switch_admin(admin1, admin2)
        await message.answer(f'Адміна було перенесено')
        await Manager.get_start(message, state)
    async def start(self):
        bots = await BotDB.get_all_bot_tokens()

        for item in bots:
            dp2 = Dispatcher()

            bot = Mailer(token=item)
            me = await bot.mybot.get_me()
            await bot.set_name(me.username)
            bot_id = await BotDB.get_bot_id_by_name(bot.name)
            MyBotsList.append(bot)
            MyBotsDict.update({me.username: bot})

            welcomes = await BotDB.get_all_welcomes_name(bot_id)

            for welcome in welcomes:
                welcome_id = await BotDB.get_welcome_id_by_name(welcome, bot_id)
                bot.WelcomesList.append(welcome)
                but = Buttons()
                bot.WelcomesDict.update({welcome: but})
                builder = but.buttons

                buttons = await BotDB.get_all_buttons_text(welcome_id)
                urls = await BotDB.get_all_buttons_url(welcome_id)

                for button, url in zip(buttons, urls):
                    builder.button(text=button, url=url)
                str_adjust = await BotDB.get_welcome_adjust(welcome_id)
                int_adjust = [int(x) for x in str_adjust.split(',')]
                builder.adjust(*int_adjust)
            dp2.message.register(bot.mailer_start, Command("start"))
            dp2.chat_join_request.register(bot.chat_join_request_handler)
            dp2.message.register(bot.confirm, F.text.startswith('Підтвердити'))
            MyBotsDisp.update({me.username:dp2})
            tasks.append(asyncio.create_task(dp2.start_polling(bot.mybot)))
    async def confirm(call: CallbackQuery, state: FSMContext):
        await call.answer()
        pass
    async def select_welcome(call: CallbackQuery, state: FSMContext):
        data = call.data

        welcome = data.split('*')[0]
        bot_name = data.split('*')[1]
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        welcome_id = await BotDB.get_welcome_id_by_name(welcome, bot_id)
        bot = MyBotsDict.get(bot_name)
        mywelcome = bot.WelcomesDict.get(welcome)
        welcomebuilder = mywelcome.buttons
        welcome_text = await BotDB.get_welcome_text(welcome_id)
        manager = MyBotsDict.get('manager')

        mes = await call.message.edit_text('Зачікайте', parse_mode='Markdown')
        await manager.mybot.delete_message(call.from_user.id, mes.message_id)
        welcome_photo = await BotDB.get_welcome_photo(welcome_id)
        if welcome_photo == '0':
            mes = await call.message.answer(welcome_text, parse_mode='Markdown', reply_markup=welcomebuilder.as_markup())
        else:
            mes = await call.message.answer_photo(photo=welcome_photo, caption=welcome_text, parse_mode='Markdown', reply_markup=welcomebuilder.as_markup())
        builder = InlineKeyboardBuilder()
        builder.button(text='Змінити текст привітання', callback_data=f"{bot_name}*{welcome}*welcome_text_change")
        builder.button(text='Змінити кнопки', callback_data=f"{bot_name}*{welcome}*welcome_buttons_change")
        builder.button(text='Налаштувати затримку відправки', callback_data=f"{bot_name}*{welcome}*welcome_delay_change")
        builder.button(text='Налаштувати видалення', callback_data=f"{bot_name}*{welcome}*welcome_delete_change")
        builder.button(text='Налаштувати картинку', callback_data=f"{bot_name}*{welcome}*welcome_photo_change")
        builder.button(text='Видалити привітання', callback_data=f'{bot_name}*{welcome}*welcome_delete')
        builder.button(text='Назад', callback_data=f"{bot_name}*welcomes_menu2")
        builder.adjust(1,1)

        await state.update_data(todelete=mes)

        if await BotDB.welcome_del_is_active(welcome_id):
            await call.message.answer(f'{welcome}\n'
                                f'Затримка відправлення: {await BotDB.get_welcome_delay(welcome_id)}\n'
                                f'Видалення через: {await BotDB.get_welcome_delete(welcome_id)}', parse_mode='Markdown', reply_markup=builder.as_markup())
        else:
            await call.message.answer(f'{welcome}\n'
                                f'Затримка відправлення: {await BotDB.get_welcome_delay(welcome_id)}\n'
                                f'Видалення вимкнено', parse_mode='Markdown', reply_markup=builder.as_markup())
        await state.set_state(MyStates.WELCOME_SELECT)
    async def welcome_delete(call: CallbackQuery, state: FSMContext):
        data = call.data
        bot_name = data.split('*')[0]
        welcome = data.split('*')[1]
        data = await state.get_data()

        builder = InlineKeyboardBuilder()
        builder.button(text= 'Так', callback_data=f'{bot_name}*{welcome}*welcome_delete_yes')
        builder.button(text='Ні', callback_data=f'{bot_name}*{welcome}*welcome_delete_no')
        builder.adjust(2)
        await call.message.edit_text('Ви впевнені, що хочете видалити привітання?', parse_mode='Markdown', reply_markup=builder.as_markup())
        mes = data.get('todelete')
        await mes.delete()
    async def welcome_delete_yes(call: CallbackQuery, state: FSMContext):
        await call.answer()
        data = call.data
        welcome = data.split('*')[1]
        bot_name = data.split('*')[0]
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        welcome_id = await BotDB.get_welcome_id_by_name(welcome,bot_id)

        await BotDB.delete_welcome(welcome_id)
        bot = MyBotsDict.get(bot_name)
        index = bot.WelcomesList.index(welcome)
        bot.WelcomesList.pop(index)
        bot.WelcomesDict.pop(welcome)

        builder = InlineKeyboardBuilder()

        builder.button(text=f"Капча", callback_data=f"{bot_name}*capcha")
        list = await BotDB.get_all_welcomes_name(bot_id)
        for button in list:
            builder.button(text=f"{button}", callback_data=f"{button}*{bot_name}*")
        builder.button(text=f"➕Додати привітання", callback_data=f"{bot_name}*add_wel")
        builder.button(text=f"Назад", callback_data=f"{bot_name}*backtomenu")
        builder.adjust(1, 1)
        await call.message.edit_text(f"----------------------| Привітання |----------------------", parse_mode='Markdown', reply_markup=builder.as_markup())
    async def welcome_delete_no(call: CallbackQuery, state: FSMContext):
        data = call.data
        welcome = data.split('*')[1]
        bot_name = data.split('*')[0]
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        welcome_id = await BotDB.get_welcome_id_by_name(welcome, bot_id)
        bot = MyBotsDict.get(bot_name)
        mywelcome = bot.WelcomesDict.get(welcome)
        welcomebuilder = mywelcome.buttons
        welcome_text = await BotDB.get_welcome_text(welcome_id)
        mes = await call.message.edit_text(welcome_text, parse_mode='Markdown', reply_markup=welcomebuilder.as_markup())

        builder = InlineKeyboardBuilder()
        builder.button(text='Змінити текст привітання', callback_data=f"{bot_name}*{welcome}*welcome_text_change")
        builder.button(text='Змінити кнопки', callback_data=f"{bot_name}*{welcome}*welcome_buttons_change")
        builder.button(text='Налаштувати затримку відправки', callback_data=f"{bot_name}*{welcome}*welcome_delay_change")
        builder.button(text='Налаштувати видалення', callback_data=f"{bot_name}*{welcome}*welcome_delete_change")
        builder.button(text='Видалити привітання', callback_data=f'{bot_name}*{welcome}*welcome_delete')
        builder.button(text='Назад', callback_data=f"{bot_name}*welcomes_menu2")
        builder.adjust(1, 1)

        await state.update_data(todelete=mes)

        if await BotDB.welcome_del_is_active(welcome_id):
            await call.message.answer(f'{welcome}\n'
                                      f'Затримка відправлення: {await BotDB.get_welcome_delay(welcome_id)}\n'
                                      f'Видалення через: {await BotDB.get_welcome_delete(welcome_id)}',
                                      parse_mode='Markdown', reply_markup=builder.as_markup())
        else:
            await call.message.answer(f'{welcome}\n'
                                      f'Затримка відправлення: {await BotDB.get_welcome_delay(welcome_id)}\n'
                                      f'Видалення вимкнено', parse_mode='Markdown', reply_markup=builder.as_markup())
    async def welcome_text_change(call: CallbackQuery, state: FSMContext):
        data = call.data
        bot_name = data.split('*')[0]
        welcome = data.split('*')[1]
        data = await state.get_data()

        mes1 = await call.message.edit_text('Введіть новий текст привітання:', parse_mode='Markdown')
        mes = data.get('todelete')
        await mes.delete()

        await state.update_data(todelete=mes1, bot_name=bot_name, welcome=welcome)
        await state.set_state(MyStates.СHANGE_WELCOME_TEXT)
    async def welcome_text_change2(message: Message, state: FSMContext):
        data = await state.get_data()
        bot_name = data.get('bot_name')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        welcome = data.get('welcome')
        mes = data.get('todelete')
        welcome_id = await BotDB.get_welcome_id_by_name(welcome, bot_id)
        newtext = message.text
        await BotDB.set_welcome_text(newtext, welcome_id)
        builder = InlineKeyboardBuilder()
        builder.button(text='Продовжити',  callback_data=f"{welcome}*{bot_name}*")
        await message.answer('Текст привітання успішно змінено', parse_mode='Markdown', reply_markup=builder.as_markup())
        await mes.delete()
        await state.set_state(MyStates.WELCOME_SELECT)
    async def welcome_buttons_change(call: CallbackQuery, state: FSMContext):
        await call.answer()
        data = call.data
        bot_name = data.split('*')[0]
        welcome = data.split('*')[1]
        data = await state.get_data()

        mes1 = await call.message.edit_text(f'Щоб змінити кнопки, надішліть їх у форматі:\n\n'
                             f'Кнопка 1 - http://example1.com | Кнопка 2 - http://example2.com\n'
                             f'Кнопка 3 - http://example3.com | Кнопка 4 - http://example4.com\n'
                             f'Кнопка 1 і Кнопка 2 знаходяться в одному рядку, Кнопка 1 і Кнопка 3 в одному стовпці. Щоб не додавати кнопки, відправте 0', parse_mode='Markdown')
        mes = data.get('todelete')
        await mes.delete()

        await state.update_data(todelete=mes1, bot_name=bot_name, welcome=welcome)
        await state.set_state(MyStates.СHANGE_WELCOME_BUTTONS)
    async def welcome_buttons_change2(message: Message, state: FSMContext):
        data = await state.get_data()
        bot_name = data.get('bot_name')
        welcome = data.get('welcome')
        mes = data.get('todelete')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        bot = MyBotsDict.get(bot_name)

        bot.WelcomesDict.pop(welcome)
        button = Buttons()
        bot.WelcomesDict.update({welcome: button})
        mybuilder = button.buttons
        welcome_id = await BotDB.get_welcome_id_by_name(welcome, bot_id)
        newtext = message.text

        await BotDB.delete_buttons_by_welcome(welcome_id)
        await BotDB.set_welcome_adjust(welcome_id,'1')

        if newtext != '0':
            alltext = newtext.split('\n')
            buttons = []
            nums = []
            for allt in alltext:
                text = allt.split(' | ')
                for txt in text:
                    buttons.append(txt)
            for button1 in buttons:
                newbutton = button1.split(' - ')
                await BotDB.add_button(welcome_id, newbutton[0], newbutton[1])
                mybuilder.button(text=newbutton[0], url=newbutton[1])
            for txt in alltext:
                nums.append(len(txt.split(' | ')))

            strnums= ','.join(map(str, nums))

            await BotDB.set_welcome_adjust(welcome_id, strnums)
            mybuilder.adjust(*nums)

        builder = InlineKeyboardBuilder()
        builder.button(text='Продовжити',  callback_data=f"{welcome}*{bot_name}*")
        await message.answer('Кнопки привітання успішно змінено', parse_mode='Markdown', reply_markup=builder.as_markup())
        await mes.delete()
        await state.set_state(MyStates.WELCOME_SELECT)
    async def welcome_delay_change(call: CallbackQuery, state: FSMContext):
        data = call.data
        bot_name = data.split('*')[0]
        welcome = data.split('*')[1]
        data = await state.get_data()

        mes1 = await call.message.edit_text(f'Введіть нову затримку відправки у форматі 10h10m10s\n'
                                    f'Щоб відправити одразу введіть 0', parse_mode='Markdown')
        mes = data.get('todelete')
        await mes.delete()

        await state.update_data(todelete=mes1, bot_name=bot_name, welcome=welcome)
        await state.set_state(MyStates.СHANGE_WELCOME_DELAY)
    async def welcome_delay_change2(message: Message, state: FSMContext):
        data = await state.get_data()
        bot_name = data.get('bot_name')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        welcome = data.get('welcome')
        mes = data.get('todelete')
        welcome_id = await BotDB.get_welcome_id_by_name(welcome, bot_id)
        newtext = message.text

        if newtext == '0':
            await BotDB.set_welcome_delay(welcome_id, "now")
            builder = InlineKeyboardBuilder()
            builder.button(text='Продовжити', callback_data=f"{welcome}*{bot_name}*")
            await message.answer('Затримку відправки привітання успішно змінено', parse_mode='Markdown',
                                 reply_markup=builder.as_markup())
            await mes.delete()
            await state.set_state(MyStates.WELCOME_SELECT)
        else:
            await BotDB.set_welcome_delay(welcome_id, newtext)
            builder = InlineKeyboardBuilder()
            builder.button(text='Продовжити', callback_data=f"{welcome}*{bot_name}*")
            await message.answer('Затримку відправки привітання успішно змінено', parse_mode='Markdown',
                                 reply_markup=builder.as_markup())
            await mes.delete()
            await state.set_state(MyStates.WELCOME_SELECT)
    async def welcome_delete_change(call: CallbackQuery, state: FSMContext):
        data = call.data
        bot_name = data.split('*')[0]
        welcome = data.split('*')[1]
        data = await state.get_data()

        mes1 = await call.message.edit_text(f'Введіть новий час, через який видалиться привітання у форматі 10h10m10s\n'
                                    f'Щоб не видаляти привітання введіть 0', parse_mode='Markdown')
        mes = data.get('todelete')
        await mes.delete()

        await state.update_data(todelete=mes1, bot_name=bot_name, welcome=welcome)
        await state.set_state(MyStates.CHANGE_WELCOME_DELETE)
    async def welcome_delete_change2(message: Message, state: FSMContext):
        data = await state.get_data()
        bot_name = data.get('bot_name')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        welcome = data.get('welcome')
        mes = data.get('todelete')
        welcome_id = await BotDB.get_welcome_id_by_name(welcome, bot_id)
        newtext = message.text

        if newtext == '0':
            await BotDB.delete_off(welcome_id)
            await BotDB.set_welcome_delete(welcome_id, "0:0:0")
            builder = InlineKeyboardBuilder()
            builder.button(text='Продовжити', callback_data=f"{welcome}*{bot_name}*")
            await message.answer('Видалення привітання успішно змінено', parse_mode='Markdown',
                                 reply_markup=builder.as_markup())
            await mes.delete()
            await state.set_state(MyStates.WELCOME_SELECT)
        else:
            await BotDB.delete_on(welcome_id)
            await BotDB.set_welcome_delete(welcome_id, newtext)
            builder = InlineKeyboardBuilder()
            builder.button(text='Продовжити', callback_data=f"{welcome}*{bot_name}*")
            await message.answer('Видалення привітання успішно змінено', parse_mode='Markdown',
                                 reply_markup=builder.as_markup())
            await mes.delete()
            await state.set_state(MyStates.WELCOME_SELECT)
    async def welcome_photo_change(call: CallbackQuery, state: FSMContext):
        data = call.data
        bot_name = data.split('*')[0]
        welcome = data.split('*')[1]
        data = await state.get_data()

        mes1 = await call.message.edit_text(f'Відправте нову картинку для привітання, щоб не додавати картинку відправте 0', parse_mode='Markdown')
        mes = data.get('todelete')
        await mes.delete()

        await state.update_data(todelete=mes1, bot_name=bot_name, welcome=welcome)
        await state.set_state(MyStates.СHANGE_WELCOME_PHOTO)
    async def welcome_photo_change2(message: Message, state: FSMContext):
        data = await state.get_data()
        bot_name = data.get('bot_name')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        welcome = data.get('welcome')
        welcome_id = await BotDB.get_welcome_id_by_name(welcome, bot_id)
        await BotDB.add_welcome_photo(welcome_id)
        if message.text == '0':
            photo = '0'
            await BotDB.set_welcome_photo(welcome_id, photo)
            await BotDB.delete_welcome_photo_by_welcome(welcome_id)
            builder = InlineKeyboardBuilder()
            builder.button(text='Продовжити', callback_data=f'{bot_name}*welcomes')
            await message.answer(f'Привітання успішно настроєно', parse_mode='Markdown',
                                 reply_markup=builder.as_markup())
            mes = data.get('todelete')
            await mes.delete()
            await state.set_state(MyStates.WELCOME_SELECT)
        else:
            try:
                bot = MyBotsDict.get('manager')
                photo = message.photo[-1].file_id
                file_info = await bot.mybot.get_file(photo)
                photo_url = file_info.file_path
                photo_data = await bot.mybot.download_file(photo_url)
                if isinstance(photo_data, io.BytesIO):
                    photo_data = photo_data.read()

                await BotDB.set_welcome_photo2(photo_data, welcome_id)
                await BotDB.set_welcome_photo(welcome_id, photo)
                builder = InlineKeyboardBuilder()
                builder.button(text='Продовжити', callback_data=f'{bot_name}*welcomes')
                await message.answer(f'Привітання успішно настроєно', parse_mode='Markdown',
                                     reply_markup=builder.as_markup())
                mes = data.get('todelete')
                await mes.delete()
                await state.set_state(MyStates.WELCOME_SELECT)
            except:
                mes1 = await message.answer(
                    f'Неправильний формат повідомлення, ще раз відправте картинку для привітання, щоб не додавати картинку відправте 0',
                    parse_mode='Markdown')
                mes = data.get('todelete')
                await mes.delete()
                await state.update_data(bot_name=bot_name, newwelcome=welcome, todelete=mes1)
    async def spam_menu(call: CallbackQuery, state: FSMContext):
        data = call.data
        bot_name = data.split('*')[0]
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        if await BotDB.subscribe_is_active(bot_id):
            builder = InlineKeyboardBuilder()

            builder.button(text=f"➕Додати розсилку", callback_data=f"{bot_name}*spam_start")
            builder.button(text=f"Назад", callback_data=f"{bot_name}")
            builder.adjust(1, 1)
            await call.message.edit_text(f"----------------------| Розсилка |----------------------",
                                         parse_mode='Markdown', reply_markup=builder.as_markup())
        else:
            await call.answer("Підписка неактивна")
    async def spam_start(call: CallbackQuery, state: FSMContext):
        data = call.data
        bot_name = data.split('*')[0]
        bot_id = await BotDB.get_bot_id_by_name(bot_name)

        mes = await call.message.edit_text(f"Введіть текст нової розсилки:",parse_mode='Markdown')
        await state.update_data(bot_name=bot_name, todelete=mes)
        await state.set_state(MyStates.NEW_SPAM_TEXT)
    async def new_spam_text(message: Message, state: FSMContext):
        data = await state.get_data()
        bot_name = data.get('bot_name')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        newtext = message.text

        spam_id = await BotDB.add_spam(bot_id, newtext)
        mes1 = await message.answer(f'Додайте кнопки в форматі:\n\n'
                                    f'Кнопка 1 - http://example1.com | Кнопка 2 - http://example2.com\n'
                                    f'Кнопка 3 - http://example3.com | Кнопка 4 - http://example4.com\n'
                                    f'Кнопка 1 і Кнопка 2 знаходяться в одному рядку, Кнопка 1 і Кнопка 3 в одному стовпці. Щоб не додавати кнопки, відправте 0',
                                    parse_mode='Markdown')
        mes = data.get('todelete')
        await mes.delete()
        await state.update_data(bot_name=bot_name, todelete=mes1, spam_id=spam_id)
        await state.set_state(MyStates.NEW_SPAM_BUTTON)
    async def new_spam_button(message: Message, state: FSMContext):
        newtext = message.text
        data = await state.get_data()
        bot_name = data.get('bot_name')
        spam_id = int(data.get('spam_id'))
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        bot = MyBotsDict.get(bot_name)
        nums = [1]
        builder = InlineKeyboardBuilder()
        if newtext != '0':
            alltext = newtext.split('\n')
            buttons = []
            nums = []
            for allt in alltext:
                text = allt.split(' | ')
                for txt in text:
                    buttons.append(txt)
            for button1 in buttons:
                newbutton = button1.split(' - ')
                builder.button(text=newbutton[0], url=newbutton[1])
            for txt in alltext:
                nums.append(len(txt.split(' | ')))
        builder.adjust(*nums)
        bot.spam_builder.update({spam_id:builder})
        mes1 = await message.answer(f'Введіть час, коли буде зроблено розсилку у форматі 10h10m10s\n'
                             f'Щоб відправити одразу введіть 0', parse_mode='Markdown')
        mes = data.get('todelete')
        await mes.delete()
        await state.update_data(bot_name=bot_name, todelete=mes1, spam_id=spam_id)
        await state.set_state(MyStates.NEW_SPAM_DELAY)
    async def new_spam_delay(message: Message, state: FSMContext):
        newtext = message.text
        data = await state.get_data()
        bot_name = data.get('bot_name')
        spam_id = data.get('spam_id')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        if newtext == '0':
            await BotDB.set_spam_delay(bot_id, "now")
            mes = data.get('todelete')
            mes1 = await message.answer(f'Відправте картинку для розсилки, щоб не додавати картинку відправте 0',
                                        parse_mode='Markdown')
            await mes.delete()
            await state.update_data(bot_name=bot_name, todelete=mes1, spam_id=spam_id)
            await state.set_state(MyStates.NEW_SPAM_PHOTO)
        else:
            await BotDB.set_spam_delay(bot_id, newtext)
            mes = data.get('todelete')
            mes1 = await message.answer(f'Відправте картинку для розсилки, щоб не додавати картинку відправте 0',
                                        parse_mode='Markdown')
            await mes.delete()
            await state.update_data(bot_name=bot_name, todelete=mes1, spam_id=spam_id)
            await state.set_state(MyStates.NEW_SPAM_PHOTO)
    async def new_spam_photo(message: Message, state: FSMContext):
        data = await state.get_data()
        bot_name = data.get('bot_name')
        spam_id = data.get('spam_id')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        await BotDB.add_spam_photo(spam_id)

        if message.text == '0':
            photo = '0'
            await BotDB.set_spam_photo2(photo,spam_id)
            mes1 = await message.answer(f'Введіть час, через який буде видалено розсилку у форматі 10h10m10s', parse_mode='Markdown')
            mes = data.get('todelete')
            await mes.delete()
            await state.update_data(bot_name=bot_name, todelete=mes1, spam_id=spam_id)
            await state.set_state(MyStates.NEW_SPAM_DELETE)
        else:
            try:
                bot = MyBotsDict.get('manager')
                photo = message.photo[-1].file_id
                file_info = await bot.mybot.get_file(photo)
                photo_url = file_info.file_path
                photo_data = await bot.mybot.download_file(photo_url)
                if isinstance(photo_data, io.BytesIO):
                    photo_data = photo_data.read()
                await BotDB.set_spam_photo2(photo_data, spam_id)
                mes1 = await message.answer(f'Введіть час, через який буде видалено розсилку у форматі 10h10m10s', parse_mode='Markdown')
                mes = data.get('todelete')
                await mes.delete()
                await state.update_data(bot_name=bot_name, todelete=mes1, spam_id=spam_id)
                await state.set_state(MyStates.NEW_SPAM_DELETE)
            except:
                mes1 = await message.answer(f'Неправильний формат повідомлення, ще раз відправте картинку для розсилки, щоб не додавати картинку відправте 0',parse_mode='Markdown')
                mes = data.get('todelete')
                await mes.delete()
                await state.update_data(bot_name=bot_name, todelete=mes1, spam_id=spam_id)
    async def new_spam_delete(message: Message, state: FSMContext):
        newtext = message.text
        data = await state.get_data()
        bot_name = data.get('bot_name')
        spam_id = data.get('spam_id')
        bot_id = await BotDB.get_bot_id_by_name(bot_name)
        time_pattern = re.compile(r'^([0-1][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])$')


        await BotDB.set_spam_delete(bot_id, newtext)
        builder = InlineKeyboardBuilder()
        admin_id = await BotDB.bot_get_admin(bot_id)

        bot_names = await BotDB.get_bot_names_by_admin(admin_id)
        for bot_name in bot_names:
            builder.button(text=f"{bot_name}", callback_data=f"{bot_name}*{bot_id}*{spam_id}*solo_spam")
        builder.button(text=f"Мульти-розсилка", callback_data=f"{bot_id}*{spam_id}*multi_spam")
        builder.button(text=f"Відмінити розсилку", callback_data=bot_name)
        builder.adjust(1, 1)
        mes1 = await message.answer(f'----------------| Бот для розсилки |----------------', parse_mode='Markdown', reply_markup=builder.as_markup())
        mes = data.get('todelete')
        await mes.delete()
        await state.update_data(todelete=mes1)
        await state.set_state(MyStates.START)
    async def solo_spam(call: CallbackQuery, state: FSMContext):
        await call.answer()
        scheduler = AsyncIOScheduler()
        data = call.data
        bot_name = data.split('*')[0]
        bot_id_main = data.split('*')[1]
        spam_id = int(data.split('*')[2])
        bot = MyBotsDict.get(bot_name)

        delay_time = await BotDB.get_spam_delay(bot_id_main, spam_id)
        if delay_time == 'now':
            scheduler.add_job(Manager.send_message, trigger='date',
                              run_date=datetime.now() + timedelta(seconds=5),
                              kwargs={'bot': bot, 'bot_id_main': bot_id_main, 'spam_id': spam_id})
        else:
            h, m, s = await Manager.parse_time_input(delay_time)
            timenow = datetime.now().replace(hour=h, minute=m, second=s)
            if timenow < datetime.now():
                timenow += timedelta(days=1)
            scheduler.add_job(Manager.send_message, trigger='date',
                              run_date=timenow,
                              kwargs={'bot': bot, 'bot_id_main': bot_id_main, 'spam_id': spam_id})

        scheduler.start()
        await Manager.select_bot(call, state)
    async def multi_spam(call: CallbackQuery, state: FSMContext):
        await call.answer()
        scheduler = AsyncIOScheduler()
        data = call.data
        bot_id_main = data.split('*')[0]
        spam_id = int(data.split('*')[1])
        admin_id = await BotDB.bot_get_admin(bot_id_main)
        bots = await BotDB.get_bots_by_admin(admin_id)
        delay_time = await BotDB.get_spam_delay(bot_id_main, spam_id)
        for _bot in bots:
            bot_name = await BotDB.bot_get_name(_bot)
            bot = MyBotsDict.get(bot_name)
            if delay_time == 'now':
                scheduler.add_job(Manager.send_message, trigger='date',
                                  run_date=datetime.now() + timedelta(seconds=5),
                                  kwargs={'bot': bot, 'bot_id_main': bot_id_main, 'spam_id': spam_id})
            else:
                h, m, s = await Manager.parse_time_input(delay_time)
                timenow = datetime.now().replace(hour=h, minute=m, second=s)
                if timenow < datetime.now():
                    timenow += timedelta(days=1)
                scheduler.add_job(Manager.send_message, trigger='date',
                                  run_date=timenow,
                                  kwargs={'bot': bot, 'bot_id_main': bot_id_main, 'spam_id': spam_id})

        scheduler.start()
        await Manager.select_bot(call, state)
    async def send_message(bot: Mailer, bot_id_main: int, spam_id: int):
        scheduler = AsyncIOScheduler()

        text_template = await BotDB.get_spam_text(bot_id_main, spam_id)
        bot_name_main = await BotDB.bot_get_name(bot_id_main)
        bot_main = MyBotsDict.get(bot_name_main)

        builder = bot_main.spam_builder.get(spam_id)
        bot_id = await BotDB.get_bot_id_by_name(bot.name)
        users = await BotDB.get_users_by_bot_id(bot_id)
        delete_time = await BotDB.get_spam_delete(bot_id_main,spam_id)
        h, m, s = await Manager.parse_time_input(delete_time)
        for user_id in users:
            try:
                user = await bot.mybot.get_chat(user_id)
                user_info = {
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                }
                text = await Manager.replace_placeholders(text_template, user_info)
                photo_data = await BotDB.get_spam_photo2(spam_id)
                if photo_data == '0':
                    mes = await bot.mybot.send_message(user_id, text, parse_mode='Markdown', reply_markup=builder.as_markup())
                else:
                    photo = types.BufferedInputFile(file=photo_data, filename='name')
                    mes = await bot.mybot.send_photo(chat_id=user_id, photo=photo, caption=text, parse_mode='Markdown',reply_markup=builder.as_markup())
                scheduler.add_job(Manager.delete_message, trigger='date',
                                  run_date=datetime.now() + timedelta(hours=h, minutes=m, seconds=s),
                                  kwargs={'message': mes, 'bot_id_main': bot_id_main, 'spam_id': spam_id})
            except aiogram.exceptions.TelegramForbiddenError:
                await BotDB.user_delete(bot_id, user)
        scheduler.start()
    async def replace_placeholders(text_template, user_info):
        placeholders = {
            '{id}': user_info.get('id', 'unknown'),
            '{username}': user_info.get('username', 'unknown'),
            '{fname}': user_info.get('first_name', 'unknown'),
            '{lname}': user_info.get('last_name', 'unknown'),
            '{fullname}': f"{user_info.get('first_name', 'unknown')} {user_info.get('last_name', 'unknown')}"
        }

        for placeholder, value in placeholders.items():
            text_template = text_template.replace(placeholder, str(value))

        return text_template
    async def delete_message(message: Message, bot_id_main: int, spam_id: int):
        bot_name = await BotDB.bot_get_name(bot_id_main)
        bot = MyBotsDict.get(bot_name)
        bot.spam_builder.pop(spam_id, None)
        await BotDB.delete_spam(spam_id)
        await message.delete()
    async def parse_time_input(input_str):
        time_pattern = re.compile(r'(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s)?')
        match = time_pattern.match(input_str)

        if match:
            groups = match.groupdict()
            hours = int(groups['hours']) if groups['hours'] else 0
            minutes = int(groups['minutes']) if groups['minutes'] else 0
            seconds = int(groups['seconds']) if groups['seconds'] else 0

        return hours, minutes, seconds