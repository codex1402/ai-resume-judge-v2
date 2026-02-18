import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

print(f"API Key loaded: {api_key[:10] if api_key else 'NONE'}...")

if not api_key:
    print("❌ No API key found in .env!")
    exit()

try:
    # Initialize the client
    client = genai.Client(api_key=api_key)
    
    print("\n🔍 Listing available models...")
    
    # List all available models
    models = client.models.list()
    print("\n📋 Available Models:")
    for model in models:
        print(f"   • {model.name}")
    
    print("\n🧪 Testing model...")
    
    # Test with the correct model name
    response = client.models.generate_content(
        model='gemini-2.5-flash',  # ← CHANGED THIS
        contents='Say "Hello, I am working!"'
    )
    
    print(f"✅ SUCCESS!")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()