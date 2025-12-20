"""
Fixed Main Flask Application with Complete Video Generation Pipeline
"""
import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import vertexai
from langchain_google_vertexai import ChatVertexAI, HarmBlockThreshold, HarmCategory

# Import utilities
from utils.script import generate_script_and_image_prompts
from utils.image_generation import generate_images_for_prompts
from utils.audio_generation import generate_tts_audio_with_timing
from utils.video_generation import build_video_from_pipeline_output
from flask_cors import CORS

load_dotenv()

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# === CONFIGURATION ===
app = Flask(__name__)
CORS(app)

# Get the absolute path to the project root (one level above utils)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------- Step 1: Initialize LLM Client ----------
try:
    vertex_key_path = os.getenv("VERTEX_AI_KEY")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = vertex_key_path
    PROJECT_ID = os.getenv("PROEJCT_ID")
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

    
# ===== MAIN VIDEO GENERATION PIPELINE =====
def generate_video_pipeline(
    summary_text: str,
    language: str = "en",
    category: str = "business"
) -> dict:
    """
    Complete end-to-end video generation pipeline with validation at each step.
    
    Returns:
        {
            'video_path': str (video URL or path),
            'error': str (error message if failed)
        }
    """
    logger.info("="*60)
    logger.info(f"START VIDEO PIPELINE | language={language}, category={category}")
    logger.info("="*60)

    # ===== STEP 1: Generate Script & Image Prompts =====
    logger.info("[1/4] Generating script and image prompts...")
    script_parts, image_prompts, ssml_text = generate_script_and_image_prompts(
        summary_text,
        language=language,
        category=category
    )

    if not script_parts or not image_prompts or not ssml_text:
        error_msg = "Script/image prompt/SSML generation failed"
        logger.error(f"✗ {error_msg}")
        return {"error": error_msg, "video_path": None}

    logger.info(f"✓ Generated {len(script_parts)} script parts and {len(image_prompts)} image prompts")

    # ===== STEP 2: Generate Audio =====
    logger.info("[2/4] Generating audio...")
    audio_filepath, mark_timings = generate_tts_audio_with_timing(
        script_text=ssml_text,
        language_code=language
    )

    if not audio_filepath or not os.path.exists(audio_filepath):
        error_msg = "Audio generation failed or file not found"
        logger.error(f"✗ {error_msg}")
        return {"error": error_msg, "video_path": None}

    audio_size = os.path.getsize(audio_filepath)
    if audio_size < 1000:
        error_msg = f"Audio file too small ({audio_size} bytes)"
        logger.error(f"✗ {error_msg}")
        return {"error": error_msg, "video_path": None}

    logger.info(f"✓ Audio generated: {os.path.basename(audio_filepath)} ({audio_size} bytes)")

    # ===== STEP 3: Generate Images =====
    logger.info("[3/4] Generating images (with fallback handling)...")
    use_ai_flags = [True] * len(image_prompts)  # Use AI for all images
    
    try:
        graphic_filepaths = generate_images_for_prompts(
            image_prompts=image_prompts,
            use_ai_flags=use_ai_flags,
            language=language,
            max_workers=1  # Keep sequential to avoid quota issues
        )
    except Exception as img_err:
        error_msg = f"Image generation failed: {img_err}"
        logger.error(f"✗ {error_msg}")
        return {"error": error_msg, "video_path": None}

    # Validate all graphics are valid
    invalid_count = 0
    for i, fp in enumerate(graphic_filepaths):
        if not fp or not os.path.exists(fp) or os.path.getsize(fp) < 100:
            logger.warning(f"Invalid graphic at index {i}: {fp}")
            invalid_count += 1

    if invalid_count == len(graphic_filepaths):
        error_msg = "All image generation failed"
        logger.error(f"✗ {error_msg}")
        return {"error": error_msg, "video_path": None}

    logger.info(f"✓ Generated/fetched {len(graphic_filepaths) - invalid_count}/{len(script_parts)} valid images")
    if invalid_count > 0:
        logger.warning(f"⚠ {invalid_count} images using placeholder")

    # ===== STEP 4: Assemble Video =====
    logger.info("[4/4] Assembling video...")
    pipeline_input = {
        "audio_filepath": audio_filepath,
        "graphic_filepaths": graphic_filepaths,
        "script_parts_text": script_parts,
        "mark_timings": mark_timings
    }

    try:
        video_path = build_video_from_pipeline_output(pipeline_input)
    except Exception as video_err:
        error_msg = f"Video assembly error: {video_err}"
        logger.error(f"✗ {error_msg}", exc_info=True)
        return {"error": error_msg, "video_path": None}

    if not video_path:
        error_msg = "Video assembly failed"
        logger.error(f"✗ {error_msg}")
        return {"error": error_msg, "video_path": None}

    logger.info(f"✓ Video created: {video_path}")
    logger.info("="*60)
    logger.info("✓ PIPELINE SUCCESS")
    logger.info("="*60)

    return {"video_path": video_path, "error": None}


# ===== FLASK ROUTES =====

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route("/active", methods=["GET"])
def active():
    """Activity check endpoint"""
    return jsonify({"status": "active"}), 200


