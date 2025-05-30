import sqlalchemy
from typing import List
import memes
from pyrogram import Client
from pyrogram.types import Message, InputMediaVideo
from pyrogram.enums import ParseMode
from datetime import datetime, timezone, timedelta
from sambot import Sambot, BotPipelineSegmentBase, MessageAdapter
from pyrogram.handlers import MessageHandler
from wordcloud import WordCloud
import asyncio
import re
from io import BytesIO
import random
from PyL360 import L360Client
import os
from database import get_session, Reminder
import time
import logging
from utils import setup_logger
from pyrogram.types import ChatMember


class PingIndicator(BotPipelineSegmentBase):
    '''
    Segment to indicate if the bot is alive. It will send a message with uptime duration

    Activate by sending '.ping'
    '''

    def CanHandle(self, message: Message):
        if not message.text:
            return False
        return message.text == '.ping' and message.from_user.is_self

    async def ProcessMessage(self, bot: Client, message: Message):
        if (not self.CanHandle(message)):
            return
        uptime = (datetime.now(timezone.utc) -
                  self.sambot._startTimeUtc).total_seconds()
        await bot.edit_message_text(message.chat.id, message.id, f"Online. I've been up for {int(uptime)} seconds now. Uptime was at {self.sambot._startTimeUtc}")
        await asyncio.sleep(3)
        await bot.delete_messages(chat_id=message.chat.id, message_ids=[message.id])

    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.ProcessMessage)
        bot.add_handler(handler, group=1001)
        # return await super().RegisterSegment(sambot, bot)


