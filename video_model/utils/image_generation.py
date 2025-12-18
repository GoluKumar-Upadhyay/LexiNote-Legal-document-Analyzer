# --- image_generation.py ---
import os
import re
import logging
import requests
from PIL import Image
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import vertexai
from langchain_google_vertexai import ChatVertexAI, HarmBlockThreshold, HarmCategory
from requests.exceptions import RequestException
from google import genai
from google.genai.types import GenerateImagesConfig
import tempfile
import uuid
import shutil

load_dotenv()

# --- Global Configuration (Ensure consistency with app.py) ---
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")

vertexai.init(project=PROJECT_ID, location=LOCATION)

safety_settings = {
    HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

# This LLM config is NOT used by image generation directly, but included for context.
llm = ChatVertexAI(
    model="gemini-1.5-flash-001",
    temperature=0.3,
    max_output_tokens=8192,
    project=PROJECT_ID,
    safety_settings=safety_settings
)

genai_client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION
)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
if not PEXELS_API_KEY:
    logging.warning("PEXELS_API_KEY environment variable not set. Stock image search will be disabled.")


# --- Temporary Image Directory ---
IMAGE_TEMP_DIR = os.path.join(tempfile.gettempdir(), f"know_your_terms_images_{uuid.uuid4().hex[:6]}")
try:
    os.makedirs(IMAGE_TEMP_DIR, exist_ok=True)
    logging.info(f"Using temp directory for images: {IMAGE_TEMP_DIR}")
except OSError as e:
    logging.critical(f"FATAL: Could not create image temp directory {IMAGE_TEMP_DIR}: {e}")
    IMAGE_TEMP_DIR = "." # Fallback to current directory

# --- Ensure default placeholder image exists ---
def ensure_default_placeholder():
    test_images_dir = os.path.join(os.path.dirname(__file__), "..", "test_images")
    os.makedirs(test_images_dir, exist_ok=True)
    placeholder_path = os.path.join(test_images_dir, "default_placeholder.png")
    # If missing or empty, create a simple PNG
    if not os.path.exists(placeholder_path) or os.path.getsize(placeholder_path) < 100:
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGBA", (512, 320), (220, 220, 220, 255))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0,0),(511,319)], outline=(180,180,180,255), width=4)
            draw.text((120,140), "No Image", fill=(80,80,80,255))
            img.save(placeholder_path, "PNG")
            logging.info(f"Created default placeholder image at: {placeholder_path}")
        except Exception as e:
            logging.error(f"Failed to create default placeholder image: {e}")
    else:
        logging.info(f"Default placeholder image exists: {placeholder_path}")
    return placeholder_path

ensure_default_placeholder()


# --- Image Generation Functions (Unchanged from last optimization) ---
def generate_ai_image(prompt: str, output_filepath: str) -> str | None:
    """Generates an image using Google GenAI Imagen 4 and saves it to a local temporary path."""
    logging.info(f"Generating AI image for prompt: '{prompt[:70]}...' -> {os.path.basename(output_filepath)}")
    try:
        image_response = genai_client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config=GenerateImagesConfig(
                image_size="2K",
            ),
        )
        if image_response.generated_images:
            image_response.generated_images[0].image.save(output_filepath)
            
            if os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 100:
                logging.info(f"Successfully generated AI image: {os.path.basename(output_filepath)}")
                return output_filepath
            else:
                logging.error(f"AI image saved incorrectly or empty: {os.path.basename(output_filepath)}")
                if os.path.exists(output_filepath): os.remove(output_filepath)
                return None
        else:
            logging.error(f"AI image generation failed (API returned no images) for prompt: '{prompt[:70]}...'")
            return None
    except Exception as e:
        logging.error(f"Exception during GenAI image generation for '{prompt[:70]}...': {e}", exc_info=True)
        if os.path.exists(output_filepath):
            try: os.remove(output_filepath)
            except OSError: pass
        return None

