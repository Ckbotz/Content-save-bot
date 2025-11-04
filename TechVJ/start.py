# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import asyncio
import random
import pyrogram
import re
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

# ========== CONFIGURATION SECTION ==========
# Add words to remove from filename (case-insensitive)
WORDS_TO_REMOVE = [
    "@ADL_DRAMA",
    "#ADL",
    "@DA_Rips",
    "[MABLG]",
    # Add more words here
]

# Permanent thumbnail URL (leave empty string "" to disable)
PERMANENT_THUMBNAIL_URL = "https://envs.sh/lga.jpg"

# ========== AUTO MONITOR CONFIGURATION ==========
# Add channel IDs to monitor (can be username or chat_id)
MONITOR_CHANNELS = ["-1002338078447", "-1001989242533",
    # "-100123456789",  # Example: Private channel
    # "example_channel",  # Example: Public channel
]

# Log channel where bot forwards files after sending to user
LOG_CHANNEL_ID = "-1002945932713"  # Set your log channel ID here (e.g., "-100123456789")

# Random check interval range in seconds (1 hour to 24 hours)
MIN_CHECK_INTERVAL = 0  # 1 hour in seconds
MAX_CHECK_INTERVAL = 86400  # 24 hours in seconds

# Delay before forwarding to log channel (in seconds)
LOG_FORWARD_DELAY = 5  # Wait 5 seconds after sending to user before logging
# =========================================


class batch_temp(object):
    IS_BATCH = {}
    CUSTOM_SLEEP = {}  # Store custom sleep values per user
    CANCEL_TASKS = {}  # Store cancellation flags for immediate stop
    MONITOR_ACTIVE = {}  # Track active monitoring tasks
    LAST_MESSAGE_IDS = {}  # Track last processed message ID per channel
    CHECK_INTERVAL_RANGE = {}  # Store custom check intervals per user


def clean_filename(filename):
    """Remove unwanted words from filename"""
    if not filename:
        return filename
    
    # Split filename and extension
    name_parts = filename.rsplit('.', 1)
    name = name_parts[0]
    ext = name_parts[1] if len(name_parts) > 1 else ""
    
    # Remove each word (case-insensitive)
    for word in WORDS_TO_REMOVE:
        name = re.sub(re.escape(word), '', name, flags=re.IGNORECASE)
    
    # Clean up extra spaces and special characters
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'[_\-\s]+', ' ', name).strip()
    
    # Reconstruct filename
    return f"{name}.{ext}" if ext else name


async def download_thumbnail(client, url):
    """Download thumbnail from URL"""
    if not url:
        return None
    
    try:
        # Create temp directory if doesn't exist
        os.makedirs("temp_thumbs", exist_ok=True)
        
        # Generate unique filename
        thumb_path = f"temp_thumbs/thumb_{random.randint(1000, 9999)}.jpg"
        
        # Download using web_fetch or similar method
        import requests
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(thumb_path, 'wb') as f:
                f.write(response.content)
            return thumb_path
    except Exception as e:
        print(f"Error downloading thumbnail: {e}")
    
    return None


# Anti-detection sleep function with randomization
async def smart_sleep(user_id):
    """Intelligent sleep with randomization to avoid detection"""
    base_sleep = batch_temp.CUSTOM_SLEEP.get(user_id, [3, 5, 7, 10])
    
    # Pick a random sleep value from the list
    sleep_time = random.choice(base_sleep)
    
    # Add random jitter (±20%) for more natural behavior
    jitter = random.uniform(-0.2, 0.2) * sleep_time
    final_sleep = sleep_time + jitter
    
    # Sleep in small chunks to allow quick cancellation
    sleep_chunks = int(final_sleep / 0.5)  # 0.5 second chunks
    for _ in range(sleep_chunks):
        if batch_temp.CANCEL_TASKS.get(user_id, False):
            break
        await asyncio.sleep(0.5)


