import asyncio
import logging
import json
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton


API_TOKEN = '8629117016:AAFjkK58pesUMjP4PlUIQYI3mj24OMa6ALA'
logging.basicConfig(level=logging.INFO)


DATA_FILE = "sleep_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

users_data = load_data()


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="😴 LOG SLEEP", callback_data="log_sleep")],
        [InlineKeyboardButton(text="📊 STATISTICS", callback_data="stats")],
        [InlineKeyboardButton(text="⏰ SMART ALARM", callback_data="smart_alarm")],
        [InlineKeyboardButton(text="🔍 ANALYSIS", callback_data="analysis")],
        [InlineKeyboardButton(text="🗑 CLEAR ALL RECORDS", callback_data="clear_all")],
    ])

def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 BACK", callback_data="back")]
    ])



def check_sleep_consistency(hours: float, bed_time: str, wake_time: str) -> tuple:
    """Checks if entered hours match the difference between bed_time and wake_time"""
    try:
        bed_h, bed_m = map(int, bed_time.split(':'))
        wake_h, wake_m = map(int, wake_time.split(':'))

        bed_min = bed_h * 60 + bed_m
        wake_min = wake_h * 60 + wake_m

        if wake_min < bed_min:
            wake_min += 1440

        actual_hours = (wake_min - bed_min) / 60
        diff = abs(actual_hours - hours)

        if diff > 1.5:
            return False, actual_hours
        return True, actual_hours
    except:
        return True, hours

def get_sleep_advice(hours: float, bed_time: str = "23:00") -> str:
    """Advice considering oversleep and bedtime"""
    try:
        hour = int(bed_time.split(':')[0])
        if hour >= 0 and hour <= 12:
            late_advice = "⚠️ You went to bed very late! This harms sleep quality."
        elif hour == 23:
            late_advice = "👍 Good time for sleep"
        elif hour <= 22 and hour >= 18:
            late_advice = "🥇 Early bedtime - great for health!"
        else:
            late_advice = ""
    except:
        late_advice = ""

    if hours >= 10:
        duration_advice = "⚠️ You sleep too much! Oversleep is harmful, 7-8 hours is optimal"
    elif hours >= 9:
        duration_advice = "😴 A bit too much. Try to sleep 7-8 hours"
    elif hours >= 8:
        duration_advice = "🌟 Great! You slept perfectly!"
    elif hours >= 7:
        duration_advice = "👍 Good! Normal for an adult"
    elif hours >= 6:
        duration_advice = "😐 Normal, but you could sleep an hour more"
    elif hours >= 5:
        duration_advice = "⚠️ Too little! Try to sleep 7-8 hours"
    else:
        duration_advice = "🔴 Critically little! You need more sleep!"

    if late_advice:
        return f"{duration_advice}\n{late_advice}"
    return duration_advice

def calculate_sleep_score(hours: float, bed_time: str = "23:00") -> int:
    """Sleep score 0-100 considering bedtime"""
    if 7 <= hours <= 8:
        score = 100
    elif 6.5 <= hours < 7:
        score = 85
    elif 8 < hours <= 9:
        score = 75
    elif 6 <= hours < 6.5:
        score = 65
    elif 9 < hours <= 10:
        score = 50
    elif 5 <= hours < 6:
        score = 40
    elif hours > 10:
        score = 25
    elif 4 <= hours < 5:
        score = 20
    else:
        score = 10

    try:
        hour = int(bed_time.split(':')[0])
        if 20 <= hour <= 22:
            score += 5
        elif hour == 23:
            pass
        elif hour == 0:
            score -= 20
        elif hour == 1:
            score -= 30
        elif hour >= 2:
            score -= 40
    except:
        pass

    return max(0, min(100, score))

def get_sleep_emoji(hours: float, bed_time: str = "23:00") -> str:
    """Emoji for score visualization"""
    score = calculate_sleep_score(hours, bed_time)
    if score >= 80:
        return "🟢"
    elif score >= 50:
        return "🟡"
    else:
        return "🔴"

def get_bed_quality_note(bed_time: str) -> str:
    """Bedtime quality note"""
    try:
        hour = int(bed_time.split(':')[0])
        if 20 <= hour <= 22:
            return "🥇 Early bedtime - great for health!"
        elif hour == 23:
            return "👍 Good time for sleep"
        elif hour == 0:
            return "😐 Already late, try to go to bed before 23:00"
        elif hour == 1:
            return "⚠️ Too late, this strongly affects sleep quality"
        elif hour >= 2:
            return "🔴 Very late! Try to go to bed before 23:00"
        else:
            return ""
    except:
        return ""

