# language: Python, file: bot.py, target: aiogram 3.x + Telethon + Playwright
# pip install -r requirements.txt && playwright install chromium && playwright install-deps chromium

import asyncio
import json
import os
import re
import time
import secrets
import string
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery, FSInputFile, InlineKeyboardButton,
    InlineKeyboardMarkup, Message,
)
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Browser, Playwright
from telethon import TelegramClient
from telethon.errors import (
    ApiIdInvalidError, FloodWaitError, PhoneCodeExpiredError,
    PhoneCodeInvalidError, PhoneNumberBannedError,
    PhoneNumberFloodError, PhoneNumberInvalidError,
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
DEAD_FILE = DATA_DIR / "dead_numbers.json"
SELECTORS_FILE = DATA_DIR / "selectors.json"
DEAD_SITES_FILE = DATA_DIR / "dead_sites.json"
SITE_FAILS_FILE = DATA_DIR / "site_fails.json"

# ── 70 сайтов ────────────────────────────────────────────────────────────
SITES: list[tuple[str, str]] = [
    ("asms.ai", "https://asms.ai/"),
    ("Receive-SMS-Free", "https://receive-sms-free.cc/"),
    ("Receive-SMS.io", "https://receive-sms.io/"),
    ("SMSToMe", "https://smstome.com/"),
    ("TempNumber", "https://temp-number.com/"),
    ("Receive-SMSS", "https://receive-smss.com/"),
    ("Quackr", "https://quackr.io/"),
    ("SMS24", "https://sms24.me/en/"),
    ("Jiemahao", "https://jiemahao.com/"),
    ("FreePhoneNum", "https://freephonenum.com/"),
    ("SMSReceiveFree", "https://smsreceivefree.com/"),
    ("OKSMS", "https://oksms.org/"),
    ("ReceiveSMS.org", "https://receivesms.org/"),
    ("Temporary-Phone-Number", "https://temporary-phone-number.com/"),
    ("Receive-A-SMS", "https://receive-a-sms.com/"),
    ("SMS-Online", "https://sms-online.co/receive-free-sms"),
    ("SMSReceiveOnline", "https://smsreceiveonline.com/"),
    ("GetFreeSMSNumber", "https://getfreesmsnumber.com/"),
    ("SMS-Receive.net", "https://sms-receive.net/"),
    ("ReceiveSMSOnline.net", "https://receivesmsonline.net/"),
    ("FreeSMSVerifications", "http://freesmsverifications.com/"),
    ("7Sim", "http://7sim.net/"),
    ("HS3X", "http://hs3x.com/"),
    ("ReceiveFreeSMS", "http://receivefreesms.com/"),
    ("ReceiveFreeSMS.net", "http://receivefreesms.net/"),
    ("ReceiveSMSOnline.in", "http://receivesmsonline.in/"),
    ("Receive-SMS-Online", "https://receive-sms-online.com/"),
    ("SMSVer", "https://smsver.com/"),
    ("Groovl", "https://groovl.com/"),
    ("SMS.Sellaite", "http://sms.sellaite.com/"),
    ("SendSMSNow", "http://sendsmsnow.com/"),
    ("ReceiveSMSOnline.eu", "http://receivesmsonline.eu/"),
    ("Proovl", "https://proovl.com/numbers"),
    ("Anon-SMS", "https://anon-sms.com/"),
    ("HideMyNumbers", "http://hidemynumbers.com/"),
    ("Pinger", "https://pinger.com/"),
    ("FreeOnlinePhone", "https://freeonlinephone.org/"),
    ("CatchSMS", "https://catchsms.com/"),
    ("ReceiveSMS.co", "https://www.receivesms.co/"),
    ("MyTrashMobile", "https://zh.mytrashmobile.com/"),
    ("FreePhoneNum.ch", "https://ch.freephonenum.com/"),
    ("ReceiveFreeSMS.com", "http://receivefreesms.com/"),
    ("ReceiveSMSOnline.net", "https://www.receivesmsonline.net/"),
    ("FreeOnlinePhone.org", "https://www.freeonlinephone.org/"),
    ("Receive-SMS-Online.com", "http://receive-sms-online.com/"),
    ("TextNow", "https://www.textnow.com/"),
    ("PingerTextFree", "https://www.pinger.com/text-free/"),
    ("SMS.Sellaite.ee", "http://sms.sellaite.com/"),
    ("Twilio", "https://www.twilio.com/"),
    ("ReceiveFreeSMS.net", "http://receivefreesms.net/"),
    ("Receive-SMS-Online.info", "https://www.receive-sms-online.info/"),
    ("SMS-Receive.net", "https://sms-receive.net/"),
    ("Receive-SMS-Now", "http://www.receive-sms-now.com/"),
    ("ReceivesSMSOnline.in", "http://receivesmsonline.in/"),
    ("SMSNumbersOnline", "https://smsnumbersonline.com/"),
    ("SMS-Online.co", "https://sms-online.co/receive-free-sms"),
    ("Receive-SMS.com", "https://receive-sms.com/"),
    ("ReceivesSMSVerification", "http://receivesmsverification.com/"),
    ("ReceiveOnlineSMS.biz", "http://receiveonlinesms.biz/"),
    ("Temp-SMS.org", "https://temp-sms.org/"),
    ("IReceiveSMS", "https://ireceivesms.com/"),
    ("AnonymSMS", "https://anonymsms.com/"),
    ("Free-SMS-Receive", "https://free-sms-receive.com/"),
    ("SMS-Receive-Online", "https://sms-receive-online.com/"),
    ("Supercloudsms", "https://supercloudsms.com/"),
    ("Textr", "https://textrapp.com/free-tools/textr-free-receive-sms-online-tool"),
    ("TempSMS", "https://tempsmss.com/receive-sms/"),
    ("GetVirtualPhoneNumber", "https://getvirtualphonenumber.com/"),
    ("SMSZ.net", "https://www.smsz.net/free-numbers"),
    ("SMSApe", "https://smsape.com/"),
    ("Yunduanxin", "https://yunduanxin.net/"),
]

SMS_WAIT = 90
SMS_POLL_INTERVAL = 7
MAX_CONCURRENT_SITES = 3
WORKER_SLEEP_BETWEEN = 2
FLOOD_THRESHOLD = 3600
MAX_SITE_FAILS = 50

REGISTRATION_TASKS: dict[int, asyncio.Task] = {}
IN_FLIGHT_PHONES: set[str] = set()
LAST_SEEN_PHONE: dict[str, str] = {}
SITE_LOCKS: dict[str, asyncio.Lock] = {name: asyncio.Lock() for name, _ in SITES}
SITE_FAILS: dict[str, int] = {}

PW: Playwright | None = None
BROWSER: Browser | None = None


# ── переводы (сокращенно) ─────────────────────────────────────────────────
TRANSLATIONS = {
    "ru": {
        "enter_password": "🔐 <b>Добро пожаловать!</b>\n\nВведите пароль:",
        "wrong_password": "❌ Неверный пароль.",
        "menu": "🏠 <b>Меню</b>\n👤 Аккаунтов: <b>{accounts}</b>\n🌐 Сайтов: <b>{limit}/{total}</b>\n💀 Мёртвых сайтов: <b>{dead_sites}</b>",
        "btn_start": "🚀 Запустить", "btn_stop": "🛑 Остановить",
        "btn_accounts": "👤 Аккаунты", "btn_stats": "📊 Статистика", "btn_logs": "📄 Логи", "btn_settings": "⚙️ Настройки",
        "btn_back": "⬅️ Назад",
        "reg_started": "🚀 <b>Регистрация запущена!</b>\n🔄 Потоков: <b>{workers}</b>\n🌐 Сайтов: <b>{limit}</b>",
        "reg_stopped": "🛑 <b>Остановлена</b>", "reg_already": "⚠️ Уже идёт.", "reg_not_running": "ℹ️ Не запущена.", "reg_no_sites": "⚠️ Нет активных сайтов.",
        "account_created_notify": "🎉 <b>Создан!</b>\n📱 <code>{phone}</code>\n🆔 <code>{uid}</code>\n📛 {name}\n🌐 {site}\n🔑 2FA: <code>{password}</code>",
        "no_accounts": "👤 Нет аккаунтов.", "accounts_title": "👤 <b>Аккаунты</b>",
        "account_detail": "👤 <b>Аккаунт</b>\n📱 <code>{phone}</code>\n📨 Кодов: <b>{codes}</b>\n🕐 {created}",
        "btn_get_codes": "📨 Коды", "btn_get_2fa": "🔑 2FA",
        "codes_list": "📨 <b>{phone}</b>\n{codes}", "codes_empty": "📭 Нет кодов.",
        "account_2fa": "🔑 <b>2FA</b>\n📱 {phone}\n🔑 <code>{password}</code>", "no_2fa": "⚠️ Нет 2FA.",
        "stats_text": "📊 <b>Статистика</b>\n✅ Создано: {created}\n📨 Запрошено: {requested}\n❌ Неверных: {invalid}\n💀 Мёртвых сайтов: {dead_sites}\n🕐 {now}",
        "settings": "⚙️ <b>Настройки</b>\n🌐 Язык: <b>{lang}</b>\n🔢 Сайтов: <b>{limit}</b>",
        "btn_sites": "🔢 Сайты", "btn_lang": "🌐 Язык", "enter_site_limit": "1–{max}:",
        "invalid_number": "⚠️ 1–{max}.", "limit_updated": "✅ <b>{limit}</b>", "lang_updated": "✅ <b>{lang}</b>",
        "logs_sent": "📄 Логи.", "no_logs": "📭 Пусто.", "logout_done": "👋 Выход.", "choose_lang": "🌐 Язык:",
    },
}

# ── JSON helpers ──────────────────────────────────────────────────────────
def _load_json(path: Path, default):
    if not path.exists(): return default
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default

def _save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_accounts() -> list[dict]: return _load_json(ACCOUNTS_FILE, [])
def save_accounts(accounts: list[dict]): _save_json(ACCOUNTS_FILE, accounts)
def load_logs() -> list[dict]: return _load_json(LOGS_FILE, [])
def save_logs(logs: list[dict]): _save_json(LOGS_FILE, logs[-2000:])
def load_settings() -> dict: return _load_json(SETTINGS_FILE, {"language": "ru", "site_limit": len(SITES)})
def save_settings(s: dict): _save_json(SETTINGS_FILE, s)
def load_stats() -> dict: return _load_json(STATS_FILE, {"accounts_created": 0, "codes_requested": 0, "invalid_codes": 0})
def save_stats(s: dict): _save_json(STATS_FILE, s)
def increment_stat(key: str, amount: int = 1):
    s = load_stats(); s[key] = s.get(key, 0) + amount; save_stats(s)
def load_authorized() -> dict: return _load_json(AUTHORIZED_FILE, {})
def save_authorized(data: dict): _save_json(AUTHORIZED_FILE, data)
def is_authorized(user_id: int) -> bool: return str(user_id) in load_authorized()
def add_authorized(user_id: int):
    data = load_authorized(); data[str(user_id)] = datetime.utcnow().isoformat() + "Z"; save_authorized(data)
def remove_authorized(user_id: int):
    data = load_authorized(); data.pop(str(user_id), None); save_authorized(data)
def load_dead() -> dict: return _load_json(DEAD_FILE, {})
def save_dead(data: dict): _save_json(DEAD_FILE, data)
def is_dead(phone: str) -> bool: return phone in load_dead()
def mark_dead(phone: str, reason: str):
    data = load_dead(); data[phone] = {"reason": reason, "ts": datetime.utcnow().isoformat() + "Z"}; save_dead(data)

def load_dead_sites() -> set[str]:
    return set(_load_json(DEAD_SITES_FILE, []))

def save_dead_sites(sites: set[str]):
    _save_json(DEAD_SITES_FILE, sorted(sites))

def mark_site_dead(site: str):
    dead = load_dead_sites()
    dead.add(site)
    save_dead_sites(dead)
    log_event("warn", f"{site}: отправлен в ЧС после {MAX_SITE_FAILS} ошибок")

def load_site_fails() -> dict:
    return _load_json(SITE_FAILS_FILE, {})

def save_site_fails(data: dict):
    _save_json(SITE_FAILS_FILE, data)

def increment_site_fail(site: str):
    data = load_site_fails()
    data[site] = data.get(site, 0) + 1
    save_site_fails(data)
    if data[site] >= MAX_SITE_FAILS:
        mark_site_dead(site)

def log_event(level: str, message: str):
    logs = load_logs()
    logs.append({"ts": datetime.utcnow().isoformat() + "Z", "level": level, "message": message})
    save_logs(logs)

def add_account(phone: str, session_file: str, password_2fa: str | None = None) -> dict:
    accounts = load_accounts()
    entry = {"phone": phone, "session": session_file, "codes": [], "password_2fa": password_2fa, "created": datetime.utcnow().isoformat() + "Z"}
    accounts.append(entry); save_accounts(accounts); return entry

def add_code_to_account(phone: str, code: str):
    accounts = load_accounts()
    for a in accounts:
        if a["phone"] == phone: a["codes"].append(code); break
    save_accounts(accounts)

# ── селекторы ────────────────────────────────────────────────────────────
def load_selectors() -> dict: return _load_json(SELECTORS_FILE, {})
def save_selectors(data: dict): _save_json(SELECTORS_FILE, data)

def remember_selector(site: str, selector: str):
    data = load_selectors(); data[site] = selector; save_selectors(data)
    log_event("info", f"{site}: запомнил селектор {selector}")

def get_selector(site: str) -> str | None: return load_selectors().get(site)

def build_selector(tag) -> str:
    if tag.get("id"): return f"{tag.name}#{tag['id']}"
    classes = tag.get("class")
    if classes: return f"{tag.name}.{classes[0]}"
    return tag.name

# ── парсинг номера ────────────────────────────────────────────────────────
STRICT_PHONE_RE = re.compile(
    r"\+(?:1|7|20|27|30|31|32|33|34|36|39|40|41|43|44|45|46|47|48|49|"
    r"51|52|53|54|55|56|57|58|60|61|62|63|64|65|66|81|82|84|86|90|91|"
    r"92|93|94|95|98|212|213|216|218|220|221|222|223|224|225|226|227|"
    r"228|229|230|231|232|233|234|235|236|237|238|239|240|241|242|243|"
    r"244|245|246|247|248|249|250|251|252|253|254|255|256|257|258|260|"
    r"261|262|263|264|265|266|267|268|269|290|291|297|298|299|350|351|"
    r"352|353|354|355|356|357|358|359|370|371|372|373|374|375|376|377|"
    r"378|380|381|382|383|385|386|387|389|420|421|423|500|501|502|503|"
    r"504|505|506|507|508|509|590|591|592|593|594|595|596|597|598|599|"
    r"670|672|673|674|675|676|677|678|679|680|681|682|683|685|686|687|"
    r"688|689|690|691|692|850|852|853|855|856|880|886|960|961|962|963|"
    r"964|965|966|967|968|970|971|972|973|974|975|976|977|992|993|994|"
    r"995|996|998)"
    r"[\s\-]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}"
)

def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"[^\d+]", "", raw)
    if digits.startswith("+"): digits = digits[1:]
    if len(digits) < 9 or len(digits) > 15 or digits.startswith("0"): return None
    return "+" + digits

