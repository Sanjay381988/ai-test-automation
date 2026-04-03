import os
from dotenv import load_dotenv
from tools.alm_connection_tool import test_jira_connection, test_ado_connection
from tools.llm_connection_tool import test_ollama_connection, test_groq_connection

def run_handshake():
    load_dotenv()
    print("--- ⚡ Phase 2: Link (Verification) ---")
    
    # Test Jira
    jira_url = os.getenv("JIRA_URL")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_token = os.getenv("JIRA_API_TOKEN")
    
    if jira_url and jira_email and jira_token and "your-domain" not in jira_url:
        print(f"Testing Jira ({jira_url})...")
        if test_jira_connection(jira_url, jira_email, jira_token):
            print("✅ Jira Connection: PASS")
        else:
            print("❌ Jira Connection: FAIL")
    else:
        print("⚠️ Jira Connection: Skipped (no valid credentials in .env)")

    # Test Local Ollama
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    print(f"Testing Ollama ({ollama_url})...")
    if test_ollama_connection(ollama_url):
        print("✅ Ollama Connection: PASS")
    else:
        print("❌ Ollama Connection: FAIL")

if __name__ == "__main__":
    run_handshake()
