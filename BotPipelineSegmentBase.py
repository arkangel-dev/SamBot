from abc import ABC, abstractmethod
from pyrogram import Client
from pyrogram.types import Message

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
    def CanHandle(self, message:Message) -> bool:
        pass

    '''
    Process the message
    '''
    @abstractmethod
    def ProcessMessage(self, bot:Client, message:Message) -> None:
        pass