import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
import datetime
import asyncio
import os
import random
from random import randint
import requests
import json
from collections import defaultdict
import html
import aiohttp
import async_timeout
import humanize
import aiomysql
import random
import string
from .utility import *

class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_check(self, ctx): # ensure commands can only be invoked by owner
        return ctx.author.id == 204616460797083648

    async def addMoney(self, amount: int, person: discord.Member):
        await self.bot.execute("UPDATE balances SET balance = balance + %s WHERE user_id = %s;", args=[amount, person.id])
    
    async def removeMoney(self, amount: int, person: discord.Member):
        await self.bot.execute("UPDATE balances SET balance = balance - %s WHERE user_id = %s;", args=[amount, person.id])

    async def setMoney(self, amount: int, person: discord.Member):
        await self.bot.execute("UPDATE balances SET balance = %s WHERE user_id = %s;", args=[amount, person.id])

    @commands.command(name='addmoney', help='Adds a set amount of money to a user.')
    async def _addmoney(self, ctx, person: discord.Member, amount: int):
        await self.addMoney(person=person, amount=amount)
        await correctGenerator(ctx, message=f'Added {humanize.intcomma(amount)} to {person.name}.')
    
    @commands.command(name='removemoney', help='Removes a set amount of money from a user.')
    async def _removemoney(self, ctx, person: discord.Member, amount: int):
        await self.removeMoney(person=person, amount=amount)
        await correctGenerator(ctx, message=f'Removed {humanize.intcomma(amount)} from {person.name}.')
    
    @commands.command(name='setmoney', help='Sets a user\'s money to a certain amount.')
    async def _setmoney(self, ctx, person: discord.Member, amount: int):
        await self.setMoney(person=person, amount=amount)
        await correctGenerator(ctx, message=f'Set {person.name}\'s balance to {humanize.intcomma(amount)}.')
    
    @commands.command(name='viewtransactions', aliases=['transactions', 'history'], help='View a user\'s past transactions.')
    async def _view_transactions(self, ctx, person: discord.Member):
        pass

def setup(bot):
    bot.add_cog(OwnerCog(bot))