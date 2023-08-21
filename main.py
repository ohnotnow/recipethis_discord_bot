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

openai.api_key = os.getenv('OPENAI_API_KEY')
openai_model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
server_id = os.getenv("DISCORD_SERVER_ID", "not_set")
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
# Create instance of bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
abusive_responses = ["Wanker", "Asshole", "Prick", "Twat"]
mention_counts = defaultdict(list) # This will hold user IDs and their mention timestamps
logger = logging.getLogger('discord')  # Get the discord logger

def get_keywords_from_openai(text):
    functions = [
        {
            "name": "get_search_keywords",
            "description": "this function takes in a user message and returns an array of keywords to search for to get the best search results",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "description": "the extracted list of good keywords to search for",
                        "items": {
                            "type": "string",
                        }
                    }
                },
                "required": ["keywords"],

            },
        }
    ]
    function_call = {"name": "get_search_keywords"}
    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant who specialises in turning user messages into search keywords."
        },
        {
            "role": "user",
            "content": text
        }
    ]
    response = openai.ChatCompletion.create(
        model=openai_model,
        messages=messages,
        function_call=function_call,
        functions=functions,
        max_tokens=100
    )

    if response.choices[0].message['function_call']:
        arguments_json = response.choices[0].message['function_call']['arguments']
        decoded_results = json.loads(arguments_json)
        return " ".join(decoded_results['keywords']).split()
    else:
        return response.choices[0].message['content'].split()

def fetch_search_results(keywords):
    search_url = f"https://recipethis.com/?s={'+'.join(keywords)}"
    response = requests.get(search_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Fetch all anchor tags inside an article tag
    anchor_tags = soup.select('article > a')[:4]

    # Extract href attributes (URLs) from these anchor tags
    urls = [a['href'] for a in anchor_tags]

    return urls[0]
    return random.choice(urls)

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

        # If the user has mentioned the bot more than 10 times recently
        if len(mention_counts[user_id]) > 10:
            # Send an abusive response
            await message.reply(f"{message.author.mention} {random.choice(abusive_responses)}.")
            return

        question = message.content.split(' ', 1)[1][:500].replace('\r', ' ').replace('\n', ' ')
        # logger.info(f'Question: {question}')
        if not any(char.isalpha() for char in question):
            await message.channel.send(f'{message.author.mention} {random.choice(abusive_responses)}.')
            return

        try:
            url = ''
            async with message.channel.typing():
                prompt = question.replace(f'<@!{bot.user.id}>', '').strip()
                keywords = get_keywords_from_openai(prompt)
                logger.info(keywords)
                url = fetch_search_results(keywords)
                    # send the response as a reply and mention the person who asked the question
            await message.reply(f'{message.author.mention} {url}')
        except Exception as e:
            logger.info(f'Error generating response: {e}')
            await message.reply(f"{message.author.mention} Aaaaand... we've _not_ beeped.", mention_author=True)

bot.run(TOKEN)
