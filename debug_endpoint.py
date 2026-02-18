"""
Debug script to test the resume scoring endpoint
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))

from backend.gatekeeper.judge import judge_resume
from backend.gatekeeper.resume_parser import extract_text_from_pdf

# Test with uploaded PDF
pdf_path = r"c:\Users\laxmi\ai-hire\uploads\Laxmikant221b220 (1).pdf"

print("="*60)
print("🧪 DEBUG: Testing Resume Scoring Pipeline")
print("="*60)

try:
    #Step 1: Extract text from PDF
    print("\n📄 Step 1: Extracting text from PDF...")
    text = extract_text_from_pdf(pdf_path)
    print(f"✅ Extracted {len(text)} characters")
    print(f"Preview: {text[:200]}...")
    
    # Step 2: Judge the resume
    print("\n🤖 Step 2: Judging resume...")
    result = judge_resume(text, track="PRODUCT")
    
    print("\n"+"="*60)
    print("📊 FINAL RESULT:")
    print("="*60)
    import json
    print(json.dumps(result, indent=2))
    
    print("\n✅ Pipeline completed successfully!")
    
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
