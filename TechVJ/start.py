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
    "[MABLG]",
    "@DA_RIPS",
    "@Da_Rips",
    # Add more words here
]

# Permanent thumbnail URL (leave empty string "" to disable)
PERMANENT_THUMBNAIL_URL = "https://envs.sh/lga.jpg"

# ========== AUTO CHANNEL MONITOR CONFIG ==========
# Add channel IDs to monitor (negative IDs for channels/groups)
MONITOR_CHANNELS = [
    -1002338078447,  # Replace with actual channel ID
    -1001989242533,  # Add more channel IDs here
]

# Enable/Disable auto monitoring (set to True to enable)
AUTO_MONITOR_ENABLED = True
# =========================================


class batch_temp(object):
    IS_BATCH = {}
    CUSTOM_SLEEP = {}  # Store custom sleep values per user
    CANCEL_TASKS = {}  # Store cancellation flags for immediate stop
    INTERVAL_SLEEP = {}  # Store interval sleep values for auto monitoring
    LAST_MESSAGE_IDS = {}  # Store last processed message ID per channel
    AUTO_MONITOR_TASKS = {}  # Store auto monitor tasks per user
    MAX_FILE_SIZE = {}  # Store maximum file size per user (in MB)


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


def format_file_size(size_bytes):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


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
        # Note: You might need to use requests library or another method
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


# Interval sleep for auto monitoring
async def interval_sleep(user_id):
    """Sleep between channel checks with random intervals"""
    base_sleep = batch_temp.INTERVAL_SLEEP.get(user_id, [300, 600, 900, 1200])  # Default 5-20 mins
    
    # Pick a random sleep value from the list
    sleep_time = random.choice(base_sleep)
    
    # Add random jitter (±10%) for more natural behavior
    jitter = random.uniform(-0.1, 0.1) * sleep_time
    final_sleep = sleep_time + jitter
    
    # Sleep in small chunks to allow quick cancellation
    sleep_chunks = int(final_sleep / 1)  # 1 second chunks
    for _ in range(sleep_chunks):
        if batch_temp.CANCEL_TASKS.get(user_id, False):
            break
        await asyncio.sleep(1)


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
                f"**📏 File Size Limit:**\n" \
                f"Use `/setmaxsize` to set maximum file size for auto downloads (in MB).\n" \
                f"Example: `/setmaxsize 500` (only download files up to 500 MB)\n" \
                f"Use `/getmaxsize` to see current size limit.\n\n" \
                f"**🤖 Auto Channel Monitor:**\n" \
                f"Use `/startmonitor` to start automatic channel monitoring.\n" \
                f"Use `/stopmonitor` to stop automatic monitoring.\n" \
                f"Use `/setintervalsleep` to set check intervals (in seconds).\n" \
                f"Example: `/setintervalsleep 300 490 520 918 684`\n" \
                f"Use `/getintervalsleep` to see current interval settings.\n" \
                f"Use `/monitorstatus` to see monitoring status.\n\n" \
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


# Set maximum file size command
@Client.on_message(filters.command(["setmaxsize"]))
async def set_max_size(client: Client, message: Message):
    try:
        parts = message.text.split()[1:]
        if not parts:
            await message.reply(
                "**Usage:** `/setmaxsize 500`\n\n"
                "Set maximum file size in MB (MegaBytes).\n"
                "Only documents within this size will be downloaded during auto monitoring.\n\n"
                "**Allowed range:** 1-4000 MB\n"
                "**Examples:**\n"
                "`/setmaxsize 100` - Download files up to 100 MB\n"
                "`/setmaxsize 500` - Download files up to 500 MB\n"
                "`/setmaxsize 2000` - Download files up to 2 GB\n\n"
                "**Note:** Set to 0 to disable size limit (download all files)"
            )
            return
        
        max_size = int(parts[0])
        
        if max_size < 0 or max_size > 4000:
            await message.reply("❌ Please provide a valid size between 0-4000 MB!")
            return
        
        batch_temp.MAX_FILE_SIZE[message.from_user.id] = max_size
        
        if max_size == 0:
            await message.reply(
                f"✅ **File size limit disabled!**\n\n"
                f"All documents will be downloaded regardless of size.\n\n"
                f"⚠️ **Warning:** Large files may take long time to download!"
            )
        else:
            await message.reply(
                f"✅ **Maximum file size set successfully!**\n\n"
                f"Max Size: `{max_size} MB` ({format_file_size(max_size * 1024 * 1024)})\n"
                f"Only documents up to this size will be downloaded.\n\n"
                f"💡 **Tip:** Lower size = faster downloads!"
            )
    except ValueError:
        await message.reply("❌ Please provide a valid numeric value!")


