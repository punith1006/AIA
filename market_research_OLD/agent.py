import json
from google.adk.agents import SequentialAgent, LlmAgent
from google.adk.models import Gemini
from google.genai import types as genai_types
from google.adk.agents.callback_context import CallbackContext

from .tools.mongoupload import update_project_report, create_blank_project
from .sub_agents.market_context import market_intelligence_agent
from .sub_agents.segmentation import segmentation_intelligence_agent
from .sub_agents.client_org_research import organizational_intelligence_agent
from .sub_agents.target_org_research import sales_intelligence_agent
from .sub_agents.prospect_research import prospect_researcher
from .config import config

# ----------------------------------------------------------------------
# Storage Callback Functions
# ----------------------------------------------------------------------
def store_market_report(callback_context: CallbackContext):
    """Store market intelligence report after market_intelligence_agent completes"""
    try:
        # Get project_id from the original input
        project_id = callback_context.state.get('project_id')
        project_id = project_id.replace('"','')
        # Get the market intelligence report from the agent output
        market_report = callback_context.state.get('market_intelligence_agent')
        
        if project_id and market_report:
            # Store the report
            update_project_report(
                project_id=project_id,
                report=market_report,
                report_type="market_context"
            )
            print(f"Market intelligence report stored successfully for project {project_id}")
        else:
            print(f"Failed to store market report - project_id: {project_id}, report exists: {bool(market_report)}")
    except Exception as e:
        print(f"Error storing market intelligence report: {e}")

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

def store_sales_report(callback_context: CallbackContext):
    """Store sales intelligence report after conditional_sales_intelligence_agent completes (if not skipped)"""
    try:
        project_id = callback_context.state.get('project_id')
        
        project_id = project_id.replace('"','')
        sales_report = callback_context.state.get('sales_intelligence_agent')
        
        if project_id and sales_report:
            # Check if sales intelligence was skipped
            if isinstance(sales_report, dict) and sales_report.get('skipped'):
                print(f"Sales intelligence was skipped - no storage needed for project {project_id}")
                return
                
            update_project_report(
                project_id=project_id,
                report=sales_report,
                report_type="target_org_research"
            )
            print(f"Sales intelligence report stored successfully for project {project_id}")
        else:
            print(f"Failed to store sales report - project_id: {project_id}, report exists: {bool(sales_report)}")
    except Exception as e:
        print(f"Error storing sales intelligence report: {e}")

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
market_intelligence_agent.output_key = "market_intelligence_agent"
segmentation_intelligence_agent.output_key = "segmentation_intelligence_agent"
organizational_intelligence_agent.output_key = "organizational_intelligence_agent"
sales_intelligence_agent.output_key = "sales_intelligence_agent"
prospect_researcher.output_key = "prospect_researcher"

# Add after-agent callbacks for storage
market_intelligence_agent.after_agent_callback = [store_market_report]
segmentation_intelligence_agent.after_agent_callback = [store_segmentation_report]
organizational_intelligence_agent.after_agent_callback = [store_organizational_report]
# Note: sales_intelligence_agent callback will be added to conditional_sales_intelligence_agent
prospect_researcher.after_agent_callback = [store_prospect_report]

# ----------------------------------------------------------------------
# User Input Analyzer
# ----------------------------------------------------------------------
user_input_analyzer = LlmAgent(
    name="user_input_analyzer",
    model = config.worker_model,
    description="Analyzes user input to determine if specific target organizations are mentioned.",
    instruction="""
        Analyze the user input to determine if they have mentioned specific organizations/companies they want to target.
        
        Look for:
        - Direct mentions of target companies (e.g., "we want to target IBM and Oracle")
        - Named organizations they want to sell to
        
        Do NOT consider these as specific organizations:
        - General industry references (e.g., "tech companies", "healthcare organizations")
        - Market segments (e.g., "enterprise customers", "small businesses") 
        - Geographic references (e.g., "companies in Silicon Valley")
        - Company types without names (e.g., "SaaS companies", "manufacturing firms")
        - Size descriptors (e.g., "Fortune 500", "startups", "mid-market")
        
        Output ONLY a JSON object:
        {
            "has_target_organizations": true/false,
            "organizations_mentioned": ["Company1", "Company2"],
            "needs_sales_intelligence": true/false
        }
        
        Set needs_sales_intelligence to true only if has_target_organizations is true.
    """,
    output_key="user_analysis",
    after_agent_callback=[extract_project_id]
)

