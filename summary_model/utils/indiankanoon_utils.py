import os
import requests
from dotenv import load_dotenv

# -------------------- LOAD ENV --------------------
load_dotenv()
token = os.getenv("KANOON_API_KEY")

if not token:
    raise ValueError("⚠️ Missing KANOON_API_KEY in environment variables!")

# -------------------- SEARCH FUNCTION --------------------
def search_indiankanoon(act_query, page=0):
    """
    Search IndianKanoon for judgments related to a law, section, or category.
    """
    url = "https://api.indiankanoon.org/search/"
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    payload = {"formInput": act_query, "pagenum": str(page)}

    response = requests.post(url, data=payload, headers=headers)
    if response.status_code != 200:
        print(f"❌ IndianKanoon search failed: {response.status_code}")
        return []

    data = response.json()
    return data.get("docs", [])


# -------------------- FETCH CASE TEXT --------------------
def fetch_case_text(docid):
    """
    Fetch short judgment snippet for a specific document ID.
    """
    url = f"https://api.indiankanoon.org/doc/{docid}/"
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    response = requests.post(url, headers=headers)
    if response.status_code != 200:
        return "⚠️ Full text not available."

    data = response.json()
    return data.get("doc", "")[:400]  # only first 400 characters


# -------------------- MAIN VERIFY FUNCTION --------------------
def verify_with_indiankanoon(act_name, category):
    """
    Combine Act + Category to fetch top 3 judgments from IndianKanoon.
    Returns a list of dicts containing title, citation, link, and short snippet.
    """
    if not act_name and not category:
        return []

    query = act_name or category
    docs = search_indiankanoon(query)

    verified_cases = []
    for doc in docs[:3]:
        title = doc.get("title", "N/A")
        citation = doc.get("citation", "N/A")
        docid = doc.get("docid")
        link = f"https://indiankanoon.org/doc/{docid}/" if docid else "N/A"
        snippet = fetch_case_text(docid) if docid else "⚠️ Text not available."

        verified_cases.append({
            "title": title,
            "citation": citation,
            "link": link,
            "snippet": snippet
        })

    return verified_cases
