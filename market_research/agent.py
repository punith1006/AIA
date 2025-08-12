# import datetime
# import uuid
# import os
# import json
# from zoneinfo import ZoneInfo
# from typing import Dict, Any, List
# from pymongo import MongoClient
# from google.adk.agents import SequentialAgent, LoopAgent, LlmAgent
# from google.adk.agents.callback_context import CallbackContext
# from google.adk.models import Gemini
# from google.genai import types as genai_types
# from .tools.mongoupload import create_blank_project
# from .tools.mongoupload import update_project_report

# # Import sub-agents
# from .sub_agents.market_context import market_intelligence_agent
# from .sub_agents.segmentation import segmentation_intelligence_agent
# from .sub_agents.target_org_research import sales_intelligence_agent
# from .sub_agents.prospect_research import prospect_researcher
# from .sub_agents.client_org_research import organizational_intelligence_agent

# from .config import config



# client_org_chancellor = LlmAgent(
#     name = "client_org_chancellor",
#     model = Gemini(
#         model=config.worker_model,
#         retry_options=genai_types.HttpRetryOptions(
#         initial_delay=1,
#         attempts=3
#         )
#     ),
#     description = "You are responsible for creating the ideal prompt for the organizational_intelligence_agent and then storing the output in mongodb.",
#     instruction = """
#                     Based on the information given to you, you should run organizational_intelligence_agent using information in the following format:
#                         {
#                         "companies": [
#                             {
#                             "name": "Company Name 1",
#                             "ticker_symbol": "CMN1",
#                             "industry": "Software",
#                             "alternate name": "Company Name 2",
#                             "website": "www.company2.com"
#                             }
#                         ],
#                         "products": [
#                                 {
#                                 "product_or_service": "Enterprise AI Solutions",
#                                 "product_type": "Innovation, R&D",
#                                 "product_link": ""
#                                 }
#                             ]
#                         }
#                      ONLY once you receive the output of the organizational_intelligent_agent, you should run update_project_report where the project ID is in your input, the report_type is always "client_org", and the report is the markdown report produced by organizational_intelligence_agent. 
#                   """,
#     tools = [update_project_report],
#     sub_agents = [organizational_intelligence_agent],
#     output_key = "client_org_chancellor"
# )

# # master_agent = SequentialAgent(
# #     name = "master_agent",
# #     description = """
# #         Takes research information from user and runs five research agents, then stores the output of each one in mongodb
# #     """,
# #     sub_agents=[client_org_chancellor]
# # )

# root_agent = client_org_chancellor

from google.adk.agents import SequentialAgent, LlmAgent
from google.adk.models import Gemini
from google.genai import types as genai_types
from .tools.mongoupload import update_project_report
from .sub_agents.client_org_research import organizational_intelligence_agent
from .config import config


# Step 1: LLM step that ONLY builds the structured JSON for the subagent
client_org_prompt_builder = LlmAgent(
    name="client_org_prompt_builder",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(
            initial_delay=1,
            attempts=3
        )
    ),
    description="Takes the input data and produces the exact JSON schema required by organizational_intelligence_agent.",
    instruction="""
        Output ONLY a valid JSON object in this format:
        {
            "companies": [
                {
                    "name": "Company Name 1",
                    "ticker_symbol": "CMN1",
                    "industry": "Software",
                    "alternate name": "Company Name 2",
                    "website": "www.company2.com"
                }
            ],
            "products": [
                {
                    "product_or_service": "Enterprise AI Solutions",
                    "product_type": "Innovation, R&D",
                    "product_link": ""
                }
            ]
        }
    """,
    output_key="org_agent_input"
)


# Step 2: Force organizational_intelligence_agent to run
# It will take org_agent_input as input automatically
client_org_sequence = SequentialAgent(
    name="client_org_chancellor",
    description="""
        Builds the prompt for organizational_intelligence_agent, runs it, 
        then uploads the markdown report to MongoDB.
    """,
    sub_agents=[
        client_org_prompt_builder,
        organizational_intelligence_agent
    ]
)

root_agent = client_org_sequence
