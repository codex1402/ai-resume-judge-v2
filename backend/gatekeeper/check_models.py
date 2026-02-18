import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ No API Key found in .env")
else:
    genai.configure(api_key=api_key)
    print(f"🔑 Key found: {api_key[:5]}...")
    print("\n🔍 Scanning for available models...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"   ✅ Available: {m.name}")
    except Exception as e:
        print(f"❌ Error scanning: {e}")