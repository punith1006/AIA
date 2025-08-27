import json
from google.adk.agents import SequentialAgent, LlmAgent
from google.adk.models import Gemini
from google.genai import types as genai_types
from google.adk.agents.callback_context import CallbackContext

from .tools.mongoupload import update_project_report, create_blank_project
from .sub_agents.client_org_research import organizational_intelligence_agent
from .config import config
# from .output_html import RES

# ----------------------------------------------------------------------
# Storage Callback Functions
# ----------------------------------------------------------------------
def store_organizational_report(callback_context: CallbackContext):
    """Store organizational intelligence report after organizational_intelligence_agent completes"""
    try:
        client_id = callback_context.state.get('client_id')
        client_id = client_id.replace('"','')
        org_report = callback_context.state.get('organizational_intelligence_agent')
        # org_report_html = RES
        org_report_html_inline = callback_context.state.get('org_html')
        print("-"*100)
        print(org_report_html_inline)
        print("-"*100)
        if client_id and org_report:
            update_project_report(
                client_id=client_id, 
                report_raw=org_report,
                report_html=org_report_html_inline,
                report_type="client_org_research"
            )
            print(f"Organizational intelligence report stored successfully for client {client_id}")
        else:
            print(f"Failed to store org report - client_id: {client_id}, report exists: {bool(org_report)}")
    except Exception as e:
        print(f"Error storing organizational intelligence report: {e}")

def extract_client_id(callback_context: CallbackContext):
    """Extract and store client_id from initial input for use by storage callbacks"""
    try:
        # Get the original input and extract client_id
        input_data = callback_context.input_data
        if isinstance(input_data, dict) and 'client_id' in input_data:
            callback_context.state['client_id'] = input_data['client_id']
        elif isinstance(input_data, str):
            # Try to parse as JSON if it's a string
            try:
                parsed = json.loads(input_data)
                if 'client_id' in parsed:
                    callback_context.state['client_id'] = parsed['client_id']
            except:
                # If not JSON, try to extract client_id from text
                # This is a fallback - adjust based on your input format
                pass
        
        print(f"Client ID extracted: {callback_context.state.get('client_id')}")
    except Exception as e:
        print(f"Error extracting client_id: {e}")

# ----------------------------------------------------------------------
# Ensure output_key is consistent for organizational intelligence agent
# ----------------------------------------------------------------------
organizational_intelligence_agent.output_key = "organizational_intelligence_agent"

# Add after-agent callback for storage
organizational_intelligence_agent.after_agent_callback = [store_organizational_report]

# ----------------------------------------------------------------------
# Input Analyzer (simplified - just extracts client_id)
# ----------------------------------------------------------------------
input_analyzer = LlmAgent(
    name="input_analyzer",
    model = config.worker_model,
    description="Analyzes user input and extracts client information.",
    instruction="""
        Analyze the user input and extract any relevant information for the organizational intelligence pipeline.
        
        Output ONLY a JSON object:
        {
            "processed": true,
            "input_summary": "Brief summary of the user request"
        }
    """,
    output_key="input_analysis",
    after_agent_callback=[extract_client_id]
)

# ----------------------------------------------------------------------
# Prompt Builder
# ----------------------------------------------------------------------
org_prompt_builder = LlmAgent(
    name="org_prompt_builder",
    model = config.worker_model,
    description="Generates JSON input for organizational_intelligence_agent using only user input.",
    instruction="""
        Based solely on the user input, create a JSON object for organizational intelligence research.
        
        Output ONLY a valid JSON object in the following format. Do not include any extra text or commentary.
        {
            "companies": [
                {
                    "name": "Company Name",
                    "ticker_symbol": "TICK",
                    "industry": "Industry mentioned or inferred from user input",
                    "alternate_name": "Alternative company name if applicable",
                    "website": "company website if known"
                }
            ],
            "products": [
                {
                    "product_or_service": "Product name from user input",
                    "product_type": "Product category inferred from user input",
                    "product_link": ""
                }
            ]
        }
        
        Extract all company and product information directly from the user input.
        Infer industry and product categories based on what the user has described.
    """,
    output_key="org_agent_input"
)

# ----------------------------------------------------------------------
# Project Creator Agent (modified to work with client_id)
# ----------------------------------------------------------------------
project_creator = LlmAgent(
    name="project_creator",
    model = config.worker_model,
    description="Creates a blank MongoDB project document using the provided client ID.",
    instruction="""
        You will receive input that contains a client_id. Extract the client_id and use the create_blank_project tool to create a new blank project document in MongoDB.
        
        After successfully creating the project, respond with just the client_id as a string and nothing else.
    """,
    tools=[create_blank_project],
    output_key="client_id"
)

# ----------------------------------------------------------------------
# Simplified Organizational Intelligence Agent
# ----------------------------------------------------------------------
organizational_only_agent = SequentialAgent(
    name="organizational_only_agent",
    description="""
        Runs a simplified organizational intelligence analysis pipeline with automatic storage:
        
        1. Analyze user input and extract client information
        2. Create blank project document in MongoDB using client_id
        3. Organizational Intelligence Research → Auto-stored to client_org_research via callback
        
        The organizational intelligence agent has an after_agent_callback that automatically stores 
        its report to MongoDB using the client_id extracted from the initial input.
    """,
    sub_agents=[
        input_analyzer,                         # Analyze input + extract client_id
        project_creator,                        # Create blank project in MongoDB
        org_prompt_builder,                     # Build org prompt  
        organizational_intelligence_agent,      # Execute org intelligence + auto-store
    ]
)

root_agent = organizational_only_agent