def extract_phone_and_url(html: str) -> tuple[str | None, str | None]:
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/number/" in href:
            m = STRICT_PHONE_RE.search(a.get_text(" ", strip=True)) or STRICT_PHONE_RE.search(href)
            if m:
                p = normalize_phone(m.group(0))
                if p: return p, href
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "?id=" in href or "/temporary-numbers/" in href or "/sms/" in href:
            m = STRICT_PHONE_RE.search(a.get_text(" ", strip=True)) or STRICT_PHONE_RE.search(href)
            if m:
                p = normalize_phone(m.group(0))
                if p: return p, href
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "smstome.com" in href or href.startswith("/"):
            m = STRICT_PHONE_RE.search(href)
            if m:
                p = normalize_phone(m.group(0))
                if p: return p, href
    for m in STRICT_PHONE_RE.finditer(html):
        p = normalize_phone(m.group(0))
        if p: return p, None
    return None, None

# ── самообучающийся код ──────────────────────────────────────────────────
def extract_code_smart(html: str, site: str | None = None) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    if site:
        selector = get_selector(site)
        if selector:
            try:
                for block in soup.select(selector):
                    text = block.get_text(" ", strip=True)
                    if "telegram" in text.lower() or "777000" in text:
                        m = re.search(r"(?<![\d+])(\d{5,6})(?![\d])", text)
                        if m: return m.group(1)
            except Exception:
                pass
    candidates = []
    for tag in soup.find_all(string=re.compile(r"telegram|777000", re.I)):
        parent = tag.parent
        for _ in range(6):
            if parent is None or parent.name in ("body", "html", "main"): break
            text = parent.get_text(" ", strip=True)
            m = re.search(r"(?<![\d+])(\d{5,6})(?![\d])", text)
            if m:
                candidates.append((parent, m.group(1))); break
            parent = parent.parent
    if not candidates: return None
    best_parent, code = candidates[-1]
    if site: remember_selector(site, build_selector(best_parent))
    return code

