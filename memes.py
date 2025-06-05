import PIL.Image
import PIL.ImageChops
from pyrogram import Client
from typing import  BinaryIO
from sambot import Sambot, BotPipelineSegmentBase, MessageAdapter
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import PIL
import io

def LoadIntoSambot(bot: Sambot):
    bot.AddPipelineSegment(Memes_Aliens())
    bot.AddPipelineSegment(Memes_ToyStory())
    bot.AddPipelineSegment(Memes_HumanDisaster())
    bot.AddPipelineSegment(Memes_Simply())
    bot.AddPipelineSegment(Memes_Detroit())

class Memes_Aliens(BotPipelineSegmentBase):
    """
    History.com's Aliens guy
    More : https://knowyourmeme.com/memes/ancient-aliens
    """
    async def CanHandle(self, sambot: Sambot, message: MessageAdapter):
        if not message.text: return
        if not message.from_user.is_self: return
        return message.text.split()[0] == '.aliens'
    
    async def ProcessMessage(self, sambot: Sambot, bot: Client, message: MessageAdapter):
        await message.delete()
        image =  _memeGenerator.HistoryAliensGuy(message.text[8:] if len(message.text) > 8 else "ALIENS")
        await bot.send_photo(
                chat_id=message.chat.id,
                reply_to_message_id=message.reply_to_message_id or message.reply_to_top_message_id,
                photo=image
            )
        
class Memes_ToyStory(BotPipelineSegmentBase):
    """
    The "one does not simply" meme from Lord of the Rings. 
    More : https://knowyourmeme.com/memes/one-does-not-simply-walk-into-mordor
    """
    async def CanHandle(self, sambot: Sambot, message: MessageAdapter):
        if not message.text: return
        if not message.from_user.is_self: return
        return message.text.split()[0] == '.toystory'
    
    async def ProcessMessage(self, sambot: Sambot, bot: Client, message: MessageAdapter):
        await message.delete()
        image =  _memeGenerator.ToyStoryMeme(message.text[9:] if len(message.text) > 9 else "MEMES")
        await bot.send_photo(
                chat_id=message.chat.id,
                reply_to_message_id=message.reply_to_message_id or message.reply_to_top_message_id,
                photo=image
            )
        
class Memes_HumanDisaster(BotPipelineSegmentBase):
    async def CanHandle(self, sambot: Sambot, message: MessageAdapter):
        if not message.text: return
        if not message.from_user.is_self: return
        return message.text.split()[0] == '.hd'
    
    async def ProcessMessage(self, sambot: Sambot, bot: Client, message: MessageAdapter):
        await message.delete()
        image =  _memeGenerator.HumanDisaster(message.text[3:])
        await bot.send_photo(
                chat_id=message.chat.id,
                reply_to_message_id=message.reply_to_message_id or message.reply_to_top_message_id,
                photo=image
            )
        
class Memes_Simply(BotPipelineSegmentBase):
    async def CanHandle(self, sambot: Sambot, message: MessageAdapter):
        if not message.text: return
        if not message.from_user.is_self: return
        return message.text.split()[0] == '.simply'
    
    async def ProcessMessage(self, sambot: Sambot, bot: Client, message: MessageAdapter):
        await message.delete()
        image = _memeGenerator.OneDoesNotSimply(message.text[7:])
        await bot.send_photo(
                chat_id=message.chat.id,
                reply_to_message_id=message.reply_to_message_id or message.reply_to_top_message_id,
                photo=image
            )

