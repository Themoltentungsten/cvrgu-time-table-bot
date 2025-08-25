from __future__ import annotations
import asyncio
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
import zoneinfo

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ContextTypes, CallbackContext, MessageHandler, CommandHandler, filters,
)

TIMEZONE = zoneinfo.ZoneInfo("Asia/Kolkata")  # IST

# Academic day boundaries & lunch
COLLEGE_OPEN = time(9, 30, tzinfo=TIMEZONE)
COLLEGE_CLOSE = time(17, 30, tzinfo=TIMEZONE)
LUNCH_FROM = time(13, 30, tzinfo=TIMEZONE)
LUNCH_TO = time(14, 30, tzinfo=TIMEZONE)

# Canonical 1-hour slots
SLOTS: List[Tuple[time, time]] = [
    (time(9,30, tzinfo=TIMEZONE),  time(10,30, tzinfo=TIMEZONE)),
    (time(10,30, tzinfo=TIMEZONE), time(11,30, tzinfo=TIMEZONE)),
    (time(11,30, tzinfo=TIMEZONE), time(12,30, tzinfo=TIMEZONE)),
    (time(12,30, tzinfo=TIMEZONE), time(13,30, tzinfo=TIMEZONE)),
    # lunch 13:30–14:30
    (time(14,30, tzinfo=TIMEZONE), time(15,30, tzinfo=TIMEZONE)),
    (time(15,30, tzinfo=TIMEZONE), time(16,30, tzinfo=TIMEZONE)),
    (time(16,30, tzinfo=TIMEZONE), time(17,30, tzinfo=TIMEZONE)),
]

@dataclass
class ClassEntry:
    subject: str
    room: str
    teacher: Optional[str] = None

# --- FULL WEEK SCHEDULE FOR GROUP-7 ---
# Monday=0 ... Sunday=6
SCHEDULE: Dict[int, List[Optional[ClassEntry]]] = {
    0: [  # MON
        ClassEntry("DMDW", "BS-102"),
        ClassEntry("OS",   "BS-102"),
        ClassEntry("AIML", "BS-102"),
        ClassEntry("WT",   "BS-102"),
        ClassEntry("DMDW LAB", "MBA Gallary"),
        ClassEntry("AIML", "CS-201"),
        ClassEntry("AIML", "CS-201"),
    ],
    1: [  # TUE
        ClassEntry("OS", "BS-104"),
        ClassEntry("WT LAB", "BS-104"),
        ClassEntry("WT LAB", "BS-104"),
        None,  # NC
        ClassEntry("DMDW", "CS-201"),
        ClassEntry("CDT", "—"),
        None,
    ],
    2: [  # WED
        None,
        ClassEntry("SDE (Skill Dev Elective)", "—"),
        None,
        None,
        None,
        None,
        None,
    ],
    3: [  # THU
        ClassEntry("WT (Oracle Lab)", "Oracle Lab"),
        ClassEntry("AIML LAB", "Oracle Lab"),
        ClassEntry("AIML LAB", "Oracle Lab"),
        None,
        ClassEntry("DMDW", "BS-403"),
        ClassEntry("AIML", "BS-403"),
        ClassEntry("OS",   "BS-403"),
    ],
    4: [  # FRI
        ClassEntry("DMDW", "CS-201"),
        ClassEntry("OS",   "CS-201"),
        ClassEntry("WT",   "CS-201"),
        None,
        None,
        ClassEntry("OS LAB", "MECH DC"),
        None,
    ],
    5: [None, None, None, None, None, None, None],  # SAT (co-curricular only)
    6: [None, None, None, None, None, None, None],  # SUN closed
}

SUPPORTED_GROUPS = {"Group-7": SCHEDULE}

FACULTY = {
    "AIML": "Dr. Priya Rao (CSE)",
    "WT": "Subhrasmita Gouda (CSE)",
    "OS": "Dr. Ashish Ranjan (CSIT)",
    "DMDW": "Dr. Bichitrananda Behera (CSE)",
}

DEVELOPER_TEXT = (
    "Developer: @yashfreakin1 (Yash Kumar)\n"
    "Timetable: CVRGU, Group‑7, Sem‑5 (W.E.F. 25/08/2025).\n"
    "Dept. Coordinator (image): Dr. B.N. Behera; University Coordinator: Dr. G. Mohanta."
)

# ---------------- Utilities ----------------
def ist_now() -> datetime:
    return datetime.now(TIMEZONE)

def slot_index_for(now: Optional[datetime] = None) -> Optional[int]:
    now = now or ist_now()
    for i, (start, end) in enumerate(SLOTS):
        if start <= now.timetz() < end:
            return i
    return None

def current_class(group: str, now: Optional[datetime] = None) -> Optional[ClassEntry]:
    now = now or ist_now()
    idx = slot_index_for(now)
    if idx is None:
        return None
    schedule = SUPPORTED_GROUPS.get(group)
    if not schedule:
        return None
    return schedule[now.weekday()][idx]

def next_class(group: str, now: Optional[datetime] = None) -> Optional[tuple[datetime, ClassEntry]]:
    now = now or ist_now()
    schedule = SUPPORTED_GROUPS.get(group)
    if not schedule:
        return None
    day = now.weekday()
    start_slot = slot_index_for(now)
    start_offset = 0
    if start_slot is None:
        if now.timetz() < time(9, 30, tzinfo=TIMEZONE):
            start_slot = 0
        else:
            day = (day + 1) % 7
            start_slot = 0
            start_offset = 24
    for dshift in range(0, 7):
        d = (day + dshift) % 7
        for i in range(start_slot if dshift == 0 else 0, len(SLOTS)):
            entry = schedule[d][i]
            if entry:
                slot_start = datetime.combine((now.date() + timedelta(days=dshift)), SLOTS[i][0])
                slot_start = slot_start.replace(tzinfo=TIMEZONE)
                if dshift == 0 and start_offset == 0 and slot_start <= now:
                    continue
                return slot_start, entry
    return None

