import asyncio
import requests
import os
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)

API = os.getenv("API")  # Your bot token from env variable
URL_PRICE = "https://alanchand.com/currencies-price"
URL_DATE = "https://www.time.ir/"

GROUP_ID = -5097868679
ADMIN_ID = 119822289
CHANNEL_ID = -1003477481048

tracked_messages = {}
DOLLAR_PRICE = "Unknown"
TODAY_DATE = "Unknown"

# --------------------------------------------
# Helpers
# --------------------------------------------

def persian_to_english_numbers(text):
    persian_numbers = "۰۱۲۳۴۵۶۷۸۹/"
    english_numbers = "0123456789-"
    translation_table = str.maketrans(persian_numbers, english_numbers)
    return text.translate(translation_table)

def translate_persian_date(text):
    days_fa = {
        "شنبه": "Saturday",
        "یکشنبه": "Sunday",
        "دوشنبه": "Monday",
        "سه‌شنبه": "Tuesday",
        "سه شنبه": "Tuesday",
        "چهارشنبه": "Wednesday",
        "پنجشنبه": "Thursday",
        "جمعه": "Friday",
    }

    months_fa = {
        "فروردین": "Farvardin",
        "اردیبهشت": "Ordibehesht",
        "خرداد": "Khordad",
        "تیر": "Tir",
        "مرداد": "Mordad",
        "شهریور": "Shahrivar",
        "مهر": "Mehr",
        "آبان": "Aban",
        "آذر": "Azar",
        "دی": "Dey",
        "بهمن": "Bahman",
        "اسفند": "Esfand",
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

# --------------------------------------------
# Commands
# --------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello!")
    print("start used")

async def cmd_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = get_price()
    date = get_date()
    msg = f"{date}\nCurrent USD price: {price} Rials"
    await update.message.reply_text(msg)

async def getID(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(str(update.effective_chat.id))

async def update_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type == "private" and user.id == ADMIN_ID:
        price = get_price()
        date = get_date()
        msg = f"{date}\nCurrent USD price: {price} Rials"

        if CHANNEL_ID in tracked_messages:
            message_id = tracked_messages[CHANNEL_ID]
            try:
                await context.bot.edit_message_text(
                    text=msg,
                    chat_id=CHANNEL_ID,
                    message_id=message_id
                )
                await update.message.reply_text("Channel message updated.")
                return
            except:
                pass

        sent = await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)
        tracked_messages[CHANNEL_ID] = sent.message_id
        await update.message.reply_text("Sent new message to channel.")
        return

    if chat.type == "private" and user.id != ADMIN_ID:
        return await cmd_price(update, context)

    await update.message.reply_text("No message to update.")

async def bot_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            chat = update.effective_chat
            price = get_price()
            date = get_date()
            msg = f"{date}\nCurrent USD price: {price} Rials"
            sent = await context.bot.send_message(chat_id=chat.id, text=msg)
            tracked_messages[chat.id] = sent.message_id
            print("Bot added to group:", chat.id)

# --------------------------------------------
# MAIN
# --------------------------------------------

async def main():
    if not API:
        print("Error: API token not set in environment variable 'API'")
        return

    app = ApplicationBuilder().token(API).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", cmd_price))
    app.add_handler(CommandHandler("id", getID))
    app.add_handler(CommandHandler("update", update_price))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bot_added))

    print("Bot running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