@app.route("/generate_video", methods=["POST"])
def generate_video_endpoint():
    """
    Main video generation endpoint.
    
    Request body (form-data):
        - summary_text: JSON string or plain text to base video on
        - category: "business", "citizen", or "student"
        - language: Language code (e.g., "en", "hi", "en-IN")
    
    Response:
        - video_path: URL to generated video
        - error: Error message if failed
    """
    try:
        summary_text = request.form.get("summary_text", "").strip()
        category = request.form.get("category", "business").lower()
        language = request.form.get("language", "en").lower()

        # Validate inputs
        if not summary_text:
            return jsonify({"error": "summary_text is required"}), 400

        if category not in ["business", "citizen", "student"]:
            return jsonify({"error": "category must be: business, citizen, or student"}), 400

        valid_languages = ["en", "hi", "en-in", "hi-in"]
        if language not in valid_languages:
            return jsonify({"error": f"language must be one of: {valid_languages}"}), 400

        # Run pipeline
        result = generate_video_pipeline(summary_text, language, category)

        if result.get("error"):
            return jsonify(result), 500

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Unexpected error in /generate_video: {e}", exc_info=True)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route("/generate_script", methods=["POST"])
def generate_script_endpoint():
    """
    Endpoint to generate only script and image prompts (without audio/video).
    
    Request body (form-data):
        - summary_text: Content to base script on
        - category: "business", "citizen", or "student"
        - language: Language code
    
    Response:
        - script_parts: List of script text strings
        - image_prompts: List of image generation prompts
    """
    try:
        summary_text = request.form.get("summary_text", "").strip()
        category = request.form.get("category", "business").lower()
        language = request.form.get("language", "en").lower()

        if not summary_text:
            return jsonify({"error": "summary_text is required"}), 400

        script_parts, image_prompts, ssml_text = generate_script_and_image_prompts(
            summary_text,
            language=language,
            category=category
        )

        if not script_parts or not image_prompts:
            return jsonify({"error": "Script generation failed"}), 500

        return jsonify({
            "script_parts": script_parts,
            "image_prompts": image_prompts,
            "ssml": ssml_text
        }), 200

    except Exception as e:
        logger.error(f"Error in /generate_script: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/generate_images", methods=["POST"])
def generate_images_endpoint():
    """
    Endpoint to generate images for prompts.
    
    Request body (JSON):
        - image_prompts: List of image generation prompts
        - use_ai_flags: List of booleans (True = use AI, False = stock images)
        - language: Language code
    
    Response:
        - List of image file paths
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        image_prompts = data.get("image_prompts", [])
        use_ai_flags = data.get("use_ai_flags", [])
        language = data.get("language", "en")

        if not isinstance(image_prompts, list):
            return jsonify({"error": "image_prompts must be a list"}), 400

        if not isinstance(use_ai_flags, list):
            return jsonify({"error": "use_ai_flags must be a list"}), 400

        if len(image_prompts) != len(use_ai_flags):
            return jsonify({"error": "image_prompts and use_ai_flags must have same length"}), 400

        result_paths = generate_images_for_prompts(
            image_prompts=image_prompts,
            use_ai_flags=use_ai_flags,
            language=language
        )

        return jsonify({"image_paths": result_paths}), 200

    except Exception as e:
        logger.error(f"Error in /generate_images: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/generate_audio", methods=["POST"])
def generate_audio_endpoint():
    """
    Endpoint to generate audio from SSML script.
    
    Request body (JSON):
        - script_text: SSML formatted script
        - language_code: Language code (e.g., "en-IN")
    
    Response:
        - audio_filepath: Path to generated audio file
        - mark_timings: List of (mark_name, time_seconds) tuples
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        script_text = data.get("script_text", "").strip()
        language_code = data.get("language_code", "en-IN")

        if not script_text:
            return jsonify({"error": "script_text is required"}), 400

        audio_filepath, mark_timings = generate_tts_audio_with_timing(
            script_text=script_text,
            language_code=language_code
        )

        if not audio_filepath:
            return jsonify({"error": "Audio generation failed"}), 500

        return jsonify({
            "audio_filepath": audio_filepath,
            "mark_timings": mark_timings
        }), 200

    except Exception as e:
        logger.error(f"Error in /generate_audio: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/assemble_video", methods=["POST"])
def assemble_video_endpoint():
    """
    Endpoint to assemble video from pre-generated components.
    
    Request body (JSON):
        - audio_filepath: Path to audio file
        - graphic_filepaths: List of image file paths
        - script_parts_text: List of script text strings
        - mark_timings: Optional list of (mark_name, time) tuples
    
    Response:
        - video_path: Path/URL to generated video
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        audio_filepath = data.get("audio_filepath")
        graphic_filepaths = data.get("graphic_filepaths", [])
        script_parts_text = data.get("script_parts_text", [])
        mark_timings = data.get("mark_timings")

        if not audio_filepath or not graphic_filepaths or not script_parts_text:
            return jsonify({
                "error": "Missing required fields: audio_filepath, graphic_filepaths, script_parts_text"
            }), 400

        pipeline_input = {
            "audio_filepath": audio_filepath,
            "graphic_filepaths": graphic_filepaths,
            "script_parts_text": script_parts_text,
            "mark_timings": mark_timings
        }

        video_path = build_video_from_pipeline_output(pipeline_input)

        if not video_path:
            return jsonify({"error": "Video assembly failed"}), 500

        return jsonify({"video_path": video_path}), 200

    except Exception as e:
        logger.error(f"Error in /assemble_video: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ===== MAIN =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, threaded=True)