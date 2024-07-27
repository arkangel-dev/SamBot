from pyrogram import Client
from pyrogram.handlers import MessageHandler

class Sambot:
    bot: Client

    def __init__(self, bot:Client):
        self.bot = bot

    def __init__(self):
        self.bot = Client("sambot")

    async def _handleMessage(self, client, message):
        pass

    def Start(self) -> None:
        handler = MessageHandler(self._handleMessage)
        self.bot.add_handler(handler)
        self.bot.run()