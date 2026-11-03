# language: Python, file: bot.py, target: aiogram 3.x + Telethon (bothost-ready)
# pip install aiogram telethon aiohttp beautifulsoup4 lxml python-dotenv

import asyncio
import json
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import (
    ApiIdInvalidError,
    FloodWaitError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberBannedError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)

load_dotenv()

# ── конфигурация ──────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TG_API_ID = int(os.getenv("TG_API_ID", "17349"))
TG_API_HASH = os.getenv("TG_API_HASH", "")
ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD", "changeme")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

ACCOUNTS_FILE = DATA_DIR / "accounts.json"
LOGS_FILE = DATA_DIR / "logs.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
AUTHORIZED_FILE = DATA_DIR / "authorized.json"
STATS_FILE = DATA_DIR / "stats.json"

# 40 сайтов: (название, URL страницы с номерами/SMS)
SITES: list[tuple[str, str]] = [
    ("TempSMSS", "https://tempsmss.com/receive-sms-for/telegram/"),
    ("SMSPool", "https://www.smspool.net/free-sms-verification-for-telegram"),
    ("SMSReceive.live", "https://smsreceive.live/free-gb-phone-number"),
    ("Tiger-SMS", "https://tiger-sms.com/free-numbers/myanmar"),
    ("asms.ai", "https://asms.ai/"),
    ("ReceiveFreeSMS", "https://receivefreesms.co.uk/"),
    ("MyTempSMS", "https://mytempsms.com/"),
    ("SMS24", "https://sms24.me/en/"),
    ("Jiemahao", "https://jiemahao.com/"),
    ("Quackr", "https://quackr.io/"),
    ("SMSToMe", "https://smstome.com/"),
    ("OKSMS", "https://oksms.org/"),
    ("Receive-SMS-Free", "https://receive-sms-free.cc/"),
    ("Receive-SMS.io", "https://receive-sms.io/"),
    ("SMSReceiveFree", "https://smsreceivefree.com/"),
    ("Receive-a-SMS", "https://receive-a-sms.com/"),
    ("SMS-Online", "https://sms-online.co/receive-free-sms"),
    ("SMSReceiveOnline", "https://smsreceiveonline.com/"),
    ("GetFreeSMSNumber", "https://getfreesmsnumber.com/"),
    ("7sim.net", "https://7sim.net/"),
    ("Receive-SMS.net", "https://receive-sms.net/"),
    ("Temp-Number", "https://temp-number.com/"),
    ("Freephonenum", "https://freephonenum.com/"),
    ("Temporary-Phone-Number", "https://temporary-phone-number.com/"),
    ("SMS-Receive.net", "https://sms-receive.net/"),
    ("Receive-smss", "https://receive-smss.com/"),
    ("Receive-SMS-Online.info", "https://receive-sms-online.info/"),
    ("AnonymSMS", "https://anonymsms.com/"),
    ("Receive-SMS.cc", "https://receive-sms.cc/"),
    ("Sellaite", "https://sms.sellaite.com/"),
    ("Receive-SMS-Online.net", "https://receive-sms-online.net/"),
    ("FreeReceiveSMS", "https://freereceivesms.com/"),
    ("ReceiveSMSFree.net", "https://receivesmsfree.net/"),
    ("SMS-Receive-Free", "https://sms-receive-free.com/"),
    ("TempSMS", "https://tempsms.com/"),
    ("SMSNumber.info", "https://smsnumber.info/"),
    ("Receive-SMS.co", "https://receive-sms.co/"),
    ("SMSTemp", "https://smstemp.com/"),
    ("TextNow", "https://www.textnow.com/"),
    ("ReceiveSMSOnline.net", "https://receivesmsonline.net/"),
]

SMS_WAIT = 60
SMS_POLL_INTERVAL = 5
MAX_CONCURRENT_SITES = 5
WORKER_SLEEP_BETWEEN = 2

# runtime-состояние (в памяти процесса)
REGISTRATION_TASKS: dict[int, asyncio.Task] = {}
IN_FLIGHT_PHONES: set[str] = set()


