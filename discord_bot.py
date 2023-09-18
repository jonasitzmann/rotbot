import datetime
import os
import pickle
from datetime import timedelta
from typing import List

import discord
import humanize
import nest_asyncio
import numpy as np
import pandas as pd
from discord.commands import ApplicationContext
from discord.ext import tasks
from parse import get_names

import config
import database
import parse
import splus
import utils
from database import db, get_key_names
from parse import Participation as P, EventType as E, Event

nest_asyncio.apply()
intents = discord.Intents.all()
s = splus.login()
token = os.environ["BOTTOKEN"]
bot = discord.Bot(intents=intents)
update_interval = datetime.timedelta(minutes=7)

splus2discord_id = database.DbDict('splus2discord_id')

id_players_info = "1-fHm9B3Gdnnb1uMfUh6m0w_GWnMqBJWNWhk3kBOxaOE"
players_info = utils.download_google_sheet_as_df(id_players_info).dropna(axis=0)
participation, url2event, old_participation = (
    None,
    {},
    None,
)
# debug = True
debug = False
all_splus_names = None

def autocomplete_name(ctx):
    names = list(splus2discord_id.keys())
    arg = ctx.value
    if arg:
        names = [n for n in names if n.lower().startswith(arg.lower())]
    return names

def autocomplete_all_names(ctx):
    arg = ctx.value
    names = all_splus_names
    if arg:
        names = [n for n in names if n.lower().startswith(arg.lower())]
    return names



@bot.event
async def on_ready():
    global all_splus_names
    all_splus_names = parse.get_names()
    update_df.start()


async def send_msg(name, msg):
    if name not in splus2discord_id:
        print(f'{name=} not in splus2discord_id\n{splus2discord_id=}')
        return
    user = bot.get_user(splus2discord_id[name])
    if user is None:
        print(f'user for {name=} is None')
    await user.send(msg)


async def remember_candidates(dt: timedelta = None, exclude_trainigs=False):
    discord2splus = {v: k for k, v in splus2discord_id.items()}
    now = datetime.datetime.now() + datetime.timedelta(hours=2)  # todo timezones!
    events: List[Event] = list(url2event.values())
    events = [e for e in events if e is not None]
    if exclude_trainigs:
        events = [e for e in events if e.type != E.TRAINING]
    for event in events:
        # for person
        #    for dt in dts[person]
        time_left_e = event.deadline - now
        delta = humanize.naturaldelta(time_left_e)
        if dt < time_left_e < dt + config.d_send_reminders:
            participants = get_event_participants(event, [P.Circle])
            participants = [p for p in participants if p is not None]
            if participants:
                msg = f'sending reminders for {event.name if event else ""} on {humanize.naturaldate(event.start)} to:\n{",".join([p.name for p in participants])}'
                print(msg)
                await bot.get_user(splus2discord_id["Jonas Sitzmann"]).send(msg)
            for p in participants:
                name = discord2splus[p.id].split(" ")[0]
                msg = f"Hey {name}, bitte trag dich für das Folgende Event ein: \n{event.name} ({humanize.naturaldate(event.start)})\nVerbleibende Zeit: {delta} \nSpielerPlus Link: <{event.url}>\nTippe /tragdichein für eine Liste von Terminen, zu denen du dich noch nicht eingetragen hast."
                await p.send(msg)


def filter_trainings_func(row):
    now = datetime.datetime.now() + datetime.timedelta(hours=2)  # todo timezones!
    days = (url2event[row.url].start - now).days
    return days < 14


@bot.slash_command(name='ichbin')
async def setup(ctx: ApplicationContext, splus_name=discord.Option(str, name='splus_name', autocomplete=autocomplete_all_names, required=True),):
    user = ctx.user
    splus2discord_id[splus_name] = user.id
    print('ok')
    await ctx.respond('ok', ephemeral=True)

