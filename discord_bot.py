import discord
from discord.commands import ApplicationContext
from discord.ext import tasks
import parse
import splus
import os
import utils
import datetime
import pickle
from parse import Participation as P, EventType as E
intents = discord.Intents.all()
s = splus.login()
token = os.environ['BOTTOKEN']
bot = discord.Bot(intents=intents)

id_players_info = '1-fHm9B3Gdnnb1uMfUh6m0w_GWnMqBJWNWhk3kBOxaOE'
players_info = utils.download_google_sheet_as_df(id_players_info).dropna(axis=0)
splus2discord, discord2splus, members, participation, url2event = {}, {}, [], None, {}
now = datetime.datetime.now()
debug = True

def get_user(discord_name):
    username, discrimantor = discord_name.split('#')
    results = [m for m in members if m.name == username and m.discriminator==discrimantor]
    return results[0] if results else None

@bot.event
async def on_ready():
    global splus2discord, discord2splus, members
    members = bot.guilds[0].members
    if debug:
        load_data_debug()
    else:
        update_df.start()
    splus2discord = {r.splus_name: get_user(r.discord_name) for i, r in players_info.iterrows()}
    discord2splus = {v: k for k, v in splus2discord.items()}
    print('ready')


def filter_trainings_func(row):
    days = (url2event[row.url].start - now).days
    return days < 14


@tasks.loop(minutes=5)
async def update_df():
    global url2event, participation
    url2event, participation = parse.get_participation()


def load_data_debug():
    global url2event, participation
    filename = 'debug_data.pck'
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            url2event, participation = pickle.load(f)
    else:
        with open(filename, 'wb') as f:
            pickle.dump(parse.get_participation(), f)



@bot.slash_command(name='tragdichein', description='Listet SpielerPlus Termine auf, zu denen du dich noch nicht eingetragen hast')
async def get_appointments(ctx: ApplicationContext):
    member = discord.utils.get(members, id=ctx.user.id)
    if splus_name := discord2splus.get(member, None):
        if splus_name in participation.columns:
            df = participation[['url', splus_name]]
            df = df[df[splus_name] == P.Circle.name.lower()]
            trainings_mask = df.apply(lambda x: url2event[x.url].type == E.TRAINING, axis=1)
            trainings_df = df[trainings_mask]
            trainings_df = trainings_df[trainings_df.apply(filter_trainings_func, axis=1)]
            non_training_df = df[~trainings_mask]
            trainings_str, others_str = ['\n'.join([utils.format_appointment(url2event[row.url]) for i, row in x.iterrows()]) for x in [trainings_df, non_training_df]]
            msg = f"Nicht Zu/Abgesagte Termine:\nTrainings (nächste 2 Wochen):\n{trainings_str}\nAndere Termine (nächste 20 Wochen):\n{others_str}"
            await member.send(embed=discord.Embed(description=msg))
            await ctx.respond('ok', ephemeral=True)

counter = 0

async def get_event_names(ctx):
    non_trainings = [e.name for e in url2event.values() if e.type != E.TRAINING]
    return non_trainings


def get_event_participants(event_name, participation_types=None):
    if participation_types is None:
        participation_types = [P.YES]
    participation_types = [p.name.lower() for p in participation_types]
    url = [e.url for e in url2event.values() if e.name == event_name][0]
    df = participation[participation.url == url].T
    df = df[df.iloc[:, 0].isin(participation_types)]
    names = df.index.tolist()
    discordnames = [splus2discord[n].mention for n in names if n in splus2discord]
    return discordnames

janein = {'ja': True, 'nein': False}

@bot.slash_command(name='mention')
async def autocomplete_example(
    ctx: discord.ApplicationContext,
    event: discord.Option(str, "", autocomplete=get_event_names),
    maybe: discord.Option(str, "", name='vllt', autocomplete=lambda x: ['ja'])='nein',
    no_response: discord.Option(str, "", name='ka', autocomplete=lambda x: ['ja'])='nein',
    yes: discord.Option(str, "", name='ja', autocomplete=lambda x: ['nein']) = 'ja',
):
    participation_types = [P.YES]*janein[yes] + [P.MAYBE]*janein[maybe] + [P.Circle]*janein[no_response]
    discordnames = get_event_participants(event, participation_types=participation_types)
    if discordnames:
        await ctx.respond(' '.join(discordnames))
    else:
        await ctx.respond('could not find anyone', ephemeral=True)


bot.run(token)