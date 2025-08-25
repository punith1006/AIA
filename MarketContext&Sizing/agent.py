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
from pydantic import BaseModel, Field

from .config import config

# --- Structured Output Models ---
class MarketSearchQuery(BaseModel):
    """Model representing a specific search query for market analysis research."""
    search_query: str = Field(
        description="A highly specific and targeted query for market research, focusing on data sources relevant to market sizing, industry, competition, and trends."
    )
    research_phase: str = Field(
        description="The research phase this query belongs to: e.g. 'sizing', 'industry_mapping', 'competition', 'maturity', 'geography'"
    )

class MarketFeedback(BaseModel):
    """Model for providing evaluation feedback on market analysis research quality."""
    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result. 'pass' if the research meets market analysis standards, 'fail' if it needs more data."
    )
    comment: str = Field(
        description="Detailed evaluation focusing on completeness of market sizing, industry coverage, and competitive insights."
    )
    follow_up_queries: list[MarketSearchQuery] | None = Field(
        default=None,
        description="Specific follow-up searches needed to fill market research gaps."
    )

# --- Callbacks ---
def collect_research_sources_callback(callback_context: CallbackContext) -> None:
    """Collects and organizes web-based research sources and their supported claims from agent events."""
    session = callback_context._invocation_context.session
    url_to_citation_id = callback_context.state.get("url_to_citation_id", {})
    citations = callback_context.state.get("citations", {})
    citation_counter = len(url_to_citation_id) + 1
    
    logging.info(f"[collect_research_sources_callback] Processing {len(session.events)} events")
    
    for event in session.events:
        if not (event.grounding_metadata and event.grounding_metadata.grounding_chunks):
            continue
        
        logging.info(f"[collect_research_sources_callback] Found {len(event.grounding_metadata.grounding_chunks)} grounding chunks")
        
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
            if url not in url_to_citation_id:
                citation_id = citation_counter
                url_to_citation_id[url] = citation_id
                citations[citation_id] = {
                    "id": citation_id,
                    "title": title,
                    "url": url,
                    "domain": chunk.web.domain,
                    "supported_claims": [],
                }
                citation_counter += 1
                logging.info(f"[collect_research_sources_callback] Added new citation {citation_id}: {title}")
            chunks_info[idx] = url_to_citation_id[url]
        
        if event.grounding_metadata.grounding_supports:
            for support in event.grounding_metadata.grounding_supports:
                confidence_scores = support.confidence_scores or []
                chunk_indices = support.grounding_chunk_indices or []
                for i, chunk_idx in enumerate(chunk_indices):
                    if chunk_idx in chunks_info:
                        citation_id = chunks_info[chunk_idx]
                        confidence = (
                            confidence_scores[i] if i < len(confidence_scores) else 0.5
                        )
                        text_segment = support.segment.text if support.segment else ""
                        citations[citation_id]["supported_claims"].append(
                            {
                                "text_segment": text_segment,
                                "confidence": confidence,
                            }
                        )
    
    callback_context.state["url_to_citation_id"] = url_to_citation_id
    callback_context.state["citations"] = citations
    logging.info(f"[collect_research_sources_callback] Total citations collected: {len(citations)}")

