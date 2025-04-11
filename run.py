from sambot import Sambot
from dotenv import load_dotenv
import os
import memes
import time
import asyncio
import signal

load_dotenv()

if __name__ == '__main__':
    api_id=int(os.getenv("PYROGRAM_APIID"))
    api_hash=os.getenv("PYROGRAM_APIHASH")
    phone_number=os.getenv("PYROGRAM_PHONENUMBER")
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    if os.path.exists('terminate-lockfile'):
        print('Terminate lockfile exists. Stopping startup')
        while True:
            time.sleep(10)

    sammy = Sambot(
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone_number
    )
    sammy.AddDefaultPipeLines()
    signal.signal(signal.SIGINT, lambda: loop.stop())
    sammy.Start()
