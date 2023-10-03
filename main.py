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
from datetime import datetime, timedelta, timezone
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


        if username == 'Gepetto':
            await insult_gepetto()
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
                    { "role": "system", "content": "You are a friendly assistant who is role playing a Northern England working-class woman that helps users in a discord server. The server is limited to adults only, so you are free to use adult langauge." },
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

@tasks.loop(hours=1)
async def insult_gepetto():
    pass
    logger.info("In insult_gepetto")
    channel = bot.get_channel(int(os.getenv('DISCORD_BOT_CHANNEL_ID', None).strip()))
    if channel is None:
        logger.info("Channel not found")
        return
    gepetto_messages = await fetch_and_filter_messages_by_user(channel, 'Gepetto', '1125')
    if len(gepetto_messages) == 0:
        logger.info("No messages from Gepetto found")
        return

    if random.random() < 0.5:
        gepetto_message = "I am the most amazing bot ever.  And Liz Truss was the best Prime Minister we ever had."
    else:
        gepetto_message = gepetto_messages[0].content

    system_prompt = f'We are roleplaying a Northern English Soap Opera in a Discord server.  Your character is a Northern woman who is in love with her Air Fryer and doesnt understand why everyone else doesnt use one. When you see a message from a user called "Gepetto" (a female character in our pretend show), you should respond with a very short comment that insults Gepetto in the style of a rude Northern English woman.'
    messages = [
        {
            'role': 'system',
            'content': system_prompt
        },
        {
            'role': 'user',
            'content': f'{gepetto_message}'
        },
    ]

    response = openai.ChatCompletion.create(
        model=openai_model,
        messages=messages,
        temperature=1.0,
        max_tokens=1024,
    )

    message = response['choices'][0]['message']['content'][:1900]
    logger.info(f"Insult: {message}")
    logger.info(f"{messages[-1]}")
    # Send the message
    await gepetto_messages[-1].reply(f"{message}")

@bot.event
async def on_ready():
    # insult_gepetto.start()
    return


bot.run(TOKEN)