# ── переводы ──────────────────────────────────────────────────────────────
TRANSLATIONS = {
    "ru": {
        "enter_password": "🔐 <b>Добро пожаловать!</b>\n\nВведите пароль для доступа к панели:",
        "wrong_password": "❌ Неверный пароль. Попробуйте снова.",
        "menu": (
            "🏠 <b>Главное меню</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👋 Привет! Я помогаю автоматизировать регистрацию аккаунтов Telegram "
            "на публичных временных номерах.\n\n"
            "📊 <b>Текущее состояние:</b>\n"
            "  👤 Аккаунтов создано: <b>{accounts}</b>\n"
            "  🌐 Сайтов в работе: <b>{limit}</b> из <b>{total}</b>\n\n"
            "Выберите действие:"
        ),
        "btn_start": "🚀 Запустить регистрацию",
        "btn_stop": "🛑 Остановить регистрацию",
        "btn_accounts": "👤 Аккаунты",
        "btn_stats": "📊 Статистика",
        "btn_logs": "📄 Логи",
        "btn_settings": "⚙️ Настройки",
        "btn_back": "⬅️ Назад",
        "reg_started": (
            "🚀 <b>Регистрация запущена!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔄 Работаю в фоне: <b>{workers}</b> параллельных потоков\n"
            "🌐 Сайтов в очереди: <b>{limit}</b>\n\n"
            "⏳ Как только аккаунт создастся — пришлю уведомление.\n"
            "🛑 Остановить можно кнопкой ниже."
        ),
        "reg_stopped": (
            "🛑 <b>Регистрация остановлена</b>\n\n"
            "Все текущие попытки прерваны. Возвращаю в меню."
        ),
        "reg_already": "⚠️ Регистрация уже идёт.",
        "reg_not_running": "ℹ️ Регистрация не запущена.",
        "reg_no_sites": "⚠️ Список сайтов пуст — нечего обрабатывать.",
        "account_created_notify": (
            "🎉 <b>Аккаунт успешно создан!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📱 Номер: <code>{phone}</code>\n"
            "🆔 Telegram ID: <code>{uid}</code>\n"
            "📛 Имя: {name}\n"
            "🌐 Источник: {site}\n\n"
            "👤 Всего аккаунтов: <b>{total}</b>"
        ),
        "no_accounts": (
            "👤 <b>Аккаунтов пока нет</b>\n\n"
            "Запустите регистрацию в главном меню — первые аккаунты появятся здесь."
        ),
        "accounts_title": (
            "👤 <b>Аккаунты</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Выберите номер, чтобы увидеть детали:"
        ),
        "account_detail": (
            "👤 <b>Аккаунт</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📱 Номер: <code>{phone}</code>\n"
            "📨 Кодов получено: <b>{codes}</b>\n"
            "🕐 Создан: {created}"
        ),
        "btn_get_codes": "📨 Получить код для входа",
        "codes_list": (
            "📨 <b>Коды для {phone}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "{codes}"
        ),
        "codes_empty": "📭 Кодов для этого аккаунта пока нет.",
        "stats_text": (
            "📊 <b>Статистика</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ <b>Создано аккаунтов:</b> {created}\n"
            "📨 <b>Запрошено кодов:</b> {requested}\n"
            "❌ <b>Неверных кодов:</b> {invalid}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🕐 Обновлено: {now}"
        ),
        "settings": (
            "⚙️ <b>Настройки</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🌐 Язык: <b>{lang}</b>\n"
            "🔢 Лимит сайтов: <b>{limit}</b>\n\n"
            "Выберите параметр для изменения:"
        ),
        "btn_sites": "🔢 Кол-во сайтов",
        "btn_lang": "🌐 Смена языка",
        "enter_site_limit": (
            "🔢 <b>Количество сайтов</b>\n\n"
            "Введите новое значение от <b>1</b> до <b>{max}</b>:"
        ),
        "invalid_number": "⚠️ Нужно число от 1 до {max}.",
        "limit_updated": "✅ Лимит обновлён: <b>{limit}</b>",
        "lang_updated": "✅ Язык изменён: <b>{lang}</b>",
        "logs_sent": "📄 Логи отправлены.",
        "no_logs": "📭 Логов пока нет.",
        "logout_done": "👋 Вы вышли. Пароль потребуется снова.",
        "choose_lang": "🌐 <b>Выберите язык</b> / Choose language:",
    },
    "en": {
        "enter_password": "🔐 <b>Welcome!</b>\n\nEnter password to access the panel:",
        "wrong_password": "❌ Wrong password. Try again.",
        "menu": (
            "🏠 <b>Main menu</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👋 Hi! I automate Telegram account registration on public temporary numbers.\n\n"
            "📊 <b>Current state:</b>\n"
            "  👤 Accounts created: <b>{accounts}</b>\n"
            "  🌐 Active sites: <b>{limit}</b> of <b>{total}</b>\n\n"
            "Choose an action:"
        ),
        "btn_start": "🚀 Start registration",
        "btn_stop": "🛑 Stop registration",
        "btn_accounts": "👤 Accounts",
        "btn_stats": "📊 Statistics",
        "btn_logs": "📄 Logs",
        "btn_settings": "⚙️ Settings",
        "btn_back": "⬅️ Back",
        "reg_started": (
            "🚀 <b>Registration started!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔄 Running in background: <b>{workers}</b> parallel workers\n"
            "🌐 Sites in queue: <b>{limit}</b>\n\n"
            "⏳ I'll notify you as soon as an account is created.\n"
            "🛑 Use the button below to stop."
        ),
        "reg_stopped": (
            "🛑 <b>Registration stopped</b>\n\n"
            "All running attempts cancelled. Returning to menu."
        ),
        "reg_already": "⚠️ Registration already running.",
        "reg_not_running": "ℹ️ Registration not running.",
        "reg_no_sites": "⚠️ Site list is empty — nothing to process.",
        "account_created_notify": (
            "🎉 <b>Account created!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📱 Phone: <code>{phone}</code>\n"
            "🆔 Telegram ID: <code>{uid}</code>\n"
            "📛 Name: {name}\n"
            "🌐 Source: {site}\n\n"
            "👤 Total accounts: <b>{total}</b>"
        ),
        "no_accounts": (
            "👤 <b>No accounts yet</b>\n\n"
            "Start registration from main menu — first accounts will appear here."
        ),
        "accounts_title": (
            "👤 <b>Accounts</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Select a number to see details:"
        ),
        "account_detail": (
            "👤 <b>Account</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📱 Phone: <code>{phone}</code>\n"
            "📨 Codes received: <b>{codes}</b>\n"
            "🕐 Created: {created}"
        ),
        "btn_get_codes": "📨 Get login code",
        "codes_list": (
            "📨 <b>Codes for {phone}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "{codes}"
        ),
        "codes_empty": "📭 No codes for this account yet.",
        "stats_text": (
            "📊 <b>Statistics</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ <b>Accounts created:</b> {created}\n"
            "📨 <b>Codes requested:</b> {requested}\n"
            "❌ <b>Invalid codes:</b> {invalid}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🕐 Updated: {now}"
        ),
        "settings": (
            "⚙️ <b>Settings</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🌐 Language: <b>{lang}</b>\n"
            "🔢 Site limit: <b>{limit}</b>\n\n"
            "Choose parameter to change:"
        ),
        "btn_sites": "🔢 Site count",
        "btn_lang": "🌐 Change language",
        "enter_site_limit": (
            "🔢 <b>Site count</b>\n\n"
            "Enter new value from <b>1</b> to <b>{max}</b>:"
        ),
        "invalid_number": "⚠️ Number must be 1–{max}.",
        "limit_updated": "✅ Limit updated: <b>{limit}</b>",
        "lang_updated": "✅ Language changed: <b>{lang}</b>",
        "logs_sent": "📄 Logs sent.",
        "no_logs": "📭 No logs yet.",
        "logout_done": "👋 Logged out. Password required again.",
        "choose_lang": "🌐 <b>Choose language</b> / Выберите язык:",
    },
}