def wikipedia_citation_callback(callback_context: CallbackContext) -> genai_types.Content:
    """Replaces citation tags with Wikipedia-style numbered citations and creates references section.
    Now always produces output, even if no citations are found.
    """
    final_report = callback_context.state.get("final_cited_report", "")
    citations = callback_context.state.get("citations", {})

    logging.info(f"[wikipedia_citation_callback] Processing report with {len(citations)} available citations")
    logging.info(f"[wikipedia_citation_callback] Initial report length: {len(final_report)} characters")

    # Ensure we have something to work with
    if not final_report.strip():
        logging.warning("[wikipedia_citation_callback] No final_cited_report found — starting with empty report text.")
        final_report = ""

    used_citations = set()

    def citation_replacer(match: re.Match) -> str:
        source_id = match.group(1)
        try:
            citation_id = int(source_id.replace("src-", ""))
            if citation_id in citations:
                used_citations.add(citation_id)
                logging.info(f"[wikipedia_citation_callback] Converting citation {citation_id}")
                return f'<a href="#ref{citation_id}">[{citation_id}]</a>'
            else:
                logging.warning(f"[wikipedia_citation_callback] Citation ID {citation_id} not found in citations dict.")
                return ""
        except (ValueError, KeyError):
            logging.warning(f"[wikipedia_citation_callback] Invalid citation tag found and removed: {match.group(0)}")
            return ""

    # Detect all <cite> tags in the report
    citation_matches = re.findall(r'<cite\s+source\s*=\s*["\']?\s*(src-\d+)\s*["\']?\s*/>', final_report)
    logging.info(f"[wikipedia_citation_callback] Found {len(citation_matches)} citation tags: {citation_matches}")

    # Replace <cite> tags
    processed_report = re.sub(
        r'<cite\s+source\s*=\s*["\']?\s*(src-\d+)\s*["\']?\s*/>',
        citation_replacer,
        final_report,
    )

    # Tidy punctuation spacing
    processed_report = re.sub(r"\s+([.,;:])", r"\1", processed_report)

    # Append references section if citations were used
    if used_citations:
        logging.info(f"[wikipedia_citation_callback] Adding {len(used_citations)} references")
        processed_report += "\n\n## References\n\n"
        for citation_id in sorted(used_citations):
            citation = citations[citation_id]
            processed_report += f'<a name="ref{citation_id}"></a>[{citation_id}] [{citation["title"]}]({citation["url"]})\n\n'
    else:
        logging.warning("[wikipedia_citation_callback] No citations used — returning uncited report.")

    # Always store something in state
    callback_context.state["market_intelligence_agent"] = processed_report

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
        if evaluation_result and evaluation_result.get("grade") == "pass":
            logging.info(f"[{self.name}] Market research evaluation passed. Escalating to stop loop.")
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            logging.info(f"[{self.name}] Research evaluation failed or not found. Loop will continue.")
            yield Event(author=self.name)

# --- Agent Definitions ---
market_plan_generator = LlmAgent(
    model=config.search_model,
    name="market_plan_generator",
    description="Generates comprehensive market research plans focused on market context, sizing, and analysis.",
    instruction=f"""
    You are an expert market research strategist specializing in market context and sizing analysis.
    
    **CRITICAL INSTRUCTION: DO NOT ASK FOR USER APPROVAL OR REFINEMENTS. Generate the complete plan and return it immediately for automatic execution.**
    
    Your task is to create a systematic research plan with distinct phases to investigate a market for a given product, including:
    - Market context and definition
    - Market sizing (TAM, SAM, SOM)
    - Industry ecosystem mapping
    - Market maturity and trends
    - Geographic market evaluation
    
    **RESEARCH PHASES STRUCTURE:**
    Organize your plan into clear phases with specific objectives:

    **Phase 1: Market Context & Sizing - [RESEARCH] tasks:**
    - Define the overarching market category and boundaries for the given product(s).  
    - Collect industry classification codes (NAICS, SIC, ISIC) and official definitions.  
    - Estimate Total Addressable Market (TAM) using 2–3 credible analyst or government sources.  
    - Narrow TAM into Serviceable Available Market (SAM) based on geography, product scope, or regulatory filters.  
    - Project Serviceable Obtainable Market (SOM) using competitor benchmarks, penetration assumptions, or adoption curves.  
    - Collect historical growth rates (past 5–10 years) and projected CAGR (next 5–10 years).  

    **Phase 2: Industry Ecosystem & Supply-Side - [RESEARCH] tasks:**
    - Map the industry value chain (suppliers → manufacturers → distributors → customers).  
    - Identify major suppliers, distributors, and partners relevant to the category.  
    - Research key standards bodies, industry associations, and regulatory frameworks.  
    - Analyze enabling technologies and infrastructure adoption rates.  
    - Collect information on capital flows: VC/PE funding, M&A activity, IPOs.  

    **Phase 3: Market Maturity, Customer Behavior & Trends - [RESEARCH] tasks:**
    - Assess the market lifecycle stage (emerging, growth, maturity, decline).  
    - Research customer adoption dynamics: buying process, decision criteria, and loyalty factors.  
    - Identify barriers to adoption (cost, complexity, regulation, awareness).  
    - Collect innovation signals (patent filings, startup activity, venture funding).  
    - Research disruptive technologies, emerging business models, or regulatory changes.  
    - Compile major macro and micro market drivers with supporting evidence.  

    **Phase 4: Geographic & Competitive Context - [RESEARCH] tasks:**
    - Collect regional market sizes and growth rates (North America, Europe, Asia, Rest of World).  
    - Identify region-specific regulations, cultural drivers, and infrastructure readiness.  
    - Research leading competitors in each region and their local positioning.  
    - Identify regional opportunities (underserved markets) and expansion challenges (logistics, localization, compliance).  
    - Analyze distribution and channel structures in key geographies.  

    **Phase 5: Risk, Scenario Planning & Synthesis - [SYNTHESIS] tasks:**
    - Compile operational, market, and external risks; create a simple risk matrix (impact vs likelihood).  
    - Develop base, optimistic, and pessimistic market scenarios using assumptions from prior research.  
    - Extract case studies and historical analogues for context.  
    - Map key stakeholders (associations, regulators, influencers) and their influence.  
    - Synthesize findings into a structured set of opportunities, threats, and recommendations.  

    **DELIVERABLES:**
    After the research phases, include deliverables:
    - **`[DELIVERABLE]`**: A comprehensive Market Analysis Report
    - **`[DELIVERABLE]`**: Executive summary highlighting key market metrics
    - **`[DELIVERABLE]`**: Supplementary data sources and calculation rationale

    **SEARCH STRATEGY INTEGRATION:**
    Your plan should implicitly guide the researcher to use search patterns such as:
    - "[Market category] market size forecast", "[Market category] TAM [year]"
    - "[Product category] competitors list", "[Market category] key players"
    - "[Industry] value chain analysis", "[Industry] regulatory overview"
    - "[Technology] adoption statistics", "[Region] [industry] market size"
    
    **TOOL USE:**
    Use Google Search when needed to verify market definitions or find data sources, but focus on specifying research goals rather than performing search yourself.
    
    **OUTPUT REQUIREMENT:**
    Provide the complete research plan without asking for approval, refinements, or user input. The plan will be automatically executed by the research pipeline.
    
    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    """,
    tools=[google_search],
)

