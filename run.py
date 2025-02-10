from sambot import Sambot
from dotenv import load_dotenv
import os
import memes
import time

load_dotenv()

if __name__ == '__main__':
    api_id=int(os.getenv("PYROGRAM_APIID"))
    api_hash=os.getenv("PYROGRAM_APIHASH")
    phone_number=os.getenv("PYROGRAM_PHONENUMBER")
    
    
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
    # memes.LoadIntoSambot(sammy)
    
    sammy.Start()
