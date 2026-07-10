import os
import requests
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BACKEND_URL = os.environ.get('BACKEND_URL', 'https://yutube-com-pcu9.onrender.com')
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN') or '8995589618:AAHWxs2-bmpuwZi3BI7LIjppxpdH5-WmYkw'

def get_status():
    try:
        r = requests.get(f'{BACKEND_URL}/api/admin/status', timeout=10)
        data = r.json()
        return data.get('enabled', True)
    except Exception as e:
        logger.error(f'get_status error: {e}')
        return None

def set_status(enabled: bool):
    try:
        r = requests.post(f'{BACKEND_URL}/api/admin/toggle', json={'enabled': enabled}, timeout=10)
        data = r.json()
        return data.get('enabled')
    except Exception as e:
        logger.error(f'set_status error: {e}')
        return None

def reply_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton('✅ Turn ON'), KeyboardButton('❌ Turn OFF')]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder='Tap a button below...'
    )

def main_menu(enabled):
    if enabled is None:
        status_dot = '⚫️'
        status_word = 'Unknown'
        status_emoji = '⚠️'
    elif enabled:
        status_dot = '🟢'
        status_word = 'ON'
        status_emoji = '✅'
    else:
        status_dot = '🔴'
        status_word = 'OFF'
        status_emoji = '❌'

    text = (
        f'{status_dot} *App Control*\n'
        f'─── · · · ───\n'
        f'App is *{status_word}* {status_emoji}\n'
        f'─── · · · ───\n'
        f'Use the menu below or tap a button:'
    )
    return text

async def send_home(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    enabled = get_status()
    text = main_menu(enabled)

    if edit:
        try:
            await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=home_keyboard())
        except Exception:
            await update.callback_query.message.reply_text(text, parse_mode='Markdown', reply_markup=home_keyboard())
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=home_keyboard())

def home_keyboard():
    keyboard = [
        [
            InlineKeyboardButton('✅ Turn ON', callback_data='toggle_on'),
            InlineKeyboardButton('❌ Turn OFF', callback_data='toggle_off')
        ],
        [
            InlineKeyboardButton('🔄 Refresh', callback_data='refresh')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f'🟢 *App Control*\n'
        f'─── · · · ───\n'
        f'Welcome! Use the buttons below to control your app.',
        parse_mode='Markdown',
        reply_markup=home_keyboard()
    )

async def cmd_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = set_status(True)
    if result is True:
        msg = '✅ App is now *ON*'
    else:
        msg = '⚠️ Failed to turn ON'
    await update.message.reply_text(msg, parse_mode='Markdown')

async def cmd_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = set_status(False)
    if result is False:
        msg = '❌ App is now *OFF*'
    else:
        msg = '⚠️ Failed to turn OFF'
    await update.message.reply_text(msg, parse_mode='Markdown')

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    enabled = get_status()
    if enabled is None:
        msg = '⚠️ *Status:* Unknown\nCould not reach backend.'
    elif enabled:
        msg = '🟢 App is *ON* ✅\nAll users can access the app.'
    else:
        msg = '🔴 App is *OFF* ❌\nUsers see maintenance page.'
    await update.message.reply_text(msg, parse_mode='Markdown')

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        '*Commands:*\n'
        '─── · · · ───\n'
        '/start — Open menu\n'
        '/on — Turn app ON\n'
        '/off — Turn app OFF\n'
        '/status — Check status\n'
        '/help — This help\n'
        '─── · · · ───\n'
        'Or use buttons at the bottom ⬇️'
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == '✅ Turn ON':
        await cmd_on(update, context)
    elif text == '❌ Turn OFF':
        await cmd_off(update, context)
    else:
        await update.message.reply_text(
            'Use /start to open the menu, or tap a button below.',
            reply_markup=reply_keyboard()
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'refresh':
        enabled = get_status()
        if enabled is None:
            toast = '⚠️ Unknown'
        elif enabled:
            toast = '🟢 App is ON'
        else:
            toast = '🔴 App is OFF'
        await query.answer(toast, show_alert=False)
        try:
            text = main_menu(enabled)
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=home_keyboard())
        except Exception:
            pass
        return

    if query.data == 'toggle_on':
        result = set_status(True)
        if result is True:
            toast = '✅ App turned ON'
        else:
            toast = '⚠️ Failed'
    elif query.data == 'toggle_off':
        result = set_status(False)
        if result is False:
            toast = '❌ App turned OFF'
        else:
            toast = '⚠️ Failed'
    else:
        toast = '⚠️ Unknown'

    await query.answer(toast, show_alert=False)
    enabled = get_status()
    try:
        text = main_menu(enabled)
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=home_keyboard())
    except Exception:
        pass

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')
    def log_message(self, fmt, *args):
        pass

def run_health_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f'Health server on port {port}')
    server.serve_forever()

def main():
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()

    try:
        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler('start', start))
        app.add_handler(CommandHandler('on', cmd_on))
        app.add_handler(CommandHandler('off', cmd_off))
        app.add_handler(CommandHandler('status', cmd_status))
        app.add_handler(CommandHandler('help', cmd_help))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
        app.add_handler(CallbackQueryHandler(button_handler))

        logger.info('Bot polling starting...')
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except Exception as e:
        logger.error(f'Bot crashed: {e}', exc_info=True)
        raise

if __name__ == '__main__':
    main()
