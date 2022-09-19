import sqlalchemy as db
import os

from discord import player

DATABASE_URL = os.environ.get('DATABASE_URL')
engine = db.create_engine(DATABASE_URL, echo=False)
meta = db.MetaData()
connection = engine.connect()

def create_players_table():
    players_tab = 'players'
    players = db.Table(
        players_tab,
        meta,
        db.Column('id', db.Integer, primary_key=True),
        db.Column('discord_id', db.Integer),
        db.Column('splus_id', db.Integer),
        db.Column('name', db.String)
    )
    meta.create_all(players)