class TikTokDownloader(BotPipelineSegmentBase):
    '''
    Segment to download TikTok and Youtube videos

    Activate it by replying the command '.dl' to a message that contains a URL to a video
    '''

    def __init__(self):
        self.logger = logging.getLogger('TikTokDownloader')
        setup_logger(self.logger)

    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|'
        r'(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )

    issue_messages = [
        "One second"
        "Something went wrong. Let me try again...",
        "Third times the charm! (Updating YT-DLP)",
        "Uhhh... just one second"
    ]

    invalid_operation_messages = [
        "You need to reply with a link!",
        "Where's the link?",
        "What do you want me to download? Reply to a message with a link!",
        "Im gonna need a link"
    ]

    def can_download(self, message: Message):
        if not message.text:
            return False
        return message.text == '.dl'

    def can_ban(self, message: Message):
        if not message.reply_to_message:
            return False
        if not message.from_user.is_self:
            return False
        return message.text == '.ban_dl'

    def can_unban(self, message: Message):
        if not message.reply_to_message:
            return False
        if not message.from_user.is_self:
            return False
        return message.text == '.unban_dl'

    async def ban_user(self, message: Message):
        if message.reply_to_message.from_user.id in self.sambot.configuration["TikTokDl"]["BannedUsers"]:
            await message.edit_text("This guy is already banned")
            return
        self.sambot.configuration['TikTokDl']['BannedUsers'].append(
            message.reply_to_message.from_user.id)
        self.sambot.SaveConfiguration()
        await message.edit_text("This fool has been banned!")

    async def unban_user(self, message: Message):
        if not message.reply_to_message.from_user.id in self.sambot.configuration["TikTokDl"]["BannedUsers"]:
            await message.edit_text("This guy was not banned")
            return
        self.sambot.configuration['TikTokDl']['BannedUsers'].remove(
            message.reply_to_message.from_user.id)
        self.sambot.SaveConfiguration()
        await message.edit_text("This fool has been unbanned!")

    def update_and_reimport_yt_dlp(self):
        import subprocess
        import importlib
        import sys
        try:
            # Install or update yt-dlp using pip
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])

            # Import or reload yt-dlp to get the latest version
            import yt_dlp
            importlib.reload(yt_dlp)
            self.logger.info(
                "yt-dlp has been updated and re-imported successfully.")

            return yt_dlp  # Return the module if needed
        except Exception as e:
            self.logger.fatal(f"An error occurred: {e}")

    async def process_message(self, bot: Client, message: Message):
        message = MessageAdapter(message)

        if not message.text:
            return False  # Check if its a text message

        if self.can_ban(message):  # Check if its a message to ban users
            await self.ban_user(message)
            return

        if self.can_unban(message):  # Check if its a message to unban users
            await self.unban_user(message)
            return

        if not self.can_download(message):
            return  # If its not a module related message, ignore it

        # If the fool is banned, react to the origin
        # message with the bird
        if message.from_user.id in self.sambot.configuration['TikTokDl']['BannedUsers']:
            await message.react("🖕")
            return

        if not message.IsRealReply():
            await self.reply_with_issue(bot, message, random.choice(self.invalid_operation_messages))
            return

        url_match = re.search(self.url_pattern, message.reply_to_message.text)
        if not url_match:
            await self.reply_with_issue(bot, message, "You need to reply to a message with a url, and no url was detected in this message!")
            return

        status_msg: Message = await self.reply_with_issue(bot, message, 'One sec. Downloading the file...')
        try_count = 0

        while (True):
            try:
                file = self.download_tiktok_video(
                    url_match.string, reloadlib=try_count > 2)
                await bot.send_media_group(
                    media=[InputMediaVideo(file, caption="Here you go!")],
                    chat_id=message.chat.id,
                    reply_to_message_id=message.reply_to_message_id)
                if status_msg:
                    await bot.delete_messages(status_msg.chat.id, message_ids=[status_msg.id])
                return
            except Exception as e:
                if (try_count == 2):
                    self.update_and_reimport_yt_dlp()

                if (try_count <= 2):
                    await status_msg.edit_text(self.issue_messages[try_count])
                    await asyncio.sleep(3)
                else:
                    await status_msg.edit_text("Yeah no, I give up, this can't be downloaded. I have failed. I failed and let down my entire clan")
                    self.logger.fatal(
                        "Download failed for {}: {}".format(url_match.string, e))
                    break
                try_count += 1

    async def reply_with_issue(self, bot: Client, message: MessageAdapter, issue: str):
        if (message.from_user.is_self):
            return await bot.edit_message_text(message.chat.id, message.id, issue)
        else:
            return await bot.send_message(
                chat_id=message.chat.id,
                text=issue,
                reply_to_message_id=message.reply_to_top_message_id)

    def download_tiktok_video(self, url, output_path='ext-mount/cache/', reloadlib: bool = False) -> str:
        import yt_dlp
        import hashlib
        import os
        import importlib

        if reloadlib:
            importlib.reload(yt_dlp)
        md5_hash = hashlib.md5()
        md5_hash.update(url.encode('utf-8'))
        filename = md5_hash.hexdigest()

        if os.path.exists(f'{output_path}/{filename}.mp4'):
            return f'{output_path}/{filename}.mp4'

        ydl_opts = {
            'outtmpl': f'{output_path}/{filename}.%(ext)s',
            'format': 'best',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',  # Convert to mp4 if needed
            }]
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return f'{output_path}/{filename}.mp4'

    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message)
        bot.add_handler(handler, group=1002)
        # return super().RegisterSegment(sambot, bot)


