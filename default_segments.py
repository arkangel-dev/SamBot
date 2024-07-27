from pyrogram import Client
from pyrogram.types import Message, InputMediaVideo
from typing import Coroutine
from datetime import datetime, timezone
from sambot import Sambot, BotPipelineSegmentBase

import time
import uuid
import asyncio
import re

'''
Segment to indicate if the bot is alive. It will send a message with uptime duration

Activate by sending '.ping'
'''
class PingIndicator(BotPipelineSegmentBase):
    async def CanHandle(self, sambot: Sambot, message: Message):
        return message.text == '.ping' and message.from_user.is_self
        
    async def ProcessMessage(self, sambot: Sambot, bot: Client, message: Message):
        uptime = (datetime.now(timezone.utc) - sambot._startTimeUtc).total_seconds()
        await bot.edit_message_text(message.chat.id, message.id, f"Online. I've been up for {int(uptime)} seconds now. Uptime was at {sambot._startTimeUtc}")
        await asyncio.sleep(3)
        await bot.delete_messages(chat_id=message.chat.id, message_ids=[message.id])

'''
Segment to download TikTok and Youtube videos

Activate it by replying the command '.dl' to a message that contains a URL to a video
'''
class TikTokDownloader(BotPipelineSegmentBase):
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|'
        r'(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    
    async def CanHandle(self, sambot: Sambot, message: Message):
        return message.text == '.dl'
    
    async def ProcessMessage(self, sambot: Sambot, bot: Client, message: Message):
        if (message.reply_to_message is None):
            await self.ReplyWithIssue(bot, message, "You need to reply to a message with a url!")
        url_match = re.search(self.url_pattern, message.reply_to_message.text)
        if not url_match:
            await self.ReplyWithIssue(bot, message, "You need to reply to a message with a url, and no url was detected in this message!")

        await bot.edit_message_text(message.chat.id, message.id, f"Please wait while I download the file")
        file = self.download_tiktok_video(url_match.string)
        await bot.delete_messages(message.chat.id, message_ids=[message.id])
        await bot.send_media_group(
            media=[InputMediaVideo(file, caption="Here you go!")],
            chat_id=message.chat.id, 
            reply_to_message_id=message.reply_to_message_id)
    
    async def ReplyWithIssue(self, bot:Client, message:Message, issue:str):
        if (message.from_user.is_self):
            await bot.edit_message_text(message.chat.id, message.id, issue)
        else:
            await bot.send_message(message.chat.id, issue)

    def download_tiktok_video(self, url, output_path='.') -> str:
        import yt_dlp
        import hashlib

        md5_hash = hashlib.md5()
        md5_hash.update(url.encode('utf-8'))
        filename = md5_hash.hexdigest()
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
        return filename + ".mp4"
        