def analyze_sleep_patterns(records: list) -> dict:
    """Sleep patterns analysis"""
    if len(records) < 3:
        return {"has_data": False, "message": "Need at least 3 records for analysis"}

    last_7 = records[-7:] if len(records) > 7 else records
    avg_hours = sum(r['hours'] for r in last_7) / len(last_7)

    good_days = len([r for r in last_7 if 7 <= r['hours'] <= 8])
    bad_days = len([r for r in last_7 if r['hours'] < 6 or r['hours'] > 10])

    late_days = 0
    for r in last_7:
        try:
            hour = int(r.get('bed_time', '23:00').split(':')[0])
            if hour >= 1 and hour <= 5:
                late_days += 1
            elif hour == 0:
                late_days += 1
        except:
            pass

    if len(records) >= 5:
        first_3 = records[:3]
        first_avg = sum(r['hours'] for r in first_3) / 3
        progress = avg_hours - first_avg
    else:
        progress = 0

    return {
        "has_data": True,
        "avg_hours": round(avg_hours, 1),
        "good_days": good_days,
        "bad_days": bad_days,
        "late_days": late_days,
        "total_days": len(last_7),
        "progress": round(progress, 1),
        "total_records": len(records)
    }


bot = Bot(token=API_TOKEN)
dp = Dispatcher()

waiting_for = {}


