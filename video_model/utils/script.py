"""
Fixed Script Generation with proper error handling
"""
import os
import re
import json
import logging
from dotenv import load_dotenv
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

def create_script_and_image_prompts(
    summary_json_str: str,
    language: str = "en",
    category: str = "business"
) -> tuple[list[str] | None, list[str] | None]:
    """
    Generate script parts and image prompts from JSON analysis in one LLM call. 
    
    Returns: 
        (script_parts_list, image_prompts_list) or (None, None) on failure
    """
    lang_for_prompt = (
        "English" if language. lower() in ["en", "en-in"]
        else ("Hindi" if language.lower() in ["hi", "hi-in"] else language)
    )

    COMMON_INSTRUCTIONS = f"""
    You are "Kanoon Mitra," an expert scriptwriter for video generation.
    Convert the provided JSON document analysis into a compelling video script.
    
    **CRITICAL:** Return ONLY a valid JSON object (no other text):
    {{
        "script_parts": [
            {{
                "part_text": "string (Simple, conversational script in {lang_for_prompt})",
                "image_prompt": "string (Descriptive prompt in English for AI image generation)"
            }}
        ]
    }}

    **Guidelines:**
    1. Create 8-10 script_parts
    2. Each part should be 2-3 sentences
    3. Use simple, conversational {lang_for_prompt}
    4. Image prompts should be visual instructions for AI image models
    5. Focus on Indian context and simple graphics
    """

    prompt_templates = {
        "business": f"""
        {COMMON_INSTRUCTIONS}
        **Audience:** Indian small business owners
        **Tone:** Helpful, clear, professional
        
        **JSON Analysis Data:**
        ```json
        {summary_json_str}
        ```
        
        Return the JSON output: 
        """,

        "citizen": f"""
        {COMMON_INSTRUCTIONS}
        **Audience:** Everyday Indian citizens
        **Tone:** Helpful, empathetic, clear
        
        **JSON Analysis Data:**
        ```json
        {summary_json_str}
        ```
        
        Return the JSON output:
        """,

        "student": f"""
        {COMMON_INSTRUCTIONS}
        **Audience:** Indian students and young professionals
        **Tone:** Supportive, educational, encouraging
        
        **JSON Analysis Data:**
        ```json
        {summary_json_str}
        ```
        
        Return the JSON output:
        """
    }

    prompt_to_use = prompt_templates.get(category, prompt_templates["citizen"])

    try:
        logger.info(f"Calling LLM for script generation (category={category}, language={language})")
        
        response = llm.invoke(prompt_to_use)
        script_data_text = getattr(response, "content", None) or getattr(response, "text", None)

        if not script_data_text or not script_data_text.strip():
            logger.error("LLM returned empty response")
            return None, None

        logger.debug(f"Raw LLM response (first 200 chars): {script_data_text[:200]}")

        # Clean response:  remove code fences
        cleaned_text = script_data_text.strip()
        cleaned_text = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned_text)
        cleaned_text = re.sub(r"```\s*$", "", cleaned_text)
        cleaned_text = cleaned_text.strip()

        # Extract JSON
        json_match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
        if not json_match:
            logger.error(f"No JSON found in LLM response")
            return None, None

        try:
            script_data = json.loads(json_match.group(0))
        except json.JSONDecodeError as json_err:
            logger.error(f"JSON decode error: {json_err}")
            return None, None

        # Extract script parts and image prompts
        script_parts = []
        image_prompts = []

        for part in script_data.get("script_parts", []):
            script_text = part.get("part_text", "").strip()
            image_prompt = part.get("image_prompt", "").strip()

            if script_text and image_prompt:
                # Clean script text
                clean_script = re.sub(r"[\*_]", "", script_text)
                script_parts.append(clean_script)
                image_prompts.append(image_prompt)
            else:
                logger.warning(f"Skipping incomplete part: {part}")

        if not script_parts or not image_prompts:
            logger.error("No valid script parts extracted")
            return None, None

        logger.info(f"✓ Generated {len(script_parts)} script parts and {len(image_prompts)} image prompts")
        return script_parts, image_prompts

    except Exception as e:
        logger.error(f"Exception during script generation: {e}", exc_info=True)
        return None, None


def create_ssml_from_parts(script_parts: list[str]) -> str:
    """
    Convert script parts to SSML with timing marks.
    
    Returns:
        SSML formatted string with <speak> tags and <mark> tags for timing
    """
    ssml_script_parts = []
    
    for i, part in enumerate(script_parts):
        # Escape XML special characters
        safe_part = (
            part.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&apos;")
        )
        # Add mark tag for timing
        ssml_script_parts.append(f'<p>{safe_part}</p><mark name="part_{i}_end"/>')

    ssml_script_text = f"<speak>{''.join(ssml_script_parts)}</speak>"
    return ssml_script_text


def generate_script_and_image_prompts(
    summary_text: str,
    language: str = "en",
    category:  str = "business"
) -> tuple[list[str] | None, list[str] | None, str | None]:
    """
    Complete pipeline:  generate script, image prompts, and SSML. 
    
    Returns:
        (script_parts, image_prompts, ssml_text) or (None, None, None) on failure
    """
    logger.info(f"Starting script generation pipeline (language={language}, category={category})")

    # 1. Generate script parts and image prompts
    script_parts, image_prompts = create_script_and_image_prompts(summary_text, language, category)
    
    if not script_parts or not image_prompts:
        logger.error("Script and image prompt generation failed")
        return None, None, None

    # 2. Create SSML from script parts
    ssml_text = create_ssml_from_parts(script_parts)
    
    if not ssml_text:
        logger.error("SSML creation failed")
        return None, None, None

    logger.info("✓ Script generation pipeline complete")
    return script_parts, image_prompts, ssml_text