# ── JSON helpers ──────────────────────────────────────────────────────────
def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_accounts() -> list[dict]:
    return _load_json(ACCOUNTS_FILE, [])


def save_accounts(accounts: list[dict]):
    _save_json(ACCOUNTS_FILE, accounts)


def load_logs() -> list[dict]:
    return _load_json(LOGS_FILE, [])


def save_logs(logs: list[dict]):
    _save_json(LOGS_FILE, logs[-2000:])


def load_settings() -> dict:
    return _load_json(SETTINGS_FILE, {"language": "ru", "site_limit": 40})


def save_settings(s: dict):
    _save_json(SETTINGS_FILE, s)


def load_stats() -> dict:
    return _load_json(
        STATS_FILE,
        {"accounts_created": 0, "codes_requested": 0, "invalid_codes": 0},
    )


def save_stats(s: dict):
    _save_json(STATS_FILE, s)


def increment_stat(key: str, amount: int = 1):
    s = load_stats()
    s[key] = s.get(key, 0) + amount
    save_stats(s)


def load_authorized() -> dict:
    return _load_json(AUTHORIZED_FILE, {})


def save_authorized(data: dict):
    _save_json(AUTHORIZED_FILE, data)


def is_authorized(user_id: int) -> bool:
    return str(user_id) in load_authorized()


