from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors.exceptions import AuthKeyUnregistered, SessionPasswordNeeded
from pyrogram.enums import MessageEntityType
from exceptions import PipelineNotImplementedException
from typing import List, Coroutine, Any
from datetime import datetime, timezone
import logging
import time
import os
import traceback
import json
from utils import setup_logger

from abc import ABC, abstractmethod


class Sambot:
    '''
    Main Sambot class
    '''
    bot: Client

    _pipelineSegments: 'List[BotPipelineSegmentBase]' = []
    _startTimeUtc: datetime
    configuration: dict

    '''
    Setup the logging. Print to console
    '''
    def _setupLogging(self):
        self.logger: logging.Logger = logging.getLogger('sambot')
        setup_logger(self.logger)

    '''
    Constructor
    '''
    def __init__(self, bot: Client):
        self._setupLogging()
        self.bot = bot
        self.configuration = self._read_json("ext-mount/settings.json")

    '''
    Constructor
    '''
    def __init__(self, api_id: int, api_hash: str, phone_number: str):
        self._setupLogging()
        self.bot = Client(
            name="sambot",
            api_id=api_id,
            api_hash=api_hash,
            workdir="ext-mount"
        )
        self.configuration = self._read_json("ext-mount/settings.json")
        
        try:
            self.bot.connect()
            self.bot.get_me()
            self.logger.info('Existing session valid')
        except (AuthKeyUnregistered):
            self.logger.info('Application not authorized yet. Starting 2FA sequence')
            self._authenticate2fa(phone_number=phone_number)
        
        self.bot.disconnect()

    def SaveConfiguration(self):
        self._write_json("ext-mount/settings.json", self.configuration)

    def _read_json(self, file_path):
        """
        Reads a JSON file and returns the data as a Python object.
        
        :param file_path: Path to the JSON file.
        :return: Data read from the JSON file.
        """
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                return data
        except FileNotFoundError:
            print(f"The file at {file_path} was not found.")
        except json.JSONDecodeError:
            print(f"Error decoding JSON from the file at {file_path}.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def _write_json(self, file_path, data):
        """
        Writes a Python object to a JSON file.
        
        :param file_path: Path to the JSON file.
        :param data: Data to be written to the JSON file.
        """
        try:
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)
                print(f"Data successfully written to {file_path}.")
        except Exception as e:
            print(f"An error occurred: {e}")


    def _authenticate2fa(self, phone_number: str):
        '''
        Authenticate via 2FA. Works by checking for updates in a file for the code
        '''
        codeSendInfo = self.bot.send_code(phone_number=phone_number)
        file_path = 'ext-mount/otp.code'

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
       

    def _getOtpFileContents(self, file_path) -> str:
        '''
        Creates a file with the provided name, waits for it to get
        modified. And once its modified it will return the contents
        of the file
        '''
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

    
    def AddHandlers(self):
        '''
        Add all the handlers
        '''
        for segment in self._pipelineSegments:
            segment.RegisterSegment(self, self.bot)


    def AddPipelineSegment(self, segment):
        '''
        Add a pipeline segment
        '''
        self.logger.info(f'Registered segment ({type(segment).__name__})')
        if not isinstance(segment, BotPipelineSegmentBase):
            raise PipelineNotImplementedException(f'The object {type(segment).__name__} does not implement the BotPipelineSegmentBase interface')
        self._pipelineSegments.append(segment)

    
    def AddDefaultPipeLines(self):
        '''
        Add default segments
        '''
        import default_segments as ds
        self.AddPipelineSegment(ds.PingIndicator())
        self.AddPipelineSegment(ds.TikTokDownloader())
        self.AddPipelineSegment(ds.MentionEveryone())
        self.AddPipelineSegment(ds.TerminateSegment())
        self.AddPipelineSegment(ds.ReactionCounter())
        self.AddPipelineSegment(ds.WordCloudGenerator())
        self.AddPipelineSegment(ds.Life360Integration())
        self.AddPipelineSegment(ds.RemindMeLater())
        self.AddPipelineSegment(ds.TotalRecall())
        self.AddHandlers()
        
    def Start(self) -> None:
        '''
        Start the bot
        '''
        # messageHandler = MessageHandler(self._handleMessage, filters=None)
        # reactionHandler = 
        # self.bot.add_handler(messageHandler)
        self.logger.info("Ready. Awaiting messages!")
        self._startTimeUtc = datetime.now(timezone.utc)
        self.bot.run()

class MessageAdapter(Message):
    '''
    Message adapter for pyrogram messages
    '''

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
    
    async def GetMentionedUsers(self):
        if not self.entities: return []
        ids = []
        for entity in self.entities:
            if (entity.type == MessageEntityType.TEXT_MENTION):
                ids.append(entity.user.id)
                continue
            
            if (entity.type == MessageEntityType.MENTION):
                mentioned_username = self.text[entity.offset : entity.offset + entity.length]
                ids.append(mentioned_username)
        return ids
    
    async def GetMentionedUsersIds(self):
        if not self.entities: return []
        ids = []
        for entity in self.entities:
            if (entity.type == MessageEntityType.TEXT_MENTION):
                ids.append(entity.user.id)
                continue
            
            if (entity.type == MessageEntityType.MENTION):
                mentioned_username = self.text[entity.offset : entity.offset + entity.length]
                user = await self._client.get_users(mentioned_username)
                ids.append(user.id)
                continue
        return ids
    
    async def GetMessagePartsAndDeleteMessage(self) -> List[str]:
        await self.delete()
        if not self.text: return []
        return self.text.split()

class BotPipelineSegmentBase(ABC):    
    def RegisterSegment(self, sambot:Sambot, bot: Client):
        '''
        Register a this segment
        '''
        pass

    
