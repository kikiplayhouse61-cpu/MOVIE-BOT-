import os
import json
import time
import requests

TOKEN = os.getenv("8982851762:AAF-db6M4lw1rGCH8sgDpEmPa2S6BjDyyPA")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

API = f"https://api.telegram.org/bot{TOKEN}"
DB_FILE = "content.json"
STATE_FILE = "state.json"


def load_json(file):
    if not os.path.exists(file):
        return {}

    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    if keyboard:
        data["reply_markup"] = json.dumps({
            "inline_keyboard": keyboard
        })

    requests.post(
        f"{API}/sendMessage",
        data=data,
        timeout=20
    )


def send_photo(chat_id, photo_id, caption, keyboard=None):
    data = {
        "chat_id": chat_id,
        "photo": photo_id,
        "caption": caption,
        "parse_mode": "HTML"
    }

    if keyboard:
        data["reply_markup"] = json.dumps({
            "inline_keyboard": keyboard
        })

    requests.post(
        f"{API}/sendPhoto",
        data=data,
        timeout=20
    )


def get_updates(offset=None):
    params = {"timeout": 30}

    if offset is not None:
        params["offset"] = offset

    return requests.get(
        f"{API}/getUpdates",
        params=params,
        timeout=40
    ).json()


def make_id(db):
    n = 1

    while str(n) in db:
        n += 1

    return str(n)


def bot_username():
    try:
        r = requests.get(
            f"{API}/getMe",
            timeout=10
        ).json()

        return r["result"]["username"]

    except:
        return "movie_ott_all_show_bot"


def start_add(chat_id):
    if chat_id != ADMIN_ID:
        send_message(chat_id, "⛔ Admin only.")
        return

    states = load_json(STATE_FILE)

    states[str(chat_id)] = {
        "step": "photo"
    }

    save_json(STATE_FILE, states)

    send_message(
        chat_id,
        "➕ <b>New Content</b>\n\n"
        "Step 1/5\n"
        "🖼️ Ab movie/show ka <b>poster photo</b> bhejo."
    )


def handle_add_process(message):
    chat_id = message["chat"]["id"]

    if chat_id != ADMIN_ID:
        return False

    states = load_json(STATE_FILE)
    key = str(chat_id)

    if key not in states:
        return False

    state = states[key]
    step = state["step"]

    # STEP 1 - PHOTO
    if step == "photo":

        if "photo" not in message:
            send_message(
                chat_id,
                "❌ Pehle <b>photo</b> bhejo."
            )
            return True

        photo_id = message["photo"][-1]["file_id"]

        state["photo_id"] = photo_id
        state["step"] = "title"

        save_json(STATE_FILE, states)

        send_message(
            chat_id,
            "✅ Photo received.\n\n"
            "Step 2/5\n"
            "🎬 Ab <b>Movie / Show Title</b> bhejo."
        )

        return True

    # STEP 2 - TITLE
    if step == "title":

        text = message.get("text", "").strip()

        if not text:
            send_message(
                chat_id,
                "❌ Title text mein bhejo."
            )
            return True

        state["title"] = text
        state["step"] = "480p"

        save_json(STATE_FILE, states)

        send_message(
            chat_id,
            f"🎬 Title: <b>{text}</b>\n\n"
            "Step 3/5\n"
            "🔗 <b>480p link</b> bhejo.\n\n"
            "Agar 480p nahi hai to <code>skip</code> likho."
        )

        return True

    # STEP 3 - 480P
    if step == "480p":

        text = message.get("text", "").strip()

        if text.lower() != "skip":
            state["links"] = {
                "480p": text
            }
        else:
            state["links"] = {}

        state["step"] = "720p"

        save_json(STATE_FILE, states)

        send_message(
            chat_id,
            "Step 4/5\n"
            "🔗 <b>720p link</b> bhejo.\n\n"
            "Nahi hai to <code>skip</code>."
        )

        return True

    # STEP 4 - 720P
    if step == "720p":

        text = message.get("text", "").strip()

        if text.lower() != "skip" and text:
            state["links"]["720p"] = text

        state["step"] = "1080p"

        save_json(STATE_FILE, states)

        send_message(
            chat_id,
            "Step 5/5\n"
            "🔗 <b>1080p link</b> bhejo.\n\n"
            "Nahi hai to <code>skip</code>."
        )

        return True

    # STEP 5 - 1080P
    if step == "1080p":

        text = message.get("text", "").strip()

        if text.lower() != "skip" and text:
            state["links"]["1080p"] = text

        db = load_json(DB_FILE)

        content_id = make_id(db)

        db[content_id] = {
            "title": state["title"],
            "photo_id": state["photo_id"],
            "links": state["links"]
        }

        save_json(DB_FILE, db)

        del states[key]
        save_json(STATE_FILE, states)

        link = (
            f"https://t.me/"
            f"{bot_username()}"
            f"?start={content_id}"
        )

        send_message(
            chat_id,
            "✅ <b>CONTENT SAVED!</b>\n\n"
            f"🎬 <b>{state['title']}</b>\n"
            f"🆔 ID: <code>{content_id}</code>\n\n"
            "🔗 <b>User Link:</b>\n"
            f"{link}\n\n"
            "Is link ko channel ke post/button mein use kar sakte ho."
        )

        return True

    return False