# Get current max size settings
@Client.on_message(filters.command(["getmaxsize"]))
async def get_max_size(client: Client, message: Message):
    max_size = batch_temp.MAX_FILE_SIZE.get(message.from_user.id, 2000)  # Default 2GB
    
    if max_size == 0:
        await message.reply(
            f"**📏 Current File Size Limit:**\n\n"
            f"Status: `Disabled` ♾️\n"
            f"All files will be downloaded regardless of size.\n\n"
            f"Use `/setmaxsize` to set a limit."
        )
    else:
        await message.reply(
            f"**📏 Current File Size Limit:**\n\n"
            f"Max Size: `{max_size} MB` ({format_file_size(max_size * 1024 * 1024)})\n"
            f"Only documents within this size will be downloaded.\n\n"
            f"Use `/setmaxsize` to change this value."
        )


# Set interval sleep command
@Client.on_message(filters.command(["setintervalsleep"]))
async def set_interval_sleep(client: Client, message: Message):
    try:
        parts = message.text.split()[1:]
        if not parts:
            await message.reply(
                "**Usage:** `/setintervalsleep 300 490 520 918 684`\n\n"
                "Provide space-separated interval values in seconds.\n"
                "Bot will randomly pick one value between channel checks.\n\n"
                "**Allowed range:** 1-86400 seconds (1 sec - 24 hours)\n"
                "**Example:** `/setintervalsleep 300 600 900 1200`"
            )
            return
        
        interval_values = [int(x) for x in parts if x.isdigit() and 1 <= int(x) <= 86400]
        
        if not interval_values:
            await message.reply("❌ Please provide valid interval values between 1-86400 seconds!")
            return
        
        batch_temp.INTERVAL_SLEEP[message.from_user.id] = interval_values
        await message.reply(
            f"✅ **Interval sleep values set successfully!**\n\n"
            f"Values: `{', '.join(map(str, interval_values))}` seconds\n"
            f"Bot will randomly pick one value between channel checks.\n\n"
            f"💡 **Tip:** Longer intervals = less detection risk!"
        )
    except ValueError:
        await message.reply("❌ Please provide valid numeric values only!")


# Get current interval sleep settings
@Client.on_message(filters.command(["getintervalsleep"]))
async def get_interval_sleep(client: Client, message: Message):
    interval_values = batch_temp.INTERVAL_SLEEP.get(message.from_user.id, [300, 600, 900, 1200])
    await message.reply(
        f"**⏱️ Current Interval Sleep Settings:**\n\n"
        f"Values: `{', '.join(map(str, interval_values))}` seconds\n"
        f"Random selection with ±10% jitter for natural behavior.\n\n"
        f"Use `/setintervalsleep` to change these values."
    )


# Check if file size is within limit
def is_file_within_limit(file_size_bytes, user_id):
    """Check if file size is within user's limit"""
    max_size_mb = batch_temp.MAX_FILE_SIZE.get(user_id, 2000)  # Default 2GB
    
    # If limit is 0, no restriction
    if max_size_mb == 0:
        return True
    
    # Convert bytes to MB
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    return file_size_mb <= max_size_mb


