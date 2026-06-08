from __future__ import annotations

import json
import mimetypes
import re
import tempfile
from copy import deepcopy
from io import BytesIO
from typing import Any

import docx2txt
import fitz
from pdf2image import convert_from_bytes

from app.services.llm import llm
from app.services.ocr import ocr

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None


CATEGORY_RULES = {
    "student": {
        "label": "Student",
        "allowed_documents": [
            "Internship offer letter",
            "Admission letter",
            "Scholarship letter",
            "University notice",
            "Academic certificate",
        ],
        "keywords": [
            "admission", "scholarship", "internship", "university", "course",
            "certificate", "academic", "student", "hostel", "placement letter",
        ],
        "summary_template": {
            "DocumentSummary": {
                "Category": "Student",
                "Header": {"Document_Name": "", "Document_Type": "", "Purpose": "", "Date": "", "Jurisdiction": ""},
                "Parties_Involved": {"Party_1": "", "Party_2": "", "Relationship": "", "Key_Obligations": ""},
                "Overview": "",
                "Key_Terms": {
                    "Duration_or_Tenure": "",
                    "Stipend_or_Payment": "",
                    "Roles_and_Responsibilities": "",
                    "Termination_or_Exit_Clause": "",
                    "Ownership_or_IP": "",
                    "Confidentiality_or_NDA": "",
                },
                "Rights_and_Fairness": {"Rights_of_Party_1": "", "Rights_of_Party_2": "", "Fairness_Check": ""},
                "Applicable_Laws_and_Acts": {"Explicit_Acts": [], "Implicit_Acts": []},
                "Risk_and_Compliance": [],
                "Confidence_and_Risk_Score": {"Confidence": "", "Risk_Level": "", "Document_Clarity": ""},
                "Recommendations": [],
                "Simple_Summary": "",
            }
        },
    },
    "citizen": {
        "label": "Citizen",
        "allowed_documents": [
            "Rental agreement",
            "Loan agreement",
            "Property deed",
            "Insurance paper",
            "Legal notice",
        ],
        "keywords": [
            "rental", "lease", "loan", "insurance", "property", "notice",
            "mortgage", "agreement", "deed", "court", "petition", "affidavit",
        ],
        "summary_template": {
            "DocumentSummary": {
                "Category": "Citizen",
                "Header": {"Document_Name": "", "Document_Type": "", "Purpose": "", "Date": "", "Jurisdiction": ""},
                "Parties_Involved": {"Party_1": "", "Party_2": "", "Relationship": "", "Key_Obligations": ""},
                "Overview": "",
                "Key_Terms": {
                    "Duration_or_Tenure": "",
                    "Payment_or_Consideration": "",
                    "Transfer_of_Rights": "",
                    "Termination_or_Cancellation": "",
                    "Witness_or_Attestation": "",
                },
                "Rights_and_Obligations": {"Rights_of_Party_1": "", "Rights_of_Party_2": "", "Mutual_Obligations": ""},
                "Applicable_Laws_and_Acts": {"Explicit_Acts": [], "Implicit_Acts": []},
                "Validation_Status": {"Is_Legally_Compliant": "", "Missing_Clauses": [], "Requires_Registration": ""},
                "Risk_and_Compliance": [],
                "Confidence_and_Risk_Score": {"Confidence": "", "Risk_Level": "", "Document_Clarity": ""},
                "Recommendations": [],
                "Simple_Summary": "",
            }
        },
    },
    "business": {
        "label": "Business",
        "allowed_documents": [
            "Vendor agreement",
            "NDA",
            "Service contract",
            "Invoice",
            "Partnership agreement",
        ],
        "keywords": [
            "contract", "nda", "policy", "invoice", "vendor", "agreement",
            "partnership", "quotation", "proposal", "rfp", "compliance",
        ],
        "summary_template": {
            "DocumentSummary": {
                "Category": "Business",
                "Header": {"Document_Name": "", "Type": "", "Purpose": "", "Date": "", "Jurisdiction": ""},
                "Parties_Involved": {"Party_1": "", "Party_2": "", "Relationship": "", "Key_Obligations": ""},
                "Overview": "",
                "Clause_Insights": [],
                "Key_Terms": {"Duration": "", "Payment_or_Consideration": "", "Transfer_of_Rights": "", "Termination": ""},
                "Applicable_Laws": [],
                "Risk_and_Compliance": {"Clause_Coverage_Percentage": "", "Potential_Issues": []},
                "Confidence_Score": "",
                "Risk_Level": "",
                "Recommendations": [],
                "Simple_Summary": "",
            }
        },
    },
}