# ── Playwright fetch ──────────────────────────────────────────────────────
async def fetch_html(url: str, wait_until: str = "networkidle", timeout: int = 30000) -> str | None:
    if BROWSER is None: return None
    page = None
    try:
        page = await BROWSER.new_page()
        await page.goto(url, wait_until=wait_until, timeout=timeout)
        await page.wait_for_timeout(2000)
        return await page.content()
    except Exception as e:
        log_event("warn", f"Playwright ошибка при {url}: {type(e).__name__}")
        return None
    finally:
        if page:
            try: await page.close()
            except Exception: pass

async def wait_for_code(url: str, site: str, timeout: int = SMS_WAIT, interval: int = SMS_POLL_INTERVAL) -> str | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        await asyncio.sleep(interval)
        html = await fetch_html(url)
        if not html: continue
        code = extract_code_smart(html, site)
        if code: return code
    return None

# ── 2FA и регистрация ─────────────────────────────────────────────────────
def gen_2fa_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(12))

async def try_site(name: str, url: str, bot: Bot, user_id: int) -> dict | None:
    lock = SITE_LOCKS[name]
    if lock.locked(): return None
    async with lock:
        log_event("info", f"{name}: старт")
        html = await fetch_html(url)
        if not html:
            increment_site_fail(name); log_event("warn", f"{name}: страница не загрузилась"); return None
        phone, phone_page = extract_phone_and_url(html)
        if not phone:
            increment_site_fail(name); log_event("warn", f"{name}: номер не найден"); return None
        if LAST_SEEN_PHONE.get(name) == phone:
            log_event("info", f"{name}: номер {phone} не изменился, пауза 3 мин")
            await asyncio.sleep(180); return None
        LAST_SEEN_PHONE[name] = phone
        if is_dead(phone):
            log_event("info", f"{name}: номер {phone} в blacklist, пропуск"); return None
        if phone in IN_FLIGHT_PHONES:
            log_event("info", f"{name}: номер {phone} уже обрабатывается"); return None
        if any(a["phone"] == phone for a in load_accounts()):
            log_event("info", f"{name}: номер {phone} уже зарегистрирован"); return None
        if phone_page and not phone_page.startswith("http"):
            phone_page = urljoin(url, phone_page)
        IN_FLIGHT_PHONES.add(phone)
        log_event("info", f"{name}: номер {phone}")
        session_file = f"data/session_{phone.lstrip('+')}"
        client = TelegramClient(session_file, TG_API_ID, TG_API_HASH)
        is_success = False
        try:
            await client.connect()
            await client.send_code_request(phone)
            increment_stat("codes_requested")
            log_event("info", f"{name}: код запрошен у Telegram")
            code = await wait_for_code(phone_page or url, site=name)
            if not code:
                log_event("warn", f"{name}: SMS не пришёл"); return None
            log_event("info", f"{name}: код {code} из SMS")
            try: await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                log_event("warn", f"{name}: 2FA на номере уже стоит, пропуск"); return None
            me = await client.get_me()
            pwd_2fa = gen_2fa_password()
            try: await client.edit_2fa(new_password=pwd_2fa)
            except Exception as e: log_event("warn", f"{name}: 2FA не установлен — {e}"); pwd_2fa = None
            is_success = True
            log_event("success", f"{name}: аккаунт создан id={me.id} phone={phone}")
            increment_stat("accounts_created")
            add_account(phone, session_file, pwd_2fa)
            add_code_to_account(phone, code)
            try:
                await bot.send_message(user_id, TRANSLATIONS["ru"]["account_created_notify"].format(
                    phone=phone, uid=me.id, name=me.first_name or "—",
                    site=name, total=len(load_accounts()), password=pwd_2fa or "не установлен"))
            except Exception: pass
            return {"name": name, "phone": phone, "id": me.id}
        except PhoneNumberInvalidError: mark_dead(phone, "invalid"); log_event("warn", f"{name}: номер не принят → blacklist")
        except PhoneNumberBannedError: mark_dead(phone, "banned"); log_event("warn", f"{name}: номер забанен → blacklist")
        except PhoneNumberFloodError: mark_dead(phone, "phone_flood"); log_event("warn", f"{name}: номер флужен → blacklist")
        except PhoneCodeInvalidError: increment_stat("invalid_codes"); log_event("warn", f"{name}: код неверный")
        except PhoneCodeExpiredError: log_event("warn", f"{name}: код истёк")
        except ApiIdInvalidError: log_event("error", f"{name}: api_id отклонён")
        except FloodWaitError as e:
            if e.seconds >= FLOOD_THRESHOLD: mark_dead(phone, f"flood_{e.seconds}s"); log_event("warn", f"{name}: FloodWait {e.seconds}s → blacklist")
            else:
                log_event("warn", f"{name}: FloodWait {e.seconds}s")
                try: await asyncio.sleep(min(e.seconds, 60))
                except asyncio.CancelledError: raise
        except Exception as e: log_event("error", f"{name}: {type(e).__name__}: {e}")
        finally:
            try: await client.disconnect()
            except Exception: pass
            if not is_success:
                sp = Path(f"{session_file}.session")
                if sp.exists():
                    try: sp.unlink()
                    except Exception: pass
            IN_FLIGHT_PHONES.discard(phone)
        return None

