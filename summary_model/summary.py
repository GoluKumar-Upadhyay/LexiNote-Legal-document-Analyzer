import os
from flask import Flask, jsonify, render_template, request
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from utils.model import llm, category_templates
from utils.rag_utils import predict_law_from_doc, verify_laws, build_verified_context
from utils.indiankanoon_utils import verify_with_indiankanoon
import re
import time
import multiprocessing
import logging
from functools import lru_cache
from typing import List, Tuple, Dict, Optional
from dotenv import load_dotenv
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s'
)

load_dotenv()


# Get the absolute path to the project root (one level above utils)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates")
)

CORS(app)

# Optimized ThreadPoolExecutor with CPU-based workers
executor = ThreadPoolExecutor(max_workers=min(8, (multiprocessing.cpu_count() or 4)))

# ===================== OPTIMIZED UTILITY FUNCTIONS =====================

def clean_llm_response(text: str) -> str:
    """Clean LLM output by removing code fences and backticks."""
    if not text:
        return text

    s = text.strip()

    # Extract content from fenced blocks
    if "```" in s:
        first = s.find("```")
        last = s.rfind("```")
        if first != -1 and last != -1 and last > first:
            inner = s[first + 3:last]
            # Remove language token (e.g., json)
            inner = re.sub(r'^\s*[a-zA-Z0-9_+-]+\s*\n', '', inner)
            return inner.strip()

    # Remove single backticks
    if s.startswith("`") and s.endswith("`"):
        return s.strip("`").strip()

    return s


@lru_cache(maxsize=128)
def detect_language(text: str) -> str:
    """Detect language with caching for repeated texts."""
    hindi_chars = re.findall(r'[\u0900-\u097F]', text[:500])  # Check first 500 chars
    return "hindi" if len(hindi_chars) > 50 else "english"


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace while preserving document structure.
    - Collapses multiple spaces/tabs to single space
    - Preserves paragraph breaks (max 2 newlines)
    - Keeps document sections intact
    """
    # Collapse horizontal whitespace (spaces and tabs)
    text = re.sub(r"[ \t]+", " ", text)
    
    # Limit consecutive newlines to max 2 (paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Remove trailing whitespace from lines
    text = re.sub(r"[ \t]+\n", "\n", text)
    
    return text.strip()


def estimate_tokens(text: str) -> int:
    """
    Rough token estimation (more accurate than character count).
    Average: 1 token ≈ 4 characters for English, 2-3 for Hindi.
    """
    # Simple heuristic: count words and punctuation
    words = len(text.split())
    punctuation = len(re.findall(r'[^\w\s]', text))
    return int(words * 1.3 + punctuation * 0.5)


def chunk_text_smart(text: str, max_tokens: int = 4000, overlap_tokens: int = 150) -> List[str]:
    """
    Smart chunking with sentence boundary detection and token awareness.
    
    Args:
        text: Input text to chunk
        max_tokens: Maximum tokens per chunk (default 4000 for safety margin)
        overlap_tokens: Overlap between chunks for context continuity
    
    Returns:
        List of text chunks
    """
    chunks = []
    
    # Convert token limits to approximate character limits
    max_chars = max_tokens * 4  # Conservative estimate
    overlap_chars = overlap_tokens * 4
    
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + max_chars, text_len)
        
        # If not at the end, try to break at natural boundaries
        if end < text_len:
            # Priority order: paragraph > sentence > word
            boundaries = [
                ('\n\n', 0.7),  # Paragraph break - ideal
                ('।\n', 0.65),   # Hindi sentence with newline
                ('.\n', 0.65),   # English sentence with newline
                ('। ', 0.6),     # Hindi sentence
                ('. ', 0.6),     # English sentence
                ('\n', 0.5),     # Line break
                (' ', 0.3)       # Word boundary - last resort
            ]
            
            chunk_text = text[start:end]
            best_break = -1
            
            for delimiter, min_ratio in boundaries:
                last_occurrence = chunk_text.rfind(delimiter)
                # Accept if break point is at least min_ratio through the chunk
                if last_occurrence > len(chunk_text) * min_ratio:
                    best_break = last_occurrence + len(delimiter)
                    break
            
            if best_break > 0:
                end = start + best_break
        
        chunk = text[start:end].strip()
        if chunk:  # Only add non-empty chunks
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap_chars if end < text_len else text_len
        
        # Ensure we make progress (prevent infinite loop)
        if start >= end - 100:
            start = end
    
    logging.info(f"Created {len(chunks)} chunks (avg tokens: {sum(estimate_tokens(c) for c in chunks) / len(chunks):.0f})")
    return chunks


# ===================== PROMPT TEMPLATES =====================

def get_base_guidelines() -> str:
    """Shared guidelines to reduce prompt redundancy."""
    return """