@tasks.loop(seconds=config.d_send_reminders.total_seconds())
async def update_df():
    global url2event, participation, old_participation
    if debug:
        with open("debug_data.pck", "rb") as f:
            url2event, participation = pickle.load(f)
    else:
        old_participation = participation
        url2event, participation = parse.update_participation(url2event)
    for args in [
        dict(dt=timedelta(hours=2)),
        dict(dt=timedelta(days=1)),
        dict(dt=timedelta(days=5), exclude_trainigs=True),
    ]:
        await remember_candidates(**args)
    if old_participation is not None:
        await check_key_diff_based(participation, old_participation)


part2num = {p.name.lower(): p.value for p in P}


async def check_key_diff_based(
    participation: pd.DataFrame, old_participation: pd.DataFrame
):
    p_new, p_old = (x.set_index("url") for x in (participation, old_participation))
    names = [col for col in p_new.columns if col in p_old.columns]
    urls = [url for url in p_new.index if url in p_old.index]
    p_new, p_old = (p.loc[urls, names] for p in (p_new, p_old))
    p_new_np, p_old_np = (
        p.applymap(lambda x: part2num[x]).to_numpy() for p in [p_new, p_old]
    )
    diff = p_new_np - p_old_np
    changed_url_idxs, changed_name_idxs = np.where(diff < 0)
    for changed_url_idx, changed_name_idx in zip(changed_url_idxs, changed_name_idxs):
        name, url = names[changed_name_idx], urls[changed_url_idx]
        event = url2event[url]
        part_new, part_old = (
            P(arr[changed_url_idx, changed_name_idx]).name
            for arr in [p_new_np, p_old_np]
        )
        key = get_key_for_event(event)
        if key is not None:
            key_owner = db.get(key)
            if key_owner == name:
                print(
                    f'{name} hat sich für {event.name} am {event.start} von "{part_old}" auf "{part_new}" gesetzt, hat aber den Schlüssel {key}!'
                )
                await send_msg(name,
                    f'Du hast dich für {event.name} am {event.start} von "{part_old}" auf "{part_new}" gesetzt, hast aber Schlüssel "{key}!"'
                )


@bot.slash_command(
    name="tragdichein",
    description="Listet SpielerPlus Termine auf, zu denen du dich noch nicht eingetragen hast",
)
async def get_appointments(ctx: ApplicationContext):
    discord2splus = {v: k for k, v in splus2discord_id.items()}
    member_id = ctx.user.id
    if splus_name := discord2splus.get(member_id, None):
        if splus_name in participation.columns:
            df = participation[["url", splus_name]]
            df = df[df[splus_name] == P.Circle.name.lower()]
            trainings_mask = df.apply(
                lambda x: url2event[x.url].type == E.TRAINING, axis=1
            )
            trainings_df = df[trainings_mask]
            trainings_df = trainings_df[
                trainings_df.apply(filter_trainings_func, axis=1)
            ]
            non_training_df = df[~trainings_mask]
            trainings_str, others_str = [
                "\n".join(
                    [
                        utils.format_appointment(url2event[row.url])
                        for i, row in x.iterrows()
                    ]
                )
                for x in [trainings_df, non_training_df]
            ]
            msg = f"Nicht Zu/Abgesagte Termine:\nTrainings (nächste 2 Wochen):\n{trainings_str}\nAndere Termine (nächste 20 Wochen):\n{others_str}"
            await bot.get_user(member_id).send(embed=discord.Embed(description=msg))
            await ctx.respond("ok", ephemeral=True)


async def get_event_names(ctx):
    non_trainings = [
        e.name
        for e in sorted(url2event.values(), key=lambda e: e.start)
        if e.type != E.TRAINING
    ]
    return ["Nächstes Training", *non_trainings]


def training2str(training: Event):
    return f"Training {training.start}"


async def get_training_names(ctx):
    return [
        training2str(e)
        for e in sorted(url2event.values(), key=lambda e: e.start)
        if e.type == E.TRAINING
    ]


