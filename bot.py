# language: Python, file: bot.py, target: aiogram 3.x + Telethon
# pip install aiogram telethon aiohttp beautifulsoup4 lxml python-dotenv

import asyncio
import json
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path

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

# ── переводы ──────────────────────────────────────────────────────────────
TRANSLATIONS = {
    "ru": {
        "enter_password": "Введите пароль для доступа:",
        "wrong_password": "Неверный пароль.",
        "menu": "Главное меню:",
        "btn_start": "🚀 Запустить регистрацию",
        "btn_accounts": "📱 Аккаунты",
        "btn_logs": "📄 Логи",
        "btn_settings": "⚙️ Настройки",
        "reg_started": "Регистрация запущена. Проверяю сайты...",
        "reg_done": "Регистрация завершена. Успешных: {ok} из {total}",
        "no_accounts": "Аккаунтов пока нет.",
        "account_detail": "Номер: {phone}\nКодов получено: {codes}",
        "btn_back": "⬅️ Назад",
        "btn_get_codes": "📨 Получить код для входа",
        "codes_list": "Коды для {phone}:\n{codes}",
        "settings": "Настройки:\nЯзык: {lang}\nЛимит сайтов: {limit}",
        "btn_sites": "🔢 Кол-во сайтов",
        "btn_lang": "🌐 Смена языка",
        "enter_site_limit": "Введите новое количество сайтов (1–{max}):",
        "invalid_number": "Нужно число от 1 до {max}.",
        "limit_updated": "Лимит обновлён: {limit}",
        "lang_updated": "Язык изменён: {lang}",
        "logs_sent": "Логи отправлены.",
        "no_logs": "Логов пока нет.",
    },
    "en": {
        "enter_password": "Enter access password:",
        "wrong_password": "Wrong password.",
        "menu": "Main menu:",
        "btn_start": "🚀 Start registration",
        "btn_accounts": "📱 Accounts",
        "btn_logs": "📄 Logs",
        "btn_settings": "⚙️ Settings",
        "reg_started": "Registration started. Checking sites...",
        "reg_done": "Registration finished. Success: {ok}/{total}",
        "no_accounts": "No accounts yet.",
        "account_detail": "Phone: {phone}\nCodes received: {codes}",
        "btn_back": "⬅️ Back",
        "btn_get_codes": "📨 Get login code",
        "codes_list": "Codes for {phone}:\n{codes}",
        "settings": "Settings:\nLanguage: {lang}\nSite limit: {limit}",
        "btn_sites": "🔢 Site count",
        "btn_lang": "🌐 Change language",
        "enter_site_limit": "Enter new site limit (1–{max}):",
        "invalid_number": "Number must be 1–{max}.",
        "limit_updated": "Limit updated: {limit}",
        "lang_updated": "Language changed: {lang}",
        "logs_sent": "Logs sent.",
        "no_logs": "No logs yet.",
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
    _save_json(LOGS_FILE, logs[-2000:])  # держим последние 2000 записей


def load_settings() -> dict:
    return _load_json(SETTINGS_FILE, {"language": "ru", "site_limit": 40})


def save_settings(s: dict):
    _save_json(SETTINGS_FILE, s)


def log_event(level: str, message: str):
    logs = load_logs()
    logs.append({
        "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "level": level,
        "message": message,
    })
    save_logs(logs)


def add_account(phone: str, session_file: str):
    accounts = load_accounts()
    accounts.append({
        "phone": phone,
        "session": session_file,
        "codes": [],
        "created": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    })
    save_accounts(accounts)


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


async def fetch_html(session, url: str, timeout: int = 20) -> str | None:
    try:
        async with session.get(url, timeout=timeout) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception:
        pass
    return None


async def wait_for_code(session, url: str, timeout: int = 90, interval: int = 5) -> str | None:
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
    name: str, url: str, session, semaphore: asyncio.Semaphore
) -> dict | None:
    async with semaphore:
        log_event("info", f"{name}: старт")
        html = await fetch_html(session, url)
        if not html:
            log_event("warn", f"{name}: страница не загрузилась")
            return None

        phone = extract_phone(html)
        if not phone:
            log_event("warn", f"{name}: номер не найден")
            return None

        log_event("info", f"{name}: номер {phone}")

        session_file = f"data/session_{phone.lstrip('+')}"
        client = TelegramClient(session_file, TG_API_ID, TG_API_HASH)
        await client.connect()
        try:
            await client.send_code_request(phone)
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
            add_account(phone, session_file)
            add_code_to_account(phone, code)
            return {"name": name, "phone": phone, "id": me.id}
        except PhoneNumberInvalidError:
            log_event("warn", f"{name}: номер не принят")
        except PhoneNumberBannedError:
            log_event("warn", f"{name}: номер забанен")
        except PhoneCodeInvalidError:
            log_event("warn", f"{name}: код неверный")
        except PhoneCodeExpiredError:
            log_event("warn", f"{name}: код истёк")
        except ApiIdInvalidError:
            log_event("error", f"{name}: api_id отклонён")
        except FloodWaitError as e:
            log_event("warn", f"{name}: FloodWait {e.seconds}s")
        except Exception as e:
            log_event("error", f"{name}: {type(e).__name__}: {e}")
        finally:
            await client.disconnect()
        return None


# ── FSM ───────────────────────────────────────────────────────────────────
class Auth(StatesGroup):
    waiting_password = State()


class SettingsFSM(StatesGroup):
    waiting_limit = State()


# ── клавиатуры ────────────────────────────────────────────────────────────
def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    t = TRANSLATIONS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["btn_start"], callback_data="start_reg")],
        [InlineKeyboardButton(text=t["btn_accounts"], callback_data="accounts")],
        [InlineKeyboardButton(text=t["btn_logs"], callback_data="logs")],
        [InlineKeyboardButton(text=t["btn_settings"], callback_data="settings")],
    ])