class MentionEveryone(BotPipelineSegmentBase):
    '''
    Mention everyone in the chat when @everyone is mentioned
    '''

    async def can_handle(self, message: MessageAdapter):
        if not message.text:
            return False
        if not message.chat.id in self.sambot.configuration["MentionEveryone"]["AllowedChats"]:
            return False
        return '@everyone' in (await message.GetMentionedUsers())

    def can_handle_config(self, message: Message):
        if (not message.from_user.is_self):
            return False
        return ' '.join(message.text.split()[:2]) == ".config mentioneveryone"

    async def handle_config_instruction(self, bot: Client, message: Message):
        parts = message.text.split()

        if (len(parts) == 2):
            parts.append('')

        if (parts[2] == 'add'):
            self.sambot.configuration['MentionEveryone']['AllowedChats'].append(
                message.chat.id)
        elif (parts[2] == 'remove'):
            self.sambot.configuration['MentionEveryone']['AllowedChats'].append(
                message.chat.id)
        else:
            await bot.send_message(
                chat_id=message.chat.id,
                text="Uknown command. Please use .config everyone_mention add|remove",
                reply_to_message_id=message.id
            )
            return

        await bot.send_message(
            chat_id=message.chat.id,
            text=f"Changes made",
            reply_to_message_id=message.id
        )
        self.sambot.SaveConfiguration()
        return

    async def process_message(self, bot: Client, message: MessageAdapter):
        message = MessageAdapter(message)
        if not message.text:
            return
        if (not await self.can_handle(message)):
            if self.can_handle_config(message):
                await self.handle_config_instruction(bot, message)
                return
            else:
                return
        mentioned_users: List[str] = []
        # user: ChatMember
        async for user in bot.get_chat_members(message.chat.id):
            user_mention = f"[{user.user.username or user.user.first_name}](tg://user?id={user.user.id})"
            mentioned_users.append(user_mention)

        # Chunk the mentioned_users list into groups of 5
        chunk_size = 5
        for i in range(0, len(mentioned_users), chunk_size):
            chunk = mentioned_users[i:i + chunk_size]
            await bot.send_message(
                chat_id=message.chat.id,
                text=' '.join(chunk),
                reply_to_message_id=message.id
            )

    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message)
        bot.add_handler(handler, 1003)
        return super().RegisterSegment(sambot, bot)


class TerminateSegment(BotPipelineSegmentBase):
    async def can_handle(self, message: MessageAdapter):
        if not message.text:
            return
        if not message.from_user.is_self:
            return
        return message.text == ".terminate"

    async def process_message(self, bot: Client, message: MessageAdapter):
        if (not await self.can_handle(message)):
            return
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"`Terminating self... Good bye...`",
            reply_to_message_id=message.id,
            parse_mode=ParseMode.MARKDOWN
        )
        await asyncio.create_task(bot.stop(False))
        open('terminate-lockfile', 'a').close()
        exit()

    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message)
        bot.add_handler(handler, 1004)


class ReactionCounter(BotPipelineSegmentBase):
    def can_handle(self, message: MessageAdapter):
        if not message.text:
            return
        return message.text == ".leaderboard" and message.from_user.is_self

    async def update_loading_async(self, message: MessageAdapter):
        postfix = ''
        while True:
            postfix += '.'
            if len(postfix) > 3:
                postfix = ''
            await message.edit_text("Loading leaderboard" + postfix)
            await asyncio.sleep(.5)

    def stop_loading(self, thread: asyncio.Future):
        thread.cancel()

    async def create_loading_message_async(self, bot: Client, message: MessageAdapter):
        loading_message = await message.reply_text("⌛ Loading leaderboard")

        # Create a new thread and call update_loading
        loop = asyncio.get_event_loop()
        thread = loop.create_task(self.update_loading_async(loading_message))

        return thread, loading_message

    async def process_message(self, bot: Client, message: MessageAdapter):
        if (not self.can_handle(message)):
            return

        loading_anim_future, og_msg = await self.create_loading_message_async(bot, message)

        start_date = datetime.today() - timedelta(days=1)
        reactions_dict = dict()
        messages_count_dict = dict()
        # Fetch messages from the chat
        async for msg in bot.get_chat_history(message.chat.id):
            # Check if message date is within the last n days
            if msg.date >= start_date:
                if not msg.from_user:
                    continue
                key = msg.from_user.first_name

                if (msg.text):
                    # if its a text message, increment the dictionary.key with the number
                    # of words (split string with white space)
                    messages_count_dict[key] = messages_count_dict.get(
                        key, 0) + len(msg.text.split(' '))
                else:
                    # otherwise just increment by one
                    messages_count_dict[key] = messages_count_dict.get(
                        key, 0) + 1

                if (msg.reactions is None):
                    continue
                count = sum(r.count for r in msg.reactions.reactions)
                reactions_dict[key] = reactions_dict.get(key, 0) + count

            else:
                break  # Stop if messages are older than start_date

        reactions_dict = {k: v for k, v in sorted(
            reactions_dict.items(), key=lambda item: item[1], reverse=True)}
        messages_count_dict = {k: v for k, v in sorted(
            messages_count_dict.items(), key=lambda item: item[1], reverse=True)}

        reply_message = "**Reactions Leaderboard ✨**\n"
        reply_message += '\n'.join(['- {} : {}'.format(x,
                                   reactions_dict[x]) for x in reactions_dict])
        reply_message += "\n\n**Yappin Leaderboard 🗣️**\n"
        reply_message += '\n'.join(['- {} : {}'.format(x, messages_count_dict[x])
                                   for x in messages_count_dict])
        await og_msg.edit_text(reply_message)
        self.stop_loading(loading_anim_future)

    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message)
        bot.add_handler(handler, 1005)


