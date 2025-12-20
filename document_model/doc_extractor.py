import os
import json
import re
import mimetypes
from io import BytesIO
from flask import Flask, request, render_template
from dotenv import load_dotenv
import fitz
import docx2txt
from google.cloud import vision_v1 as vision
from pdf2image import convert_from_bytes
from langchain_google_vertexai import ChatVertexAI
import tempfile
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS





load_dotenv()


# Get the absolute path to the project root (one level above utils)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates")
)

CORS(app)


vision_client = vision.ImageAnnotatorClient()

# Vertex AI client (will use ADC or VERTEX_AI_CREDENTIALS if set)
llm = ChatVertexAI(model="gemini-2.5-flash-lite", temperature=0)


# ------------------- Extract Text Function -------------------
def extract_text(file_storage):
    """
    file_storage: Flask's file object (in-memory)
    """
    text = ""
    try:
        file_bytes = file_storage.read()
        filename_lower = file_storage.filename.lower()
        mime_type = mimetypes.guess_type(file_storage.filename)[0]

        # PDF (text)
        if filename_lower.endswith(".pdf") and mime_type == "application/pdf":
            try:
                with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                    for page in doc:
                        page_text = page.get_text("text")
                        page_text = page_text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
                        text += page_text + "\n"
                if text.strip():
                    return text.strip()
            except:
                pass

        # DOCX
        elif filename_lower.endswith(".docx"):
            with tempfile.NamedTemporaryFile(delete=True, suffix=".docx") as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                text = docx2txt.process(tmp.name)
                text = text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
                return text.strip()

        # TXT
        elif filename_lower.endswith(".txt"):
            text = file_bytes.decode("utf-8", errors="ignore")
            return text.strip()

        # IMAGE or PDF (image-based OCR)
        if mime_type and ("image" in mime_type or filename_lower.endswith(".pdf")):
            pages = []
            if filename_lower.endswith(".pdf"):
                pages = convert_from_bytes(file_bytes, dpi=300)
            else:
                from PIL import Image
                pages = [Image.open(BytesIO(file_bytes))]

            for i, page in enumerate(pages):
                with BytesIO() as img_buffer:
                    page.save(img_buffer, format="JPEG")
                    img_buffer.seek(0)
                    content = img_buffer.read()
                image = vision.Image(content=content)
                response = vision_client.document_text_detection(image=image)
                page_text = response.full_text_annotation.text
                page_text = page_text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
                text += f"\n\n--- PAGE {i+1} ---\n\n" + page_text

    except Exception as e:
        print(f"Error extracting text from {file_storage.filename}: {e}")
        return ""
    finally:
        file_storage.seek(0)  # Reset pointer for potential re-use

    return text.strip()

# ------------------- Pre-filter & Keywords (same as before) -------------------
CITIZEN_KEYWORDS = [
    # Legal & Court Documents
    "rental", "lease", "loan", "insurance", "property", "employment",
    "legal notice", "tenancy", "mortgage","certificate",
    "agreement", "deed", "judgment", "order", "bail", "court",
    "petition", "complaint", "fir", "charge sheet", "evidence",
    "appeal", "writ", "ndps", "narcotics", "seizure", "arrest", "offence",
    "accused", "petitioner", "respondent", "high court", "session court",
    "bail application", "criminal case", "ndps act", "union of india",
    "state", "public prosecutor", "investigation", "enforcement",
    "gazette", "central bureau of narcotics",
    "crime", "criminal", "arrest warrant", "summons", "affidavit",
    "power of attorney", "will", "trust deed", "notary", "divorce",
    "marriage certificate", "mutation document",
    "police report",   
    "court affidavit"
]

BUSINESS_KEYWORDS = [
    "contract", "nda", "mou", "policy", "compliance", "invoice", "purchase order",
    "agreement", "terms and conditions", "partnership", "corporate", "licensing",
    "confidentiality", "quotation", "tender", "proposal", "rfp", "sow",
    "memorandum of understanding", "board resolution", "gst invoice",
    "tax invoice", "debit note", "credit note", "payment receipt",
    "purchase agreement", "vendor registration", "audit report",
    "annual report", "business license", "trade license",
    "certificate of incorporation", 
    "gst filing", "company registration", "trademark", "patent", "ipo",
    "share certificate", "stock transfer", "compliance certificate",
    "employee contract",
    "resignation letter", "termination letter", "non-compete agreement",
    "confidentiality agreement", "performance report", "sales report",
    "import export license","delivery challan", "bank guarantee",
    "letter of credit", "vendor agreement", "purchase agreement",
    "project proposal", "financial statement", "budget report"
]

