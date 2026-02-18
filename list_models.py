"""
Quick test: List available Gemini models
"""
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ No API key found!")
    exit(1)

print(f"🔑 API Key: {api_key[:10]}...")

try:
    client = genai.Client(api_key=api_key)
    print("\n📋 Listing all available models...\n")
    
    models = client.models.list()
    gemini_models = []
    
    for model in models:
        print(f"  • {model.name}")
        if 'gemini' in model.name.lower():
            gemini_models.append(model.name)
    
    print(f"\n✅ Found {len(list(models))} total models")
    print(f"\n🎯 Gemini models:")
    for gm in gemini_models:
        print(f"   → {gm}")
        
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