# ── воркеры ───────────────────────────────────────────────────────────────
async def worker(bot: Bot, user_id: int, targets: list[tuple[str, str]], worker_id: int):
    idx = worker_id % len(targets) if targets else 0
    while True:
        if not targets: await asyncio.sleep(5); continue
        name, url = targets[idx % len(targets)]
        idx += 1
        try: await try_site(name, url, bot, user_id)
        except asyncio.CancelledError: raise
        except Exception as e: log_event("error", f"w{worker_id}: {e}")
        try: await asyncio.sleep(WORKER_SLEEP_BETWEEN)
        except asyncio.CancelledError: raise

async def registration_main(bot: Bot, user_id: int, targets: list[tuple[str, str]]):
    workers = [asyncio.create_task(worker(bot, user_id, targets, i)) for i in range(MAX_CONCURRENT_SITES)]
    try: await asyncio.gather(*workers)
    except asyncio.CancelledError:
        for w in workers: w.cancel()
        for w in workers:
            try: await w
            except: pass
        raise

# ── FSM ───────────────────────────────────────────────────────────────────
class Auth(StatesGroup): waiting_password = State()
class SettingsFSM(StatesGroup): waiting_limit = State()

# ── клавиатуры ────────────────────────────────────────────────────────────
def menu_text() -> str:
    s = load_settings()
    dead_sites = len(load_dead_sites())
    return TRANSLATIONS["ru"]["menu"].format(
        accounts=len(load_accounts()), limit=s["site_limit"], total=len(SITES), dead_sites=dead_sites)

