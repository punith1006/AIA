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

from .config import config
from .segmentation_report_template import SEG_TEMPLATE

# --- Structured Output Models ---
class SegmentationSearchQuery(BaseModel):
    """Model representing a specific search query for segmentation research."""
    search_query: str = Field(
        description="A specific and targeted query for segmentation research, focusing on data sources relevant to market and customer segments."
    )
    research_phase: str = Field(
        description="The research phase this query belongs to: e.g. 'segment_discovery', 'customer_analysis', 'attractiveness', 'fit'"
    )

class SegmentationFeedback(BaseModel):
    """Model for providing evaluation feedback on segmentation research quality."""
    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result. 'pass' if the segmentation research is comprehensive, 'fail' if it needs more detail."
    )
    comment: str = Field(
        description="Detailed evaluation focusing on completeness of segment discovery, customer segment profiles, and prioritization insights."
    )
    follow_up_queries: list[SegmentationSearchQuery] | None = Field(
        default=None,
        description="Specific follow-up searches needed to fill segmentation research gaps."
    )

# --- Callbacks ---
def collect_research_sources_callback(callback_context: CallbackContext) -> None:
    """Collects and organizes web-based research sources for Wikipedia-style numbered citations."""
    session = callback_context._invocation_context.session
    url_to_citation_num = callback_context.state.get("url_to_citation_num", {})
    citations = callback_context.state.get("citations", {})
    citation_counter = len(url_to_citation_num) + 1
    
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
            if url not in url_to_citation_num:
                citation_num = citation_counter
                url_to_citation_num[url] = citation_num
                citations[citation_num] = {
                    "number": citation_num,
                    "title": title,
                    "url": url,
                    "domain": chunk.web.domain,
                    "supported_claims": [],
                }
                citation_counter += 1
            chunks_info[idx] = url_to_citation_num[url]
        if event.grounding_metadata.grounding_supports:
            for support in event.grounding_metadata.grounding_supports:
                confidence_scores = support.confidence_scores or []
                chunk_indices = support.grounding_chunk_indices or []
                for i, chunk_idx in enumerate(chunk_indices):
                    if chunk_idx in chunks_info:
                        citation_num = chunks_info[chunk_idx]
                        confidence = (
                            confidence_scores[i] if i < len(confidence_scores) else 0.5
                        )
                        text_segment = support.segment.text if support.segment else ""
                        citations[citation_num]["supported_claims"].append(
                            {
                                "text_segment": text_segment,
                                "confidence": confidence,
                            }
                        )
    callback_context.state["url_to_citation_num"] = url_to_citation_num
    callback_context.state["citations"] = citations

def wikipedia_citation_replacement_callback(callback_context: CallbackContext) -> genai_types.Content:
    """Replaces citation tags with Wikipedia-style numbered citations and adds reference section."""
    final_report = callback_context.state.get("final_cited_report", "")
    citations = callback_context.state.get("citations", {})

    def tag_replacer(match: re.Match) -> str:
        citation_id = match.group(1)
        # Extract citation number from src-X format
        try:
            citation_num = int(citation_id.replace("src-", ""))
            if citation_num in citations:
                return f'<sup><a href="#ref{citation_num}">[{citation_num}]</a></sup>'
            else:
                logging.warning(f"Invalid citation tag found and removed: {match.group(0)}")
                return ""
        except (ValueError, KeyError):
            logging.warning(f"Invalid citation tag found and removed: {match.group(0)}")
            return ""

    # Replace citation tags with numbered links
    processed_report = re.sub(
        r'<cite\s+source\s*=\s*["\']?\s*(src-\d+)\s*["\']?\s*/>',
        tag_replacer,
        final_report,
    )
    
    # Clean up spacing around punctuation
    processed_report = re.sub(r"\s+([.,;:])", r"\1", processed_report)
    
    # Add References section at the end
    if citations:
        references_section = "\n\n## References\n\n"
        for citation_num in sorted(citations.keys()):
            citation = citations[citation_num]
            references_section += f'<a id="ref{citation_num}"></a>[{citation_num}] [{citation["title"]}]({citation["url"]}) - {citation["domain"]}\n\n'
        processed_report += references_section
    
    callback_context.state["segmentation_intelligence_agent"] = processed_report
    return genai_types.Content(parts=[genai_types.Part(text=processed_report)])