def add_authorized(user_id: int):
    data = load_authorized()
    data[str(user_id)] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    save_authorized(data)


def remove_authorized(user_id: int):
    data = load_authorized()
    data.pop(str(user_id), None)
    save_authorized(data)


def log_event(level: str, message: str):
    logs = load_logs()
    logs.append({
        "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "level": level,
        "message": message,
    })
    save_logs(logs)


def add_account(phone: str, session_file: str) -> dict:
    accounts = load_accounts()
    entry = {
        "phone": phone,
        "session": session_file,
        "codes": [],
        "created": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    accounts.append(entry)
    save_accounts(accounts)
    return entry


def add_code_to_account(phone: str, code: str):
    accounts = load_accounts()
    for a in accounts:
        if a["phone"] == phone:
            a["codes"].append(code)
            break
    save_accounts(accounts)


# ── парсинг номеров и SMS ─────────────────────────────────────────────────
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

PHONE_RE = re.compile(r"\+?[1-9]\d{6,14}")
STRICT_PHONE_RE = re.compile(
    r"\+(?:[1-9]\d{0,2})[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{4}"
)
CODE_RE = re.compile(r"(?<!\d)(\d{5,6})(?!\d)")


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"[^\d+]", "", raw)
    if digits.startswith("+"):
        digits = digits[1:]
    if len(digits) < 7 or len(digits) > 15 or digits.startswith("0"):
        return None
    return "+" + digits


def extract_phone(html: str) -> str | None:
    for m in STRICT_PHONE_RE.finditer(html):
        p = normalize_phone(m.group(0))
        if p:
            return p
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("tel:"):
            p = normalize_phone(a["href"][4:])
            if p:
                return p
    for attr in ("data-phone", "data-number"):
        for tag in soup.find_all(attrs={attr: True}):
            p = normalize_phone(tag[attr])
            if p:
                return p
    for m in PHONE_RE.finditer(html):
        p = normalize_phone(m.group(0))
        if p:
            return p
    return None