You are a professional legal document summarizer.

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown, no explanations, no extra text.
2. Follow the exact structure provided - do not change key names.
3. Use clear, simple language - explain complex terms briefly.
4. Provide comprehensive summaries - not minimal or generic.
5. If document is in Hindi, output ENTIRE summary in Hindi (except Act names).
"""


def get_category_structure(category: str) -> dict:
    """Get JSON structure for each category."""
    structures = {
        "student": {
            "DocumentSummary": {
                "Category": "Student",
                "Header": {
                    "Document_Name": "",
                    "Document_Type": "",
                    "Purpose": "",
                    "Date": "",
                    "Jurisdiction": ""
                },
                "Parties_Involved": {
                    "Party_1": "",
                    "Party_2": "",
                    "Relationship": "",
                    "Key_Obligations": ""
                },
                "Overview": "2-3 line educational explanation",
                "Key_Terms": {
                    "Duration_or_Tenure": "",
                    "Stipend_or_Payment": "",
                    "Roles_and_Responsibilities": "",
                    "Termination_or_Exit_Clause": "",
                    "Ownership_or_IP": "",
                    "Confidentiality_or_NDA": ""
                },
                "Rights_and_Fairness": {
                    "Rights_of_Party_1": "",
                    "Rights_of_Party_2": "",
                    "Fairness_Check": ""
                },
                "Applicable_Laws_and_Acts": {
                    "Explicit_Acts": [],
                    "Implicit_Acts": []
                },
                "Risk_and_Compliance": [],
                "Confidence_and_Risk_Score": {
                    "Confidence": "",
                    "Risk_Level": "",
                    "Document_Clarity": ""
                },
                "Recommendations": [],
                "Simple_Summary": ""
            }
        },
        "citizen": {
            "DocumentSummary": {
                "Category": "Citizen",
                "Header": {
                    "Document_Name": "",
                    "Document_Type": "",
                    "Purpose": "",
                    "Date": "",
                    "Jurisdiction": ""
                },
                "Parties_Involved": {
                    "Party_1": "",
                    "Party_2": "",
                    "Relationship": "",
                    "Key_Obligations": ""
                },
                "Overview": "2-3 line public-friendly explanation",
                "Key_Terms": {
                    "Duration_or_Tenure": "",
                    "Payment_or_Consideration": "",
                    "Transfer_of_Rights": "",
                    "Termination_or_Cancellation": "",
                    "Witness_or_Attestation": ""
                },
                "Rights_and_Obligations": {
                    "Rights_of_Party_1": "",
                    "Rights_of_Party_2": "",
                    "Mutual_Obligations": ""
                },
                "Applicable_Laws_and_Acts": {
                    "Explicit_Acts": [],
                    "Implicit_Acts": []
                },
                "Validation_Status": {
                    "Is_Legally_Compliant": "",
                    "Missing_Clauses": [],
                    "Requires_Registration": ""
                },
                "Risk_and_Compliance": [],
                "Confidence_and_Risk_Score": {
                    "Confidence": "",
                    "Risk_Level": "",
                    "Document_Clarity": ""
                },
                "Recommendations": [],
                "Simple_Summary": ""
            }
        },
        "business": {
            "DocumentSummary": {
                "Category": "Business",
                "Header": {
                    "Document_Name": "",
                    "Type": "",
                    "Purpose": "",
                    "Date": "",
                    "Jurisdiction": ""
                },
                "Parties_Involved": {
                    "Party_1": "",
                    "Party_2": "",
                    "Relationship": "",
                    "Key_Obligations": ""
                },
                "Overview": "3-4 line commercial summary",
                "Clause_Insights": [],
                "Key_Terms": {
                    "Duration": "",
                    "Payment_or_Consideration": "",
                    "Transfer_of_Rights": "",
                    "Termination": ""
                },
                "Applicable_Laws": [],
                "Risk_and_Compliance": {
                    "Clause_Coverage_Percentage": "",
                    "Potential_Issues": []
                },
                "Confidence_Score": "",
                "Risk_Level": "",
                "Recommendations": [],
                "Simple_Summary": ""
            }
        }
    }
    return structures.get(category, structures["citizen"])


# ===================== CHUNK SUMMARIZATION =====================

def summarize_chunk(
    chunk: str,
    chunk_idx: int,
    total_chunks: int,
    category: str,
    lang: str,
    template_text: str
) -> Tuple[int, Optional[str]]:
    """
    Summarize a single chunk with error handling.
    Returns tuple of (chunk_index, summary_or_none)
    """
    try:
        prompt = f"""
{get_base_guidelines()}

