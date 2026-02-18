"""
Test the actual HTTP endpoint while the server is running
"""
import requests
import time

url = "http://127.0.0.1:5000/analyze"
pdf_path = r"c:\Users\laxmi\ai-hire\uploads\Laxmikant221b220 (1).pdf"

print("="*70)
print("🧪 TESTING HTTP ENDPOINT")
print("="*70)

print(f"\nEndpoint: {url}")
print(f"PDF: {pdf_path}")

input("\n⏸️  Press Enter AFTER you've started the server (python server.py)...")

try:
    print("\n📤 Uploading PDF to server...")
    
    with open(pdf_path, 'rb') as f:
        files = {'file': ('test_resume.pdf', f, 'application/pdf')}
        
        print("⏰ Sending request (this may take 10-20 seconds)...")
        response = requests.post(url, files=files, timeout=60)
        
        print(f"\n✅ Status Code: {response.status_code}")
        
        if response.status_code == 200:
            import json
            result = response.json()
            print("\n📊 Response:")
            print(json.dumps(result, indent=2))
            print("\n✅ ENDPOINT TEST SUCCESSFUL!")
        else:
            print(f"\n❌ Error response:")
            print(response.text)
            
except requests.exceptions.ConnectionError:
    print("\n❌ Connection failed!")
    print("Make sure the server is running: python server.py")
except requests.exceptions.Timeout:
    print("\n❌ Request timed out after 60 seconds")
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
