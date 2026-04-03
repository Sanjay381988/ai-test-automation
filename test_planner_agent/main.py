import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tools.alm_connection_tool import test_jira_connection, test_ado_connection
from tools.llm_connection_tool import test_ollama_connection, test_groq_connection
from tools.alm_fetch_tool import fetch_jira_ticket, fetch_ado_ticket
from tools.llm_generate_tool import generate_test_plan_content
from tools.docx_writer_tool import generate_test_plan_docx
from tools.confluence_tool import push_to_confluence, generate_confluence_html

app = FastAPI(title="AI Test Planner API")
TMP_DIR = "/tmp" if os.name != "nt" else os.path.join(os.path.dirname(__file__), ".tmp")
os.makedirs(TMP_DIR, exist_ok=True)

def normalize_content(content: dict) -> dict:
    """Normalize LLM output so all fields are plain strings / list-of-strings.
    Prevents React 'Objects are not valid as a React child' crashes."""
    # Normalize list fields
    for field in ["test_scenarios"]:
        val = content.get(field)
        if val is None:
            content[field] = []
        elif isinstance(val, dict):
            content[field] = [str(v) for v in val.values()]
        elif isinstance(val, list):
            normalized = []
            for item in val:
                if isinstance(item, str):
                    normalized.append(item)
                elif isinstance(item, dict):
                    # Extract most meaningful string from dict
                    text = (item.get("scenario") or item.get("name") or
                            item.get("description") or item.get("title") or
                            item.get("text") or item.get("step") or str(item))
                    normalized.append(str(text))
                else:
                    normalized.append(str(item))
            content[field] = normalized
        elif isinstance(val, str):
            # Split newline-separated strings into list
            content[field] = [s.strip() for s in val.split('\n') if s.strip()]
        else:
            content[field] = [str(val)]

    # Normalize scalar fields
    for field in ["objective", "scope", "risks", "environment"]:
        val = content.get(field)
        if val is None:
            content[field] = ""
        elif isinstance(val, list):
            content[field] = " ".join(str(v) for v in val)
        elif isinstance(val, dict):
            content[field] = "; ".join(f"{k}: {v}" for k, v in val.items())
        elif not isinstance(val, str):
            content[field] = str(val)

    return content


def generate_markdown_content(ticket_id: str, content: dict) -> str:
    md = f"# Test Plan: {ticket_id}\n\n"
    if content.get("objective"):
        md += f"## 🎯 Objective\n{content['objective']}\n\n"
    if content.get("scope"):
        md += f"## 📋 Scope\n{content['scope']}\n\n"
    if content.get("test_scenarios"):
        md += f"## 🧪 Test Scenarios\n"
        scenarios = content["test_scenarios"]
        if isinstance(scenarios, list):
            for s in scenarios:
                md += f"- {s}\n"
        else:
            md += f"{scenarios}\n"
        md += "\n"
    if content.get("risks"):
        md += f"## ⚠️ Risks\n{content['risks']}\n\n"
    if content.get("environment"):
        md += f"## 🖥️ Environment\n{content['environment']}\n\n"
    return md

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ALMConnectionTest(BaseModel):
    provider: str
    url: str
    email: str = ""
    token: str = ""
    pat: str = ""

class LLMConnectionTest(BaseModel):
    provider: str
    url: str = ""
    api_key: str = ""

class GeneratePlanRequest(BaseModel):
    alm_provider: str
    alm_url: str
    alm_email: str = ""
    alm_token: str = ""
    alm_pat: str = ""
    llm_provider: str
    llm_model: str
    llm_api_key: str = ""
    llm_url: str = ""
    ticket_id: str
    additional_context: str = ""

class PushConfluenceRequest(BaseModel):
    alm_url: str
    alm_email: str
    alm_token: str
    space_key: str
    ticket_id: str
    content: dict

@app.post("/api/test-alm")
def api_test_alm(req: ALMConnectionTest):
    if req.provider.lower() == "jira":
        ok = test_jira_connection(req.url, req.email, req.token)
    else:
        ok = test_ado_connection(req.url, req.pat)
    if ok:
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="ALM Connection Failed")

@app.post("/api/test-llm")
def api_test_llm(req: LLMConnectionTest):
    if "mock" in req.provider.lower():
        return {"status": "success"}
    if req.provider.lower() == "groq":
        ok = test_groq_connection(req.api_key)
    else:
        ok = test_ollama_connection(req.url)
    if ok:
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="LLM Connection Failed")

