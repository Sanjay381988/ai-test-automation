# Project Constitution

## Data Schemas

```json
{
  "ConnectionConfig": {
    "almProvider": "jira | ado | xray",
    "almUrl": "string",
    "almCredentials": "string",
    "llmProvider": "ollama | groq",
    "llmModel": "string",
    "llmApiKey": "string (optional if local)"
  },
  "GenerationRequest": {
    "ticketId": "string",
    "additionalContext": "string (optional)"
  },
  "TicketData": {
    "id": "string",
    "title": "string",
    "description": "string",
    "acceptanceCriteria": "string"
  },
  "TestPlanPayload": {
    "status": "success | error",
    "filePath": "string (path to generated .docx)",
    "message": "string"
  }
}
```

## Behavioral Rules
- Strict adherence to B.L.A.S.T protocol and A.N.T. 3-layer architecture.
- Deterministic business logic.

## Architectural Invariants
- Use `architecture/` for SOPs.
- Use `tools/` for python scripts.
- Use `.tmp/` for intermediate file operations.