def extract_code(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    for m in re.finditer(r"Telegram[^0-9]{0,40}(\d{5,6})", text, re.I):
        return m.group(1)
    for m in CODE_RE.finditer(text):
        return m.group(1)
    return None


async def fetch_html(session: aiohttp.ClientSession, url: str,
                     timeout: int = 20) -> str | None:
    try:
        async with session.get(url, timeout=timeout) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception:
        pass
    return None


async def wait_for_code(session: aiohttp.ClientSession, url: str,
                        timeout: int = SMS_WAIT,
                        interval: int = SMS_POLL_INTERVAL) -> str | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        await asyncio.sleep(interval)
        html = await fetch_html(session, url)
        if html:
            code = extract_code(html)
            if code:
                return code
    return None


# ── регистрация на одном сайте ────────────────────────────────────────────
async def try_site(
    name: str,
    url: str,
    session: aiohttp.ClientSession,
    bot: Bot,
    user_id: int,
) -> dict | None:
    log_event("info", f"{name}: старт")
    html = await fetch_html(session, url)
    if not html:
        log_event("warn", f"{name}: страница не загрузилась")
        return None

    phone = extract_phone(html)
    if not phone:
        log_event("warn", f"{name}: номер не найден")
        return None

    if phone in IN_FLIGHT_PHONES:
        log_event("warn", f"{name}: номер {phone} уже обрабатывается")
        return None

    existing = load_accounts()
    if any(a["phone"] == phone for a in existing):
        log_event("warn", f"{name}: номер {phone} уже зарегистрирован")
        return None

    IN_FLIGHT_PHONES.add(phone)
    log_event("info", f"{name}: номер {phone}")

    session_file = f"data/session_{phone.lstrip('+')}"
    client = TelegramClient(session_file, TG_API_ID, TG_API_HASH)
    try:
        await client.connect()
        await client.send_code_request(phone)
        increment_stat("codes_requested")
        log_event("info", f"{name}: код запрошен у Telegram")

        code = await wait_for_code(session, url)
        if not code:
            log_event("warn", f"{name}: SMS не пришёл")
            return None

        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            log_event("warn", f"{name}: 2FA, пропуск")
            return None

        me = await client.get_me()
        log_event("success", f"{name}: аккаунт создан id={me.id} phone={phone}")
        increment_stat("accounts_created")
        add_account(phone, session_file)
        add_code_to_account(phone, code)

        total = len(load_accounts())
        try:
            await bot.send_message(
                user_id,
                TRANSLATIONS[load_settings().get("language", "ru")][
                    "account_created_notify"
                ].format(
                    phone=phone,
                    uid=me.id,
                    name=me.first_name or "—",
                    site=name,
                    total=total,
                ),
            )
        except Exception as e:
            log_event("warn", f"{name}: уведомление не доставлено — {e}")

        return {"name": name, "phone": phone, "id": me.id}

    except PhoneNumberInvalidError:
        log_event("warn", f"{name}: номер не принят")
    except PhoneNumberBannedError:
        log_event("warn", f"{name}: номер забанен")
    except PhoneCodeInvalidError:
        increment_stat("invalid_codes")
        log_event("warn", f"{name}: код неверный")
    except PhoneCodeExpiredError:
        log_event("warn", f"{name}: код истёк")
    except ApiIdInvalidError:
        log_event("error", f"{name}: api_id отклонён")
    except FloodWaitError as e:
        log_event("warn", f"{name}: FloodWait {e.seconds}s")
        try:
            await asyncio.sleep(min(e.seconds, 60))
        except asyncio.CancelledError:
            raise
    except Exception as e:
        log_event("error", f"{name}: {type(e).__name__}: {e}")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass
        IN_FLIGHT_PHONES.discard(phone)
    return None


# ── воркер и главный цикл регистрации ─────────────────────────────────────
async def worker(
    bot: Bot,
    user_id: int,
    targets: list[tuple[str, str]],
    session: aiohttp.ClientSession,
    worker_id: int,
):
    idx = worker_id % len(targets) if targets else 0
    while True:
        if not targets:
            await asyncio.sleep(5)
            continue
        name, url = targets[idx % len(targets)]
        idx += 1
        try:
            await try_site(name, url, session, bot, user_id)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log_event("error", f"w{worker_id}: {type(e).__name__}: {e}")
        try:
            await asyncio.sleep(WORKER_SLEEP_BETWEEN)
        except asyncio.CancelledError:
            raise


async def registration_main(
    bot: Bot,
    user_id: int,
    targets: list[tuple[str, str]],
    session: aiohttp.ClientSession,
):
    workers = [
        asyncio.create_task(worker(bot, user_id, targets, session, i))
        for i in range(MAX_CONCURRENT_SITES)
    ]
    try:
        await asyncio.gather(*workers)
    except asyncio.CancelledError:
        for w in workers:
            w.cancel()
        for w in workers:
            try:
                await w
            except (asyncio.CancelledError, Exception):
                pass
        raise


# ── FSM ───────────────────────────────────────────────────────────────────
class Auth(StatesGroup):
    waiting_password = State()


class SettingsFSM(StatesGroup):
    waiting_limit = State()


# ── клавиатуры и тексты ───────────────────────────────────────────────────
def menu_text(lang: str) -> str:
    settings = load_settings()
    return TRANSLATIONS[lang]["menu"].format(
        accounts=len(load_accounts()),
        limit=settings["site_limit"],
        total=len(SITES),
    )


def main_menu_kb(lang: str, running: bool = False) -> InlineKeyboardMarkup:
    t = TRANSLATIONS[lang]
    rows = []
    if running:
        rows.append([InlineKeyboardButton(text=t["btn_stop"], callback_data="stop_reg")])
    else:
        rows.append([InlineKeyboardButton(text=t["btn_start"], callback_data="start_reg")])
    rows.append([
        InlineKeyboardButton(text=t["btn_accounts"], callback_data="accounts"),
        InlineKeyboardButton(text=t["btn_stats"], callback_data="stats"),
    ])
    rows.append([
        InlineKeyboardButton(text=t["btn_logs"], callback_data="logs"),
        InlineKeyboardButton(text=t["btn_settings"], callback_data="settings"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def stop_kb(lang: str) -> InlineKeyboardMarkup:
    t = TRANSLATIONS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["btn_stop"], callback_data="stop_reg")],
    ])


