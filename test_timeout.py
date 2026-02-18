"""
Test with timeout to see if API is just slow
"""
import os
from google import genai
from dotenv import load_dotenv
import threading

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ No API key!")
    exit(1)

print(f"🔑 API Key loaded")

client = genai.Client(api_key=api_key)

print("📡 Testing simple API call...")

def test_generate():
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Say hello in 3 words'
        )
        print(f"✅ Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

# Run with a timeout
thread = threading.Thread(target=test_generate)
thread.daemon = True
thread.start()

print("⏰ Waiting for response (15 second timeout)...")
thread.join(timeout=15)

if thread.is_alive():
    print("❌ API call timed out after 15 seconds!")
    print("This suggests either:")
    print("  1. Network connectivity issue")
    print("  2. API rate limiting")
    print("  3. Model is unavailable")
else:
    print("✅ Test completed!")