# ----------------------------------------------------------------------
# Initial project creation agent
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
# Prompt Builders
# ----------------------------------------------------------------------
market_prompt_builder = LlmAgent(
    name="market_prompt_builder",
    model = config.worker_model,
    description="Generates JSON input for market_intelligence_agent from user input.",
    instruction="""
        Based on the user input, extract and structure the information to create a JSON object for market intelligence research.
        Output ONLY a valid JSON object in the following format. Do not include any extra text or commentary.
        {
            "product_or_service": "Your product or service name",
            "target_market_industry": "The industry or sector your product/service operates in",
            "geographic_focus": "Specific regions, countries, or continents (e.g., 'North America', 'Global', 'Europe and Asia')"
        }
        
        If geographic focus is not specified in the user input, default to "Global".
        Extract the most relevant industry based on the product/service description.
    """,
    output_key="market_agent_input"
)

segmentation_prompt_builder = LlmAgent(
    name="segmentation_prompt_builder",
    model = config.worker_model,
    description="Generates JSON input for segmentation_intelligence_agent using user input and market intelligence report.",
    instruction="""
        Using the user input and the market intelligence report from the previous step, create a JSON object for market segmentation analysis.
        
        Market Intelligence Report: {market_intelligence_agent}
        
        Output ONLY a valid JSON object in the following format. Do not include any extra text or commentary.
        {
            "product_name": "Your Product Name Here",
            "product_description": "A detailed description of your product or service and what it does.",
            "industry_market": "The industry or market in which your product operates",
            "current_understanding": "Any existing insights from the market intelligence report about target demographics, market challenges, or strategic context."
        }
        
        Use insights from the market intelligence report to enhance the current_understanding field.
        Be specific and detailed in the product_description based on user input and market context.
    """,
    output_key="segmentation_agent_input"
)

org_prompt_builder = LlmAgent(
    name="org_prompt_builder",
    model = config.worker_model,
    description="Generates JSON input for organizational_intelligence_agent using user input and previous reports.",
    instruction="""
        Using the user input, market intelligence report, create a JSON object for organizational intelligence research.
        Market Intelligence Report: {market_intelligence_agent}
        
        Output ONLY a valid JSON object in the following format. Do not include any extra text or commentary.
        {
            "companies": [
                {
                    "name": "Company Name",
                    "ticker_symbol": "TICK",
                    "industry": "Industry from segmentation report",
                    "alternate_name": "Alternative company name if applicable",
                    "website": "company website if known"
                }
            ],
            "products": [
                {
                    "product_or_service": "Product name from user input",
                    "product_type": "Product category based on segmentation analysis",
                    "product_link": ""
                }
            ]
        }
        
        Use the market and segmentation insights to identify relevant companies and categorize products appropriately.
        Focus on the industry and geographic focus identified in previous reports.
    """,
    output_key="org_agent_input"
)

# ----------------------------------------------------------------------
# CONDITIONAL SALES INTELLIGENCE AGENTS
# ----------------------------------------------------------------------
conditional_sales_prompt_builder = LlmAgent(
    name="conditional_sales_prompt_builder",
    model = config.worker_model,
    description="Conditionally generates JSON input for sales_intelligence_agent or passes through empty result.",
    instruction="""
        Check the user analysis: {user_analysis}
        
        If the user_analysis shows "needs_sales_intelligence": true, then create a JSON object for sales intelligence research using the user input and previous reports.
        
        If "needs_sales_intelligence": false, output exactly: {{"skip_sales": true}}
        
        When creating sales intelligence input (needs_sales_intelligence is true):
        
        User Analysis: {user_analysis}
        Market Intelligence Report: {market_intelligence_agent}
        
        Output a valid JSON object:
        {
            "products": [
                {
                    "name": "Product name from previous reports",
                    "category": "Product category from segmentation analysis",
                    "details": "Enhanced product details from organizational intelligence"
                }
            ],
            "target_organizations": [
                {
                    "name": "Organization name from user_analysis.organizations_mentioned",
                    "industry": "Industry from market analysis",
                    "context": "Context about why this organization is a target"
                }
            ],
            "research_objectives": "Research objectives focused on the specific organizations mentioned by the user"
        }
        
        Use the organizations_mentioned from user_analysis as the primary targets.
    """,
    output_key="sales_agent_input"
)

