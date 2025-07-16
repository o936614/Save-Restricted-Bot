import subprocess
import sys

# تثبيت الحزم المطلوبة إذا لم تكن موجودة
required_packages = ["pyrogram, tgcrypto"]
for pkg in required_packages:
    try:
        __import__(pkg)
    except ImportError:
        print(f"Installing {pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

import pyrogram
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied, PeerIdInvalid
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keep_alive import keep_alive
keep_alive()

import time
import os
import threading
import json

with open('config.json', 'r') as f: DATA = json.load(f)
def getenv(var): return os.environ.get(var) or DATA.get(var, None)

bot_token = getenv("TOKEN") 
api_hash = getenv("HASH") 
api_id = getenv("ID")
bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

ss = getenv("STRING")
if ss is not None:
    acc = Client("myacc" ,api_id=api_id, api_hash=api_hash, session_string=ss)
    acc.start()
else: acc = None

user_bulk_state = {}  # user_id: {"step": 1, "first_link": None}
user_single_state = set()  # user_id الذين ينتظرون رابط واحد بعد /single

# download status
def downstatus(statusfile,message):
    while True:
        if os.path.exists(statusfile):
            break

    time.sleep(3)      
    while os.path.exists(statusfile):
        with open(statusfile,"r") as downread:
            txt = downread.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, f"__Downloaded__ : **{txt}**")
            time.sleep(10)
        except:
            time.sleep(5)

# upload status
def upstatus(statusfile,message):
    while True:
        if os.path.exists(statusfile):
            break

    time.sleep(3)      
    while os.path.exists(statusfile):
        with open(statusfile,"r") as upread:
            txt = upread.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, f"__Uploaded__ : **{txt}**")
            time.sleep(10)
        except:
            time.sleep(5)

# progress writter
def progress(current, total, message, type):
    with open(f'{message.id}{type}status.txt',"w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")

# فلترة الـ entities
def filter_entities(entities):
    """Remove entities with unknown users to avoid PeerIdInvalid error."""
    filtered = []
    for e in entities or []:
        if hasattr(e, "user"):
            if getattr(e.user, "id", None) is not None:
                filtered.append(e)
        else:
            filtered.append(e)
    return filtered

# start command
@bot.on_message(filters.command(["start"]))
def send_start(client: pyrogram.client.Client, message: pyrogram.types.messages_and_media.message.Message):
    bot.send_message(message.chat.id, f"__👋 Hi **{message.from_user.mention}**, I am Save Restricted Bot, I can send you restricted content by its post link__")

# إضافة أمر /single لمعالجة رابط واحد فقط
@bot.on_message(filters.command(["single"]))
def single_command(client: pyrogram.client.Client, message: pyrogram.types.messages_and_media.message.Message):
    user_single_state.add(message.from_user.id)
    bot.send_message(message.chat.id, "يرجى إرسال رابط الرسالة التي تريد معالجتها.")

# إضافة أمر /bulk لمعالجة عدة روابط
@bot.on_message(filters.command(["bulk"]))
def bulk_command(client: pyrogram.client.Client, message: pyrogram.types.messages_and_media.message.Message):
    user_id = message.from_user.id
    user_bulk_state[user_id] = {"step": 1, "first_link": None}
    bot.send_message(message.chat.id, "يرجى إرسال رابط الرسالة الأولى.")

