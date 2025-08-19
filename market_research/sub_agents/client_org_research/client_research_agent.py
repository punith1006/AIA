import datetime
import logging
import re
from collections.abc import AsyncGenerator
from typing import Literal

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.planners import BuiltInPlanner
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from google.genai import types as genai_types
from google.adk.models import Gemini
from pydantic import BaseModel, Field

from ...config import config

# --- Structured Output Models ---
class SearchQuery(BaseModel):
    """Model representing a specific search query for organizational research."""

    search_query: str = Field(
        description="A highly specific and targeted query for organizational web search, focusing on company information, social media, and public perception."
    )
    research_phase: str = Field(
        description="The research phase this query belongs to: 'foundation', 'market_intelligence', 'deep_dive', or 'risk_assessment'"
    )

class Feedback(BaseModel):
    """Model for providing evaluation feedback on organizational research quality."""

    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result. 'pass' if the research meets organizational intelligence standards, 'fail' if it needs more depth."
    )
    comment: str = Field(
        description="Detailed evaluation focusing on completeness of company information, source diversity, and sales-relevant insights."
    )
    follow_up_queries: list[SearchQuery] | None = Field(
        default=None,
        description="Specific follow-up searches needed to fill organizational intelligence gaps. Should focus on missing company data, leadership info, financial status, or market position.",
    )

# --- Callbacks ---
def collect_research_sources_callback(callback_context: CallbackContext) -> None:
    """Collects and organizes web-based research sources and their supported claims from agent events."""
    session = callback_context._invocation_context.session
    url_to_short_id = callback_context.state.get("url_to_short_id", {})
    sources = callback_context.state.get("sources", {})
    id_counter = len(url_to_short_id) + 1
    
    for event in session.events:
        if not (event.grounding_metadata and event.grounding_metadata.grounding_chunks):
            continue
        chunks_info = {}
        for idx, chunk in enumerate(event.grounding_metadata.grounding_chunks):
            if not chunk.web:
                continue
            url = chunk.web.uri
            title = (
                chunk.web.title
                if chunk.web.title != chunk.web.domain
                else chunk.web.domain
            )
            if url not in url_to_short_id:
                short_id = f"src-{id_counter}"
                url_to_short_id[url] = short_id
                sources[short_id] = {
                    "short_id": short_id,
                    "title": title,
                    "url": url,
                    "domain": chunk.web.domain,
                    "supported_claims": [],
                }
                id_counter += 1
            chunks_info[idx] = url_to_short_id[url]
        
        if event.grounding_metadata.grounding_supports:
            for support in event.grounding_metadata.grounding_supports:
                confidence_scores = support.confidence_scores or []
                chunk_indices = support.grounding_chunk_indices or []
                for i, chunk_idx in enumerate(chunk_indices):
                    if chunk_idx in chunks_info:
                        short_id = chunks_info[chunk_idx]
                        confidence = (
                            confidence_scores[i] if i < len(confidence_scores) else 0.5
                        )
                        text_segment = support.segment.text if support.segment else ""
                        sources[short_id]["supported_claims"].append(
                            {
                                "text_segment": text_segment,
                                "confidence": confidence,
                            }
                        )
    
    callback_context.state["url_to_short_id"] = url_to_short_id
    callback_context.state["sources"] = sources

