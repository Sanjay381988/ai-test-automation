import requests
from jira import JIRA

def fetch_jira_ticket(url: str, email: str, api_token: str, ticket_id: str) -> dict:
    try:
        jira_options = {'server': url}
        jira = JIRA(options=jira_options, basic_auth=(email, api_token))
        issue = jira.issue(ticket_id)
        return {
            "id": issue.key,
            "title": issue.fields.summary,
            "description": issue.fields.description,
        }
    except Exception as e:
        return {"error": str(e)}

def fetch_ado_ticket(url: str, pat: str, ticket_id: str) -> dict:
    try:
        api_url = f"{url.rstrip('/')}/_apis/wit/workitems/{ticket_id}?api-version=7.0"
        auth = ('', pat)
        resp = requests.get(api_url, auth=auth, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            fields = data.get("fields", {})
            return {
                "id": str(data.get("id")),
                "title": fields.get("System.Title", ""),
                "description": fields.get("System.Description", ""),
            }
        else:
            return {"error": f"HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"error": str(e)}
