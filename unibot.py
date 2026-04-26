#API_TOKEN = '8629117016:AAFjkK58pesUMjP4PlUIQYI3mj24OMa6ALA'  # ⬅️ ВСТАВЬТЕ ВАШ ТОКЕН
import asyncio
import logging
import json
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# ========== КОНФИГУРАЦИЯ ==========
API_TOKEN = '8629117016:AAFjkK58pesUMjP4PlUIQYI3mj24OMa6ALA'  # ⬅️ ВСТАВЬТЕ ВАШ ТОКЕН
logging.basicConfig(level=logging.INFO)

# ========== ХРАНЕНИЕ ДАННЫХ ==========
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


# ========== КНОПКИ ==========
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="😴 ЗАПИСАТЬ СОН", callback_data="log_sleep")],
        [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="stats")],
        [InlineKeyboardButton(text="⏰ УМНЫЙ БУДИЛЬНИК", callback_data="smart_alarm")],
        [InlineKeyboardButton(text="🔍 АНАЛИЗ", callback_data="analysis")],
        [InlineKeyboardButton(text="🗑 ОЧИСТИТЬ ВСЕ ЗАПИСИ", callback_data="clear_all")],
    ])


def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="back")]
    ])


# ========== ФУНКЦИИ ДЛЯ СНА ==========

# НОВАЯ ФУНКЦИЯ - проверяет соответствие часов и времени
def check_sleep_consistency(hours: float, bed_time: str, wake_time: str) -> tuple:
    """Проверяет, соответствуют ли введенные часы разнице между bed_time и wake_time"""
    try:
        bed_h, bed_m = map(int, bed_time.split(':'))
        wake_h, wake_m = map(int, wake_time.split(':'))

        bed_min = bed_h * 60 + bed_m
        wake_min = wake_h * 60 + wake_m

        # Если проснулся на следующий день
        if wake_min < bed_min:
            wake_min += 1440

        actual_hours = (wake_min - bed_min) / 60

        # Разница между заявленными и реальными часами (округленно)
        diff = abs(actual_hours - hours)

        if diff > 1.5:
            return False, actual_hours
        return True, actual_hours
    except:
        return True, hours


def get_sleep_advice(hours: float, bed_time: str = "23:00") -> str:
    """Совет с учетом пересыпа и времени отхода"""
    # Сначала оценка времени отхода
    try:
        hour = int(bed_time.split(':')[0])
        if hour >= 0 and hour <=12:
            # 00:00, 01:00, 02:00 и позже
            late_advice = "⚠️ Ты лег очень поздно! Это вредит качеству сна."
        elif hour == 23:
            late_advice = "👍 Хорошее время для сна"
        elif hour <= 22 and hour >= 18:
            late_advice = "🥇 Ранний отход - отлично для здоровья!"
        else:
            late_advice = ""
    except:
        late_advice = ""

    # Оценка продолжительности
    if hours >= 10:
        duration_advice = "⚠️ Ты слишком много спишь! Пересып вреден, оптимально 7-8 часов"
    elif hours >= 9:
        duration_advice = "😴 Многовато. Постарайся спать 7-8 часов"
    elif hours >= 8:
        duration_advice = "🌟 Отлично! Ты идеально выспался!"
    elif hours >= 7:
        duration_advice = "👍 Хорошо! Норма для взрослого человека"
    elif hours >= 6:
        duration_advice = "😐 Нормально, но можно спать на час больше"
    elif hours >= 5:
        duration_advice = "⚠️ Мало! Старайся спать 7-8 часов"
    else:
        duration_advice = "🔴 Критически мало! Тебе нужно больше спать!"

    if late_advice:
        return f"{duration_advice}\n{late_advice}"
    return duration_advice