def citation_replacement_callback(
    callback_context: CallbackContext,
) -> genai_types.Content:
    """Replaces citation tags in a report with Wikipedia-style clickable numbered references."""
    final_report = callback_context.state.get("organizational_intelligence_agent", "")
    sources = callback_context.state.get("sources", {})

    # Assign each short_id a numeric index
    short_id_to_index = {}
    for idx, short_id in enumerate(sorted(sources.keys()), start=1):
        short_id_to_index[short_id] = idx

    # Replace <cite> tags with clickable reference links
    def tag_replacer(match: re.Match) -> str:
        short_id = match.group(1)
        if short_id not in short_id_to_index:
            logging.warning(f"Invalid citation tag found and removed: {match.group(0)}")
            return ""
        index = short_id_to_index[short_id]
        return f"[<a href=\"#ref{index}\">{index}</a>]"

    processed_report = re.sub(
        r'<cite\s+source\s*=\s*["\']?\s*(src-\d+)\s*["\']?\s*/?>',
        tag_replacer,
        final_report,
    )
    processed_report = re.sub(r"\s+([.,;:])", r"\1", processed_report)

    # Build a Wikipedia-style References section with anchors
    references = "\n\n## References\n"
    for short_id, idx in sorted(short_id_to_index.items(), key=lambda x: x[1]):
        source_info = sources[short_id]
        domain = source_info.get('domain', '')
        references += (
            f"<p id=\"ref{idx}\">[{idx}] "
            f"<a href=\"{source_info['url']}\">{source_info['title']}</a>"
            f"{f' ({domain})' if domain else ''}</p>\n"
        )

    processed_report += references
    callback_context.state["organizational_intelligence_agent"] = processed_report
    return genai_types.Content(parts=[genai_types.Part(text=processed_report)])

# --- Custom Agent for Loop Control ---
class EscalationChecker(BaseAgent):
    """Checks research evaluation and escalates to stop the loop if grade is 'pass'."""

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        evaluation_result = ctx.session.state.get("research_evaluation")
        logging.info(f"[{self.name}] Checking evaluation result: {evaluation_result}")
        
        # More robust check for pass condition
        if (evaluation_result and 
            isinstance(evaluation_result, dict) and 
            evaluation_result.get("grade") == "pass"):
            logging.info(f"[{self.name}] Research evaluation passed. Escalating to stop loop.")
            yield Event(author=self.name, actions=EventActions(escalate=True))
        elif (evaluation_result and 
              hasattr(evaluation_result, 'grade') and 
              evaluation_result.grade == "pass"):
            logging.info(f"[{self.name}] Research evaluation passed (object). Escalating to stop loop.")
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            logging.info(f"[{self.name}] Research evaluation failed or not found. Loop will continue.")
            yield Event(author=self.name)

# --- ENHANCED AGENT DEFINITIONS ---
organizational_plan_generator = LlmAgent(
    model=config.search_model,
    name="organizational_plan_generator",
    description="Generates comprehensive organizational research plans focused on company intelligence, social media presence, and market positioning.",
    instruction=f"""
    You are an expert organizational intelligence strategist specializing in company research for sales and business development.
    
    Your task is to create a systematic 4-phase research plan to investigate one or more organizations, focusing on:
    - Company website and official presence
    - Social media activity and public perception
    - Financial health and market position
    - Leadership and competitive landscape
    
    **RESEARCH PHASES STRUCTURE:**
    Always organize your plan into these 4 distinct phases with specific objectives:

    **Phase 1: Foundation Research (30% of effort) - [RESEARCH] tasks:**
    - Investigate company website, official communications, and basic corporate information
    - Research LinkedIn company page and key employee profiles
    - Find SEC filings, financial reports, or funding information
    - Gather basic industry and market positioning data

    **Phase 2: Market Intelligence (25% of effort) - [RESEARCH] tasks:**
    - Analyze industry reports and market position
    - Research direct competitors and competitive landscape
    - Find recent business news coverage and media mentions
    - Investigate trade publication coverage and industry recognition

    **Phase 3: Deep Dive Investigation (25% of effort) - [RESEARCH] tasks:**
    - Research leadership team backgrounds and recent changes
    - Analyze technology stack and digital presence
    - Find partnership announcements and strategic initiatives  
    - Gather customer testimonials, case studies, and reviews

    **Phase 4: Risk & Opportunity Assessment (20% of effort) - [RESEARCH] tasks:**
    - Investigate potential controversies, legal issues, or reputation risks
    - Assess financial health indicators and stability
    - Identify buying signals and business expansion indicators
    - Analyze competitive threats and market challenges

    **DELIVERABLE CLASSIFICATION:**
    After the research phases, add synthesis deliverables:
    - **`[DELIVERABLE]`**: Create comprehensive organizational intelligence report
    - **`[DELIVERABLE]`**: Develop sales approach recommendations and stakeholder mapping
    - **`[DELIVERABLE]`**: Compile competitive positioning analysis

    **TOOL USE:**
    Only use Google Search if the organization name is ambiguous or you need to verify the organization exists.
    Do NOT research the actual content - that's for the researcher agent.
    
    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    
    Focus on creating plans that will generate sales-relevant intelligence about organizations.
    """,
    output_key="research_plan",
    tools=[google_search],
)

