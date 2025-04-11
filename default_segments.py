from pyrogram import Client
from pyrogram.types import Message, InputMediaVideo
from pyrogram.enums import ParseMode
from datetime import datetime, timezone, timedelta
from sambot import Sambot, BotPipelineSegmentBase, MessageAdapter
from pyrogram.handlers import MessageHandler
from wordcloud import WordCloud
import asyncio
import re
from io import BytesIO
import random
from PyL360 import L360Client
import os
class PingIndicator(BotPipelineSegmentBase):
    '''
    Segment to indicate if the bot is alive. It will send a message with uptime duration

    Activate by sending '.ping'
    '''
    def CanHandle(self, message: Message):
        if not message.text: return False
        return message.text == '.ping' and message.from_user.is_self
        
    async def ProcessMessage(self, bot: Client, message: Message):
        if (not self.CanHandle(message)): return
        uptime = (datetime.now(timezone.utc) - self.sambot._startTimeUtc).total_seconds()
        await bot.edit_message_text(message.chat.id, message.id, f"Online. I've been up for {int(uptime)} seconds now. Uptime was at {self.sambot._startTimeUtc}")
        await asyncio.sleep(3)
        await bot.delete_messages(chat_id=message.chat.id, message_ids=[message.id])
        
    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.ProcessMessage)
        bot.add_handler(handler, group=1001)
        # return await super().RegisterSegment(sambot, bot)

class TikTokDownloader(BotPipelineSegmentBase):
    '''
    Segment to download TikTok and Youtube videos

    Activate it by replying the command '.dl' to a message that contains a URL to a video
    '''
    
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|'
        r'(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    
    issue_messages = [
        "One second"
        "Something went wrong. Let me try again...",
        "Third times the charm! (Updating YT-DLP)",
        "Uhhh... just one second"
    ]
    
    invalid_operation_messages = [
        "You need to reply with a link!",
        "Where's the link?",
        "What do you want me to download? Reply to a message with a link!",
        "Im gonna need a link"
    ]
    
    def can_download(self, message: Message):
        if not message.text: return False
        return message.text == '.dl'
    
    def can_ban(self, message: Message):
        if not message.reply_to_message: return False
        if not message.from_user.is_self: return False
        return message.text == '.ban_dl'
    
    def can_unban(self, message: Message):
        if not message.reply_to_message: return False
        if not message.from_user.is_self: return False
        return message.text == '.unban_dl'
    
    async def ban_user(self, message: Message):
        if message.reply_to_message.from_user.id in self.sambot.configuration["tiktok_dl"]["banned_users"]:
            await message.edit_text("This guy is already banned")
            return
        self.sambot.configuration["tiktok_dl"]["banned_users"].append(message.reply_to_message.from_user.id)
        self.sambot.SaveConfiguration()
        await message.edit_text("This fool has been banned!")
        
    async def unban_user(self, message: Message):
        if not message.reply_to_message.from_user.id in self.sambot.configuration["tiktok_dl"]["banned_users"]:
            await message.edit_text("This guy was not banned")
            return
        self.sambot.configuration["tiktok_dl"]["banned_users"].remove(message.reply_to_message.from_user.id)
        self.sambot.SaveConfiguration()
        await message.edit_text("This fool has been unbanned!")
        
        
    def update_and_reimport_yt_dlp(self):
        import subprocess
        import importlib
        import sys
        try:
            # Install or update yt-dlp using pip
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
            
            # Import or reload yt-dlp to get the latest version
            import yt_dlp
            importlib.reload(yt_dlp)
            print("yt-dlp has been updated and re-imported successfully.")
            
            return yt_dlp  # Return the module if needed
        except Exception as e:
            print(f"An error occurred: {e}")
        
    async def process_message(self, bot: Client, message: Message):
        message = MessageAdapter(message)
        
        if not message.text: return False # Check if its a text message
        
        if self.can_ban(message): # Check if its a message to ban users
            await self.ban_user(message)
            return
        
        if self.can_unban(message): # Check if its a message to unban users
            await self.unban_user(message)
            return
        
        if not self.can_download(message): return # If its not a module related message, ignore it
        
        # If the fool is banned, react to the origin
        # message with the bird
        if message.from_user.id in self.sambot.configuration["tiktok_dl"]["banned_users"]:
            await message.react("🖕")
            return
        
        if not message.IsRealReply():
            await self.reply_with_issue(bot, message, random.choice(self.invalid_operation_messages))
            return
        
        url_match = re.search(self.url_pattern, message.reply_to_message.text)
        if not url_match:
            await self.reply_with_issue(bot, message, "You need to reply to a message with a url, and no url was detected in this message!")
            return

        status_msg:Message = await self.reply_with_issue(bot, message, 'One sec. Downloading the file...')
        try_count = 0
        
        while (True):
            try:
                file = self.download_tiktok_video(url_match.string, reloadlib=try_count > 2)
                await bot.send_media_group(
                    media=[InputMediaVideo(file, caption="Here you go!")],
                    chat_id=message.chat.id, 
                    reply_to_message_id=message.reply_to_message_id)
                if status_msg:
                    await bot.delete_messages(status_msg.chat.id, message_ids=[status_msg.id])
                return
            except Exception as e:
                if (try_count == 2):
                    self.update_and_reimport_yt_dlp()
                
                if (try_count < 3):
                    await status_msg.edit_text(self.issue_messages[try_count])
                else:
                    await status_msg.edit_text("Yeah no, I give up, this can't be downloaded. I have failed. I failed and let down my entire clan")
                    break
                try_count += 1
    
    async def reply_with_issue(self, bot:Client, message:MessageAdapter, issue:str):
        if (message.from_user.is_self):
            return await bot.edit_message_text(message.chat.id, message.id, issue)
        else:
            return await bot.send_message(
                chat_id=message.chat.id,
                text=issue,
                reply_to_message_id=message.reply_to_top_message_id)

    def download_tiktok_video(self, url, output_path='ext-mount/cache/', reloadlib:bool = False) -> str:
        import yt_dlp
        import hashlib
        import os
        import importlib

        if reloadlib: importlib.reload(yt_dlp)
        md5_hash = hashlib.md5()
        md5_hash.update(url.encode('utf-8'))
        filename = md5_hash.hexdigest()

        if os.path.exists(f'{output_path}/{filename}.mp4'):
            return f'{output_path}/{filename}.mp4'

        ydl_opts = {
            'outtmpl': f'{output_path}/{filename}.%(ext)s',
            'format': 'best',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',  # Convert to mp4 if needed
            }]
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return f'{output_path}/{filename}.mp4'
      
    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message)
        bot.add_handler(handler, group=1002)
        # return super().RegisterSegment(sambot, bot)