class Memes_Detroit(BotPipelineSegmentBase):
    async def CanHandle(self, sambot: Sambot, message: MessageAdapter):
        if not message.text: return
        if not message.from_user.is_self: return
        return message.text == '.detroit'
    
    async def ProcessMessage(self, sambot: Sambot, bot: Client, message: MessageAdapter):
        if not message.reply_to_message or not message.reply_to_message.media:
            await message.edit_text(text="Sam, You need to reply to a message with an image")
            return
        
        await message.edit_text(text="Hold on")
        dl_img = await bot.download_media(message.reply_to_message, in_memory=True)
        return_img = _memeGenerator.DetroitMeme(dl_img)
        await bot.send_photo(
                chat_id=message.chat.id,
                reply_to_message_id=message.reply_to_message_id or message.reply_to_top_message_id,
                photo=return_img
            )
        await message.delete()

class _memeGenerator:
    def _drawTextWithOutline(draw, text, x, y, fsize):
        draw.text((x-2, y-2), text,(0,0,0),font=fsize)
        draw.text((x+2, y-2), text,(0,0,0),font=fsize)
        draw.text((x+2, y+2), text,(0,0,0),font=fsize)
        draw.text((x-2, y+2), text,(0,0,0),font=fsize)
        draw.text((x, y), text, (255,255,255), font=fsize)
        return

    def _drawText(draw, text, x, y, fsize):
        draw.text((x, y), text, (255,255,255), font=fsize)
        return

    def _average_colour(image):
        colour_tuple = [None, None, None]
        for channel in range(3):
            # Get data for one channel at a time
            pixels = image.getdata(band=channel)
            values = []
            for pixel in pixels:
                values.append(pixel)
            colour_tuple[channel] = sum(values) / len(values)
        return tuple(colour_tuple)

    def OneDoesNotSimply(text) -> BinaryIO:

        img = Image.open("static/one-does-not-simply.jpg")
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("static/impact.ttf", 42)
        w = draw.textlength(text, font)
        _memeGenerator._drawTextWithOutline(draw,text, img.width/2 - w/2, 280, font)
        output = io.BytesIO()
        img.save(output, format='JPEG')
        return output

    def HumanDisaster(text) -> BinaryIO:
        img = Image.open("static/human-disaster.png")
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("static/impact.ttf", 42)
        w = draw.textlength(text, font)
        _memeGenerator._drawText(draw,text, img.width/2 - w/2, 570, font)
        output = io.BytesIO()
        img.save(output, format='JPEG')
        return output

    def HistoryAliensGuy(text) -> BinaryIO:

        img = Image.open("static/history-aliens.jpg")
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("static/impact.ttf", 50)
        w = draw.textlength(text, font)
        _memeGenerator._drawTextWithOutline(draw,text, img.width/2 - w/2, 377, font)
        output = io.BytesIO()
        img.save(output, format='JPEG')
        return output

    def ToyStoryMeme(text) -> BinaryIO:
        img = Image.open("static/woody-buzz.jpg")
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("static/impact.ttf", 45)
        w = draw.textlength(text, font)
        w1 = draw.textlength(text + " Everywhere", font)
        _memeGenerator._drawTextWithOutline(draw,str(text).capitalize(), img.width/2 - w/2, 2, font)
        _memeGenerator._drawTextWithOutline(draw,str(text).capitalize() + " Everywhere", img.width/2 - w1/2, 250, font)
        output = io.BytesIO()
        img.save(output, format='JPEG')
        return output

    def DetroitMeme(image:BinaryIO) -> BinaryIO:
        img = Image.open(image)
        img = Image.open("static/dbh-painting-meme.png")
        background = Image.open(image)
        size = (2560,1600)
        small_image = (920,1150)
        edited_image = background
        edited_image = edited_image.resize(size,)
        scaled_image = background.resize(small_image, PIL.Image.Resampling.LANCZOS)
        edited_image = Image.new("RGBA", (2560,1600), "#F00")
        scaled_image = scaled_image.convert('RGBA')
        scaled_image = scaled_image.rotate(4, expand=1 ).resize(small_image)
        edited_image.paste(scaled_image, (845, 248),scaled_image)
        edited_image.paste(img, (0,0), img)
        output = io.BytesIO()
        edited_image.save(output, format='PNG')
        return output