MINDMAP_ICONS = {
    "header": "document",
    "parties_involved": "people",
    "key_terms": "document",
    "applicable_laws": "law",
    "applicable_laws_and_acts": "law",
    "risk_and_compliance": "risk_high",
    "recommendations": "recommendation",
    "simple_summary": "star",
    "overview": "info",
}


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", str(text))
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def clean_llm_response(text: str) -> str:
    text = str(text).strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_json_block(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", clean_llm_response(text), re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model response.")
    return json.loads(match.group(0))


def first_non_empty_lines(text: str, limit: int = 5) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()][:limit]


def short_sentences(text: str, limit: int = 3) -> str:
    parts = re.split(r"(?<=[.!?])\s+", normalize_whitespace(text))
    return " ".join(parts[:limit]).strip()[:1200]


def extract_dates(text: str, limit: int = 6) -> list[str]:
    pattern = r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4}|[A-Za-z]+\s+\d{1,2},\s+\d{4})\b"
    seen: list[str] = []
    for match in re.findall(pattern, text):
        if match not in seen:
            seen.append(match)
        if len(seen) >= limit:
            break
    return seen


def extract_acts(text: str, limit: int = 5) -> list[str]:
    pattern = r"\b([A-Z][A-Za-z&(),.\- ]+ Act, \d{4})\b"
    seen: list[str] = []
    for match in re.findall(pattern, text):
        act = normalize_whitespace(match)
        if act not in seen:
            seen.append(act)
        if len(seen) >= limit:
            break
    return seen


def relevant_sentences(text: str, keywords: list[str], limit: int = 5) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", normalize_whitespace(text))
    matches: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in keywords):
            matches.append(sentence[:280])
        if len(matches) >= limit:
            break
    return matches


def heuristic_chunk_notes(text: str) -> dict[str, Any]:
    key_points = first_non_empty_lines(text, limit=4)
    if not key_points:
        key_points = [short_sentences(text, limit=2)] if text.strip() else []

    return {
        "Key_Points": [point for point in key_points if point],
        "Potential_Risks": relevant_sentences(text, ["penalty", "liable", "termination", "indemnity", "breach", "without pay", "no stipend"], limit=4),
        "Parties": relevant_sentences(text, ["between", "party", "institute", "company", "student", "intern", "tenant", "vendor"], limit=4),
        "Dates": extract_dates(text),
        "Clauses_or_Obligations": relevant_sentences(text, ["shall", "must", "agree", "responsible", "obligation", "submit", "complete"], limit=5),
        "Payments_or_Compensation": relevant_sentences(text, ["payment", "stipend", "fee", "salary", "consideration", "amount", "deposit"], limit=4),
        "Acts": extract_acts(text),
        "Missing_or_Unclear_Items": [
            item
            for item, keywords in {
                "Termination terms may be missing or unclear.": ["termination", "terminate", "exit"],
                "Payment or compensation terms may be missing or unclear.": ["payment", "stipend", "fee", "salary", "consideration"],
                "Confidentiality terms may be missing or unclear.": ["confidential", "nda", "non-disclosure"],
                "Intellectual property ownership may be missing or unclear.": ["intellectual property", "ip", "ownership", "copyright"],
            }.items()
            if not any(keyword in text.lower() for keyword in keywords)
        ][:4],
    }


