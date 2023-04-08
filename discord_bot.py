import asyncio
from typing import List
import discord
import humanize
from discord.commands import ApplicationContext
from discord.ext import tasks
import parse
import splus
import os
import utils
import datetime
from datetime import timedelta
import pickle
from parse import Participation as P, EventType as E, Event
import nest_asyncio
from database import db, get_key_names
nest_asyncio.apply()
intents = discord.Intents.all()
s = splus.login()
token = os.environ['BOTTOKEN']
bot = discord.Bot(intents=intents)
update_interval = datetime.timedelta(minutes=7)


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


async def remember_candidates(dt: timedelta=None, exclude_trainigs=False):
    now = datetime.datetime.now() + datetime.timedelta(hours=2)  # todo timezones!
    if dt is None:
        dt = datetime.timedelta(hours=1)
    events: List[Event] = list(url2event.values())
    events = [e for e in events if e is not None]
    if exclude_trainigs:
        events = [e for e in events if e.type != E.TRAINING]
    for event in events:
        time_left_e = event.deadline - now
        delta = humanize.naturaldelta(time_left_e)
        if dt < time_left_e < dt + update_interval:
            participants = get_event_participants(event, [P.Circle])
            participants = [p for p in participants if p is not None]
            if participants:
                msg = f'sending reminders for {event.name if event else ""} on {humanize.naturaldate(event.start)} to:\n{",".join([p.name for p in participants])}'
                print(msg)
                await splus2discord['Jonas Sitzmann'].send(msg)
            for p in participants:
                name = discord2splus[p].split(' ')[0]
                msg = f'Hey {name}, bitte trag dich für das Folgende Event ein: \n{event.name} ({humanize.naturaldate(event.start)})\nVerbleibende Zeit: {delta} \nSpielerPlus Link: <{event.url}>\nTippe /tragdichein für eine Liste von Terminen, zu denen du dich noch nicht eingetragen hast.'
                # print(msg)
                await p.send(msg)



def filter_trainings_func(row):
    now = datetime.datetime.now() + datetime.timedelta(hours=2)  # todo timezones!
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
    for args in [
        dict(dt=timedelta(hours=2)),
        dict(dt=timedelta(days=1)),
        dict(dt=timedelta(days=5), exclude_trainigs=True),
    ]:
        await remember_candidates(**args)


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

def autocomplete_name(ctx):
    names = list(splus2discord.keys())
    arg = ctx.value
    if arg:
        names = [n for n in names if n.lower().startswith(arg.lower())]
    return names

@bot.slash_command(name='pn')
async def write_personal_message(
    ctx: discord.ApplicationContext,
    target_name: discord.Option(str, '', name='an', autocomplete=autocomplete_name),
    message: discord.Option(str, '', name='nachricht')
):
    member = splus2discord[target_name]
    await member.send(message)
    await ctx.respond('ok', ephemeral=True)
    

@bot.slash_command(name='mention')
async def autocomplete_example(
    ctx: discord.ApplicationContext,
    event: discord.Option(str, "", autocomplete=get_event_names),
    maybe: discord.Option(str, "", name='vllt', autocomplete=lambda x: ['ja'])='nein',
    no_response: discord.Option(str, "", name='ka', autocomplete=lambda x: ['ja'])='nein',
    yes: discord.Option(str, "", name='ja', autocomplete=lambda x: ['nein']) = 'ja',
):
    participation_types = [P.YES]*janein[yes] + [P.MAYBE]*janein[maybe] + [P.Circle]*janein[no_response]
    discordnames = [p.mention for p in get_event_participants(event, participation_types=participation_types) if p is not None]
    if discordnames:
        await ctx.respond(' '.join(discordnames))
    else:
        await ctx.respond('could not find anyone', ephemeral=True)


@bot.slash_command(name='schüsselübergabe')
async def key_to(
    ctx: discord.ApplicationContext,
    key_name: discord.Option(str, '', autocomplete=get_key_names, name='schlüssel'),
    receiver: discord.Option(str, '', autocomplete=autocomplete_name, name='emfänger*in')
):
    db.set(key_name, receiver)
    sender_name = discord2splus.get(ctx.author, 'Unbekannt')
    await splus2discord[receiver].send(f'{sender_name} hat dir den Schlüssel {key_name} übergeben.')
    await ctx.respond(f'{receiver} hat jetzt den Schüssel "{key_name}"')

@bot.slash_command(name='wo sind die schlüssel?')
async def where_are_the_keys(ctx:discord.ApplicationContext):
    await ctx.respond('\n'.join([f"{k}: {db.get(k)}" for k in get_key_names()]))

bot.run(token)