def format_entry(entry: ClassEntry) -> str:
    sub_key = entry.subject.split()[0]
    teacher = FACULTY.get(sub_key)
    t_str = f"\nFaculty: {teacher}" if teacher else ""
    return f"{entry.subject} @ {entry.room}{t_str}"

def day_schedule(group: str, day_idx: int) -> str:
    rows = []
    for (i, (start, end)) in enumerate(SLOTS):
        entry = SUPPORTED_GROUPS[group][day_idx][i]
        label = f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"
        if entry:
            rows.append(f"{label}: {format_entry(entry)}")
        elif start == time(13, 30, tzinfo=TIMEZONE):
            rows.append(f"{label}: Lunch Break")
        else:
            rows.append(f"{label}: —")
    return "\n".join(rows)

# ---------------- Persistence ----------------
USER_GROUP: Dict[int, str] = {}

# ---------------- UI & Handlers ----------------
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("Where is the class?"), KeyboardButton("Who is the developer?")]],
    resize_keyboard=True,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user and user.id not in USER_GROUP:
        USER_GROUP[user.id] = "Group-7"
    await update.message.reply_text(
        (
            "Welcome! You are registered under Group-7.\n"
            "Use the buttons below or commands: /today /next /subscribe /setgroup /help"
        ), reply_markup=MAIN_KEYBOARD
    )

async def setgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /setgroup Group-7")
        return
    group = " ".join(context.args)
    if group not in SUPPORTED_GROUPS:
        await update.message.reply_text(
            f"Unknown group '{group}'. Supported: {', '.join(SUPPORTED_GROUPS.keys())}"
        )
        return
    USER_GROUP[update.effective_user.id] = group
    await update.message.reply_text(f"Updated your group to {group}.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start – register & show menu\n"
        "/today – today's schedule\n"
        "/next – next class from now\n"
        "/subscribe – 10‑min reminders before each class today\n"
        "/setgroup <name> – change your group\n"
        "/help – help"
    )

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip().lower()
    if "where is the class" in text:
        await where_is_class(update, context)
    elif "who is the developer" in text:
        await update.message.reply_text(DEVELOPER_TEXT)
    else:
        await update.message.reply_text("Please use the provided buttons or /help.")

async def where_is_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    group = USER_GROUP.get(user_id, "Group-7")
    now = ist_now()
    # Sunday or outside hours
    if now.weekday() == 6 or not (time(9, 30, tzinfo=TIMEZONE) <= now.timetz() <= time(17, 30, tzinfo=TIMEZONE)):
        await update.message.reply_text("College is closed.")
        return
    # Lunch
    if time(13, 30, tzinfo=TIMEZONE) <= now.timetz() < time(14, 30, tzinfo=TIMEZONE):
        await update.message.reply_text("It's lunch break (13:30–14:30).")
        return
    entry = current_class(group, now)
    if entry:
        (start, end) = SLOTS[slot_index_for(now)]
        await update.message.reply_text(
            f"Current class ({start.strftime('%H:%M')}–{end.strftime('%H:%M')}):\n" + format_entry(entry)
        )
    else:
        await update.message.reply_text("No class right now.")

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group = USER_GROUP.get(update.effective_user.id, "Group-7")
    d = ist_now().weekday()
    if d == 6:
        await update.message.reply_text("Sunday: College is closed.")
        return
    await update.message.reply_text(
        f"Today's schedule for {group}:\n" + day_schedule(group, d)
    )

async def next_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group = USER_GROUP.get(update.effective_user.id, "Group-7")
    nxt = next_class(group, ist_now())
    if not nxt:
        await update.message.reply_text("No upcoming classes found.")
        return
    when, entry = nxt
    await update.message.reply_text(
        f"Next class at {when.strftime('%a %H:%M')} – {format_entry(entry)}"
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Schedules one‑off reminders 10 minutes before each remaining class today."""
    user_id = update.effective_user.id
    group = USER_GROUP.get(user_id, "Group-7")
    now = ist_now()
    day = now.weekday()
    jobs = 0
    for i, (start, _end) in enumerate(SLOTS):
        slot_time = datetime.combine(now.date(), start).replace(tzinfo=TIMEZONE)
        if slot_time <= now:
            continue
        entry = SUPPORTED_GROUPS[group][day][i]
        if not entry:
            continue
        remind_at = slot_time - timedelta(minutes=10)
        if remind_at <= now:
            continue
        context.job_queue.run_once(
            reminder_job,
            when=remind_at,
            data={"chat_id": update.effective_chat.id, "entry": entry, "slot": (start.strftime('%H:%M'))},
            name=f"reminder-{user_id}-{slot_time.isoformat()}",
            chat_id=update.effective_chat.id,
        )
        jobs += 1
    if jobs:
        await update.message.reply_text(f"Subscribed: I'll remind you 10 minutes before {jobs} class(es) today.")
    else:
        await update.message.reply_text("No remaining classes to remind you about today.")

async def reminder_job(context: CallbackContext):
    data = context.job.data
    entry: ClassEntry = data["entry"]
    slot_label = data["slot"]
    await context.bot.send_message(
        chat_id=data["chat_id"],
        text=f"⏰ Reminder ({slot_label}): {format_entry(entry)}",
    )
