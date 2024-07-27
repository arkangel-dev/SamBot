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
sammy.AddPipelineSegment(ExamplePipeline())
sammy.Start()