def show_content(chat_id, content_id):

    db = load_json(DB_FILE)

    if content_id not in db:
        send_message(
            chat_id,
            "❌ Content nahi mila."
        )
        return

    item = db[content_id]

    keyboard = []

    for quality, url in item["links"].items():

        keyboard.append([
            {
                "text": f"▶️ {quality}",
                "url": url
            }
        ])

    caption = (
        f"🎬 <b>{item['title']}</b>\n\n"
        "👇 <b>Apni quality select karein:</b>"
    )

    if item.get("photo_id"):
        send_photo(
            chat_id,
            item["photo_id"],
            caption,
            keyboard
        )
    else:
        send_message(
            chat_id,
            caption,
            keyboard
        )


def list_content(chat_id):

    if chat_id != ADMIN_ID:
        send_message(chat_id, "⛔ Admin only.")
        return

    db = load_json(DB_FILE)

    if not db:
        send_message(
            chat_id,
            "📭 Koi content saved nahi hai."
        )
        return

    text = "📚 <b>Saved Content</b>\n\n"

    for cid, item in db.items():
        text += (
            f"🆔 <code>{cid}</code>\n"
            f"🎬 {item['title']}\n\n"
        )

    send_message(chat_id, text)


def delete_content(chat_id, content_id):

    if chat_id != ADMIN_ID:
        send_message(chat_id, "⛔ Admin only.")
        return

    db = load_json(DB_FILE)

    if content_id not in db:
        send_message(
            chat_id,
            "❌ ID nahi mila."
        )
        return

    title = db[content_id]["title"]

    del db[content_id]

    save_json(DB_FILE, db)

    send_message(
        chat_id,
        f"🗑️ Deleted:\n<b>{title}</b>"
    )


def handle_message(message):

    chat_id = message["chat"]["id"]

    # Add process first
    if handle_add_process(message):
        return

    text = message.get("text", "").strip()

    if text == "/add":
        start_add(chat_id)
        return

    if text == "/list":
        list_content(chat_id)
        return

    if text.startswith("/delete "):
        content_id = text.split(maxsplit=1)[1]
        delete_content(chat_id, content_id)
        return

    if text == "/id":
        send_message(
            chat_id,
            f"🆔 Your Telegram ID:\n"
            f"<code>{chat_id}</code>"
        )
        return

    if text.startswith("/start"):

        parts = text.split(maxsplit=1)

        if len(parts) == 1:
            send_message(
                chat_id,
                "👋 <b>Welcome!</b>\n\n"
                "Channel se mila hua content link open karein."
            )
        else:
            content_id = parts[1].strip()
            show_content(chat_id, content_id)

        return

    if text == "/cancel":

        if chat_id == ADMIN_ID:

            states = load_json(STATE_FILE)

            if str(chat_id) in states:
                del states[str(chat_id)]
                save_json(STATE_FILE, states)

            send_message(
                chat_id,
                "❌ Current upload cancelled."
            )

        return


def main():

    if not TOKEN:
        print("❌ BOT_TOKEN missing")
        return

    if not ADMIN_ID:
        print("❌ ADMIN_ID missing")
        return

    print("🤖 Bot started...")

    offset = None

    while True:

        try:

            data = get_updates(offset)

            if data.get("ok"):

                for update in data.get("result", []):

                    offset = update["update_id"] + 1

                    if "message" in update:
                        handle_message(
                            update["message"]
                        )

        except Exception as e:

            print("Error:", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
