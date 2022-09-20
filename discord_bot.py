import interactions
import discord
import parse
import splus
import os
import utils
import datetime
from parse import Participation as P
s = splus.login()
token = os.environ['BOTTOKEN']
bot = interactions.Client(
    token=token,
    default_scope=False,
)
id_players_info = '1-fHm9B3Gdnnb1uMfUh6m0w_GWnMqBJWNWhk3kBOxaOE'
players_info = utils.download_google_sheet_as_df(id_players_info).dropna(axis=0)
splus2discord, discord2splus, members = {}, {}, []
now = datetime.datetime.now()

def get_user(discord_name):
    username, discrimantor = discord_name.split('#')
    results = [m for m in members if m.user.username == username and m.user.discriminator==discrimantor]
    return results[0] if results else None

@bot.event
async def on_ready():
    global splus2discord, discord2splus, members
    members = await bot.guilds[0].get_all_members()
    splus2discord = {r.splus_name: get_user(r.discord_name) for i, r in players_info.iterrows()}
    discord2splus = {v: k for k, v in splus2discord.items()}


def filter_trainings_func(row):
    days = (row['date'] - now).days
    return days < 14



@bot.command(name='tragdichein', description='Listet SpielerPlus Termine auf, zu denen du dich noch nicht eingetragen hast',
             # options=[
             #     interactions.Option(
             #         name="wochen",
             #         description="max. Wochen in der Zukunft",
             #         type=interactions.OptionType.INTEGER,
             #         required=False,
             #     )]
             )

async def get_appointments(ctx: interactions.CommandContext):
    member = discord.utils.get(members, id=ctx.user.id)
    if splus_name := discord2splus.get(member, None):
        participation = parse.get_participation()
        if splus_name in participation.columns:
            df = participation[[*'name date url'.split(), splus_name]]
            df = df[df[splus_name] == P.Circle.name.lower()]
            trainings_mask = df['name'] == 'Training'
            trainings_df = df[trainings_mask]
            trainings_df = trainings_df[trainings_df.apply(filter_trainings_func, axis=1)]
            non_training_df = df[~trainings_mask]
            trainings_str, others_str = ['\n'.join([utils.format_appointment(row) for i, row in x.iterrows()]) for x in [trainings_df, non_training_df]]
            msg = f"Nicht Zu/Abgesagte Termine:\nTrainings (nächste 2 Wochen):\n{trainings_str}\nAndere Termine (nächste 20 Wochen):\n{others_str}"
            return await ctx.send(msg)
    await member.send_message('Dir ist kein SpierlPlus Account zugeordnet')


bot.start()
