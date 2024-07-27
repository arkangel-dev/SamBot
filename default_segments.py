from pyrogram import Client
from pyrogram.types import Message
from typing import Coroutine
from datetime import datetime, timezone
from sambot import Sambot, BotPipelineSegmentBase

import time
import asyncio

'''
Segment to indicate if the bot is alive.

Activate by sending '.ping'
'''
class PingIndicator(BotPipelineSegmentBase):
    async def CanHandle(self, sambot: Sambot, message: Message):
        return message.text == '.ping'
        
    async def ProcessMessage(self, sambot: Sambot, bot: Client, message: Message):
        uptime = (datetime.now(timezone.utc) - sambot._startTimeUtc).total_seconds()
        await bot.edit_message_text(message.chat.id, message.id, f"Online. I've been up for {int(uptime)} seconds now. Uptime was at {sambot._startTimeUtc}")
        await asyncio.sleep(3)
        await bot.delete_messages(chat_id=message.chat.id, message_ids=[message.id])
