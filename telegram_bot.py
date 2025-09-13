import os
import time
import json
import requests
import logging
from datetime import datetime
import pytz  # Import pytz for timezone handling
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Define the IST timezone
IST = pytz.timezone('Asia/Kolkata')


# ==================== User Store ====================


class UserStore:
    def __init__(self, filepath="users.json"):
        self.filepath = filepath

    def load_users(self):
        if not os.path.exists(self.filepath):
            return {}
        with open(self.filepath, "r") as f:
            return json.load(f)

    def save_users(self, users: dict):
        with open(self.filepath, "w") as f:
            json.dump(users, f, indent=4)

    def update_user(self, chat_id: int):
        users = self.load_users()
        # Use IST for last_seen timestamp
        users[str(chat_id)] = {"last_seen": datetime.now(IST).isoformat()}
        self.save_users(users)

    def remove_user(self, chat_id: int):
        users = self.load_users()
        if str(chat_id) in users:
            del users[str(chat_id)]
            self.save_users(users)

    def get_all_user_ids(self):
        """Gets all user IDs without filtering."""
        users = self.load_users()
        return [int(uid) for uid in users.keys()]


# ==================== Logger ====================


LOG_ROOT = "logs"


class BotLogger:
    def __init__(self):
        self.logger = self.setup_logger()

    def setup_logger(self):
        # Use IST for the daily log directory
        today_str = datetime.now(IST).strftime("%Y-%m-%d")
        log_dir = os.path.join(LOG_ROOT, today_str)
        os.makedirs(log_dir, exist_ok=True)

        print(f"Logging directory: {os.path.abspath(log_dir)}")

        logger = logging.getLogger("telegram_bot_logger")
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ"
        )
        
        # Use a custom converter for IST timestamps in logs
        def time_converter(*args):
            return datetime.now(IST).timetuple()

        formatter.converter = time_converter

        levels = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warn": logging.WARNING,
            "critical": logging.CRITICAL,
        }

        for level_name, level in levels.items():
            handler = logging.FileHandler(os.path.join(log_dir, f"{level_name}.log"))
            handler.setLevel(level)
            handler.addFilter(lambda record, lvl=level: record.levelno == lvl)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger


# ==================== Response Handler ====================


class ResponseHandler:
    def handle(self, text: str) -> str:
        processed = text.lower()
        if "hello" in processed:
            return "👋 Hello! How can I help you?"
        if "hi" in processed:
            return "Hi there!"
        if "how are you" in processed:
            return "😊 I’m doing well, thank you! How are you?"
        return "🤔 I’m not sure what you mean..."



# ==================== Alert Manager ====================


class AlertService:
    def __init__(self):
        config_path = os.path.abspath("config.json")
        with open("config.json", "r") as f:
            config = json.load(f)
        self.alerts_enabled = config.get("telegram_alerts", False)
        self.TOKEN=config.get("telegram_bot_token","8224633656:AAEfO603nFQdNguV-dJ_UK2jzDb8DPNNmW4")
        self.BASE_URL = f"https://api.telegram.org/bot{self.TOKEN}/sendMessage"

        # Create UserStore instance here to use internally
        self.user_store = UserStore()

    def send_signal_alert(self, message: str):
        """
        Send Telegram alerts synchronously.
        """

        if not self.alerts_enabled:
            print("[Alert Service] Telegram alerts are disabled in the configuration.")
            return

        chat_ids = self.user_store.get_all_user_ids()
        if not chat_ids:
            print("[Alert Service] No users to send alerts to.")
            return

        print(f"[Alert Service] Sending alert to users: {chat_ids}")
        for chat_id in chat_ids:
            try:
                resp = requests.post(self.BASE_URL, data={
                    "chat_id": chat_id,
                    "text": message
                })
                if resp.status_code == 200:
                    print(f"[Alert Service] ✅ Alert sent to {chat_id}")
                else:
                    print(f"[Alert Service] ❌ Failed to send alert to {chat_id}: {resp.text}")
            except Exception as e:
                print(f"[Alert Service] ❌ Error sending alert to {chat_id}: {e}")


# ==================== Bot Handlers ====================