def main_menu_kb(running: bool = False) -> InlineKeyboardMarkup:
    t = TRANSLATIONS["ru"]; rows = []
    if running: rows.append([InlineKeyboardButton(text=t["btn_stop"], callback_data="stop_reg")])
    else: rows.append([InlineKeyboardButton(text=t["btn_start"], callback_data="start_reg")])
    rows.append([InlineKeyboardButton(text=t["btn_accounts"], callback_data="accounts"), InlineKeyboardButton(text=t["btn_stats"], callback_data="stats")])
    rows.append([InlineKeyboardButton(text=t["btn_logs"], callback_data="logs"), InlineKeyboardButton(text=t["btn_settings"], callback_data="settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def stop_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=TRANSLATIONS["ru"]["btn_stop"], callback_data="stop_reg")]])

def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=TRANSLATIONS["ru"]["btn_back"], callback_data="menu")]])

def accounts_kb(accounts: list[dict]) -> InlineKeyboardMarkup:
    t = TRANSLATIONS["ru"]; rows = []
    for i, a in enumerate(accounts):
        rows.append([InlineKeyboardButton(text=f"{a['phone']} · {len(a['codes'])}", callback_data=f"acc:{i}")])
    rows.append([InlineKeyboardButton(text=t["btn_back"], callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def account_detail_kb(idx: int) -> InlineKeyboardMarkup:
    t = TRANSLATIONS["ru"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["btn_get_codes"], callback_data=f"codes:{idx}")],
        [InlineKeyboardButton(text=t["btn_get_2fa"], callback_data=f"acc2fa:{idx}")],
        [InlineKeyboardButton(text=t["btn_back"], callback_data="accounts")],
    ])