class WordCloudGenerator(BotPipelineSegmentBase):

    currentMessage = ''
    isRunning = False

    def can_handle(self, message: MessageAdapter):
        if not message.text:
            return
        return message.text == ".wordcloud" and message.from_user.is_self

    async def update_loading_async(self, message: MessageAdapter):
        postfix = ''
        while True:
            postfix += '.'
            if len(postfix) > 3:
                postfix = ''
            await message.edit_text(f'`{self.currentMessage}{postfix}`', parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(.5)

    def stop_loading(self, thread: asyncio.Future):
        thread.cancel()

    async def create_loading_message_async(self, bot: Client, message: MessageAdapter):
        loading_message = await message.reply_text("⌛ Loading leaderboard")

        # Create a new thread and call update_loading
        loop = asyncio.get_event_loop()
        thread = loop.create_task(self.update_loading_async(loading_message))

        return thread, loading_message

    async def process_message(self, bot: Client, message: MessageAdapter):
        # Check if the message is from me
        if (not self.can_handle(message)):
            return
        
        if (self.isRunning):
            await message.reply_text("I'm already generating a wordcloud, please try again later")
            return
        
        future, og_msg = await self.create_loading_message_async(bot, message)
        self.isRunning = True

        start_date = datetime.today() - timedelta(days=3)
        messages_list = []
        # Fetch messages from the chat
        async for msg in bot.get_chat_history(message.chat.id):
            # Check if message date is within the last n days
            if msg.date >= start_date:
                if (not msg.text):
                    continue
                messages_list.append(msg.text)
            else:
                break  # Stop if messages are older than start_date
            self.currentMessage = f'Reading messages from {msg.date.strftime("%Y-%m-%d")}'

        self.currentMessage = f'Generating wordcloud from {len(messages_list)} messages'
        joined = ' '.join(messages_list)
        wordcloud = WordCloud(
            width=1080,
            height=1080,
            min_word_length=3,

        ).generate(joined).to_image()

        binary_io = BytesIO()

        # Save the image to the BytesIO object
        wordcloud.save(binary_io, format="PNG")
        binary_io.seek(0)
        await bot.send_photo(
            chat_id=message.chat.id,
            reply_to_message_id=message.reply_to_message_id or message.reply_to_top_message_id,
            photo=binary_io
        )
        self.stop_loading(future)
        await og_msg.delete()
        self.isRunning = False

    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message)
        bot.add_handler(handler, 1006)


class WhoIsNoora(BotPipelineSegmentBase):
    pass