def calculate_sleep_score(hours: float, bed_time: str = "23:00") -> int:
    """Оценка сна 0-100 с учетом времени отхода ко сну"""
    # Базовая оценка по часам
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

    # ШТРАФ за позднее засыпание (ИСПРАВЛЕН!)
    try:
        hour = int(bed_time.split(':')[0])
        if 20 <= hour <= 22:  # 20:00, 21:00, 22:00 - хорошее время
            score += 5
        elif hour == 23:  # 23:00 - норма
            pass
        elif hour == 0:  # 00:00 - уже поздно
            score -= 20
        elif hour == 1:  # 01:00 - очень поздно
            score -= 30
        elif hour >= 2:  # 02:00 и позже - критично поздно
            score -= 40
    except:
        pass

    return max(0, min(100, score))


def get_sleep_emoji(hours: float, bed_time: str = "23:00") -> str:
    """Эмодзи для визуализации"""
    score = calculate_sleep_score(hours, bed_time)
    if score >= 80:
        return "🟢"
    elif score >= 50:
        return "🟡"
    else:
        return "🔴"


def get_bed_quality_note(bed_time: str) -> str:
    """Оценка времени отхода ко сну (ИСПРАВЛЕНА!)"""
    try:
        hour = int(bed_time.split(':')[0])
        if 20 <= hour <= 22:  # 20:00, 21:00, 22:00
            return "🥇 Ранний отход - отлично для здоровья!"
        elif hour == 23:  # 23:00
            return "👍 Хорошее время для сна"
        elif hour == 0:  # 00:00
            return "😐 Уже поздно, старайся ложиться до 23:00"
        elif hour == 1:  # 01:00
            return "⚠️ Слишком поздно, это сильно влияет на качество сна"
        elif hour >= 2:  # 02:00 и позже
            return "🔴 Очень поздно! Постарайся ложиться до 23:00"
        else:
            return ""
    except:
        return ""

def analyze_sleep_patterns(records: list) -> dict:
    """Анализ паттернов сна (ИСПРАВЛЕНО - правильный подсчет late_days)"""
    if len(records) < 3:
        return {"has_data": False, "message": "Нужно минимум 3 записи для анализа"}

    last_7 = records[-7:] if len(records) > 7 else records
    avg_hours = sum(r['hours'] for r in last_7) / len(last_7)

    good_days = len([r for r in last_7 if 7 <= r['hours'] <= 8])
    bad_days = len([r for r in last_7 if r['hours'] < 6 or r['hours'] > 10])

    # Анализ времени засыпания (ИСПРАВЛЕНО! теперь правильно считает)
    late_days = 0
    for r in last_7:
        try:
            hour = int(r.get('bed_time', '23:00').split(':')[0])
            # Если лег в 01:00, 02:00, 03:00, 04:00, 05:00 - считаем поздним
            if hour >= 1 and hour <= 5:
                late_days += 1
            # Если лег в 00:00 - тоже считаем поздним (полночь)
            elif hour == 0:
                late_days += 1
        except:
            pass

    # Прогресс
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


# ========== БОТ ==========
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Кто ждет ввода и на каком шаге
waiting_for = {}  # {user_id: {"step": "hours"} или {"step": "alarm"}}


# ========== СТАРТ ==========
@dp.message(Command("start"))
async def start(message: Message):
    user_id = str(message.from_user.id)

    if user_id not in users_data:
        users_data[user_id] = {"records": []}
        save_data(users_data)

    count = len(users_data[user_id]["records"])

    await message.answer(
        f"🌙 *SLEEP TRACKER*\n\n"
        f"📊 У тебя *{count}* записей сна\n\n"
        f"😴 Что я умею:\n"
        f"• Записывать сон (часы + время)\n"
        f"• Считать оценку сна\n"
        f"• Анализировать паттерны\n"
        f"• Подбирать время пробуждения\n\n"
        f"👉 *Нажми 'ЗАПИСАТЬ СОН' чтобы начать*",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )


@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌙 *ГЛАВНОЕ МЕНЮ*",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()


