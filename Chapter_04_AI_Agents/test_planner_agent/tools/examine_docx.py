import docx
import sys

def extract_text(doc_path):
    try:
        doc = docx.Document(doc_path)
        text = []
        for para in doc.paragraphs:
            if para.text.strip():
                text.append(para.text.strip())
        print("\n".join(text[:50])) # Print first 50 lines
    except Exception as e:
        print(f"Error reading docx: {e}")

if __name__ == "__main__":
    extract_text(sys.argv[1])
