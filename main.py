import os
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import (
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TELEGRAM")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

CAR_TYPE, CAR_COLOR, CAR_MILEAGE_DECISION, CAR_MILEAGE, PHOTO, SUMMARY = range(6)

app = FastAPI()
telegram_app = Application.builder().token(BOT_TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["Sedan", "SUV", "Sports", "Electric"]]

    await update.message.reply_text(
        "<b>Welcome to the Car Sales Listing Bot!\n"
        "Let's get some details about the car you're selling.\n"
        "What is your car type?</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return CAR_TYPE


async def car_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    context.user_data["car_type"] = update.message.text

    cars = {
        "Sedan": "🚗",
        "SUV": "🚙",
        "Sports": "🏎️",
        "Electric": "⚡",
    }

    logger.info("Car type of %s: %s", user.first_name, update.message.text)

    await update.message.reply_text(
        f"<b>You selected {update.message.text} car {cars.get(update.message.text, '')}.\n"
        f"What color your car is?</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )

    keyboard = [
        [InlineKeyboardButton("Red", callback_data="Red")],
        [InlineKeyboardButton("Blue", callback_data="Blue")],
        [InlineKeyboardButton("Black", callback_data="Black")],
        [InlineKeyboardButton("White", callback_data="White")],
    ]

    await update.message.reply_text(
        "<b>Please choose:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return CAR_COLOR


async def car_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    context.user_data["car_color"] = query.data

    await query.edit_message_text(
        text=f"<b>You selected {query.data} color.\n"
        f"Would you like to fill in the mileage for your car?</b>",
        parse_mode="HTML",
    )

    keyboard = [
        [InlineKeyboardButton("Fill", callback_data="Fill")],
        [InlineKeyboardButton("Skip", callback_data="Skip")],
    ]

    await query.message.reply_text(
        "<b>Choose an option:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return CAR_MILEAGE_DECISION


async def car_mileage_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "Fill":
        await query.edit_message_text(
            text="<b>Please type in the mileage (e.g., 50000):</b>",
            parse_mode="HTML",
        )
        return CAR_MILEAGE

    await query.edit_message_text(
        text="<b>Mileage step skipped.</b>",
        parse_mode="HTML",
    )

    return await skip_mileage(update, context)


async def car_mileage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["car_mileage"] = update.message.text

    await update.message.reply_text(
        "<b>Mileage noted.\n"
        "Please upload a photo of your car 📷, or send /skip.</b>",
        parse_mode="HTML",
    )

    return PHOTO


async def skip_mileage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["car_mileage"] = "Not provided"

    text = "<b>Please upload a photo of your car 📷, or send /skip.</b>"

    if update.callback_query:
        chat_id = update.callback_query.message.chat_id
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
        )
    elif update.message:
        await update.message.reply_text(
            text,
            parse_mode="HTML",
        )

    return PHOTO


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    context.user_data["car_photo"] = photo_file.file_id

    await update.message.reply_text(
        "<b>Photo uploaded successfully.\n"
        "Let's summarize your selections.</b>",
        parse_mode="HTML",
    )

    return await summary(update, context)


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["car_photo"] = "Not provided"

    await update.message.reply_text(
        "<b>No photo uploaded.\n"
        "Let's summarize your selections.</b>",
        parse_mode="HTML",
    )

    return await summary(update, context)


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    selections = context.user_data

    summary_text = (
        "<b>Here's what you told me about your car:\n</b>"
        f"<b>Car Type:</b> {selections.get('car_type')}\n"
        f"<b>Color:</b> {selections.get('car_color')}\n"
        f"<b>Mileage:</b> {selections.get('car_mileage')}\n"
        f"<b>Photo:</b> {'Uploaded' if selections.get('car_photo') != 'Not provided' else 'Not provided'}"
    )

    chat_id = update.effective_chat.id

    if selections.get("car_photo") and selections.get("car_photo") != "Not provided":
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=selections["car_photo"],
            caption=summary_text,
            parse_mode="HTML",
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=summary_text,
            parse_mode="HTML",
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Bye! Hope to talk to you again soon.",
        reply_markup=ReplyKeyboardRemove(),
    )

    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        CAR_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, car_type)],
        CAR_COLOR: [CallbackQueryHandler(car_color)],
        CAR_MILEAGE_DECISION: [CallbackQueryHandler(car_mileage_decision)],
        CAR_MILEAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, car_mileage)],
        PHOTO: [
            MessageHandler(filters.PHOTO, photo),
            CommandHandler("skip", skip_photo),
        ],
        SUMMARY: [MessageHandler(filters.ALL, summary)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

telegram_app.add_handler(conv_handler)


@app.on_event("startup")
async def startup() -> None:
    await telegram_app.initialize()
    await telegram_app.start()

    if WEBHOOK_URL:
        await telegram_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        logger.info("Webhook configured: %s/webhook", WEBHOOK_URL)
    else:
        logger.warning("WEBHOOK_URL is not configured")


@app.on_event("shutdown")
async def shutdown() -> None:
    await telegram_app.stop()
    await telegram_app.shutdown()


@app.get("/")
async def home():
    return {"status": "Bot is running"}


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}
