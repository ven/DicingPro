import discord
from discord.ext import commands
import sys, traceback
import datetime
import asyncio
import config
from config import *
import random
from discord import FFmpegPCMAudio
import aiomysql
from random import randint

def get_prefix(bot, message):

    prefixes = ['!']

    if not message.guild:
        return '?'

    return commands.when_mentioned_or(*prefixes)(bot, message)

initial_extensions = ['cogs.owner', 'cogs.admin', 'cogs.general']

bot = commands.AutoShardedBot(command_prefix=get_prefix, case_insensitive=True)
loop = bot.loop
bot.remove_command('help')
bot.load_extension("jishaku")

if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print(f'Failed to load extension {extension}.', file=sys.stderr)
            traceback.print_exc()

@bot.event
async def on_ready():

    print(f'\n\nLogged in as: {bot.user.name} - {bot.user.id}\nVersion: {discord.__version__}\n')
    print(f'Successfully logged in and booted...!')

    await bot.change_presence(status = discord.Status.online, activity=discord.Activity(type=discord.ActivityType.playing, name=f"with the dice."))

async def execute(query, args=None):
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cur:
            if args:
                await cur.execute(query=query, args=args)
            else:
                await cur.execute(query=query)
            await conn.commit()
            return cur

async def fetchone(query, args=None):
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cur:
            if args:
                await cur.execute(query=query, args=args)
            else:
                await cur.execute(query=query)
            row = await cur.fetchone()
            if row != None:
                return row[0]
            else:
                return None


async def fetchmultiple(query, args=None):
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cur:
            if args:
                await cur.execute(query=query, args=args)
            else:
                await cur.execute(query=query)
            row = await cur.fetchone()
            if row != None:
                return row
            else:
                return None

async def fetchall(query, args=None):
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cur:
            if args:
                await cur.execute(query=query, args=args)
            else:
                await cur.execute(query=query)
            rows = await cur.fetchall()
            return rows

bot.execute = execute
bot.fetchone = fetchone
bot.fetchall = fetchall

@asyncio.coroutine
def database():
    bot.pool = yield from aiomysql.create_pool(host='127.0.0.1', port=3306,
                                                user='youshallnotpass', password='youshallnotpass',
                                                db='db', autocommit=True, loop=loop)

loop.run_until_complete(database())

bot.run(config.TOKEN, bot=True, reconnect=True)