def get_event_participants(event, participation_types=None, splus_names=False):
    if participation_types is None:
        participation_types = [P.YES]
    participation_types = [p.name.lower() for p in participation_types]
    if isinstance(event, Event):
        url = event.url
    elif event == "Nächstes Training":
        trainings = [e for e in url2event.values() if e.type == E.TRAINING]
        training = sorted(trainings, key=lambda e: e.start)[0]
        url = training.url
    else:
        url = [e.url for e in url2event.values() if e.name == event][0]
    df = participation[participation.url == url].T
    df = df[df.iloc[:, 0].isin(participation_types)]
    names = df.index.tolist()
    if splus_names:
        return names
    discord_users = [bot.get_user(splus2discord_id[n]) for n in names if n in splus2discord_id]
    return discord_users


janein = {"ja": True, "nein": False}



@bot.slash_command(name="pn")
async def write_personal_message(
    ctx: discord.ApplicationContext,
    target_name: discord.Option(str, "", name="an", autocomplete=autocomplete_name),
    message: discord.Option(str, "", name="nachricht"),
):
    await send_msg(target_name, message)
    ctx.respond('ok', )


@bot.slash_command(name="mention")
async def autocomplete_example(
    ctx: discord.ApplicationContext,
    event: discord.Option(str, "", autocomplete=get_event_names),
    maybe: discord.Option(str, "", name="vllt", autocomplete=lambda x: ["ja"]) = "nein",
    no_response: discord.Option(
        str, "", name="ka", autocomplete=lambda x: ["ja"]
    ) = "nein",
    yes: discord.Option(str, "", name="ja", autocomplete=lambda x: ["nein"]) = "ja",
):
    participation_types = (
        [P.YES] * janein[yes]
        + [P.MAYBE] * janein[maybe]
        + [P.Circle] * janein[no_response]
    )
    discordnames = [
        p.mention
        for p in get_event_participants(event, participation_types=participation_types)
        if p is not None
    ]
    if discordnames:
        await ctx.respond(" ".join(discordnames))
    else:
        await ctx.respond("could not find anyone", ephemeral=True)


@bot.slash_command(name="schuesseluebergabe")
async def key_to(
    ctx: discord.ApplicationContext,
    key_name: discord.Option(str, "", autocomplete=get_key_names, name="schluessel"),
    receiver: discord.Option(
        str, "", autocomplete=autocomplete_name, name="emfaenger_in"
    ),
):

    db.set(key_name, receiver)
    discord2splus = {v: k for k, v in splus2discord_id.items()}
    sender_name = discord2splus.get(ctx.author.id, "Unbekannt")
    await send_msg(receiver, f"{sender_name} hat dir den Schlüssel {key_name} übergeben.")
    await ctx.respond(f'{receiver} hat jetzt den Schüssel "{key_name}"')


@bot.slash_command(name="wosinddieschluessel")
async def where_are_the_keys(ctx: discord.ApplicationContext):
    await ctx.respond("\n".join([f"{k}: {db.get(k)}" for k in get_key_names()]))


location2key = {
    "Rote Wiese": "Rote Wiese",
    "Rheinring": "Westpark",
    "Sackring": "Halle",
}

@bot.slash_command(name="schluesselda")
async def bot_key_present(
    ctx: discord.ApplicationContext,
    event_name: discord.Option(str, "", autocomplete=get_training_names, name="event"),
):
    possible_training_event = [
        e
        for e in url2event.values()
        if e.type == E.TRAINING and training2str(e) == event_name
    ]
    if len(possible_training_event) == 1:
        response = is_key_present(possible_training_event[0])
    elif len(possible_training_event) > 1:
        response = "mehrere passende Trainings gefunden"
    elif len(possible_training_event) == 0:
        response = "kein passendes Training gefunden"
    await ctx.respond(response)


def get_key_for_event(event: Event):
    event_location = event.location
    if event_location is not None:
        possible_keys = [v for k, v in location2key.items() if (k in event_location)]
        assert (
            len(possible_keys) <= 1
        ), f"to many possible keys for location {event_location}: {possible_keys}"
        if possible_keys:
            key = possible_keys[0]
            return key
    return None


def is_key_present(event: Event):
    key = get_key_for_event(event)
    if key is None:
        return
    key_owner_splus = db.get(key)
    participants = get_event_participants(event, splus_names=True)
    return key_owner_splus in participants


bot.run(token)
