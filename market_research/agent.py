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
# Ensure output_key is consistent for all imported sub-agents
# ----------------------------------------------------------------------
market_intelligence_agent.output_key = "market_intelligence_agent"
segmentation_intelligence_agent.output_key = "segmentation_intelligence_agent"
organizational_intelligence_agent.output_key = "organizational_intelligence_agent"
sales_intelligence_agent.output_key = "sales_intelligence_agent"
prospect_researcher.output_key = "prospect_researcher"

# ----------------------------------------------------------------------
# User Input Analyzer
# ----------------------------------------------------------------------
user_input_analyzer = LlmAgent(
    name="user_input_analyzer",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=3, attempts=3)
    ),
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
    output_key="user_analysis"
)

# ----------------------------------------------------------------------
# Initial project creation agent
# ----------------------------------------------------------------------
project_creator = LlmAgent(
    name="project_creator",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=3, attempts=3)
    ),
    description="Creates a blank MongoDB project document using the provided project ID.",
    instruction="""
        You will receive input that contains a project_id. Extract the project_id and use the create_blank_project tool to create a new blank project document in MongoDB.
        
        After successfully creating the project, respond with: "Blank project created successfully with ID: [project_id]"
    """,
    tools=[create_blank_project],
    output_key="project_created"
)

# ----------------------------------------------------------------------
# Prompt Builders
# ----------------------------------------------------------------------
market_prompt_builder = LlmAgent(
    name="market_prompt_builder",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=3, attempts=3)
    ),
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
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=3, attempts=3)
    ),
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
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=3, attempts=3)
    ),
    description="Generates JSON input for organizational_intelligence_agent using user input and previous reports.",
    instruction="""
        Using the user input, market intelligence report, and segmentation report, create a JSON object for organizational intelligence research.
        
        Market Intelligence Report: {market_intelligence_agent}
        Segmentation Report: {segmentation_intelligence_agent}
        
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
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=3, attempts=3)
    ),
    description="Conditionally generates JSON input for sales_intelligence_agent or passes through empty result.",
    instruction="""
        Check the user analysis: {user_analysis}
        
        If the user_analysis shows "needs_sales_intelligence": true, then create a JSON object for sales intelligence research using the user input and previous reports.
        
        If "needs_sales_intelligence": false, output exactly: {{"skip_sales": true}}
        
        When creating sales intelligence input (needs_sales_intelligence is true):
        
        User Analysis: {user_analysis}
        Market Intelligence Report: {market_intelligence_agent}
        Segmentation Report: {segmentation_intelligence_agent}
        Organizational Report: {organizational_intelligence_agent}
        
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
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=3, attempts=3)
    ),
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
    output_key="sales_intelligence_agent"
)

conditional_sales_storage_agent = LlmAgent(
    name="conditional_sales_storage_agent",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=3, attempts=3)
    ),
    description="Conditionally stores sales intelligence report to MongoDB or skips storage.",
    instruction="""
        Check the sales intelligence report: {sales_intelligence_agent}
        
        If the report contains "skipped": true, then respond with: "Sales intelligence skipped - no storage needed"
        
        Otherwise, store the sales intelligence report to MongoDB:
        - Use the project_id from the initial input
        - Use the sales intelligence report content  
        - Use report_type: "target_org_research"
        
        After storing, respond with: "Sales intelligence report stored successfully"
    """,
    tools=[update_project_report],
    output_key="sales_stored"
)