organizational_section_planner = LlmAgent(
    model=config.worker_model,
    name="organizational_section_planner",
    description="Creates a structured report outline following the standardized organizational research format.",
    instruction="""
    You are an expert business intelligence report architect. Using the organizational research plan, create a structured markdown outline that follows the standardized Organizational Research Report Format.

    Your outline must include these core sections (omit sections only if explicitly noted in the research plan):

    # 1. Executive Summary
    - Organization Name and basic identifiers
    - Industry/Sector classification
    - Founded date and key metrics
    - Key Findings Summary for sales approach

    # 2. Company Overview  
    - Business Model and revenue generation
    - Core Products/Services portfolio
    - Target Markets and customer segments
    - Value Proposition and competitive positioning
    - Organizational Structure details

    # 3. Financial Health & Performance
    - Revenue Trends and growth patterns
    - Profitability and financial metrics
    - Funding Status and investor information
    - Market Position and competitive ranking
    - Financial Stability Indicators

    # 4. Leadership & Key Personnel
    - Executive Team profiles and backgrounds
    - Board of Directors and key stakeholders
    - Key Decision Makers for purchasing
    - Recent Leadership Changes and impact

    # 5. Recent News & Developments
    - Positive Developments and achievements
    - Challenges/Controversies and risk factors
    - Strategic Initiatives and future plans
    - Market Recognition and awards

    # 6. Technology & Innovation Profile
    - Tech Stack and digital infrastructure
    - Digital Maturity assessment
    - Innovation Focus and R&D investments
    - Technology Partnerships and vendors

    # 7. Competitive Landscape
    - Direct Competitors identification
    - Competitive Advantages and differentiators
    - Competitive Challenges and vulnerabilities
    - Market Dynamics and industry trends

    # 8. Cultural & Operational Insights
    - Company Culture and values
    - Corporate Social Responsibility initiatives
    - Operational Challenges and constraints
    - Geographic Presence and expansion

    # 9. Sales Intelligence
    - Buying Signals and opportunity indicators
    - Budget Indicators and financial capacity
    - Decision-Making Process characteristics
    - Preferred Vendor Characteristics patterns

    # 10. Risk Assessment
    - Business Risks and market threats
    - Reputation Risks and PR challenges
    - Relationship Risks for partnerships
    - Opportunity Risks and timing factors

    # 11. Recommendations for Approach
    - Optimal Messaging strategies
    - Timing Considerations for outreach
    - Key Stakeholders to Target
    - Potential Objections and responses
    - Competitive Positioning strategies

    Ensure your outline is comprehensive but allows for sections to be omitted if insufficient information is found during research.
    Do not include a separate References section - citations will be inline.
    """,
    output_key="report_sections",
)

