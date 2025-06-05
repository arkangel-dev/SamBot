### Adding new Segments

Make a new class that implements the interface `BotPipelineSegmentBase`. The `CanHandle` method will determine if the segment can handle the message based on the content, and the `ProcessMessage` will be executed if the `CanHandle` method returns true
```python
from pyrogram import Client
from pyrogram.types import Message
from sambot import BotPipelineSegmentBase, Sambot

# Pipeline segment that will execute if the message content is trigger-word
# Once executed, will send the message 'Response to trigger`
class ExamplePipeline(BotPipelineSegmentBase):
     def CanHandle(self, sambot: Sambot, message: Message):
        return message.text == ".trigger-word" 

     def ProcessMessage(self, sambot: Sambot, bot: Client, message: Message):
        bot.send_message(message.chat.id, "Response to trigger!")
```

Now, you can add this segment into the bot

```python
from sambot import Sambot
from dotenv import load_dotenv
from example import ExamplePipeline
import os

load_dotenv()

api_id=int(os.getenv("PYROGRAM_APIID"))
api_hash=os.getenv("PYROGRAM_APIHASH")
phone_number=os.getenv("PYROGRAM_PHONENUMBER")

sammy = Sambot(
    api_id=api_id,
    api_hash=api_hash,
    phone_number=phone_number
)
sammy.AddDefaultPipeLines()
sammy.AddPipelineSegment(ExamplePipeline()) # We are adding the new segment here
sammy.Start()
```