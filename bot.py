# bot.py  – под wb_utils.py, стикеры, сообщение не удаляется, имена обновляются
import time, json
from wb_utils import (tg, send, edit, answer_callback,
                      load_state, save_state, human_delta, ADMIN_ID)

# ---------- стикеры ----------
STK_PROPOSAL = "CAACAgIAAxkBAAEOo-hoC1giSTz8OfIgXQKk0G9xmggRuwACyWAAAhGSeUkhrgbAgeWsAzYE"
STK_ACCEPT   = "CAACAgIAAxkBAAEOpBJoC1lmMeeYXAwTYBMxQUbMDMpJkQACnGkAAjVceUmr2v2MsvShNDYE"
# -----------------------------

POLL_TIMEOUT   = 25
MARRY_TIMEOUT  = 3 * 3600
OFFSET         = 0

state = load_state()             # {chat_id:{marriages:[], proposals:[]}}

# ---------- helpers ----------

def chat_bucket(chat_id: int):
    k = str(chat_id)
    if k not in state:
        state[k] = {"marriages": [], "proposals": []}
    return state[k]

def already_married(chat_id, user_id):
    return any(m["is_active"] and user_id in (m["p1_id"], m["p2_id"])
               for m in chat_bucket(chat_id)["marriages"])

def clear_buttons(chat_id, message_id):
    try:
        tg("editMessageReplyMarkup",
           chat_id=chat_id,
           message_id=message_id,
           reply_markup={"inline_keyboard": []})
    except Exception:
        pass

def purge_old_proposals():
    now = int(time.time())
    for chat_id, bucket in state.items():
        for prop in bucket["proposals"][:]:
            if now - prop["created_at"] >= MARRY_TIMEOUT:
                clear_buttons(int(chat_id), prop["message_id"])
                send(int(chat_id), "⌛️ Предложение истекло.")
                bucket["proposals"].remove(prop)
    save_state(state)

def announce_divorce(chat_id, pair):
    txt = (f"⚡️ {pair['p1_name']} и {pair['p2_name']} официально развелись.\n"
           "Иногда дороги расходятся, чтобы каждый нашёл своё счастье.\n"
           "Без ссор, без драмы — просто новая глава.\n"
           "Спасибо за всё, что было, и удачи в том, что будет.\n"
           "💔🕊")
    send(chat_id, txt)

# ----- свежие имена -----

def get_first_name(chat_id: int, user_id: int, fallback: str) -> str:
    """
    Пытаемся получить актуальный first_name через getChatMember.
    Если не вышло (пользователь вышел или ограничен) — возвращаем запасной вариант.
    """
    try:
        r = tg("getChatMember", chat_id=chat_id, user_id=user_id)
        if r.get("ok"):
            return r["result"]["user"]["first_name"]
    except Exception:
        pass
    return fallback

# ---------- /marry ----------

def handle_marry(msg):
    chat_id = msg["chat"]["id"]
    frm_id  = msg["from"]["id"]
    frm_nm  = msg["from"]["first_name"]

    rep = msg.get("reply_to_message")
    if not rep:
        send(chat_id, "Сделай /marry реплаем на сообщение пользователя 💍")
        return
    to_id  = rep["from"]["id"]
    to_nm  = rep["from"]["first_name"]

    if frm_id == to_id:
        send(chat_id, "Сам(а) на себе не женишься 😉")
        return
    if already_married(chat_id, frm_id):
        send(chat_id, "Ты уже в браке — сначала разведись.")
        return
    if already_married(chat_id, to_id):
        send(chat_id, f"{to_nm} уже в браке.")
        return

    tg("sendSticker", chat_id=chat_id, sticker=STK_PROPOSAL)

    text = (f"💍 {frm_nm} делает предложение {to_nm} !\n"
            "Сердце бьётся быстрее, руки дрожат, а в глазах — любовь.\n"
            "“Ты выйдешь за меня?” — прозвучало сейчас для всех нас.\n"
            f"Затаим дыхание... что ответит {to_nm} ?\n"
            "— Весь чат держит кулачки!\n❤️✨")
    kb = {"inline_keyboard": [[
        {"text": "Принять 💍",   "callback_data": f"acc:{frm_id}"},
        {"text": "Отклонить ❌", "callback_data": f"dec:{frm_id}"}
    ]]}
    r = send(chat_id, text, reply_markup=kb)
    chat_bucket(chat_id)["proposals"].append({
        "from_id": frm_id, "from_name": frm_nm,
        "to_id": to_id,   "to_name": to_nm,
        "message_id": r["result"]["message_id"],
        "created_at": int(time.time())
    })
    save_state(state)

# ---------- callback accept / decline ----------