def settings_kb() -> InlineKeyboardMarkup:
    t = TRANSLATIONS["ru"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["btn_sites"], callback_data="set_limit"), InlineKeyboardButton(text=t["btn_lang"], callback_data="set_lang")],
        [InlineKeyboardButton(text=t["btn_back"], callback_data="menu")],
    ])

def lang_kb() -> InlineKeyboardMarkup:
    t = TRANSLATIONS["ru"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"), InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(text=t["btn_back"], callback_data="settings")],
    ])

# ── роутер ────────────────────────────────────────────────────────────────
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    if is_authorized(message.from_user.id):
        await state.clear()
        running = message.from_user.id in REGISTRATION_TASKS
        await message.answer(menu_text(), reply_markup=main_menu_kb(running))
        return
    await state.set_state(Auth.waiting_password)
    await message.answer(TRANSLATIONS["ru"]["enter_password"])

@router.message(Auth.waiting_password)
async def check_password(message: Message, state: FSMContext):
    if not message.text or message.text.strip() != ACCESS_PASSWORD:
        await message.answer(TRANSLATIONS["ru"]["wrong_password"])
        return
    add_authorized(message.from_user.id)
    log_event("info", f"Авторизация id={message.from_user.id}")
    await state.clear()
    running = message.from_user.id in REGISTRATION_TASKS
    await message.answer(menu_text(), reply_markup=main_menu_kb(running))

