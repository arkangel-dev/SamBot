from sambot import Sambot
from dotenv import load_dotenv
import os

load_dotenv()

if __name__ == '__main__':
    api_id=int(os.getenv("PYROGRAM_APIID"))
    api_hash=os.getenv("PYROGRAM_APIHASH")
    phone_number=os.getenv("PYROGRAM_PHONENUMBER")

    sammy = Sambot(
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone_number
    )
    sammy.AddDefaultPipeLines()
    sammy.Start()
