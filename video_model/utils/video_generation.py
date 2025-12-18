# --- utils/video_assembly.py ---
import os
import logging
import uuid
from google.cloud import storage
from moviepy import (
    VideoFileClip,
    TextClip,
    CompositeVideoClip,
    ImageClip,
    AudioFileClip,
    ColorClip,
    concatenate_videoclips,
)
from moviepy.video.fx import FadeIn, FadeOut

# GCS config (reuse from image_generation)
GCS_BUCKET_NAME = os.getenv("STORAGE_BUCKET_NAME")
GCS_VIDEO_URL_FORMAT = "https://storage.googleapis.com/{bucket}/{filename}"

def upload_video_to_gcs(local_path: str, gcs_filename: str) -> str | None:
    """Uploads a file to GCS and returns its public URL."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_filename)
        blob.upload_from_filename(local_path)
        url = GCS_VIDEO_URL_FORMAT.format(bucket=GCS_BUCKET_NAME, filename=gcs_filename)
        logging.info(f"Uploaded video to GCS: {url}")
        return url
    except Exception as e:
        logging.error(f"Failed to upload {local_path} to GCS: {e}", exc_info=True)
        return None

# Define a standard video size
VIDEO_SIZE = (1280, 720)  # 720p


def _delete_file_safe(filepath):
    try:
        os.remove(filepath)
    except Exception:
        pass

def assemble_video_with_titles(
    graphic_filepaths,
    audio_filepath,
    script_parts_text,
    part_timings=None,  # Can be None
    font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    base_output_path="video.mp4",
    title_duration=2.0,
    video_background=None,  # Optional: path to a video background
) -> str | None:
    """
    Combines graphics, audio, title cards, and text overlays into a video using MoviePy v2.x.
    Uses part timings from SSML marks if provided.
    base_output_path: The base filename for the video (will be made unique).
    """
    all_clips_to_composite = []

    # Make output_path unique
    base, ext = os.path.splitext(base_output_path)
    unique_id = uuid.uuid4().hex[:8]
    unique_output_path = f"{base}_{unique_id}{ext}"

    try:
        # ...existing code...
        # 1. Load Audio
        logging.info(f"Loading audio: {audio_filepath}")
        audio_clip = AudioFileClip(audio_filepath)
        total_duration = audio_clip.duration
        logging.info(f"Audio duration: {total_duration:.2f}s")

        # 2. Always use white background
        background_clip = ColorClip(
            size=VIDEO_SIZE, color=(255, 255, 255), duration=total_duration
        )
        all_clips_to_composite.append(background_clip)

        # 3. Prepare timings
        num_parts = len(script_parts_text)
        if part_timings and isinstance(part_timings, list):
            timings = []
            for i in range(num_parts):
                mark_name = f"part_{i}_end"
                part_end_time = next(
                    (time for mark, time in part_timings if mark == mark_name), None
                )
                timings.append(part_end_time)
        else:
            timings = [total_duration * (i + 1) / num_parts for i in range(num_parts)]

        # 4. Create clips for each part
        if len(graphic_filepaths) < num_parts:
            graphic_filepaths += [None] * (num_parts - len(graphic_filepaths))

        part_start_time = 0.0
        for i, script_part in enumerate(script_parts_text):
            title_text = f"Part {i+1}"
            try:
                title_clip = (
                    TextClip(
                        title_text,
                        fontsize=90,
                        color="yellow",
                        fontfile=font_path,
                        size=(int(VIDEO_SIZE[0] * 0.9), None),
                        method="caption",
                        align="center",
                    )
                    .with_position("center")
                    .with_start(part_start_time)
                    .with_duration(title_duration)
                    .with_effects([FadeIn(0.5), FadeOut(0.5)])
                )
                all_clips_to_composite.append(title_clip)
            except Exception as e:
                logging.error(f"Title card error: {e}")

            content_start_time = part_start_time + title_duration
            part_end_time = (
                timings[i] if (i < len(timings) and timings[i] is not None) else total_duration
            )
            content_duration = max(0.1, part_end_time - content_start_time)

            graphic_path = graphic_filepaths[i]
            # For the first image, stretch to full video duration (after title)
            if i == 0 and graphic_path and os.path.exists(graphic_path):
                try:
                    graphic_clip = (
                        ImageClip(graphic_path)
                        .with_duration(total_duration - title_duration)
                        .with_start(title_duration)
                        .with_position("center")
                        .resized(height=int(VIDEO_SIZE[1] * 0.8))
                        .with_effects([FadeIn(0.5), FadeOut(0.5)])
                    )
                    all_clips_to_composite.append(graphic_clip)
                except Exception as img_err:
                    logging.error(f"Failed to load image '{graphic_path}': {img_err}")
            elif graphic_path and os.path.exists(graphic_path):
                try:
                    graphic_clip = (
                        ImageClip(graphic_path)
                        .with_duration(content_duration)
                        .with_start(content_start_time)
                        .with_position("center")
                        .resized(height=int(VIDEO_SIZE[1] * 0.8))
                        .with_effects([FadeIn(0.5), FadeOut(0.5)])
                    )
                    all_clips_to_composite.append(graphic_clip)
                except Exception as img_err:
                    logging.error(f"Failed to load image '{graphic_path}': {img_err}")
            else:
                logging.warning(f"Graphic file not found for part {i+1}: {graphic_path}")

            try:
                text_overlay_clip = (
                    TextClip.create_caption_clip(
                        txt=script_part,
                        font_size=40,
                        color="white",
                        font=font_path,
                        size=(int(VIDEO_SIZE[0] * 0.85), int(VIDEO_SIZE[1] * 0.4)),
                        method="caption",
                        align="center",
                        stroke_color="black",
                        stroke_width=1.5,
                    )
                    .with_position(("center", 0.7))
                    .with_start(content_start_time)
                    .with_duration(content_duration)
                    .with_effects([FadeIn(0.5), FadeOut(0.5)])
                )
                all_clips_to_composite.append(text_overlay_clip)
            except Exception as e:
                logging.error(f"Text overlay error: {e}")

            part_start_time = part_end_time

        # 5. Composite Final Video
        logging.info("Compositing final video…")
        final_clip = CompositeVideoClip(all_clips_to_composite, size=VIDEO_SIZE)
        final_clip = final_clip.with_duration(total_duration).with_audio(audio_clip)

        # 6. Write video file
        logging.info(f"Writing final video to {unique_output_path}…")
        final_clip.write_videofile(
            unique_output_path,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            threads=4,
            logger="bar",
        )
        logging.info("Video assembly complete.")

        # 7. Upload to GCS and return link
        gcs_filename = os.path.basename(unique_output_path)
        gcs_url = upload_video_to_gcs(unique_output_path, gcs_filename)
        if gcs_url:
            logging.info(f"Video uploaded to GCS: {gcs_url}")
            _delete_file_safe(unique_output_path)
            return gcs_url
        else:
            logging.error("Video upload to GCS failed.")
            return unique_output_path

    except Exception as e:
        logging.error(f"Error during video assembly: {e}", exc_info=True)
        return None

    finally:
        if "audio_clip" in locals():
            audio_clip.close()
        for clip in all_clips_to_composite:
            if hasattr(clip, "close"):
                clip.close()
        if "final_clip" in locals():
            final_clip.close()

        # --- Cleanup only used images and audio ---
        # Remove only the files used for this video
        used_image_files = [p for p in graphic_filepaths if p and os.path.isfile(p) and not p.endswith("default_placeholder.png")]
        for img_fp in used_image_files:
            _delete_file_safe(img_fp)
        if audio_filepath and os.path.isfile(audio_filepath):
            _delete_file_safe(audio_filepath)


# --- Example usage wrapper ---
def build_video_from_pipeline_output(
    pipeline_output,
    font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    base_output_path="output_video.mp4",
):
    """
    pipeline_output: dict with keys 'audio_filepath', 'graphic_filepaths', 'script_parts_text', 'mark_timings'
    """
    return assemble_video_with_titles(
        graphic_filepaths=pipeline_output.get("graphic_filepaths"),
        audio_filepath=pipeline_output.get("audio_filepath"),
        script_parts_text=pipeline_output.get("script_parts_text"),
        part_timings=pipeline_output.get("mark_timings"),
        font_path=font_path,
        base_output_path=base_output_path,
    )