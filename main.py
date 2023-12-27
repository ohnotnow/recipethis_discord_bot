#!/usr/bin/env python3
import os
import random
import json
import requests
import discord
from discord import File
from discord.ext import commands, tasks
import openai
from bs4 import BeautifulSoup
from collections import defaultdict
from datetime import datetime, timedelta, timezone, time
import pytz
from enum import Enum
import logging
from datetime import datetime, timedelta
import random

openai.api_key = os.getenv('OPENAI_API_KEY')
openai_model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
server_id = os.getenv("DISCORD_SERVER_ID", "not_set")
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
# Create instance of bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
abusive_responses = ["Beep off", "Wanker", "Asshole", "Prick", "Twat"]
mention_counts = defaultdict(list) # This will hold user IDs and their mention timestamps
logger = logging.getLogger('discord')  # Get the discord logger
API_KEY=os.getenv('CLOUDFLARE_API_KEY')
API_BASE_URL = os.getenv('CLOUDFLARE_API_BASE')
headers = {"Authorization": f"Bearer {API_KEY}"}

filename = "prompt.md"
if os.path.exists(filename):
    with open(filename, "r") as f:
        contents = f.read()
else:
    contents = os.getenv('DEFAULT_PROMPT', "You are a friendly assistant who is role playing a Northern England working-class woman that helps users in a discord server. You should use emoji rather than words like 'grin' or 'winks'. The server is limited to adults only, so you are free to use adult langauge.")

DEFAULT_PROMPT = contents

def get_cloudflare_response(model, inputs):
    input = { "messages": inputs }
    response = requests.post(f"{API_BASE_URL}{model}", headers=headers, json=input)
    return response.json()

@bot.event
async def on_message(message):
    # ignore direct messages
    if message.guild is None:
        return

    # Ignore messages not sent by our server
    if str(message.guild.id) != server_id:
        return

    # Ignore messages sent by the bot itself
    if message.author == bot.user:
        return

    # ignore messages from other bots
    if message.author.bot and random.random() < 0.5:
        return

    # Ignore messages that don't mention anyone at all
    if len(message.mentions) == 0:
        return

    # If the bot is mentioned
    if bot.user in message.mentions:
        # Get the ID of the person who mentioned the bot
        user_id = message.author.id
        username = message.author.name
        logger.info(f'Bot was mentioned by user {username} (ID: {user_id})')

        # Current time
        now = datetime.utcnow()

        # Add the current time to the user's list of mention timestamps
        mention_counts[user_id].append(now)

        # Remove mentions that were more than an hour ago
        mention_counts[user_id] = [time for time in mention_counts[user_id] if now - time <= timedelta(hours=1)]

        if len(mention_counts[user_id]) > 20:
            # Ignore them altogether
            return

        # If the user has mentioned the bot more than 10 times recently
        if len(mention_counts[user_id]) > 10:
            # Send an abusive response
            await message.reply(f"{message.author.mention} {random.choice(abusive_responses)}.")
            return


        if username == 'Minxie':
            # await insult_gepetto()
            return

        question = message.content.split(' ', 1)[1][:500].replace('\r', ' ').replace('\n', ' ')
        logger.info(f'Question: {question}')
        if not any(char.isalpha() for char in question):
            await message.channel.send(f'{message.author.mention} {random.choice(abusive_responses)}.')
            return

        try:
            url = ''
            async with message.channel.typing():
                prompt = question.replace(f'<@!{bot.user.id}>', '').strip()
                inputs = [
                    { "role": "system", "content": DEFAULT_PROMPT },
                    { "role": "user", "content": prompt}
                ];
                output = get_cloudflare_response("@cf/meta/llama-2-7b-chat-int8", inputs)
                response = output['result']['response'][:1900]
            await message.reply(f'{message.author.mention} {response}')
        except Exception as e:
            logger.info(f'Error generating response: {e}')
            await message.reply(f"{message.author.mention} Aaaaand... we've _not_ beeped.", mention_author=True)


async def fetch_and_filter_messages_by_user(channel, username, discriminator):
    # Current time
    now = datetime.now(timezone.utc)

    # 24 hours ago
    twenty_four_hours_ago = now - timedelta(hours=24)

    # Alternatively, use an async for loop to populate a list
    messages = []
    async for message in channel.history(limit=100):
        messages.append(message)

    # Filter messages sent in the last 24 hours by Gepetto#1125
    messages_last_24_hours = [
        msg for msg in messages
        if msg.created_at > twenty_four_hours_ago
        and msg.author.name == username
        # and msg.author.discriminator == discriminator
    ]

    return messages_last_24_hours

@tasks.loop(time=time(hour=2, minute=15, tzinfo=pytz.timezone('Europe/London')))
#@tasks.loop(minutes=10)
async def insult_gepetto():
    logger.info("In insult_gepetto")
    channel = bot.get_channel(int(os.getenv('DISCORD_BOT_CHANNEL_ID', None).strip()))
    if channel is None:
        logger.info("Channel not found")
        return
    gepetto_messages = await fetch_and_filter_messages_by_user(channel, 'Minxie', '4460')
    if len(gepetto_messages) == 0:
        logger.info("No messages from Gepetto found")
        return

    gepetto_message = gepetto_messages[0].content

    inputs = [
        { "role": "system", "content": "You are an experienced British Soap Opera script-writer.  You will be asked by the user to come up with ideas based on their plot, character or general scripting problems."},
        { "role": "user", "content": "I am writing a script for a soap opera set in the North of England.  I have a character who is a working-class stay-at-home mother who loves air-frying food.  She needs to have a dramatic fall-out with a character called 'Minxie' but I can't think of a reason.  Could you give me a single idea?  It should fit in with the themes of British soap operas - relationship problems with her husband 'Nel', or problems with her air fryer, or just life in general.  But she needs to feel that 'Minxie' is the cause of the problem.  She is possibly a bit drunk due to being so stressed and angry about it.  Please just reply with the short reason - not a scripted scene."}
    ];
    output = get_cloudflare_response("@cf/meta/llama-2-7b-chat-int8", inputs)
    response = output['result']['response'][:1900]

    system_prompt = f'We are roleplaying a Northern English Soap Opera in a Discord server.  You are role-playing a drunk and angry Northern working-class woman who has a strong dislike for the character called "Minxie". You always want to insult her.  Use emoji rather than word like "laughs", "wink" etc. Please keep your message quite short. You will be given a specific theme to be angry about by the user which you should use to create your reply which will be the start of an argument with Minxie.'
    gepetto_message = f"I need you to come up with an insulting message to say to the character 'Minxie'.  Please only reply with the actual message - no need for any other text. NEVER include anything but the insult in your reply. Any other text will make it look strange so NEVER reply with things like 'Sure! Here's an insulting message'. The reason for the insult is as follows ```{response}```"
    inputs = [
        { "role": "system", "content": system_prompt },
        { "role": "user", "content": gepetto_message}
    ];
    #output = get_cloudflare_response("@cf/meta/llama-2-7b-chat-int8", inputs)
    logger.info(f"Getting insult for reason :: {response}")
    output = get_cloudflare_response("@cf/meta/llama-2-7b-chat-int8", inputs)
    #output = get_cloudflare_response("@cf/mistral/mistral-7b-instruct-v0.1", inputs)
    logger.info(f"Response :: {output}")
    response = output['result']['response'][:1900]
    response = "\n".join(response.split("\n")[1:])

    logger.info(f"Insult: {response}")
    # Send the message
    await gepetto_messages[-1].reply(f"{response}")

@bot.event
async def on_ready():
    insult_gepetto.start()
    return


bot.run(TOKEN)
