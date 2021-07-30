#!/usr/bin/env python3

import os

import discord
import kucoin

client = discord.Client()

@client.event
async def on_read():
    print(f'{client.user} has connected to discord')

client.run(os.getenv('DISCORD_TOKEN'))
