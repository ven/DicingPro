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
import itertools
import aiomysql
import random
import string
from .utility import *

DEPOSIT_CHANNEL_ID = 614578150600605696
WITHDRAWAL_CHANNEL_ID = 614578167612571689
CASHIER_ROLE_ID = 614574310488801310

class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.duelgames = []
        self.correct = '<:check_mark:614598372648550421>'
        self.wrong = '<:cross_mark:614598372929830913>'
        
    async def checkExists(self, person):
        res = await self.bot.fetchone("SELECT user_id FROM balances WHERE user_id = %s;", args=[person.id])
        if not res: # if they don't have a db entry
            await self.bot.execute("INSERT INTO balances (user_id) VALUES (%s);", args=[person.id]) # make a db entry        

    # cog check

    async def cog_check(self, ctx):
        await self.checkExists(person=ctx.author)
        return True

    # events

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.checkExists(person=member)
    
    # helper functions

    async def amountHandler(self, amount: str):

        amount = amount.upper()

        try:
            int(amount)
            return int(amount)

        except:
            if 'K' in amount:
                if len(amount) > 1:
                    return float(amount.replace('K', '')) * 1000
                return 1000.0

            if 'M' in amount:
                if len(amount) > 1:
                    return float(amount.replace('M', '')) * 1000000
                return 1000000.0

            if 'B' in amount:
                return float(amount.replace('B', '')) * 1000000000

        return 0
    
    async def betHandler(self, ctx, person: discord.Member, amount: int):

        balance = await self.balance(person=person)

        if amount < 0:
            await wrongGenerator(ctx, message=f'No.')
            return None

        if amount > balance:
            await wrongGenerator(ctx, message=f'This bet is greater than your balance.')
            return None
        
        elif amount < 10000 or amount > 10000000:
            await wrongGenerator(ctx, message=f'The minimum bet is 07 10,000.\nThe maximum bet is 07 10,000,000.')

        elif amount <= balance:
            await self.removeMoney(amount=amount, person=person)
            newBalance = await self.balance(person=person)
            return amount

    async def cashierHandler(self, ctx, person: discord.Member, amount: int, cashier_type: str):

        CASHIER_ROLE = ctx.guild.get_role(CASHIER_ROLE_ID)
        DEPOSIT_CHANNEL = ctx.guild.get_channel(DEPOSIT_CHANNEL_ID)
        WITHDRAW_CHANNEL = ctx.guild.get_channel(WITHDRAWAL_CHANNEL_ID)
        USER_ID = await self.bot.fetchone("SELECT id FROM balances WHERE user_id = %s;", args=[person.id])

        embed = discord.Embed(colour=discord.Colour.green())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.description = 'Make sure you are trading with a Cashier. Scammers may use similar names in an attempt to scam you out of your money.'

        def check(reaction, user):
            return not user.bot
        
        if cashier_type == 'CASHIN':
            embed.title = '**Cashin Request**'
            await ctx.send(embed=embed)

            await self.bot.execute("INSERT INTO deposits (user_id, amount) VALUES (%s, %s);", args=[USER_ID, amount])

            embed.description = f'**Amount:** 07 {humanize.intcomma(amount)}\n'

            msg = await DEPOSIT_CHANNEL.send(embed=embed, content=CASHIER_ROLE.mention)
            await msg.add_reaction('✅')

            reaction, user = await self.bot.wait_for('reaction_add', timeout=None, check=check)

            if reaction.emoji == '✅':
                await self.bot.execute("DELETE FROM deposits WHERE user_id = %s;", args=[USER_ID])
                await msg.delete()

                embed.description = f'{person.mention}, you will be cashed in by {user.mention}!'
                await ctx.send(embed=embed)


        elif cashier_type == 'CASHOUT':
            embed.title = '**Cashout Request**'
            await ctx.send(embed=embed)

            await self.bot.execute("INSERT INTO withdrawals (user_id, amount) VALUES ((SELECT id FROM balances WHERE user_id = %s), %s);", args=[person.id, amount])

            embed.description = f'**Amount:** 07 {humanize.intcomma(amount)}\n'

            msg = await WITHDRAW_CHANNEL.send(embed=embed, content=CASHIER_ROLE.mention)
            await msg.add_reaction('✅')

            reaction, user = await self.bot.wait_for('reaction_add', timeout=None, check=check)

            if reaction.emoji == '✅':
                await self.bot.execute("DELETE FROM deposits WHERE user_id = %s;", args=[USER_ID])
                await msg.delete()

                embed.description = f'{person.mention}, you will be cashed out by {user.mention}!'
                await ctx.send(embed=embed)

    async def balance(self, person: discord.Member):
        await self.checkExists(person=person)
        res = await self.bot.fetchone("SELECT balance FROM balances WHERE user_id = %s;", args=[person.id])
        return res or 0
    
    async def addMoney(self, amount: int, person: discord.Member):
        await self.bot.execute("UPDATE balances SET balance = balance + %s WHERE user_id = %s;", args=[amount, person.id])
    
    async def removeMoney(self, amount: int, person: discord.Member):
        await self.bot.execute("UPDATE balances SET balance = balance - %s WHERE user_id = %s;", args=[amount, person.id])

    async def setMoney(self, amount: int, person: discord.Member):
        await self.bot.execute("UPDATE balances SET balance = %s WHERE user_id = %s;", args=[amount, person.id])

    # commands
    
    @commands.command(name='wallet', aliases=['balance', 'w', 'bal', 'wal'], help='Views a user\'s wallet balance.')
    async def _wallet(self, ctx, person: discord.Member=None):

        if not person:
            person = ctx.author

        balance = await self.balance(person=person)

        embed = discord.Embed(colour=discord.Colour.blue())
        embed.set_author(name=person.name, icon_url=person.avatar_url)

        embed.title = '💰 **Balance**'
        embed.add_field(name='**07**', value=f'{humanize.intcomma(balance)}', inline=True)
        embed.add_field(name='**RS3**', value=f'0', inline=True)

        await ctx.send(embed=embed)
    
    @commands.command(name='transfer', aliases=['send'], help='Transfers a set amount of money to a user.')
    async def _transfer(self, ctx, person: discord.Member, amount: str):

        balance = await self.balance(person=ctx.author)
        amount = await self.amountHandler(amount=amount)

        if amount > balance:
            await wrongGenerator(ctx, message=f'You do not have enough money to cover this transaction.')
        
        else:
            await self.removeMoney(amount=amount, person=ctx.author) # remove money from person transferring
            await self.addMoney(amount=amount, person=person) # add money to the other user

            await correctGenerator(ctx, message=f'Successfully transferred 07 {humanize.intcomma(amount)} to {person.name}!')
    
    @commands.command(name='cashin', help='Cashes in a set amount of money.')
    async def _cashin(self, ctx, amount):

        money_amount = await self.amountHandler(amount=amount)

        if money_amount < 1000000:
            await wrongGenerator(ctx, message=f'The minimum deposit is 1 million.')

        await self.cashierHandler(ctx, person=ctx.author, amount=money_amount, cashier_type='CASHIN')
    
    @commands.command(name='cashout', help='Cashes out a set amount of money.')
    async def _cashout(self, ctx, amount):

        balance = await self.balance(person=ctx.author)
        money_amount = await self.amountHandler(amount=amount)

        if money_amount > balance:
            await wrongGenerator(ctx, message=f'You cannot afford to withdraw this much money.')
        
        else:
            if money_amount < 5000000:
                await wrongGenerator(ctx, message=f'The minimum withdrawal is 5 million.')
                
            else:
                await self.cashierHandler(ctx, person=ctx.author, amount=money_amount, cashier_type='CASHOUT')

    # gamemodes

    @commands.command(name='duel', help='Challenges a user to a duel for a set amount of money.')
    async def _duel(self, ctx, person: discord.Member, bet: str):

        correct = self.bot.get_emoji(614598372648550421)
        wrong = self.bot.get_emoji(614598372929830913)

        if ctx.author.id in self.duelgames or person.id in self.duelgames:
            await wrongGenerator(ctx, message=f'You or the opponent already have an active duel game.')

        else:
            amount = await self.amountHandler(amount=bet)
            bet = await self.betHandler(ctx, person=ctx.author, amount=amount)

            if bet:

                other_balance = await self.balance(person=person)

                if bet > other_balance:
                    await self.addMoney(person=ctx.author, amount=bet)
                    await wrongGenerator(ctx, message=f'{person.name} does not have enough money to afford this bet.')

                else:

                    self.duelgames.append(ctx.author.id)

                    embed = discord.Embed(title='⚔ **Duel**', description=f'**{person.mention}, {ctx.author.mention} has challenged you to a duel for 07 {humanize.intcomma(bet)}!**', colour=discord.Colour.blue())
                    embed.add_field(name='**To accept this duel, react with**', value=correct, inline=False)
                    embed.add_field(name='**To decline this duel, react with**', value=wrong, inline=False)

                    msg = await ctx.send(embed=embed)
                    await msg.add_reaction(correct)
                    await msg.add_reaction(wrong)

                    def check(reaction, user):
                        return user.id == person.id and reaction.message.guild.id == ctx.guild.id and reaction.message.id == msg.id

                    try:
                        reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                        await msg.clear_reactions()
                        if reaction.emoji == correct:

                            await self.removeMoney(person=person, amount=bet)

                            self.duelgames.append(person.id)
                            
                            embed.description = f'{ctx.author.name} **VS** {person.name}\n\n❤ **{ctx.author.name}: 100\n❤ {person.name}: 100**'
                            embed.colour = discord.Colour.green()

                            embed.remove_field(index=1)
                            embed.remove_field(index=0)
                            embed.add_field(name='**Duel Accepted!**', value='**The fight will begin momentarily...**')

                            await msg.edit(embed=embed)

                            embed.remove_field(index=0)

                            await asyncio.sleep(2)

                            player1health = 100
                            player2health = 100

                            async def gameRound(name):

                                embed.clear_fields()
                                roll = random.randint(0, 25)
                                speech = f'{name} <:abyssal_whip:614811028554907700> whipped with {roll} damage!'
                                embed.add_field(name=f'**{name}\'s Turn**', value=speech, inline=False)

                                return roll
                            
                            while (player1health > 0) and (player2health > 0):
                                
                                if player1health - await gameRound(name=person.name) <= 0:
                                    player1health = 0
                                    embed.description = f'{ctx.author.name} **VS** {person.name}\n\n❤ **{ctx.author.name}: {player1health}\n❤ {person.name}: {player2health}**'
                                    await msg.edit(embed=embed)
                                    break
                                else:
                                    player1health -= await gameRound(name=person.name)

                                embed.description = f'{ctx.author.name} **VS** {person.name}\n\n❤ **{ctx.author.name}: {player1health}\n❤ {person.name}: {player2health}**'
                                await msg.edit(embed=embed)

                                if (player1health > 0) and (player2health > 0):
                                
                                    await asyncio.sleep(4)

                                    if player2health - await gameRound(name=ctx.author.name) <= 0:
                                        player2health = 0
                                        embed.description = f'{ctx.author.name} **VS** {person.name}\n\n❤ **{ctx.author.name}: {player1health}\n❤ {person.name}: {player2health}**'
                                        await msg.edit(embed=embed)
                                        break
                                    else:
                                        player2health -= await gameRound(name=ctx.author.name)

                                    embed.description = f'{ctx.author.name} **VS** {person.name}\n\n❤ **{ctx.author.name}: {player1health}\n❤ {person.name}: {player2health}**'
                                    await msg.edit(embed=embed)

                                    await asyncio.sleep(4)
                                
                                else:
                                    break
                                    
                            if player1health > player2health:
                                embed.clear_fields()
                                self.duelgames.remove(ctx.author.id)
                                self.duelgames.remove(person.id)
                                embed.add_field(name=f'{correct} **{ctx.author.name} won!**', value=f'💵 07 {humanize.intcomma(bet)} has been added to {ctx.author.name}\'s balance.')

                                await self.addMoney(person=ctx.author, amount=bet*2)
                                await msg.edit(embed=embed)

                            elif player2health > player1health:
                                embed.clear_fields()
                                self.duelgames.remove(ctx.author.id)
                                self.duelgames.remove(person.id)
                                embed.add_field(name=f'{correct} **{person.name} won!**', value=f'💵 07 {humanize.intcomma(bet)} has been added to {person.name}\'s balance.')

                                await self.addMoney(person=person, amount=bet*2)
                                await msg.edit(embed=embed)

                        else:
                            self.duelgames.remove(ctx.author.id)
                            await self.addMoney(person=ctx.author, amount=bet)
                            await wrongGenerator(ctx, message=f'Duel declined.')

                    except:
                        await wrongGenerator(ctx, message=f'Duel declined.')
                        await self.addMoney(person=ctx.author, amount=bet)
                        self.duelgames.remove(ctx.author.id)

    @commands.command(name='54x2', aliases=['54'], help='Gambles a set amount of money on 54x2.')
    async def _54x2(self, ctx, bet: str):

        amount = await self.amountHandler(amount=bet)
        bet = await self.betHandler(ctx, person=ctx.author, amount=amount)

        if bet:
            number = random.randint(1, 100)

            embed = discord.Embed(timestamp=datetime.datetime.utcnow())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon_url)
            embed.title = '**54x2 Dicing**'
            embed.description = f'💵 {humanize.intcomma(amount)}'

            if 1 <= number <= 54:
                embed.colour = discord.Colour.red()
                embed.add_field(name=f'{self.wrong} **You lost!**', value=f'The \🎲 dice rolled **{number}**.\n💵 **{humanize.intcomma(amount)}** has been removed from your balance.', inline=False)
            
            elif 55 <= number <= 100:
                embed.colour = discord.Colour.green()
                embed.add_field(name=f'{self.correct} **You won!**', value=f'The \🎲 dice rolled **{number}**.\n💵 **{humanize.intcomma(amount*0.95)}** has been added to your balance.', inline=False)
                await self.addMoney(amount=amount*1.95, person=ctx.author)
            
            await ctx.send(embed=embed)

    @commands.command(name='92x10', aliases=['92'], help='Gambles a set amount of money on 92x10.')
    async def _92x10(self, ctx, bet: str):

        amount = await self.amountHandler(amount=bet)
        bet = await self.betHandler(ctx, person=ctx.author, amount=amount)

        if bet:
            number = random.randint(1,100)

            embed = discord.Embed(timestamp=datetime.datetime.utcnow())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon_url)
            embed.title = '**92x10 Dicing**'
            embed.description = f'💵 {humanize.intcomma(amount)}'

            if 1 <= number <= 92:
                embed.colour = discord.Colour.red()
                embed.add_field(name=f'{self.wrong} **You lost!**', value=f'The \🎲 dice rolled **{number}**.\n💵 **{humanize.intcomma(amount)}** has been removed from your balance.', inline=False)
            
            elif 93 <= number <= 100:
                embed.colour = discord.Colour.green()
                embed.add_field(name=f'{self.correct} **You won!**', value=f'The \🎲 dice rolled **{number}**.\n💵 **{humanize.intcomma(amount*9.5)}** has been added to your balance.', inline=False)
                await self.addMoney(amount=amount*9.5, person=ctx.author)
            
            await ctx.send(embed=embed)

    @commands.command(name='30x3', aliases=['30'], help='Gambles a set amount of money on 30x3.')
    async def _30x3(self, ctx, bet: str):

        amount = await self.amountHandler(amount=bet)
        bet = await self.betHandler(ctx, person=ctx.author, amount=amount)

        if bet:
            number = random.randint(1,100)

            embed = discord.Embed(timestamp=datetime.datetime.utcnow())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon_url)
            embed.title = '**30x3 Dicing**'
            embed.description = f'💵 {humanize.intcomma(amount)}'

            if 30 <= number <= 100:
                embed.colour = discord.Colour.red()
                embed.add_field(name=f'{self.wrong} **You lost!**', value=f'The \🎲 dice rolled **{number}**.\n💵 **{humanize.intcomma(amount)}** has been removed from your balance.', inline=False)
            
            elif 1 <= number <= 30:
                embed.colour = discord.Colour.green()
                embed.add_field(name=f'{self.correct} **You won!**', value=f'The \🎲 dice rolled **{number}**.\n💵 **{humanize.intcomma(amount*2.9)}** has been added to your balance.', inline=False)
                await self.addMoney(amount=amount*2.9, person=ctx.author)
            
            await ctx.send(embed=embed)

    @commands.command(name='20x4', aliases=['20'], help='Gambles a set amount of money on 18x4.')
    async def _20x4(self, ctx, bet: str):

        amount = await self.amountHandler(amount=bet)
        bet = await self.betHandler(ctx, person=ctx.author, amount=amount)

        if bet:
            number = random.randint(1,100)

            embed = discord.Embed(timestamp=datetime.datetime.utcnow())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon_url)
            embed.title = '**20x4 Dicing**'
            embed.description = f'💵 {humanize.intcomma(amount)}'

            if 21 <= number <= 100:
                embed.colour = discord.Colour.red()
                embed.add_field(name=f'{self.wrong} **You lost!**', value=f'The \🎲 dice rolled **{number}**.\n💵 **{humanize.intcomma(amount)}** has been removed from your balance.', inline=False)
            
            elif 1 <= number <= 20:
                embed.colour = discord.Colour.green()
                embed.add_field(name=f'{self.correct} **You won!**', value=f'The \🎲 dice rolled **{number}**.\n💵 **{humanize.intcomma(amount*3.9)}** has been added to your balance.', inline=False)
                await self.addMoney(amount=amount*3.9, person=ctx.author)
            
            await ctx.send(embed=embed)
    
    @commands.command(name='fp', help='Gambles a set amount of money on Flower Poker.')
    async def _flowerpoker(self, ctx, bet: str):

        amount = await self.amountHandler(amount=bet)
        bet = await self.betHandler(ctx, person=ctx.author, amount=amount)

        async def flowerPicker():

            """
            Chooses a random flower with a certain value from the selection.

            Returns: flower list [index 0: flower emoji, index 1: flower value (red, blue, etc)]
            """

            flowers = {
                0: "<:Yellow_flowers:614844614058311700>",
                1: "<:White_flowers:614844614116900864>",
                2: "<:Red_flowers:614844614079152128>",
                3: "<:Purple_flowers:614844614062637056>", 
                4: "<:Orange_flowers:614844613798133761>",
                5: "<:Flowers_pastel:614844614024626176>",
                6: "<:Blue_flowers:614844613827624981>",
                7: "<:Black_flowers:614844613668372511>"
            }

            index = random.randint(0, len(flowers.keys()) - 1)

            return [flowers[index], index]

        async def getHandValue(hand, type: str):

            handDict = dict((x,hand.count(x)) for x in set(hand))
            value = 0

            if len(set(hand)) == 1: # all the same value, must be 5oK
                return [5, '5 of a Kind']
            
            elif len(set(hand)) == 2 and all(i in [4, 1] for i in handDict.values()): # only 2 unique values
                return [4, '4 of a Kind']
            
            elif len(set(hand)) == 2 and all(i in [3, 2] for i in handDict.values()):
                return [3, 'Full House']
            
            elif len(set(hand)) == 3 and all(i in [3, 1] for i in handDict.values()):
                return [2, '3 of a Kind']
            
            elif 2 in handDict.values():
                return [1, '2 Pair']
            
            return [0, 'No Pairs']

        if bet:
            embed = discord.Embed(timestamp=datetime.datetime.utcnow())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon_url)
            embed.title = '**Flower Poker**'

            playerValues = [] # the corresponding flower number
            playerFlowers = [] # the picked flowers emojis

            houseValues = []
            houseFlowers = []
            
            for x in range(5): # pick 5 flowers for each player

                # player values + flowers
                
                chosen = await flowerPicker()
                playerFlowers.append(chosen[0])
                playerValues.append(chosen[1])

                # house values + flowers
                
                chosen = await flowerPicker()
                houseFlowers.append(chosen[0])
                houseValues.append(chosen[1])

            playerHandValue = await getHandValue(hand=playerValues, type='PLAYER')
            houseHandValue = await getHandValue(hand=houseValues, type='HOUSE') 

            embed.add_field(name=f'**{ctx.author.name} | {playerHandValue[1]}**', value=" ".join(x for x in playerFlowers), inline=False)
            embed.add_field(name=f'**DicingPro | {houseHandValue[1]}**', value=" ".join(x for x in houseFlowers), inline=False)

            if playerHandValue[0] > houseHandValue[0]: # player wins
                embed.colour = discord.Colour.green()
                embed.add_field(name=f'{self.correct} **You won!**', value=f'💵 **{humanize.intcomma(bet*1.95)}** has been added to your balance.', inline=False)
                await self.addMoney(amount=bet*1.95, person=ctx.author)

            elif playerHandValue[0] < houseHandValue[0]: # house wins
                embed.colour = discord.Colour.red()
                embed.add_field(name=f'{self.wrong} **You lost!**', value=f'💵 **{humanize.intcomma(bet)}** has been removed from your balance.', inline=False)

            elif playerHandValue[0] == houseHandValue[0]: # draw, reroll fp
                embed.add_field(name=f'**You drew!**', value=f'💵 **No money** has been removed from your balance.', inline=False)
                await self.addMoney(amount=bet, person=ctx.author)

            await ctx.send(embed=embed)

    @commands.command(name='hotorcold', aliases=['hot', 'cold', 'hc', 'hotcold'], help='Gambles a set amount of money on Hot or Cold.')
    async def _hot_or_cold(self, ctx, chosen: str, bet: str):

        HOT_FLOWERS = ['<:Yellow_flowers:614844614058311700>', '<:Red_flowers:614844614079152128>', '<:Orange_flowers:614844613798133761>']
        COLD_FLOWERS = ['<:Flowers_pastel:614844614024626176>', '<:Purple_flowers:614844614062637056>', '<:Blue_flowers:614844613827624981>']
        HOST_FLOWER = '<:Flowers_mixed:614844613743738909>'

        choice = None
        amount = await self.amountHandler(amount=bet)
        bet = await self.betHandler(ctx, person=ctx.author, amount=amount)

        if chosen.upper() in ['HOT', 'H']:
            chosen = 'HOT'
        elif chosen.upper() in ['COLD', 'C']:
            chosen = 'COLD'

        if bet:
            number = random.randint(1, 3)

            embed = discord.Embed(timestamp=datetime.datetime.utcnow())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon_url)
            embed.title = '**Hot or Cold**'

            if number == 1:
                pick = random.choice(HOT_FLOWERS)
                pick_name = 'HOT'
            
            elif number == 2:
                pick = random.choice(COLD_FLOWERS)
                pick_name = 'COLD'
            
            elif number == 3:
                pick = HOST_FLOWER
                pick_name = 'HOST'
            
            if chosen == pick_name:
                embed.colour = discord.Colour.green()
                embed.add_field(name='**Picked**', value=pick, inline=False)
                embed.add_field(name=f'{self.correct} **You won!**', value=f'💵 **{humanize.intcomma(bet*1.95)}** has been added to your balance!', inline=False)

                await self.addMoney(amount=bet*1.95, person=ctx.author)

            else:
                embed.colour = discord.Colour.red()
                embed.add_field(name='**Picked**', value=pick, inline=False)
                embed.add_field(name=f'{self.wrong} **You lost!**', value=f'💵 **{humanize.intcomma(bet)}** has been removed from your balance!', inline=False)
            
            await ctx.send(embed=embed)

    @commands.command(name='blackjack', aliases=['bj'])
    async def _blackjack(self, ctx, bet: str):

        amount = await self.amountHandler(amount=bet)
        bet = await self.betHandler(ctx, person=ctx.author, amount=amount)

        cards = [
            ['<:card40:617824319678054513>', '<:card27:617824317572513997>', '<:card14:617824316117090334>', '<:card1:617824307598327809>'],
            ['<:card41:617824319212355595>', '<:card28:617824317559930901>', '<:card2:617824308538114088>', '<:card15:617824316171747328>'],
            ['<:card42:617824321309638687>', '<:card29:617824319405555722>', '<:card16:617824317572513810>', '<:card3:617824318927274015>'],
            ['<:card43:617824321355907072>', '<:card4:617824319149441054>', '<:card30:617824319678054441>', '<:card17:617824317513662464>'],
            ['<:card44:617824323368910924>', '<:card31:617824320890339328>', '<:card18:617824317874503700>', '<:card5:617824321343324176>'],
            ['<:card6:617824322291105803>', '<:card45:617824324304371753>', '<:card32:617824322735570984>', '<:card19:617824318776279061>'],
            ['<:card7:617824322827976800>', '<:card46:617824324665212929>', '<:card33:617824323364716604>', '<:card20:617824319132925952>'],
            ['<:card8:617824324640047124>', '<:card47:617824325940019220>', '<:card34:617824323885072384>', '<:card21:617824321347387425>'],
            ['<:card9:617824324245782560>', '<:card35:617824324463886366>', '<:card22:617824321309507595>', '<:card49:617824326019973140>'],
            ['<:card49:617824326019973140>', '<:card50:617824325596086282>', '<:card39:617824326359711752>', '<:card38:617824326611107871>', '<:card37:617824325256609792>', '<:card36:617824324786847744>', '<:card26:617824325994676307>', '<:card25:617824326464307220>', '<:card24:617824325638029342>', '<:card23:617824322886696983>', '<:card13:617824326560907282>', '<:card12:617824326133219339>', '<:card11:617824325998870550>', '<:card10:617824325193564180>', '<:card52:617824382215258153>', '<:card51:617824380654846048>']
        ]

        async def generateDeck():
        
            temp = []

            for index, card_types in enumerate(cards):
                value = index + 1
                for card in card_types:
                    temp.append([card, value])
            
            random.shuffle(temp)
                        
            return temp
        
        deck = await generateDeck()

        gameFinished = False
        dealerHand = []
        playerHand = []

        async def drawCard():
            return deck.pop()
        
        async def getHandValue(hand: list):

            async def aceChecker(value: int):
                temp_add = value + 11
                if temp_add > 21:
                    return 1
                else:
                    return 11

            value = 0
            ace = 0

            for card in hand:
                if int(card[1]) == 1:
                    ace += 1
                else:
                    value += card[1]
            
            for x in range(ace):
                value += await aceChecker(value=value)

            return value

        async def getHandEmojis(hand: list):
            return "".join([x[0] for x in hand])

        async def getEmbed():

            embed = discord.Embed(colour=discord.Colour.blue())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon_url)
            embed.set_thumbnail(url='https://i.imgur.com/A0SqM0m.png')
            embed.title = '**Blackjack**'
            embed.description = '**Type `hit` or `stand`.**'

            dealerValue = await getHandValue(hand=dealerHand)
            dealerEmoji = await getHandEmojis(hand=dealerHand)

            playerValue = await getHandValue(hand=playerHand)
            playerEmoji = await getHandEmojis(hand=playerHand)

            embed.add_field(name=f'**Player - {playerValue}**', value=playerEmoji, inline=False)
            embed.add_field(name=f'**Dealer - {dealerValue}**', value=dealerEmoji, inline=False)

            return embed

        if bet:

            dealerHand.append(await drawCard()) # draw one card for player

            for x in range(2): # draw two cards for player
                playerHand.append(await drawCard())

            playHuman = True
            playerBusted = False

            playDealer = True
            dealerBusted = False

            embed = await getEmbed()
            message = await ctx.send(embed=embed)

            while playHuman:

                inputCycle = True

                def check(m):
                    return m.author.id == ctx.author.id

                while inputCycle:
                    msg = await self.bot.wait_for('message', check=check)
                    if msg.content in ['H', 'hit']:
                        playerHand.append(await drawCard())
                        embed = await getEmbed()
                        await message.edit(embed=embed)
                        inputCycle = False
                        
                        if await getHandValue(hand=playerHand) > 21:
                            playerBusted = True
                            playHuman = False

                    elif msg.content in ['S', 'stand']:
                        playHuman = False
                        inputCycle = False
            
            while not playerBusted and playDealer:

                dealerValue = await getHandValue(hand=dealerHand)
                
                if dealerValue < 17: # less than 17
                    dealerHand.append(await drawCard())
                else: # greater than 17 
                    playDealer = False
                
                if dealerValue > 21:
                    playDealer = False
                    dealerBusted = True
                
                embed = await getEmbed()
                await message.edit(embed=embed)

                await asyncio.sleep(1.5)

            embed = await getEmbed()
            
            if playerBusted: # dealer wins
                embed.colour = discord.Colour.red()
                embed.add_field(name=f'{self.wrong} **You lost!**', value=f'💵 **{humanize.intcomma(amount)}** has been removed from your balance.', inline=False)

            elif dealerBusted: # player wins
                embed.colour = discord.Colour.green()
                embed.add_field(name=f'{self.correct} **You won!**', value=f'💵 **{humanize.intcomma(amount*1.95)}** has been added to your balance.', inline=False)
                await self.addMoney(amount=amount*1.95, person=ctx.author)

            elif await getHandValue(hand=playerHand) > await getHandValue(hand=dealerHand): # player wins
                embed.colour = discord.Colour.green()
                embed.add_field(name=f'{self.correct} **You won!**', value=f'💵 **{humanize.intcomma(amount*1.95)}** has been added to your balance.', inline=False)
                await self.addMoney(amount=amount*1.95, person=ctx.author)
            
            elif await getHandValue(hand=playerHand) == await getHandValue(hand=dealerHand): # draw
                embed.colour = discord.Colour.gold()
                embed.add_field(name=f'**You drew!**', value=f'💵 **{humanize.intcomma(amount)}** has been added back to your balance.', inline=False)
                await self.addMoney(amount=amount, person=ctx.author)

            else: # dealer wins
                embed.colour = discord.Colour.red()
                embed.add_field(name=f'{self.wrong} **You lost!**', value=f'💵 **{humanize.intcomma(amount)}** has been removed from your balance.', inline=False)
            
            await message.edit(embed=embed)

def setup(bot):
    bot.add_cog(GeneralCog(bot))