import requests

def push_to_confluence(url: str, email: str, token: str, space_key: str, title: str, html_content: str) -> dict:
    if url.endswith('/'):
        url = url[:-1]
        
    confluence_api = f"{url}/wiki/rest/api/content"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "type": "page",
        "title": title,
        "space": {
            "key": space_key
        },
        "body": {
            "storage": {
                "value": html_content,
                "representation": "storage"
            }
        }
    }
    
    try:
        response = requests.post(confluence_api, json=payload, auth=(email, token), headers=headers)
        if response.status_code in [200, 201]:
            data = response.json()
            # Construct absolute link
            link = url + data.get("_links", {}).get("webui", "")
            return {"status": "success", "link": link}
        else:
            # Try to parse error
            msg = response.text
            try:
                msg = response.json().get('message', msg)
            except:
                pass
            return {"status": "error", "detail": f"HTTP {response.status_code}: {msg}"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

def generate_confluence_html(ticket_id: str, content: dict) -> str:
    html = f"<h1>AI Generated Test Plan for {ticket_id}</h1>"
    
    html += "<h2>Objective</h2>"
    html += f"<p>{content.get('objective', '')}</p>"
    
    html += "<h2>Scope</h2>"
    html += f"<p>{content.get('scope', '')}</p>"
    
    html += "<h2>Test Scenarios</h2>"
    html += "<ul>"
    scenarios = content.get('test_scenarios', [])
    if isinstance(scenarios, list):
        for s in scenarios:
            html += f"<li>{s}</li>"
    else:
        html += f"<li>{scenarios}</li>"
    html += "</ul>"
    
    html += "<h2>Risks</h2>"
    html += f"<p>{content.get('risks', '')}</p>"
    
    html += "<h2>Environment</h2>"
    html += f"<p>{content.get('environment', '')}</p>"
    
    return html
