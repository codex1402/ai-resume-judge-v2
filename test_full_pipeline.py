"""
Full test of the resume judging pipeline with detailed logging
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("="*70)
print("🧪 TESTING RESUME JUDGING PIPELINE")
print("="*70)

# Step 1: Import and configure
print("\n📦 Step 1: Importing modules...")
try:
    from backend.gatekeeper.resume_parser import extract_text_from_pdf
    from backend.gatekeeper.judge import judge_resume
    print("✅ Modules imported successfully")
except Exception as e:
    print(f"❌ Import failed: {e}")
    exit(1)

# Step 2: Extract text from PDF
print("\n📄 Step 2: Extracting text from PDF...")
pdf_path = r"c:\Users\laxmi\ai-hire\uploads\Laxmikant221b220 (1).pdf"

try:
    text = extract_text_from_pdf(pdf_path)
    print(f"✅ Extracted {len(text)} characters")
    print(f"First 150 chars: {text[:150]}...")
except Exception as e:
    print(f"❌ Extraction failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 3: Judge the resume
print("\n🤖 Step 3: Judging resume with AI...")
print("(This may take 10-15 seconds...)")

try:
    result = judge_resume(text, track="PRODUCT")
    
    print("\n" + "="*70)
    print("📊 RESULT:")
    print("="*70)
    
    import json
    print(json.dumps(result, indent=2))
    
    print("\n" + "="*70)
    print("✅ PIPELINE TEST SUCCESSFUL!")
    print("="*70)
    
except KeyboardInterrupt:
    print("\n\n⚠️  Interrupted by user")
    exit(1)
except Exception as e:
    print(f"\n❌ Judging failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