def back_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=TRANSLATIONS[lang]["btn_back"], callback_data="menu")],
    ])


def accounts_kb(accounts: list[dict], lang: str) -> InlineKeyboardMarkup:
    t = TRANSLATIONS[lang]
    rows = []
    for i, a in enumerate(accounts):
        rows.append([
            InlineKeyboardButton(
                text=f"{a['phone']} · {len(a['codes'])} кодов",
                callback_data=f"acc:{i}",
            )
        ])
    rows.append([InlineKeyboardButton(text=t["btn_back"], callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def account_detail_kb(idx: int, lang: str) -> InlineKeyboardMarkup:
    t = TRANSLATIONS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["btn_get_codes"], callback_data=f"codes:{idx}")],
        [InlineKeyboardButton(text=t["btn_back"], callback_data="accounts")],
    ])


def settings_kb(lang: str) -> InlineKeyboardMarkup:
    t = TRANSLATIONS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["btn_sites"], callback_data="set_limit")],
        [InlineKeyboardButton(text=t["btn_lang"], callback_data="set_lang")],
        [InlineKeyboardButton(text=t["btn_back"], callback_data="menu")],
    ])


def lang_kb(lang: str) -> InlineKeyboardMarkup:
    t = TRANSLATIONS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
        ],
        [InlineKeyboardButton(text=t["btn_back"], callback_data="settings")],
    ])


# ── роутер ────────────────────────────────────────────────────────────────
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    settings = load_settings()
    lang = settings.get("language", "ru")

    if is_authorized(message.from_user.id):
        await state.clear()
        running = message.from_user.id in REGISTRATION_TASKS
        await message.answer(menu_text(lang), reply_markup=main_menu_kb(lang, running))
        return

    await state.set_state(Auth.waiting_password)
    await message.answer(TRANSLATIONS[lang]["enter_password"])


@router.message(Auth.waiting_password)
async def check_password(message: Message, state: FSMContext):
    settings = load_settings()
    lang = settings.get("language", "ru")

    if not message.text or message.text.strip() != ACCESS_PASSWORD:
        await message.answer(TRANSLATIONS[lang]["wrong_password"])
        return

    add_authorized(message.from_user.id)
    log_event("info", f"Авторизация пользователя id={message.from_user.id}")
    await state.clear()
    running = message.from_user.id in REGISTRATION_TASKS
    await message.answer(menu_text(lang), reply_markup=main_menu_kb(lang, running))