organizational_researcher = LlmAgent(
    model=config.search_model,
    name="organizational_researcher",
    description="Specialized organizational intelligence researcher focusing on company websites, social media, and public perception analysis.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialized organizational intelligence researcher with expertise in company analysis, digital presence evaluation, and competitive intelligence gathering.

    **CORE RESEARCH PRINCIPLES:**
    - Objectivity First: Present facts without bias, include both positive and negative information
    - Source Diversity: Use company websites, news articles, social media, financial reports, industry publications
    - Relevance Focus: Prioritize information impacting sales conversations and business relationships
    - Recency Priority: Emphasize developments from last 6-12 months with historical context
    - Verification: Cross-reference important claims across multiple sources

    **EXECUTION METHODOLOGY:**
    Execute research systematically but efficiently. Conduct targeted searches focusing on the most critical information first:

    *Company Website & Official Presence:*
    - "[Company Name] official website"
    - "[Company Name] about us mission vision"
    - "[Company Name] products services offerings"
    - "[Company Name] leadership team executives"

    *Financial & Corporate Information:*
    - "[Company Name] revenue funding financial performance"
    - "[Company Name] company size employees headcount"

    *Recent Developments:*
    - "[Company Name] news 2024 recent developments"
    - "[Company Name] partnerships acquisitions"

    **SEARCH STRATEGY IMPLEMENTATION:**
    - Execute searches systematically but avoid excessive iteration
    - Focus on official sources and recent developments
    - Cross-reference claims across multiple sources for verification
    - Note information gaps but prioritize available information

    **QUALITY STANDARDS:**
    - Fact-checking: Verify significant claims across sources
    - Attribution: Note sources for major findings  
    - Balance: Include both organizational strengths and weaknesses
    - Relevance: Focus on information impacting sales potential
    - Completeness: Address key aspects while being practical about depth

    Your final output must be comprehensive organizational intelligence suitable for sales decision-making.
    """,
    tools=[google_search],
    output_key="organizational_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

organizational_evaluator = LlmAgent(
    model=config.critic_model,
    name="organizational_evaluator",
    description="Evaluates organizational research completeness and identifies intelligence gaps for sales-focused company analysis.",
    instruction=f"""
    You are a senior business intelligence analyst evaluating organizational research for completeness and sales relevance.

    **EVALUATION CRITERIA:**
    Assess the research findings in 'organizational_research_findings' against these standards:

    **1. Foundation Research Quality (40%):**
    - Company website and official information completeness
    - Leadership team identification and background details
    - Basic company metrics (size, industry, structure)

    **2. Market Intelligence Depth (30%):**
    - Business model and revenue stream clarity
    - Recent news coverage and developments
    - Competitive positioning insights

    **3. Sales Intelligence Value (30%):**
    - Decision-maker identification potential
    - Financial capacity indicators
    - Opportunity and risk factors

    **EVALUATION RULES - BE MORE LENIENT:**
    1. Grade "pass" if the following CORE elements are present:
       - Basic company information (what they do, size, leadership)
       - Some financial/business model information
       - Recent developments or news (if available)
       - Official website information

    2. Grade "fail" ONLY if research is severely lacking in multiple core areas:
       - No clear understanding of what the company does
       - No leadership or company structure information
       - No recent information or business context
       - Insufficient information for sales approach

    3. When in doubt, grade "pass" - perfect information is not required

    **FOLLOW-UP QUERY GENERATION:**
    If grading "fail", generate 3-5 specific, targeted follow-up queries focusing ONLY on the most critical missing pieces.

    Be pragmatic about research quality - aim for "good enough for sales intelligence" rather than "perfect and complete."

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    
    **IMPORTANT:** Your response must be a single, raw JSON object that validates against the 'Feedback' schema.
    """,
    output_schema=Feedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="research_evaluation",
)

enhanced_organizational_search = LlmAgent(
    model=config.search_model,
    name="enhanced_organizational_search",
    description="Executes targeted follow-up searches to fill organizational intelligence gaps identified by the evaluator.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialist organizational researcher executing precision follow-up research to address specific intelligence gaps.

    **MISSION:**
    Your previous organizational research was graded as insufficient. You must now:

    1. **Review Evaluation Feedback:** Analyze 'research_evaluation' to understand specific deficiencies

    2. **Execute Targeted Searches:** Run EVERY query in 'follow_up_queries' efficiently:
       - Use exact company names for precision
       - Include recent date modifiers when relevant
       - Focus on filling the specific gaps identified
       - Prioritize official sources and recent information

    3. **Integrate and Enhance:** Combine new findings with existing 'organizational_research_findings'

    **SEARCH OPTIMIZATION:**
    - Execute searches efficiently and systematically
    - Focus on the most critical missing information
    - Avoid redundant or overly similar searches
    - Prioritize actionable business intelligence

    **INTEGRATION STANDARDS:**
    - Merge new information with existing research seamlessly
    - Highlight newly discovered information
    - Ensure enhanced research addresses the evaluation gaps
    - Maintain focus on sales-relevant intelligence

    Your output must be the complete, enhanced organizational research findings that address the identified gaps.
    """,
    tools=[google_search],
    output_key="organizational_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

organizational_report_composer = LlmAgent(
    model=config.critic_model,
    name="organizational_report_composer",
    include_contents="none",
    description="Composes comprehensive organizational intelligence reports following the standardized business research format with proper citations.",
    instruction="""
    You are an expert business intelligence report writer specializing in organizational research for sales and business development.

    **MISSION:** Transform research data into a polished, professional Organizational Research Report following the standardized format.

    ### INPUT DATA SOURCES
    * Research Plan: `{research_plan}`
    * Research Findings: `{organizational_research_findings}` 
    * Citation Sources: `{sources}`
    * Report Structure: `{report_sections}`

    ### REPORT COMPOSITION STANDARDS

    **1. Format Adherence:**
    - Follow the section structure provided in Report Structure
    - Use clear section headers and bullet points for readability
    - Include specific examples and data points where available
    - Omit sections only if absolutely no relevant information was found

    **2. Content Quality:**
    - **Objectivity First:** Present both positive and negative findings without bias
    - **Sales Relevance:** Focus on information impacting sales conversations
    - **Recency Priority:** Emphasize recent developments with context
    - **Source Diversity:** Reflect information from multiple source types

    **3. Sales Intelligence Focus:**
    Each section should provide sales-relevant insights where possible.

    ### CRITICAL CITATION REQUIREMENTS
    **Citation Format:** Use ONLY `<cite source="src-ID_NUMBER" />` tags immediately after claims
    **Citation Strategy:**
    - Cite factual claims, financial data, and leadership information
    - Cite recent developments and news items
    - Cite competitive positioning claims
    - Do NOT include a separate References section - all citations must be inline

    ### FINAL QUALITY CHECKS
    - Ensure report follows standardized format structure
    - Verify sections provide actionable insights
    - Check proper citation placement throughout
    - Ensure professional, objective tone

    Generate a comprehensive organizational intelligence report that enables informed sales decision-making.
    """,
    output_key="organizational_intelligence_agent",
    after_agent_callback=citation_replacement_callback,
)

# --- UPDATED PIPELINE WITH REDUCED LOOP ITERATIONS ---
organizational_research_pipeline = SequentialAgent(
    name="organizational_research_pipeline",
    description="Executes comprehensive organizational intelligence research following the 4-phase methodology for sales-focused company analysis.",
    sub_agents=[
        organizational_section_planner,
        organizational_researcher,
        LoopAgent(
            name="quality_assurance_loop",
            max_iterations=2,  # Reduced from config.max_search_iterations
            sub_agents=[
                organizational_evaluator,
                EscalationChecker(name="escalation_checker"),
                enhanced_organizational_search,
            ],
        ),
        organizational_report_composer,
    ],
)

# --- UPDATED MAIN AGENT ---
organizational_intelligence_agent = LlmAgent(
    name="organizational_intelligence_agent",
    model=config.worker_model,
    description="Specialized organizational research assistant that creates comprehensive company intelligence reports for sales and business development.",
    instruction=f"""
    You are a specialized Organizational Intelligence Assistant focused on comprehensive company research for sales and business development purposes.

    **CORE MISSION:**
    Convert ANY user request about organizations into a systematic research plan that generates sales-relevant business intelligence.

    **CRITICAL WORKFLOW RULE:**
    NEVER answer organizational questions directly. Your ONLY first action is to use `organizational_plan_generator` to create a research plan.

    **Your 3-Step Process:**
    1. **Plan Generation:** Use `organizational_plan_generator` to create a comprehensive research plan
    2. **Plan Refinement:** Ensure the plan is focused and achievable
    3. **Research Execution:** Delegate to `organizational_research_pipeline` with the plan

    **RESEARCH FOCUS AREAS:**
    - Company Intelligence: Official information, business model, leadership
    - Digital Presence: Website, social media, online reputation  
    - Financial Health: Revenue, funding, market performance
    - Competitive Position: Market share, advantages, industry standing
    - Sales Intelligence: Decision-makers, buying signals, opportunities
    - Risk Assessment: Controversies, regulatory issues, threats

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}

    Remember: Plan ? Refine ? Execute. Always delegate to the specialized research pipeline.
    """,
    sub_agents=[organizational_research_pipeline],
    tools=[AgentTool(organizational_plan_generator)],
    output_key="client_org_research_plan",
)

# root_agent = organizational_intelligence_agent