STUDENT_KEYWORDS = [
    "admission", "scholarship", "internship", "internship offer", "internship letter",
    "hostel", "disciplinary", "university", "course", "exam", "student loan",
    "certificate", "educational", "program", "offer of internship",
    "letter of recommendation", "bonafide certificate", "transfer certificate",
    "research paper", "publication", "attendance sheet",
    "college id card", "admission form", "application form", "fee structure",
    "syllabus", "prospectus", "placement letter", "training certificate",
    "campus selection", "offer of admission", "counselling letter", "internship completion",
    "internship certificate", "academic transcript", "degree certificate",
    
]

def pre_filter(text):
    text_lower = text.lower()
    scores = {
        "CITIZEN_DOC": sum(k in text_lower for k in CITIZEN_KEYWORDS),
        "BUSINESS_DOC": sum(k in text_lower for k in BUSINESS_KEYWORDS),
        "STUDENT_DOC": sum(k in text_lower for k in STUDENT_KEYWORDS)
    }
    predicted_category = max(scores, key=scores.get)
    if scores[predicted_category] == 0:
        return "INVALID_DOC"
    return predicted_category

# ------------------- Classify & Extract -------------------
def classify_and_extract(file_storage, user_category):
    text = extract_text(file_storage)
    if not text:
        return {"predicted_category": "INVALID_DOC",
                "reason": "Document is empty or text could not be extracted.",
                "suggested_action": "Please upload a valid document with readable text."}

    if pre_filter(text) == "INVALID_DOC":
        return {"predicted_category": "INVALID_DOC",
                "reason": "No relevant keywords found for citizen, business, or student legal matters.",
                "suggested_action": "Please upload a valid legal document."}

    smart_prompt = f"""
                      You are an expert legal document classifier. Your primary task is to distinguish between an actual, enforceable legal document and a document that is merely informational or descriptive.

                      A **VALID** document can be one of the following categories:

                      1. **CITIZEN_DOC**: Legal documents related to individuals like rental agreements, loans, insurance, property deeds, certificates, legal notices.
                      2. **BUSINESS_DOC**: Contracts, MOUs, NDAs, corporate policies, invoices, purchase orders, agreements between companies.
                      3. **STUDENT_DOC**: Documents for students such as admission letters, scholarship letters, internship offer letters, university policies, educational certificates, program enrolment letters.

                      An **INVALID_DOC** is any text that DESCRIBES or DISCUSSES legal topics but is not a legal instrument itself.

                      Now classify the following document. Return ONLY a JSON object with:

                      {{
                      "predicted_category": "CITIZEN_DOC" | "BUSINESS_DOC" | "STUDENT_DOC" | "INVALID_DOC",
                      "confidence": "high" | "medium" | "low",
                      "reason": "Explain why this is an actual legal document of the predicted category.",
                      "suggested_action": "Next steps for the user."
                      }}

                      Document:
                      {text}
                      """
    
    try:
        llm_response_obj = llm.invoke(smart_prompt)
        llm_response_text = llm_response_obj.content
        match = re.search(r"\{.*\}", llm_response_text, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            raise ValueError("LLM did not return a valid JSON object.")
    except Exception as e:
        return {"predicted_category": "INVALID_DOC",
                "reason": f"Could not perform semantic analysis. Error: {e}",
                "suggested_action": "Please try again with a different document."}

    llm_predicted_category = result.get("predicted_category", "INVALID_DOC")
    user_selected_category = f"{user_category.upper()}_DOC"

    if llm_predicted_category == user_selected_category:
        print("\n LLM confirms the document is valid and matches your category.\n")
        print("--- Extracted Document Text ---\n")
        return {"predicted_category": llm_predicted_category,
                "confidence": result.get("confidence", "medium"),
                "reason": result.get("reason", ""),
                "extracted_text": text,
                "suggested_action": "Document processed successfully."}
    else:
        if llm_predicted_category == "INVALID_DOC":
            result["suggested_action"] = "The AI determined this is not a legal document. No text extracted."
        else:
            result["suggested_action"] = f"The AI classified this document as {llm_predicted_category}, which does not match your selected category '{user_selected_category}'."
    return result

# ------------------- Flask Routes -------------------

@app.route("/active", methods=["GET"])
def active():
    return "active"

@app.route("/health")
def health():
    return {"status": "ok"}, 200

@app.route("/uploads", methods=["POST"])
def uploads():
    category = request.form.get("category")
    file = request.files.get("file")

    if not file or not category:
        return jsonify({
            "error": "Missing file or category"
        }), 400

    # Call your existing function
    result = classify_and_extract(file, category)

    # Return JSON directly
    return jsonify(result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, threaded=True)