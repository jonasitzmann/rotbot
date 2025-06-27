import os
import shutil
from pathlib import Path
import ffmpeg

import cv2
from PIL import Image

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


def create_animation(input_img_path: Path, frame_rate: int=24, num_spins: int=10, num_segments: int=32) -> Path:
    frames_dir = create_frames(input_img_path, num_segments)
    video_path = create_video(frames_dir, frame_rate=frame_rate, num_spins=num_spins)
    compressed_path = compress_video(video_path)
    return compressed_path

def create_frames(img_path, num_segments):
    print("creating frames")
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
    output_path.unlink(missing_ok=True)
    shutil.rmtree(output_path, ignore_errors=True)
    ffmpeg.input(video_path).output(
        filename=output_path,
        vcodec='libx264',
        crf=28,  # Higher means more compression (23=default, 28-35=smaller files)
        preset='slow'  # can be 'ultrafast', 'fast', 'medium', 'slow'
    ).run()
    return output_path

# Directory with image frames
def create_video(frame_dir: Path, frame_rate: int, num_spins: int):
    print("creating video...")
    output_video = frame_dir.with_suffix(".mp4")
    imgs = sorted(os.listdir(frame_dir)) * num_spins
    first_frame = cv2.imread(os.path.join(frame_dir, imgs[0]))
    height, width, layers = first_frame.shape
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # Or 'mp4v' for .mp4 files
    video = cv2.VideoWriter(output_video, fourcc, frameSize=(width, height), fps=frame_rate)
    for img_name in imgs:
        img_path = os.path.join(frame_dir, img_name)
        frame = cv2.imread(img_path)
        video.write(frame)
    video.release()
    return output_video



if __name__ == "__main__":
    main()