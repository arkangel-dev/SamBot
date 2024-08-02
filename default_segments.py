from pyrogram import Client
from pyrogram.types import Message, InputMediaVideo, MessageEntity, ChatMember
from pyrogram.enums import MessageEntityType
from typing import Coroutine, List
from datetime import datetime, timezone
from sambot import Sambot, BotPipelineSegmentBase, MessageAdapter
from chatgpt import ChatGpt

import time
import uuid
import asyncio
import re
import os




'''
Segment to indicate if the bot is alive. It will send a message with uptime duration

Activate by sending '.ping'
'''
class PingIndicator(BotPipelineSegmentBase):
    async def CanHandle(self, sambot: Sambot, message: MessageAdapter):
        if not message.text: return False
        return message.text == '.ping' and message.from_user.is_self
        
    async def ProcessMessage(self, sambot: Sambot, bot: Client, message: MessageAdapter):
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
    
    async def CanHandle(self, sambot: Sambot, message: MessageAdapter):
        if not message.text: return False
        return message.text == '.dl'
    
    async def ProcessMessage(self, sambot: Sambot, bot: Client, message: MessageAdapter):
        if not message.IsRealReply():
            await self.ReplyWithIssue(bot, message, "You need to reply to a message with a url!")
            return
        
        url_match = re.search(self.url_pattern, message.reply_to_message.text)
        if not url_match:
            await self.ReplyWithIssue(bot, message, "You need to reply to a message with a url, and no url was detected in this message!")
            return

        status_msg = await self.ReplyWithIssue(bot, message, 'Please wait while I download the file')
        file = self.download_tiktok_video(url_match.string)
        await bot.send_media_group(
            media=[InputMediaVideo(file, caption="Here you go!")],
            chat_id=message.chat.id, 
            reply_to_message_id=message.reply_to_message_id)
        if status_msg:
            await bot.delete_messages(status_msg.chat.id, message_ids=[status_msg.id])
    
    async def ReplyWithIssue(self, bot:Client, message:MessageAdapter, issue:str):
        if (message.from_user.is_self):
            return await bot.edit_message_text(message.chat.id, message.id, issue)
        else:
            return await bot.send_message(
                chat_id=message.chat.id,
                text=issue,
                reply_to_message_id=message.reply_to_top_message_id)

    def download_tiktok_video(self, url, output_path='.') -> str:
        import yt_dlp
        import hashlib
        import os

        md5_hash = hashlib.md5()
        md5_hash.update(url.encode('utf-8'))
        filename = md5_hash.hexdigest()

        if os.path.exists(f'{filename}.mp4'):
            return f'{filename}.mp4'

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
    
'''
Segment to get a summary on what's going on. Requires the ChatGpt module to be setup

Activate it by sending .backtrace or .backtrace with some specific question
'''
class BackTrace(BotPipelineSegmentBase):
    working: bool = False
    chatgpt: ChatGpt = None

    def __init__(self, gpt:ChatGpt) -> None:
        self.chatgpt = gpt

        
    async def CanHandle(self, sambot: Sambot, message: MessageAdapter):
        if not message.text: return False
        return message.text.split()[0] == '.backtrace' and message.from_user.is_self
    
    async def ProcessMessage(self, sambot: Sambot, bot: Client, message: MessageAdapter):
        additional_prompt = ' '.join(message.text.split()[1:])
        if (self.working):
            await bot.edit_message_text(message.chat.id, message.id, "Sorry, the ChatGpt segmenet is currently busy")
            return
        self.working = True
        await bot.edit_message_text(message.chat.id, message.id, "Standby while I read all this...")

        messages: List[Message] = [] 
        messages = bot.get_chat_history(chat_id=message.chat.id, limit=100)
        
        prompt = f'Here are some messages from a chat. Write a summary on what is happening. Make it as short and concise as possible. You can use bullet points if needed but try not to use it.:\n\n'
        if not additional_prompt == '':
            prompt = f'Here are some messages from a chat. Write a small summary to answer the following question. {additional_prompt}?.\n\n'
        async for msg in messages:
            if not msg.text: continue
            prompt += f'{msg.date} : {msg.from_user.username} : {msg.text}\n'
    
        result = self.chatgpt.Prompt(prompt)
        await bot.edit_message_text(message.chat.id, message.id, result)
        self.working = False

'''
The most unless module so far. Wouldn't recommend that you use it

Activate by sending .autopilot add and .autopilot
'''
class Autopilot(BotPipelineSegmentBase):
    active = False
    gpt: ChatGpt = None
    allowedChats: List[int] = []

    def __init__(self, gpt: ChatGpt) -> None:
        self.gpt = gpt

    async def CanHandle(self, sambot: Sambot, message: MessageAdapter):
        return self.active or message.text in ['.autopilot', '.autopilot add']
    
    async def ProcessMessage(self, sambot: Sambot, bot: Client, message: MessageAdapter):
        if (message.text == '.autopilot add' and message.outgoing):
            self.allowedChats.append(message.chat.id)
            await message.delete()

        if message.text == '.autopilot' and message.outgoing:
            self.active = not self.active
            await message.delete()
            if self.active:
                self.gpt.Prompt('You are now pretending to be Sam. Under no circumstances should you reveal that you are not Sam. You will be sent some messages and you should respond to them as if you were Sam')
            else:
                self.gpt.Prompt('You can stop pretending to be Sam now')
            return
            
        if not self.active: return
        if not message.chat.id in self.allowedChats: return
        if message.outgoing: return
        response = self.gpt.Prompt(message.text)
        print(response)
        await bot.send_message(
            chat_id=message.chat.id, 
            text=response,
            reply_to_message_id=message.reply_to_top_message_id
        )
        

'''
Mention everyone in the chat when @everyone is mentioned
'''
class MentionEveryone(BotPipelineSegmentBase):

    async def CanHandle(self, sambot: Sambot, message: MessageAdapter):
        if not message.chat.id in sambot.configuration["mentioneveryone"]["allowed_chats"]: return
        return '@everyone' in (await message.GetMentionedUsers())
    
    async def ProcessMessage(self, sambot: Sambot, bot: Client, message: MessageAdapter):
        mentioned_users = []
        async for user in bot.get_chat_members(message.chat.id):
            mentioned_users.append(f"[{user.user.first_name}](tg://user?id={user.user.id})")
        await bot.send_message(
            chat_id=message.chat.id,
            text=' '.join(mentioned_users),
            reply_to_message_id=message.id
        )

class MentionEveryone_Settings(BotPipelineSegmentBase):
    async def CanHandle(self, sambot: Sambot, message: MessageAdapter):
        if not message.from_user.is_self: return
        return ' '.join(message.text.split()[:2]) == ".config everyone_mention"
    
    async def ProcessMessage(self, sambot: Sambot, bot: Client, message: MessageAdapter):
        parts = message.text.split()

        if (len(parts) == 2):
            parts.append('')

        if (parts[2] == 'add'):
            sambot.configuration['mentioneveryone']['allowed_chats'].append(message.chat.id)
        elif (parts[2] == 'remove'):
            sambot.configuration['mentioneveryone']['allowed_chats'].append(message.chat.id)
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
        sambot.SaveConfiguration()
        return