conditional_sales_intelligence_agent = LlmAgent(
    name="conditional_sales_intelligence_agent",
    model = config.worker_model,
    description="Conditionally executes sales intelligence research or skips if no specific targets identified.",
    instruction="""
        Check the sales_agent_input: {sales_agent_input}
        
        If sales_agent_input contains "skip_sales": true, then output exactly:
        {{"skipped": true, "reason": "No specific target organizations identified in user input"}}
        
        Otherwise, execute sales intelligence research using the provided input and the original sales_intelligence_agent logic.
        
        When executing (not skipping):
        Use the sales_agent_input to conduct detailed sales intelligence research on the specified target organizations.
        Focus on understanding their business needs, decision-making processes, competitive landscape, and how your product/service could address their challenges.
        Provide actionable insights for sales and business development teams.
        
        Analyze each target organization's:
        - Current business challenges and pain points
        - Technology stack and existing solutions
        - Decision-making hierarchy and key stakeholders
        - Budget and procurement processes
        - Recent business developments and strategic initiatives
        - Competitive positioning and market presence
        
        Output a comprehensive sales intelligence report with specific, actionable recommendations for approaching each target organization.
    """,
    output_key="sales_intelligence_agent",
    after_agent_callback=[store_sales_report]
)

# ----------------------------------------------------------------------
# Modified Prospect Research (handles optional sales intelligence)
# ----------------------------------------------------------------------
prospect_prompt_builder = LlmAgent(
    name="prospect_prompt_builder",
    model = config.worker_model,
    description="Generates JSON input for prospect_researcher using all available reports.",
    instruction="""
        Using the user input and all available intelligence reports, create a JSON object for prospect research.
        
        User Analysis: {user_analysis}
        Segmentation Report: {segmentation_intelligence_agent}
        Organizational Report: {organizational_intelligence_agent}
        
        Note: Sales intelligence may be skipped if no specific targets were identified.
        
        Output ONLY a valid JSON object:
        {
            "products_services": [
                {
                    "name": "Product name from previous analysis",
                    "description": "Comprehensive description incorporating all available insights"
                }
            ],
            "company_information": "Background about the company based on available intelligence",
            "known_competitors": ["List of competitors from organizational intelligence"],
            "target_context": "Additional context from sales intelligence if available, or general market context if sales intelligence was skipped"
        }
        
        If sales intelligence was skipped (contains "skipped": true), focus on general market and organizational insights.
        If sales intelligence is available, incorporate those specific target insights.
    """,
    output_key="prospect_agent_input"
)

# ----------------------------------------------------------------------
# Working Sequential Agent with Conditional Logic and Callback Storage
# ----------------------------------------------------------------------
comprehensive_intelligence_chancellor = SequentialAgent(
    name="comprehensive_intelligence_chancellor",
    description="""
        Runs a comprehensive intelligence analysis pipeline with conditional sales intelligence and automatic storage:
        
        1. Analyze user input for specific target organizations
        2. Create blank project document in MongoDB
        3. Market Intelligence Analysis â†’ Auto-stored to market_context via callback
        4. Market Segmentation Analysis â†’ Auto-stored to market_segment via callback
        5. Organizational Intelligence Research â†’ Auto-stored to client_org_research via callback
        6. [CONDITIONAL] Sales Intelligence Research â†’ Auto-stored to target_org_research via callback
           - Only executes if user specified particular organizations (e.g., "target Microsoft and Google")
           - Skips if user only mentioned general categories (e.g., "target tech companies")
        7. Prospect Research â†’ Auto-stored to prospect_research via callback
        
        Each research agent now has an after_agent_callback that automatically stores its report to MongoDB
        using the project_id extracted from the initial input. This ensures consistent storage without
        requiring separate storage agents.
    """,
    sub_agents=[
        user_input_analyzer,                    # Analyze input + extract project_id
        # project_creator,                        # Create project
        market_prompt_builder,                  # Build market prompt
        market_intelligence_agent,              # Execute market intelligence + auto-store
        segmentation_prompt_builder,            # Build segmentation prompt
        segmentation_intelligence_agent,        # Execute segmentation + auto-store
        org_prompt_builder,                     # Build org prompt
        organizational_intelligence_agent,      # Execute org intelligence + auto-store
        conditional_sales_prompt_builder,       # Conditionally build sales prompt OR skip
        conditional_sales_intelligence_agent,   # Conditionally execute sales intelligence + auto-store OR skip
        prospect_prompt_builder,                # Build prospect prompt (handles optional sales data)
        prospect_researcher,                    # Execute prospect research + auto-store
    ]
)

root_agent = comprehensive_intelligence_chancellor