@router.message(F.text == "/logout")
async def cmd_logout(message: Message, state: FSMContext):
    remove_authorized(message.from_user.id)
    await state.clear()
    await message.answer(TRANSLATIONS["ru"]["logout_done"])

@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery):
    running = call.from_user.id in REGISTRATION_TASKS
    await call.message.edit_text(menu_text(), reply_markup=main_menu_kb(running))
    await call.answer()

@router.callback_query(F.data == "accounts")
async def cb_accounts(call: CallbackQuery):
    accounts = load_accounts()
    if not accounts:
        await call.message.edit_text(TRANSLATIONS["ru"]["no_accounts"], reply_markup=back_kb())
        await call.answer(); return
    await call.message.edit_text(TRANSLATIONS["ru"]["accounts_title"], reply_markup=accounts_kb(accounts))
    await call.answer()

@router.callback_query(F.data.startswith("acc:"))
async def cb_account_detail(call: CallbackQuery):
    idx = int(call.data.split(":")[1])
    accounts = load_accounts()
    if idx >= len(accounts):
        await call.answer("Not found", show_alert=True); return
    a = accounts[idx]
    text = TRANSLATIONS["ru"]["account_detail"].format(
        phone=a["phone"], codes=len(a.get("codes", [])), created=a.get("created", "—"))
    await call.message.edit_text(text, reply_markup=account_detail_kb(idx))
    await call.answer()

@router.callback_query(F.data.startswith("codes:"))
async def cb_get_codes(call: CallbackQuery):
    idx = int(call.data.split(":")[1])
    accounts = load_accounts()
    if idx >= len(accounts):
        await call.answer("Not found", show_alert=True); return
    a = accounts[idx]
    codes = a.get("codes", [])
    if not codes:
        await call.answer(TRANSLATIONS["ru"]["codes_empty"], show_alert=True); return
    text = TRANSLATIONS["ru"]["codes_list"].format(
        phone=a["phone"], codes="\n".join(f"• <code>{c}</code>" for c in codes))
    await call.message.answer(text)
    await call.answer()

@router.callback_query(F.data.startswith("acc2fa:"))
async def cb_acc_2fa(call: CallbackQuery):
    idx = int(call.data.split(":")[1])
    accounts = load_accounts()
    if idx >= len(accounts):
        await call.answer("Not found", show_alert=True); return
    a = accounts[idx]; pwd = a.get("password_2fa")
    if not pwd:
        await call.answer(TRANSLATIONS["ru"]["no_2fa"], show_alert=True); return
    await call.message.answer(TRANSLATIONS["ru"]["account_2fa"].format(phone=a["phone"], password=pwd))
    await call.answer()

@router.callback_query(F.data == "stats")
async def cb_stats(call: CallbackQuery):
    s = load_stats()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    text = TRANSLATIONS["ru"]["stats_text"].format(
        created=s.get("accounts_created", 0), requested=s.get("codes_requested", 0),
        invalid=s.get("invalid_codes", 0), dead_sites=len(load_dead_sites()), now=now)
    await call.message.edit_text(text, reply_markup=back_kb())
    await call.answer()

@router.callback_query(F.data == "logs")
async def cb_logs(call: CallbackQuery):
    logs = load_logs()
    if not logs:
        await call.answer(TRANSLATIONS["ru"]["no_logs"], show_alert=True); return
    path = DATA_DIR / "logs_export.json"
    _save_json(path, logs)
    await call.message.answer_document(FSInputFile(path, filename="logs.json"), caption=TRANSLATIONS["ru"]["logs_sent"])
    await call.answer()