class MentionEveryone(BotPipelineSegmentBase):
    '''
    Mention everyone in the chat when @everyone is mentioned
    '''

    async def can_handle(self, message: MessageAdapter):
        if not message.text: return False
        if not message.chat.id in self.sambot.configuration["mentioneveryone"]["allowed_chats"]: return False
        return '@everyone' in (await message.GetMentionedUsers())
    
    def can_handle_config(self, message: Message):
        if (not message.from_user.is_self): return False
        return ' '.join(message.text.split()[:2]) == ".config mentioneveryone"
    
    async def handle_config_instruction(self, bot:Client, message:Message):
        parts = message.text.split()

        if (len(parts) == 2):
            parts.append('')

        if (parts[2] == 'add'):
            self.sambot.configuration['mentioneveryone']['allowed_chats'].append(message.chat.id)
        elif (parts[2] == 'remove'):
            self.sambot.configuration['mentioneveryone']['allowed_chats'].append(message.chat.id)
        else:
            await bot.send_message(
                chat_id=message.chat.id,
                text="Uknown command. Please use .config everyone_mention add|remove",
                reply_to_message_id=message.id
            )
            return
        
        await bot.send_message(
                chat_id=message.chat.id,
                text=f"Changes made",
                reply_to_message_id=message.id
            )
        self.sambot.SaveConfiguration()
        return
    
    async def process_message(self, bot: Client, message: MessageAdapter):
        message = MessageAdapter(message)
        if not message.text: return
        if (not await self.can_handle(message)): 
            if self.can_handle_config(message):
                await self.handle_config_instruction(bot, message)
                return
            else:
                return
        mentioned_users = []
        async for user in bot.get_chat_members(message.chat.id):
            mentioned_users.append(f"[{user.user.first_name}](tg://user?id={user.user.id})")
        await bot.send_message(
            chat_id=message.chat.id,
            text=' '.join(mentioned_users),
            reply_to_message_id=message.id
        )
        
    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message)
        bot.add_handler(handler, 1003)
        return super().RegisterSegment(sambot, bot)