def handle_callback(cb):
    data    = cb["data"]
    chat_id = cb["message"]["chat"]["id"]
    msg_id  = cb["message"]["message_id"]
    uid     = cb["from"]["id"]

    bucket = chat_bucket(chat_id)
    prop = next((p for p in bucket["proposals"] if p["message_id"] == msg_id), None)
    if not prop:
        answer_callback(cb["id"], "Уже неактуально.")
        return
    if uid != prop["to_id"]:
        answer_callback(cb["id"], "Кнопки только для адресата!")
        return

    clear_buttons(chat_id, msg_id)

    if data.startswith("acc"):
        tg("sendSticker", chat_id=chat_id, sticker=STK_ACCEPT)

        bucket["marriages"].append({
            "p1_id": prop["from_id"], "p1_name": prop["from_name"],
            "p2_id": prop["to_id"],   "p2_name": prop["to_name"],
            "married_at": int(time.time()),
            "is_active": True
        })
        send(chat_id,
             f"💍 Она сказала “да”!\n"
             f"{prop['from_name']} + {prop['to_name']} теперь вместе навсегда!\n"
             "Поздравляем вас! ❤️✨")
    else:
        send(chat_id,
             f"💔 {prop['to_name']} отклонил(а) предложение {prop['from_name']}\n"
             "Мы рядом, всё ещё впереди! 🖤")

    bucket["proposals"].remove(prop)
    save_state(state)
    answer_callback(cb["id"])

# ---------- /razvod ----------

def handle_razvod(msg):
    chat_id = msg["chat"]["id"]
    uid     = msg["from"]["id"]
    nm      = msg["from"]["first_name"]
    bucket  = chat_bucket(chat_id)
    pair = next((m for m in bucket["marriages"]
                 if m["is_active"] and uid in (m["p1_id"], m["p2_id"])), None)
    if not pair:
        send(chat_id, "Ты ни с кем не женат(а).")
        return
    other_id   = pair["p2_id"] if pair["p1_id"] == uid else pair["p1_id"]
    other_name = get_first_name(chat_id, other_id,
                                pair["p2_name"] if pair["p1_id"] == uid else pair["p1_name"])
    kb = {"inline_keyboard":[[
        {"text":"Согласиться на развод 💔", "callback_data":f"div:{uid}"}
    ]]}
    send(chat_id,
         f"⚠️ {nm} хочет развестись с {other_name}.",
         reply_markup=kb)

def handle_divorce_confirm(cb):
    chat_id = cb["message"]["chat"]["id"]
    uid     = cb["from"]["id"]
    who     = int(cb["data"].split(":")[1])
    bucket  = chat_bucket(chat_id)
    pair = next((m for m in bucket["marriages"]
                 if m["is_active"] and who in (m["p1_id"], m["p2_id"])), None)
    if not pair or uid not in (pair["p1_id"], pair["p2_id"]):
        answer_callback(cb["id"], "Не твоя кнопка.")
        return
    pair["is_active"] = False
    save_state(state)
    clear_buttons(chat_id, cb["message"]["message_id"])
    send(chat_id, "Развод оформлен 🖋")
    answer_callback(cb["id"])
    announce_divorce(chat_id, pair)

# ---------- /rating ----------

def handle_rating(msg):
    chat_id = msg["chat"]["id"]
    active = [m for m in chat_bucket(chat_id)["marriages"] if m["is_active"]]
    if not active:
        send(chat_id, "Пока никто не женат 💔")
        return

    now = int(time.time())
    lines = ["👑 Наши пары\n"]

    for m in active:
        # подтягиваем свежие first_name
        p1 = get_first_name(chat_id, m["p1_id"], m["p1_name"])
        p2 = get_first_name(chat_id, m["p2_id"], m["p2_name"])
        lines.append(f"{p1} + {p2} — {human_delta(now - m['married_at'])}\n")

    send(chat_id, "\n".join(lines).rstrip())

# ---------- /xui ----------

def handle_xui(msg):
    if msg["from"]["id"] != ADMIN_ID:
        return
    rep = msg.get("reply_to_message")
    if not rep:
        send(msg["chat"]["id"], "Сделай /xui реплаем.")
        return
    victim = rep["from"]["id"]
    chat_id= msg["chat"]["id"]
    bucket = chat_bucket(chat_id)
    pair = next((m for m in bucket["marriages"]
                 if m["is_active"] and victim in (m["p1_id"], m["p2_id"])), None)
    if not pair:
        send(chat_id, f"{rep['from']['first_name']} не в браке.")
        return
    pair["is_active"] = False
    save_state(state)
    announce_divorce(chat_id, pair)

# ---------- user left ----------

def handle_left(upd):
    chat_id = upd["my_chat_member"]["chat"]["id"]
    uid     = upd["my_chat_member"]["from"]["id"]
    bucket  = chat_bucket(chat_id)
    pair = next((m for m in bucket["marriages"]
                 if m["is_active"] and uid in (m["p1_id"], m["p2_id"])), None)
    if pair:
        pair["is_active"] = False
        save_state(state)
        announce_divorce(chat_id, pair)

# ---------- main loop ----------

CMD = {
    "/marry":  handle_marry,
    "/razvod": handle_razvod,
    "/rating": handle_rating,
    "/xui":    handle_xui,
}

def main():
    global OFFSET
    while True:
        upd = tg("getUpdates", offset=OFFSET, timeout=POLL_TIMEOUT)
        for u in upd.get("result", []):
            OFFSET = u["update_id"] + 1
            if "message" in u and "text" in u["message"]:
                cmd = u["message"]["text"].split()[0]
                if cmd in CMD:
                    CMD[cmd](u["message"])
            elif "callback_query" in u:
                cb = u["callback_query"]
                if cb["data"].startswith(("acc","dec")):
                    handle_callback(cb)
                elif cb["data"].startswith("div"):
                    handle_divorce_confirm(cb)
            elif u.get("my_chat_member",{}).get("new_chat_member",{}).get("status") == "left":
                handle_left(u)
        purge_old_proposals()

if __name__ == "__main__":
    main()
