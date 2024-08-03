# SamBot 🤖

### Setup & Installation
Run the following commands to set the environment variables
```bash
export PYROGRAM_APIID=ENTER_YOUR_ID_HERE
export PYROGRAM_APIHASH=ENTER_YOUR_HASH_HERE
export PYROGRAM_PHONENUMBER=ENTEER_YOUR_PHONE_NUMBER_HERE
```

Once that is done, run `run.py` and that will attempt to login to your account. For first time use, it will trigger an OTP sequence where you will get a code to your telegram account or SMS. When this happens a blank file named `otp.code` will be generated. You can enter the otp code into this file and save it and that should be it.

You might be asking why I didn't just get the code via console. I can do whatever I want. Don't ask questions. But yeah no, its so I can mount the `otp.code` when this project is dockerized

## Settings
You need a `settings.json` file mounted to the docker container. Im sure you can figure that out yourself, because I can't be bothered to write the instructions here. Anyway the settings file should look like this

```json
{
    "mentioneveryone": {
        "allowed_chats": [
        ]
    }
}
```

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
