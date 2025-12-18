# --- audio_generation_rest.py ---

import os
import re
import logging
import tempfile
import uuid
import requests
import json
import base64
import shutil
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from requests.exceptions import HTTPError, RequestException
from pydub import AudioSegment

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s')

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
credentials = None

if SERVICE_ACCOUNT_FILE and os.path.exists(SERVICE_ACCOUNT_FILE):
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        logging.info(f"Service account credentials loaded successfully from {SERVICE_ACCOUNT_FILE} for REST API.")
    except Exception as e:
        logging.critical(f"FATAL: Failed to load service account credentials from {SERVICE_ACCOUNT_FILE}: {e}")
else:
    logging.critical(f"FATAL: SERVICE_ACCOUNT_CREDENTIALS env var not set or file does not exist at path: {SERVICE_ACCOUNT_FILE}")


def split_ssml_by_marks(ssml_text: str, max_bytes: int = 4500) -> list[tuple[str, list[str]]]:
    """
    Splits SSML text into chunks that fit within byte limit.
    Returns list of (ssml_chunk, mark_names_in_chunk) tuples.
    """
    # Extract all parts between <p> tags with their marks
    parts_pattern = r'<p>(.*?)</p><mark name="(.*?)"\s*/>'
    matches = re.findall(parts_pattern, ssml_text, re.DOTALL)
    
    if not matches:
        logging.error("Could not parse SSML parts")
        return []
    
    chunks = []
    current_chunk_parts = []
    current_chunk_marks = []
    current_size = len('<speak></speak>'.encode('utf-8'))
    
    for text, mark_name in matches:
        part_ssml = f'<p>{text}</p><mark name="{mark_name}"/>'
        part_size = len(part_ssml.encode('utf-8'))
        
        if current_size + part_size > max_bytes and current_chunk_parts:
            # Save current chunk
            chunk_ssml = f"<speak>{''.join(current_chunk_parts)}</speak>"
            chunks.append((chunk_ssml, current_chunk_marks))
            
            # Start new chunk
            current_chunk_parts = [part_ssml]
            current_chunk_marks = [mark_name]
            current_size = len('<speak></speak>'.encode('utf-8')) + part_size
        else:
            current_chunk_parts.append(part_ssml)
            current_chunk_marks.append(mark_name)
            current_size += part_size
    
    # Add last chunk
    if current_chunk_parts:
        chunk_ssml = f"<speak>{''.join(current_chunk_parts)}</speak>"
        chunks.append((chunk_ssml, current_chunk_marks))
    
    logging.info(f"Split SSML into {len(chunks)} chunks")
    return chunks


def generate_audio_chunk(ssml_text: str, language_code: str, chunk_index: int) -> tuple[str | None, list[tuple[str, float]] | None]:
    """Generate audio for a single SSML chunk."""
    if not credentials:
        logging.error("Google Cloud credentials not available.")
        return None, None
    
    request_body = {
        "input": {"ssml": ssml_text},
        "voice": {"languageCode": language_code},
        "audioConfig": {"audioEncoding": "MP3"},
        "enableTimePointing": ["SSML_MARK"]
    }
    
    # Voice selection
    if language_code in ["en-IN", "en"]:
        request_body["voice"]["name"] = "en-IN-Wavenet-A"
        request_body["voice"]["ssmlGender"] = "MALE"
    elif language_code in ["hi-IN", "hi"]:
        request_body["voice"]["name"] = "hi-IN-Wavenet-D"
        request_body["voice"]["ssmlGender"] = "MALE"
    else:
        request_body["voice"]["ssmlGender"] = "NEUTRAL"
    
    try:
        credentials.refresh(Request())
    except Exception as auth_err:
        logging.error(f"Failed to refresh auth token: {auth_err}")
        return None, None
    
    auth_token = credentials.token
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    rest_api_url = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"
    
    unique_id = uuid.uuid4().hex[:8]
    output_filename = f"audio_chunk_{chunk_index}_{language_code}_{unique_id}.mp3"
    test_audio_dir = os.path.join(os.path.dirname(__file__), "..", "test_audio")
    test_audio_dir = os.path.abspath(test_audio_dir)
    os.makedirs(test_audio_dir, exist_ok=True)
    audio_filepath = os.path.join(test_audio_dir, output_filename)
    
    try:
        response = requests.post(rest_api_url, headers=headers, json=request_body, timeout=60)
        response.raise_for_status()
        response_data = response.json()
        
        audio_content_base64 = response_data.get("audioContent")
        if not audio_content_base64:
            logging.error("API response did not contain audioContent.")
            return None, None
        
        audio_bytes = base64.b64decode(audio_content_base64)
        
        with open(audio_filepath, "wb") as out:
            out.write(audio_bytes)
        
        if not os.path.exists(audio_filepath) or os.path.getsize(audio_filepath) == 0:
            logging.error(f"Failed to write audio chunk {chunk_index}")
            return None, None
        
        logging.info(f"Audio chunk {chunk_index} written successfully")
        
        # Process timings
        mark_timings = []
        timepoints_data = response_data.get("timepoints")
        if timepoints_data:
            mark_names = re.findall(r'<mark name=["\'](.*?)["\']\s*/>', ssml_text)
            if len(mark_names) == len(timepoints_data):
                for i, point in enumerate(timepoints_data):
                    mark = mark_names[i]
                    time_sec = float(point.get("timeSeconds", 0.0))
                    mark_timings.append((mark, time_sec))
            else:
                logging.warning(f"Timing mismatch in chunk {chunk_index}")
        
        return audio_filepath, mark_timings
    
    except HTTPError as http_err:
        logging.error(f"HTTP error in chunk {chunk_index}: {http_err} - {http_err.response.text}")
        return None, None
    except Exception as e:
        logging.error(f"Error in chunk {chunk_index}: {e}", exc_info=True)
        if os.path.exists(audio_filepath):
            try: os.remove(audio_filepath)
            except OSError: pass
        return None, None


