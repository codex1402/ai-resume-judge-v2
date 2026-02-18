import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Import functions from backend modules
from backend.gatekeeper.resume_parser import extract_text_from_pdf
from backend.gatekeeper.judge import analyze_resume_ats

# --- 1. CONFIGURATION ---
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
app = Flask(__name__)
CORS(app)  # Allow Frontend connection

print(f"API Key: {'Loaded' if api_key else 'Missing'}")

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- 2. THE SERVER ROUTES ---

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No filename"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    try:
        # Extract text from PDF
        text = extract_text_from_pdf(filepath)
        
        if not text:
            return jsonify({
                "error": "Could not extract text from PDF",
                "candidate_name": "Error",
                "overall_score": 0,
                "verdict": "ERROR"
            }), 400
        
        # Run the ATS Analysis
        result = analyze_resume_ats(text)
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Server Error: {type(e).__name__}: {e}")
        return jsonify({
            "error": str(e),
            "candidate_name": "Server Error",
            "overall_score": 0,
            "verdict": "ERROR"
        }), 500

if __name__ == '__main__':
    print("Entry-Level ATS Server Running on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
