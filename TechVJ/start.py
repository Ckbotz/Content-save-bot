# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import asyncio
import random
import pyrogram
from pyrogram import Client, filters, enums
from pyrogram.errors import (
    FloodWait,
    UserIsBlocked,
    InputUserDeactivated,
    UserAlreadyParticipant,
    InviteHashExpired,
    UsernameNotOccupied
)
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, ERROR_MESSAGE, LOGIN_SYSTEM, STRING_SESSION
from database.db import db
from TechVJ.strings import HELP_TXT
from bot import TechVJUser


class batch_temp(object):
    IS_BATCH = {}
    CUSTOM_SLEEP = {}  # Store custom sleep values per user


# Anti-detection sleep function with randomization
async def smart_sleep(user_id):
    """Intelligent sleep with randomization to avoid detection"""
    base_sleep = batch_temp.CUSTOM_SLEEP.get(user_id, [3, 5, 7, 10])
    
    # Pick a random sleep value from the list
    sleep_time = random.choice(base_sleep)
    
    # Add random jitter (±20%) for more natural behavior
    jitter = random.uniform(-0.2, 0.2) * sleep_time
    final_sleep = sleep_time + jitter
    
    await asyncio.sleep(max(1, final_sleep))  # Minimum 1 second


# download status
async def downstatus(client, statusfile, message, chat):
    while True:
        if os.path.exists(statusfile):
            break
        await asyncio.sleep(3)

    while os.path.exists(statusfile):
        with open(statusfile, "r") as downread:
            txt = downread.read()
        try:
            await client.edit_message_text(chat, message.id, f"**Downloaded:** **{txt}**")
            await asyncio.sleep(10)
        except:
            await asyncio.sleep(5)


# upload status
async def upstatus(client, statusfile, message, chat):
    while True:
        if os.path.exists(statusfile):
            break
        await asyncio.sleep(3)

    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            await client.edit_message_text(chat, message.id, f"**Uploaded:** **{txt}**")
            await asyncio.sleep(10)
        except:
            await asyncio.sleep(5)


# progress writer
def progress(current, total, message, type):
    with open(f"{message.id}{type}status.txt", "w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")


