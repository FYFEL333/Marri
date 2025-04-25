# utils.py  — окончательный
import os, json, time, requests

BOT_TOKEN = "7587962873:AAF5lds518iLooybIEjMqPa5tBD-DDiEJ5s"   # ← ВСЁ! тут токен
ADMIN_ID  = 6037202333

API_URL   = f"https://api.telegram.org/bot{BOT_TOKEN}"

HERE        = os.path.dirname(__file__)
STORAGE_DIR = os.path.join(HERE, "storage")
PAIR_FILE   = os.path.join(STORAGE_DIR, "marriages.json")

# ---------- Telegram ----------
def tg(method: str, **params):
    resp = requests.post(f"{API_URL}/{method}", json=params, timeout=30)
    return resp.json()

def send(chat_id, text, **kw):
    return tg("sendMessage", chat_id=chat_id, text=text,
              parse_mode="HTML", disable_web_page_preview=True, **kw)

def edit(chat_id, msg_id, **kw):
    return tg("editMessageText", chat_id=chat_id, message_id=msg_id, **kw)

def answer_callback(cb_id, text="", show_alert=False):
    tg("answerCallbackQuery", callback_query_id=cb_id,
       text=text, show_alert=show_alert)

# ---------- Storage ----------
def _ensure_file():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    if not os.path.exists(PAIR_FILE):
        with open(PAIR_FILE, "w", encoding="utf-8") as f:
            f.write("{}")

def load_state():
    _ensure_file()
    with open(PAIR_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_state(data):
    _ensure_file()
    with open(PAIR_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- Красивый «сколько времени вместе» ----------
def human_delta(sec):
    units = [('год',31536000),('месяц',2592000),('день',86400),
             ('час',3600),('минута',60)]
    parts=[]
    for name, s in units:
        q, sec = divmod(sec, s)
        if q:
            if name=='год':
                w='год'if q%10==1 and q%100!=11 else'года'if q%10 in(2,3,4)\
                    and q%100 not in(12,13,14)else'лет'
            elif name=='месяц':
                w='месяц'if q%10==1 and q%100!=11 else'месяца'if q%10 in(2,3,4)\
                    and q%100 not in(12,13,14)else'месяцев'
            elif name=='день':
                w='день'if q%10==1 and q%100!=11 else'дня'if q%10 in(2,3,4)\
                    and q%100 not in(12,13,14)else'дней'
            elif name=='час':
                w='час'if q%10==1 and q%100!=11 else'часа'if q%10 in(2,3,4)\
                    and q%100 not in(12,13,14)else'часов'
            else:
                w='минута'if q%10==1 and q%100!=11 else'минуты'if q%10 in(2,3,4)\
                    and q%100 not in(12,13,14)else'минут'
            parts.append(f"{q} {w}")
        if len(parts)==2: break
    return ', '.join(parts) if parts else 'меньше минуты'