def search_stock_images(query: str, num_images: int = 1, language: str = "en") -> list[str]:
    """Searches Pexels API for images."""
    logging.info(f"Searching Pexels for query: '{query}', lang: {language}")
    image_urls = []
    if not PEXELS_API_KEY:
        logging.error("PEXELS_API_KEY not set. Cannot search stock images.")
        return image_urls
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": query, "per_page": num_images, "locale": language}
        response = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        photos = data.get("photos", [])
        if photos:
            image_urls = [p.get("src", {}).get("large") or p.get("src", {}).get("original")
                          for p in photos if p.get("src")]
            image_urls = [url for url in image_urls if url]
        else:
            logging.warning(f"No Pexels images found for query: '{query}'")
    except RequestException as e:
        logging.error(f"Network error searching Pexels for '{query}': {e}")
    except Exception as e:
        logging.error(f"Exception during Pexels search for '{query}': {e}", exc_info=True)
    logging.info(f"Found {len(image_urls)} Pexels image URL(s) for '{query}'")
    return image_urls

def download_image(image_url: str, output_filepath: str) -> bool:
    """Downloads a single image from URL to a local temporary path."""
    logging.info(f"Downloading image from URL: {image_url} -> {os.path.basename(output_filepath)}")
    try:
        response = requests.get(image_url, stream=True, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get('content-type', '').lower()
        if not content_type.startswith('image/'):
            logging.warning(f"URL content is not an image (Content-Type: {content_type}): {image_url}")
            return False
        
        with open(output_filepath, 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
            
        if os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 100:
            logging.info(f"Successfully downloaded image: {os.path.basename(output_filepath)}")
            return True
        else:
            logging.error(f"Downloaded image empty/corrupt for: {os.path.basename(output_filepath)}")
            if os.path.exists(output_filepath): os.remove(output_filepath)
            return False
    except RequestException as e:
        logging.error(f"Network error downloading {image_url}: {e}")
        return False
    except Exception as e:
        logging.error(f"Exception downloading {image_url}: {e}", exc_info=True)
        if os.path.exists(output_filepath):
            try: os.remove(output_filepath)
            except OSError: pass
        return False

# --- Worker Function for ThreadPoolExecutor ---
def fetch_image_worker(query: str, use_ai: bool, language: str, output_dir: str) -> str | None:
    """
    Worker function to either generate an AI image or fetch a stock image.
    Returns the path to the *temporary* local file, or None on failure.
    """
    unique_id = uuid.uuid4().hex[:8]
    file_extension = ".png" if use_ai else ".jpg"
    safe_query_part = "".join(filter(str.isalnum, query.split()[:5]))[:40].lower()
    filename = f"{safe_query_part}_{unique_id}{file_extension}"
    output_filepath = os.path.join(output_dir, filename)

    # Directory for persistent images
    test_images_dir = os.path.join(os.path.dirname(__file__), "..", "test_images")
    os.makedirs(test_images_dir, exist_ok=True)
    test_images_path = os.path.join(test_images_dir, filename)

    result_path = None
    if use_ai:
        result_path = generate_ai_image(prompt=query, output_filepath=output_filepath)
    else:
        image_urls = search_stock_images(query, num_images=1, language=language)
        if image_urls:
            if download_image(image_urls[0], output_filepath=output_filepath):
                result_path = output_filepath
            else:
                logging.warning(f"Failed to download stock image for query: '{query}'")
        else:
            logging.warning(f"No stock images found for query: '{query}'")

    # If image was successfully created/downloaded, copy to test_images and return that path
    if result_path and os.path.exists(result_path) and os.path.getsize(result_path) > 100:
        try:
            import shutil
            shutil.copy2(result_path, test_images_path)
            logging.info(f"Copied image to test_images: {test_images_path}")
            return test_images_path
        except Exception as copy_err:
            logging.warning(f"Could not copy image to test_images: {copy_err}")
            return result_path  # fallback to temp path if copy fails
    return None

# --- Main Orchestrator Function (Optimized Parallel Handling) ---
def generate_images_for_prompts(
    image_prompts: list[str],
    use_ai_flags: list[bool],
    language: str = "en",
    max_workers: int = 5,
    fallback_image_path: str | None = None
) -> list[str | None]:
    """
    Generates/fetches images in parallel for a list of prompts.
    Returns a list of paths to the *temporary* local image files, or None for failures.
    """
    if len(image_prompts) != len(use_ai_flags):
        logging.error("Mismatched lengths for image_prompts and use_ai_flags.")
        raise ValueError("Length of image_prompts and use_ai_flags must match.")

    # Determine and validate the fallback image path ONCE
    valid_fallback_path = None
    if fallback_image_path:
        if os.path.exists(fallback_image_path) and os.path.getsize(fallback_image_path) > 100:
            valid_fallback_path = fallback_image_path
        else:
            logging.warning(f"Provided fallback_image_path '{fallback_image_path}' is invalid or missing. Will try default.")

    if not valid_fallback_path:
        default_fallback_path = os.path.join(os.path.dirname(__file__), "..", "test_images", "default_placeholder.png")
        if os.path.exists(default_fallback_path) and os.path.getsize(default_fallback_path) > 100:
            valid_fallback_path = default_fallback_path
            logging.info(f"Using default fallback image: {valid_fallback_path}")
        else:
            logging.critical(f"Default fallback image not found or empty at: {default_fallback_path}. No valid fallback available.")
            valid_fallback_path = None # Explicitly set to None if no valid fallback

    image_filepaths_ordered: list[str | None] = [None] * len(image_prompts)
    logging.info(f"Starting image processing for {len(image_prompts)} prompts (max_workers={max_workers}).")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(fetch_image_worker, prompt, use_ai, language, IMAGE_TEMP_DIR): idx
            for idx, (prompt, use_ai) in enumerate(zip(image_prompts, use_ai_flags))
        }

        processed_count = 0
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            prompt_for_log = image_prompts[idx]
            try:
                result_path = future.result() # This is the local temp path or None
                
                if result_path and os.path.exists(result_path) and os.path.getsize(result_path) > 100:
                    image_filepaths_ordered[idx] = result_path
                    logging.debug(f"Success for prompt index {idx} ('{prompt_for_log[:30]}...') -> {os.path.basename(result_path)}")
                elif valid_fallback_path:
                    image_filepaths_ordered[idx] = valid_fallback_path
                    logging.warning(f"Failed to get image for prompt index {idx} ('{prompt_for_log[:30]}...'), using fallback.")
                else:
                    image_filepaths_ordered[idx] = None
                    logging.error(f"Failed to get image for prompt index {idx} ('{prompt_for_log[:30]}...') and no valid fallback available.")
            except Exception as e:
                logging.error(f"Exception from future for prompt index {idx} ('{prompt_for_log[:30]}...'): {e}", exc_info=True)
                if valid_fallback_path:
                    image_filepaths_ordered[idx] = valid_fallback_path
                    logging.warning(f"Exception for prompt index {idx}, using fallback.")
                else:
                    image_filepaths_ordered[idx] = None
                    logging.error(f"Exception for prompt index {idx} and no valid fallback available.")
            processed_count += 1
            logging.info(f"Processed {processed_count}/{len(image_prompts)} image tasks.")

    # Final tally for logging
    valid_count = sum(1 for p in image_filepaths_ordered if p and p != valid_fallback_path)
    fallback_applied_count = sum(1 for p in image_filepaths_ordered if p == valid_fallback_path)
    failed_count = sum(1 for p in image_filepaths_ordered if p is None)

    logging.info(f"Image processing complete. Generated/Fetched: {valid_count}. Fallback used: {fallback_applied_count}. Failed (None): {failed_count}.")
    return image_filepaths_ordered