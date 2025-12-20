import os
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from utils.model import llm

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("INDEX_NAME")
MODEL_NAME = os.getenv("MODEL_NAME")
API_URL = os.getenv("API_URL")

EMBED_MODEL = os.getenv("EMBED_MODEL")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)
embedder = SentenceTransformer(EMBED_MODEL)


# ---------------- STEP 1: Predict Law & Category (Gemini) ----------------
def predict_law_from_doc(doc_text: str):
    """Ask Gemini to predict act name, act number, and category."""
    prompt = f"""
You are a professional Indian legal AI trained to identify Acts and categories.
From the following document, predict:

1️⃣ The **Act Name** (e.g., "The Hindu Marriage Act, 1955")
2️⃣ The **Act Number** (e.g., "Act No. 25 of 1955")
3️⃣ The **Category** (e.g., "Family, Marriage & Personal Law")

DOCUMENT:
{doc_text}
"""
    response = llm.invoke(prompt)
    return response.content.strip()


# ---------------- STEP 2: Pinecone Verification ----------------
def verify_laws(predicted_act: str, predicted_category: str, top_k=1):
    """Fetch matching laws from Pinecone."""
    query = f"{predicted_act} {predicted_category}"
    embedding = embedder.encode(query).tolist()

    results = index.query(vector=embedding, top_k=top_k, include_metadata=True)
    verified = []
    for match in results["matches"]:
        verified.append({
            "act_name": match["metadata"]["act_name"],
            "category": match["metadata"]["category"],
            "act_details_chunk": match["metadata"]["act_details_chunk"]
        })
    return verified


# ---------------- STEP 3: Build Verified Context ----------------
def build_verified_context(doc_text, template_text, predicted_text, verified_laws):
    """Add verified context and instructions to the final prompt."""
    verified_context = "\n\n".join([
        f"Act: {v['act_name']}\nCategory: {v['category']}\nDetails: {v['act_details_chunk'][:1000]}..."
        for v in verified_laws
    ])

    return f"""
You are given:
- Original Document
- Predicted Law Context (from Gemini)
- Verified Acts fetched from Pinecone (Third-party legal DB)

Your objective:
✅ Use the VERIFIED law context to produce a final, legally grounded summary.
✅ Mention both the **Predicted Act** and **Verified Acts**.
✅ Only include verified facts.

📋 FORMAT TO FOLLOW:
{template_text}

📄 ORIGINAL DOCUMENT:
{doc_text}

📄 PREDICTED ACT INFO:
{predicted_text}

📄 VERIFIED LAW CONTEXT (from Pinecone):
{verified_context}
"""
