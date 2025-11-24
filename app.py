import os
import requests
import asyncpg
import asyncio
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters , 
    Application
)
from datetime import time , date
REFERENCE_DATE = date(2026, 9, 20)
DATABASE_URL = os.getenv("DATABASE_URL") # your Railway PostgreSQL URL
API = os.getenv("API")  # Your bot token from env variable
URL_PRICE = "https://alanchand.com/currencies-price"
URL_DATE = "https://www.time.ir/"

ADMIN_ID = 119822289
CHANNEL_ID = -1003477481048
CHANNEL_ID_2 = -1003027488793

tracked_messages = {}
DOLLAR_PRICE = "Unknown"
TODAY_DATE = "Unknown"

async def init_db():
    global conn
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("Database connected!")
    except Exception as e:
        print("Failed to connect to database:", e)
        conn = None


async def set_value(conn, chat_id, message_id):
    await conn.execute("""
        INSERT INTO my_table (chat_id, message_id) VALUES ($1, $2)
        ON CONFLICT (chat_id) DO UPDATE SET message_id = $2
    """, chat_id, message_id)


async def get_value(conn, chat_id):
    return await conn.fetchval(
        "SELECT message_id FROM my_table WHERE chat_id=$1", chat_id
    )

async def reminder(context : ContextTypes.DEFAULT_TYPE):
    today = date.today()
    delta = REFERENCE_DATE - today
    delta = delta.days
    msg = f"{delta}"
    await context.bot.send_message(chat_id=CHANNEL_ID , text=msg)


async def startup(app : Application):
    app.job_queue.run_daily(
        callback=reminder,
        time= time(hour=0 , minute=0),
        days=(0, 1, 2, 3, 4, 5, 6),   # every day
    )
    app.job_queue.run_once(reminder, when=5)
    print("Test message will be sent in 5 seconds...")





def persian_to_english_numbers(text):
    persian_numbers = "۰۱۲۳۴۵۶۷۸۹/"
    english_numbers = "0123456789-"
    translation_table = str.maketrans(persian_numbers, english_numbers)
    return text.translate(translation_table)

def translate_persian_date(text):
    days_fa = {
        "یکشنبه": "Sunday" , "یک شنبه": "Sunday" , "دوشنبه": "Monday", "دو شنبه": "Monday",
        "سه شنبه": "Tuesday" , "چهارشنبه": "Wednesday", "چهار شنبه": "Wednesday" ,
        "پنجشنبه": "Thursday", "پنج شنبه": "Thursday",
        "شنبه": "Saturday","جمعه": "Friday",
    }
    months_fa = {
        "فروردین": "Farvardin", "اردیبهشت": "Ordibehesht", "خرداد": "Khordad",
        "تیر": "Tir", "مرداد": "Mordad", "شهریور": "Shahrivar",
        "مهر": "Mehr", "آبان": "Aban", "آذر": "Azar",
        "دی": "Dey", "بهمن": "Bahman", "اسفند": "Esfand",
    }

    for fa, en in days_fa.items():
        text = text.replace(fa, en)
    for fa, en in months_fa.items():
        text = text.replace(fa, en)
    return text

def safe_get_html(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def get_price():
    global DOLLAR_PRICE
    soup = safe_get_html(URL_PRICE)
    if not soup:
        return DOLLAR_PRICE
    try:
        row = soup.find("tr", title="قیمت دلار آمریکا")
        price = persian_to_english_numbers(
            row.find("td", class_="buyPrice text-center").text.strip()
        )
        DOLLAR_PRICE = price
        print("Updated price:", price)
        return price
    except:
        return DOLLAR_PRICE

def get_date():
    global TODAY_DATE
    soup = safe_get_html(URL_DATE)
    if not soup:
        return TODAY_DATE
    try:
        fr = persian_to_english_numbers(
            soup.find("span", class_="TodayDate_root__title__value__yfkwD").text.strip()
        )
        en = soup.find("p", class_="MuiTypography-root MuiTypography-button1 en muirtl-1vbhkcf").text.strip()
        full = f"{en}\n{fr}"
        TODAY_DATE = translate_persian_date(full)
        print("Updated date:", TODAY_DATE)
        return TODAY_DATE
    except:
        return TODAY_DATE

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello!")
    print("start used")

async def cmd_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = get_price()
    date = get_date()
    chat = update.effective_chat
    msg = f"{date}\nCurrent USD price: {price} Rials"
    sent = await context.bot.send_message(chat.id , text=msg)
    await set_value(conn , chat.id , sent.message_id)

async def getID(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(str(update.effective_chat.id))

async def update_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
#for admin channel
    if chat.type == "private" and user.id == ADMIN_ID:
        price = get_price()
        date = get_date()
        msg = f"{date}\nCurrent USD price: {price} Rials"

        try:
            await context.bot.send_message(
                text=msg,
                chat_id=CHANNEL_ID
            )
            await update.message.reply_text("Channel message updated.")
            return
        except:
            pass
#for users
    if chat.type == "private" and user.id != ADMIN_ID:
        return await cmd_price(update, context)
#for groups 
    if chat.type in ["group", "supergroup"]:
        message_id = await get_value(conn , chat.id)
        #if the group doesnt exists in database
        if message_id == None:
            price = get_price()
            date = get_date()
            msg = f"{date}\nCurrent USD price: {price} Rials"
            try:
                sent = await context.bot.send_message(chat_id=chat.id , text=msg)
                await set_value(conn , chat.id , sent.message_id)
            except:
                pass
        #if the group exists in database
        else:
            price = get_price()
            date = get_date()
            msg = f"{date}\nCurrent USD price: {price} Rials"
            try:
                await context.bot.edit_message_text(text=msg , chat_id=chat.id , message_id=message_id)
            except:
                pass



async def bot_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            chat = update.effective_chat
            price = get_price()
            date = get_date()
            msg = f"{date}\nCurrent USD price: {price} Rials"
            sent = await context.bot.send_message(chat_id=chat.id, text=msg)
            await set_value(conn , chat_id=chat.id , message_id=sent.message_id)
            
            print("Bot added to group:", chat.id)


def run_bot():
    if not API:
        print("Error: API token not set in environment variable 'API'")
        return

    app = ApplicationBuilder().token(API).build()
    app.job_queue.run_once(startup , when=0 , data=app)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", cmd_price))
    app.add_handler(CommandHandler("id", getID))
    app.add_handler(CommandHandler("update", update_price))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bot_added))

    # Initialize database connection
    asyncio.get_event_loop().run_until_complete(init_db())
    
    print("Bot running...")
    app.run_polling()  # v20+ manages the asyncio loop internally

# --------------------------------------------
if __name__ == "__main__":
    run_bot()
