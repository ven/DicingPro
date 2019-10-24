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

async def wrongGenerator(ctx, *, message, optionalDescription: str=None, delete_after=None):

    wrongembed = discord.Embed(colour=discord.Colour.red(), description=optionalDescription)
    wrongembed.title = f'<:cross_mark:614598372929830913> **{message}**'

    return await ctx.send(embed=wrongembed, delete_after=delete_after)

async def correctGenerator(ctx, *, message, optionalDescription: str=None, delete_after=None):

    correctembed = discord.Embed(colour=discord.Colour.green(), description=optionalDescription)
    correctembed.title = f'<:check_mark:614598372648550421> **{message}**'

    return await ctx.send(embed=correctembed, delete_after=delete_after)