@app.post("/api/generate")
def api_generate(req: GeneratePlanRequest):
    # Fetch Ticket
    if req.alm_provider.lower() == "jira":
        ticket_data = fetch_jira_ticket(req.alm_url, req.alm_email, req.alm_token, req.ticket_id)
    else:
        ticket_data = fetch_ado_ticket(req.alm_url, req.alm_pat, req.ticket_id)
        
    if "error" in ticket_data:
        raise HTTPException(status_code=400, detail=f"ALM Error: {ticket_data['error']}")
        
    # Set up LLM
    llm_config = {
        "provider": req.llm_provider.lower(),
        "model": req.llm_model,
        "api_key": req.llm_api_key,
        "url": req.llm_url
    }
    
    # Generate content
    if "mock" in llm_config["provider"]:
        content = {
            "objective": "Mock UI Testing Objective fetching ticket " + ticket_data.get("key", ""),
            "scope": "In-scope: UI Preview logic. Out-of-scope: Actual LLM call.",
            "test_scenarios": ["Verify LLM bypass works", "Verify Docx Generation completes safely"],
            "risks": "No actual AI testing logic generated.",
            "environment": "Localhost Dashboard Environment"
        }
    else:
        content = generate_test_plan_content(ticket_data, llm_config, req.additional_context)
    if "error" in content:
        raise HTTPException(status_code=500, detail=f"LLM Error: {content['error']}")

    # Normalize LLM output to prevent frontend rendering crashes
    content = normalize_content(content)

    # Write docx
    import os
    template_path = os.path.join(os.path.dirname(__file__), "resources", "Test Plan - Template.docx")
    
    file_name = f"Test_Plan_{req.ticket_id}_{uuid.uuid4().hex[:6]}.docx"
    output_path = os.path.join(TMP_DIR, file_name)
    
    success = generate_test_plan_docx(template_path, output_path, content)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write docx file.")
        
    # Save MD version for download in Phase 4 too
    md_content = generate_markdown_content(req.ticket_id, content)
    md_file_name = f"Test_Plan_{req.ticket_id}_{uuid.uuid4().hex[:6]}.md"
    with open(os.path.join(TMP_DIR, md_file_name), "w", encoding="utf-8") as f:
        f.write(md_content)
        
    # Get HTML for UI display
    html_preview = generate_confluence_html(req.ticket_id, content)
        
    return {"status": "success", "file_name": file_name, "md_file": md_file_name, "data": content, "html": html_preview}

@app.post("/api/preview")
def api_preview(req: GeneratePlanRequest):
    if req.alm_provider.lower() == "jira":
        ticket_data = fetch_jira_ticket(req.alm_url, req.alm_email, req.alm_token, req.ticket_id)
    else:
        ticket_data = fetch_ado_ticket(req.alm_url, req.alm_pat, req.ticket_id)
        
    if "error" in ticket_data:
        raise HTTPException(status_code=400, detail=f"ALM Error: {ticket_data['error']}")
        
    llm_config = {
        "provider": req.llm_provider.lower(),
        "model": req.llm_model,
        "api_key": req.llm_api_key,
        "url": req.llm_url
    }
    
    if "mock" in llm_config["provider"]:
        content = {
            "objective": "Mock UI Testing Objective fetching ticket " + ticket_data.get("key", ""),
            "scope": "In-scope: UI Preview logic. Out-of-scope: Actual LLM call.",
            "test_scenarios": ["Verify LLM bypass works", "Verify Docx Generation completes safely"],
            "risks": "No actual AI testing logic generated.",
            "environment": "Localhost Dashboard Environment"
        }
    else:
        content = generate_test_plan_content(ticket_data, llm_config, req.additional_context)
        
    if "error" in content:
        raise HTTPException(status_code=500, detail=f"LLM Error: {content['error']}")

    # Normalize LLM output to prevent frontend rendering crashes
    content = normalize_content(content)

    html_preview = generate_confluence_html(req.ticket_id, content)
    
    # Save MD version for download
    md_content = generate_markdown_content(req.ticket_id, content)
    md_file_name = f"Test_Plan_{req.ticket_id}_{uuid.uuid4().hex[:6]}.md"
    with open(os.path.join(TMP_DIR, md_file_name), "w", encoding="utf-8") as f:
        f.write(md_content)

    return {"status": "success", "data": content, "html": html_preview, "md_file": md_file_name}

@app.post("/api/confluence")
def api_push_confluence(req: PushConfluenceRequest):
    html = generate_confluence_html(req.ticket_id, req.content)
    title = f"Test Plan: {req.ticket_id} ({uuid.uuid4().hex[:4]})"
    res = push_to_confluence(req.alm_url, req.alm_email, req.alm_token, req.space_key, title, html)
    if res.get("status") == "success":
        return res
    raise HTTPException(status_code=500, detail=res.get("detail"))

@app.get("/api/download/{file_name}")
def download_file(file_name: str):
    file_path = os.path.join(TMP_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    if file_name.endswith('.md'):
        media_type = 'text/markdown'
    return FileResponse(path=file_path, filename=file_name, media_type=media_type)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