# ----------------------------------------------------------------------
# Modified Prospect Research (handles optional sales intelligence)
# ----------------------------------------------------------------------
prospect_prompt_builder = LlmAgent(
    name="prospect_prompt_builder",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=3, attempts=3)
    ),
    description="Generates JSON input for prospect_researcher using all available reports.",
    instruction="""
        Using the user input and all available intelligence reports, create a JSON object for prospect research.
        
        User Analysis: {user_analysis}
        Market Intelligence Report: {market_intelligence_agent}
        Segmentation Report: {segmentation_intelligence_agent}
        Organizational Report: {organizational_intelligence_agent}
        Sales Intelligence Report: {sales_intelligence_agent}
        
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
# Storage Agents (unchanged)
# ----------------------------------------------------------------------
market_storage_agent = LlmAgent(
    name="market_storage_agent",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=3, attempts=3)
    ),
    description="Stores market intelligence report to MongoDB",
    instruction="""
        Store the market intelligence report to MongoDB.
        
        Use the project_id from the initial input and the market intelligence report: {market_intelligence_agent}
        
        Use the update_project_report tool with:
        - project_id: the ID from user input
        - report: the market intelligence report content
        - report_type: "market_context"
        
        After storing, respond with: "Market intelligence report stored successfully"
    """,
    tools=[update_project_report],
    output_key="market_stored"
)

segmentation_storage_agent = LlmAgent(
    name="segmentation_storage_agent",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=3, attempts=3)
    ),
    description="Stores segmentation intelligence report to MongoDB",
    instruction="""
        Store the segmentation intelligence report to MongoDB.
        
        Use the project_id from the initial input and the segmentation report: {segmentation_intelligence_agent}
        
        Use the update_project_report tool with:
        - project_id: the ID from user input
        - report: the segmentation intelligence report content  
        - report_type: "market_segment"
        
        After storing, respond with: "Segmentation report stored successfully"
    """,
    tools=[update_project_report],
    output_key="segmentation_stored"
)

org_storage_agent = LlmAgent(
    name="org_storage_agent",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=3, attempts=3)
    ),
    description="Stores organizational intelligence report to MongoDB",
    instruction="""
        Store the organizational intelligence report to MongoDB.
        
        Use the project_id from the initial input and the organizational report: {organizational_intelligence_agent}
        
        Use the update_project_report tool with:
        - project_id: the ID from user input
        - report: the organizational intelligence report content
        - report_type: "client_org_research"
        
        After storing, respond with: "Organizational intelligence report stored successfully"
    """,
    tools=[update_project_report],
    output_key="org_stored"
)

prospect_storage_agent = LlmAgent(
    name="prospect_storage_agent",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=3, attempts=3)
    ),
    description="Stores prospect research report to MongoDB",
    instruction="""
        Store the prospect research report to MongoDB.
        
        Use the project_id from the initial input and the prospect research report: {prospect_researcher}
        
        Use the update_project_report tool with:
        - project_id: the ID from user input
        - report: the prospect research report content
        - report_type: "prospect_research"
        
        After storing, respond with: "Prospect research report stored successfully"
    """,
    tools=[update_project_report],
    output_key="prospect_stored"
)

# ----------------------------------------------------------------------
# Working Sequential Agent with Conditional Logic
# ----------------------------------------------------------------------
comprehensive_intelligence_chancellor = SequentialAgent(
    name="comprehensive_intelligence_chancellor",
    description="""
        Runs a comprehensive intelligence analysis pipeline with conditional sales intelligence:
        
        1. Analyze user input for specific target organizations
        2. Create blank project document in MongoDB
        3. Market Intelligence Analysis → Store to market_context
        4. Market Segmentation Analysis → Store to market_segment  
        5. Organizational Intelligence Research → Store to client_org_research
        6. [CONDITIONAL] Sales Intelligence Research → Store to target_org_research
           - Only executes if user specified particular organizations (e.g., "target Microsoft and Google")
           - Skips if user only mentioned general categories (e.g., "target tech companies")
        7. Prospect Research → Store to prospect_research (adapts based on whether sales intelligence ran)
        
        The conditional logic is implemented through agents that check previous outputs and decide whether to execute or skip their functionality.
    """,
    sub_agents=[
        user_input_analyzer,                    # Analyze input for specific organizations
        project_creator,                        # Create project
        market_prompt_builder,                  # Build market prompt
        market_intelligence_agent,              # Execute market intelligence
        market_storage_agent,                   # Store market report
        segmentation_prompt_builder,            # Build segmentation prompt
        segmentation_intelligence_agent,        # Execute segmentation
        segmentation_storage_agent,             # Store segmentation report
        org_prompt_builder,                     # Build org prompt
        organizational_intelligence_agent,      # Execute org intelligence
        org_storage_agent,                      # Store org report
        conditional_sales_prompt_builder,       # Conditionally build sales prompt OR skip
        conditional_sales_intelligence_agent,   # Conditionally execute sales intelligence OR skip
        conditional_sales_storage_agent,        # Conditionally store sales report OR skip
        prospect_prompt_builder,                # Build prospect prompt (handles optional sales data)
        prospect_researcher,                    # Execute prospect research
        prospect_storage_agent                  # Store prospect report
    ]
)

root_agent = comprehensive_intelligence_chancellor