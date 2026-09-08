import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

API_ID = 35554225
API_HASH = "638334a4943ae8ee4eccac9b23f037ec"
BOT_TOKEN = "8755509692:AAHKS3sPPLURVZ8dnqd1rUMAPQ8H1gLdQkQ"

app = Client("matrix_rename_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_data = {}

async def auto_delete_file(client, chat_id, message_id):
    await asyncio.sleep(43200)
    try:
        await client.delete_messages(chat_id, message_id)
    except Exception:
        pass

def humanbytes(size):
    if not size:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((f"{days}d, " if days else "") +
           (f"{hours}h, " if hours else "") +
           (f"{minutes}m, " if minutes else "") +
           (f"{seconds}s" if seconds else ""))
    return tmp[:-2] if tmp.endswith(", ") else tmp or "0s"

async def progress_bar(current, total, status_text, start_time, message: Message):
    now = time.time()
    diff = now - start_time
    if round(diff % 3) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        
        if speed > 0:
            eta_seconds = (total - current) / speed
            eta_str = TimeFormatter(eta_seconds * 1000)
        else:
            eta_str = "கணக்கிடப்படுகிறது..."

        filled_length = int(12 * current // total)
        bar = "█" * filled_length + "░" * (12 - filled_length)

        progress_str = (
            f"🔄 **{status_text}...**\n\n"
            f"[{bar}] `{percentage:.2f}%`\n\n"
            f"🚀 **வேகம்:** `{humanbytes(speed)}/s`\n"
            f"📦 **முடிந்தது:** `{humanbytes(current)}` / `{humanbytes(total)}`\n"
            f"⏱️ **மீதமுள்ள நேரம் (ETA):** `{eta_str}`"
        )
        try:
            await message.edit_text(progress_str)
        except Exception:
            pass

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text("👋 **வணக்கம்!**\n\nஎனக்கு 2GB அளவுக்குள்ள இருக்குற வீடியோ அல்லது டாக்குமெண்ட் ஃபைலை அனுப்புங்க.")

@app.on_message(filters.document | filters.video)
async def handle_media(client, message):
    file_size = message.document.file_size if message.document else message.video.file_size
    
    if file_size > 2000 * 1024 * 1024:
        await message.reply_text("❌ இந்த ஃபைல் 2GB-க்கு மேல இருக்கு! 2GB வரைக்கும் தான் அப்லோட் பண்ண முடியும்.")
        return

    chat_id = message.chat.id
    user_data[chat_id] = {"media_msg": message}

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ பெயர் மட்டும் மாற்ற (Rename Only)", callback_data="mode_rename")],
        [InlineKeyboardButton("🖼️ தம்ப்லைன் மட்டும் மாற்ற (Thumb Only)", callback_data="mode_thumb")],
        [InlineKeyboardButton("⚡ இரண்டும் மாற்ற (Rename & Thumb)", callback_data="mode_both")]
    ])
    
    await message.reply_text("என்ன பண்ணனும்னு கீழ இருக்குற ஆப்சனை தேர்வு செய்யுங்க:", reply_markup=buttons)

@app.on_callback_query()
async def button_callback(client, callback):
    chat_id = callback.message.chat.id
    data = callback.data

    if chat_id not in user_data or "media_msg" not in user_data[chat_id]:
        await callback.message.edit_text("❌ நேரம் முடிந்தது. மீண்டும் ஃபைலை அனுப்புங்கள்.")
        return

    if data.startswith("mode_"):
        mode = data.replace("mode_", "")
        user_data[chat_id]["mode"] = mode

        if mode in ["rename", "both"]:
            await callback.message.edit_text("✏️ **புதிய ஃபைல் பெயரை டைப் செய்து அனுப்புங்கள்:**\nஎடுத்துக்காட்டு: `My_Movie_2026`")
            user_data[chat_id]["step"] = "await_rename"
        elif mode == "thumb":
            await callback.message.edit_text("🖼️ **புதிய தம்ப்லைன் போட்டோவை அனுப்புங்கள்:**")
            user_data[chat_id]["step"] = "await_thumb"

    elif data.startswith("fmt_"):
        upload_fmt = data.replace("fmt_", "")
        user_data[chat_id]["upload_fmt"] = upload_fmt
        await callback.message.edit_text("⏳ **வேலை தொடங்குகிறது...**")
        await start_processing(client, chat_id, callback.message)