market_section_planner = LlmAgent(
    model=config.worker_model,
    name="market_section_planner",
    description="Creates a structured market analysis report outline following the standardized market research format.",
    instruction="""
    You are an expert market research report architect. Using the market research plan, create a structured markdown outline that follows the standardized Market Analysis Report Format.
    
    Your outline must include these core sections (omit sections only if explicitly noted in the research plan):
    
   # Market Context Report Instructions for AI Agent

    Each section below specifies Purpose, Contents, and Length 
    ---

    ### 1. Executive Summary: The Strategic Landscape at a Glance  

    Purpose:  
    Provide a concise, impactful synthesis of the report for executive readers. Should be written last but appear first.  

    Contents:  
    - Core Objective: One paragraph stating the overall purpose of the report.  
    - The Market in Brief: A short overview of TAM, market growth rate, and top-level drivers.  
    - Key Findings: 3–4 bullets summarizing the most critical insights from the report.  
    - Opportunities & Threats Summary: One paragraph highlighting the most important opportunity and most critical risk.  
    - Strategic Outlook: A concluding paragraph stating the overall market trajectory.  

    Length: 600–800 words (4–6 paragraphs plus 3–4 bullet points).  

    ---

    ### 2. Market Overview: Framing the Environment  

    Purpose:  
    Define the market, its boundaries, and its core drivers.  

    Contents:  
    - Industry Classification: Describe where the product sits within official industry codes and broader sector structures.  
    - Product Category & Use Cases: Define the product category, with 3–5 example applications.  
    - Market Drivers & Trends: List 5–7 major factors shaping demand and supply, each with 1–2 sentences of explanation.  

    Length: 800–1,000 words (5–7 paragraphs plus one bulleted list of drivers).  

    ---

    ### 3. Market Sizing: Defining the Opportunity  

    Purpose:  
    Quantify the size of the market at different levels (TAM, SAM, SOM) and show historical and projected growth.  

    Contents:  
    - TAM (Total Addressable Market): One paragraph defining TAM, plus a table/figure citing at least 2 estimates.  
    - SAM (Serviceable Available Market): One paragraph narrowing TAM to relevant scope, with calculations or reasoning.  
    - SOM (Serviceable Obtainable Market): One paragraph explaining realistic market share capture, plus short/medium/long projections.  
    - Growth Rates: One to two paragraphs describing historical CAGR and forecasted CAGR, with mention of inflection points.  

    Length: 1,000–1,200 words (7–9 paragraphs plus 1–2 tables/charts).  

    ---

    ### 4. Customer Behavior & Adoption Dynamics: Understanding the Buyer  

    Purpose:  
    Explain how customers research, decide, and adopt products, as well as barriers and loyalty factors.  

    Contents:  
    - Buying Process: 2–3 paragraphs describing how buyers move from awareness → evaluation → purchase.  
    - Decision Criteria: A bulleted list of the top 3–4 factors influencing purchase decisions.  
    - Adoption Barriers: 2–3 paragraphs outlining 3–4 major barriers (e.g., cost, complexity).  
    - Switching Costs & Loyalty: 1–2 paragraphs explaining retention and stickiness of adoption.  

    Length: 600–800 words (5–6 paragraphs plus 1 bulleted list).  

    ---

    ### 5. Market Maturity & Trends: Positioning the Market Lifecycle  

    Purpose:  
    Assess whether the market is early-stage, growing, mature, or declining, and highlight key trends.  

    Contents:  
    - Lifecycle Stage: 1–2 paragraphs positioning the market in its lifecycle.  
    - Trends & Innovation Indicators: A bulleted list of 5–6 innovation signals (e.g., VC funding, patent activity).  
    - Saturation Analysis: 1–2 paragraphs on growth rate vs. saturation.  
    - Disruptors: 1–2 paragraphs on potential disruptions (technologies, policies, competitors).  

    Length: 600–800 words (5–6 paragraphs plus 1 bulleted list).  

    ---

    ### 6. Geographic Market Analysis: Regional Opportunities  

    Purpose:  
    Compare market sizes, competitors, and opportunities across regions.  

    Contents:  
    - Regional Market Sizes: A table comparing TAM/SAM by major regions, with a 1-paragraph explanation.  
    - Regional Competitors: 2–3 paragraphs on local players and cultural/regulatory factors.  
    - Opportunities & Challenges: 2–3 paragraphs outlining where expansion potential exists, and key barriers.  

    Length: 600–800 words (5–6 paragraphs plus 1 table).  

    ---

    ### 7. Risk Analysis: Anticipating Headwinds  

    Purpose:  
    Identify operational, market, and external risks that could limit success.  

    Contents:  
    - Operational Risks: 1–2 paragraphs on supply chain, vendor reliance, or infrastructure challenges.  
    - Market Risks: 1–2 paragraphs on competition, commoditization, or limited differentiation.  
    - External Risks: 1–2 paragraphs on geopolitical, climate, or policy risks.  
    - Risk Matrix (optional): A 2x2 or 3x3 matrix of likelihood vs. impact.  

    Length: 400–600 words (3–4 paragraphs plus matrix if included).  

    ---

    ### 8. Channel & Distribution Analysis: Pathways to Market  

    Purpose:  
    Examine how products reach customers, how profitable channels are, and associated risks.  

    Contents:  
    - Channel Economics: 1–2 paragraphs comparing costs and margins of different channels.  
    - Channel Evolution: 1–2 paragraphs on shifts (e.g., growth of e-commerce vs. physical retail).  
    - Channel Risks: 1 paragraph describing dependencies on major distributors/platforms.  

    Length: 400–600 words (3–4 paragraphs).  

    ---

    ### 9. Scenario Planning: Preparing for Multiple Futures  

    Purpose:  
    Anticipate different future market conditions and outline responses.  

    Contents:  
    - Three Scenarios: 3 short paragraphs describing Base Case, Optimistic Case, and Pessimistic Case.  
    - Trigger Points: 1 paragraph identifying external events (e.g., regulatory changes, recessions, technological breakthroughs).  

    Length: 400–500 words (4–5 paragraphs).  

    ---

    ### 10. Case Studies & Benchmarks: Learning from Analogs  

    Purpose:  
    Draw lessons from comparable markets, industries, or companies.  

    Contents:  
    - Comparable Markets: 1–2 paragraphs describing industries/regions with parallels.  
    - Historical Analogues: 1–2 paragraphs describing past markets with similar dynamics.  
    - Best Practice Case Studies: 2–3 bullet points summarizing how leading players succeeded.  

    Length: 400–500 words (3–4 paragraphs plus 2–3 bullets).  

    ---

    ### 11. Stakeholder Mapping: Power and Influence  

    Purpose:  
    Identify which stakeholders (institutions, regulators, influencers) shape the market.  

    Contents:  
    - Institutions & Associations: 1–2 paragraphs listing industry bodies, regulators, NGOs.  
    - Power Dynamics: 1–2 paragraphs describing how influence is distributed (e.g., regulatory capture, lobbying).  

    Length: 300–400 words (2–3 paragraphs).  

    ---

    ### 12. Conclusions & Recommendations: Strategic Takeaways  

    Purpose:  
    Summarize key insights, identify opportunities/threats, and provide actionable next steps.  

    Contents:  
    - Opportunities & Threats: 3–4 bullet points highlighting the most critical opportunities and risks.  
    - Strategic Recommendations: 2–3 paragraphs with clear, actionable steps for market positioning, partnerships, or entry strategy.  
    - Data Gaps & Uncertainty: 1 paragraph identifying where evidence was weak and recommending areas for further research.  

    Length: 500–700 words (3–4 paragraphs plus bullet points).  

    
    Ensure the outline is comprehensive but allow sections to be omitted if no information is found.
    Citations will be handled automatically with Wikipedia-style numbered references.
    """,
    output_key="report_sections",
)