# ========== 1. ЗАПИСЬ СНА (3 ШАГА) ==========
@dp.callback_query(F.data == "log_sleep")
async def log_sleep(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    waiting_for[user_id] = {"step": "hours"}
    await callback.message.answer(
        "😴 *ЗАПИСЬ СНА - ШАГ 1/3*\n\n"
        "Сколько часов ты спал?\n\n"
        "📝 *Примеры:* 7, 7.5, 8, 6\n\n"
        "Просто напиши число\n\n"
        "Или напиши *отмена*",
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message()
async def handle_all_messages(message: Message):
    user_id = str(message.from_user.id)
    text = message.text.strip()

    # ОТМЕНА
    if text.lower() == "отмена":
        if user_id in waiting_for:
            del waiting_for[user_id]
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return

    # Если не ждем ничего
    if user_id not in waiting_for:
        await message.answer("Используй кнопки меню", reply_markup=main_menu())
        return

    step_data = waiting_for[user_id]
    step = step_data.get("step")

    # ШАГ 1: запись часов
    if step == "hours":
        try:
            hours = float(text.replace(',', '.'))
            if 0 < hours <= 24:
                waiting_for[user_id]["hours"] = hours
                waiting_for[user_id]["step"] = "bed_time"
                await message.answer(
                    f"✅ Спал: {hours} часов\n\n"
                    "😴 *ЗАПИСЬ СНА - ШАГ 2/3*\n\n"
                    "Во сколько ты лег спать?\n\n"
                    "📝 *Формат:* ЧЧ:ММ\n"
                    "Примеры: 23:00, 23:30, 00:30\n\n"
                    "Или напиши *отмена*",
                    parse_mode="Markdown"
                )
            else:
                await message.answer("❌ Часы должны быть от 0 до 24. Попробуй еще раз:")
        except ValueError:
            await message.answer("❌ Напиши число! Например: 7.5 или 8")
        return

    # ШАГ 2: время отхода ко сну
    if step == "bed_time":
        if ':' not in text:
            await message.answer("❌ Используй формат ЧЧ:ММ. Пример: 23:00 или 23:30")
            return

        try:
            bed_time = text.strip()
            datetime.strptime(bed_time, "%H:%M")
            waiting_for[user_id]["bed_time"] = bed_time
            waiting_for[user_id]["step"] = "wake_time"
            await message.answer(
                f"✅ Лег спать в {bed_time}\n\n"
                "😴 *ЗАПИСЬ СНА - ШАГ 3/3*\n\n"
                "Во сколько ты проснулся?\n\n"
                "📝 *Формат:* ЧЧ:ММ\n"
                "Примеры: 07:00, 08:30, 09:00\n\n"
                "Или напиши *отмена*",
                parse_mode="Markdown"
            )
        except:
            await message.answer("❌ Неправильный формат! Пример: 23:30 или 00:15")
        return

    # ШАГ 3: время пробуждения
    if step == "wake_time":
        if ':' not in text:
            await message.answer("❌ Используй формат ЧЧ:ММ. Пример: 07:00")
            return

        try:
            wake_time = text.strip()
            datetime.strptime(wake_time, "%H:%M")

            # Сохраняем все данные
            today = datetime.now().strftime("%Y-%m-%d")
            hours = waiting_for[user_id]["hours"]
            bed_time = waiting_for[user_id]["bed_time"]

            # Проверяем соответствие часов и времени (НЕ УДАЛЯТЬ, просто предупреждаем)
            is_consistent, actual_hours = check_sleep_consistency(hours, bed_time, wake_time)

            if not is_consistent:
                await message.answer(
                    f"⚠️ *ВНИМАНИЕ!*\n\n"
                    f"По времени {bed_time} → {wake_time} получается {actual_hours:.1f} часов сна,\n"
                    f"а ты указал(а) {hours} часов.\n\n"
                    f"Я сохраняю твои данные как есть, но учти это несоответствие!",
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

            # Очищаем ожидание
            del waiting_for[user_id]

            # Считаем оценку (с учетом времени)
            score = calculate_sleep_score(hours, bed_time)
            advice = get_sleep_advice(hours, bed_time)
            emoji = get_sleep_emoji(hours, bed_time)
            bed_note = get_bed_quality_note(bed_time)

            count = len(users_data[user_id]["records"])

            await message.answer(
                f"{emoji} *Сон сохранен!*\n\n"
                f"📅 {today}\n"
                f"😴 Спал: *{hours} часов*\n"
                f"🛏 Лег: {bed_time} | Проснулся: {wake_time}\n"
                f"📊 Оценка: *{score}/100*\n\n"
                f"💡 {advice}\n\n"
                f"📊 Всего записей: *{count}*\n\n"
                f"👉 Нажми *АНАЛИЗ* после 3 записей",
                parse_mode="Markdown",
                reply_markup=main_menu()
            )
        except:
            await message.answer("❌ Неправильный формат! Пример: 07:00 или 08:30")
        return

    # ===== УМНЫЙ БУДИЛЬНИК =====
    if step == "alarm":
        if ':' not in text:
            await message.answer("❌ Напиши время в формате ЧЧ:ММ (например: 23:30)")
            return

        try:
            time_parts = text.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])

            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                await message.answer("❌ Неправильное время! Часы от 0 до 23, минуты от 0 до 59")
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
                f"⏰ *УМНЫЙ БУДИЛЬНИК*\n\n"
                f"Если ляжешь в *{text}*:\n\n"
                f"🌙 *Вариант 1:* Проснуться в *{wake5_hour:02d}:{wake5_min:02d}*\n"
                f"   → 5 циклов = 7.5 часов сна (оптимально)\n\n"
                f"🌙 *Вариант 2:* Проснуться в *{wake6_hour:02d}:{wake6_min:02d}*\n"
                f"   → 6 циклов = 9 часов сна\n\n"
                f"💡 *Совет:* Просыпаться лучше в конце цикла - так легче вставать!",
                parse_mode="Markdown",
                reply_markup=main_menu()
            )
            del waiting_for[user_id]
        except Exception as e:
            await message.answer("❌ Ошибка! Пример правильного формата: 23:30 или 00:15")
        return


