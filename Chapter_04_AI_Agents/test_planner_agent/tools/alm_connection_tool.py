import requests
from jira import JIRA

def test_jira_connection(url: str, email: str, api_token: str) -> bool:
    try:
        jira_options = {'server': url}
        jira = JIRA(options=jira_options, basic_auth=(email, api_token))
        # ping to test
        jira.myself()
        return True
    except Exception as e:
        print(f"Jira connection failed: {e}")
        return False

def test_ado_connection(url: str, pat: str) -> bool:
    # Minimal ADO ping test using PAT logic
    # URL expected to be something like https://dev.azure.com/{organization}
    try:
        api_url = f"{url.rstrip('/')}/_apis/projects?api-version=7.0"
        auth = ('', pat) # ADO usually uses PAT as basic auth password with any username
        resp = requests.get(api_url, auth=auth, timeout=5)
        if resp.status_code in [200, 203]:
            return True
        else:
            print(f"ADO connection failed: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"ADO connection failed: {e}")
        return False
