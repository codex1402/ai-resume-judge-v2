"""
Simple synchronous test of HTTP endpoint
"""
import requests

url = "http://127.0.0.1:5000/analyze"
pdf_path = r"c:\Users\laxmi\ai-hire\uploads\Laxmikant221b220 (1).pdf"

print("📤 Uploading PDF...")

try:
    with open(pdf_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files, timeout=90)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        import json
        print("\n📊 Result:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"❌ {type(e).__name__}: {e}")
