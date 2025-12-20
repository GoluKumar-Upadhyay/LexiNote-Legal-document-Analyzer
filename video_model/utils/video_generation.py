"""
Fixed Video Assembly WITHOUT text overlays (works without ImageMagick)
"""
import os
import logging
import uuid
from google.cloud import storage
from moviepy.editor import (
    CompositeVideoClip,
    ImageClip,
    AudioFileClip,
    ColorClip,
)
from PIL import Image

logger = logging.getLogger(__name__)

GCS_BUCKET_NAME = os.getenv("STORAGE_BUCKET_NAME")
GCS_VIDEO_URL_FORMAT = "https://storage.googleapis.com/{bucket}/{filename}"

VIDEO_SIZE = (1280, 720)  # 720p standard


def upload_video_to_gcs(local_path: str, gcs_filename: str) -> str | None:
    if not GCS_BUCKET_NAME:
        logger.warning("STORAGE_BUCKET_NAME not set. Skipping GCS upload.")
        return local_path

    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_filename)

        blob.upload_from_filename(local_path)
        blob.make_public()

        return GCS_VIDEO_URL_FORMAT.format(
            bucket=GCS_BUCKET_NAME,
            filename=gcs_filename
        )
    except Exception as e:
        logger.error(f"GCS upload failed: {e}")
        return local_path


def _delete_file_safe(filepath):
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass


def resize_image_safe(image_path, target_height):
    """
    Safely resize image using Pillow (handles ANTIALIAS deprecation)
    """
    try:
        img = Image.open(image_path)
        
        # Calculate new dimensions maintaining aspect ratio
        aspect_ratio = img.width / img.height
        new_width = int(target_height * aspect_ratio)
        
        # Use LANCZOS (replacement for ANTIALIAS in newer Pillow)
        try:
            resized = img.resize((new_width, target_height), Image.LANCZOS)
        except AttributeError:
            # Fallback for very old Pillow versions
            resized = img.resize((new_width, target_height), Image.ANTIALIAS)
        
        # Save to temp file
        temp_path = image_path.replace('.png', '_resized.png').replace('.jpg', '_resized.jpg')
        resized.save(temp_path)
        return temp_path
    except Exception as e:
        logger.warning(f"Could not resize image {image_path}: {e}")
        return image_path


def assemble_video_with_titles(
    graphic_filepaths: list[str],
    audio_filepath: str,
    script_parts_text: list[str],
    part_timings: list[tuple[str, float]] | None = None,
    font_path: str | None = None,
    base_output_path: str = "output_video.mp4",
    title_duration: float = 2.0
) -> str | None:
    """
    Assemble video with ONLY images and audio (no text overlays)
    This works without ImageMagick installation
    """

    all_clips = []
    base, ext = os.path.splitext(base_output_path)
    unique_output_path = f"{base}_{uuid.uuid4().hex[:8]}{ext}"

    audio_clip = None
    resized_images = []  # Track resized images for cleanup

    try:
        # Validate audio file
        if not audio_filepath or not os.path.exists(audio_filepath):
            logger.error(f"Audio file missing: {audio_filepath}")
            return None

        audio_clip = AudioFileClip(audio_filepath)
        total_duration = audio_clip.duration

        if total_duration <= 0:
            logger.error("Audio duration is zero or negative")
            return None

        logger.info(f"Creating video without text overlays (ImageMagick not required)")

        # Create background
        background = ColorClip(
            size=VIDEO_SIZE,
            color=(30, 30, 30)  # Dark background
        ).set_duration(total_duration)

        all_clips.append(background)

        num_parts = len(script_parts_text)

        # Calculate timings
        if part_timings:
            timings = [
                next((t for m, t in part_timings if m == f"part_{i}_end"), None)
                for i in range(num_parts)
            ]
        else:
            timings = [total_duration * (i + 1) / num_parts for i in range(num_parts)]

        # Validate graphic filepaths
        for i, path in enumerate(graphic_filepaths):
            if not path or not os.path.exists(path):
                logger.error(f"Invalid graphic path at index {i}: {path}")
                raise ValueError(f"All graphic paths must be valid. Invalid at index {i}")

        part_start_time = 0.0

        for i, script_part in enumerate(script_parts_text):
            part_end_time = timings[i] if timings[i] else total_duration
            part_duration = max(0.5, part_end_time - part_start_time)

            # ---------- IMAGE ----------
            if i < len(graphic_filepaths) and graphic_filepaths[i]:
                graphic_path = graphic_filepaths[i]
                if os.path.exists(graphic_path):
                    try:
                        # Resize image safely
                        target_height = int(VIDEO_SIZE[1] * 0.85)  # Use more vertical space
                        resized_path = resize_image_safe(graphic_path, target_height)
                        if resized_path != graphic_path:
                            resized_images.append(resized_path)
                        
                        img_clip = ImageClip(resized_path) \
                            .set_start(part_start_time) \
                            .set_duration(part_duration) \
                            .set_position("center")
                        
                        all_clips.append(img_clip)
                        logger.info(f"Added image for part {i+1}: {os.path.basename(graphic_path)}")
                        
                    except Exception as img_err:
                        logger.warning(f"Could not load image {graphic_path}: {img_err}")
                else:
                    logger.warning(f"Image file not found: {graphic_path}")

            part_start_time = part_end_time

        # Assemble final video
        logger.info(f"Assembling video with {len(all_clips)} clips...")
        final_clip = CompositeVideoClip(all_clips, size=VIDEO_SIZE)
        final_clip = final_clip.set_audio(audio_clip).set_duration(total_duration)

        logger.info(f"Writing video to {unique_output_path}...")
        final_clip.write_videofile(
            unique_output_path,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            threads=4,
            verbose=False,
            logger=None
        )

        if not os.path.exists(unique_output_path) or os.path.getsize(unique_output_path) < 1000:
            logger.error("Video file was not created or is too small")
            return None

        logger.info(f"✓ Video created successfully: {unique_output_path}")

        final_url = upload_video_to_gcs(
            unique_output_path,
            os.path.basename(unique_output_path)
        )

        return final_url

    except Exception as e:
        logger.error(f"Video assembly error: {e}", exc_info=True)
        return None

    finally:
        # Cleanup
        if audio_clip:
            audio_clip.close()
        for clip in all_clips:
            try:
                clip.close()
            except:
                pass
        
        # Delete resized temp images
        for resized_path in resized_images:
            _delete_file_safe(resized_path)
            
        _delete_file_safe(audio_filepath)



def build_video_from_pipeline_output(
    pipeline_output: dict,
    font_path: str | None = None,
    base_output_path: str = "output_video.mp4"
) -> str | None:
    """
    Wrapper to build video from pipeline output dictionary.
    
    Expected keys:
        - audio_filepath: str
        - graphic_filepaths: list[str]
        - script_parts_text: list[str]
        - mark_timings: list[tuple[str, float]] or None
    """
    return assemble_video_with_titles(
        graphic_filepaths=pipeline_output.get("graphic_filepaths", []),
        audio_filepath=pipeline_output.get("audio_filepath"),
        script_parts_text=pipeline_output.get("script_parts_text", []),
        part_timings=pipeline_output.get("mark_timings"),
        font_path=font_path,
        base_output_path=base_output_path
    )