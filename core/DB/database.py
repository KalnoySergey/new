import pytz
import asyncio
import sqlite3
from datetime import datetime, timedelta
import io

class BotDB:
    """Constructor"""

    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()


    """Admins methods"""

    async def admin_exist(self, admin_id):
        self.cursor.execute("SELECT id FROM admins WHERE admin_id = ?", (admin_id,))
        result = self.cursor.fetchall()
        return bool(result)
    async def admin_del(self, admin_id):
        if await self.admin_exist(admin_id):
            self.cursor.execute("DELETE FROM admins WHERE admin_id = ?", (admin_id,))
            return self.conn.commit()
    async def admin_add_with_role(self, admin_id, role):
        if(not await self.admin_exist(admin_id)):
            self.cursor.execute("INSERT INTO admins (admin_id, role) VALUES (?, ?)", (admin_id, role))
            return self.conn.commit()
    async def admin_add(self, admin_id):
        if not await self.admin_exist(admin_id):
            self.cursor.execute("INSERT INTO admins (admin_id) VALUES (?)", (admin_id,))
            return self.conn.commit()
    async def admin_get_role(self, admin_id):
        if await self.admin_exist(admin_id):
            self.cursor.execute("SELECT role FROM admins WHERE admin_id = ?", (admin_id,))
            result = self.cursor.fetchone()
            return result[0]
    async def switch_admin(self, admin_id1, admin_id2):
        if await self.admin_exist(admin_id1):
            await self.admin_del(admin_id2)
            self.cursor.execute("UPDATE admins SET admin_id = ? WHERE admin_id = ?", (admin_id2, admin_id1))
            self.cursor.execute("UPDATE bots SET admin_id = ? WHERE admin_id = ?", (admin_id2, admin_id1))
            return self.conn.commit()
    async def del_all_from_admins(self):
        self.cursor.execute("DELETE FROM admins")
        return self.conn.commit()
    async def admin_has_bots(self, admin_id):
        self.cursor.execute("SELECT COUNT(*) FROM bots WHERE admin_id = ?", (admin_id,))
        result = self.cursor.fetchone()
        return result[0] > 0 if result else False


    """Bots methods"""

    async def bot_exist(self, bot_id):
        self.cursor.execute("SELECT id FROM bots WHERE bot_id = ?", (bot_id,))
        result = self.cursor.fetchall()
        return bool(result)
    async def bot_exist_name(self, bot_name):
        self.cursor.execute("SELECT id FROM bots WHERE name = ?", (bot_name,))
        result = self.cursor.fetchall()
        return bool(result)
    async def bot_add(self, admin_id, bot_id, token, name):
        if not await self.bot_exist(bot_id):
            self.cursor.execute("INSERT INTO bots (admin_id, bot_id, token, name) VALUES (?, ?, ?, ?)", (admin_id, bot_id, token, name))
            return self.conn.commit()
    async def bot_delete(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute("DELETE FROM bots WHERE bot_id = ?", (bot_id,))
            return self.conn.commit()
    async def bot_get_name(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute("SELECT name FROM bots WHERE bot_id = ?", (bot_id,))
            result = self.cursor.fetchone()
            return result[0]
    async def bot_get_capcha(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute("SELECT capcha_text FROM bots WHERE bot_id = ?", (bot_id,))
            result = self.cursor.fetchone()
            return result[0]
    async def capcha_is_active(self, bot_id):
        self.cursor.execute("SELECT capcha_active FROM bots WHERE bot_id = ?", (bot_id,))
        result = self.cursor.fetchone()
        return bool(result[0])
    async def capcha_on(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute("UPDATE bots SET capcha_active = True WHERE bot_id = ?", (bot_id,))
            return self.conn.commit()
    async def capcha_off(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute("UPDATE bots SET capcha_active = False WHERE bot_id = ?", (bot_id,))
            return self.conn.commit()
    async def set_capha(self, bot_id, newtext):
        if await self.bot_exist(bot_id):
            self.cursor.execute("UPDATE bots SET capcha_text = ? WHERE bot_id = ?", (newtext, bot_id))
            return self.conn.commit()
    async def switch_capcha(self, bot_id):
        if await self.bot_exist(bot_id):
            if await self.capcha_is_active(bot_id):
                await self.capcha_off(bot_id)
            else:
                await self.capcha_on(bot_id)
    async def bot_get_admin(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute("SELECT admin_id FROM bots WHERE bot_id = ?", (bot_id,))
            result = self.cursor.fetchone()
            return result[0]
    async def get_bots_by_admin(self, admin_id):
        if await self.admin_exist(admin_id) and await self.admin_has_bots(admin_id):
            self.cursor.execute("SELECT bot_id FROM bots WHERE admin_id = ?", (admin_id,))
            result = self.cursor.fetchall()
            bot_ids = [bot_id[0] for bot_id in result]
            return bot_ids

    async def set_bot_days_0(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute("UPDATE bots SET days = 0 WHERE bot_id = ?", (bot_id,))
            return self.conn.commit()
    async def subscribe_on(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute("UPDATE bots SET payed = True WHERE bot_id = ?", (bot_id,))
            return self.conn.commit()
    async def subscribe_off(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute("UPDATE bots SET payed = False WHERE bot_id = ?", (bot_id,))
            return self.conn.commit()
    async def switch_subscribe(self, bot_id):
        if await self.bot_exist(bot_id):
            if await self.subscribe_is_active(bot_id):
                await self.subscribe_off(bot_id)
            else:
                await self.subscribe_on(bot_id)
    async def subscribe_is_active(self, bot_id):
        self.cursor.execute("SELECT payed FROM bots WHERE bot_id = ?", (bot_id,))
        result = self.cursor.fetchone()
        return bool(result[0])
    async def get_bot_id_by_name(self, name):
        if await self.bot_exist_name(name):
            self.cursor.execute("SELECT bot_id FROM bots WHERE name = ?", (name,))
            result = self.cursor.fetchone()
            return result[0]
    async def check_subscription_status(self, bot_id):
        if await self.bot_exist(bot_id):
            if await self.admin_get_role(await self.bot_get_admin(bot_id)) == 'Admin':
                self.cursor.execute("SELECT payed FROM bots WHERE bot_id = ?", (bot_id,))
                result = self.cursor.fetchone()
                if result:
                    payed = result[0]
                    if payed:
                        current_date_utc = datetime.utcnow()
                        if current_date_utc >= await self.get_subscription_end_date(bot_id):
                            await self.subscribe_off(bot_id)
                            await self.set_bot_days_0(bot_id)
                            return False
                        else:
                            return True
            else:
                pass
    async def get_subscription_end_date(self, bot_id):
        if await self.bot_exist(bot_id) and await self.subscribe_is_active(bot_id):
            self.cursor.execute("SELECT date, days FROM bots WHERE bot_id = ?", (bot_id,))
            result = self.cursor.fetchone()

            if result:
                date_str, days = result
                subscription_date_utc = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                end_date_utc = subscription_date_utc + timedelta(days=days)
                final_date = (end_date_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

                return final_date
        return None
    async def continue_subscribe(self,  bot_id, month):
        if await self.bot_exist(bot_id):
            self.cursor.execute("SELECT date, days FROM bots WHERE bot_id = ?", (bot_id,))
            result = self.cursor.fetchone()

            if result:
                date_str, days = result
                subscription_date_utc = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                end_date_utc = subscription_date_utc + timedelta(days=days)
                final_date = (end_date_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                diff = final_date - subscription_date_utc
                diff = round(diff.total_seconds() / (60 * 60 * 24))
                res = ((month * 30) + diff) - 1
                new_date = datetime.utcnow()
                new_date = new_date.replace(microsecond=0)
                self.cursor.execute("UPDATE bots SET days = ? WHERE bot_id = ?", (res, bot_id))
                self.cursor.execute("UPDATE bots SET date = ? WHERE bot_id = ?", (new_date, bot_id))
                return self.conn.commit()
    async def get_bot_names_by_admin(self, admin_id):
        if await self.admin_exist(admin_id) and await self.admin_has_bots(admin_id):
            self.cursor.execute("SELECT name FROM bots WHERE admin_id = ?", (admin_id,))
            result = self.cursor.fetchall()
            bot_names = [bot[0] for bot in result]
            return bot_names
        else:
            return []
    async def get_all_bot_tokens(self):
        self.cursor.execute("SELECT token FROM bots")
        result = self.cursor.fetchall()
        bot_tokens = [token[0] for token in result]
        return bot_tokens
    async def del_all_from_bots(self):
        self.cursor.execute("DELETE FROM bots")
        return self.conn.commit()

    """Users methods"""


    async def user_exist(self, bot_id, user_id):
        self.cursor.execute("SELECT id FROM users WHERE bot_id = ? AND user_id = ?", (bot_id, user_id))
        result = self.cursor.fetchall()
        return bool(result)
    async def user_add(self, bot_id, user_id, language):
        if not await self.user_exist(bot_id, user_id):
            self.cursor.execute("INSERT INTO users (bot_id, user_id, language) VALUES (?, ?, ?)", (bot_id, user_id, language))
            return self.conn.commit()
    async def user_delete(self, bot_id, user_id):
        if await self.user_exist(bot_id, user_id):
            self.cursor.execute("DELETE FROM users WHERE bot_id = ? AND user_id = ?", (bot_id, user_id))
            return self.conn.commit()
    async def user_added_today(self, bot_id):
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('SELECT COUNT(*) FROM users WHERE bot_id = ? AND date >= ?', (bot_id, today_start))
        result = self.cursor.fetchone()
        return result[0] if result else 0
    async def user_added_yesterday(self, bot_id):
        yesterday_start = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        yesterday_end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('SELECT COUNT(*) FROM users WHERE bot_id = ? AND date >= ? AND date < ?', (bot_id, yesterday_start, yesterday_end))
        result = self.cursor.fetchone()
        return result[0] if result else 0
    async def user_added_last_week(self, bot_id):
        week_start = (datetime.now() - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('SELECT COUNT(*) FROM users WHERE bot_id = ? AND date >= ?', (bot_id, week_start))
        result = self.cursor.fetchone()
        return result[0] if result else 0
    async def user_get_language(self, bot_id, user_id):
        self.cursor.execute("SELECT language FROM users WHERE bot_id = ? AND user_id = ?", (bot_id, user_id))
        result = self.cursor.fetchone()
        return result[0]
    async def get_users_by_bot_id(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute('SELECT user_id FROM users WHERE bot_id = ?', (bot_id,))
            array = []
            result = self.cursor.fetchall()
            for user in result:
                array.append(user[0])
            return array
    async def get_user_count(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE bot_id = ?', (bot_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        else:
            return 0
    async def get_user_uk_count(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE bot_id = ? AND language = "uk"', (bot_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        else:
            return 0
    async def get_user_ru_count(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE bot_id = ? AND language = "ru"', (bot_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        else:
            return 0
    async def get_user_en_count(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE bot_id = ? AND language = "en"', (bot_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        else:
            return 0
    async def del_all_from_users(self):
        self.cursor.execute("DELETE FROM users")
        return self.conn.commit()

    """Welcomes methods"""

    async def get_all_welcomes_name(self, bot_id):
        if await self.bot_exist(bot_id):
            self.cursor.execute('SELECT welcome_name FROM welcomes WHERE bot_id = ?', (bot_id,))
            result = self.cursor.fetchall()
            welcome_names = [name[0] for name in result]
            return welcome_names
    async def add_welcome(self, bot_id, name, text):
        if await self.bot_exist(bot_id):
            self.cursor.execute("INSERT INTO welcomes (welcome_name, bot_id, text) VALUES (?, ?, ?)",(name, bot_id, text))
            return self.conn.commit()
    async def get_welcome_id_by_name(self, name, bot_id):
        self.cursor.execute("SELECT id FROM welcomes WHERE welcome_name = ? AND bot_id = ?", (name, bot_id))
        result = self.cursor.fetchone()
        return result[0]
    async def get_welcome_text(self, welcome_id):
        self.cursor.execute("SELECT text FROM welcomes WHERE id = ?", (welcome_id,))
        result = self.cursor.fetchone()
        return result[0]
    async def set_welcome_text(self, text, welcome_id):
        self.cursor.execute("UPDATE welcomes SET text = ? WHERE id = ?", (text, welcome_id))
        return self.conn.commit()
    async def set_welcome_delay(self, welcome_id, delay):
        self.cursor.execute("UPDATE welcomes SET delay_time = ? WHERE id = ?", (delay, welcome_id))
        return self.conn.commit()
    async def set_welcome_delete(self, welcome_id, delete):
        self.cursor.execute("UPDATE welcomes SET delete_time = ? WHERE id = ?", (delete, welcome_id))
        return self.conn.commit()
    async def set_welcome_photo(self, welcome_id, photo):
        self.cursor.execute("UPDATE welcomes SET welcome_photo = ? WHERE id = ?", (photo, welcome_id))
        return self.conn.commit()
    async def delete_on(self, welcome_id):
        self.cursor.execute("UPDATE welcomes SET isdelete = True WHERE id = ?", (welcome_id,))
        return self.conn.commit()
    async def delete_off(self, welcome_id):
        self.cursor.execute("UPDATE welcomes SET isdelete = False WHERE id = ?", (welcome_id,))
        return self.conn.commit()
    async def welcome_del_is_active(self, welcome_id):
        self.cursor.execute("SELECT isdelete FROM welcomes WHERE id = ?", (welcome_id,))
        result = self.cursor.fetchone()
        return bool(result[0])
    async def get_welcome_delay(self, welcome_id):
        self.cursor.execute("SELECT delay_time FROM welcomes WHERE id = ?", (welcome_id,))
        result = self.cursor.fetchone()
        return result[0]
    async def get_welcome_delete(self, welcome_id):
        self.cursor.execute("SELECT delete_time FROM welcomes WHERE id = ?", (welcome_id,))
        result = self.cursor.fetchone()
        return result[0]
    async def get_welcome_photo(self, welcome_id):
        self.cursor.execute("SELECT welcome_photo FROM welcomes WHERE id = ?", (welcome_id,))
        result = self.cursor.fetchone()
        return result[0]

    async def set_welcome_adjust(self, welcome_id, adjust):
        self.cursor.execute("UPDATE welcomes SET adjust = ? WHERE id = ?", (adjust, welcome_id))
        return self.conn.commit()
    async def get_welcome_adjust(self, welcome_id):
        self.cursor.execute("SELECT adjust FROM welcomes WHERE id = ?", (welcome_id,))
        result = self.cursor.fetchone()
        return result[0]
    async def delete_welcome(self, welcome_id):
        await self.delete_buttons_by_welcome(welcome_id)
        await self.delete_welcome_photo_by_welcome(welcome_id)
        self.cursor.execute("DELETE FROM welcomes WHERE id = ?", (welcome_id,))
        return self.conn.commit()
    async def del_all_from_welcomes(self):
        await self.del_all_from_buttons()
        await self.del_all_from_welcome_photos()
        self.cursor.execute("DELETE FROM welcomes")
        return self.conn.commit()


    """Buttons methods"""
    async def add_button(self, welcome_id, text, url):
        self.cursor.execute("INSERT INTO buttons (welcome_id, text, url) VALUES (?, ?, ?)",(welcome_id, text, url))
        return self.conn.commit()
    async def delete_buttons_by_welcome(self, welcome_id):
        self.cursor.execute("DELETE FROM buttons WHERE welcome_id = ?", (welcome_id,))
        return self.conn.commit()
    async def del_all_from_buttons(self):
        self.cursor.execute("DELETE FROM buttons")
        return self.conn.commit()
    async def get_all_buttons_text(self, welcome_id):
        self.cursor.execute("SELECT text FROM buttons WHERE welcome_id = ?", (welcome_id,))
        result = self.cursor.fetchall()
        buttons_text = [but[0] for but in result]
        return buttons_text
    async def get_all_buttons_url(self, welcome_id):
        self.cursor.execute("SELECT url FROM buttons WHERE welcome_id = ?", (welcome_id,))
        result = self.cursor.fetchall()
        buttons_url = [url[0] for url in result]
        return buttons_url


    """Spams methods"""

    async def add_spam(self, bot_id, text):
        if await self.bot_exist(bot_id):
            self.cursor.execute("INSERT INTO spams (bot_id, text) VALUES (?, ?)",(bot_id, text))
            self.conn.commit()
            last_inserted_id = self.cursor.lastrowid
            return last_inserted_id
    async def del_all_from_spams(self):
        await self.del_all_from_spam_photos()
        self.cursor.execute("DELETE FROM spams")
        return self.conn.commit()
    async def get_spam_text(self, bot_id, spam_id):
        self.cursor.execute("SELECT text FROM spams WHERE bot_id = ? AND id = ?", (bot_id, spam_id))
        result = self.cursor.fetchone()
        return result[0]
    async def set_spam_delay(self, bot_id, delay):
        self.cursor.execute("UPDATE spams SET send_time = ? WHERE bot_id = ?", (delay, bot_id))
        return self.conn.commit()
    async def set_spam_delete(self, bot_id, delete):
        self.cursor.execute("UPDATE spams SET delete_time = ? WHERE bot_id = ?", (delete, bot_id))
        return self.conn.commit()
    async def del_spam_by_bot_id(self, bot_id):
        self.cursor.execute("DELETE FROM spams WHERE bot_id = ?",(bot_id,))
        return self.conn.commit()
    async def get_spam_delay(self, bot_id, spam_id):
        self.cursor.execute("SELECT send_time FROM spams WHERE bot_id = ? AND id = ?", (bot_id, spam_id))
        result = self.cursor.fetchone()
        return result[0]
    async def get_spam_delete(self, bot_id, spam_id):
        self.cursor.execute("SELECT delete_time FROM spams WHERE bot_id = ? AND id = ?", (bot_id, spam_id))
        result = self.cursor.fetchone()
        return result[0]
    async def delete_spam(self, last_inserted_id):
        await self.delete_spam_photo_by_spam(last_inserted_id)
        self.cursor.execute("DELETE FROM spams WHERE id = ?", (last_inserted_id,))
        return self.conn.commit()


    """Welcome_photo methods"""
    async def welcome_photo_exist(self, welcome_id):
        self.cursor.execute("SELECT id FROM welcome_photos WHERE welcome_id = ?", (welcome_id,))
        result = self.cursor.fetchall()
        return bool(result)
    async def add_welcome_photo(self, welcome_id):
        if not await self.welcome_photo_exist(welcome_id):
            self.cursor.execute("INSERT INTO welcome_photos (welcome_id) VALUES ( ?)",(welcome_id,))
            self.conn.commit()
            return self.conn.commit()
    async def get_welcome_photo2(self, welcome_id):
        self.cursor.execute("SELECT photo FROM welcome_photos WHERE welcome_id = ?", (welcome_id,))
        result = self.cursor.fetchone()
        return result[0]
    async def set_welcome_photo2(self, photo_data, welcome_id):
        self.cursor.execute("UPDATE welcome_photos SET photo = ? WHERE welcome_id = ?", (photo_data, welcome_id))
        return self.conn.commit()
    async def delete_welcome_photo(self, photo_id):
        self.cursor.execute("DELETE FROM welcome_photos WHERE id = ?", (photo_id,))
        return self.conn.commit()
    async def delete_welcome_photo_by_welcome(self, welcome_id):
        self.cursor.execute("DELETE FROM welcome_photos WHERE welcome_id = ?", (welcome_id,))
        return self.conn.commit()
    async def del_all_from_welcome_photos(self):
        self.cursor.execute("DELETE FROM welcome_photos")
        return self.conn.commit()

    """Spam_photo methods"""

    async def spam_photo_exist(self, spam_id):
        self.cursor.execute("SELECT id FROM spam_photos WHERE spam_id = ?", (spam_id,))
        result = self.cursor.fetchall()
        return bool(result)
    async def add_spam_photo(self, spam_id):
        if not await self.spam_photo_exist(spam_id):
            self.cursor.execute("INSERT INTO spam_photos (spam_id) VALUES ( ?)", (spam_id,))
            self.conn.commit()
            return self.conn.commit()
    async def get_spam_photo2(self, spam_id):
        self.cursor.execute("SELECT photo FROM spam_photos WHERE spam_id = ?", (spam_id,))
        result = self.cursor.fetchone()
        return result[0]
    async def set_spam_photo2(self, photo_data, spam_id):
        self.cursor.execute("UPDATE spam_photos SET photo = ? WHERE spam_id = ?", (photo_data, spam_id))
        return self.conn.commit()
    async def delete_spam_photo(self, photo_id):
        self.cursor.execute("DELETE FROM spam_photos WHERE id = ?", (photo_id,))
        return self.conn.commit()
    async def delete_spam_photo_by_spam(self, spam_id):
        self.cursor.execute("DELETE FROM spam_photos WHERE spam_id = ?", (spam_id,))
        return self.conn.commit()
    async def del_all_from_spam_photos(self):
        self.cursor.execute("DELETE FROM spam_photos")
        return self.conn.commit()


    """Close Data Base"""
    async def close_db(self):
        self.conn.close()