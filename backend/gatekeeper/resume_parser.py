"""
AI Hiring Lab - PDF Resume Parser
Day 1: Extract and clean text from resume PDFs
Author: Laxmikant Shukla
"""

import PyPDF2
import sys
from pathlib import Path


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as a string
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            num_pages = len(pdf_reader.pages)
            print(f"📄 Found {num_pages} page(s) in PDF")
            
            # Extract text from each page
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                text += page_text + "\n"
                print(f"   ✓ Extracted page {page_num}/{num_pages}")
            
            return text.strip()
    
    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")


def clean_text(text: str) -> str:
    """
    Clean extracted text by removing extra whitespace.
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text with normalized spacing
    """
    # Remove multiple spaces and normalize whitespace
    cleaned = ' '.join(text.split())
    return cleaned


def analyze_resume_structure(text: str) -> dict:
    """
    Basic analysis of resume structure.
    
    Args:
        text: Resume text
        
    Returns:
        Dictionary with basic stats
    """
    words = text.split()
    
    # Common resume keywords
    keywords = {
        'education': ['education', 'degree', 'university', 'college', 'b.tech', 'm.tech'],
        'experience': ['experience', 'worked', 'intern', 'job', 'company'],
        'skills': ['skills', 'python', 'java', 'javascript', 'react', 'django'],
        'projects': ['project', 'built', 'developed', 'created'],
        'contact': ['email', 'phone', 'linkedin', 'github']
    }
    
    stats = {
        'total_chars': len(text),
        'total_words': len(words),
        'sections_found': []
    }
    
    text_lower = text.lower()
    for section, section_keywords in keywords.items():
        if any(keyword in text_lower for keyword in section_keywords):
            stats['sections_found'].append(section)
    
    return stats


def main():
    """Main function to test the PDF parser."""
    
    print("=" * 70)
    print("🚀 AI HIRING LAB - RESUME PARSER")
    print("=" * 70)
    print()
    
    # Check for command line argument
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = "backend/test_data/sample_resume.pdf"
    
    print(f"📂 Target file: {pdf_path}")
    print()
    
    # Check if file exists
    if not Path(pdf_path).exists():
        print("❌ ERROR: File not found!")
        print()
        print("💡 To test the parser:")
        print("   1. Add a PDF resume to: backend/test_data/sample_resume.pdf")
        print("   2. Or run: python backend/gatekeeper/parser.py <path-to-resume.pdf>")
        print()
        return
    
    try:
        # Extract text
        print("🔄 Extracting text from PDF...")
        raw_text = extract_text_from_pdf(pdf_path)
        
        # Clean text
        print("🧹 Cleaning text...")
        cleaned_text = clean_text(raw_text)
        
        # Analyze structure
        print("🔍 Analyzing resume structure...")
        stats = analyze_resume_structure(cleaned_text)
        
        # Display results
        print()
        print("=" * 70)
        print("📊 EXTRACTION RESULTS")
        print("=" * 70)
        print()
        print(f"✓ Total characters: {stats['total_chars']:,}")
        print(f"✓ Total words: {stats['total_words']:,}")
        print(f"✓ Sections detected: {', '.join(stats['sections_found']) if stats['sections_found'] else 'None'}")
        print()
        print("-" * 70)
        print("📝 EXTRACTED TEXT (First 600 characters):")
        print("-" * 70)
        print()
        print(cleaned_text[:600])
        if len(cleaned_text) > 600:
            print("\n... [Text truncated for display]")
        print()
        print("=" * 70)
        print("✅ SUCCESS! PDF Parser is working correctly!")
        print("=" * 70)
        
    except FileNotFoundError as e:
        print(f"❌ ERROR: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        print("💡 Make sure the PDF is not corrupted and is readable.")
        print("DEBUG TEXT LENGTH:", len(text))




if __name__ == "__main__":
    main()