import requests

def test_ollama_connection(url: str = "http://localhost:11434") -> bool:
    try:
        resp = requests.get(f"{url}/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception as e:
        print(f"Ollama connection failed: {e}")
        return False

def test_groq_connection(api_key: str) -> bool:
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        resp = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=5)
        return resp.status_code == 200
    except Exception as e:
        print(f"GROQ connection failed: {e}")
        return False