@router.message(F.text == "/logout")
async def cmd_logout(message: Message, state: FSMContext):
    remove_authorized(message.from_user.id)
    settings = load_settings()
    lang = settings.get("language", "ru")
    await state.clear()
    await message.answer(TRANSLATIONS[lang]["logout_done"])


@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery):
    settings = load_settings()
    lang = settings.get("language", "ru")
    running = call.from_user.id in REGISTRATION_TASKS
    await call.message.edit_text(menu_text(lang), reply_markup=main_menu_kb(lang, running))
    await call.answer()


@router.callback_query(F.data == "accounts")
async def cb_accounts(call: CallbackQuery):
    settings = load_settings()
    lang = settings.get("language", "ru")
    accounts = load_accounts()
    if not accounts:
        await call.message.edit_text(
            TRANSLATIONS[lang]["no_accounts"], reply_markup=back_kb(lang)
        )
        await call.answer()
        return
    await call.message.edit_text(
        TRANSLATIONS[lang]["accounts_title"],
        reply_markup=accounts_kb(accounts, lang),
    )
    await call.answer()


@router.callback_query(F.data.startswith("acc:"))
async def cb_account_detail(call: CallbackQuery):
    idx = int(call.data.split(":")[1])
    settings = load_settings()
    lang = settings.get("language", "ru")
    accounts = load_accounts()
    if idx >= len(accounts):
        await call.answer("Not found", show_alert=True)
        return
    a = accounts[idx]
    text = TRANSLATIONS[lang]["account_detail"].format(
        phone=a["phone"],
        codes=len(a.get("codes", [])),
        created=a.get("created", "—"),
    )
    await call.message.edit_text(text, reply_markup=account_detail_kb(idx, lang))
    await call.answer()


@router.callback_query(F.data.startswith("codes:"))
async def cb_get_codes(call: CallbackQuery):
    idx = int(call.data.split(":")[1])
    settings = load_settings()
    lang = settings.get("language", "ru")
    accounts = load_accounts()
    if idx >= len(accounts):
        await call.answer("Not found", show_alert=True)
        return
    a = accounts[idx]
    codes = a.get("codes", [])
    if not codes:
        await call.answer(TRANSLATIONS[lang]["codes_empty"], show_alert=True)
        return
    text = TRANSLATIONS[lang]["codes_list"].format(
        phone=a["phone"], codes="\n".join(f"• <code>{c}</code>" for c in codes)
    )
    await call.message.answer(text)
    await call.answer()


@router.callback_query(F.data == "stats")
async def cb_stats(call: CallbackQuery):
    settings = load_settings()
    lang = settings.get("language", "ru")
    s = load_stats()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    text = TRANSLATIONS[lang]["stats_text"].format(
        created=s.get("accounts_created", 0),
        requested=s.get("codes_requested", 0),
        invalid=s.get("invalid_codes", 0),
        now=now,
    )
    await call.message.edit_text(text, reply_markup=back_kb(lang))
    await call.answer()


@router.callback_query(F.data == "logs")
async def cb_logs(call: CallbackQuery):
    settings = load_settings()
    lang = settings.get("language", "ru")
    logs = load_logs()
    if not logs:
        await call.answer(TRANSLATIONS[lang]["no_logs"], show_alert=True)
        return
    path = DATA_DIR / "logs_export.json"
    _save_json(path, logs)
    await call.message.answer_document(
        FSInputFile(path, filename="logs.json"),
        caption=TRANSLATIONS[lang]["logs_sent"],
    )
    await call.answer()


@router.callback_query(F.data == "settings")
async def cb_settings(call: CallbackQuery):
    settings = load_settings()
    lang = settings.get("language", "ru")
    text = TRANSLATIONS[lang]["settings"].format(
        lang=settings["language"], limit=settings["site_limit"]
    )
    await call.message.edit_text(text, reply_markup=settings_kb(lang))
    await call.answer()