Task: Summarize this document chunk (Part {chunk_idx + 1}/{total_chunks})

Output Structure:
{template_text}

Language: {"Output in Hindi (except Act names)" if lang == "hindi" else "Output in English"}

Document Text:
{chunk}

Output ONLY valid JSON:
"""
        
        response = llm.invoke(prompt)
        summary = clean_llm_response(response.content)
        
        logging.info(f"✓ Chunk {chunk_idx + 1}/{total_chunks} summarized ({estimate_tokens(summary)} tokens)")
        return (chunk_idx, summary)
        
    except Exception as e:
        logging.error(f"✗ Chunk {chunk_idx + 1}/{total_chunks} failed: {e}")
        return (chunk_idx, None)


# ===================== LEGAL VERIFICATION =====================

def verify_document_laws(doc_text: str, is_sample: bool = False) -> Dict:
    """
    Verify document laws with parallel execution.
    Can work on full document or sample for long docs.
    """
    try:
        # Use first 3000 chars for long docs
        sample_text = doc_text[:3000] if is_sample else doc_text
        
        # Predict applicable laws
        predicted_text = predict_law_from_doc(sample_text)
        predicted_act = predicted_text.split("Act Name:")[-1].split("\n")[0].strip() if "Act Name:" in predicted_text else ""
        predicted_category = predicted_text.split("Category:")[-1].split("\n")[0].strip() if "Category:" in predicted_text else ""
        
        # Parallel verification
        future_laws = executor.submit(verify_laws, predicted_act, predicted_category)
        future_kanoon = executor.submit(verify_with_indiankanoon, predicted_act, predicted_category)
        
        verified_laws = future_laws.result(timeout=30)
        indiankanoon_cases = future_kanoon.result(timeout=30)
        
        verification_status = (
            "Verified using Indian Legal Database (Pinecone + IndianKanoon)"
            if verified_laws or indiankanoon_cases
            else "No external verification found — analyzed using Gemini's internal reasoning"
        )
        
        return {
            "predicted_text": predicted_text,
            "verified_laws": verified_laws,
            "indiankanoon_cases": indiankanoon_cases,
            "verification_status": verification_status,
            "is_sample": is_sample
        }
        
    except Exception as e:
        logging.error(f"Legal verification failed: {e}")
        return {
            "predicted_text": "",
            "verified_laws": [],
            "indiankanoon_cases": [],
            "verification_status": "Verification unavailable",
            "is_sample": is_sample
        }


# ===================== FLASK ROUTES =====================

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/active", methods=["GET"])
def active():
    return jsonify({"status": "active", "version": "2.0-optimized"}), 200


@app.route("/summarize", methods=["POST"])
def summarize():
    start_total = time.time()
    
    try:
        # Parse request
        category = request.form.get("category", "").strip().lower()
        doc_text = request.form.get("document_text", "").strip()
        
        if not doc_text:
            return jsonify({"error": "Empty document_text"}), 400
        
        if category not in ["business", "citizen", "student"]:
            category = "citizen"  # Default fallback
        
        # Normalize whitespace (preserving structure)
        doc_text = normalize_whitespace(doc_text)
        
        # Detect language
        lang = detect_language(doc_text)
        
        # Get template
        template_text = category_templates.get(category, "{text}")
        
        logging.info(f"Processing {category} document: {len(doc_text)} chars, {estimate_tokens(doc_text)} tokens, {lang}")
        
        # ============ SHORT DOCUMENT PATH ============
        if len(doc_text) < 3500:
            start_verify = time.time()
            
            # Verify laws
            verification_data = verify_document_laws(doc_text, is_sample=False)
            
            # Build verified prompt
            verified_prompt = build_verified_context(
                doc_text,
                template_text,
                verification_data["predicted_text"],
                verification_data["verified_laws"]
            )
            
            # Add IndianKanoon cases
            if verification_data["indiankanoon_cases"]:
                verified_prompt += "\n\nThird-Party Legal Verification (IndianKanoon):\n"
                for case in verification_data["indiankanoon_cases"]:
                    verified_prompt += f"- {case['title']} ({case['citation']}) → {case['link']}\n"
            
            verified_prompt += f"\n\nVerification Status: {verification_data['verification_status']}\n"
            
            if lang == "hindi":
                verified_prompt += "\nOutput in Hindi (except Act names).\n"
            
            end_verify = time.time()
            logging.info(f"[TIMING] Verification: {end_verify - start_verify:.2f}s")
            
            # Generate summary
            start_llm = time.time()
            response = llm.invoke(verified_prompt)
            summary_text = clean_llm_response(response.content)
            end_llm = time.time()
            
            logging.info(f"[TIMING] LLM: {end_llm - start_llm:.2f}s | Total: {end_llm - start_total:.2f}s")
            
            return summary_text, 200, {'Content-Type': 'application/json; charset=utf-8'}
        
        # ============ LONG DOCUMENT PATH ============
        start_chunking = time.time()
        
        # Smart chunking with token awareness
        chunks = chunk_text_smart(doc_text, max_tokens=4000, overlap_tokens=150)
        
        end_chunking = time.time()
        logging.info(f"[TIMING] Chunking: {end_chunking - start_chunking:.2f}s ({len(chunks)} chunks)")
        
        # Legal verification on sample (parallel with chunking)
        start_verify = time.time()
        verification_data = verify_document_laws(doc_text, is_sample=True)
        end_verify = time.time()
        logging.info(f"[TIMING] Sample verification: {end_verify - start_verify:.2f}s")
        
        # Parallel chunk summarization with error handling
        start_parallel = time.time()
        
        futures = {
            executor.submit(
                summarize_chunk,
                chunk,
                i,
                len(chunks),
                category,
                lang,
                template_text
            ): i for i, chunk in enumerate(chunks)
        }
        
        # Collect results as they complete (with timeout)
        summaries = [None] * len(chunks)
        for future in as_completed(futures, timeout=300):
            try:
                chunk_idx, summary = future.result(timeout=60)
                summaries[chunk_idx] = summary
            except Exception as e:
                chunk_idx = futures[future]
                logging.error(f"Chunk {chunk_idx + 1} failed: {e}")
                summaries[chunk_idx] = f'{{"error": "Chunk processing failed"}}'
        
        # Filter out failed chunks
        valid_summaries = [s for s in summaries if s and "error" not in s.lower()]
        
        if not valid_summaries:
            return jsonify({"error": "All chunks failed to process"}), 500
        
        combined_summaries = "\n\n---CHUNK SEPARATOR---\n\n".join(valid_summaries)
        
        end_parallel = time.time()
        logging.info(f"[TIMING] Parallel summarization: {end_parallel - start_parallel:.2f}s")
        
        # Merge summaries
        start_merge = time.time()
        
        structure = get_category_structure(category)
        
        merge_prompt = f"""
{get_base_guidelines()}