# start command
@Client.on_message(filters.command(["start"]))
async def send_start(client: Client, message: Message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)

    buttons = [
        [InlineKeyboardButton("❣️ Developer", url="https://t.me/kingvj01")],
        [
            InlineKeyboardButton("🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ", url="https://t.me/vj_bot_disscussion"),
            InlineKeyboardButton("🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ", url="https://t.me/vj_botz"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await client.send_message(
        chat_id=message.chat.id,
        text=(
            f"<b>👋 Hi {message.from_user.mention}, I am Save Restricted Content Bot. "
            f"I can send you restricted content by its post link.\n\n"
            f"For downloading restricted content /login first.\n\n"
            f"Know how to use bot by - /help</b>"
        ),
        reply_markup=reply_markup,
        reply_to_message_id=message.id,
    )


# help command
@Client.on_message(filters.command(["help"]))
async def send_help(client: Client, message: Message):
    help_text = f"{HELP_TXT}\n\n**🕐 Custom Sleep Settings:**\n" \
                f"Use `/setsleep` command to set custom delays between batch downloads.\n" \
                f"Example: `/setsleep 3 5 7 10` (bot will randomly pick from these values)\n\n" \
                f"Use `/getsleep` to see your current sleep settings."
    await client.send_message(chat_id=message.chat.id, text=help_text)


# Set custom sleep command
@Client.on_message(filters.command(["setsleep"]))
async def set_sleep(client: Client, message: Message):
    try:
        # Parse sleep values from command
        parts = message.text.split()[1:]
        if not parts:
            await message.reply(
                "**Usage:** `/setsleep 3 5 7 10`\n\n"
                "Provide space-separated sleep values in seconds.\n"
                "Bot will randomly pick one value for each download to avoid detection.\n\n"
                "**Allowed range:** 1-1000 seconds\n"
                "**Example:** `/setsleep 3 5 7 10 12 15`"
            )
            return
        
        sleep_values = [int(x) for x in parts if x.isdigit() and 1 <= int(x) <= 1000]
        
        if not sleep_values:
            await message.reply("❌ Please provide valid sleep values between 1-1000 seconds!")
            return
        
        batch_temp.CUSTOM_SLEEP[message.from_user.id] = sleep_values
        await message.reply(
            f"✅ **Sleep values set successfully!**\n\n"
            f"Values: `{', '.join(map(str, sleep_values))}` seconds\n"
            f"Bot will randomly pick one value between downloads.\n\n"
            f"💡 **Tip:** More varied values = better anti-detection!"
        )
    except ValueError:
        await message.reply("❌ Please provide valid numeric values only!")


# Get current sleep settings
@Client.on_message(filters.command(["getsleep"]))
async def get_sleep(client: Client, message: Message):
    sleep_values = batch_temp.CUSTOM_SLEEP.get(message.from_user.id, [3, 5, 7, 10])
    await message.reply(
        f"**⏱️ Current Sleep Settings:**\n\n"
        f"Values: `{', '.join(map(str, sleep_values))}` seconds\n"
        f"Random selection with ±20% jitter for natural behavior.\n\n"
        f"Use `/setsleep` to change these values."
    )


# cancel command
@Client.on_message(filters.command(["cancel"]))
async def send_cancel(client: Client, message: Message):
    batch_temp.IS_BATCH[message.from_user.id] = True
    await client.send_message(chat_id=message.chat.id, text="**Batch Successfully Cancelled.**")


@Client.on_message(filters.text & filters.private)
async def save(client: Client, message: Message):
    # joining chats
    if ("https://t.me/+" in message.text or "https://t.me/joinchat/" in message.text) and LOGIN_SYSTEM is False:
        if TechVJUser is None:
            await client.send_message(
                message.chat.id,
                "**String Session is not Set**",
                reply_to_message_id=message.id,
            )
            return

        try:
            try:
                await TechVJUser.join_chat(message.text)
            except Exception as e:
                await client.send_message(
                    message.chat.id,
                    f"**Error** : __{e}__",
                    reply_to_message_id=message.id,
                )
                return

            await client.send_message(
                message.chat.id,
                "**Chat Joined**",
                reply_to_message_id=message.id,
            )

        except UserAlreadyParticipant:
            await client.send_message(
                message.chat.id,
                "**Chat already Joined**",
                reply_to_message_id=message.id,
            )

        except InviteHashExpired:
            await client.send_message(
                message.chat.id,
                "**Invalid Link**",
                reply_to_message_id=message.id,
            )

        return

    if "https://t.me/" in message.text:
        if batch_temp.IS_BATCH.get(message.from_user.id) is False:
            return await message.reply_text(
                "**One Task Is Already Processing. Wait For Complete It. "
                "If You Want To Cancel This Task Then Use - /cancel**"
            )

        datas = message.text.split("/")
        temp = datas[-1].replace("?single", "").split("-")
        fromID = int(temp[0].strip())

        try:
            toID = int(temp[1].strip())
        except:
            toID = fromID

        batch_temp.IS_BATCH[message.from_user.id] = False
        
        # Calculate total items for progress info
        total_items = toID - fromID + 1
        completed = 0

        for msgid in range(fromID, toID + 1):
            if batch_temp.IS_BATCH.get(message.from_user.id):
                break

            if LOGIN_SYSTEM:
                user_data = await db.get_session(message.from_user.id)
                if user_data is None:
                    await message.reply("**For Downloading Restricted Content You Have To /login First.**")
                    batch_temp.IS_BATCH[message.from_user.id] = True
                    return

                try:
                    acc = Client(
                        "saverestricted",
                        session_string=user_data,
                        api_hash=API_HASH,
                        api_id=API_ID,
                    )
                    await acc.start()
                except:
                    batch_temp.IS_BATCH[message.from_user.id] = True
                    return await message.reply(
                        "**Your Login Session Expired. So /logout First Then Login Again By - /login**"
                    )

            else:
                if TechVJUser is None:
                    batch_temp.IS_BATCH[message.from_user.id] = True
                    await client.send_message(
                        message.chat.id,
                        "**String Session is not Set**",
                        reply_to_message_id=message.id,
                    )
                    return

                acc = TechVJUser

            # private
            if "https://t.me/c/" in message.text:
                chatid = int("-100" + datas[4])
                try:
                    # Wait for download and upload to complete before continuing
                    await handle_private(client, acc, message, chatid, msgid)
                    completed += 1
                except Exception as e:
                    if ERROR_MESSAGE:
                        await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

            # bot
            elif "https://t.me/b/" in message.text:
                username = datas[4]
                try:
                    # Wait for download and upload to complete before continuing
                    await handle_private(client, acc, message, username, msgid)
                    completed += 1
                except Exception as e:
                    if ERROR_MESSAGE:
                        await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

            # public
            else:
                username = datas[3]
                try:
                    msg = await client.get_messages(username, msgid)
                except UsernameNotOccupied:
                    await client.send_message(
                        message.chat.id,
                        "The username is not occupied by anyone",
                        reply_to_message_id=message.id,
                    )
                    return

                try:
                    await client.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                    completed += 1
                except:
                    try:
                        # Wait for download and upload to complete before continuing
                        await handle_private(client, acc, message, username, msgid)
                        completed += 1
                    except Exception as e:
                        if ERROR_MESSAGE:
                            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

            # Apply smart sleep AFTER download and upload is complete and BEFORE starting next download
            if msgid < toID:  # Don't sleep after last item
                await smart_sleep(message.from_user.id)
                
            # Optional: Show progress every 5 items
            if completed % 5 == 0 and completed < total_items:
                try:
                    await client.send_message(
                        message.chat.id,
                        f"📊 Progress: {completed}/{total_items} completed...",
                        reply_to_message_id=message.id
                    )
                except:
                    pass

        batch_temp.IS_BATCH[message.from_user.id] = True
        
        # Send completion message
        if completed > 0:
            await client.send_message(
                message.chat.id,
                f"✅ **Batch Complete!**\n\nProcessed: {completed}/{total_items} items",
                reply_to_message_id=message.id
            )


# handle private - completely download and upload before returning
async def handle_private(client: Client, acc, message: Message, chatid: int, msgid: int):
    msg: Message = await acc.get_messages(chatid, msgid)
    if msg.empty:
        return

    msg_type = get_message_type(msg)
    if not msg_type:
        return

    chat = message.chat.id
    if batch_temp.IS_BATCH.get(message.from_user.id):
        return

    if msg_type == "Text":
        try:
            await client.send_message(
                chat,
                msg.text,
                entities=msg.entities,
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
            )
            return
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(
                    message.chat.id,
                    f"Error: {e}",
                    reply_to_message_id=message.id,
                    parse_mode=enums.ParseMode.HTML,
                )
            return

    smsg = await client.send_message(message.chat.id, "**Downloading**", reply_to_message_id=message.id)
    
    # Start download status task
    down_task = asyncio.create_task(downstatus(client, f"{message.id}downstatus.txt", smsg, chat))

    try:
        # Download the file (await completes when download is done)
        file = await acc.download_media(msg, progress=progress, progress_args=[message, "down"])
        
        # Remove download status file
        if os.path.exists(f"{message.id}downstatus.txt"):
            os.remove(f"{message.id}downstatus.txt")
        
        # Cancel download status task
        down_task.cancel()
        
    except Exception as e:
        if os.path.exists(f"{message.id}downstatus.txt"):
            os.remove(f"{message.id}downstatus.txt")
        down_task.cancel()
        if ERROR_MESSAGE:
            await client.send_message(
                message.chat.id,
                f"Error: {e}",
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
            )
        await smsg.delete()
        return

    if batch_temp.IS_BATCH.get(message.from_user.id):
        if os.path.exists(file):
            os.remove(file)
        return

    # Update message to uploading
    try:
        await smsg.edit("**Uploading**")
    except:
        pass
    
    # Start upload status task
    up_task = asyncio.create_task(upstatus(client, f"{message.id}upstatus.txt", smsg, chat))
    
    caption = msg.caption if msg.caption else None
    upload_success = False

    if msg_type == "Document":
        try:
            ph_path = await acc.download_media(msg.document.thumbs[0].file_id)
        except:
            ph_path = None
        try:
            # Upload the file (await completes when upload is done)
            await client.send_document(
                chat,
                file,
                thumb=ph_path,
                caption=caption,
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            upload_success = True
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(
                    message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML
                )
        if ph_path and os.path.exists(ph_path):
            os.remove(ph_path)

    elif msg_type == "Video":
        try:
            ph_path = await acc.download_media(msg.video.thumbs[0].file_id)
        except:
            ph_path = None
        try:
            # Upload the file (await completes when upload is done)
            await client.send_video(
                chat,
                file,
                duration=msg.video.duration,
                width=msg.video.width,
                height=msg.video.height,
                thumb=ph_path,
                caption=caption,
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            upload_success = True
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(
                    message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML
                )
        if ph_path and os.path.exists(ph_path):
            os.remove(ph_path)

    elif msg_type == "Animation":
        try:
            await client.send_animation(chat, file, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
            upload_success = True
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(
                    message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML
                )

    elif msg_type == "Sticker":
        try:
            await client.send_sticker(chat, file, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
            upload_success = True
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(
                    message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML
                )

    elif msg_type == "Voice":
        try:
            await client.send_voice(
                chat,
                file,
                caption=caption,
                caption_entities=msg.caption_entities,
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            upload_success = True
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(
                    message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML
                )

    elif msg_type == "Audio":
        try:
            ph_path = await acc.download_media(msg.audio.thumbs[0].file_id)
        except:
            ph_path = None
        try:
            await client.send_audio(
                chat,
                file,
                thumb=ph_path,
                caption=caption,
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            upload_success = True
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(
                    message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML
                )
        if ph_path and os.path.exists(ph_path):
            os.remove(ph_path)

    elif msg_type == "Photo":
        try:
            await client.send_photo(
                chat, file, caption=caption, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML
            )
            upload_success = True
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(
                    message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML
                )

    # Clean up upload status file
    if os.path.exists(f"{message.id}upstatus.txt"):
        os.remove(f"{message.id}upstatus.txt")
    
    # Cancel upload status task
    up_task.cancel()
    
    # Clean up downloaded file
    if os.path.exists(file):
        os.remove(file)
    
    # Delete status message
    try:
        await client.delete_messages(message.chat.id, [smsg.id])
    except:
        pass
    
    # This function now returns only after download AND upload are complete


# get the type of message
def get_message_type(msg: pyrogram.types.messages_and_media.message.Message):
    try:
        msg.document.file_id
        return "Document"
    except:
        pass
    try:
        msg.video.file_id
        return "Video"
    except:
        pass
    try:
        msg.animation.file_id
        return "Animation"
    except:
        pass
    try:
        msg.sticker.file_id
        return "Sticker"
    except:
        pass
    try:
        msg.voice.file_id
        return "Voice"
    except:
        pass
    try:
        msg.audio.file_id
        return "Audio"
    except:
        pass
    try:
        msg.photo.file_id
        return "Photo"
    except:
        pass
    try:
        msg.text
        return "Text"
    except:
        pass