@bot.on_message(filters.text)
def save(client: pyrogram.client.Client, message: pyrogram.types.messages_and_media.message.Message):
    user_id = message.from_user.id

    # معالجة حالة /bulk
    if user_id in user_bulk_state:
        state = user_bulk_state[user_id]
        if state["step"] == 1:
            state["first_link"] = message.text.strip()
            state["step"] = 2
            bot.send_message(message.chat.id, "يرجى إرسال رابط الرسالة الأخيرة.")
            return
        elif state["step"] == 2:
            first_link = state["first_link"]
            last_link = message.text.strip()
            del user_bulk_state[user_id]
            try:
                # استخراج بيانات الرابط الأول والأخير
                f_datas = first_link.split("/")
                l_datas = last_link.split("/")
                if "https://t.me/c/" in first_link and "https://t.me/c/" in last_link:
                    chatid = int("-100" + f_datas[4])
                else:
                    chatid = f_datas[3]  # username

                # رقم الرسالة الأولى والأخيرة
                f_msgid = int(f_datas[-1].replace("?single", "").strip())
                l_msgid = int(l_datas[-1].replace("?single", "").strip())

                # معالجة الرسائل من الأولى للأخيرة
                for msgid in range(f_msgid, l_msgid+1):
                    if "https://t.me/c/" in first_link:
                        if acc is None:
                            bot.send_message(message.chat.id,f"**String Session is not Set**")
                            return
                        handle_private(message, chatid, msgid)
                    else:
                        try:
                            msg = bot.get_messages(chatid, msgid)
                        except UsernameNotOccupied: 
                            bot.send_message(message.chat.id,f"**The username is not occupied by anyone**")
                            continue
                        try:
                            bot.copy_message(message.chat.id, msg.chat.id, msg.id)
                        except:
                            if acc is None:
                                bot.send_message(message.chat.id,f"**String Session is not Set**")
                                continue
                            try:
                                handle_private(message, chatid, msgid)
                            except Exception as e:
                                bot.send_message(message.chat.id,f"**Error** : __{e}__")
                    time.sleep(3)
            except Exception as e:
                bot.send_message(message.chat.id, f"حدث خطأ أثناء معالجة الروابط: {e}")
            return

    # معالجة حالة /single
    if user_id in user_single_state:
        user_single_state.remove(user_id)
        # نتوقع أن المستخدم أرسل رابط رسالة واحدة فقط
        if message.text.startswith("https://t.me/"):
            datas = message.text.split("/")
            temp = datas[-1].replace("?single","").strip()
            msgid = int(temp)
            # private
            if "https://t.me/c/" in message.text:
                chatid = int("-100" + datas[4])
                if acc is None:
                    bot.send_message(message.chat.id,f"**String Session is not Set**", reply_to_message_id=message.id)
                    return
                handle_private(message, chatid, msgid)
            # bot
            elif "https://t.me/b/" in message.text:
                username = datas[4]
                if acc is None:
                    bot.send_message(message.chat.id,f"**String Session is not Set**", reply_to_message_id=message.id)
                    return
                try: handle_private(message, username, msgid)
                except Exception as e: bot.send_message(message.chat.id,f"**Error** : __{e}__", reply_to_message_id=message.id)
            # public
            else:
                username = datas[3]
                try: msg  = bot.get_messages(username, msgid)
                except UsernameNotOccupied: 
                    bot.send_message(message.chat.id,f"**The username is not occupied by anyone**", reply_to_message_id=message.id)
                    return
                try:
                    bot.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                except:
                    if acc is None:
                        bot.send_message(message.chat.id,f"**String Session is not Set**", reply_to_message_id=message.id)
                        return
                    try: handle_private(message, username, msgid)
                    except Exception as e: bot.send_message(message.chat.id,f"**Error** : __{e}__", reply_to_message_id=message.id)
            return
        else:
            bot.send_message(message.chat.id, "الرابط غير صحيح، يرجى إرسال رابط رسالة تلغرام.")
            return

    # باقي الحالات
    if message.text.startswith("https://t.me/+") or message.text.startswith("https://t.me/joinchat/"):
        if acc is None:
            bot.send_message(message.chat.id,f"**String Session is not Set**", reply_to_message_id=message.id)
            return
        try:
            try: acc.join_chat(message.text)
            except Exception as e: 
                bot.send_message(message.chat.id,f"**Error** : __{e}__", reply_to_message_id=message.id)
                return
            bot.send_message(message.chat.id,"**Chat Joined**", reply_to_message_id=message.id)
        except UserAlreadyParticipant:
            bot.send_message(message.chat.id,"**Chat already Joined**", reply_to_message_id=message.id)
        except InviteHashExpired:
            bot.send_message(message.chat.id,"**Invalid Link**", reply_to_message_id=message.id)
    else:
        print(message.text)

