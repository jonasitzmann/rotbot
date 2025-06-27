from io import BytesIO
import discord
from discord.commands import ApplicationContext
from spin_image import create_animation
import os
import shutil
from pathlib import Path
import ffmpeg

import cv2
from PIL import Image


intents = discord.Intents.all()
token = os.environ["BOTTOKEN"]
bot = discord.Bot(intents=intents)

frames_dir = Path("frames")


def main():
    # todo configuration --------------
    img_path = Path("images/faule_motte.png")
    print(img_path.absolute())
    frame_rate = 24
    num_spins = 5
    num_segments = 32
    rotation_rate = frame_rate / num_segments
    print(f"{rotation_rate=}")
    # todo -----------------------------
    create_animation(input_img_path=img_path)


def create_animation(input_img_path: Path, frame_rate: int=24, num_spins: int=5, num_segments: int=32) -> Path:
    frames_dir = create_frames(input_img_path, num_segments)
    video_path = create_video(frames_dir, frame_rate=frame_rate, num_spins=num_spins)
    create_compressed_video(frame_dir=frames_dir, frame_rate=frame_rate, num_spins=num_spins)
    return compressed_path

def create_frames(img_path, num_segments):
    shutil.rmtree(frames_dir, ignore_errors=True)
    os.mkdir(frames_dir)
    img = Image.open(img_path)
    # frame_angle = 360 / frame_rate * rotation_freq
    # duration = 1.0 / rotation_freq
    # num_frames = int(frame_rate * duration)
    frame_angle = 360 / num_segments
    num_frames = num_segments
    for frame_idx in range(num_frames):
        rotated = img.rotate(angle=frame_angle * frame_idx)
        rotated.save(frames_dir / f"{frame_idx:04}.png")
    return frames_dir

def compress_video(video_path: Path) -> Path:
    output_path = video_path.with_stem("compressed")

    # Delete existing output file if it exists
    output_path.unlink(missing_ok=True)

    # Use FFmpeg with lower RAM usage
    (
        ffmpeg
        .input(str(video_path))
        .output(
            str(output_path),
            vcodec='libx264',
            crf=28,                # More compression
            preset='veryfast',     # Faster = lower CPU/RAM use
            max_muxing_queue_size=1024,  # Prevent memory spikes with large/variable frames
        )
        .overwrite_output()
        .run(quiet=True)  # Suppress verbose logging (less overhead)
    )

    return output_path

# Directory with image frames
def create_video(frame_dir: Path, frame_rate: int, num_spins: int):
    output_video = frame_dir.with_suffix(".mp4")
    imgs = sorted(os.listdir(frame_dir))
    first_frame = cv2.imread(os.path.join(frame_dir, imgs[0]))
    height, width, layers = first_frame.shape
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # Or 'mp4v' for .mp4 files
    video = cv2.VideoWriter(output_video, fourcc, frameSize=(width, height), fps=frame_rate)
    for spin_num in range(num_spins):
        for img_name in imgs:
            img_path = os.path.join(frame_dir, img_name)
            frame = cv2.imread(img_path)
            video.write(frame)
    video.release()
    shutil.rmtree(frames_dir, ignore_errors=True)
    return output_video

@bot.slash_command(name="process_image", description="Upload an image and optionally flip it")
async def process_image(
    ctx: ApplicationContext,
    image: discord.Option(discord.Attachment, description="Upload an image"),
    num_segments: discord.Option(int, default=32, description="Number of circle segments(32)") = 32,
    num_rotations: discord.Option(int, default=5, description="Number of circle rotations(5)") = 5,
    frame_rate: discord.Option(int, default=24, description="Number of circle rotations(24)") = 24,
):
    await ctx.defer()
    # Download the image into memory
    try:
        await ctx.send("starting")
        await ctx.send(f'{num_rotations=}')
        await ctx.send(f'{num_segments=}')
        print(f'{num_rotations=}')
        print(f'{num_segments=}')
        image_bytes = await image.read()
        pil_image = Image.open(BytesIO(image_bytes))
        fp = "received_image.png"
        await ctx.send("saving image")
        print("saving image")
        pil_image.save(fp)
        await ctx.send("creating frames")
        print("creating frames")
        frames_dir = create_frames(img_path=fp, num_segments=num_segments)
        await ctx.send("creating video")
        print("creating video")
        video_path = create_video(frames_dir, frame_rate=frame_rate, num_spins=num_rotations)
        await ctx.send("compressing video")
        print("compressing video")
        compressed_path = compress_video(video_path)
        print(f'{compressed_path=}')
        await ctx.send("sending video")
        print("sending video")
        file = discord.File(fp=compressed_path)
        await ctx.send(file=file)
        await ctx.respond("done")
        print("done")
    except Exception as e:
        print("Error: ", e)
        await ctx.respond(f"error:\n{e}")

@bot.slash_command(name="ping")
async def ping(ctx: ApplicationContext):
    await ctx.respond("moin")


print("starting rotbot")
bot.run(token)