class Life360Integration(BotPipelineSegmentBase):

    def __init__(self):
        self.l360_client = L360Client(
            username=os.getenv("Life360_Username"),
            password=os.getenv("Life360_Password"),
        )
        self.l360_client.Authenticate()

    async def process_message(self, bot: Client, message: MessageAdapter):
        message = MessageAdapter(message)
        if not message.text:
            return
        if message.text.split()[0] == '.whereis':
            await self.HandleQuery(bot, message)
        if not message.from_user.is_self:
            return
        if ' '.join(message.text.split()[:2]) == ".config whereis":
            await self.HandleConfiguration(bot, message)

    async def HandleQuery(self, bot: Client, message: MessageAdapter):
        if message.chat.id not in self.sambot.configuration["L360"]["AllowedChats"]:
            return
        mentioned_users = await message.GetMentionedUsersIds()
        if len(mentioned_users) != 1:
            await message.reply_text("You need to mention one user like `.whereis @sammy`", parse_mode=ParseMode.MARKDOWN)
            return
        user_id = str(mentioned_users[0])

        assignments = self.sambot.configuration["L360"]["Assignments"]

        if not user_id in assignments:
            await message.reply_text("`No L360 profile is assigned to this user`", parse_mode=ParseMode.MARKDOWN)
            return

        l360_entry = assignments[user_id].split('/')
        l360_user = l360_entry[1]
        l360_circle = l360_entry[0]

        reply_msg = await message.reply_text("`Asking Life360...`", parse_mode=ParseMode.MARKDOWN)
        available_circles = self.l360_client.GetCircles()
        circle = next(
            (x for x in available_circles.circles if x.name == l360_circle), None)

        if not circle:
            await message.reply_text("The circle `{}` was not found on my Life360 account".format(l360_circle), parse_mode=ParseMode.MARKDOWN)
            return

        circle_members_list = circle.GetDetails().members
        circle_member = next(
            (x for x in circle_members_list if x.firstName == l360_user), None)

        if not circle_member:
            await message.reply_text("The user `{}` was not found in `{}`".format(l360_user, l360_circle), parse_mode=ParseMode.MARKDOWN)
            return

        await asyncio.sleep(1)
        await reply_msg.delete()

        summary_data = "{} is at {}".format(
            circle_member.firstName,
            circle_member.location.name or circle_member.location.shortAddress
        )
        summary_msg = await message.reply_text(summary_data)
        await summary_msg.reply_location(
            latitude=float(circle_member.location.latitude),
            longitude=float(circle_member.location.longitude),
        )

    async def HandleConfiguration(self, bot: Client, message: MessageAdapter):
        message_parts = message.text.split()
        if len(message_parts) < 3:
            await message.edit_text("`Invalid command\nsetuser - Link a user to a L360 user`", parse_mode=ParseMode.MARKDOWN)
            return

        match message_parts[2]:
            case "setuser":
                if not message.IsRealReply():
                    await message.edit_text("`You need to reply to a user for this command`", parse_mode=ParseMode.MARKDOWN)
                    return
                l360User = ' '.join(message_parts[3:])
                self.sambot.configuration["L360"]["Assignments"][str(
                    message.reply_to_message.from_user.id)] = l360User
                self.sambot.SaveConfiguration()
                await message.react("👍")

            case "unsetuser":
                if not message.IsRealReply():
                    await message.reply_text("`You need to reply to a user for this command`", parse_mode=ParseMode.MARKDOWN)
                    return

                if not str(message.reply_to_message.from_user.id) in self.sambot.configuration["L360"]["Assignments"]:
                    await message.reply_text("`This user is not configured`", parse_mode=ParseMode.MARKDOWN)
                    return

                del self.sambot.configuration["L360"]["Assignments"][str(
                    message.reply_to_message.from_user.id)]
                self.sambot.SaveConfiguration()
                await message.react("👍")

            case "allow":
                self.sambot.configuration["L360"]["AllowedChats"].append(
                    message.chat.id)
                self.sambot.SaveConfiguration()
                await message.react("👍")
                pass

            case "disallow":
                self.sambot.configuration["L360"]["AllowedChats"].remove(
                    message.chat.id)
                self.sambot.SaveConfiguration()
                await message.react("👍")
                pass

            case default:
                await message.edit_text("`Invalid command`", parse_mode=ParseMode.MARKDOWN)

    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message)
        bot.add_handler(handler, 1007)