class TerminateSegment(BotPipelineSegmentBase):
    async def can_handle(self, message: MessageAdapter):
        if not message.text: return
        if not message.from_user.is_self: return
        return message.text == ".terminate"
    
    async def process_message(self, bot: Client, message: MessageAdapter):
        if (not await self.can_handle(message)): return
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"`Terminating self... Good bye...`",
            reply_to_message_id=message.id,
            parse_mode=ParseMode.MARKDOWN
        )
        await asyncio.create_task(bot.stop(False))
        exit()
        
    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message)
        bot.add_handler(handler, 1004)

class ReactionCounter(BotPipelineSegmentBase):
    def can_handle(self, message: MessageAdapter):
        if not message.text: return
        return message.text == ".leaderboard" and message.from_user.is_self
    
    async def process_message(self, bot: Client, message: MessageAdapter):
        if (not self.can_handle(message)): return
        start_date = datetime.today() - timedelta(days=1)
        reactions_dict = dict()
        messages_count_dict = dict()
        # Fetch messages from the chat
        async for msg in bot.get_chat_history(message.chat.id):
            # Check if message date is within the last n days
            if msg.date >= start_date:
                if not msg.from_user: continue
                key = msg.from_user.first_name
                
                if (msg.text):
                    # if its a text message, increment the dictionary.key with the number
                    # of words (split string with white space)
                    messages_count_dict[key] = messages_count_dict.get(key, 0) + len(msg.text.split(' '))
                else:
                    # otherwise just increment by one
                    messages_count_dict[key] = messages_count_dict.get(key, 0) + 1
                
                if (msg.reactions is None): continue
                count = sum(r.count for r in msg.reactions.reactions)
                reactions_dict[key] = reactions_dict.get(key, 0) + count 
                
            else:
                break  # Stop if messages are older than start_date
        
        reactions_dict = {k: v for k, v in sorted(reactions_dict.items(), key=lambda item: item[1],reverse=True)}
        messages_count_dict = {k: v for k, v in sorted(messages_count_dict.items(), key=lambda item: item[1],reverse=True)}
        
        reply_message = "**Reactions Leaderboard ✨**\n"
        reply_message += '\n'.join(['- {} : {}'.format(x, reactions_dict[x]) for x in reactions_dict])
        reply_message += "\n\n**Yappin Leaderboard 🗣️**\n"
        reply_message += '\n'.join(['- {} : {}'.format(x, messages_count_dict[x]) for x in messages_count_dict])
        await message.reply_text(reply_message)
        
        
    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message)
        bot.add_handler(handler, 1005)
        
class WordCloudGenerator(BotPipelineSegmentBase):
    def can_handle(self, message: MessageAdapter):
        if not message.text: return
        return message.text == ".wordcloud" and message.from_user.is_self
    
    async def process_message(self, bot: Client, message: MessageAdapter):
        if (not self.can_handle(message)): return
        start_date = datetime.today() - timedelta(days=1)
        messages_list = []
        # Fetch messages from the chat
        async for msg in bot.get_chat_history(message.chat.id):
            # Check if message date is within the last n days
            if msg.date >= start_date:
                if (not msg.text): continue
                messages_list.append(msg.text)
            else:
                break  # Stop if messages are older than start_date
        
        joined = ' '.join(messages_list)
        wordcloud = WordCloud(width=2000,height=2000).generate(joined).to_image()
        
        binary_io = BytesIO()
        
        wordcloud.save(binary_io, format="PNG")  # Save the image to the BytesIO object
        binary_io.seek(0)
        await bot.send_photo(
                chat_id=message.chat.id,
                reply_to_message_id=message.reply_to_message_id or message.reply_to_top_message_id,
                photo=binary_io
            )
        
    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message)
        bot.add_handler(handler, 1006)
        
class WhoIsNoora(BotPipelineSegmentBase):
    pass