Task: Merge these part-wise summaries into ONE comprehensive final summary.

Requirements:
- Combine all information intelligently
- Remove redundancy
- Maintain chronological and logical flow
- Follow this EXACT structure:

{json.dumps(structure, indent=2)}

Legal Verification Info:
- Status: {verification_data['verification_status']}
- Sample-based: {verification_data['is_sample']}
{f"- Verified Acts: {verification_data['verified_laws']}" if verification_data['verified_laws'] else ""}

Language: {"Output in Hindi (except Act names)" if lang == "hindi" else "Output in English"}

PART-WISE SUMMARIES:
{combined_summaries}

Output ONLY valid JSON:
"""
        
        final_response = llm.invoke(merge_prompt)
        summary_text = clean_llm_response(final_response.content)
        
        end_merge = time.time()
        end_total = time.time()
        
        logging.info(f"[TIMING] Merge: {end_merge - start_merge:.2f}s | Total: {end_total - start_total:.2f}s")
        
        return summary_text, 200, {'Content-Type': 'application/json; charset=utf-8'}
        
    except Exception as e:
        logging.error(f"Summarization failed: {e}", exc_info=True)
        return jsonify({
            "error": "Summarization failed",
            "details": str(e)
        }), 500


# ===================== MAIN =====================

if __name__ == "__main__":   
    
    app.run(host="0.0.0.0", port=5001, threaded=True)