# Auto channel monitor function
async def auto_channel_monitor(client: Client, user_id: int):
    """Automatically monitor channels and download new documents"""
    
    if not AUTO_MONITOR_ENABLED:
        await client.send_message(
            user_id,
            "❌ **Auto monitoring is disabled in bot configuration.**"
        )
        return
    
    if not MONITOR_CHANNELS:
        await client.send_message(
            user_id,
            "❌ **No channels configured for monitoring.**"
        )
        return
    
    # Initialize user session
    if LOGIN_SYSTEM:
        user_data = await db.get_session(user_id)
        if user_data is None:
            await client.send_message(
                user_id,
                "**For auto monitoring you need to /login first.**"
            )
            return
        
        try:
            acc = Client(
                "automonitor",
                session_string=user_data,
                api_hash=API_HASH,
                api_id=API_ID,
            )
            await acc.start()
        except:
            await client.send_message(
                user_id,
                "**Your login session expired. Please /logout and /login again.**"
            )
            return
    else:
        if TechVJUser is None:
            await client.send_message(
                user_id,
                "**String session is not set.**"
            )
            return
        acc = TechVJUser
    
    # Initialize last message IDs if not exists
    if user_id not in batch_temp.LAST_MESSAGE_IDS:
        batch_temp.LAST_MESSAGE_IDS[user_id] = {}
    
    max_size_mb = batch_temp.MAX_FILE_SIZE.get(user_id, 2000)
    size_info = f"up to {max_size_mb} MB" if max_size_mb > 0 else "All sizes"
    
    await client.send_message(
        user_id,
        f"🤖 **Auto Channel Monitor Started!**\n\n"
        f"📡 Monitoring {len(MONITOR_CHANNELS)} channel(s)\n"
        f"📄 Tracking: Documents only\n"
        f"📏 Size limit: {size_info}\n"
        f"⏱️ Check interval: Random from your settings\n\n"
        f"Use /stopmonitor to stop."
    )
    
    cycle_count = 0
    
    while not batch_temp.CANCEL_TASKS.get(user_id, False):
        cycle_count += 1
        
        try:
            await client.send_message(
                user_id,
                f"🔄 **Cycle #{cycle_count} - Starting channel check...**"
            )
            
            # Process each channel
            for channel_id in MONITOR_CHANNELS:
                if batch_temp.CANCEL_TASKS.get(user_id, False):
                    break
                
                try:
                    # Get last processed message ID for this channel
                    last_msg_id = batch_temp.LAST_MESSAGE_IDS[user_id].get(channel_id, 0)
                    
                    # Fetch new messages from the channel
                    messages = []
                    skipped_count = 0
                    async for msg in acc.get_chat_history(channel_id, limit=100):
                        if msg.id <= last_msg_id:
                            break
                        # Only process documents
                        if msg.document:
                            # Check file size
                            if is_file_within_limit(msg.document.file_size, user_id):
                                messages.append(msg)
                            else:
                                skipped_count += 1
                    
                    # Reverse to process oldest first
                    messages.reverse()
                    
                    if not messages and skipped_count == 0:
                        await client.send_message(
                            user_id,
                            f"📭 Channel `{channel_id}`: No new documents found."
                        )
                        continue
                    
                    status_msg = f"📬 Channel `{channel_id}`: Found {len(messages)} new document(s)"
                    if skipped_count > 0:
                        status_msg += f"\n⚠️ Skipped {skipped_count} file(s) exceeding size limit"
                    
                    await client.send_message(user_id, status_msg)
                    
                    # Process each document
                    for idx, msg in enumerate(messages, 1):
                        if batch_temp.CANCEL_TASKS.get(user_id, False):
                            break
                        
                        try:
                            file_size_str = format_file_size(msg.document.file_size)
                            await client.send_message(
                                user_id,
                                f"📥 Processing document {idx}/{len(messages)} from channel `{channel_id}`\n"
                                f"📦 Size: {file_size_str}"
                            )
                            
                            # Download and upload document
                            success = await process_document(client, acc, user_id, msg)
                            
                            if success:
                                # Update last message ID
                                batch_temp.LAST_MESSAGE_IDS[user_id][channel_id] = msg.id
                                
                                # Sleep between documents using custom sleep
                                if idx < len(messages):
                                    await smart_sleep(user_id)
                            
                        except Exception as e:
                            if ERROR_MESSAGE:
                                await client.send_message(
                                    user_id,
                                    f"❌ Error processing document: {e}"
                                )
                    
                    # Update last message ID even if some failed
                    if messages:
                        batch_temp.LAST_MESSAGE_IDS[user_id][channel_id] = messages[-1].id
                    
                except Exception as e:
                    if ERROR_MESSAGE:
                        await client.send_message(
                            user_id,
                            f"❌ Error checking channel `{channel_id}`: {e}"
                        )
            
            # Check if cancelled
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                break
            
            # Sleep before next cycle
            await client.send_message(
                user_id,
                f"✅ Cycle #{cycle_count} complete. Sleeping before next check..."
            )
            await interval_sleep(user_id)
            
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(
                    user_id,
                    f"❌ Error in monitor cycle: {e}"
                )
            # Sleep on error
            await asyncio.sleep(60)
    
    # Cleanup
    await client.send_message(
        user_id,
        "🛑 **Auto Channel Monitor Stopped!**"
    )
    
    if user_id in batch_temp.AUTO_MONITOR_TASKS:
        del batch_temp.AUTO_MONITOR_TASKS[user_id]