class Life360Integration(BotPipelineSegmentBase):
    
    def __init__(self):
        self.l360_client = L360Client(
            username=os.getenv("Life360_Username"),
            password=os.getenv("Life360_Password"),
        )
        self.l360_client.Authenticate()
    
    async def process_message(self, bot: Client, message: MessageAdapter):
        message = MessageAdapter(message)
        if not message.text: return
        if message.text.split()[0] == '.whereis': await self.HandleQuery(bot, message)
        if not message.from_user.is_self: return
        if ' '.join(message.text.split()[:2]) == ".config whereis": await self.HandleConfiguration(bot, message)
        
    async def HandleQuery(self, bot: Client, message: MessageAdapter):
        # if not message.IsRealReply():
        #     await message.reply_text("You need to reply to a user for this to work...")
        #     return
        # user_id = str(message.reply_to_message.from_user.id)
        
        mentioned_users = await message.GetMentionedUsersIds()
        if len(mentioned_users) != 1:
            await message.reply_text("You need to mention one user like `.whereis @sammy`", parse_mode=ParseMode.MARKDOWN)
            return
        user_id = str(mentioned_users[0])
        
        assignments = self.sambot.configuration["L360"]["Assignments"]

        if not user_id in assignments:
            await message.reply_text("`No L360 profile is assigned to this user`", parse_mode=ParseMode.MARKDOWN)
            return
        
        
        l360_entry = assignments[user_id].split('/')
        l360_user = l360_entry[1]
        l360_circle = l360_entry[0]
        
        reply_msg = await message.reply_text("`Asking Life360...`", parse_mode=ParseMode.MARKDOWN)
        available_circles = self.l360_client.GetCircles()
        circle = next((x for x in available_circles.circles if x.name == l360_circle), None)
        
        if not circle:
            await message.reply_text("The circle `{}` was not found on my Life360 account".format(l360_circle), parse_mode=ParseMode.MARKDOWN)
            return
        
        circle_members_list = circle.GetDetails().members
        circle_member = next((x for x in circle_members_list if x.firstName == l360_user), None)
        
        if not circle_member:
            await message.reply_text("The user `{}` was not found in `{}`".format(l360_user, l360_circle), parse_mode=ParseMode.MARKDOWN)
            return
        
        await asyncio.sleep(1)
        await reply_msg.delete()
        
        summary_data = "{} is at {}".format(
            circle_member.firstName,
            circle_member.location.name or circle_member.location.shortAddress
        )
        summary_msg = await message.reply_text(summary_data)
        await summary_msg.reply_location(
            latitude=float(circle_member.location.latitude),
            longitude=float(circle_member.location.longitude),
        )
        
    async def HandleConfiguration(self, bot: Client, message: MessageAdapter):
        message_parts = message.text.split()
        if len(message_parts) < 3:
            await message.edit_text("`Invalid command\nsetuser - Link a user to a L360 user`", parse_mode=ParseMode.MARKDOWN)
            return
        
        match message_parts[2]:
            case "setuser":
                if not message.IsRealReply(): 
                    await message.edit_text("`You need to reply to a user for this command`", parse_mode=ParseMode.MARKDOWN)
                    return
                l360User = ' '.join(message_parts[3:])
                self.sambot.configuration["L360"]["Assignments"][str(message.reply_to_message.from_user.id)] = l360User
                self.sambot.SaveConfiguration()
                await message.react("👍")
                
            case "unsetuser":
                if not message.IsRealReply(): 
                    await message.reply_text("`You need to reply to a user for this command`", parse_mode=ParseMode.MARKDOWN)
                    return
                
                if not str(message.reply_to_message.from_user.id) in self.sambot.configuration["L360"]["Assignments"]:
                    await message.reply_text("`This user is not configured`", parse_mode=ParseMode.MARKDOWN)
                    return
                
                del self.sambot.configuration["L360"]["Assignments"][str(message.reply_to_message.from_user.id)]
                self.sambot.SaveConfiguration()
                await message.react("👍")
            
            case default:
                await message.edit_text("`Invalid command`", parse_mode=ParseMode.MARKDOWN)
    
    def RegisterSegment(self, sambot: Sambot, bot: Client):
        self.sambot = sambot
        handler = MessageHandler(self.process_message)
        bot.add_handler(handler, 1007)

