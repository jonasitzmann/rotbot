from io import BytesIO
import os
from PIL import Image
import discord
import numpy as np
import pandas as pd
from discord.commands import ApplicationContext
from database import db, get_key_names
from parse import Participation as P, EventType as E, Event
from spin_image import create_animation

intents = discord.Intents.all()
token = os.environ["BOTTOKEN"]
bot = discord.Bot(intents=intents)

@bot.slash_command(name="process_image", description="Upload an image and optionally flip it")
async def process_image(
    ctx: ApplicationContext,
    image: discord.Option(discord.Attachment, description="Upload an image"),
    num_segments: discord.Option(int, default=32, description="Number of circle segments"),
    num_rotations: discord.Option(int, default=10, description="Number of circle rotations"),
):
    await ctx.defer()
    # Download the image into memory
    image_bytes = await image.read()
    pil_image = Image.open(BytesIO(image_bytes))
    fp = "received_image.png"
    pil_image.save(fp)
    video_path = create_animation(input_img_path=fp, num_segments=num_segments, num_spins=num_rotations)
    # # Optionally flip it
    # if flip:
    #     pil_image = pil_image.transpose(Image.FLIP_TOP_BOTTOM)
    file = discord.File(fp=video_path)
    await ctx.respond(file=file)

@bot.slash_command(name="ping")
async def ping(ctx: ApplicationContext):
    await ctx.respond("moin")


bot.run(token)