@router.callback_query(F.data == "set_lang")
async def cb_set_lang(call: CallbackQuery):
    settings = load_settings()
    lang = settings.get("language", "ru")
    await call.message.edit_text(
        TRANSLATIONS[lang]["choose_lang"], reply_markup=lang_kb(lang)
    )
    await call.answer()


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(call: CallbackQuery):
    lang = call.data.split(":")[1]
    if lang not in TRANSLATIONS:
        await call.answer("Unsupported", show_alert=True)
        return
    settings = load_settings()
    settings["language"] = lang
    save_settings(settings)
    await call.message.edit_text(
        menu_text(lang), reply_markup=main_menu_kb(lang)
    )
    await call.answer(TRANSLATIONS[lang]["lang_updated"].format(lang=lang))


@router.callback_query(F.data == "set_limit")
async def cb_set_limit(call: CallbackQuery, state: FSMContext):
    settings = load_settings()
    lang = settings.get("language", "ru")
    await state.set_state(SettingsFSM.waiting_limit)
    await call.message.edit_text(
        TRANSLATIONS[lang]["enter_site_limit"].format(max=len(SITES))
    )
    await call.answer()


@router.message(SettingsFSM.waiting_limit)
async def process_limit(message: Message, state: FSMContext):
    settings = load_settings()
    lang = settings.get("language", "ru")
    max_sites = len(SITES)
    try:
        val = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer(
            TRANSLATIONS[lang]["invalid_number"].format(max=max_sites),
            reply_markup=settings_kb(lang),
        )
        return
    if not 1 <= val <= max_sites:
        await message.answer(
            TRANSLATIONS[lang]["invalid_number"].format(max=max_sites),
            reply_markup=settings_kb(lang),
        )
        return
    settings["site_limit"] = val
    save_settings(settings)
    await state.clear()
    await message.answer(
        TRANSLATIONS[lang]["limit_updated"].format(limit=val),
        reply_markup=settings_kb(lang),
    )


# ── Start / Stop ──────────────────────────────────────────────────────────
@router.callback_query(F.data == "start_reg")
async def cb_start_reg(call: CallbackQuery):
    user_id = call.from_user.id
    settings = load_settings()
    lang = settings.get("language", "ru")

    # уже идёт?
    existing = REGISTRATION_TASKS.get(user_id)
    if existing and not existing.done():
        await call.answer(TRANSLATIONS[lang]["reg_already"], show_alert=True)
        return
    if existing:
        REGISTRATION_TASKS.pop(user_id, None)

    targets = SITES[: settings["site_limit"]]
    if not targets:
        await call.answer(TRANSLATIONS[lang]["reg_no_sites"], show_alert=True)
        return

    await call.message.edit_text(
        TRANSLATIONS[lang]["reg_started"].format(
            workers=MAX_CONCURRENT_SITES, limit=len(targets)
        ),
        reply_markup=stop_kb(lang),
    )
    await call.answer()

    http = aiohttp.ClientSession(headers={"User-Agent": UA})

    async def runner():
        try:
            await registration_main(call.bot, user_id, targets, http)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log_event("error", f"runner: {type(e).__name__}: {e}")
        finally:
            try:
                await http.close()
            except Exception:
                pass
            REGISTRATION_TASKS.pop(user_id, None)

    REGISTRATION_TASKS[user_id] = asyncio.create_task(runner())


@router.callback_query(F.data == "stop_reg")
async def cb_stop_reg(call: CallbackQuery):
    user_id = call.from_user.id
    settings = load_settings()
    lang = settings.get("language", "ru")

    task = REGISTRATION_TASKS.get(user_id)
    if not task or task.done():
        REGISTRATION_TASKS.pop(user_id, None)
        await call.answer(TRANSLATIONS[lang]["reg_not_running"], show_alert=True)
        return

    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass
    REGISTRATION_TASKS.pop(user_id, None)

    await call.message.edit_text(
        TRANSLATIONS[lang]["reg_stopped"],
        reply_markup=main_menu_kb(lang, running=False),
    )
    await call.answer()


# ── запуск ────────────────────────────────────────────────────────────────
async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN не задан в переменных окружения")
    if not TG_API_HASH:
        raise SystemExit("TG_API_HASH не задан в переменных окружения")

    log_event("info", "Бот запущен")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