class RemindMeLater(BotPipelineSegmentBase):

    def __init__(self):
        self.logger = logging.getLogger('RemindMeLater')
        setup_logger(self.logger)

    def get_total_seconds_from_string(self, time_string: str) -> int:
        import re

        pattern = r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?'
        match = re.match(pattern, time_string)

        if not match:
            raise ValueError("Invalid time format")
        days, hours, minutes, seconds = match.groups(default='0')
        total_seconds = int(days) * 86400 + int(hours) * \
            3600 + int(minutes) * 60 + int(seconds)
        return total_seconds

    async def add_reminder(self, bot: Client, message: MessageAdapter):
        message_text = message.text.split()
        if len(message_text) < 3:
            await message.reply_text("`Invalid command. Please use .remindme time message`")
            return

        try:
            total_seconds = self.get_total_seconds_from_string(message_text[1])
        except ValueError:
            await message.reply_text("`Invalid time format. Please use (number)d|h|m|s`")
            return

        if total_seconds <= 0:
            await message.reply_text("`Time must be greater than 0`")
            return

        reminder_val = ' '.join(message_text[2:])

        reminder_object = Reminder(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            reminder_text=reminder_val,
            remind_at=datetime.now(timezone.utc) +
            timedelta(seconds=total_seconds),
            messageid=message.id
        )
        time_left = (reminder_object.remind_at -
                     datetime.now(timezone.utc)).total_seconds()
        if (time_left < 30):
            asyncio.create_task(self.wait_and_send_reminder(reminder_object))
        else:
            self.add_reminder_to_db(reminder_object)
        await message.reply_text("⏰ Reminder added!")

    def start_check_reminder_job(self):
        loop = asyncio.get_event_loop()
        loop.call_soon(lambda: asyncio.create_task(self.check_reminders()))

    async def check_reminders(self):
        self.logger.info("Starting reminder background job...")
        while True:
            session = get_session()
            reminders = session.query(Reminder).filter(
                Reminder.remind_at <= datetime.now(timezone.utc) + timedelta(seconds=30)).all()
            for reminder in reminders:
                asyncio.create_task(
                    self.wait_and_send_reminder(reminder, cleanup=True))
            await asyncio.sleep(30)

    async def wait_and_send_reminder(self, reminder: Reminder, cleanup: bool = False):
        if reminder.remind_at.tzinfo is None:
            reminder.remind_at = reminder.remind_at.replace(
                tzinfo=timezone.utc)

        time_left = (reminder.remind_at -
                     datetime.now(timezone.utc)).total_seconds()

        self.logger.info("Reminder found: {} with {}s left : arming".format(
            reminder.reminder_text, time_left))
        await asyncio.sleep(time_left)
        original_user = (await self.sambot.bot.get_users(reminder.user_id))
        await self.sambot.bot.send_message(
            chat_id=reminder.chat_id,
            text="Hey [{}](tg://user?id={})! This is a reminder for: **{}** ⏰".format(
                original_user.first_name, reminder.user_id, reminder.reminder_text),
            reply_to_message_id=reminder.messageid,
            parse_mode=ParseMode.MARKDOWN
        )

        if (cleanup):
            session = get_session()
            session.delete(reminder)
            session.commit()
        pass

    def add_reminder_to_db(self, reminder: Reminder):
        from database import get_session
        session = get_session()
        session.add(reminder)
        session.commit()

    async def check_if_reminders_allowed(self, message: MessageAdapter) -> bool:
        if not message.chat.id in self.sambot.configuration["RemindMe"]["AllowedChats"]:
            return False
        return True

    async def handle_config_instruction(self, bot: Client, message: MessageAdapter):
        message_parts = message.text.split()
        if len(message_parts) < 3:
            await message.edit_text("`Invalid command\n.config remindme allow | disallow`", parse_mode=ParseMode.MARKDOWN)
            return

        match message_parts[2]:
            case "allow":
                self.sambot.configuration["RemindMe"]["AllowedChats"].append(
                    message.chat.id)
                self.sambot.SaveConfiguration()
                await message.react("👍")
                pass

            case "disallow":
                self.sambot.configuration["RemindMe"]["AllowedChat"].remove(
                    message.chat.id)
                self.sambot.SaveConfiguration()
                await message.react("👍")
                pass

            case default:
                await message.edit_text("`Invalid command`", parse_mode=ParseMode.MARKDOWN)

    async def process_message(self, bot: Client, message: MessageAdapter):
        message = MessageAdapter(message)
        if not message.text:
            return
        if message.text.split()[0] == '.remindme':
            if await self.check_if_reminders_allowed(message):
                await self.add_reminder(bot, message)
        if message.from_user.is_self:
            if ' '.join(message.text.split()[:2]) == '.config remindme':
                await self.handle_config_instruction(bot, message)

    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message)
        bot.add_handler(handler, 1008)
        self.start_check_reminder_job()
