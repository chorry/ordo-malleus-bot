from collections import Counter
from datetime import timedelta
from datetime import datetime
from datetime import date
import asyncio
import argparse
import logging
import logging.handlers
import os
import random
import re
import time
import urllib
import discord
import requests

from discord import Intents, Reaction
from discord.ext.commands import HelpCommand
from discord.ext import commands
from pythonjsonlogger import jsonlogger
import sentry_sdk
import yaml

# MAIN
# Load config
with open('.config', 'r', encoding="utf-8") as configfile:
    cfg = yaml.safe_load(configfile)

# Setup sentry.io reporting
sentry_dsn = cfg['debug']['sentry dsn']
sentry_app_name = cfg['debug']['sentry appname']
sentry_environment = cfg['debug']['sentry environment']
sentry_sdk.init(sentry_dsn, release=sentry_app_name, environment=sentry_environment)

# Enable debug for asyncio
os.environ['PYTHONASYNCIODEBUG'] = '1'

# Setup logging
logging_level = cfg['debug']['debug level']
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s: %(message)s')

handler = logging.handlers.RotatingFileHandler('comrade.log', mode='a', maxBytes=10485760, backupCount=0,
                                               encoding='utf-8')
handler.setLevel(logging_level)
handler.setFormatter(formatter)

logger = logging.getLogger("comrade")
logger.setLevel(logging_level)
logger.addHandler(handler)
logger.info('')
logger.info('Session started')

# Init and configure discord bot
discord_token = cfg['bot']['bot token']
discord_watched_channels = cfg['bot']['watched channels']
bot_admins = cfg['bot']['admin users']
target_image_channel = cfg['bot']['target channel']

intents = Intents().default()
intents.members = True
intents.reactions = True

client = commands.Bot(intents=intents, command_prefix="?")
copy_image_emoji = 'hothothot'
main_channel = ''

# TRIGGERS AND COMMANDS
@client.event
async def on_ready():
    print("checking guilds")
    for guild in client.guilds:
        print(
            f"{client.user} is connected to the following guild:\n"
            f"{guild.name}(id: {guild.id})"
        )

@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Gives a role based on a reaction emoji."""
    guild = client.get_guild(payload.guild_id)
    if guild is None:
        return

    if payload.emoji.name != copy_image_emoji:
        return

    print("Got emoji reaction")
    print(payload)

    source_msg = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
    print("fetched msg", source_msg, "content:", source_msg.content, "attaches:", source_msg.attachments)
    #we dont handle non-pics, or multi-pics (if any)
    if len(source_msg.attachments) != 1:
        return

    image_author = source_msg.author.nick

    #download file locally
    downloaded_file = requests.get(source_msg.attachments[0].url)
    print(downloaded_file)
    print(downloaded_file.headers.get('content-type'))

    image_dir =os.path.join(os.getcwd(), 'images')
    isExist = os.path.exists(image_dir)
    if not isExist:
        os.makedirs(image_dir)
    result_path = os.path.join(image_dir, str(source_msg.id) + '_' + source_msg.attachments[0].filename)
    print("Result path is ", result_path)
    open(result_path, 'wb').write(downloaded_file.content)

    #Send attachment to specific channel
    print ("Trying to reupload")
    target_channel = client.get_channel(target_image_channel)
    my_embed = discord.Embed(url=source_msg.attachments[0].url, description=source_msg.attachments[0].filename)

    upload_file = discord.File(result_path)
    print ("Sending new embed")
    print (my_embed.url)
    await target_channel.send(content=image_author + ' proudly presents, ' + payload.member.nick + ' approves', file=upload_file)


client.run(discord_token)
print("the end")
