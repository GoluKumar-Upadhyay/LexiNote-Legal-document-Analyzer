"""
Fixed Image Generation with proper quota management and fallback handling
"""
import os
import logging
import requests
import tempfile
import uuid
import shutil
import time
from PIL import Image
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.exceptions import RequestException
from google import genai
from google.genai.types import GenerateImagesConfig
import vertexai
from langchain_google_vertexai import ChatVertexAI, HarmBlockThreshold, HarmCategory

load_dotenv()

logger = logging.getLogger(__name__)

try:
    vertex_key_path = os.getenv("VERTEX_AI_KEY")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = vertex_key_path
    PROJECT_ID = os.getenv("PROJECT_ID")
    vertexai.init(project=PROJECT_ID, location="us-central1")

    safety_settings = {
        HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }

    llm = ChatVertexAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2,
        max_output_tokens=8148,
        project=PROJECT_ID,
        safety_settings=safety_settings
    )

except Exception as e:
    logging.critical(f"Failed to initialize Vertex AI: {e}", exc_info=True)
    llm = None


genai_client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location="us-central1"
)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
if not PEXELS_API_KEY:
    logger.warning("PEXELS_API_KEY not set. Stock image search disabled.")

# --- Temporary Image Directory ---
IMAGE_TEMP_DIR = os.path.join(tempfile.gettempdir(), f"video_generator_images_{uuid.uuid4().hex[:6]}")
try:
    os.makedirs(IMAGE_TEMP_DIR, exist_ok=True)
    logger.info(f"Using temp directory for images: {IMAGE_TEMP_DIR}")
except OSError as e:
    logger.critical(f"Could not create image temp directory: {e}")
    IMAGE_TEMP_DIR = tempfile.gettempdir()


def ensure_default_placeholder():
    """Create default placeholder image if missing"""
    test_images_dir = os.path.join(os.path.dirname(__file__), "..", "test_images")
    os.makedirs(test_images_dir, exist_ok=True)
    
    placeholder_path = os.path.join(test_images_dir, "default_placeholder.png")
    
    if not os.path.exists(placeholder_path) or os.path.getsize(placeholder_path) < 100:
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new("RGB", (1280, 720), (240, 240, 240))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(10, 10), (1270, 710)], outline=(180, 180, 180), width=8)
            
            # Try to use a font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", 60)
            except:
                font = ImageFont.load_default()
            
            text = "Image Placeholder"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (1280 - text_width) // 2
            y = (720 - text_height) // 2
            
            draw.text((x, y), text, fill=(100, 100, 100), font=font)
            img.save(placeholder_path, "PNG")
            logger.info(f"Created default placeholder: {placeholder_path}")
        except Exception as e:
            logger.error(f"Failed to create placeholder: {e}")
    
    return placeholder_path


ensure_default_placeholder()


def generate_ai_image(prompt: str, output_filepath: str, retry_count: int = 0, max_retries: int = 2) -> str | None:
    """Generate image using Google GenAI Imagen with retry logic"""
    logger.info(f"Generating AI image (attempt {retry_count + 1}/{max_retries + 1}): '{prompt[:50]}...'")
    
    try:
        image_response = genai_client.models.generate_images(
            model="imagen-3.0-generate-001",
            prompt=prompt,
            config=GenerateImagesConfig(image_size="2K"),
        )
        
        if image_response.generated_images:
            image_response.generated_images[0].image.save(output_filepath)
            
            # Validate saved file
            if os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 100:
                logger.info(f"✓ AI image generated: {os.path.basename(output_filepath)}")
                return output_filepath
            else:
                logger.error(f"Generated image is empty: {output_filepath}")
                if os.path.exists(output_filepath):
                    os.remove(output_filepath)
                return None
        else:
            logger.error(f"AI image generation failed (no images returned)")
            return None
            
    except Exception as e:
        error_msg = str(e)
        
        # Check if it's a quota error
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            logger.warning(f"Quota exceeded for AI image generation")
            
            # If we have retries left, wait and try again
            if retry_count < max_retries:
                wait_time = 5 * (retry_count + 1)  # Progressive backoff: 5s, 10s
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                return generate_ai_image(prompt, output_filepath, retry_count + 1, max_retries)
            else:
                logger.error(f"Max retries reached, falling back to stock images")
                return None
        else:
            logger.error(f"Exception during AI image generation: {e}")
            
        if os.path.exists(output_filepath):
            try:
                os.remove(output_filepath)
            except OSError:
                pass
        return None


def search_stock_images(query: str, num_images: int = 1, language: str = "en") -> list[str]:
    """Search Pexels for stock images"""
    logger.info(f"Searching Pexels for: '{query}'")
    
    image_urls = []
    if not PEXELS_API_KEY:
        logger.error("PEXELS_API_KEY not set")
        return image_urls
    
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": query, "per_page": num_images, "locale": language}
        
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        photos = data.get("photos", [])
        
        if photos:
            image_urls = [
                p.get("src", {}).get("large") or p.get("src", {}).get("original")
                for p in photos if p.get("src")
            ]
            image_urls = [url for url in image_urls if url]
            logger.info(f"Found {len(image_urls)} Pexels images")
        else:
            logger.warning(f"No Pexels images found for: '{query}'")
            
    except RequestException as e:
        logger.error(f"Network error searching Pexels: {e}")
    except Exception as e:
        logger.error(f"Exception during Pexels search: {e}", exc_info=True)
    
    return image_urls