def estimate_risk(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ["penalty", "liable", "termination", "indemnity", "breach"]):
        return "High"
    if any(term in lowered for term in ["notice", "renewal", "fee", "deposit", "arbitration"]):
        return "Medium"
    return "Low"


def merge_with_template(template: Any, result: Any) -> Any:
    if isinstance(template, dict):
        output = {}
        result_dict = result if isinstance(result, dict) else {}
        for key, value in template.items():
            output[key] = merge_with_template(value, result_dict.get(key))
        for key, value in result_dict.items():
            if key not in output:
                output[key] = value
        return output
    if isinstance(template, list):
        return result if isinstance(result, list) else deepcopy(template)
    return template if result is None else result


def extract_text(file_bytes: bytes, filename: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    filename_lower = filename.lower()
    mime_type = mimetypes.guess_type(filename)[0]
    text = ""

    try:
        if filename_lower.endswith(".pdf") and mime_type == "application/pdf":
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                for page in doc:
                    text += page.get_text("text") + "\n"
            text = text.strip()
            if text:
                return normalize_whitespace(text), warnings
    except Exception as exc:
        warnings.append(f"PDF text extraction failed: {exc}")

    try:
        if filename_lower.endswith(".docx"):
            with tempfile.NamedTemporaryFile(delete=True, suffix=".docx") as temp_file:
                temp_file.write(file_bytes)
                temp_file.flush()
                text = docx2txt.process(temp_file.name) or ""
            if text.strip():
                return normalize_whitespace(text), warnings
    except Exception as exc:
        warnings.append(f"DOCX extraction failed: {exc}")

    if filename_lower.endswith(".txt"):
        return normalize_whitespace(file_bytes.decode("utf-8", errors="ignore")), warnings

    if not (mime_type and ("image" in mime_type or filename_lower.endswith(".pdf"))):
        return "", warnings

    if not ocr.available():
        warnings.append("Google Vision OCR is not configured, so image OCR is unavailable.")
        return "", warnings

    try:
        if filename_lower.endswith(".pdf"):
            pages = convert_from_bytes(file_bytes, dpi=250)
        else:
            if not Image:
                warnings.append("Pillow is unavailable for image OCR.")
                return "", warnings
            pages = [Image.open(BytesIO(file_bytes))]

        chunks = []
        for index, page in enumerate(pages, start=1):
            buffer = BytesIO()
            page.save(buffer, format="JPEG")
            page_text = ocr.detect(buffer.getvalue())
            if page_text:
                chunks.append(f"--- PAGE {index} ---\n{page_text}")
        return normalize_whitespace("\n\n".join(chunks)), warnings
    except Exception as exc:
        warnings.append(f"OCR extraction failed: {exc}")
        return "", warnings


def pre_filter(text: str) -> str:
    scores = {
        category: sum(keyword in text.lower() for keyword in rule["keywords"])
        for category, rule in CATEGORY_RULES.items()
    }
    predicted = max(scores, key=scores.get)
    return predicted if scores[predicted] else "invalid"


def _heuristic_classification(text: str, selected_category: str) -> tuple[dict[str, Any], str]:
    predicted = pre_filter(text)
    allowed_docs = CATEGORY_RULES[selected_category]["allowed_documents"]
    if predicted == "invalid":
        return (
            {
                "predicted_category": "INVALID_DOC",
                "confidence": "low",
                "reason": "The uploaded file does not look like a supported legal document for this section.",
                "suggested_action": f"Upload one of these {CATEGORY_RULES[selected_category]['label'].lower()} documents: {', '.join(allowed_docs)}.",
                "can_generate_summary": False,
                "expected_documents": allowed_docs,
            },
            "heuristic",
        )

    matched = predicted == selected_category
    predicted_label = f"{predicted.upper()}_DOC"
    return (
        {
            "predicted_category": predicted_label,
            "confidence": "medium" if matched else "low",
            "reason": "Keyword-based fallback matched the document to the closest legal category.",
            "suggested_action": (
                "Document processed successfully."
                if matched
                else f"This file looks like a {CATEGORY_RULES[predicted]['label'].lower()} document, not a {CATEGORY_RULES[selected_category]['label'].lower()} document."
            ),
            "can_generate_summary": matched,
            "expected_documents": allowed_docs,
        },
        "heuristic",
    )


def classify_document(text: str, selected_category: str) -> tuple[dict[str, Any], str]:
    if not text.strip():
        return (
            {
                "predicted_category": "INVALID_DOC",
                "confidence": "low",
                "reason": "The file did not contain readable text.",
                "suggested_action": "Upload a readable PDF, DOCX, TXT, PNG, or JPG file.",
                "can_generate_summary": False,
                "expected_documents": CATEGORY_RULES[selected_category]["allowed_documents"],
            },
            "heuristic",
        )

    prompt = f"""
Classify this uploaded document into exactly one of these:
- CITIZEN_DOC
- BUSINESS_DOC
- STUDENT_DOC
- INVALID_DOC

Return strict JSON only:
{{
  "predicted_category": "CITIZEN_DOC | BUSINESS_DOC | STUDENT_DOC | INVALID_DOC",
  "confidence": "high | medium | low",
  "reason": "Short explanation",
  "suggested_action": "What the user should do next"
}}

Selected section: {selected_category}
Document:
{text[:12000]}
""".strip()

    try:
        raw_text, provider = llm.generate(
            prompt,
            "You are an Indian legal document classifier. Return JSON only.",
            max_tokens=220,
            temperature=0.0,
        )
        result = extract_json_block(raw_text)
        matched = result.get("predicted_category") == f"{selected_category.upper()}_DOC"
        result["can_generate_summary"] = matched
        result["expected_documents"] = CATEGORY_RULES[selected_category]["allowed_documents"]
        if not matched and result.get("predicted_category") != "INVALID_DOC":
            result["suggested_action"] = (
                f"This file looks like a {result['predicted_category'].replace('_DOC', '').lower()} document. "
                f"Please upload a {CATEGORY_RULES[selected_category]['label'].lower()} document in this section."
            )
        if result.get("predicted_category") == "INVALID_DOC":
            result["can_generate_summary"] = False
        return result, provider
    except Exception:
        return _heuristic_classification(text, selected_category)


def heuristic_summary(category: str, text: str, provider: str = "heuristic") -> dict[str, Any]:
    summary = deepcopy(CATEGORY_RULES[category]["summary_template"])
    doc = summary["DocumentSummary"]
    lines = first_non_empty_lines(text)
    overview = short_sentences(text, limit=4)
    risk_level = estimate_risk(text)
    doc_name = lines[0][:120] if lines else "Uploaded Document"

    header = doc.get("Header", {})
    header["Document_Name"] = doc_name
    if "Document_Type" in header:
        header["Document_Type"] = f"{CATEGORY_RULES[category]['label']} Legal Document"
    if "Type" in header:
        header["Type"] = f"{CATEGORY_RULES[category]['label']} Legal Document"
    header["Purpose"] = overview[:240]
    header["Jurisdiction"] = "India"

    parties = doc["Parties_Involved"]
    parties["Party_1"] = "Not clearly identified"
    parties["Party_2"] = "Not clearly identified"
    parties["Relationship"] = f"{CATEGORY_RULES[category]['label']} legal relationship"
    parties["Key_Obligations"] = "Review the uploaded text carefully before relying on this summary."

    doc["Overview"] = overview or "Fallback summary generated without a live LLM provider."
    doc["Simple_Summary"] = doc["Overview"]
    doc["Recommendations"] = [
        "Check all names, dates, and payment clauses carefully.",
        f"Use the {CATEGORY_RULES[category]['label'].lower()} section only for the right document type.",
        "Consult a legal professional before taking a final decision.",
    ]

    if category == "business":
        doc["Clause_Insights"] = [
            {"Topic": "Fallback Summary", "Explanation": "This summary was created without full semantic extraction."}
        ]
        doc["Applicable_Laws"] = [{"Act": "Indian Contract Act, 1872", "Relevance": "General contract enforceability."}]
        doc["Risk_and_Compliance"]["Clause_Coverage_Percentage"] = "Partial"
        doc["Risk_and_Compliance"]["Potential_Issues"] = [
            {"Issue": "Detailed clause extraction unavailable.", "Recommendation": "Enable a live LLM provider for richer analysis."}
        ]
        doc["Confidence_Score"] = "Low"
        doc["Risk_Level"] = risk_level
    else:
        doc["Applicable_Laws_and_Acts"]["Explicit_Acts"] = [{"Act": "Indian Contract Act, 1872", "Reason": "Baseline legal framework."}]
        doc["Risk_and_Compliance"] = [{"Issue": "Fallback summary mode is active.", "Recommendation": "Enable a live LLM provider for better accuracy."}]
        doc["Confidence_and_Risk_Score"]["Confidence"] = "Low"
        doc["Confidence_and_Risk_Score"]["Risk_Level"] = risk_level
        doc["Confidence_and_Risk_Score"]["Document_Clarity"] = "Partial"
        if category == "citizen":
            doc["Validation_Status"]["Is_Legally_Compliant"] = "Unknown"
            doc["Validation_Status"]["Requires_Registration"] = "Unknown"

    doc["_meta"] = {"provider_used": provider, "fallback": provider == "heuristic"}
    return summary


def chunk_text(text: str, max_chars: int = 9000, overlap: int = 400) -> list[str]:
    chunks = []
    start = 0
    text = normalize_whitespace(text)
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n\n", start, end), text.rfind(". ", start, end), text.rfind(" ", start, end))
            if boundary > start + 1000:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


def summarize_document(category: str, text: str) -> dict[str, Any]:
    template = CATEGORY_RULES[category]["summary_template"]
    chunks = chunk_text(text)
    if not chunks:
        return heuristic_summary(category, text)

    notes_prompt = """
Return strict JSON only:
{
  "Key_Points": [],
  "Potential_Risks": [],
  "Parties": [],
  "Dates": [],
  "Clauses_or_Obligations": [],
  "Payments_or_Compensation": [],
  "Acts": [],
  "Missing_or_Unclear_Items": []
}
""".strip()

    try:
        notes = [heuristic_chunk_notes(chunk) for chunk in chunks[: min(3, len(chunks))]]
        if len(chunks) <= 2:
            selected_chunks = chunks
        else:
            selected_chunks = [chunks[0], chunks[len(chunks) // 2], chunks[-1]]
        document_excerpt = "\n\n--- DOCUMENT SEGMENT ---\n\n".join(selected_chunks)[:12000]

        prompt = f"""
Create a detailed, production-quality Indian legal document summary.
Return only valid JSON using this exact structure:
{json.dumps(template, indent=2)}

Output rules:
- Keep the language simple, clear, and professional.
- Be comprehensive and field-rich, not short or generic.
- Use only facts grounded in the document text or clearly supported by the chunk notes.
- Do not invent clauses, dates, parties, payments, or laws.
- Do not mention fake or speculative laws like "if applicable" placeholders.
- If a legal act is not clearly stated or strongly inferable, write "Not clearly identifiable from the document".
- If a field is missing in the document, write "Not stated in the document".
- Make the Overview 4 to 7 sentences when enough material exists.
- Make Simple_Summary 3 to 5 sentences in plain language.
- Provide at least 4 actionable Recommendations when the document contains enough substance.
- Mention practical risks, fairness concerns, missing clauses, and next actions.
- Extract names, dates, payment details, duration, exit terms, IP, confidentiality, obligations, and compliance points whenever present.
- If the document appears weak, incomplete, one-sided, or unfair, say so clearly.

Category-specific rules:
- For student documents, explicitly assess stipend fairness, unpaid workload, research or publication burden, IP ownership, reporting burden, and termination clarity.
- For citizen documents, explicitly assess registration need, enforceability, witness requirements, compliance gaps, missing clauses, and day-to-day risk to the individual.
- For business documents, explicitly assess payment clarity, deliverables, indemnity or liability exposure, termination rights, IP ownership, confidentiality, and compliance gaps.

Formatting rules:
- Recommendations must be specific, practical, and written as short action items.
- Risk_and_Compliance should highlight real issues, not generic filler.
- Applicable laws should be conservative and real.
- If the document does not fit the selected category well, mention the mismatch in Recommendations or Risk_and_Compliance.

Chunk notes:
{json.dumps(notes, indent=2)}

Document text:
{document_excerpt}
""".strip()
        raw_text, provider = llm.generate(
            prompt,
            "You are a professional Indian legal analyst. Return strict JSON only and keep the output faithful to the document.",
            max_tokens=3200,
            temperature=0.08,
        )
        merged = merge_with_template(template, extract_json_block(raw_text))
        merged["DocumentSummary"]["_meta"] = {"provider_used": provider, "fallback": False, "chunk_count": len(chunks)}
        return merged
    except Exception:
        return heuristic_summary(category, text)


def flatten_scalar(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value[:3]:
            if isinstance(item, dict):
                parts.append(", ".join(f"{k}: {v}" for k, v in list(item.items())[:2]))
            else:
                parts.append(str(item))
        return "; ".join(parts)
    if isinstance(value, dict):
        return ", ".join(f"{k}: {v}" for k, v in list(value.items())[:2])
    return str(value)


def heuristic_mindmap(summary_json: dict[str, Any]) -> dict[str, Any]:
    summary = summary_json.get("DocumentSummary", summary_json)
    header = summary.get("Header", {})
    root_label = header.get("Document_Name") or "Document Summary"
    root_details = header.get("Purpose") or summary.get("Overview") or "Generated summary"
    children = []
    for key, value in summary.items():
        if key in {"Header", "_meta"} or not value:
            continue
        child = {
            "id": key.lower(),
            "label": key.replace("_", " ")[:40],
            "details": short_sentences(flatten_scalar(value), limit=1) or "N/A",
            "icon": MINDMAP_ICONS.get(key.lower(), "info"),
            "status": "info",
            "secondaryLabel": "",
            "children": [],
        }
        if isinstance(value, dict):
            for sub_key, sub_value in list(value.items())[:8]:
                child["children"].append(
                    {
                        "id": f"{key.lower()}-{sub_key.lower()}",
                        "label": sub_key.replace("_", " ")[:36],
                        "details": short_sentences(flatten_scalar(sub_value), limit=1) or "N/A",
                        "icon": "info",
                        "status": "neutral",
                        "secondaryLabel": "",
                        "children": [],
                    }
                )
        children.append(child)
    return {
        "id": "root",
        "label": root_label[:48],
        "details": short_sentences(root_details, limit=1) or "N/A",
        "icon": "document",
        "status": "info",
        "secondaryLabel": summary.get("Category", ""),
        "children": children,
    }


def generate_mindmap(summary_json: dict[str, Any], category: str) -> dict[str, Any]:
    prompt = f"""
Convert this legal summary JSON into a hierarchical mind map JSON.
Return only valid JSON:
{{
  "id": "root",
  "label": "short title",
  "details": "one short sentence",
  "icon": "document | law | people | risk_high | risk_low | check | money | time | info | recommendation | star",
  "status": "positive | negative | neutral | info",
  "secondaryLabel": "",
  "children": []
}}

Summary:
{json.dumps(summary_json, ensure_ascii=False)}
Category: {category}
""".strip()
    try:
        raw_text, provider = llm.generate(
            prompt,
            "You convert structured summaries into hierarchical JSON mind maps. Return JSON only.",
            max_tokens=1600,
            temperature=0.08,
        )
        result = extract_json_block(raw_text)
        result.setdefault("id", "root")
        result.setdefault("secondaryLabel", category.title())
        result["_meta"] = {"provider_used": provider, "fallback": False}
        return result
    except Exception:
        result = heuristic_mindmap(summary_json)
        result["_meta"] = {"provider_used": "heuristic", "fallback": True}
        return result