def merge_audio_files(audio_filepaths: list[str], output_filepath: str) -> bool:
    """Merge multiple MP3 files into one."""
    try:
        combined = AudioSegment.empty()
        for filepath in audio_filepaths:
            if filepath and os.path.exists(filepath):
                audio = AudioSegment.from_mp3(filepath)
                combined += audio
        
        combined.export(output_filepath, format="mp3")
        logging.info(f"Merged {len(audio_filepaths)} audio chunks into {output_filepath}")
        
        # Cleanup individual chunks
        for filepath in audio_filepaths:
            if filepath and os.path.exists(filepath):
                try: os.remove(filepath)
                except OSError: pass
        
        return True
    except Exception as e:
        logging.error(f"Failed to merge audio files: {e}")
        return False


def generate_tts_audio_with_timing(
    script_text: str,
    language_code: str = "en-IN",
    output_filename_base: str = "summary_audio"
) -> tuple[str | None, list[tuple[str, float]] | None]:
    """
    Generates audio and SSML mark timings, handling long text by chunking.
    Returns the path to the audio file and a list of (mark_name, time_seconds) tuples.
    """
    if not credentials:
        logging.error("Google Cloud credentials not available.")
        return None, None
    
    if not script_text or not script_text.strip():
        logging.error("Cannot generate audio from empty script text.")
        return None, None
    
    logging.info(f"Requesting TTS audio for language: {language_code}")
    
    # Check if text is too long
    text_bytes = len(script_text.encode('utf-8'))
    logging.info(f"SSML text size: {text_bytes} bytes")
    
    if text_bytes > 4800:  # Leave some margin
        logging.info("Text exceeds limit, splitting into chunks...")
        chunks = split_ssml_by_marks(script_text)
        
        if not chunks:
            logging.error("Failed to split SSML into chunks")
            return None, None
        
        audio_filepaths = []
        all_timings = []
        cumulative_time = 0.0
        
        for idx, (chunk_ssml, chunk_marks) in enumerate(chunks):
            audio_path, timings = generate_audio_chunk(chunk_ssml, language_code, idx)
            
            if not audio_path:
                logging.error(f"Failed to generate chunk {idx}")
                return None, None
            
            audio_filepaths.append(audio_path)
            
            # Adjust timings with cumulative offset
            if timings:
                adjusted_timings = [(mark, time + cumulative_time) for mark, time in timings]
                all_timings.extend(adjusted_timings)
                
                # Get duration of this chunk to offset next chunk
                try:
                    chunk_audio = AudioSegment.from_mp3(audio_path)
                    cumulative_time += len(chunk_audio) / 1000.0  # Convert ms to seconds
                except Exception as e:
                    logging.error(f"Failed to get chunk duration: {e}")
        
        # Merge all chunks
        unique_id = uuid.uuid4().hex[:8]
        output_filename = f"{output_filename_base}_{language_code}_{unique_id}.mp3"
        test_audio_dir = os.path.join(os.path.dirname(__file__), "..", "test_audio")
        final_audio_path = os.path.join(test_audio_dir, output_filename)
        
        if merge_audio_files(audio_filepaths, final_audio_path):
            return final_audio_path, all_timings
        else:
            return None, None
    
    else:
        # Original single-chunk logic
        return generate_audio_chunk(script_text, language_code, 0)