import json
from google.adk.agents import SequentialAgent, LlmAgent
from google.adk.models import Gemini
from google.genai import types as genai_types
from google.adk.agents.callback_context import CallbackContext

from .tools.mongoupload import update_project_report, create_blank_project
from .sub_agents.segmentation import segmentation_intelligence_agent
from .sub_agents.client_org_research import organizational_intelligence_agent
from .sub_agents.prospect_research import prospect_researcher
from .config import config

# ----------------------------------------------------------------------
# Storage Callback Functions
# ----------------------------------------------------------------------
def store_segmentation_report(callback_context: CallbackContext):
    """Store segmentation report after segmentation_intelligence_agent completes"""
    try:
        project_id = callback_context.state.get('project_id')
        project_id = project_id.replace('"','')
        segmentation_report = callback_context.state.get('segmentation_intelligence_agent')
        
        if project_id and segmentation_report:
            update_project_report(
                project_id=project_id,
                report=segmentation_report,
                report_type="market_segment"
            )
            print(f"Segmentation report stored successfully for project {project_id}")
        else:
            print(f"Failed to store segmentation report - project_id: {project_id}, report exists: {bool(segmentation_report)}")
    except Exception as e:
        print(f"Error storing segmentation report: {e}")

def store_organizational_report(callback_context: CallbackContext):
    """Store organizational intelligence report after organizational_intelligence_agent completes"""
    try:
        project_id = callback_context.state.get('project_id')
        project_id = project_id.replace('"','')
        org_report = callback_context.state.get('organizational_intelligence_agent')
        
        if project_id and org_report:
            update_project_report(
                project_id=project_id,
                report=org_report,
                report_type="client_org_research"
            )
            print(f"Organizational intelligence report stored successfully for project {project_id}")
        else:
            print(f"Failed to store org report - project_id: {project_id}, report exists: {bool(org_report)}")
    except Exception as e:
        print(f"Error storing organizational intelligence report: {e}")

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
            print(f"Prospect research report stored successfully for project {project_id}")
        else:
            print(f"Failed to store prospect report - project_id: {project_id}, report exists: {bool(prospect_report)}")
    except Exception as e:
        print(f"Error storing prospect research report: {e}")

def extract_project_id(callback_context: CallbackContext):
    """Extract and store project_id from initial input for use by storage callbacks"""
    try:
        # Get the original input and extract project_id
        input_data = callback_context.input_data
        if isinstance(input_data, dict) and 'project_id' in input_data:
            callback_context.state['project_id'] = input_data['project_id']
        elif isinstance(input_data, str):
            # Try to parse as JSON if it's a string
            try:
                parsed = json.loads(input_data)
                if 'project_id' in parsed:
                    callback_context.state['project_id'] = parsed['project_id']
            except:
                # If not JSON, try to extract project_id from text
                # This is a fallback - adjust based on your input format
                pass
        
        print(f"Project ID extracted: {callback_context.state.get('project_id')}")
    except Exception as e:
        print(f"Error extracting project_id: {e}")

# ----------------------------------------------------------------------
# Ensure output_key is consistent for all imported sub-agents
# ----------------------------------------------------------------------
segmentation_intelligence_agent.output_key = "segmentation_intelligence_agent"
organizational_intelligence_agent.output_key = "organizational_intelligence_agent"
prospect_researcher.output_key = "prospect_researcher"

# Add after-agent callbacks for storage
segmentation_intelligence_agent.after_agent_callback = [store_segmentation_report]
organizational_intelligence_agent.after_agent_callback = [store_organizational_report]
prospect_researcher.after_agent_callback = [store_prospect_report]

# ----------------------------------------------------------------------
# Input Analyzer (simplified - just extracts project_id)
# ----------------------------------------------------------------------
input_analyzer = LlmAgent(
    name="input_analyzer",
    model = config.worker_model,
    description="Analyzes user input and extracts project information.",
    instruction="""
        Analyze the user input and extract any relevant information for the intelligence pipeline.
        
        Output ONLY a JSON object:
        {
            "processed": true,
            "input_summary": "Brief summary of the user request"
        }
    """,
    output_key="input_analysis",
    after_agent_callback=[extract_project_id]
)

# ----------------------------------------------------------------------
# Prompt Builders
# ----------------------------------------------------------------------
segmentation_prompt_builder = LlmAgent(
    name="segmentation_prompt_builder",
    model = config.worker_model,
    description="Generates JSON input for segmentation_intelligence_agent from user input.",
    instruction="""
        Based on the user input, create a JSON object for market segmentation analysis.
        
        Output ONLY a valid JSON object in the following format. Do not include any extra text or commentary.
        {
            "product_name": "Your Product Name Here",
            "product_description": "A detailed description of your product or service and what it does.",
            "industry_market": "The industry or market in which your product operates",
            "current_understanding": "Any existing insights about target demographics, market challenges, or strategic context from the user input."
        }
        
        Extract the product/service information from the user input.
        Be specific and detailed in the product_description based on user input.
    """,
    output_key="segmentation_agent_input"
)

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

prospect_prompt_builder = LlmAgent(
    name="prospect_prompt_builder",
    model = config.worker_model,
    description="Generates JSON input for prospect_researcher using segmentation and organizational reports.",
    instruction="""
        Using the user input, segmentation report, and organizational report, create a JSON object for prospect research.
        
        Segmentation Report: {segmentation_intelligence_agent}
        Organizational Report: {organizational_intelligence_agent}
        
        Output ONLY a valid JSON object:
        {
            "products_services": [
                {
                    "name": "Product name from segmentation analysis",
                    "description": "Comprehensive description incorporating segmentation and organizational insights"
                }
            ],
            "company_information": "Background about the company based on organizational intelligence",
            "known_competitors": ["List of competitors from organizational intelligence"],
            "target_context": "Additional context from segmentation and organizational analysis"
        }
        
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

# ----------------------------------------------------------------------
# Simplified Sequential Agent
# ----------------------------------------------------------------------
simplified_intelligence_agent = SequentialAgent(
    name="simplified_intelligence_agent",
    description="""
        Runs a simplified intelligence analysis pipeline with automatic storage:
        
        1. Analyze user input and extract project information
        2. Create blank project document in MongoDB
        3. Market Segmentation Analysis → Auto-stored to market_segment via callback
        4. Organizational Intelligence Research → Auto-stored to client_org_research via callback
        5. Prospect Research → Auto-stored to prospect_research via callback
        
        Each research agent has an after_agent_callback that automatically stores its report to MongoDB
        using the project_id extracted from the initial input.
    """,
    sub_agents=[
        input_analyzer,                         # Analyze input + extract project_id
        project_creator,                        # Create blank project in MongoDB
        org_prompt_builder,                     # Build org prompt  
        organizational_intelligence_agent,      # Execute org intelligence + auto-store
        segmentation_prompt_builder,            # Build segmentation prompt
        segmentation_intelligence_agent,        # Execute segmentation + auto-store
        prospect_prompt_builder,                # Build prospect prompt
        prospect_researcher,                    # Execute prospect research + auto-store
    ]
)

root_agent = simplified_intelligence_agent