def download_image(image_url: str, output_filepath: str) -> bool:
    """Download image from URL"""
    logger.info(f"Downloading image: {image_url}")
    
    try:
        response = requests.get(image_url, stream=True, timeout=30)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '').lower()
        if not content_type.startswith('image/'):
            logger.warning(f"URL is not an image (Content-Type: {content_type})")
            return False
        
        with open(output_filepath, 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
        
        # Validate downloaded file
        if os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 100:
            logger.info(f"✓ Image downloaded: {os.path.basename(output_filepath)}")
            return True
        else:
            logger.error(f"Downloaded image is empty")
            if os.path.exists(output_filepath):
                os.remove(output_filepath)
            return False
            
    except RequestException as e:
        logger.error(f"Network error downloading image: {e}")
        return False
    except Exception as e:
        logger.error(f"Exception downloading image: {e}", exc_info=True)
        if os.path.exists(output_filepath):
            try:
                os.remove(output_filepath)
            except OSError:
                pass
        return False


def fetch_image_worker(query: str, use_ai: bool, language: str, output_dir: str) -> str | None:
    """Worker to generate or fetch a single image with fallback to placeholder"""
    unique_id = uuid.uuid4().hex[:8]
    file_extension = ".png" if use_ai else ".jpg"
    safe_query_part = "".join(filter(str.isalnum, query.split()[:5]))[:40].lower()
    filename = f"{safe_query_part}_{unique_id}{file_extension}"
    output_filepath = os.path.join(output_dir, filename)

    result_path = None
    
    # Try AI generation first if requested
    if use_ai:
        result_path = generate_ai_image(prompt=query, output_filepath=output_filepath)
    
    # Fallback to stock images if AI fails
    if not result_path:
        logger.info(f"Falling back to stock images for: '{query}'")
        image_urls = search_stock_images(query, num_images=1, language=language)
        if image_urls:
            if download_image(image_urls[0], output_filepath=output_filepath):
                result_path = output_filepath
    
    # Final fallback to placeholder
    if not result_path or not os.path.exists(result_path):
        logger.warning(f"All methods failed, using placeholder for: '{query}'")
        result_path = ensure_default_placeholder()

    # Persist to test_images directory
    if result_path and os.path.exists(result_path) and os.path.getsize(result_path) > 100:
        test_images_dir = os.path.join(os.path.dirname(__file__), "..", "test_images")
        os.makedirs(test_images_dir, exist_ok=True)
        test_images_path = os.path.join(test_images_dir, filename)
        
        try:
            shutil.copy2(result_path, test_images_path)
            logger.info(f"Copied image to test_images: {test_images_path}")
            return test_images_path
        except Exception as copy_err:
            logger.warning(f"Could not copy to test_images: {copy_err}")
            return result_path
    
    return result_path


def generate_images_for_prompts(
    image_prompts: list[str],
    use_ai_flags: list[bool],
    language: str = "en",
    max_workers: int = 1,
    fallback_image_path: str | None = None
) -> list[str]:
    """
    Fixed version with better error handling and guaranteed valid image paths.
    """
    if len(image_prompts) != len(use_ai_flags):
        logger.error("Mismatched lengths for image_prompts and use_ai_flags")
        raise ValueError("Length mismatch")

    valid_fallback_path = None
    if fallback_image_path and os.path.exists(fallback_image_path):
        valid_fallback_path = fallback_image_path
    if not valid_fallback_path:
        valid_fallback_path = ensure_default_placeholder()

    image_filepaths = []
    
    logger.info(f"Generating {len(image_prompts)} images sequentially to respect quota...")

    for idx, (prompt, use_ai) in enumerate(zip(image_prompts, use_ai_flags)):
        logger.info(f"Processing image {idx + 1}/{len(image_prompts)}")
        
        try:
            result_path = fetch_image_worker(prompt, use_ai, language, IMAGE_TEMP_DIR)
            
            # Ensure we always have a valid path
            if result_path and os.path.exists(result_path) and os.path.getsize(result_path) > 100:
                image_filepaths.append(result_path)
            else:
                logger.warning(f"Invalid result for image {idx + 1}, using fallback")
                image_filepaths.append(valid_fallback_path)
            
            # Delay between requests (longer for AI)
            if use_ai and idx < len(image_prompts) - 1:
                time.sleep(5)  # Increased from 2 to 5 seconds
            elif idx < len(image_prompts) - 1:
                time.sleep(1)  # Small delay for stock images too
                
        except Exception as e:
            logger.error(f"Error on image {idx + 1}: {e}")
            image_filepaths.append(valid_fallback_path)

    # Final validation - ensure all paths are valid
    for i, path in enumerate(image_filepaths):
        if not path or not os.path.exists(path):
            logger.warning(f"Invalid path at index {i}, replacing with fallback")
            image_filepaths[i] = valid_fallback_path

    logger.info(f"✓ Image generation complete: {len(image_filepaths)} valid paths")
    return image_filepaths