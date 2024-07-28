from pyrogram import Client
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from pyrogram.errors.exceptions import AuthKeyUnregistered, SessionPasswordNeeded

from exceptions import PipelineNotImplementedException
from typing import List, Coroutine, Any
from datetime import datetime, timezone
import logging
import time
import os
import traceback

from abc import ABC, abstractmethod


'''
Main Sambot class
'''
class Sambot:
    bot: Client

    _pipelineSegments: 'List[BotPipelineSegmentBase]' = []
    _startTimeUtc: datetime

    '''
    Setup the logging. Print to console
    '''
    def _setupLogging(self):
        self.logger: logging.Logger = logging.getLogger('sambot')
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(ch)

    '''
    Constructor
    '''
    def __init__(self, bot: Client):
        self._setupLogging()
        self.bot = bot

    '''
    Constructor
    '''
    def __init__(self, api_id: int, api_hash: str, phone_number: str):
        self._setupLogging()
        self.bot = Client(
            name="sambot",
            api_id=api_id,
            api_hash=api_hash
        )
        
        try:
            self.bot.connect()
            self.bot.get_me()
            self.logger.info('Existing session valid')
        except (AuthKeyUnregistered):
            self.logger.info('Application not authorized yet. Starting 2FA sequence')
            self._authenticate2fa(phone_number=phone_number)
        
        self.bot.disconnect()

    '''
    Authenticate via 2FA. Works by checking for updates in a file for the code
    '''
    def _authenticate2fa(self, phone_number: str):
        codeSendInfo = self.bot.send_code(phone_number=phone_number)
        file_path = 'otp.code'

        self.logger.info(f'A code has been sent to your Telegram account. Please enter the code in the file {file_path}')
        otp_code = self._getOtpFileContents(file_path)

        self.logger.info(f'Code received {otp_code}')
        try:
            self.bot.sign_in(
                phone_number=phone_number,
                phone_code_hash=codeSendInfo.phone_code_hash,
                phone_code=otp_code
            )
            self.logger.info('Login complete. Yay!')
        except SessionPasswordNeeded:
            self.logger.warn(f'A password is needed. Please enter the password in the file {file_path}')
            password = self._getOtpFileContents(file_path=file_path)
            self.bot.check_password(password=password)
       
    '''
    Creates a file with the provided name, waits for it to get
    modified. And once its modified it will return the contents
    of the file
    '''
    def _getOtpFileContents(self, file_path) -> str:
        with open(file_path, "w") as file:
            pass
        initial_mod_time = os.path.getmtime(file_path)
        newcontent = ""
        while True:
            time.sleep(1) 
            current_mod_time = os.path.getmtime(file_path)
            if current_mod_time != initial_mod_time:
                with open(file_path, 'r') as file:
                    newcontent = file.read()
                break
        return newcontent

    '''
    Message handler
    '''
    async def _handleMessage(self, client: Client, message: Message):
        for segment in self._pipelineSegments:
            try:
                if await segment.CanHandle(self, MessageAdapter(message)):
                    self.logger.info(f'Segment accepted message {type(segment).__name__}')
                    await segment.ProcessMessage(self, message=MessageAdapter(message), bot=client)
            except Exception as ex:
                await client.send_message(
                    chat_id=message.chat.id,
                    text=f'Whoops. Something went wrong in the {type(segment).__name__} pipeline segment',
                    reply_to_message_id=message.reply_to_top_message_id)
                self.logger.error(f'Error in {type(segment).__name__} segment :\n{traceback.format_exc()}')

    '''
    Add a pipeline segment
    '''
    def AddPipelineSegment(self, segment):
        if not isinstance(segment, BotPipelineSegmentBase):
            raise PipelineNotImplementedException(f'The object {type(segment).__name__} does not implement the BotPipelineSegmentBase interface')
        self._pipelineSegments.append(segment)

    '''
    Add default segments
    '''
    def AddDefaultPipeLines(self):
        from default_segments import PingIndicator, TikTokDownloader, BackTrace, Autopilot
        from chatgpt import ChatGpt

        self.chatgpt= ChatGpt(
            username=os.getenv('CHATGPT_USERNAME'),
            password=os.getenv('CHATGPT_PASSWORD')
        )
        self.chatgpt.Login()
        self.AddPipelineSegment(PingIndicator())
        self.AddPipelineSegment(TikTokDownloader())
        self.AddPipelineSegment(BackTrace(self.chatgpt))
        # self.AddPipelineSegment(Autopilot(self.chatgpt))
        

    '''
    Start the bot
    '''
    def Start(self) -> None:
        handler = MessageHandler(self._handleMessage, filters=None)
        self.bot.add_handler(handler)
        self.logger.info("Ready. Awaiting messages!")
        self._startTimeUtc = datetime.now(timezone.utc)
        self.bot.run()

'''
Message adapter for pyrogram messages
'''
class MessageAdapter(Message):

    def __init__(self, msg: Message):
        self.__dict__ = msg.__dict__

    def IsTopicMessage(self):
        if self.reply_to_message:
            if not self.reply_to_message.text:
                return True
        return False
    
    '''
    Is this a real reply or is it a topic reply?
    '''
    def IsRealReply(self):
        if self.reply_to_message:
            if self.reply_to_message.text:
                return True
        return False

'''
This is the base class for pipeline segments
Everytime a message is received, all messages will
be passed 
'''
class BotPipelineSegmentBase(ABC):

    '''
    When a message is recieved, it will be passed to this
    method, if the message can be processed, this method should
    return true
    '''
    @abstractmethod
    async def CanHandle(self, sambot:Sambot, message:MessageAdapter):
        return False

    '''
    Process the message. 

    Returns: A flag that indicate if the pipeline should terminate
    '''
    @abstractmethod
    async def ProcessMessage(self, sambot:Sambot, bot:Client, message:MessageAdapter):
        pass

    