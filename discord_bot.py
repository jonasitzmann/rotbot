import asyncio
import discord
import humanize
from discord.commands import ApplicationContext
from discord.ext import tasks
import parse
import splus
import os
import utils
import datetime
import pickle
from parse import Participation as P, EventType as E, Event
import nest_asyncio
nest_asyncio.apply()
intents = discord.Intents.all()
s = splus.login()
token = os.environ['BOTTOKEN']
bot = discord.Bot(intents=intents)
update_interval = datetime.timedelta(minutes=5)


id_players_info = '1-fHm9B3Gdnnb1uMfUh6m0w_GWnMqBJWNWhk3kBOxaOE'
players_info = utils.download_google_sheet_as_df(id_players_info).dropna(axis=0)
splus2discord, discord2splus, members, participation, url2event = {}, {}, [], None, {}
# debug = True
debug = False

def get_user(discord_name):
    username, discrimantor = discord_name.split('#')
    results = [m for m in members if m.name == username and m.discriminator==discrimantor]
    return results[0] if results else None

@bot.event
async def on_ready():
    global splus2discord, discord2splus, members
    members = bot.guilds[0].members
    splus2discord = {r.splus_name: get_user(r.discord_name) for i, r in players_info.iterrows()}
    discord2splus = {v: k for k, v in splus2discord.items()}
    update_df.start()


async def remember_candidates(time_left=None):
    now = datetime.datetime.now()
    if time_left is None:
        time_left = datetime.timedelta(hours=2)
        # time_left = datetime.timedelta(minutes=154)
    for event in list(url2event.values()):
        time_left_e = event.deadline - now
        if (time_left - update_interval) < time_left_e < time_left:
            participants = get_event_participants(event, [P.Circle])
            await splus2discord['Jonas Sitzmann'].send(f'sending reminders for {event} to:\n{",".join([p.name for p in participants])}')
            for p in participants:
                name = discord2splus[p].split(' ')[0]
                delta = humanize.naturaltime(time_left_e)
                msg = f'Hey {name}, bitte trag dich für das Folgende Event ein: \n{event.name}\nVerbleibende Zeit: {delta} \nSpielerPlus Link: <{event.url}>'
                await p.send(msg)



def filter_trainings_func(row):
    now = datetime.datetime.now()
    days = (url2event[row.url].start - now).days
    return days < 14


@tasks.loop(seconds=update_interval.total_seconds())
async def update_df():
    global url2event, participation
    if debug:
        with open('debug_data.pck', 'rb') as f:
            url2event, participation = pickle.load(f)
    else:
        url2event, participation = parse.get_participation()
    await remember_candidates()


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
    non_trainings = [e.name for e in sorted(url2event.values(), key=lambda e: e.start) if e.type != E.TRAINING]
    return ['Nächstes Training', *non_trainings]


def get_event_participants(event, participation_types=None):
    if participation_types is None:
        participation_types = [P.YES]
    participation_types = [p.name.lower() for p in participation_types]
    if isinstance(event, Event):
        url = event.url
    elif event == 'Nächstes Training':
        trainings = [e for e in url2event.values() if e.type == E.TRAINING]
        training = sorted(trainings, key=lambda e: e.start)[0]
        url = training.url
    else:
        url = [e.url for e in url2event.values() if e.name == event][0]
    df = participation[participation.url == url].T
    df = df[df.iloc[:, 0].isin(participation_types)]
    names = df.index.tolist()
    discordnames = [splus2discord[n] for n in names if n in splus2discord]
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
    discordnames = [p.mention for p in get_event_participants(event, participation_types=participation_types)]
    if discordnames:
        await ctx.respond(' '.join(discordnames))
    else:
        await ctx.respond('could not find anyone', ephemeral=True)


bot.run(token)