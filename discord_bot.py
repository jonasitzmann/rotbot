import discord
from discord.commands import ApplicationContext
from discord.ext import tasks
import parse
import splus
import os
import utils
import datetime
from parse import Participation as P
intents = discord.Intents.all()
s = splus.login()
token = os.environ['BOTTOKEN']
bot = discord.Bot(intents=intents)

id_players_info = '1-fHm9B3Gdnnb1uMfUh6m0w_GWnMqBJWNWhk3kBOxaOE'
players_info = utils.download_google_sheet_as_df(id_players_info).dropna(axis=0)
splus2discord, discord2splus, members, participation = {}, {}, [], None
now = datetime.datetime.now()

def get_user(discord_name):
    username, discrimantor = discord_name.split('#')
    results = [m for m in members if m.name == username and m.discriminator==discrimantor]
    return results[0] if results else None

@bot.event
async def on_ready():
    global splus2discord, discord2splus, members, participation
    members = bot.guilds[0].members
    participation = parse.get_participation()
    splus2discord = {r.splus_name: get_user(r.discord_name) for i, r in players_info.iterrows()}
    discord2splus = {v: k for k, v in splus2discord.items()}
    update_df.start()


def filter_trainings_func(row):
    days = (now - row['date']).days
    return days < 14


@tasks.loop(minutes=5)
async def update_df():
    global participation
    participation = parse.get_participation()


@bot.slash_command(name='tragdichein', description='Listet SpielerPlus Termine auf, zu denen du dich noch nicht eingetragen hast')
async def get_appointments(ctx: ApplicationContext):
    member = discord.utils.get(members, id=ctx.user.id)
    if splus_name := discord2splus.get(member, None):
        if splus_name in participation.columns:
            df = participation[[*'name date url'.split(), splus_name]]
            df = df[df[splus_name] == P.Circle.name.lower()]
            trainings_mask = df['name'] == 'Training'
            trainings_df = df[trainings_mask]
            trainings_df = trainings_df[trainings_df.apply(filter_trainings_func, axis=1)]
            non_training_df = df[~trainings_mask]
            trainings_str, others_str = ['\n'.join([utils.format_appointment(row) for i, row in x.iterrows()]) for x in [trainings_df, non_training_df]]
            msg = f"Nicht Zu/Abgesagte Termine:\nTrainings (nächste 2 Wochen):\n{trainings_str}\nAndere Termine (nächste 20 Wochen):\n{others_str}"
            await member.send(embed=discord.Embed(description=msg))
            await ctx.respond('ok', ephemeral=True)

bot.run(token)