# download status with cancellation check
async def downstatus(client, statusfile, message, chat, user_id):
    while True:
        if batch_temp.CANCEL_TASKS.get(user_id, False):
            return
        if os.path.exists(statusfile):
            break
        await asyncio.sleep(3)

    while os.path.exists(statusfile):
        if batch_temp.CANCEL_TASKS.get(user_id, False):
            return
        with open(statusfile, "r") as downread:
            txt = downread.read()
        try:
            await client.edit_message_text(chat, message.id, f"**Downloaded:** **{txt}**")
            await asyncio.sleep(10)
        except:
            await asyncio.sleep(5)


# upload status with cancellation check
async def upstatus(client, statusfile, message, chat, user_id):
    while True:
        if batch_temp.CANCEL_TASKS.get(user_id, False):
            return
        if os.path.exists(statusfile):
            break
        await asyncio.sleep(3)

    while os.path.exists(statusfile):
        if batch_temp.CANCEL_TASKS.get(user_id, False):
            return
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


# Forward to log channel with delay
async def forward_to_log(client, message, user_id):
    """Forward sent message to log channel after delay"""
    if not LOG_CHANNEL_ID:
        return
    
    try:
        await asyncio.sleep(LOG_FORWARD_DELAY)
        await client.copy_message(
            chat_id=LOG_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.id,
            caption=f"📤 Sent to User: {user_id}\n\n{message.caption if message.caption else ''}"
        )
    except Exception as e:
        print(f"Error forwarding to log channel: {e}")


# Auto monitor channels for new documents
async def auto_monitor_channels(client: Client, user_id: int):
    """Monitor channels for new document messages and auto-download/upload"""
    
    if not MONITOR_CHANNELS:
        return
    
    # Get user session
    if LOGIN_SYSTEM:
        user_data = await db.get_session(user_id)
        if user_data is None:
            return
        
        try:
            acc = Client(
                "monitor_session",
                session_string=user_data,
                api_hash=API_HASH,
                api_id=API_ID,
            )
            await acc.start()
        except:
            return
    else:
        if TechVJUser is None:
            return
        acc = TechVJUser
    
    batch_temp.MONITOR_ACTIVE[user_id] = True
    
    # Initialize last message IDs for each channel
    if user_id not in batch_temp.LAST_MESSAGE_IDS:
        batch_temp.LAST_MESSAGE_IDS[user_id] = {}
        
        # Get current latest message ID for each channel
        for channel_id in MONITOR_CHANNELS:
            try:
                msgs = await acc.get_history(channel_id, limit=1)
                if msgs:
                    batch_temp.LAST_MESSAGE_IDS[user_id][channel_id] = msgs[0].id
            except Exception as e:
                print(f"Error getting history for {channel_id}: {e}")
                batch_temp.LAST_MESSAGE_IDS[user_id][channel_id] = 0
    
    await client.send_message(
        user_id,
        f"🤖 **Auto Monitor Started!**\n\n"
        f"📡 Monitoring {len(MONITOR_CHANNELS)} channel(s)\n"
        f"⏰ Check interval: Random between {MIN_CHECK_INTERVAL//3600}h - {MAX_CHECK_INTERVAL//3600}h\n"
        f"📄 Only downloading: Documents\n\n"
        f"Use /stopmonitor to stop monitoring."
    )
    
    while batch_temp.MONITOR_ACTIVE.get(user_id, False):
        try:
            # Check each channel for new documents
            for channel_id in MONITOR_CHANNELS:
                if not batch_temp.MONITOR_ACTIVE.get(user_id, False):
                    break
                
                last_msg_id = batch_temp.LAST_MESSAGE_IDS[user_id].get(channel_id, 0)
                
                try:
                    # Get messages after last processed ID
                    async for msg in acc.get_chat_history(channel_id, offset_id=last_msg_id, limit=50):
                        if not batch_temp.MONITOR_ACTIVE.get(user_id, False):
                            break
                        
                        # Only process documents
                        if msg.document:
                            # Update last message ID
                            batch_temp.LAST_MESSAGE_IDS[user_id][channel_id] = max(
                                batch_temp.LAST_MESSAGE_IDS[user_id][channel_id],
                                msg.id
                            )
                            
                            # Process the document
                            await client.send_message(
                                user_id,
                                f"📥 **New Document Found!**\n"
                                f"Channel: `{channel_id}`\n"
                                f"Processing..."
                            )
                            
                            # Create a dummy message object for handle_private
                            class DummyMessage:
                                def __init__(self, chat_id):
                                    self.chat = type('obj', (object,), {'id': chat_id})
                                    self.id = 0
                            
                            dummy_msg = DummyMessage(user_id)
                            
                            # Download and upload
                            success = await handle_private(client, acc, dummy_msg, channel_id, msg.id, is_auto=True)
                            
                            if success:
                                await client.send_message(
                                    user_id,
                                    f"✅ **Document uploaded successfully!**"
                                )
                            
                            # Apply smart sleep between documents
                            await smart_sleep(user_id)
                
                except Exception as e:
                    print(f"Error checking channel {channel_id}: {e}")
                    continue
            
            # Random sleep before next check
            min_interval = batch_temp.CHECK_INTERVAL_RANGE.get(user_id, [MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL])[0]
            max_interval = batch_temp.CHECK_INTERVAL_RANGE.get(user_id, [MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL])[1]
            sleep_time = random.randint(min_interval, max_interval)
            
            await client.send_message(
                user_id,
                f"⏳ **Next check in {sleep_time//3600}h {(sleep_time%3600)//60}m**"
            )
            
            # Sleep in chunks to allow quick cancellation
            for _ in range(sleep_time):
                if not batch_temp.MONITOR_ACTIVE.get(user_id, False):
                    break
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"Error in monitor loop: {e}")
            await asyncio.sleep(60)
    
    await client.send_message(user_id, "🛑 **Auto monitoring stopped.**")


