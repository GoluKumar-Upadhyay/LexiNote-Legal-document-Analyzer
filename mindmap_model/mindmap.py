
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import os
import json
import re
import logging
import uuid
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
# --- Core AI Libraries ---
import vertexai
from langchain_core.prompts import PromptTemplate
from langchain_google_vertexai import ChatVertexAI, HarmBlockThreshold, HarmCategory
from requests.exceptions import RequestException

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s')
load_dotenv()




# Get the absolute path to the project root (one level above utils)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates")
)

CORS(
    app,
    resources={r"/generate_mindmap": {"origins": "http://localhost:8100"}},
    supports_credentials=True
)



# ---------- Step 1: Initialize LLM Client ----------
try:

    
   
    vertex_key_path = os.getenv("VERTEX_AI_KEY")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = vertex_key_path
    PROJECT_ID = "ageless-earth-457916-v1"
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

# --- *** NEW OPTIMIZED PROMPT GUIDELINES *** ---
COMMON_PROMPT_GUIDELINES = """
You are "Kanoon Mitra," an expert legal analyst and UI/UX designer.
Your task is to convert a complex 'DocumentSummary' JSON into a simple, hierarchical JSON tree for a mind map.
You MUST return ONLY a single, valid JSON object. Do NOT use markdown.
Your response MUST start with {{ and end with }}.

**Output JSON Schema:**
{{
  "id": "string (Unique ID, e.g., 'root')",
  "label": "string (A VERY SHORT, 2-4 word title for the node)",
  "details": "string (A **CONCISE 1-2 SENTENCE SUMMARY** max 10-15 words of the explanation. 'N/A' if none.)",
  "icon": "string (Icon name: 'document', 'law', 'people', 'risk_high', 'risk_low', 'check', 'money', 'time', 'info', 'recommendation', 'star')",
  "status": "string ('positive', 'negative', 'neutral', 'info')",
  "secondaryLabel": "string (Optional shorter text, e.g., '9/10' or 'Low Risk')",
  "children": [
    {{
      "id": "string",
      "label": "string (SHORT 2-4 word title)",
      "details": "string (CONCISE 1-2 SENTENCE SUMMARY)",
      "icon": "string",
      "status": "string",
      "secondaryLabel": "string",
      "children": [ ... ] // Recursive structure
    }}
  ]
}}

**Node Generation Rules (Critical):**
1.  **Root Node:** The 'Document_Name' must be the 'label' for the root node (id: 'root'). 'details' should be a 1-sentence summary of the 'Purpose'.
2.  **Hierarchy:** Create a logical hierarchy from the summary.
3.  **LABELS MUST BE SHORT:** The 'label' field MUST be a short, 2-4 word conceptual title (e.g., "Payment Terms", "Risk Level").
4.  **DETAILS MUST BE SUMMARIZED:** Put the long explanatory text from the input into the 'details' field, but you **MUST summarize it** into a concise, 1-2 sentence max 10-15 words explanation. Do not just copy the full long paragraph.
5.  **Informative Data:** Use the 'icon', 'status', and 'secondaryLabel' fields for at-a-glance context.
6.  **Language:** All text fields MUST be in the language of the input summary.
"""

# --- Category-Specific Prompt Templates ---
category_templates = {
    "business": f"""
    {COMMON_PROMPT_GUIDELINES}
    **Business Instructions:**
    - Create main branches for: 'Header', 'Parties Involved', 'Clause Insights', 'Key Terms', 'Applicable Laws', 'Risk & Compliance', and 'Recommendations'.
    - For 'Clause Insights', create a child node for each 'Topic'. The 'label' should be the 'Topic' (e.g., "Confidentiality"). The 'details' MUST be a **1-sentence summary** of the 'Explanation'.
    - For 'Applicable Laws', create a child node for each 'Act'. 'label' is the Act name, 'details' is a **1-sentence summary** of the 'Relevance'.
    - For 'Risk & Compliance', create child nodes for 'Confidence_Score', 'Risk_Level', and each 'Issue' in 'Potential_Issues'.
    - For 'Potential_Issues', the 'label' should be a **short summary** of the 'Issue' and the 'details' should be a **1-sentence summary** of the 'Recommendation'.
    - For 'Risk_Level: Low', set `status: 'positive'`, 'icon: 'risk_low'', 'secondaryLabel: 'Low''.
    - For 'Risk_Level: High', set `status: 'negative'`, 'icon: 'risk_high'', 'secondaryLabel: 'High''.
    
    **Input Summary (JSON):**
    {{text}}
    **Your Hierarchical JSON Output:**
    """,
    
    "citizen": f"""
    {COMMON_PROMPT_GUIDELINES}
    **Citizen Instructions:**
    - Create main branches for: 'Header', 'Parties Involved', 'Key Terms', 'Rights & Obligations', 'Applicable Laws', 'Validation Status', and 'Recommendations'.
    - For 'Key Terms', create child nodes for each key (e.g., 'Duration_or_Tenure'). 'label' is the key, 'details' is a **1-sentence summary** of the value.
    - For 'Risk_and_Compliance', create a main branch and child nodes for each 'Issue'. 'label' is a **short summary** of the 'Issue', 'details' is a **1-sentence summary** of the 'Recommendation'.
    
    **Input Summary (JSON):**
    {{text}}
    **Your Hierarchical JSON Output:**
    """,
    
    "student": f"""
    {COMMON_PROMPT_GUIDELINES}
    **Student Instructions:**
    - Create main branches for: 'Header', 'Parties Involved', 'Key Terms', 'Rights and Fairness', 'Applicable Laws', 'Risk & Compliance', and 'Recommendations'.
    - For 'Key Terms', create child nodes for each key (e.g., 'Stipend_or_Payment'). 'label' is the key, 'details' is a **1-sentence summary** of the value.
    - For 'Risk_and_Compliance', create a main branch and child nodes for each 'Issue'. 'label' is a **short summary** of the 'Issue', 'details' is a **1-sentence summary** of the 'Recommendation'.
    
    **Input Summary (JSON):**
    {{text}}
    **Your Hierarchical JSON Output:**
    """
}