# --- Custom Agent for Loop Control ---
class EscalationChecker(BaseAgent):
    """Checks research evaluation and escalates to stop the loop if grade is 'pass' or if evaluation is missing."""
    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        evaluation_result = ctx.session.state.get("research_evaluation")
        
        if evaluation_result and evaluation_result.get("grade") == "pass":
            logging.info(f"[{self.name}] Segmentation research evaluation passed. Escalating to stop loop.")
            yield Event(author=self.name, actions=EventActions(escalate=True))
        elif not evaluation_result:
            logging.info(f"[{self.name}] No research evaluation found. Proceeding with enhancement search to improve completeness.")
            yield Event(author=self.name)
        else:
            logging.info(f"[{self.name}] Research evaluation failed. Loop will continue.")
            yield Event(author=self.name)

# --- Agent Definitions ---
segmentation_plan_generator = LlmAgent(
    model=config.search_model,
    name="segmentation_plan_generator",
    description="Generates comprehensive segmentation research plans focusing on market segments and customer segments.",
    instruction=f"""
    You are an expert market and customer segmentation strategist specializing in defining target market segments and customer groups for product targeting strategy.

    Your task is to create a systematic research plan with distinct phases to investigate segmentation for a given product, including:
    - Market Segment Discovery and Industry Mapping
    - Customer Segment Identification and Profiling
    - Segment Evaluation (attractiveness, competitive context)
    - Segmentation Framework and Targeting Recommendations

    **RESEARCH PHASES STRUCTURE:**
    Organize your plan into clear phase with specific objectives:

    **Phase 1: Market Segment Discovery (30% of effort) - [RESEARCH] tasks:**
    - Identify all potential market segments and sub-segments relevant to the product.
    - Map industry categories and use cases by segment.
    - Create a comprehensive inventory of addressable market segments.
    - Analyze segment characteristics and geographic variations.

    **Phase 2: Customer Segment Identification (20% of effort) - [RESEARCH] tasks:**
    - Identify distinct customer groups within each market segment (demographics, firmographics).
    - Characterize customer behaviors, needs, and decision criteria per segment.
    - Determine roles and influence patterns (decision makers vs end users).
    - Document customer journey stages relevant to the product.

    **Phase 3: Segment Attractiveness & Evaluation (25% of effort) - [RESEARCH] tasks:**
    - Assess segment size, growth trajectory, and revenue potential.
    - Evaluate competitive intensity and market share by segment.
    - Analyze accessibility and barriers for each segment.
    - Conduct entry barrier and channel analysis per segment.

    **Phase 4: Prioritization & Targeting Strategy (25% of effort) - [RESEARCH] tasks:**
    - Develop segment evaluation criteria (size, fit, competition).
    - Score and rank segments by attractiveness and strategic fit.
    - Align segments with product capabilities and company goals.
    - Provide targeting recommendations for top segments.

    **DELIVERABLES:**
    After the research phases, include deliverables:
    - **`[DELIVERABLE]`**: A Market Segment Inventory listing all viable segments with key attributes.
    - **`[DELIVERABLE]`**: A Customer Segment Matrix detailing customer profiles per segment.
    - **`[DELIVERABLE]`**: Segment Prioritization Rankings and Framework for top 3-5 segments.
    - **`[DELIVERABLE]`**: Targeting Recommendations for priority segments.

    **SEARCH STRATEGY INTEGRATION:**
    Your plan should implicitly guide the researcher to use search patterns such as:
    - "target market segments for [product category]"
    - "[product type] customer segmentation demographics"
    - "[industry] customer needs analysis"
    - "[product] use cases by industry"
    - "buying process [customer segment] [product]"

    **TOOL USE:**
    Use Google Search when needed to verify segment definitions or find relevant data, but focus on specifying research goals rather than performing search yourself.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Generate a detailed segmentation research plan with the structure above.
    """,
    tools=[google_search],
    output_key="research_plan",
)

