import telebot
from telebot import types
import os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)

state = {}
complaints = {}
complaint_id = 0
admin_reply_to = {}


# ---------------- MENU ----------------
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Вопрос", "Баг")
    kb.add("Открытые вакансии")
    kb.add("Жалоба на игрока")
    return kb


@bot.message_handler(commands=["start"])
def start(m):
    bot.send_message(m.chat.id, "Меню:", reply_markup=menu())


# ---------------- QUESTION ----------------
@bot.message_handler(func=lambda m: m.text == "Вопрос")
def q_start(m):
    state[m.from_user.id] = {"type": "question", "step": 1}
    bot.send_message(m.chat.id, "Введите ваш Ник:")


# ---------------- BUG ----------------
@bot.message_handler(func=lambda m: m.text == "Баг")
def b_start(m):
    state[m.from_user.id] = {"type": "bug", "step": 1}
    bot.send_message(m.chat.id, "Введите ваш Ник:")


# ---------------- VACANCIES ----------------
@bot.message_handler(func=lambda m: m.text == "Открытые вакансии")
def vac(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "Медиа",
        url="https://docs.google.com/forms/d/1ZUh1SNLY0n4PeevHKWy6SeoTBDP-nTJwTV2f4VjcwOk/viewform"
    ))
    kb.add(types.InlineKeyboardButton(
        "Стажер",
        url="https://docs.google.com/forms/d/1sqtfB4KQL9yE_PXBtPdKTpoIc7VQqrYHk4NbmkfzNFQ/viewform"
    ))
    bot.send_message(m.chat.id, "Вакансии:", reply_markup=kb)


# ---------------- COMPLAINT ----------------
@bot.message_handler(func=lambda m: m.text == "Жалоба на игрока")
def c_start(m):
    state[m.from_user.id] = {"type": "complaint", "step": 1}
    bot.send_message(m.chat.id, "Введите ваш Ник:")


# ---------------- TEXT HANDLER ----------------
@bot.message_handler(content_types=["text"])
def text(m):
    uid = m.from_user.id

    # ADMIN ANSWER
    if uid == ADMIN_ID and uid in admin_reply_to:
        user_id = admin_reply_to[uid]
        bot.send_message(user_id, "Ответ от администрации:\n" + m.text)
        bot.send_message(uid, "Ответ отправлен.")
        del admin_reply_to[uid]
        return

    if uid not in state:
        return

    s = state[uid]

    # -------- QUESTION --------
    if s["type"] == "question":

        if s["step"] == 1:
            s["nick"] = m.text
            s["step"] = 2
            bot.send_message(uid, "Введите ваш вопрос:")
            return

        if s["step"] == 2:
            s["question"] = m.text

            bot.send_message(uid, "Вопрос передан руководству.")

            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("Ответить", callback_data=f"ans_{uid}"))

            bot.send_message(
                ADMIN_ID,
                "НОВЫЙ ВОПРОС\n\nНик: " + s["nick"] + "\nВопрос: " + s["question"],
                reply_markup=kb
            )

            del state[uid]
            return

    # -------- BUG --------
    if s["type"] == "bug":

        if s["step"] == 1:
            s["nick"] = m.text
            s["step"] = 2
            bot.send_message(uid, "Найденный баг:")
            return

        if s["step"] == 2:
            s["bug"] = m.text
            s["step"] = 3
            bot.send_message(uid, "Как вы его спровоцировали:")
            return

        if s["step"] == 3:
            s["how"] = m.text

            bot.send_message(uid, "Баг передан руководству.")

            bot.send_message(
                ADMIN_ID,
                "НОВЫЙ БАГ\n\nНик: " + s["nick"] +
                "\nБаг: " + s["bug"] +
                "\nКак: " + s["how"]
            )

            del state[uid]
            return

    # -------- COMPLAINT TEXT --------
    if s["type"] == "complaint":

        if s["step"] == 1:
            s["nick"] = m.text
            s["step"] = 2
            bot.send_message(uid, "Ник игрока:")
            return

        if s["step"] == 2:
            s["target"] = m.text
            s["step"] = 3
            bot.send_message(uid, "Его нарушение:")
            return

        if s["step"] == 3:
            s["violation"] = m.text
            s["step"] = 4
            bot.send_message(uid, "Прикрепите фото или видео:")
            return


# ---------------- MEDIA (FIXED) ----------------
@bot.message_handler(content_types=["photo", "video"])
def media(m):
    uid = m.from_user.id

    if uid not in state:
        return

    s = state[uid]

    if s.get("type") != "complaint":
        return

    if s.get("step") != 4:
        bot.send_message(uid, "Сначала заполните все поля жалобы.")
        return

    global complaint_id
    complaint_id += 1

    if m.content_type == "photo":
        file_id = m.photo[-1].file_id
        mtype = "photo"
    else:
        file_id = m.video.file_id
        mtype = "video"

    complaints[complaint_id] = {
        "uid": uid,
        "nick": s["nick"],
        "target": s["target"],
        "violation": s["violation"],
        "file_id": file_id,
        "type": mtype
    }

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("Принять", callback_data=f"ok_{complaint_id}"),
        types.InlineKeyboardButton("Отклонить", callback_data=f"no_{complaint_id}")
    )

    text = (
        "ЖАЛОБА #" + str(complaint_id) +
        "\nНик: " + s["nick"] +
        "\nИгрок: " + s["target"] +
        "\nНарушение: " + s["violation"]
    )

    if mtype == "photo":
        bot.send_photo(ADMIN_ID, file_id, caption=text, reply_markup=kb)
    else:
        bot.send_video(ADMIN_ID, file_id, caption=text, reply_markup=kb)

    bot.send_message(uid, "Жалоба отправлена.")

    del state[uid]


# ---------------- CALLBACKS ----------------
@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    data = call.data

    if data.startswith("ans_"):
        uid = int(data.split("_")[1])
        admin_reply_to[call.from_user.id] = uid
        bot.send_message(call.from_user.id, "Введите ответ:")
        return

    if data.startswith("ok_"):
        cid = int(data.split("_")[1])
        comp = complaints[cid]
        bot.send_message(comp["uid"], "Ваша жалоба одобрена.")
        bot.send_message(call.message.chat.id, "Жалоба принята.")
        return

    if data.startswith("no_"):
        cid = int(data.split("_")[1])
        comp = complaints[cid]
        bot.send_message(comp["uid"], "Ваша жалоба отклонена.")
        bot.send_message(call.message.chat.id, "Жалоба отклонена.")
        return


bot.polling(none_stop=True)