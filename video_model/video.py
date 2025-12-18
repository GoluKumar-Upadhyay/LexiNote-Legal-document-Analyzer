import os, re
import logging
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from google.cloud import language_v1
from google.cloud import texttospeech
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.prompts import PromptTemplate
import vertexai
from langchain_google_vertexai import ChatVertexAI, HarmBlockThreshold, HarmCategory
from requests.exceptions import RequestException
from utils.script import create_script_and_image_prompts, generate_script_and_image_prompts
from utils.image_generation import generate_images_for_prompts
from utils.audio_generation import generate_tts_audio_with_timing
from utils.video_generation import build_video_from_pipeline_output
from flask_cors import CORS



# from utils.image_generation import generate_images_for_prompts
load_dotenv()

language_client = language_v1.LanguageServiceClient()
tts_client = texttospeech.TextToSpeechClient()
vertex_key_path = os.getenv("VERTEX_AI_KEY")
indiankanoon_key = os.getenv("KANOON_API_KEY")
pixel_key = os.getenv("PEXELS_API_KEY")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")

VERTEX_AI_CREDENTIALS = os.getenv("VERTEX_AI_CREDENTIALS")
if VERTEX_AI_CREDENTIALS:
    os.environ["VERTEX_AI_CREDENTIALS"] = VERTEX_AI_CREDENTIALS

vertexai.init(project=PROJECT_ID, location=LOCATION)

safety_settings = {
    HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

llm = ChatVertexAI(
    model="gemini-2.5-flash",
    temperature=0.3,
    max_output_tokens=2048,
    project=PROJECT_ID,
    safety_settings=safety_settings
)

app = Flask(__name__)
CORS(app)


# Video Generation Pipeline
def generate_video_pipeline(summary_text, language="en", category="business"):
    print("Script Parts: ", language, category)
    script_parts, image_prompts, ssml_text = generate_script_and_image_prompts(summary_text, language, category)
    print("Script Parts: ", ssml_text)
    audio_filepath, mark_timings = None, None
    if ssml_text:

        audio_filepath, mark_timings = generate_tts_audio_with_timing(
            script_text=ssml_text,
            language_code=language
        )
    else:
        logging.error("Script generation failed, cannot generate audio.")

    use_ai_flags = [True] * len(image_prompts)  # For simplicity, use AI for all prompts
    graphic_filepaths = generate_images_for_prompts(
        image_prompts=image_prompts,
        use_ai_flags=use_ai_flags,
        language=language
    )

    pipeline_input = {
        "audio_filepath": audio_filepath,
        "graphic_filepaths": graphic_filepaths,
        "script_parts_text": script_parts,
        "mark_timings": mark_timings
    }
    video_path = build_video_from_pipeline_output(pipeline_input)

    return {
        'video_path': video_path
    }

# --- Flask API Router ---

@app.route("/health", methods=["GET"])
def health():
    return "active"

@app.route('/generate_video', methods=['POST'])
def uploads():
    category = request.form.get("category")
    summary_text = request.form.get("summary_text")
    language = request.form.get("language", "en")

    if not summary_text or not category or not language:
        return jsonify({
            "error": "Missing summary_text, category, or language"
        }), 400
    
    # Call your existing function
    result = generate_video_pipeline(summary_text, language, category)

    # Return JSON directly
    return jsonify(result)

@app.route('/generate_script', methods=['POST'])
def generate_script_api():
    category = request.form.get("category")
    summary_text = request.form.get("summary_text")
    language = request.form.get("language", "en")

    if not summary_text or not category or not language:
        return jsonify({
            "error": "Missing summary_text, category, or language"
        }), 400
    
    # Call your existing function
    result = generate_script_and_image_prompts(summary_text, category, language)

    # Return JSON directly
    return jsonify(result)

@app.route('/generate_images', methods=['POST'])
def generate_images_api():

    data = request.get_json()
    image_prompts = data.get("image_queries") # Match key from Postman
    use_ai_flags = data.get("use_ai_flags")
    language = data.get("language", "en")
    # Add fallback image path from config or default
    fallback_img_path = os.getenv("FALLBACK_IMAGE_PATH", "path/to/default_placeholder.png") # Provide a default path

    # Basic Input Validation
    if not isinstance(image_prompts, list) or not isinstance(use_ai_flags, list):
        return jsonify({"error": "image_queries and use_ai_flags must be lists."}), 400
    if len(image_prompts) != len(use_ai_flags):
         return jsonify({"error": "image_queries and use_ai_flags must have the same length."}), 400
    if not all(isinstance(p, str) for p in image_prompts):
         return jsonify({"error": "image_queries must contain only strings."}), 400
    if not all(isinstance(f, bool) for f in use_ai_flags):
         return jsonify({"error": "use_ai_flags must contain only booleans."}), 400

        # Call the main orchestrator function
    result_paths = generate_images_for_prompts(
        image_prompts=image_prompts,
        use_ai_flags=use_ai_flags,
        language=language,
        fallback_image_path=fallback_img_path
    )

    # Return the full list including None/fallbacks
    return jsonify(result_paths)

@app.route('/generate_audio', methods=['POST'])
def generate_audio_api():

    data = request.get_json()
    summary_text = data.get("summary_text") # Match key from Postman
    language = data.get("language", "en-IN")

        # Call the main orchestrator function
    result_paths = generate_tts_audio_with_timing(
        script_text=summary_text,
        language_code=language,
    )

    # Return the full list including None/fallbacks
    return jsonify(result_paths)

@app.route('/generate_1video', methods=['POST'])
def generate_video_api():
    data = request.get_json()
    # Accept direct input for video assembly
    audio_filepath = data.get("audio_filepath")
    graphic_filepaths = data.get("graphic_filepaths")
    script_parts_text = data.get("script_parts_text")
    part_timings = data.get("mark_timings")
    font_path = data.get("font_path", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    base_output_path = data.get("output_path", "output_video.mp4")

    # Validate required fields
    if not audio_filepath or not graphic_filepaths or not script_parts_text:
        return jsonify({"error": "Missing required fields: audio_filepath, graphic_filepaths, script_parts_text"}), 400

    pipeline_input = {
        "audio_filepath": audio_filepath,
        "graphic_filepaths": graphic_filepaths,
        "script_parts_text": script_parts_text,
        "mark_timings": part_timings
    }
    video_path = build_video_from_pipeline_output(
        pipeline_input,
        font_path=font_path,
        base_output_path=base_output_path
    )

    if video_path:
        return jsonify({"video_path": video_path})
    else:
        return jsonify({"error": "Video generation failed"}), 500

@app.route("/active", methods=["GET"])
def active():
    return jsonify({"status": "active"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, threaded=True)