# handle private
def handle_private(message: pyrogram.types.messages_and_media.message.Message, chatid: int, msgid: int):
    msg: pyrogram.types.messages_and_media.message.Message = acc.get_messages(chatid,msgid)
    msg_type = get_message_type(msg)

    if "Text" == msg_type:
        safe_entities = filter_entities(msg.entities)
        if safe_entities:
            try:
                bot.send_message(message.chat.id, msg.text, entities=safe_entities, reply_to_message_id=message.id)
            except PeerIdInvalid:
                bot.send_message(message.chat.id, msg.text, reply_to_message_id=message.id)
        else:
            bot.send_message(message.chat.id, msg.text, reply_to_message_id=message.id)
        return

    smsg = bot.send_message(message.chat.id, '__Downloading__', reply_to_message_id=message.id)
    dosta = threading.Thread(target=lambda:downstatus(f'{message.id}downstatus.txt',smsg),daemon=True)
    dosta.start()
    file = acc.download_media(msg, progress=progress, progress_args=[message,"down"])
    os.remove(f'{message.id}downstatus.txt')

    upsta = threading.Thread(target=lambda:upstatus(f'{message.id}upstatus.txt',smsg),daemon=True)
    upsta.start()
    
    if "Document" == msg_type:
        try:
            thumb = acc.download_media(msg.document.thumbs[0].file_id)
        except: thumb = None
        
        bot.send_document(message.chat.id, file, thumb=thumb, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message,"up"])
        if thumb != None: os.remove(thumb)

    elif "Video" == msg_type:
        try: 
            thumb = acc.download_media(msg.video.thumbs[0].file_id)
        except: thumb = None

        bot.send_video(message.chat.id, file, duration=msg.video.duration, width=msg.video.width, height=msg.video.height, thumb=thumb, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message,"up"])
        if thumb != None: os.remove(thumb)

    elif "Animation" == msg_type:
        bot.send_animation(message.chat.id, file, reply_to_message_id=message.id)
           
    elif "Sticker" == msg_type:
        bot.send_sticker(message.chat.id, file, reply_to_message_id=message.id)

    elif "Voice" == msg_type:
        bot.send_voice(message.chat.id, file, caption=msg.caption, thumb=None, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message,"up"])

    elif "Audio" == msg_type:
        try:
            thumb = acc.download_media(msg.audio.thumbs[0].file_id)
        except: thumb = None
            
        bot.send_audio(message.chat.id, file, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message,"up"])   
        if thumb != None: os.remove(thumb)

    elif "Photo" == msg_type:
        bot.send_photo(message.chat.id, file, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id)

    os.remove(file)
    if os.path.exists(f'{message.id}upstatus.txt'): os.remove(f'{message.id}upstatus.txt')
    bot.delete_messages(message.chat.id,[smsg.id])

# get the type of message
def get_message_type(msg: pyrogram.types.messages_and_media.message.Message):
    try:
        msg.document.file_id
        return "Document"
    except: pass

    try:
        msg.video.file_id
        return "Video"
    except: pass

    try:
        msg.animation.file_id
        return "Animation"
    except: pass

    try:
        msg.sticker.file_id
        return "Sticker"
    except: pass

    try:
        msg.voice.file_id
        return "Voice"
    except: pass

    try:
        msg.audio.file_id
        return "Audio"
    except: pass

    try:
        msg.photo.file_id
        return "Photo"
    except: pass

    try:
        msg.text
        return "Text"
    except: pass

# infinty polling
bot.run()
