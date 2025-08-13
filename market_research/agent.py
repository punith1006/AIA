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
# Initial project creation agent
# ----------------------------------------------------------------------
project_creator = LlmAgent(
    name="project_creator",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=1, attempts=3)
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
        retry_options=genai_types.HttpRetryOptions(initial_delay=1, attempts=3)
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
        retry_options=genai_types.HttpRetryOptions(initial_delay=1, attempts=3)
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
        retry_options=genai_types.HttpRetryOptions(initial_delay=1, attempts=3)
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

sales_prompt_builder = LlmAgent(
    name="sales_prompt_builder",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=1, attempts=3)
    ),
    description="Generates JSON input for sales_intelligence_agent using user input and previous reports.",
    instruction="""
        Using the user input and all previous intelligence reports (market, segmentation, organizational), create a JSON object for sales intelligence research.
        
        Market Intelligence Report: {market_intelligence_agent}
        Segmentation Report: {segmentation_intelligence_agent}
        Organizational Report: {organizational_intelligence_agent}
        
        Output ONLY a valid JSON object in the following format. Do not include any extra text or commentary.
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
                    "name": "Organization name from organizational intelligence report",
                    "industry": "Industry from market analysis",
                    "context": "Context from segmentation and organizational reports about why this organization is a good target"
                }
            ],
            "research_objectives": "Specific research objectives based on the market context, segmentation insights, and organizational intelligence findings. Focus on understanding adoption patterns, decision-makers, and competitive positioning."
        }
        
        Leverage insights from all previous reports to identify the most promising target organizations and define focused research objectives.
        The research objectives should be specific and actionable based on the intelligence gathered so far.
    """,
    output_key="sales_agent_input"
)

prospect_prompt_builder = LlmAgent(
    name="prospect_prompt_builder",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=1, attempts=3)
    ),
    description="Generates JSON input for prospect_researcher using user input and all previous reports.",
    instruction="""
        Using the user input and all previous intelligence reports (market, segmentation, organizational, sales), create a JSON object for prospect research.
        
        Market Intelligence Report: {market_intelligence_agent}
        Segmentation Report: {segmentation_intelligence_agent}
        Organizational Report: {organizational_intelligence_agent}
        Sales Intelligence Report: {sales_intelligence_agent}
        
        Output ONLY a valid JSON object in the following format. Do not include any extra text or commentary.
        {
            "products_services": [
                {
                    "name": "Product name from previous analysis",
                    "description": "Comprehensive description incorporating insights from market analysis, segmentation findings, and organizational intelligence about features, benefits, use cases, and target market."
                }
            ],
            "company_information": "Background about the company based on organizational intelligence, market positioning from market analysis, and competitive context from all previous reports.",
            "known_competitors": ["List of competitors identified through organizational intelligence and market analysis"]
        }
        
        Synthesize all previous intelligence to create the most comprehensive and accurate prospect research input.
        The product descriptions should reflect the market context, target segments, and competitive landscape identified in earlier reports.
        Company information should incorporate organizational insights and market positioning analysis.
        Known competitors should be based on findings from the organizational intelligence report.
    """,
    output_key="prospect_agent_input"
)

# ----------------------------------------------------------------------
# Storage Agents
# ----------------------------------------------------------------------
market_storage_agent = LlmAgent(
    name="market_storage_agent",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=1, attempts=3)
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
        retry_options=genai_types.HttpRetryOptions(initial_delay=1, attempts=3)
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
        retry_options=genai_types.HttpRetryOptions(initial_delay=1, attempts=3)
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

sales_storage_agent = LlmAgent(
    name="sales_storage_agent",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=1, attempts=3)
    ),
    description="Stores sales intelligence report to MongoDB",
    instruction="""
        Store the sales intelligence report to MongoDB.
        
        Use the project_id from the initial input and the sales intelligence report: {sales_intelligence_agent}
        
        Use the update_project_report tool with:
        - project_id: the ID from user input
        - report: the sales intelligence report content
        - report_type: "target_org_research"
        
        After storing, respond with: "Sales intelligence report stored successfully"
    """,
    tools=[update_project_report],
    output_key="sales_stored"
)

prospect_storage_agent = LlmAgent(
    name="prospect_storage_agent",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(initial_delay=1, attempts=3)
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
# Final Sequential Agent
# ----------------------------------------------------------------------
comprehensive_intelligence_chancellor = SequentialAgent(
    name="comprehensive_intelligence_chancellor",
    description="""
        Runs a comprehensive intelligence analysis pipeline with MongoDB storage:
        
        1. Creates blank project document in MongoDB
        2. Market Intelligence Analysis → Store to market_context
        3. Market Segmentation Analysis → Store to market_segment
        4. Organizational Intelligence Research → Store to client_org_research
        5. Sales Intelligence Research → Store to target_org_research
        6. Prospect Research → Store to prospect_research
        
        Each step builds on the insights from previous steps to avoid hallucination and ensure coherent analysis.
        All reports are automatically stored in MongoDB after generation.
    """,
    sub_agents=[
        project_creator,
        market_prompt_builder,
        market_intelligence_agent,
        market_storage_agent,
        segmentation_prompt_builder,
        segmentation_intelligence_agent,
        segmentation_storage_agent,
        org_prompt_builder,
        organizational_intelligence_agent,
        org_storage_agent,
        sales_prompt_builder,
        sales_intelligence_agent,
        sales_storage_agent,
        prospect_prompt_builder,
        prospect_researcher,
        prospect_storage_agent
    ]
)

root_agent = comprehensive_intelligence_chancellor
