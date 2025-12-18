from utils.indiankanoon_utils import verify_with_indiankanoon
import os
from dotenv import load_dotenv

# Load .env to make sure environment variables are available
load_dotenv()

print("\n🔍 Testing IndianKanoon Integration...")
print(f"KANOON_API_KEY Loaded: {bool(os.getenv('KANOON_API_KEY'))}")

# Try a known Act name for test
act_name = "Information Technology Act 2000"
category = "Cyber Law"

cases = verify_with_indiankanoon(act_name, category)

if not cases:
    print("⚠️ No results found or API key invalid.")
else:
    print(f"✅ Found {len(cases)} verified results for '{act_name}'\n")
    for i, case in enumerate(cases, start=1):
        print(f"Result {i}:")
        print(f"Title    : {case['title']}")
        print(f"Citation : {case['citation']}")
        print(f"Link     : {case['link']}")
        print(f"Snippet  : {case['snippet']}\n")
        print("-" * 80)