class BotHandlers:
    BOT_USERNAME = "@SWTSdeltaexchange_bot"

    def __init__(self, user_store, response_handler, pin):
        self.user_store = user_store
        self.response_handler = response_handler
        self.pin = pin
        self.user_states = {}

        self.bot_logger = BotLogger().logger

    def debug(self, msg: str):
        self.bot_logger.debug(msg)

    def info(self, msg: str):
        self.bot_logger.info(msg)

    def critical(self, msg: str):
        self.bot_logger.critical(msg)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat.id
        text = update.message.text
        chat_type = update.message.chat.type

        self.debug(f"Received message from {chat_id}: {text}")

        if chat_id in self.user_states:
            state = self.user_states[chat_id]
            if text == self.pin:
                if state == 'awaiting_pin_for_link':
                    self.user_store.update_user(chat_id)
                    await update.message.reply_text(
                        "Hello, Now you will receiving notifications ."
                    )
                elif state == 'awaiting_pin_for_terminate':
                    try:
                        self.manager.terminate_all()
                        await update.message.reply_text("✅ All strategies terminated.")
                    except Exception as e:
                        self.critical(f"Error terminating strategies: {e}")
                        await update.message.reply_text(f"❌ Failed to terminate strategies: {e}")
                del self.user_states[chat_id]
            else:
                await update.message.reply_text("Incorrect PIN. Please try again.")
            return

        if chat_type == "group" and self.BOT_USERNAME not in text:
            return

        msg = text.replace(self.BOT_USERNAME, "").strip() if chat_type == "group" else text
        response = self.response_handler.handle(msg)

        self.info(f"Message from {chat_id}: {msg} -> Responding: {response}")

        await update.message.reply_text(response)

    async def link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat.id
        self.user_states[chat_id] = 'awaiting_pin_for_link'
        await update.message.reply_text("Please enter the 4-digit PIN to link your account.")

    async def unlink(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat.id
        self.user_store.remove_user(chat_id)
        await update.message.reply_text(
            "Hello, Now you will not receiving notifications ."
        )

    async def terminate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat.id
        self.user_states[chat_id] = 'awaiting_pin_for_terminate'
        await update.message.reply_text("Please enter the 4-digit PIN to terminate all strategies.")


    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("ℹ️ Send me a message, and I'll respond!")

    async def custom(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("⚙️ Welcome to the Custom command!")

    async def error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return

    async def start_command(self,update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat.id
        self.user_store.update_user(chat_id) 
        await update.message.reply_text(
            'Welcome to Secret Weapon Trading Solution Notification Service \n To start receiving notification please click on /link option in menu'
        )


# ==================== Telegram Bot App ====================

class TelegramBotApp:
    def __init__(self):
        """
        Initializes the Telegram Bot application.
        It will only set up the bot if "telegram_alerts" is true in config.json.
        """
        config_path = os.path.abspath("config.json")
        with open("config.json", "r") as f:
            config = json.load(f)

        self.alerts_enabled = config.get("telegram_alerts", False)
        self.app = None  # Default to None

        if self.alerts_enabled:
            print("[Telegram Bot] Initializing Telegram integration.")
            token = config.get("telegram_bot_token","8224633656:AAEfO603nFQdNguV-dJ_UK2jzDb8DPNNmW4" )
            pin = config.get("telegram_bot_pin", "1234")

            # Initialize all components required for the bot to run
            self.user_store = UserStore()
            self.response_handler = ResponseHandler()
            self.alert_service = AlertService()
            self.bot_handlers = BotHandlers(self.user_store, self.response_handler, pin)

            # Build the application
            self.app = Application.builder().token(token).build()
            self.app.add_handler(CommandHandler("link", self.bot_handlers.link))
            self.app.add_handler(CommandHandler("unlink", self.bot_handlers.unlink))
            self.app.add_handler(CommandHandler("terminate", self.bot_handlers.terminate))
            self.app.add_handler(CommandHandler("start", self.bot_handlers.start_command))
            self.app.add_handler(CommandHandler("help", self.bot_handlers.help))
            self.app.add_handler(CommandHandler("custom", self.bot_handlers.custom))
            self.app.add_handler(MessageHandler(filters.TEXT, self.bot_handlers.handle_message))
            self.app.add_error_handler(self.bot_handlers.error)
        else:
            print("[Telegram Bot] Telegram integration is disabled. Bot will not connect.")

    def run(self):
        """
        Runs the bot's polling loop only if it has been initialized.
        """
        if self.app:
            self.bot_handlers.bot_logger.info("Starting Telegram bot...")
            self.app.run_polling()


# ==================== Main Entrypoint ====================


if __name__ == "__main__":
    bot_app = TelegramBotApp()
    bot_app.run()
