# --- script_generation.py ---
import os, re
import logging
import requests
from PIL import Image
from flask import Flask, json, request, jsonify
from dotenv import load_dotenv
from google.cloud import language_v1
from google.cloud import texttospeech
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.prompts import PromptTemplate
import vertexai
from langchain_google_vertexai import ChatVertexAI, HarmBlockThreshold, HarmCategory
from requests.exceptions import RequestException

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
    max_output_tokens=8192,  # Optimized for 400-700 words
    project=PROJECT_ID,
    safety_settings=safety_settings
)

app = Flask(__name__)

def create_script_and_image_prompts( summary_json_str: str, language: str = "en", category: str = "business" ) -> tuple[list[str] | None, list[str] | None]:
    """
    Generates a full video script (as parts) AND a list of corresponding image prompts
    in a single LLM call, based on the input summary JSON.
    
    Returns:
        (script_parts, image_prompts) or (None, None) on failure.
    """
    
        # --- Map language code to human-readable name for LLM prompt ---
    lang_for_prompt = "English" if language.lower() in ["en", "en-in"] else ("Hindi" if language.lower() in ["hi", "hi-in"] else language)

    # --- Define Prompt Templates ---
    # These templates instruct the LLM to perform both tasks at once.

    COMMON_INSTRUCTIONS = f"""
    You are \"Kanoon Mitra,\" an expert scriptwriter and creative director for an AI video generator.
    Your task is to convert the provided JSON document analysis into a compelling video script.
    The script must be 300-600 words long, broken into 8-10 small, logical parts for fast video pacing.

        **CRITICAL:** You must return a SINGLE valid JSON object (no other text) that follows this schema:
        {{
            "script_parts": [
                {{
                    "part_text": "string (The simple, conversational script text for this part, in {lang_for_prompt})",
                    "image_prompt": "string (A descriptive, 1-sentence prompt in English for an AI image model (like Imagen) to generate a simple graphic, diagram, or illustration for this specific part. Focus on Indian context, simple graphics, and text labels if needed. e.g., 'Simple diagram of payment milestones: 40% start, 30% demo, labeled in {lang_for_prompt}.')"
                }}
            ]
        }}

        **Guidelines:**
        1.  **Analyze JSON:** Base the script *only* on the provided "JSON Analysis Data".
        2.  **Walkthrough:** The `script_parts` must form a logical narrative, walking the user through the JSON.
        3.  **Tone & Language:** Use simple, informal, conversational {lang_for_prompt}.
        4.  **Granularity:** Create **8-10 `script_parts`**, each being just a few sentences long.
        5.  **Image Prompts:** Each `image_prompt` must be a *visual instruction* for an AI to generate a graphic/diagram that matches its corresponding `part_text`.
        6.  **Validation:** Subtly mention validation data (from `validation_snippet` if present in the input JSON).
        """

    prompt_templates = {
        "business": f"""
        {COMMON_INSTRUCTIONS}
        **Audience:** Indian small business owners.
        **Tone:** Helpful, clear, and professional.

        **Instructions:**
        - Start with the "Overview".
        - Explain the most important "Clause_Insights" and "Key_Terms".
        - Clearly highlight the "Risk_and_Compliance" issues and "Recommendations".
        - Conclude with the "Simple_Summary".

        **JSON Analysis Data (Input):**
        ```json
        {summary_json_str}
        ```

        **Your JSON Output (Script & Prompts):**
        """,

        "citizen": f"""
        {COMMON_INSTRUCTIONS}
        **Audience:** Everyday Indian citizens (non-lawyers).
        **Tone:** Helpful, empathetic, and clear (e.g., "Namaste! Let's look at your document...").

        **Instructions:**
        - Start with the "Overview" and "KeyParties".
        - Explain the "KeyTerms" one by one.
        - Clearly highlight the "Risk_and_Compliance" or "Risk_Level" issues and "Recommendations".
        - Conclude with the "Simple_Summary".

        **JSON Analysis Data (Input):**
        ```json
        {summary_json_str}
        ```

        **Your JSON Output (Script & Prompts):**
        """,

        "student": f"""
        {COMMON_INSTRUCTIONS}
        **Audience:** Indian students and young professionals.
        **Tone:** Supportive, educational, and encouraging.

        **Instructions:**
        - Start with the "Overview" and "yourRole".
        - Explain the "Key_Terms" (especially Stipend, Duration, IP, and Termination).
        - Clearly explain the "Rights_and_Fairness" section.
        - Conclude by summarizing the "FinalTips" or "Recommendations".

        **JSON Analysis Data (Input):**
        ```json
        {summary_json_str}
        ```

        **Your JSON Output (Script & Prompts):**
        """
    }

    # --- 2. Select and Format the Prompt ---
    prompt_to_use = prompt_templates.get(category, prompt_templates["citizen"]) # Default to citizen

    # --- 3. Call the LLM and Process the Response ---
    try:
        # Use the globally defined 'llm' client
        response = llm.invoke(prompt_to_use)

        script_data_text = getattr(response, "content", None) or getattr(response, "text", None)
        logging.info(f"Raw LLM response: {script_data_text}")
        if not script_data_text or not script_data_text.strip():
            logging.warning("LLM returned empty response for script/prompts.")
            return None, None

        # Pre-process: Remove code fences and markdown
        cleaned_text = script_data_text.strip()
        cleaned_text = re.sub(r"^```[a-zA-Z]*\\s*", "", cleaned_text)
        cleaned_text = re.sub(r"```\\s*$", "", cleaned_text)
        cleaned_text = cleaned_text.strip()

        # Extract JSON object
        json_match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
        if not json_match:
            logging.warning(f"Failed to find valid JSON in LLM response: {cleaned_text}")
            return None, None

        try:
            script_data = json.loads(json_match.group(0))
        except Exception as json_err:
            logging.warning(f"JSON decode error: {json_err}\nRaw JSON: {json_match.group(0)}")
            return None, None

        # Now, extract the data into two parallel lists
        script_parts = []
        image_prompts = []

        for part in script_data.get("script_parts", []):
            script_text = part.get("part_text")
            image_prompt = part.get("image_prompt")

            # Ensure both parts exist before adding
            if script_text and image_prompt:
                # Clean script text for TTS (remove markdown)
                clean_script_part = re.sub(r"[\*_]", "", script_text.strip())
                script_parts.append(clean_script_part)
                image_prompts.append(image_prompt.strip())
            else:
                logging.warning(f"Skipping incomplete part from LLM: {part}")

        if not script_parts or not image_prompts:
            logging.warning("LLM returned valid JSON, but 'script_parts' was empty or malformed.")
            return None, None

        logging.info(f"Successfully generated {len(script_parts)} script parts and {len(image_prompts)} image prompts.")
        return script_parts, image_prompts

    except Exception as e:
        logging.error(f"Exception during consolidated script generation: {e}", exc_info=True)
        return None, None