def accounts_kb(accounts: list[dict], lang: str) -> InlineKeyboardMarkup:
    t = TRANSLATIONS[lang]
    rows = []
    for i, a in enumerate(accounts):
        rows.append([
            InlineKeyboardButton(
                text=f"{a['phone']} ({len(a['codes'])} кодов)",
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


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings")],
    ])


# ── роутер ────────────────────────────────────────────────────────────────
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(Auth.waiting_password)
    await message.answer(TRANSLATIONS[load_settings().get("language", "ru")]["enter_password"])


@router.message(Auth.waiting_password)
async def check_password(message: Message, state: FSMContext):
    settings = load_settings()
    lang = settings.get("language", "ru")
    if message.text.strip() != ACCESS_PASSWORD:
        await message.answer(TRANSLATIONS[lang]["wrong_password"])
        return
    await state.clear()
    await message.answer(TRANSLATIONS[lang]["menu"], reply_markup=main_menu_kb(lang))


@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery):
    settings = load_settings()
    lang = settings.get("language", "ru")
    await call.message.edit_text(
        TRANSLATIONS[lang]["menu"], reply_markup=main_menu_kb(lang)
    )
    await call.answer()


@router.callback_query(F.data == "accounts")
async def cb_accounts(call: CallbackQuery):
    settings = load_settings()
    lang = settings.get("language", "ru")
    accounts = load_accounts()
    if not accounts:
        await call.message.edit_text(TRANSLATIONS[lang]["no_accounts"])
        await call.answer()
        return
    await call.message.edit_text(
        "Аккаунты:" if lang == "ru" else "Accounts:",
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
        phone=a["phone"], codes=len(a["codes"])
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
        text = "Кодов нет." if lang == "ru" else "No codes."
    else:
        text = TRANSLATIONS[lang]["codes_list"].format(
            phone=a["phone"], codes="\n".join(codes)
        )
    await call.message.answer(text)
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
    await call.message.edit_text("Выберите язык / Choose language:", reply_markup=lang_kb())
    await call.answer()


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(call: CallbackQuery):
    lang = call.data.split(":")[1]
    settings = load_settings()
    settings["language"] = lang
    save_settings(settings)
    await call.message.edit_text(
        TRANSLATIONS[lang]["lang_updated"].format(lang=lang),
        reply_markup=main_menu_kb(lang),
    )
    await call.answer()


@router.callback_query(F.data == "set_limit")
async def cb_set_limit(call: CallbackQuery, state: FSMContext):
    settings = load_settings()
    lang = settings.get("language", "ru")
    max_sites = len(SITES)
    await state.set_state(SettingsFSM.waiting_limit)
    await call.message.edit_text(
        TRANSLATIONS[lang]["enter_site_limit"].format(max=max_sites)
    )
    await call.answer()


@router.message(SettingsFSM.waiting_limit)
async def process_limit(message: Message, state: FSMContext):
    settings = load_settings()
    lang = settings.get("language", "ru")
    max_sites = len(SITES)
    try:
        val = int(message.text.strip())
    except ValueError:
        await message.answer(TRANSLATIONS[lang]["invalid_number"].format(max=max_sites))
        return
    if not 1 <= val <= max_sites:
        await message.answer(TRANSLATIONS[lang]["invalid_number"].format(max=max_sites))
        return
    settings["site_limit"] = val
    save_settings(settings)
    await state.clear()
    await message.answer(
        TRANSLATIONS[lang]["limit_updated"].format(limit=val),
        reply_markup=settings_kb(lang),
    )


@router.callback_query(F.data == "start_reg")
async def cb_start_reg(call: CallbackQuery):
    settings = load_settings()
    lang = settings.get("language", "ru")
    await call.message.edit_text(TRANSLATIONS[lang]["reg_started"])
    await call.answer()

    async def run_registration():
        import aiohttp

        limit = settings["site_limit"]
        targets = SITES[:limit]
        sem = asyncio.Semaphore(5)  # не более 5 сайтов одновременно

        async with aiohttp.ClientSession(headers={"User-Agent": UA}) as http:
            tasks = [try_site(name, url, http, sem) for name, url in targets]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        ok = sum(1 for r in results if isinstance(r, dict))
        log_event("info", f"Регистрация завершена: успешно {ok}/{len(targets)}")
        await call.message.answer(
            TRANSLATIONS[lang]["reg_done"].format(ok=ok, total=len(targets))
        )

    asyncio.create_task(run_registration())


# ── запуск ────────────────────────────────────────────────────────────────
async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN не задан в .env")
    if not TG_API_HASH:
        raise SystemExit("TG_API_HASH не задан в .env")

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