@app.on_message(filters.text & ~filters.regex(r"^/"))
async def handle_text(client, message):
    chat_id = message.chat.id
    if chat_id in user_data and user_data[chat_id].get("step") == "await_rename":
        user_data[chat_id]["new_name"] = message.text.strip()
        
        if user_data[chat_id]["mode"] == "both":
            await message.reply_text("🖼️ அடுத்து: புதிய தம்ப்லைன் போட்டோவை அனுப்புங்கள்:")
            user_data[chat_id]["step"] = "await_thumb"
        else:
            user_data[chat_id]["step"] = None
            await ask_upload_format(client, chat_id)

@app.on_message(filters.photo)
async def handle_photo(client, message):
    chat_id = message.chat.id
    if chat_id in user_data and user_data[chat_id].get("step") == "await_thumb":
        status_msg = await message.reply_text("📥 **தம்ப்லைன் பதிவிறக்கம் செய்யப்படுகிறது...**")
        thumb_path = await client.download_media(message.photo)
        user_data[chat_id]["thumb_path"] = thumb_path
        user_data[chat_id]["step"] = None
        await status_msg.delete()
        
        await ask_upload_format(client, chat_id)

async def ask_upload_format(client, chat_id):
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 MKV டாக்குமெண்ட் ஃபார்மட்", callback_data="fmt_mkv"),
            InlineKeyboardButton("🎬 வீடியோ ஃபார்மட் (MP4)", callback_data="fmt_video")
        ]
    ])
    await client.send_message(chat_id, "ஃபைலை எந்த ஃபார்மட்ல அப்லோட் பண்ணனும்னு தேர்வு செய்யுங்க:", reply_markup=buttons)

async def start_processing(client, chat_id, status_msg):
    data = user_data.get(chat_id)
    if not data:
        return

    media_msg = data["media_msg"]
    new_name = data.get("new_name")
    thumb_path = data.get("thumb_path")
    upload_fmt = data.get("upload_fmt", "mkv")

    ext = ".mkv" if upload_fmt == "mkv" else ".mp4"

    start_time = time.time()
    await status_msg.edit_text("📥 **ஃபைல் பதிவிறக்கம் ஆகிறது...**")

    downloaded_path = await client.download_media(
        media_msg,
        progress=progress_bar,
        progress_args=("பதிவிறக்கம் செய்யப்படுகிறது", start_time, status_msg)
    )

    if new_name:
        dir_name = os.path.dirname(downloaded_path)
        final_path = os.path.join(dir_name, f"{new_name}{ext}")
        os.rename(downloaded_path, final_path)
    else:
        final_path = downloaded_path

    upload_start_time = time.time()
    await status_msg.edit_text("📤 **ஃபைல் பதிவேற்றம் ஆகிறது...**")

    sent_msg = None
    if upload_fmt == "video":
        sent_msg = await client.send_video(
            chat_id=chat_id,
            video=final_path,
            thumb=thumb_path if thumb_path else None,
            caption=f"✅ **வெற்றிகரமாக அனுப்பப்பட்டது!**\n📄 **பெயர்:** `{os.path.basename(final_path)}`",
            progress=progress_bar,
            progress_args=("பதிவேற்றம் செய்யப்படுகிறது", upload_start_time, status_msg)
        )
    else:
        sent_msg = await client.send_document(
            chat_id=chat_id,
            document=final_path,
            thumb=thumb_path if thumb_path else None,
            caption=f"✅ **வெற்றிகரமாக அனுப்பப்பட்டது!**\n📄 **பெயர்:** `{os.path.basename(final_path)}`",
            progress=progress_bar,
            progress_args=("பதிவேற்றம் செய்யப்படுகிறது", upload_start_time, status_msg)
        )

    await status_msg.delete()

    warning_msg = await client.send_message(
        chat_id, 
        "⚠️ **கவனிக்க:** இந்த ஃபைல் 12 மணி நேரத்துல தானா அழிஞ்சிடும்! அதனால வேற எங்காச்சும் சேவ் பண்ணி வச்சுக்கோங்க."
    )

    if os.path.exists(final_path):
        os.remove(final_path)
    if thumb_path and os.path.exists(thumb_path):
        os.remove(thumb_path)
    
    del user_data[chat_id]

    if sent_msg:
        asyncio.create_task(auto_delete_file(client, chat_id, sent_msg.id))
    if warning_msg:
        asyncio.create_task(auto_delete_file(client, chat_id, warning_msg.id))

print("பாட் இயங்குகிறது...")
app.run()