# ========== 2. СТАТИСТИКА ==========
@dp.callback_query(F.data == "stats")
async def show_stats(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    records = users_data.get(user_id, {}).get("records", [])

    if not records:
        await callback.message.edit_text(
            "📊 *СТАТИСТИКА*\n\n"
            "У тебя пока нет записей!\n\n"
            "👉 Нажми 'ЗАПИСАТЬ СОН'",
            parse_mode="Markdown",
            reply_markup=back_menu()
        )
        await callback.answer()
        return

    text = f"📊 *ТВОИ ЗАПИСИ*\n\n"
    text += f"📅 Всего: *{len(records)}* записей\n\n"

    text += "📝 *Последние записи:*\n"
    for r in records[-5:][::-1]:
        score = calculate_sleep_score(r['hours'], r.get('bed_time', '23:00'))
        emoji = get_sleep_emoji(r['hours'], r.get('bed_time', '23:00'))
        bed = r.get('bed_time', '?')
        wake = r.get('wake_time', '?')
        text += f"{emoji} {r['date']}: {r['hours']}ч (лег {bed}→{wake}) | оценка *{score}/100*\n"

    if len(records) >= 3:
        last_7 = records[-7:] if len(records) > 7 else records
        avg = sum(r['hours'] for r in last_7) / len(last_7)
        text += f"\n📊 Средний сон: *{avg:.1f} часов*"

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_menu())
    await callback.answer()