# Process single document
async def process_document(client: Client, acc, user_id: int, msg):
    """Download and upload a single document"""
    
    # Check cancellation
    if batch_temp.CANCEL_TASKS.get(user_id, False):
        return False
    
    # Create a dummy message object for compatibility
    class DummyMessage:
        def __init__(self, chat_id):
            self.chat = type('obj', (object,), {'id': chat_id})
            self.id = random.randint(100000, 999999)
    
    dummy_msg = DummyMessage(user_id)
    
    smsg = await client.send_message(user_id, "**📥 Downloading document...**")
    
    # Start download status
    down_task = asyncio.create_task(
        downstatus(client, f"{dummy_msg.id}downstatus.txt", smsg, user_id, user_id)
    )
    
    file = None
    try:
        # Check cancellation
        if batch_temp.CANCEL_TASKS.get(user_id, False):
            down_task.cancel()
            if os.path.exists(f"{dummy_msg.id}downstatus.txt"):
                os.remove(f"{dummy_msg.id}downstatus.txt")
            await smsg.delete()
            return False
        
        # Download file
        file = await acc.download_media(msg, progress=progress, progress_args=[dummy_msg, "down"])
        
        # Check cancellation
        if batch_temp.CANCEL_TASKS.get(user_id, False):
            down_task.cancel()
            if os.path.exists(f"{dummy_msg.id}downstatus.txt"):
                os.remove(f"{dummy_msg.id}downstatus.txt")
            if file and os.path.exists(file):
                os.remove(file)
            await smsg.delete()
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
        
        # Remove download status
        if os.path.exists(f"{dummy_msg.id}downstatus.txt"):
            os.remove(f"{dummy_msg.id}downstatus.txt")
        
        down_task.cancel()
        
    except Exception as e:
        if os.path.exists(f"{dummy_msg.id}downstatus.txt"):
            os.remove(f"{dummy_msg.id}downstatus.txt")
        down_task.cancel()
        if file and os.path.exists(file):
            os.remove(file)
        if ERROR_MESSAGE:
            await client.send_message(user_id, f"❌ Download error: {e}")
        await smsg.delete()
        return False
    
    # Check cancellation before upload
    if batch_temp.CANCEL_TASKS.get(user_id, False):
        if file and os.path.exists(file):
            os.remove(file)
        await smsg.delete()
        return False
    
    # Update to uploading
    try:
        await smsg.edit("**📤 Uploading document...**")
    except:
        pass
    
    # Start upload status
    up_task = asyncio.create_task(
        upstatus(client, f"{dummy_msg.id}upstatus.txt", smsg, user_id, user_id)
    )
    
    caption = msg.caption if msg.caption else None
    upload_success = False
    
    # Download thumbnail
    perm_thumb = None
    if PERMANENT_THUMBNAIL_URL:
        perm_thumb = await download_thumbnail(client, PERMANENT_THUMBNAIL_URL)
    
    try:
        if batch_temp.CANCEL_TASKS.get(user_id, False):
            raise Exception("Cancelled by user")
        
        # Get thumbnail
        if perm_thumb:
            ph_path = perm_thumb
        else:
            try:
                ph_path = await acc.download_media(msg.document.thumbs[0].file_id)
            except:
                ph_path = None
        
        # Upload document
        await client.send_document(
            user_id,
            file,
            thumb=ph_path,
            caption=caption,
            parse_mode=enums.ParseMode.HTML,
            progress=progress,
            progress_args=[dummy_msg, "up"],
        )
        upload_success = True
        
        if ph_path and os.path.exists(ph_path):
            os.remove(ph_path)
    
    except Exception as e:
        if "Cancelled by user" not in str(e) and ERROR_MESSAGE:
            await client.send_message(user_id, f"❌ Upload error: {e}")
    
    # Cleanup
    if os.path.exists(f"{dummy_msg.id}upstatus.txt"):
        os.remove(f"{dummy_msg.id}upstatus.txt")
    
    up_task.cancel()
    
    if file and os.path.exists(file):
        os.remove(file)
    
    try:
        await smsg.delete()
    except:
        pass
    
    return upload_success


