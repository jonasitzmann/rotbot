import os
import discord
from discord import ApplicationContext
import asyncio
import json


intents = discord.Intents.all()
token = os.environ.get("BOTTOKEN")
bot = discord.Bot(intents=intents)
splus2disord = {}


@bot.event
async def on_ready():
    me: discord.Member = bot.get_user(682350362849705985)
    members = bot.guilds[0].members
    print(f'{me=}')
    await me.send('Hello World')

@bot.slash_command(name='ichbin')
async def setup(ctx: ApplicationContext, splus_name=discord.Option(name='splus_name'),):
    user = ctx.user
    await user.send(splus_name)
    await ctx.respond('ok', ephemeral=True)




if __name__ == '__main__':
    bot.run(token)

