import requests

# Test the API endpoint
url = "http://127.0.0.1:5000/analyze"
pdf_path = r"c:\Users\laxmi\ai-hire\uploads\Laxmikant221b220 (1).pdf"

try:
    with open(pdf_path, 'rb') as f:
        files = {'file': ('resume.pdf', f, 'application/pdf')}
        print("📤 Uploading PDF to server...")
        response = requests.post(url, files=files)
        
        print(f"\n✅ Status Code: {response.status_code}")
        print(f"\n📊 Response:")
        print(response.json())
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
