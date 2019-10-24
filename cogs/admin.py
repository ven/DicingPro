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

ADMIN_ROLE = 614572100623138831

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx): # check if user is admin

        role = ctx.guild.get_role(ADMIN_ROLE)
        return role in ctx.author.roles

        await wrongGenerator(ctx, message=f'You are not an admin.', optionalDescription='**Insufficient Permissions**')

    @commands.command(name='cashiers', aliases=['cashierbals', 'cashierbal', 'cashiertotal', 'cashiertotals'], help='Displays a cashier\'s remaining balance to be paid back into the House.')
    async def _get_cashier_balances(self, ctx):
        
        res = await self.bot.fetchall("SELECT user_id, outstanding_balance FROM cashiers;")

        embed = discord.Embed(colour=discord.Colour.blue())
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.title = '**Outstanding Cashier Balances**'
        embed.description = 'How much each Cashier has of the house\'s money.'

        for user_id, balance in res:
            person = self.bot.get_user(user_id)
            embed.add_field(name=f'**{person.mention}**', value=f'💵 {humanize.intcomma(balance)}', inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='profit', aliases=['getprofit', 'dailyprofit', 'profitstats', 'housestats', 'dailyhouse'], help='Displays the house\'s daily profit.')
    async def _get_house_daily(self, ctx):

        yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        total_amounts = await self.bot.fetchall("SELECT amount FROM transactions WHERE date > %s;", args=[yesterday])
        total_bets = await self.bot.fetchall("SELECT id FROM bets WHERE date > %s;", args=[yesterday])

        # transactions table for the outcome of the game
        # bets table for bets without the outcome

        embed = discord.Embed(colour=discord.Colour.blue())
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.title = '**House Profit**'
        embed.description ='**Numerous metrics regarding the house\'s daily profit.**'

        total_profit = sum(x for x in total_amounts)

        embed.add_field(name='**Daily Profit**', value=f'💵 {humanize.intcomma(total_profit)}', inline=False)
        embed.add_field(name='**Total Bets Placed**', value=len(total_bets), inline=False)

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(AdminCog(bot))