def create_ssml_from_parts(script_parts: list[str]) -> str:
    """
    Wraps each script part in SSML <p> tags and adds a <mark>
    tag after each part for timing.
    """
    ssml_script_parts = []
    for i, part in enumerate(script_parts):
        # 1. Clean the text for SSML
        #    Escape special characters: & < > " '
        safe_part = (
            part.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&apos;")
        )
        # 2. Wrap in paragraph tags and add the crucial <mark> tag *after* the text.
        ssml_script_parts.append(f'<p>{safe_part}</p><mark name="part_{i}_end"/>')

    # 3. Join all parts and wrap in the main <speak> tag
    ssml_script_text = f"<speak>{''.join(ssml_script_parts)}</speak>"
    
    return ssml_script_text

def generate_script_and_image_prompts(summary_text, language="en", category="business"):
    script_parts, image_prompts = create_script_and_image_prompts(summary_text, language, category)
    if not script_parts or not image_prompts:
        logging.error("Pipeline failed: Script generation returned None.")
        return None, [], [] # Indicate failure
    
    ssml_text = create_ssml_from_parts(script_parts) if isinstance(script_parts, list) else script_parts
    
    if not ssml_text:
        logging.error("Pipeline failed: SSML creation returned None.")
        return None, [], None
    return script_parts, image_prompts, ssml_text