segmentation_section_planner = LlmAgent(
    model=config.worker_model,
    name="segmentation_section_planner",
    description="Creates a structured segmentation analysis report outline following a standardized format.",
    instruction=f"""
    You are an expert market segmentation report architect. Using the segmentation research plan, create a structured markdown outline that follows the standardized Segmentation Analysis Report format.

    Your outline must include these core sections (omit sections only if explicitly noted in the research plan):

    # Market Context Report Instructions for AI Agent

    Each section below specifies Purpose, Contents, and Length so the AI can generate consistent, high-quality output.  

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


    **TOOL USE:**
    Use `google_search` only if you need to clarify industry terminology, market categories, or recent developments that might affect the research approach. Do not research the actual content - that's for the next agent.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
CRITICAL: EVERY SUBSECTION AND POINT IS ALLOWED TO BE A PARAGRAPH WITH 2-4 SENTENCES
    """,
    output_key="report_sections",
)

segmentation_researcher = LlmAgent(
    model=config.search_model,
    name="segmentation_researcher",
    description="Specialized segmentation research agent focusing on market segments, customer segmentation, and strategic analysis.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialized market and customer segmentation analyst.

    **CORE RESEARCH PRINCIPLES:**
    - Objectivity: Present facts without bias, include both opportunities and challenges.
    - Source Diversity: Use industry reports, market studies, news, and reputable data sources.
    - Relevance: Prioritize information affecting segmentation strategy for the product.
    - Recency: Emphasize recent data and developments (last 2-3 years).
    - Verification: Cross-check key findings across multiple sources.

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


    **OUTPUT:** The output should be the segmentation research findings suitable for report composition.
    """,
    tools=[google_search],
    output_key="segmentation_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

segmentation_evaluator = LlmAgent(
    model=config.critic_model,
    name="segmentation_evaluator",
    description="Evaluates segmentation research completeness and identifies gaps in segmentation analysis.",
    instruction=f"""
    You are a senior segmentation analysis evaluator. 

    **EVALUATION CRITERIA:**
    Assess the segmentation research findings in 'segmentation_research_findings' against these standards:

    **1. Segment Discovery (30%):**
    - A comprehensive list of market segments is present.
    - Segment definitions and industry categories are clearly described.
    - Use-case or product-market alignment for each segment is identified.

    **2. Customer Segmentation (20%):**
    - Customer profiles (demographics, roles) are detailed for each segment.
    - Behavioral patterns and needs of each customer group are described.
    - Decision-maker influence and customer journey factors are included.

    **3. Segment Attractiveness & Competition (25%):**
    - Size and growth estimates for each segment are provided.
    - Competitive intensity and key competitors by segment are included.
    - Accessibility and barrier analysis is addressed.

    **4. Prioritization & Fit (25%):**
    - Criteria for evaluating segments are defined.
    - Top segments are ranked with rationale.
    - Strategic fit of product to segments is analyzed.
    - Targeting recommendations are given for priority segments.

    **CRITICAL EVALUATION RULES:**
    1. Grade "fail" if any core element above is missing or insufficient.
    2. Grade "fail" if research lacks current data or authoritative sources.
    3. Grade "fail" if significant strategic insights are absent.
    4. Grade "pass" only if research provides a comprehensive, well-supported segmentation analysis.

    **FOLLOW-UP QUERY GENERATION:**
    If grading "fail", generate 5-7 specific follow-up queries targeting the most critical gaps:
    - Focus on missing segment definitions, customer data, or attractiveness metrics.
    - Prioritize queries for up-to-date segment size and competitor information.
    - Include queries to verify or expand on key segment insights.

    Your response must be a single JSON object conforming to the SegmentationFeedback schema.
    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    """,
    output_schema=SegmentationFeedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="research_evaluation",
)

enhanced_segmentation_search = LlmAgent(
    model=config.search_model,
    name="enhanced_segmentation_search",
    description="Performs targeted follow-up searches to fill segmentation research gaps identified by the evaluator.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialized segmentation research analyst executing precision follow-up research to address specific gaps.

    **MISSION:**
    Check if evaluation feedback and follow-up queries are available, then proceed accordingly:

    **IF `research_evaluation` AND `follow_up_queries` ARE AVAILABLE:**
    1. Review Evaluation Feedback: Analyze 'research_evaluation' to understand deficiencies in:
       - Segment definitions and inventory
       - Customer profile details
       - Segment size, growth, or competitor data
       - Overall prioritization or recommendations

    2. Execute Targeted Searches: Run EVERY query in 'follow_up_queries' using:
       - Exact product category and segment names
       - Recent year modifiers (e.g., 2023, 2024, latest)
       - Industry report sources and credible outlets
       - Cross-verify information across multiple sources

    **IF INPUTS ARE MISSING:**
    1. Acknowledge the missing inputs clearly
    2. Analyze existing 'segmentation_research_findings' to identify obvious gaps
    3. Generate your own comprehensive follow-up searches based on common segmentation research gaps:
       - Missing market size data for key segments
       - Incomplete customer demographic profiles
       - Lack of competitive analysis data
       - Missing growth projections
       - Insufficient geographic or industry breakdowns

    **ALWAYS DO:**
    3. Integrate and Enhance: Combine new findings with existing 'segmentation_research_findings' to produce:
       - A more complete segment inventory with descriptions
       - Additional customer segment profiles and needs data
       - Enhanced attractiveness analysis with updated metrics
       - Improved prioritization rationale with any missing information

    **SEARCH OPTIMIZATION:**
    - Prioritize authoritative data sources (industry reports, official statistics).
    - Seek multiple validations of key figures.
    - Use specific queries for missing data (e.g., exact segment name + "market size 2024").

    **OUTPUT:** Your output should be the updated 'segmentation_research_findings' addressing all identified gaps, whether from provided evaluation or self-identified gaps.
    """,
    tools=[google_search],
    output_key="segmentation_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

segmentation_report_composer = LlmAgent(
    model=config.critic_model,
    name="segmentation_report_composer",
    include_contents="none",
    description="Composes comprehensive segmentation analysis reports with Wikipedia-style numbered citations.",
    instruction="""
    You are an expert segmentation analysis report writer specializing in market segmentation and customer segmentation insights.

    **MISSION:** Transform segmentation research data into a polished, professional Segmentation Analysis Report following the exact standardized format with Wikipedia-style numbered citations.

    ---
    ### INPUT DATA SOURCES
    * Research Plan: `{research_plan}`
    * Research Findings: `{segmentation_research_findings}`
    * Citation Sources: `{citations}`
    * Report Structure: `{report_sections}`

    ---
    ### REPORT COMPOSITION STANDARDS

    **1. Format Adherence:**
    - Follow the section structure provided in the Report Structure exactly.
    - Use clear section headers and a combination of short paragraphs and bullet points for readability.
    - Include date ranges and data sources for all statistics.
    - Provide specific examples and figures where available.
    - Omit sections only if no relevant information is found.
    - The subsections can be expanded into multiple small paragraphs rather than just one bullet point

    **2. Content Quality:**
    - Objectivity: Present both opportunities and challenges for each segment.
    - Relevance: Focus on information relevant to segment selection and targeting.
    - Recency: Emphasize recent data and developments (last 2-3 years).
    - Source Diversity: Include information from industry reports, news, and data sources.
    - Accuracy: Verify and cite all factual claims and figures.
    - The subsections can be expanded into multiple small paragraphs rather than just one bullet point


    **3. Strategic Insights:**
    Each section should conclude with actionable insights:
    - Executive Summary: Key segment takeaways for stakeholders.
    - Market Segment Overview: Strategic importance of each segment.
    - Customer Segment Profiles: Implications of customer needs on targeting.
    - Segment Attractiveness: Opportunities and threats per segment.
    - Prioritization & Fit: Rationale for top segments and next steps.
    - Segmentation Framework: Guidelines for targeting each chosen segment.
    - Conclusions: Final recommendations and considerations.
    - The subsections can be expanded into multiple small paragraphs rather than just one bullet point


    ---
    ### WIKIPEDIA-STYLE CITATION REQUIREMENTS
    **Citation Format:** Use ONLY `<cite source="src-ID_NUMBER" />` tags immediately after factual claims.
    - Cite segment size figures, growth rates, and market values.
    - Cite customer demographic or behavior statistics.
    - Cite competitor information and market share data.
    - Cite industry trends, regulatory factors, and adoption challenges.
    - Citations will be automatically converted to numbered hyperlinks with a References section at the end.

    ---
    ### FINAL QUALITY CHECKS
    - Ensure the report follows the exact outline structure.
    - Verify all sections contain concrete data and sources.
    - Confirm balance between opportunities and risks.
    - Highlight recent information and trends.
    - Maintain a professional, objective tone throughout.

    Generate a complete Segmentation Analysis Report to inform strategic targeting decisions.
    """,
    output_key="final_cited_report",
    after_agent_callback=wikipedia_citation_replacement_callback,
)

# NEW HTML REPORT COMPOSER AGENT
segmentation_html_composer = LlmAgent(
    model=config.critic_model,
    name="segmentation_html_composer",
    include_contents="none",
    description="Composes a stylish HTML segmentation analysis report using the template format.",
    instruction=SEG_TEMPLATE,
    output_key="seg_html",
)

segmentation_research_pipeline = SequentialAgent(
    name="segmentation_research_pipeline",
    description="Executes comprehensive segmentation research following the structured methodology.",
    sub_agents=[
        segmentation_section_planner,
        segmentation_researcher,
        LoopAgent(
            name="quality_assurance_loop",
            max_iterations=config.max_search_iterations,
            sub_agents=[
                segmentation_evaluator,
                EscalationChecker(name="escalation_checker"),
                enhanced_segmentation_search,
            ],
        ),
        segmentation_report_composer,
        segmentation_html_composer,  # Added HTML composer after markdown report
    ],
)

segmentation_intelligence_agent = LlmAgent(
    name="segmentation_intelligence_agent",
    model=config.critic_model,
    description="Specialized segmentation intelligence assistant that creates comprehensive segmentation analysis reports automatically.",
    instruction=f"""
    You are a specialized Segmentation Intelligence Assistant focused on creating strategic segmentation analyses for product planning.

    **CORE MISSION:**
    Convert any user request about a product into a systematic segmentation research plan and analysis, including:
    - Market segment discovery and industry mapping
    - Customer segment identification and profiling
    - Segment attractiveness, competitive analysis, and prioritization
    - Segmentation framework with targeting recommendations

    **AUTOMATIC EXECUTION WORKFLOW:**
    1. **Plan Generation:** Use `segmentation_plan_generator` to create a comprehensive research plan covering all core objectives.
    2. **Immediate Execution:** Once the plan is generated, immediately delegate to `segmentation_research_pipeline` without waiting for user approval or input.

    **RESEARCH FOCUS AREAS:**
    - Segment Scope: market categories, customer types, geography
    - Segment Analysis: size, growth, competition
    - Customer Insights: needs, behaviors, decision factors
    - Strategy: opportunities and targeting tactics

    **OUTPUT EXPECTATIONS:**
    The final result should be:
    1. A detailed Segmentation Analysis Report (markdown) with Wikipedia-style numbered citations and actionable recommendations
    2. A stylish HTML report using the professional template format for presentation purposes

    **IMPORTANT:** Never ask for user approval, confirmation, or additional input after receiving the initial request. Generate the plan and immediately proceed with execution to deliver the complete analysis.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}

    Remember: Plan -> Execute Immediately. Never wait for user input during the process.
    """,
    sub_agents=[segmentation_research_pipeline],
    tools=[AgentTool(segmentation_plan_generator)],
    output_key="research_plan",
)

root_agent = segmentation_intelligence_agent