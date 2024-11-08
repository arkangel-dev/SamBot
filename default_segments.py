from pyrogram import Client
from pyrogram.types import Message, InputMediaVideo
from pyrogram.enums import ParseMode
from typing import Coroutine, List
from datetime import datetime, timezone
from sambot import Sambot, BotPipelineSegmentBase, MessageAdapter
from chatgpt import ChatGpt
from pyrogram.handlers import MessageHandler, MessageReactionUpdatedHandler

import asyncio
import re
import random

class PingIndicator(BotPipelineSegmentBase):
    '''
    Segment to indicate if the bot is alive. It will send a message with uptime duration

    Activate by sending '.ping'
    '''
    def CanHandle(self, message: Message):
        if not message.text: return False
        return message.text == '.ping' and message.from_user.is_self
        
    async def ProcessMessage(self, bot: Client, message: Message):
        if (not self.CanHandle(message)): return
        uptime = (datetime.now(timezone.utc) - self.sambot._startTimeUtc).total_seconds()
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
    
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|'
        r'(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    
    issue_messages = [
        "One second"
        "Something went wrong. Let me try again...",
        "Third times the charm! (Updating YT-DLP)"
    ]
    
    invalid_operation_messages = [
        "You need to reply with a link!",
        "Where's the link?",
        "What do you want me to download? Reply to a message with a link!",
        "Im gonna need a link"
    ]
    
    def can_handle(self, message: Message):
        if not message.text: return False
        return message.text == '.dl'
    
    def update_and_reimport_yt_dlp(self):
        import subprocess
        import importlib
        import sys
        try:
            # Install or update yt-dlp using pip
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
            
            # Import or reload yt-dlp to get the latest version
            import yt_dlp
            importlib.reload(yt_dlp)
            print("yt-dlp has been updated and re-imported successfully.")
            
            return yt_dlp  # Return the module if needed
        except Exception as e:
            print(f"An error occurred: {e}")
        
    async def process_message(self, bot: Client, message: Message):
        message = MessageAdapter(message)
        if (not self.can_handle(message)): return
        
        if not message.IsRealReply():
            await self.reply_with_issue(bot, message, random.choice(self.invalid_operation_messages))
            return
        
        url_match = re.search(self.url_pattern, message.reply_to_message.text)
        if not url_match:
            await self.reply_with_issue(bot, message, "You need to reply to a message with a url, and no url was detected in this message!")
            return

        status_msg:Message = await self.reply_with_issue(bot, message, 'One sec. Downloading the file...')
        try_count = 0
        
        while (True):
            try:
                file = self.download_tiktok_video(url_match.string)
                await bot.send_media_group(
                    media=[InputMediaVideo(file, caption="Here you go!")],
                    chat_id=message.chat.id, 
                    reply_to_message_id=message.reply_to_message_id)
                if status_msg:
                    await bot.delete_messages(status_msg.chat.id, message_ids=[status_msg.id])
                return
            except:
                if (try_count == 2):
                    self.update_and_reimport_yt_dlp()
                
                if (try_count < 3):
                    await status_msg.edit_text(self.issue_messages[try_count])
                else:
                    await status_msg.edit_text("Yeah no, I give up, this can't be downloaded. Either my IP is ratelimited or this link doesn't have a downloadable video.")
                    break
                try_count += 1
    
    async def reply_with_issue(self, bot:Client, message:MessageAdapter, issue:str):
        if (message.from_user.is_self):
            return await bot.edit_message_text(message.chat.id, message.id, issue)
        else:
            return await bot.send_message(
                chat_id=message.chat.id,
                text=issue,
                reply_to_message_id=message.reply_to_top_message_id)

    def download_tiktok_video(self, url, output_path='ext-mount/cache/') -> str:
        import yt_dlp
        import hashlib
        import os

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
        if not message.text: return False
        if not message.chat.id in self.sambot.configuration["mentioneveryone"]["allowed_chats"]: return False
        return '@everyone' in (await message.GetMentionedUsers())
    
    def can_handle_config(self, message: Message):
        if (not message.from_user.is_self): return False
        return ' '.join(message.text.split()[:2]) == ".config mentioneveryone"
    
    async def handle_config_instruction(self, bot:Client, message:Message):
        parts = message.text.split()

        if (len(parts) == 2):
            parts.append('')

        if (parts[2] == 'add'):
            self.sambot.configuration['mentioneveryone']['allowed_chats'].append(message.chat.id)
        elif (parts[2] == 'remove'):
            self.sambot.configuration['mentioneveryone']['allowed_chats'].append(message.chat.id)
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
        if (not await self.can_handle(message)): 
            if self.can_handle_config(message):
                await self.handle_config_instruction(bot, message)
                return
            else:
                return
        mentioned_users = []
        async for user in bot.get_chat_members(message.chat.id):
            mentioned_users.append(f"[{user.user.first_name}](tg://user?id={user.user.id})")
        await bot.send_message(
            chat_id=message.chat.id,
            text=' '.join(mentioned_users),
            reply_to_message_id=message.id
        )
        
    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message)
        bot.add_handler(handler, 1003)
        return super().RegisterSegment(sambot, bot)

class TerminateSegment(BotPipelineSegmentBase):
    async def can_handle(self, message: MessageAdapter):
        if not message.text: return
        if not message.from_user.is_self: return
        return message.text == ".terminate"
    
    async def process_message(self, bot: Client, message: MessageAdapter):
        if (not await self.can_handle(message)): return
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"`Terminating self... Good bye...`",
            reply_to_message_id=message.id,
            parse_mode=ParseMode.MARKDOWN
        )
        await asyncio.create_task(bot.stop(False))
        exit()
        
    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message, 1004)
        bot.add_handler(handler)
