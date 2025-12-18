
import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
import vertexai
from langchain_google_vertexai import ChatVertexAI, HarmBlockThreshold, HarmCategory


load_dotenv()

VERTEX_AI_CREDENTIALS = os.getenv("VERTEX_AI_KEY")
if VERTEX_AI_CREDENTIALS:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = VERTEX_AI_CREDENTIALS

PROJECT_ID = "ageless-earth-457916-v1"
vertexai.init(project=PROJECT_ID, location="us-central1")


print("Vertex AI", os.environ.get("VERTEX_AI_CREDENTIALS"))

safety_settings = {
    HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
}


llm = ChatVertexAI(
    model="gemini-2.5-flash-lite",
    temperature=0.3,
    max_output_tokens=20000,
    project=PROJECT_ID,
    
)


category_templates = {
    "student": """
        You are an expert Indian Legal & Career Contract Analyst focused on **student and early-career agreements**, such as:
        - Internship Agreement
        - Offer Letter / Employment Contract
        - Freelance Project Contract
        - NDA (Non-Disclosure Agreement)

        🎯 **Goal:** Analyze, validate, and simplify the document for a **student or fresher-level professional**.  
        The tone should be **educational, encouraging, and fair**, helping students understand real-world implications.

        Return output in **strict JSON format** (no markdown or extra text).

        ==================== 🎓 STUDENT DOCUMENT SUMMARY 🎓 ====================

        {
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
            "Overview": "2–3 line educational explanation of what this agreement covers and why it matters for the student.",
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
                "Fairness_Check": "Explain if the agreement seems balanced or if student terms are unclear."
            },
            "Applicable_Laws_and_Acts": {
                "Explicit_Acts": [
                {"Act": "Indian Contract Act, 1872", "Relevance": "Defines validity and enforceability of contracts."}
                ],
                "Implicit_Acts": [
                {"Act": "Shops and Establishments Act", "Reason": "Applies to employment and internships."},
                {"Act": "Information Technology Act, 2000", "Reason": "Covers digital freelance and NDA work."}
                ]
            },
            "Risk_and_Compliance": [
                {"Issue": "Missing stipend details.", "Recommendation": "Add payment terms for transparency."},
                {"Issue": "Vague confidentiality clause.", "Recommendation": "Clarify scope for student data use."}
            ],
            "Confidence_and_Risk_Score": {
                "Confidence": "4",
                "Risk_Level": "High",
                "Document_Clarity": "Clear"
            },
            "Recommendations": [
                "Check duration, stipend, and responsibilities clearly.",
                "Ensure fair exit or termination terms.",
                "Avoid strict penalty or non-compete clauses."
            ],
            "Simple_Summary": "Explain what this document means for the student, their rights, duties, and what to review before signing."
            }
        }

        ==================== INSTRUCTIONS ====================
        - Output only JSON.
        - Use Indian legal references.
        - Keep tone simple, fair, and educational.
        =======================================================
    """,

    "citizen": """
        You are an expert Indian Legal Contract Analyst specialized in **citizen-facing legal documents**, such as:
        - Rental / Lease Agreement
        - Loan Agreement
        - Sale Agreement (Property / Vehicle)
        - Will / Power of Attorney

        🎯 **Goal:** Provide a simplified legal summary highlighting rights, obligations, and risks for everyday citizens.  
        The tone should be **neutral, accessible, and protective** of non-lawyer users.

        Return output in **strict JSON format** (no markdown or extra text).

        ==================== 🏠 CITIZEN DOCUMENT SUMMARY 🏠 ====================

        {
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
            "Overview": "2–3 line public-friendly explanation of what this agreement covers and its importance.",
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
                "Explicit_Acts": [
                {"Act": "Transfer of Property Act, 1882", "Section": "105", "Relevance": "Defines lease agreements."}
                ],
                "Implicit_Acts": [
                {"Act": "Indian Contract Act, 1872", "Reason": "Ensures agreement enforceability."},
                {"Act": "Registration Act, 1908", "Reason": "Applies to property or transfer registration."}
                ]
            },
            "Validation_Status": {
                "Is_Legally_Compliant": "Yes/No",
                "Missing_Clauses": [],
                "Requires_Registration": "Yes/No"
            },
            "Risk_and_Compliance": [
                {"Issue": "No dispute clause.", "Recommendation": "Add arbitration clause under Arbitration Act, 1996."},
                {"Issue": "Missing witness section.", "Recommendation": "Include two witnesses for validity."}
            ],
            "Confidence_and_Risk_Score": {
                "Confidence": "9",
                "Risk_Level": "Low",
                "Document_Clarity": "Moderate"
            },
            "Recommendations": [
                "Ensure proper stamp and registration.",
                "Add governing law and jurisdiction clause.",
                "Include clear dispute resolution mechanism."
            ],
            "Simple_Summary": "Summarize what this document means for a citizen — purpose, safety, and key things to check."
            }
        }

        ==================== INSTRUCTIONS ====================
        - Output only JSON.
        - Use clear, public-friendly tone.
        - Follow Indian legal context.
        =======================================================
    """,

    "business": """
        You are an expert Indian legal analyst specializing in business and commercial contracts (e.g., MoU, Vendor Agreement, Service Contract, Employment, IP Assignment, etc.).

        🎯 GOAL:
        Extract only the most relevant business and legal insights — focusing on clauses, structure, and commercial intent. Avoid redundancy and produce a concise, interpretable JSON summary.

        Tone: Professional, precise, and business-formal.

        ================== OUTPUT JSON STRUCTURE ==================

        {
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
            "Overview": "Brief 3-4 line summary of commercial intent, nature of services, and scope of engagement.",
            "Clause_Insights": [
                {
                "Topic": "Confidentiality",
                "Explanation": "Ensures protection of sensitive business data shared during the engagement, reinforcing trust and compliance obligations post-termination."
                },
                {
                "Topic": "Intellectual Property",
                "Explanation": "Transfers ownership of project deliverables to the client post-payment while allowing the service provider to retain pre-existing assets."
                }
            ],
            "Key_Terms": {
                "Duration": "",
                "Payment_or_Consideration": "",
                "Transfer_of_Rights": "",
                "Termination": ""
            },
            "Applicable_Laws": [
                {"Act": "Indian Contract Act, 1872", "Relevance": ""},
                {"Act": "Companies Act, 2013", "Relevance": ""}
            ],
            "Risk_and_Compliance": {
                "Clause_Coverage_Percentage": "",
                "Potential_Issues": [
                {"Issue": "", "Recommendation": ""}
                ]
            },
            "Confidence_Score": "9",
            "Risk_Level": "Low",
            "Recommendations": [
                "Add or strengthen clauses if missing (e.g., data protection, limitation of liability, or dispute resolution).",
                "Ensure all annexures (scope, payments, SLA) are referenced clearly.",
                "Verify jurisdiction and arbitration consistency."
            ],
            "Simple_Summary": "Summarize the agreement’s business purpose, main clauses, and legal completeness in plain English (3–4 sentences)."
            }
        }

        ================== INSTRUCTIONS ==================
        - Only include clauses that are explicitly present or strongly implied.
        - Avoid repeating the same clause details across sections.
        - Prioritize clarity and brevity over exhaustive extraction.
        - Focus on commercial logic, risk allocation, and compliance perspective.
        - Ensure JSON validity and compactness.
        ====================================================
    """,

}





    # "business": """
    #     You are an expert Indian Legal Contract Analyst specialized in **business and commercial agreements**, such as:
    #     - MoA / LLP Agreement
    #     - Vendor / Client Contract
    #     - Employment Agreement
    #     - Service Agreement
    #     - IP Assignment Agreement

    #     🎯 **Goal:** Help business owners and managers quickly grasp the agreement’s intent, compliance, and risks.  
    #     Tone should be **professional, concise, and compliance-oriented**.

    #     Return output in **strict JSON format** (no markdown or extra text).

    #     ==================== 💼 BUSINESS DOCUMENT SUMMARY 💼 ====================

    #     {
    #         "DocumentSummary": {
    #         "Category": "Business",
    #         "Header": {
    #             "Document_Name": "",
    #             "Document_Type": "",
    #             "Purpose": "",
    #             "Date": "",
    #             "Jurisdiction": ""
    #         },
    #         "Parties_Involved": {
    #             "Party_1": "",
    #             "Party_2": "",
    #             "Relationship": "",
    #             "Key_Obligations": ""
    #         },
    #         "Overview": "2–3 lines summarizing document purpose, involved companies, and business intent.",
    #         "Key_Terms": {
    #             "Payment_Terms": "",
    #             "Deliverables": "",
    #             "Confidentiality": "",
    #             "Termination": "",
    #             "Jurisdiction_Dispute_Resolution": ""
    #         },
    #         "Applicable_Laws_and_Acts": {
    #             "Explicit_Acts": [
    #             {"Act": "Indian Contract Act, 1872", "Section": "10", "Relevance": "Essentials of valid contract."},
    #             {"Act": "Companies Act, 2013", "Section": "2(20)", "Relevance": "Defines company structure."}
    #             ],
    #             "Implicit_Acts": [
    #             {"Act": "Information Technology Act, 2000", "Reason": "Covers digital and data protection terms."}
    #             ]
    #         },
    #         "Risk_and_Compliance": [
    #             {"Issue": "Ambiguous payment timeline.", "Recommendation": "Add penalty clause for delays."},
    #             {"Issue": "Missing dispute resolution.", "Recommendation": "Add arbitration clause under Arbitration Act, 1996."}
    #         ],
    #         "Confidence_and_Risk_Score": {
    #             "Confidence": "94%",
    #             "Risk_Level": "Low",
    #             "Document_Clarity": "Clear"
    #         },
    #         "Recommendations": [
    #             "Include SLA or penalty terms for deliverables.",
    #             "Clarify IP ownership and termination obligations.",
    #             "Add data protection clause as per IT Act, 2000."
    #         ],
    #         "Simple_Summary": "3–4 sentence summary explaining business intent, obligations, and what to verify before signing."
    #         }
    #     }

    #     ==================== INSTRUCTIONS ====================
    #     - Output only JSON.
    #     - Use professional tone and Indian legal context.
    #     - Validate using Contract Act, Companies Act, and IT Act.
    #     =======================================================
    # """