@router.callback_query(F.data == "settings")
async def cb_settings(call: CallbackQuery):
    s = load_settings()
    text = TRANSLATIONS["ru"]["settings"].format(lang=s["language"], limit=s["site_limit"])
    await call.message.edit_text(text, reply_markup=settings_kb())
    await call.answer()

@router.callback_query(F.data == "set_lang")
async def cb_set_lang(call: CallbackQuery):
    await call.message.edit_text(TRANSLATIONS["ru"]["choose_lang"], reply_markup=lang_kb())
    await call.answer()

@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(call: CallbackQuery):
    lang = call.data.split(":")[1]
    if lang not in TRANSLATIONS:
        await call.answer("Unsupported", show_alert=True); return
    s = load_settings(); s["language"] = lang; save_settings(s)
    await call.message.edit_text(menu_text(), reply_markup=main_menu_kb())
    await call.answer(TRANSLATIONS["ru"]["lang_updated"].format(lang=lang))

@router.callback_query(F.data == "set_limit")
async def cb_set_limit(call: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsFSM.waiting_limit)
    await call.message.edit_text(TRANSLATIONS["ru"]["enter_site_limit"].format(max=len(SITES)))
    await call.answer()

@router.message(SettingsFSM.waiting_limit)
async def process_limit(message: Message, state: FSMContext):
    max_sites = len(SITES)
    try: val = int(message.text.strip())
    except: await message.answer(TRANSLATIONS["ru"]["invalid_number"].format(max=max_sites), reply_markup=settings_kb()); return
    if not 1 <= val <= max_sites:
        await message.answer(TRANSLATIONS["ru"]["invalid_number"].format(max=max_sites), reply_markup=settings_kb()); return
    s = load_settings(); s["site_limit"] = val; save_settings(s)
    await state.clear()
    await message.answer(TRANSLATIONS["ru"]["limit_updated"].format(limit=val), reply_markup=settings_kb())

@router.callback_query(F.data == "start_reg")
async def cb_start_reg(call: CallbackQuery):
    user_id = call.from_user.id
    existing = REGISTRATION_TASKS.get(user_id)
    if existing and not existing.done():
        await call.answer(TRANSLATIONS["ru"]["reg_already"], show_alert=True); return
    if existing: REGISTRATION_TASKS.pop(user_id, None)
    dead = load_dead_sites()
    active = [(n, u) for n, u in SITES if n not in dead]
    targets = active[: load_settings()["site_limit"]]
    if not targets:
        await call.answer(TRANSLATIONS["ru"]["reg_no_sites"], show_alert=True); return
    await call.message.edit_text(
        TRANSLATIONS["ru"]["reg_started"].format(workers=MAX_CONCURRENT_SITES, limit=len(targets)),
        reply_markup=stop_kb())
    await call.answer()
    async def runner():
        try: await registration_main(call.bot, user_id, targets)
        except asyncio.CancelledError: pass
        except Exception as e: log_event("error", f"runner: {e}")
        finally: REGISTRATION_TASKS.pop(user_id, None)
    REGISTRATION_TASKS[user_id] = asyncio.create_task(runner())

@router.callback_query(F.data == "stop_reg")
async def cb_stop_reg(call: CallbackQuery):
    user_id = call.from_user.id
    task = REGISTRATION_TASKS.get(user_id)
    if not task or task.done():
        REGISTRATION_TASKS.pop(user_id, None)
        await call.answer(TRANSLATIONS["ru"]["reg_not_running"], show_alert=True); return
    task.cancel()
    try: await task
    except: pass
    REGISTRATION_TASKS.pop(user_id, None)
    await call.message.edit_text(TRANSLATIONS["ru"]["reg_stopped"], reply_markup=main_menu_kb(running=False))
    await call.answer()

# ── запуск ────────────────────────────────────────────────────────────────
async def main():
    global PW, BROWSER
    if not BOT_TOKEN: raise SystemExit("BOT_TOKEN не задан")
    if not TG_API_HASH: raise SystemExit("TG_API_HASH не задан")
    log_event("info", "Запуск Playwright...")
    PW = await async_playwright().start()
    BROWSER = await PW.chromium.launch(headless=True)
    log_event("info", "Playwright готов")
    log_event("info", "Бот запущен")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    try: await dp.start_polling(bot)
    finally:
        if BROWSER: await BROWSER.close()
        if PW: await PW.stop()

if __name__ == "__main__":
    asyncio.run(main())