@dp.message(Command("start"))
async def start(message: Message):
    user_id = str(message.from_user.id)

    if user_id not in users_data:
        users_data[user_id] = {"records": []}
        save_data(users_data)

    count = len(users_data[user_id]["records"])

    await message.answer(
        f"🌙 *SLEEP TRACKER*\n\n"
        f"📊 You have *{count}* sleep records\n\n"
        f"😴 What I can do:\n"
        f"• Record sleep (hours + time)\n"
        f"• Calculate sleep score\n"
        f"• Analyze patterns\n"
        f"• Find optimal wake-up time\n\n"
        f"👉 *Press 'LOG SLEEP' to start*",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌙 *MAIN MENU*",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()


@dp.callback_query(F.data == "log_sleep")
async def log_sleep(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    waiting_for[user_id] = {"step": "hours"}
    await callback.message.answer(
        "😴 *LOG SLEEP - STEP 1/3*\n\n"
        "How many hours did you sleep?\n\n"
        "📝 *Examples:* 7, 7.5, 8, 6\n\n"
        "Just write the number\n\n"
        "Or write 'cancel'",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message()
async def handle_all_messages(message: Message):
    user_id = str(message.from_user.id)
    text = message.text.strip()

    if text.lower() == "cancel":
        if user_id in waiting_for:
            del waiting_for[user_id]
        await message.answer("❌ Cancelled", reply_markup=main_menu())
        return

    if user_id not in waiting_for:
        await message.answer("Use the menu buttons", reply_markup=main_menu())
        return

    step_data = waiting_for[user_id]
    step = step_data.get("step")

    if step == "hours":
        try:
            hours = float(text.replace(',', '.'))
            if 0 < hours <= 24:
                waiting_for[user_id]["hours"] = hours
                waiting_for[user_id]["step"] = "bed_time"
                await message.answer(
                    f"✅ Slept: {hours} hours\n\n"
                    "😴 *LOG SLEEP - STEP 2/3*\n\n"
                    "What time did you go to bed?\n\n"
                    "📝 *Format:* HH:MM\n"
                    "Examples: 23:00, 23:30, 00:30\n\n"
                    "Or write 'cancel'",
                    parse_mode="Markdown"
                )
            else:
                await message.answer("❌ Hours must be between 0 and 24. Try again:")
        except ValueError:
            await message.answer("❌ Write a number! Example: 7.5 or 8")
        return

   
    if step == "bed_time":
        if ':' not in text:
            await message.answer("❌ Use HH:MM format. Example: 23:00 or 23:30")
            return

        try:
            bed_time = text.strip()
            datetime.strptime(bed_time, "%H:%M")
            waiting_for[user_id]["bed_time"] = bed_time
            waiting_for[user_id]["step"] = "wake_time"
            await message.answer(
                f"✅ Went to bed at {bed_time}\n\n"
                "😴 *LOG SLEEP - STEP 3/3*\n\n"
                "What time did you wake up?\n\n"
                "📝 *Format:* HH:MM\n"
                "Examples: 07:00, 08:30, 09:00\n\n"
                "Or write 'cancel'",
                parse_mode="Markdown"
            )
        except:
            await message.answer("❌ Wrong format! Example: 23:30 or 00:15")
        return

 
    if step == "wake_time":
        if ':' not in text:
            await message.answer("❌ Use HH:MM format. Example: 07:00")
            return

        try:
            wake_time = text.strip()
            datetime.strptime(wake_time, "%H:%M")

            today = datetime.now().strftime("%Y-%m-%d")
            hours = waiting_for[user_id]["hours"]
            bed_time = waiting_for[user_id]["bed_time"]

            is_consistent, actual_hours = check_sleep_consistency(hours, bed_time, wake_time)

            if not is_consistent:
                await message.answer(
                    f"⚠️ *WARNING!*\n\n"
                    f"From {bed_time} → {wake_time} it's {actual_hours:.1f} hours of sleep,\n"
                    f"but you entered {hours} hours.\n\n"
                    f"I'm saving your data as is, but keep this inconsistency in mind!",
                    parse_mode="Markdown"
                )

            record = {
                "date": today,
                "hours": hours,
                "bed_time": bed_time,
                "wake_time": wake_time,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            users_data[user_id]["records"].append(record)
            save_data(users_data)

            del waiting_for[user_id]

            score = calculate_sleep_score(hours, bed_time)
            advice = get_sleep_advice(hours, bed_time)
            emoji = get_sleep_emoji(hours, bed_time)
            bed_note = get_bed_quality_note(bed_time)

            count = len(users_data[user_id]["records"])

            await message.answer(
                f"{emoji} *Sleep saved!*\n\n"
                f"📅 {today}\n"
                f"😴 Slept: *{hours} hours*\n"
                f"🛏 Bed: {bed_time} | Woke: {wake_time}\n"
                f"📊 Score: *{score}/100*\n\n"
                f"💡 {advice}\n\n"
                f"📊 Total records: *{count}*\n\n"
                f"👉 Press *ANALYSIS* after 3 records",
                parse_mode="Markdown",
                reply_markup=main_menu()
            )
        except:
            await message.answer("❌ Wrong format! Example: 07:00 or 08:30")
        return

   
    if step == "alarm":
        if ':' not in text:
            await message.answer("❌ Write time in HH:MM format (example: 23:30)")
            return

        try:
            time_parts = text.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])

            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                await message.answer("❌ Invalid time! Hours 0-23, minutes 0-59")
                return

            bed_minutes = hour * 60 + minute

            wake5 = bed_minutes + 450
            if wake5 >= 1440:
                wake5 -= 1440
            wake5_hour = wake5 // 60
            wake5_min = wake5 % 60

            wake6 = bed_minutes + 540
            if wake6 >= 1440:
                wake6 -= 1440
            wake6_hour = wake6 // 60
            wake6_min = wake6 % 60

            await message.answer(
                f"⏰ *SMART ALARM*\n\n"
                f"If you sleep at *{text}*:\n\n"
                f"🌙 *Option 1:* Wake up at *{wake5_hour:02d}:{wake5_min:02d}*\n"
                f"   → 5 cycles = 7.5 hours of sleep (optimal)\n\n"
                f"🌙 *Option 2:* Wake up at *{wake6_hour:02d}:{wake6_min:02d}*\n"
                f"   → 6 cycles = 9 hours of sleep\n\n"
                f"💡 *Tip:* Waking up at the end of a cycle makes it easier to get up!",
                parse_mode="Markdown",
                reply_markup=main_menu()
            )
            del waiting_for[user_id]
        except Exception as e:
            await message.answer("❌ Error! Example correct format: 23:30 or 00:15")
        return

@dp.callback_query(F.data == "stats")
async def show_stats(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    records = users_data.get(user_id, {}).get("records", [])

    if not records:
        await callback.message.edit_text(
            "📊 *STATISTICS*\n\n"
            "You have no records yet!\n\n"
            "👉 Press 'LOG SLEEP'",
            parse_mode="Markdown",
            reply_markup=back_menu()
        )
        await callback.answer()
        return

    text = f"📊 *YOUR RECORDS*\n\n"
    text += f"📅 Total: *{len(records)}* records\n\n"

    text += "📝 *Last records:*\n"
    for r in records[-5:][::-1]:
        score = calculate_sleep_score(r['hours'], r.get('bed_time', '23:00'))
        emoji = get_sleep_emoji(r['hours'], r.get('bed_time', '23:00'))
        bed = r.get('bed_time', '?')
        wake = r.get('wake_time', '?')
        text += f"{emoji} {r['date']}: {r['hours']}h (bed {bed}→{wake}) | score *{score}/100*\n"

    if len(records) >= 3:
        last_7 = records[-7:] if len(records) > 7 else records
        avg = sum(r['hours'] for r in last_7) / len(last_7)
        text += f"\n📊 Average sleep: *{avg:.1f} hours*"

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_menu())
    await callback.answer()


@dp.callback_query(F.data == "smart_alarm")
async def smart_alarm_start(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    waiting_for[user_id] = {"step": "alarm"}
    await callback.message.answer(
        "⏰ *SMART ALARM*\n\n"
        "What time do you plan to go to bed?\n\n"
        "📝 Write time in HH:MM format\n"
        "Example: 23:30 or 00:00\n\n"
        "Or write 'cancel'",
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "analysis")
async def show_analysis(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    records = users_data.get(user_id, {}).get("records", [])

    if len(records) == 0:
        await callback.message.edit_text(
            "🔍 *SLEEP ANALYSIS*\n\n"
            "❌ You have no records!\n\n"
            "👉 Press 'LOG SLEEP'",
            parse_mode="Markdown",
            reply_markup=back_menu()
        )
        await callback.answer()
        return

    if len(records) < 3:
        await callback.message.edit_text(
            f"🔍 *SLEEP ANALYSIS*\n\n"
            f"📊 You have *{len(records)}* records\n\n"
            f"⚠️ Need *3 records* for analysis\n\n"
            f"👉 Add {3 - len(records)} more records",
            parse_mode="Markdown",
            reply_markup=back_menu()
        )
        await callback.answer()
        return

    analysis = analyze_sleep_patterns(records)

    text = "🔍 *YOUR SLEEP ANALYSIS*\n\n"
    text += f"📊 Last {analysis['total_days']} days:\n"
    text += f"   • Average sleep: *{analysis['avg_hours']} hours*\n"
    text += f"   • Good days (7-8h): *{analysis['good_days']}/{analysis['total_days']}*\n"

    if analysis['bad_days'] > 0:
        text += f"   • Bad days: *{analysis['bad_days']}/{analysis['total_days']}*\n"

    if analysis['late_days'] > 0:
        text += f"   • Late bedtimes (after 01:00): *{analysis['late_days']}/{analysis['total_days']}*\n"

    text += "\n"

    if analysis['avg_hours'] >= 7.5:
        text += "✅ *Grade: EXCELLENT*\n"
    elif analysis['avg_hours'] >= 6.5:
        text += "🟡 *Grade: GOOD*\n"
    else:
        text += "🔴 *Grade: NEEDS ATTENTION*\n"

    if analysis['progress'] > 0.3:
        text += f"\n📈 *Progress:* +{analysis['progress']}h 🎉\n"
    elif analysis['progress'] < -0.3:
        text += f"\n📉 *Progress:* {analysis['progress']}h\n"

    text += "\n💡 *TIPS:*\n"
    if analysis['avg_hours'] < 7:
        text += "   • 😴 Sleep 7-8 hours\n"
    if analysis['late_days'] > analysis['total_days'] // 2:
        text += "   • 🌙 Go to bed before 23:00\n"

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_menu())
    await callback.answer()


@dp.callback_query(F.data == "clear_all")
async def clear_records(callback: CallbackQuery):
    user_id = str(callback.from_user.id)

    if user_id in users_data:
        users_data[user_id]["records"] = []
        save_data(users_data)
        await callback.message.edit_text(
            "🗑 *ALL RECORDS DELETED!*\n\n"
            "Now you can start with a clean slate.\n"
            "Press 'LOG SLEEP' to add your first record",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
    else:
        await callback.message.edit_text("❌ You have no records to delete", reply_markup=main_menu())
    await callback.answer()


async def main():
    print("=" * 50)
    print("🌙 SLEEP TRACKER STARTED!")
    print("=" * 50)
    print(f"👥 Users: {len(users_data)}")
    print("\n📝 FUNCTIONS:")
    print("   ✅ Sleep logging (hours + bed time + wake time)")
    print("   ✅ Smart alarm")
    print("   ✅ Statistics")
    print("   ✅ Analysis after 3 records")
    print("   ✅ Bedtime consideration in score")
    print("   ✅ Clear records (button)")
    print("=" * 50)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