# ========== 3. УМНЫЙ БУДИЛЬНИК (СТАРТ) ==========
@dp.callback_query(F.data == "smart_alarm")
async def smart_alarm_start(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    waiting_for[user_id] = {"step": "alarm"}
    await callback.message.answer(
        "⏰ *УМНЫЙ БУДИЛЬНИК*\n\n"
        "Во сколько ты планируешь лечь спать?\n\n"
        "📝 Напиши время в формате ЧЧ:ММ\n"
        "Пример: 23:30 или 00:00\n\n"
        "Или напиши 'отмена'",
        parse_mode="Markdown"
    )
    await callback.answer()


# ========== 4. АНАЛИЗ ==========
@dp.callback_query(F.data == "analysis")
async def show_analysis(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    records = users_data.get(user_id, {}).get("records", [])

    if len(records) == 0:
        await callback.message.edit_text(
            "🔍 *АНАЛИЗ СНА*\n\n"
            "❌ У тебя нет записей!\n\n"
            "👉 Нажми 'ЗАПИСАТЬ СОН'",
            parse_mode="Markdown",
            reply_markup=back_menu()
        )
        await callback.answer()
        return

    if len(records) < 3:
        await callback.message.edit_text(
            f"🔍 *АНАЛИЗ СНА*\n\n"
            f"📊 У тебя *{len(records)}* записи\n\n"
            f"⚠️ Для анализа нужно *3 записи*\n\n"
            f"👉 Добавь еще {3 - len(records)} записи",
            parse_mode="Markdown",
            reply_markup=back_menu()
        )
        await callback.answer()
        return

    analysis = analyze_sleep_patterns(records)

    text = "🔍 *АНАЛИЗ ТВОЕГО СНА*\n\n"
    text += f"📊 За последние {analysis['total_days']} дней:\n"
    text += f"   • Средний сон: *{analysis['avg_hours']} часов*\n"
    text += f"   • Хороших дней (7-8ч): *{analysis['good_days']}/{analysis['total_days']}*\n"

    if analysis['bad_days'] > 0:
        text += f"   • Плохих дней: *{analysis['bad_days']}/{analysis['total_days']}*\n"

    if analysis['late_days'] > 0:
        text += f"   • Поздних засыпаний (после 01:00): *{analysis['late_days']}/{analysis['total_days']}*\n"

    text += "\n"

    if analysis['avg_hours'] >= 7.5:
        text += "✅ *Оценка: ОТЛИЧНО*\n"
    elif analysis['avg_hours'] >= 6.5:
        text += "🟡 *Оценка: ХОРОШО*\n"
    else:
        text += "🔴 *Оценка: ТРЕБУЕТ ВНИМАНИЯ*\n"

    if analysis['progress'] > 0.3:
        text += f"\n📈 *Прогресс:* +{analysis['progress']}ч 🎉\n"
    elif analysis['progress'] < -0.3:
        text += f"\n📉 *Прогресс:* {analysis['progress']}ч\n"

    text += "\n💡 *СОВЕТЫ:*\n"
    if analysis['avg_hours'] < 7:
        text += "   • 😴 Спи 7-8 часов\n"
    if analysis['late_days'] > analysis['total_days'] // 2:
        text += "   • 🌙 Ложись до 23:00\n"

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_menu())
    await callback.answer()


# ========== 5. ОЧИСТКА ЗАПИСЕЙ ==========
@dp.callback_query(F.data == "clear_all")
async def clear_records(callback: CallbackQuery):
    user_id = str(callback.from_user.id)

    if user_id in users_data:
        users_data[user_id]["records"] = []
        save_data(users_data)
        await callback.message.edit_text(
            "🗑 *ВСЕ ЗАПИСИ УДАЛЕНЫ!*\n\n"
            "Теперь можно начать с чистого листа.\n"
            "Нажми 'ЗАПИСАТЬ СОН' чтобы добавить первую запись",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
    else:
        await callback.message.edit_text("❌ У тебя и так нет записей", reply_markup=main_menu())
    await callback.answer()


# ========== ЗАПУСК ==========
async def main():
    print("=" * 50)
    print("🌙 SLEEP TRACKER ЗАПУЩЕН!")
    print("=" * 50)
    print(f"👥 Пользователей: {len(users_data)}")
    print("\n📝 ФУНКЦИИ:")
    print("   ✅ Запись сна (часы + время отхода + время пробуждения)")
    print("   ✅ Умный будильник")
    print("   ✅ Статистика")
    print("   ✅ Анализ после 3 записей")
    print("   ✅ Учет времени отхода в оценке")
    print("   ✅ Очистка записей (кнопка)")
    print("=" * 50)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())