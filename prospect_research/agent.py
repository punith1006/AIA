import json
from google.adk.agents import SequentialAgent, LlmAgent
from google.adk.models import Gemini
from google.genai import types as genai_types
from google.adk.agents.callback_context import CallbackContext
from .prospect_agent import prospect_researcher
from .prospect_agent import market_report, segmentation_report
from .config import config
from .tools.mongoupload import update_project_report, create_blank_project
# from .output_html import RES

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
        
def store_prospect_report(callback_context: CallbackContext):
    """Store prospect research report after prospect_researcher completes"""
    try:
        project_id = callback_context.state.get('project_id')
        project_id = project_id.replace('"','')
        prospect_report = callback_context.state.get('prospect_researcher')
        
        if project_id and prospect_report:
            update_project_report(
                project_id=project_id,
                report=prospect_report,
                report_type="prospect_research"
            )
            
            print("###################################################################################")
            print("###################################################################################")
            print(f"Prospect research report stored successfully for project {project_id}")
            print("###################################################################################")
            print("###################################################################################")
        else:
            print(f"Failed to store prospect report - project_id: {project_id}, report exists: {bool(prospect_report)}")
    except Exception as e:
        print(f"Error storing prospect research report: {e}")

# ----------------------------------------------------------------------
# Input Analyzer (simplified - just extracts client_id)
# ----------------------------------------------------------------------
input_analyzer = LlmAgent(
    name="input_analyzer",
    model = config.worker_model,
    description="Analyzes user input and extracts client information.",
    instruction="""
        Analyze the user input and extract any relevant information for the propsect intelligence pipeline.
        
        Output ONLY a JSON object:
        {
            "processed": true,
            "input_summary": "Brief summary of the user request"
        }
    """,
    output_key="input_analysis",
    after_agent_callback=[extract_client_id]
)

prospect_prompt_builder = LlmAgent(
    name="prospect_prompt_builder",
    model=config.worker_model,
    description="Generates JSON input for prospect_researcher using segmentation and organizational reports.",
    instruction=f"""
        Using the user input, segmentation report, and market report, create a JSON object for prospect research.
        market report : {market_report}
        Segmentation Report: {segmentation_report} 
        
        Output ONLY a valid JSON object:
        {{
            "products_services": [
                {{
                    "name": "Product name from segmentation analysis",
                    "description": "Comprehensive description incorporating segmentation and organizational insights"
                }}
            ],
            "company_information": "Background about the company based on organizational intelligence",
            "known_competitors": ["List of competitors from organizational intelligence"],
            "target_context": "Additional context from segmentation and organizational analysis"
        }}
        
        Incorporate insights from both the segmentation and organizational intelligence reports.
    """,
    output_key="prospect_agent_input"
)

# ----------------------------------------------------------------------
# Project Creator Agent
# ----------------------------------------------------------------------
project_creator = LlmAgent(
    name="project_creator",
    model = config.worker_model,
    description="Creates a blank MongoDB project document using the provided project ID.",
    instruction="""
        You will receive input that contains a project_id. Extract the project_id and use the create_blank_project tool to create a new blank project document in MongoDB.
        
        After successfully creating the project, respond with just the project_id as a string and nothing else.
    """,
    tools=[create_blank_project],
    output_key="project_id"
)

prospect_researcher.after_agent_callback = [store_prospect_report]

# ----------------------------------------------------------------------
# Simplified prospect Intelligence Agent
# ----------------------------------------------------------------------
prospect_only_agent = SequentialAgent(
    name="prospect_only_agent",
    description="""
        Runs a simplified organizational intelligence analysis pipeline with automatic storage:
        
        1. Analyze user input and extract client information
        3. Prospect Intelligence Research → JSON filter for apollo search
        
        """,
    sub_agents=[
        input_analyzer,                         # Analyze input + extract client_id
        project_creator,
        prospect_prompt_builder,
        prospect_researcher
    ]
)

root_agent = prospect_only_agent