# Start monitoring command
@Client.on_message(filters.command(["startmonitor"]))
async def start_monitor(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not MONITOR_CHANNELS:
        await message.reply("❌ **No channels configured for monitoring!**\n\nAdmin needs to add channels in MONITOR_CHANNELS.")
        return
    
    if batch_temp.MONITOR_ACTIVE.get(user_id, False):
        await message.reply("⚠️ **Monitoring is already active!**\n\nUse /stopmonitor to stop it first.")
        return
    
    # Start monitoring in background
    asyncio.create_task(auto_monitor_channels(client, user_id))


# Stop monitoring command
@Client.on_message(filters.command(["stopmonitor"]))
async def stop_monitor(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not batch_temp.MONITOR_ACTIVE.get(user_id, False):
        await message.reply("❌ **No active monitoring to stop!**")
        return
    
    batch_temp.MONITOR_ACTIVE[user_id] = False
    await message.reply("🛑 **Stopping auto monitor...**")


# Set check interval command
@Client.on_message(filters.command(["setcheckinterval"]))
async def set_check_interval(client: Client, message: Message):
    try:
        parts = message.text.split()[1:]
        if len(parts) != 2:
            await message.reply(
                "**Usage:** `/setcheckinterval <min_hours> <max_hours>`\n\n"
                "Example: `/setcheckinterval 1 12`\n"
                "This will check channels randomly between 1-12 hours.\n\n"
                "**Allowed range:** 1-24 hours"
            )
            return
        
        min_hours = int(parts[0])
        max_hours = int(parts[1])
        
        if not (1 <= min_hours <= 24 and 1 <= max_hours <= 24 and min_hours < max_hours):
            await message.reply("❌ Invalid range! Min should be less than max, both between 1-24 hours.")
            return
        
        batch_temp.CHECK_INTERVAL_RANGE[message.from_user.id] = [min_hours * 3600, max_hours * 3600]
        await message.reply(
            f"✅ **Check interval set!**\n\n"
            f"Min: {min_hours}h, Max: {max_hours}h\n"
            f"Bot will randomly check between this range."
        )
    except ValueError:
        await message.reply("❌ Please provide valid numeric values!")


# Get check interval command
@Client.on_message(filters.command(["getcheckinterval"]))
async def get_check_interval(client: Client, message: Message):
    intervals = batch_temp.CHECK_INTERVAL_RANGE.get(
        message.from_user.id, 
        [MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL]
    )
    min_hours = intervals[0] // 3600
    max_hours = intervals[1] // 3600
    
    await message.reply(
        f"**⏰ Current Check Interval:**\n\n"
        f"Min: {min_hours} hours\n"
        f"Max: {max_hours} hours\n\n"
        f"Use `/setcheckinterval` to change."
    )


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
                f"Use `/getsleep` to see your current sleep settings.\n\n" \
                f"**⏰ Auto Monitor Settings:**\n" \
                f"Use `/setcheckinterval` to set check interval range (in hours)\n" \
                f"Example: `/setcheckinterval 2 8` (check every 2-8 hours randomly)\n" \
                f"Use `/getcheckinterval` to see current settings\n\n" \
                f"**🤖 Auto Monitor Commands:**\n" \
                f"`/startmonitor` - Start automatic channel monitoring\n" \
                f"`/stopmonitor` - Stop automatic channel monitoring\n\n" \
                f"**🛑 Cancel Command:**\n" \
                f"Use `/cancel` to immediately stop any ongoing batch process including current download/upload."
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


# cancel command - IMMEDIATE STOP
@Client.on_message(filters.command(["cancel"]))
async def send_cancel(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if there's an active batch
    if user_id not in batch_temp.IS_BATCH or batch_temp.IS_BATCH.get(user_id, True) is True:
        await client.send_message(
            chat_id=message.chat.id, 
            text="**❌ No Active Batch Process To Cancel.**",
            reply_to_message_id=message.id
        )
        return
    
    # Set immediate cancellation flags
    batch_temp.CANCEL_TASKS[user_id] = True
    batch_temp.IS_BATCH[user_id] = True
    
    await client.send_message(
        chat_id=message.chat.id, 
        text="**🛑 CANCELLING ALL PROCESSES IMMEDIATELY!**\n\n"
             "⚠️ Stopping current download/upload...\n"
             "⚠️ Cleaning up temporary files...\n"
             "⚠️ Process will stop within seconds.",
        reply_to_message_id=message.id
    )


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
        user_id = message.from_user.id
        
        if batch_temp.IS_BATCH.get(user_id) is False:
            return await message.reply_text(
                "**⚠️ One Task Is Already Processing!**\n\n"
                "Please wait for it to complete or use /cancel to stop it."
            )

        datas = message.text.split("/")
        temp = datas[-1].replace("?single", "").split("-")
        fromID = int(temp[0].strip())

        try:
            toID = int(temp[1].strip())
        except:
            toID = fromID

        # Initialize cancellation flag
        batch_temp.CANCEL_TASKS[user_id] = False
        batch_temp.IS_BATCH[user_id] = False
        
        # Calculate total items for progress info
        total_items = toID - fromID + 1
        completed = 0

        for msgid in range(fromID, toID + 1):
            # IMMEDIATE CANCELLATION CHECK
            if batch_temp.CANCEL_TASKS.get(user_id, False) or batch_temp.IS_BATCH.get(user_id, True):
                await client.send_message(
                    message.chat.id,
                    f"**🛑 Batch Process Cancelled!**\n\n"
                    f"✅ Completed: {completed}/{total_items} items\n"
                    f"❌ Cancelled at: {msgid}/{toID}",
                    reply_to_message_id=message.id
                )
                batch_temp.CANCEL_TASKS[user_id] = False
                batch_temp.IS_BATCH[user_id] = True
                return

            if LOGIN_SYSTEM:
                user_data = await db.get_session(user_id)
                if user_data is None:
                    await message.reply("**For Downloading Restricted Content You Have To /login First.**")
                    batch_temp.IS_BATCH[user_id] = True
                    batch_temp.CANCEL_TASKS[user_id] = False
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
                    batch_temp.IS_BATCH[user_id] = True
                    batch_temp.CANCEL_TASKS[user_id] = False
                    return await message.reply(
                        "**Your Login Session Expired. So /logout First Then Login Again By - /login**"
                    )

            else:
                if TechVJUser is None:
                    batch_temp.IS_BATCH[user_id] = True
                    batch_temp.CANCEL_TASKS[user_id] = False
                    await client.send_message(
                        message.chat.id,
                        "**String Session is not Set**",
                        reply_to_message_id=message.id,
                    )
                    return

                acc = TechVJUser

            # CANCELLATION CHECK BEFORE PROCESSING
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                await client.send_message(
                    message.chat.id,
                    f"**🛑 Batch Process Cancelled!**\n\n"
                    f"✅ Completed: {completed}/{total_items} items",
                    reply_to_message_id=message.id
                )
                batch_temp.CANCEL_TASKS[user_id] = False
                batch_temp.IS_BATCH[user_id] = True
                return

            # private
            if "https://t.me/c/" in message.text:
                chatid = int("-100" + datas[4])
                try:
                    success = await handle_private(client, acc, message, chatid, msgid)
                    if success:
                        completed += 1
                except Exception as e:
                    if ERROR_MESSAGE:
                        await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

            # bot
            elif "https://t.me/b/" in message.text:
                username = datas[4]
                try:
                    success = await handle_private(client, acc, message, username, msgid)
                    if success:
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
                    batch_temp.IS_BATCH[user_id] = True
                    batch_temp.CANCEL_TASKS[user_id] = False
                    return

                try:
                    await client.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                    completed += 1
                except:
                    try:
                        success = await handle_private(client, acc, message, username, msgid)
                        if success:
                            completed += 1
                    except Exception as e:
                        if ERROR_MESSAGE:
                            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

            # CANCELLATION CHECK AFTER PROCESSING
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                await client.send_message(
                    message.chat.id,
                    f"**🛑 Batch Process Cancelled!**\n\n"
                    f"✅ Completed: {completed}/{total_items} items",
                    reply_to_message_id=message.id
                )
                batch_temp.CANCEL_TASKS[user_id] = False
                batch_temp.IS_BATCH[user_id] = True
                return

            # Apply smart sleep BEFORE starting next download
            if msgid < toID:
                await smart_sleep(user_id)
                
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

        # Cleanup flags
        batch_temp.IS_BATCH[user_id] = True
        batch_temp.CANCEL_TASKS[user_id] = False
        
        # Send completion message
        if completed > 0:
            await client.send_message(
                message.chat.id,
                f"✅ **Batch Complete!**\n\nProcessed: {completed}/{total_items} items",
                reply_to_message_id=message.id
            )


# handle private with immediate cancellation support - returns True if successful
async def handle_private(client: Client, acc, message: Message, chatid: int, msgid: int, is_auto=False):
    user_id = message.from_user.id if not is_auto else message.chat.id
    
    # IMMEDIATE CANCELLATION CHECK
    if batch_temp.CANCEL_TASKS.get(user_id, False):
        return False
    
    msg: Message = await acc.get_messages(chatid, msgid)
    if msg.empty:
        return False

    msg_type = get_message_type(msg)
    if not msg_type:
        return False

    chat = message.chat.id
    
    # CHECK CANCELLATION
    if batch_temp.CANCEL_TASKS.get(user_id, False):
        return False

    if msg_type == "Text":
        # Skip text messages in auto mode
        if is_auto:
            return False
        
        try:
            await client.send_message(
                chat,
                msg.text,
                entities=msg.entities,
                reply_to_message_id=message.id if not is_auto else None,
                parse_mode=enums.ParseMode.HTML,
            )
            return True
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(
                    message.chat.id,
                    f"Error: {e}",
                    reply_to_message_id=message.id if not is_auto else None,
                    parse_mode=enums.ParseMode.HTML,
                )
            return False

    # Only process documents in auto mode
    if is_auto and msg_type != "Document":
        return False

    smsg = await client.send_message(message.chat.id, "**Downloading**", reply_to_message_id=message.id if not is_auto else None)
    
    # Start download status task
    down_task = asyncio.create_task(downstatus(client, f"{message.id}downstatus.txt", smsg, chat, user_id))

    file = None
    try:
        # CHECK CANCELLATION BEFORE DOWNLOAD
        if batch_temp.CANCEL_TASKS.get(user_id, False):
            down_task.cancel()
            if os.path.exists(f"{message.id}downstatus.txt"):
                os.remove(f"{message.id}downstatus.txt")
            try:
                await smsg.delete()
            except:
                pass
            return False
        
        # Download the file
        file = await acc.download_media(msg, progress=progress, progress_args=[message, "down"])
        
        # CHECK CANCELLATION AFTER DOWNLOAD
        if batch_temp.CANCEL_TASKS.get(user_id, False):
            down_task.cancel()
            if os.path.exists(f"{message.id}downstatus.txt"):
                os.remove(f"{message.id}downstatus.txt")
            if file and os.path.exists(file):
                os.remove(file)
            try:
                await smsg.delete()
            except:
                pass
            return False
        
        # Clean filename
        if file and os.path.exists(file):
            dir_name = os.path.dirname(file)
            old_filename = os.path.basename(file)
            new_filename = clean_filename(old_filename)
            new_file_path = os.path.join(dir_name, new_filename)
            
            if old_filename != new_filename:
                os.rename(file, new_file_path)
                file = new_file_path
        
        # Remove download status file
        if os.path.exists(f"{message.id}downstatus.txt"):
            os.remove(f"{message.id}downstatus.txt")
        
        # Cancel download status task
        down_task.cancel()
        
    except Exception as e:
        if os.path.exists(f"{message.id}downstatus.txt"):
            os.remove(f"{message.id}downstatus.txt")
        down_task.cancel()
        if file and os.path.exists(file):
            os.remove(file)
        if ERROR_MESSAGE:
            await client.send_message(
                message.chat.id,
                f"Error: {e}",
                reply_to_message_id=message.id if not is_auto else None,
                parse_mode=enums.ParseMode.HTML,
            )
        try:
            await smsg.delete()
        except:
            pass
        return False

    # FINAL CANCELLATION CHECK BEFORE UPLOAD
    if batch_temp.CANCEL_TASKS.get(user_id, False):
        if file and os.path.exists(file):
            os.remove(file)
        try:
            await smsg.delete()
        except:
            pass
        return False

    # Update message to uploading
    try:
        await smsg.edit("**Uploading**")
    except:
        pass
    
    # Start upload status task
    up_task = asyncio.create_task(upstatus(client, f"{message.id}upstatus.txt", smsg, chat, user_id))

# ========== CAPTION CUSTOMIZATION ==========
# Get original caption
original_caption = msg.caption if msg.caption else ""

# Modify caption here - Choose one of the options below:

# Option 1: Keep original caption
# caption = f"<b>📄 {filename}\n\n@DramaShip\n@CompletedDramas\n@DramasCompleted</b>"

# Option 2: Add custom text to original caption
# caption = f"{original_caption}\n\n📥 Downloaded by @YourBotUsername" if original_caption else "📥 Downloaded by @YourBotUsername"

# Option 3: Replace with completely custom caption
# caption = "📁 Your Custom Caption Here"

# Option 4: Add filename to caption
# filename = os.path.basename(file) if file else "Unknown"
# caption = f"<b>📄 {filename}\n\n@DramaShip\n@CompletedDramas\n@DramasCompleted</b>" if original_caption else f"<b>📄 {filename}\n\n@DramaShip\n@CompletedDramas\n@DramasCompleted</b>"

# Option 5: Remove caption completely
caption = None
# ===========================================

upload_success = False
sent_message = None
    
    # Download permanent thumbnail if set
    perm_thumb = None
    if PERMANENT_THUMBNAIL_URL:
        perm_thumb = await download_thumbnail(client, PERMANENT_THUMBNAIL_URL)

    try:
        if msg_type == "Document":
            # CHECK CANCELLATION
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise Exception("Cancelled by user")
            
            # Use permanent thumbnail or original
            if perm_thumb:
                ph_path = perm_thumb
            else:
                try:
                    ph_path = await acc.download_media(msg.document.thumbs[0].file_id)
                except:
                    ph_path = None
            
            sent_message = await client.send_document(
                chat,
                file,
                thumb=ph_path,
                caption=caption,
                reply_to_message_id=message.id if not is_auto else None,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            upload_success = True
            
            if ph_path and os.path.exists(ph_path):
                os.remove(ph_path)

        elif msg_type == "Video":
            # CHECK CANCELLATION
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise Exception("Cancelled by user")
            
            # Use permanent thumbnail or original
            if perm_thumb:
                ph_path = perm_thumb
            else:
                try:
                    ph_path = await acc.download_media(msg.video.thumbs[0].file_id)
                except:
                    ph_path = None
            
            sent_message = await client.send_video(
                chat,
                file,
                duration=msg.video.duration,
                width=msg.video.width,
                height=msg.video.height,
                thumb=ph_path,
                caption=caption,
                reply_to_message_id=message.id if not is_auto else None,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            upload_success = True
            
            if ph_path and os.path.exists(ph_path):
                os.remove(ph_path)

        elif msg_type == "Animation":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise Exception("Cancelled by user")
            
            sent_message = await client.send_animation(chat, file, reply_to_message_id=message.id if not is_auto else None, parse_mode=enums.ParseMode.HTML)
            upload_success = True

        elif msg_type == "Sticker":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise Exception("Cancelled by user")
            
            sent_message = await client.send_sticker(chat, file, reply_to_message_id=message.id if not is_auto else None, parse_mode=enums.ParseMode.HTML)
            upload_success = True

        elif msg_type == "Voice":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise Exception("Cancelled by user")
            
            sent_message = await client.send_voice(
                chat,
                file,
                caption=caption,
                caption_entities=msg.caption_entities,
                reply_to_message_id=message.id if not is_auto else None,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            upload_success = True

        elif msg_type == "Audio":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise Exception("Cancelled by user")
            
            # Use permanent thumbnail or original
            if perm_thumb:
                ph_path = perm_thumb
            else:
                try:
                    ph_path = await acc.download_media(msg.audio.thumbs[0].file_id)
                except:
                    ph_path = None
            
            sent_message = await client.send_audio(
                chat,
                file,
                thumb=ph_path,
                caption=caption,
                reply_to_message_id=message.id if not is_auto else None,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            upload_success = True
            
            if ph_path and os.path.exists(ph_path):
                os.remove(ph_path)

        elif msg_type == "Photo":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise Exception("Cancelled by user")
            
            sent_message = await client.send_photo(
                chat, file, caption=caption, reply_to_message_id=message.id if not is_auto else None, parse_mode=enums.ParseMode.HTML
            )
            upload_success = True

    except Exception as e:
        if "Cancelled by user" not in str(e) and ERROR_MESSAGE:
            await client.send_message(
                message.chat.id, f"Error: {e}", reply_to_message_id=message.id if not is_auto else None, parse_mode=enums.ParseMode.HTML
            )

    # Clean up upload status file
    if os.path.exists(f"{message.id}upstatus.txt"):
        os.remove(f"{message.id}upstatus.txt")
    
    # Cancel upload status task
    up_task.cancel()
    
    # Clean up downloaded file
    if file and os.path.exists(file):
        os.remove(file)
    
    # Delete status message
    try:
        await client.delete_messages(message.chat.id, [smsg.id])
    except:
        pass
    
    # Forward to log channel if successful
    if upload_success and sent_message and LOG_CHANNEL_ID:
        asyncio.create_task(forward_to_log(client, sent_message, user_id))

    return upload_success


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
