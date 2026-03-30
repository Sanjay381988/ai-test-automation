# Layer 1: Architecture SOP

## 1. Goal
Generate a docx Test Plan dynamically based on Jira/ADO tickets using user-supplied API connections to local/remote LLMs.

## 2. Inputs
- Connection Options (ALM URL, Token, LLM Provider, API Key)
- Ticket ID (e.g. `PROJ-123`)
- Additional Context (optional rules)

## 3. Tool Logic Execution Flow (Navigation)
1. **Link Verification (`app.py`):** User presses "Test Connection". App calls `tools.alm_connection_tool` or `tools.llm_connection_tool`.
2. **Fetch Data (`tools/alm_fetch_tool.py`):** App calls fetch tool with ALM credentials and API. Retrieves JSON Ticket Data (Title, Description, AC).
3. **Generate Markdown Content (`tools/llm_generate_tool.py`):** Passes Ticket Data + Context into LLM to generate sections for the Test Plan loosely based on docx template markers.
4. **Build Document (`tools/docx_writer_tool.py`):** Maps the Markdown content logically into a copied variation of `Test Plan - Template.docx` stored in `.tmp/`.
5. **Payload Delivery (`app.py`):** Presents the `.docx` file as a download in UI.