# Start auto monitoring command
@Client.on_message(filters.command(["startmonitor"]))
async def start_monitor(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if already running
    if user_id in batch_temp.AUTO_MONITOR_TASKS:
        await message.reply("⚠️ **Auto monitoring is already running!**\n\nUse /stopmonitor to stop it first.")
        return
    
    # Reset cancellation flag
    batch_temp.CANCEL_TASKS[user_id] = False
    
    # Start monitoring task
    task = asyncio.create_task(auto_channel_monitor(client, user_id))
    batch_temp.AUTO_MONITOR_TASKS[user_id] = task
    
    await message.reply("✅ Starting auto channel monitor...")


# Stop auto monitoring command
@Client.on_message(filters.command(["stopmonitor"]))
async def stop_monitor(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in batch_temp.AUTO_MONITOR_TASKS:
        await message.reply("❌ **No active monitoring process found.**")
        return
    
    # Set cancellation flag
    batch_temp.CANCEL_TASKS[user_id] = True
    
    await message.reply("🛑 **Stopping auto monitor...**\n\nThis may take a few seconds.")


# Monitor status command
@Client.on_message(filters.command(["monitorstatus"]))
async def monitor_status(client: Client, message: Message):
    user_id = message.from_user.id
    
    is_running = user_id in batch_temp.AUTO_MONITOR_TASKS
    interval_values = batch_temp.INTERVAL_SLEEP.get(user_id, [300, 600, 900, 1200])
    sleep_values = batch_temp.CUSTOM_SLEEP.get(user_id, [3, 5, 7, 10])
    max_size_mb = batch_temp.MAX_FILE_SIZE.get(user_id, 2000)
    
    status_text = f"**📊 Auto Monitor Status**\n\n"
    status_text += f"🔴 Status: {'🟢 Running' if is_running else '⚪ Stopped'}\n"
    status_text += f"📡 Channels: {len(MONITOR_CHANNELS)}\n"
    status_text += f"📏 Max Size: {'No limit' if max_size_mb == 0 else f'{max_size_mb} MB'}\n"
    status_text += f"⏱️ Check Intervals: `{', '.join(map(str, interval_values))}` sec\n"
    status_text += f"💤 Download Sleep: `{', '.join(map(str, sleep_values))}` sec\n"
    
    if user_id in batch_temp.LAST_MESSAGE_IDS:
        status_text += f"\n**📍 Last Processed Messages:**\n"
        for ch_id, msg_id in batch_temp.LAST_MESSAGE_IDS[user_id].items():
            status_text += f"Channel `{ch_id}`: Message #{msg_id}\n"
    
    await message.reply(status_text)


# cancel command - IMMEDIATE STOP
@Client.on_message(filters.command(["cancel"]))
async def send_cancel(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if there's an active batch
    if user_id not in batch_temp.IS_BATCH or batch_temp.IS_BATCH.get(user_id, True) is True:
        # Check for auto monitor
        if user_id in batch_temp.AUTO_MONITOR_TASKS:
            batch_temp.CANCEL_TASKS[user_id] = True
            await message.reply("🛑 **Stopping auto monitor...**")
            return
        
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
async def handle_private(client: Client, acc, message: Message, chatid: int, msgid: int):
    user_id = message.from_user.id
    
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
        try:
            await client.send_message(
                chat,
                msg.text,
                entities=msg.entities,
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
            )
            return True
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(
                    message.chat.id,
                    f"Error: {e}",
                    reply_to_message_id=message.id,
                    parse_mode=enums.ParseMode.HTML,
                )
            return False

    smsg = await client.send_message(message.chat.id, "**Downloading**", reply_to_message_id=message.id)
    
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
                reply_to_message_id=message.id,
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
    
    caption = msg.caption if msg.caption else None
    upload_success = False
    
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
            
            if ph_path and os.path.exists(ph_path):
                os.remove(ph_path)

        elif msg_type == "Animation":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise Exception("Cancelled by user")
            
            await client.send_animation(chat, file, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
            upload_success = True

        elif msg_type == "Sticker":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise Exception("Cancelled by user")
            
            await client.send_sticker(chat, file, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
            upload_success = True

        elif msg_type == "Voice":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise Exception("Cancelled by user")
            
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
            
            if ph_path and os.path.exists(ph_path):
                os.remove(ph_path)

        elif msg_type == "Photo":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise Exception("Cancelled by user")
            
            await client.send_photo(
                chat, file, caption=caption, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML
            )
            upload_success = True

    except Exception as e:
        if "Cancelled by user" not in str(e) and ERROR_MESSAGE:
            await client.send_message(
                message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML
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
