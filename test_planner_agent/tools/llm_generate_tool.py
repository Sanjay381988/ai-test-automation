import os
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_community.chat_models import ChatOllama

def generate_test_plan_content(ticket_data: dict, llm_config: dict, additional_context: str = "") -> dict:
    """
    Generates structured test plan content based on the ticket data using the specified LLM.
    """
    provider = llm_config.get("provider", "groq")
    model_name = llm_config.get("model", "llama3-8b-8192")
    api_key = llm_config.get("api_key", "")
    
    if provider == "groq":
        llm = ChatGroq(groq_api_key=api_key, model_name=model_name)
    elif provider == "ollama":
        # local Ollama instance
        base_url = llm_config.get("url", "http://localhost:11434")
        llm = ChatOllama(model=model_name, base_url=base_url)
    else:
        return {"error": "Invalid LLM provider specified."}

    prompt = PromptTemplate.from_template(
        "You are an expert QA Test Planner.\n"
        "Generate a professional test plan for the following ALM ticket.\n\n"
        "Ticket ID: {ticket_id}\n"
        "Title: {title}\n"
        "Description: {description}\n"
        "Additional Context: {additional_context}\n\n"
        "Please provide the output in a structured JSON format with the following keys exactly: \n"
        "- 'objective': A clear objective of the testing.\n"
        "- 'scope': What is in-scope and out-of-scope.\n"
        "- 'test_scenarios': A bulleted list of 5-10 high level test scenarios.\n"
        "- 'risks': Any potential risks associated with this feature.\n"
        "- 'environment': The recommended testing environments.\n"
        "Return ONLY valid JSON.\n"
        "JSON:\n"
    )
    
    chain = prompt | llm
    
    try:
        response = chain.invoke({
            "ticket_id": ticket_data.get("id", "Unknown"),
            "title": ticket_data.get("title", ""),
            "description": ticket_data.get("description", ""),
            "additional_context": additional_context
        })
        
        # Parse the JSON string from response
        import json
        content = response.content
        # sometimes LLMs wrap json in ```json ... ```
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        generated_data = json.loads(content)
        return generated_data
        
    except Exception as e:
        return {"error": f"LLM Generation failed: {str(e)}"}