# ---------- Step 2: Generate Mind Map Data from LLM ----------
def generate_mindmap_data(llm_client, summary_json_str: str, category: str) -> dict | None:
    """
    Takes a document summary JSON string and category, and uses the LLM
    to generate a HIERARCHICAL JSON structure.
    """
    
    prompt_template = category_templates.get(category.lower(), category_templates["citizen"])
    formatted_prompt = PromptTemplate(input_variables=["text"], template=prompt_template).format(text=summary_json_str)

    logging.info(f"Generating mind map data from LLM for category: {category}...")

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = llm_client.invoke(formatted_prompt)
            raw_output = response.content.strip()
        except Exception as e:
            logging.error(f"LLM invocation failed (attempt {attempt}): {e}", exc_info=True)
            if attempt == max_retries:
                return None
            continue

        # --- Robust JSON Cleaning ---
        if raw_output.startswith("```"):
            raw_output = re.sub(r"^```[json]*\n", "", raw_output, flags=re.MULTILINE)
            raw_output = re.sub(r"\n```$", "", raw_output, flags=re.MULTILINE)
        raw_output = raw_output.strip()

        # Remove newlines inside quoted strings (to avoid unterminated string errors)
        def clean_newlines_in_strings(text):
            # Replace newlines inside double quotes with a space
            def replacer(match):
                return match.group(0).replace('\n', ' ')
            return re.sub(r'"(.*?)"', replacer, text, flags=re.DOTALL)

        cleaned_output = clean_newlines_in_strings(raw_output)
        cleaned_output = re.sub(r",\s*(\]|})", r"\1", cleaned_output) # Fix trailing commas

        try:
            mindmap_data = json.loads(cleaned_output)
            logging.info(f"Mind map JSON parsed successfully on attempt {attempt}.")
            if "label" not in mindmap_data:
                logging.error(f"Generated JSON is missing root 'label' key (attempt {attempt}).")
                if attempt == max_retries:
                    return None
                continue
            return mindmap_data
        except json.JSONDecodeError as e:
            logging.error(f"Model output was not valid JSON (attempt {attempt}). Error: {e}")
            logging.error(f"--- Raw Output ---:\n{cleaned_output}")
            # Try partial recovery: find last closing bracket
            last_brace = cleaned_output.rfind('}')
            if last_brace != -1:
                partial = cleaned_output[:last_brace+1]
                try:
                    mindmap_data = json.loads(partial)
                    logging.info(f"Partial mind map JSON parsed successfully on attempt {attempt}.")
                    if "label" not in mindmap_data:
                        logging.error(f"Partial JSON missing root 'label' key (attempt {attempt}).")
                        if attempt == max_retries:
                            return None
                        continue
                    return mindmap_data
                except Exception as e2:
                    logging.error(f"Partial JSON recovery failed (attempt {attempt}): {e2}")
            if attempt == max_retries:
                return None
            continue

# ---------- Step 3: Create Flask App and Endpoint ----------


@app.route("/generate_mindmap", methods=['POST'])
def generate_mindmap_api():

    if not llm:
        return jsonify({"error": "LLM client not initialized."}), 503

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request must be JSON."}), 400
            
        summary_json_obj = data.get("summary_json") 
        summary_json_str = json.dumps(summary_json_obj) 
        category = data.get("category", "citizen").lower()

        if not summary_json_str or category not in ["business", "citizen", "student"]:
            return jsonify({"error": "Missing 'summary_json' or invalid 'category'."}), 400
            
    except Exception as e:
        return jsonify({"error": f"Invalid request format: {e}"}), 400

    # --- 1. Generate the HIERARCHICAL JSON ---
    hierarchical_data = generate_mindmap_data(llm, summary_json_str, category)
    
    if not hierarchical_data:
        logging.error("Failed to generate hierarchical JSON from LLM.")
        return jsonify({"error": "Failed to generate mind map data from LLM."}), 500
        
    # --- 2. Return the HIERARCHICAL JSON directly ---
    return jsonify(hierarchical_data), 200

# ---------- Main Execution (for local testing) ----------
if __name__ == "__main__":
    
    app.run(host="0.0.0.0", port=5002, threaded=True)