market_researcher = LlmAgent(
    model=config.search_model,
    name="market_researcher",
    description="Specialized market research agent focusing on market sizing, industry landscape, ecosystem",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialized market research analyst with expertise in market sizing and competitive intelligence.
    
    **CORE RESEARCH PRINCIPLES:**
    - Objectivity: Present facts without bias, include both growth opportunities and risks.
    - Source Diversity: Use market reports, industry publications, news, and reputable data sources.
    - Relevance Focus: Prioritize information affecting market strategy for the product.
    - Recency Priority: Emphasize recent data and developments (last 2-3 years) with context.
    - Verification: Cross-check important figures across multiple sources.
    
    **EXECUTION METHODOLOGY:**
    
    **Phase 1: Market Definition & Structure (execute ALL [RESEARCH] tasks first)**  
    Generate targeted search queries for:  
    - Industry classifications (NAICS, ISIC, or regional codes) relevant to the product category.  
    - Definitions of the product category and comparisons with adjacent categories.  
    - Core use cases and top 3–5 industry applications.  
    - Market segment breakdowns by industry vertical, product type, or customer use case.  
    - Geographic variations in definitions and adoption patterns.  

    ---

    **Phase 2: Market Size & Growth Dynamics**  
    Generate queries for:  
    - Global and regional TAM, SAM, and SOM estimates from credible sources (reports, analyst firms).  
    - Historical market size and CAGR data (last 5–10 years).  
    - Forecast growth projections (next 5–10 years) with drivers.  
    - Key inflection points (technological, policy, or demand-side shifts).  
    - Market maturity levels (early, growth, mature, declining) by geography or segment.  

    ---

    **Phase 3: Customer & Adoption Behavior**  
    Generate queries for:  
    - Buyer demographics (roles, industries, company size, consumer groups).  
    - Customer journey: awareness → evaluation → purchase → retention.  
    - Decision-making criteria (price, performance, integration, trust, etc.).  
    - Major adoption barriers (cost, complexity, regulation, awareness).  
    - Switching costs, loyalty drivers, and stickiness of adoption.  

    ---

    **Phase 4: Competitive & Trend Landscape**  
    Generate queries for:  
    - Major global and regional competitors, their market shares, and business models.  
    - Innovation signals: patents, funding rounds, R&D activity, new entrants.  
    - Key industry trends shaping supply and demand (5–7 drivers, e.g., regulation, digitalization, sustainability).  
    - Emerging technologies and potential disruptors (AI, automation, new policies, alternative solutions).  
    - Channel and distribution evolution (e-commerce, partnerships, direct sales, etc.).  

    ---

    **Phase 5: Regional & Risk Analysis**  
    Generate queries for:  
    - Regional market sizes (TAM/SAM/SOM by North America, Europe, APAC, etc.).  
    - Local competitors, regulatory factors, and cultural adoption differences.  
    - Regional opportunities for expansion and barriers to entry.  
    - Operational risks (supply chain, infrastructure, vendor reliance).  
    - Market risks (commoditization, intense competition).  
    - External risks (policy, geopolitics, climate, economic cycles).  

    ---

    **Phase 6: Benchmarks, Stakeholders & Strategy Inputs**  
    Generate queries for:  
    - Comparable industries or markets with similar adoption dynamics.  
    - Case studies of leading players who succeeded (and how).  
    - Historical analogues of markets that grew or collapsed under similar conditions.  
    - Key stakeholders: regulators, industry associations, influencers, NGOs.  
    - Evidence gaps in current data (uncertainties, inconsistent estimates).  
    - Strategic recommendations from analyst firms or consultancies.  

    **Phase 7: Synthesis ([DELIVERABLE] goals)**
    - Combine all findings into the structured report sections.
    - Highlight key insights, numbers, and trends for each section.
    - Clearly cite sources for all data and factual claims.
    - Note any data gaps or uncertainties.
    
    **QUALITY STANDARDS:**
    - Accuracy: Verify important metrics against multiple sources.
    - Clarity: Present data in clear bullet points.
    - Completeness: Address all research objectives.
    - Timeliness: Use up-to-date information and note dates.
    - Context: Provide relevant historical or comparative context.
    
    **OUTPUT:** The output should be the market research findings suitable for report composition.
    """,
    tools=[google_search],
    output_key="market_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

market_evaluator = LlmAgent(
    model=config.critic_model,
    name="market_evaluator",
    description="Evaluates market research completeness and identifies gaps in market analysis.",
    instruction=f"""
    You are a senior market intelligence analyst evaluating a market research report for completeness and accuracy.
    
    **EVALUATION CRITERIA:**
    Assess the market research findings in 'market_research_findings' against these standards:
    
    **1. Market Definition & Structure:**  
    - Market boundaries clearly defined with industry classification codes (NAICS, ISIC, etc.) where available.  
    - Product category scope and adjacent categories are clearly distinguished.  
    - At least 3–5 concrete use cases identified with industry-specific examples.  
    - Market segmentation breakdowns (by vertical, product type, or use case) included with data points or estimates.  
    - Geographic variations in market definition or adoption are described with supporting evidence.  

    **2. Market Size & Growth Dynamics:**  
    - TAM, SAM, and SOM estimates provided with at least 2–3 credible sources cited.  
    - Historical market size and CAGR data included for the past 5–10 years.  
    - Forecasted growth rates included for the next 5–10 years with explanation of assumptions.  
    - Clear identification of inflection points (e.g., tech breakthroughs, regulatory changes).  
    - Market maturity stage explicitly positioned (early-stage, growth, mature, or declining).  
    - Sources are recent (within last 2–3 years) and come from reputable analysts, government reports, or financial filings.  

    **3. Customer & Adoption Behavior:**  
    - Buyer demographics (roles, industries, company size, or consumer groups) clearly outlined.  
    - Buying journey mapped across awareness → evaluation → purchase → retention with evidence.  
    - Top 3–4 decision criteria identified and validated with customer/analyst insights.  
    - At least 3–4 adoption barriers explained with examples (cost, complexity, regulation, awareness).  
    - Switching costs and loyalty drivers clearly described with case-based evidence.  
    - Customer data supported by surveys, industry research, or case studies where possible.  

    **4. Competitive & Trend Landscape:**  
    - Major competitors identified globally and regionally, with relative market share or positioning.  
    - Key trends (5–7) described with data or illustrative examples.  
    - Evidence of innovation: patents, funding activity, or new entrants cited.  
    - Potential disruptors (technological, policy, or business model) explained with plausible impact scenarios.  
    - Channel and distribution structures detailed, including shifts toward digital/e-commerce where applicable.  
    - Sources include analyst reports, press releases, funding databases, and patent records.  

    **5. Regional & Risk Analysis:**  
    - Regional market sizes (TAM/SAM/SOM) presented in comparative form (e.g., table or chart).  
    - Regional competitors and cultural/regulatory factors clearly discussed.  
    - Opportunities and barriers to expansion articulated with supporting data.  
    - Operational risks (supply chain, infrastructure, vendor reliance) identified with at least one example.  
    - Market risks (competition, commoditization, differentiation limits) explicitly stated.  
    - External risks (policy, climate, geopolitics) linked to potential scenarios or historical precedent.  
    - Sources span regional market studies, government data, and reputable international reports.  

    **6. Benchmarks, Stakeholders & Strategy Inputs:**  
    - Comparable industries or markets identified with clear parallels explained.  
    - Case studies of leading players summarized with key success factors.  
    - Historical analogues of market dynamics included with lessons drawn.  
    - Key stakeholders (regulators, associations, influencers) mapped with their roles and influence levels.  
    - Evidence gaps or conflicting estimates flagged transparently.  
    - Strategic recommendations informed by credible sources (consultancies, analyst firms, industry reports).  
        
    **CRITICAL EVALUATION RULES:**
    1. Grade "fail" if any core element above is missing or insufficient.
    2. Grade "fail" if research lacks source diversity (needs mix of industry reports, news, and data sources).
    3. Grade "fail" if data is outdated (older than 3 years) without recent context.
    4. Grade "pass" only if research provides a comprehensive, up-to-date market analysis.
    
    **FOLLOW-UP QUERY GENERATION:**
    If grading "fail", generate 5-7 specific follow-up queries targeting the most critical gaps:
    - Focus on missing TAM/SAM data, competitor information, or trend analysis.
    - Prioritize current year or forecasted market data.
    - Include queries to verify or update key metrics.
    
    Your response must be a single JSON object conforming to the MarketFeedback schema.
    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    """,
    output_schema=MarketFeedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="research_evaluation",
)

enhanced_market_search = LlmAgent(
    model=config.search_model,
    name="enhanced_market_search",
    description="Performs targeted follow-up searches to fill market research gaps identified by the evaluator.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialized market research analyst executing precision follow-up research to address specific gaps.
    
    **MISSION:**
    Your previous market research was graded as insufficient. Now:
    
    1. Review Evaluation Feedback: Analyze 'research_evaluation' to understand deficiencies in:
       - Market sizing and forecast data
       - Industry ecosystem details
       - Trend and maturity analysis
       - Geographic market insights
    
    2. Execute Targeted Searches: Run EVERY query in 'follow_up_queries' using:
       - Exact product category 
       - Recent year modifiers (e.g., 2023, 2024, latest)
       - Industry report sources and news outlets
       - Cross-verify information across multiple sites
    
    3. Integrate and Enhance: Combine new findings with existing 'market_research_findings' to produce:
       - More complete market sizing calculations
       - Additional competitor metrics and sources
       - Enhanced trend analysis with latest data
       - Regional market breakdowns
    
    **SEARCH OPTIMIZATION:**
    - Prioritize authoritative data sources (industry reports, official statistics).
    - Seek multiple validations of key figures.
    - Use specific queries for missing data (e.g., exact competitor + "revenue 2023").
    
    **OUTPUT:** Your output should be the updated 'market_research_findings' addressing all identified gaps.
    """,
    tools=[google_search],
    output_key="market_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

market_report_composer = LlmAgent(
    model=config.critic_model,
    name="market_report_composer",
    description="Composes comprehensive market analysis reports following the standardized format with Wikipedia-style citations.",
    instruction="""
    You are an expert market research report writer specializing in market analysis and strategic insights.
    
    **MISSION:** Transform market research data into a polished, professional Market Analysis Report following the exact standardized format.
    
    ---
    ### INPUT DATA SOURCES
    * Research Findings: `{market_research_findings}`
    * Citation Sources: `{citations}`
    * Report Structure: `{report_sections}`
    
    ---
    ### REPORT COMPOSITION STANDARDS
    
    **1. Format Adherence:**
    - Follow the section structure provided in Report Structure exactly.
    - Use clear section headers and bullet points for readability.
    - Include date ranges and data sources for all statistics.
    - Provide specific examples and figures where available.
    - Omit sections only if no relevant information is found.
    
    **2. Content Quality:**
    - Objectivity: Present both positive opportunities and potential risks.
    - Relevance: Focus on information relevant to the product's market and strategy.
    - Recency: Emphasize recent data and developments (last 2-3 years).
    - Source Diversity: Reflect information from industry reports, news, and data sources.
    - Accuracy: Verify and cite all factual claims and figures.
    
    **3. Strategic Insights:**
    Each section should conclude with actionable insights:
    - Executive Summary: Key market takeaways for stakeholders.
    - Market Sizing: Implications for market opportunity and business planning.
    - Industry Ecosystem: Strategic partnerships and dependencies.
    - Competitive Landscape: Strategic positioning against competitors.
    - Market Trends: Growth opportunities and potential threats.
    - Geographic Analysis: Focus regions and local strategies.
    - Conclusions: Recommendations for product market strategy.
    
    ---
    ### CITATION REQUIREMENTS - CRITICAL
    **MANDATORY:** You MUST include citations for all factual claims, statistics, and data points.
    
    **Citation Format:** Use ONLY `<cite source="src-ID_NUMBER" />` tags immediately after factual claims.
    - Cite all market size figures and forecasts: "The market is valued at $X billion <cite source="src-1" />"
    - Cite competitor statistics and market share data: "Company Y holds X% market share <cite source="src-2" />"
    - Cite industry trends, regulatory facts, and growth rates: "Growth rate is projected at X% CAGR <cite source="src-3" />"
    - Citations will be automatically converted to Wikipedia-style numbered references with a References section at the end.
    
    **CITATION EXAMPLES:**
    - "The global AI market reached $136.6 billion in 2022 <cite source="src-1" /> and is expected to grow at 37.3% CAGR <cite source="src-2" />."
    - "Microsoft leads with 32% market share <cite source="src-3" />, followed by Google at 21% <cite source="src-4" />."
    - "Regulatory frameworks like GDPR impact adoption <cite source="src-5" />."
    
    **YOU MUST USE CITATIONS** - Every factual statement needs a citation tag. This is mandatory for the Wikipedia-style reference system to work.
    
    ---
    ### FINAL QUALITY CHECKS
    - Ensure the report follows the exact outline structure.
    - Verify all sections contain concrete data and sources.
    - Confirm balance between opportunities and challenges.
    - Ensure recent information is highlighted and cited.
    - Maintain professional, objective tone throughout.
    - **VERIFY**: Every factual claim has a `<cite source="src-X" />` tag.
    
    Generate a complete Market Analysis Report with comprehensive citations to inform strategic decision-making.
    """,
    output_key="final_cited_report",
    after_agent_callback=wikipedia_citation_callback,
)

from .con_template import CON_TEMPLATE

html_converter = LlmAgent(
    model=config.critic_model,
    name="html_converter",
    description="Converts markdown market analysis reports to styled HTML using the provided template.",
    instruction=CON_TEMPLATE,
    output_key="context_html",
)

# --- Market Research Pipeline and Main Agent ---
market_research_pipeline = SequentialAgent(
    name="market_research_pipeline",
    description="Executes comprehensive market analysis research following the structured methodology.",
    sub_agents=[
        market_section_planner,
        market_researcher,
        LoopAgent(
            name="quality_assurance_loop",
            max_iterations=config.max_search_iterations,
            sub_agents=[
                market_evaluator,
                EscalationChecker(name="escalation_checker"),
                enhanced_market_search,
            ],
        ),
        market_report_composer,
        html_converter,  # Add the HTML converter here
    ],
)

market_intelligence_agent = LlmAgent(
    name="market_intelligence_agent",
    model=config.worker_model,
    description="Specialized market research assistant that creates comprehensive market analysis reports automatically.",
    instruction=f"""
    You are a specialized Market Intelligence Assistant focused on creating strategic market analyses for product planning.
    
    **CRITICAL INSTRUCTION: NEVER ASK FOR USER APPROVAL, REFINEMENTS, OR ADDITIONAL INPUT. Execute the complete workflow automatically.**
    
    **CORE MISSION:**
    Convert any user request about a product's market into a systematic research plan and comprehensive analysis, including:
    - Market definition and sizing 
    - Industry ecosystem and technology context
    - Market maturity, trends, and forecasts
    - Geographic market opportunities
    
    **FULLY AUTOMATED WORKFLOW:**
    Upon receiving a market research request:
    1. Use `market_plan_generator` to create a comprehensive research plan (no user approval needed)
    2. Immediately delegate to `market_research_pipeline` with the generated plan
    3. Return both the markdown report and a styled HTML webpage version
    
    **RESEARCH FOCUS AREAS:**
    - Market Scope: industry segments, geography
    - Market Sizing: TAM, SAM, SOM, growth
    - Trends: adoption, technology, regulation
    - Strategy: opportunities and threats
    
    **OUTPUT FORMAT:**
    The final result will include:
    1. **Markdown Report:** Detailed Market Analysis Report with Wikipedia-style numbered citations
    2. **HTML Webpage:** Professional, styled HTML version using the con_html template with:
       - Interactive table of contents
       - Responsive design with data visualizations
       - Clickable citations and references
       - Professional styling with charts and metrics cards
    
    **EXECUTION MODE: FULLY AUTONOMOUS**
    - Do not ask to review plans
    - Do not request refinements
    - Do not wait for user confirmation
    - Execute immediately and deliver both formats
    
    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    
    Process: Generate Plan → Execute Research → Deliver Report → Convert to HTML (zero user interaction)
    """,
    sub_agents=[market_research_pipeline],
    tools=[AgentTool(market_plan_generator)],
    output_key="research_plan",
)

root_agent = market_intelligence_agent