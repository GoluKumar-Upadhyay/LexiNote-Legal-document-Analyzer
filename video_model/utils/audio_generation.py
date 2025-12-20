"""
Fixed Audio Generation with proper validation and error handling
"""
import os
import re
import logging
import tempfile
import uuid
import base64
import shutil
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from requests. exceptions import HTTPError, RequestException
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Credential Loading ---
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
credentials = None

if SERVICE_ACCOUNT_FILE and os.path.exists(SERVICE_ACCOUNT_FILE):
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        logger.info(f"Service account credentials loaded from {SERVICE_ACCOUNT_FILE}")
    except Exception as e: 
        logger.critical(f"FATAL: Failed to load credentials: {e}")
else:
    logger.critical(f"FATAL: SERVICE_ACCOUNT_CREDENTIALS not set or invalid path")


def generate_tts_audio_with_timing(
    script_text:  str,
    language_code:  str = "en-IN",
    output_filename_base: str = "summary_audio"
) -> tuple[str | None, list[tuple[str, float]] | None]:
    """
    Generates audio and SSML mark timings using Google Cloud TTS REST API v1beta1. 
    
    Args:
        script_text:  SSML formatted script with <mark> tags
        language_code:  Language code (e.g., "en-IN", "hi-IN")
        output_filename_base: Base filename for audio output
    
    Returns:
        Tuple of (audio_filepath, mark_timings_list) or (None, None) on failure
    """
    # Validation
    if not credentials:
        logger.error("Google Cloud credentials not available.")
        return None, None
    
    if not script_text or not script_text.strip():
        logger.error("Cannot generate audio from empty script text.")
        return None, None

    logger.info(f"Generating TTS audio for language:  {language_code}")

    # Request body with SSML mark timing support
    request_body = {
        "input": {"ssml": script_text},
        "voice":  {"languageCode": language_code},
        "audioConfig": {"audioEncoding": "MP3"},
        "enableTimePointing": ["SSML_MARK"]
    }

    # Voice selection based on language
    if language_code in ["en-IN", "en"]:
        request_body["voice"]["name"] = "en-IN-Wavenet-A"
        request_body["voice"]["ssmlGender"] = "MALE"
        logger.info("Using voice: en-IN-Wavenet-A (Male)")
    elif language_code in ["hi-IN", "hi"]:
        request_body["voice"]["name"] = "hi-IN-Wavenet-D"
        request_body["voice"]["ssmlGender"] = "MALE"
        logger.info("Using voice: hi-IN-Wavenet-D (Male)")
    else:
        request_body["voice"]["ssmlGender"] = "NEUTRAL"
        logger.info(f"Using NEUTRAL voice for {language_code}")

    # Refresh credentials
    try:
        credentials. refresh(Request())
    except Exception as auth_err:
        logger.error(f"Failed to refresh auth token: {auth_err}")
        return None, None

    auth_token = credentials.token
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    rest_api_url = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"

    # Create test_audio directory
    test_audio_dir = os.path.join(os.path.dirname(__file__), "..", "test_audio")
    test_audio_dir = os.path.abspath(test_audio_dir)
    try:
        os.makedirs(test_audio_dir, exist_ok=True)
    except Exception as dir_err:
        logger.error(f"Could not create test_audio directory: {dir_err}")
        test_audio_dir = tempfile.gettempdir()

    unique_id = uuid.uuid4().hex[:8]
    output_filename = f"{output_filename_base}_{language_code}_{unique_id}. mp3"
    audio_filepath = os.path.join(test_audio_dir, output_filename)

    try:
        logger.debug(f"Making REST API call to {rest_api_url}")
        response = requests.post(
            rest_api_url,
            headers=headers,
            json=request_body,
            timeout=60
        )
        response.raise_for_status()

        response_data = response.json()

        # Decode and save audio content
        audio_content_base64 = response_data.get("audioContent")
        if not audio_content_base64:
            logger.error("API response did not contain audioContent.")
            return None, None

        audio_bytes = base64.b64decode(audio_content_base64)

        with open(audio_filepath, "wb") as out: 
            out.write(audio_bytes)

        # Verify file was written
        if not os.path. exists(audio_filepath):
            logger.error(f"Failed to write audio file: {audio_filepath}")
            return None, None

        file_size = os.path.getsize(audio_filepath)
        if file_size < 1000:
            logger.error(f"Audio file too small ({file_size} bytes): {audio_filepath}")
            os.remove(audio_filepath)
            return None, None

        logger.info(f'Audio saved successfully: {os.path.basename(audio_filepath)} ({file_size} bytes)')

        # Extract timing information
        mark_timings = []
        timepoints_data = response_data.get("timepoints", [])
        
        if timepoints_data:
            # Extract mark names from SSML
            mark_names = re.findall(r'<mark name=["\'](.*?)["\']\s*/>', script_text)
            
            if len(mark_names) == len(timepoints_data):
                for i, point in enumerate(timepoints_data):
                    mark = mark_names[i]
                    time_sec = float(point.get("timeSeconds", 0.0))
                    mark_timings.append((mark, time_sec))
                logger.info(f"Extracted {len(mark_timings)} SSML mark timings")
            else:
                logger. warning(
                    f"TIMING MISMATCH: {len(mark_names)} marks vs "
                    f"{len(timepoints_data)} timepoints. Using None for timings."
                )
                mark_timings = None
        else:
            logger.warning("No timepoints returned from API")
            mark_timings = None

        return audio_filepath, mark_timings

    except HTTPError as http_err:
        logger.error(f"HTTP error:  {http_err.response.status_code} - {http_err.response.text}")
        return None, None
    except RequestException as req_err:
        logger.error(f"Request error: {req_err}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        if os.path.exists(audio_filepath):
            try:
                os.remove(audio_filepath)
            except OSError:
                pass
        return None, None