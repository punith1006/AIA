import datetime
import logging
import re
from collections.abc import AsyncGenerator
from typing import Literal, Dict, List, Optional

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


# --- Structured Output Models ---
class ProductInfo(BaseModel):
    """Model for product information input."""
    name: str = Field(description="Product name")
    category: str = Field(description="Product category or type")
    description: str = Field(description="Brief product description")
    key_features: List[str] = Field(default=[], description="Key product features or capabilities")
    target_market: str = Field(default="", description="Primary target market or industry")


class OrganizationTarget(BaseModel):
    """Model for target organization information."""
    name: str = Field(description="Organization name")
    industry: str = Field(default="", description="Industry or sector")
    size_estimate: str = Field(default="", description="Estimated company size (e.g., 'Large Enterprise', 'Mid-market')")
    location: str = Field(default="", description="Primary location or headquarters")


class SalesResearchQuery(BaseModel):
    """Model representing a specific search query for sales intelligence research."""
    search_query: str = Field(
        description="A highly specific and targeted query for sales intelligence research"
    )
    research_phase: str = Field(
        description="The research phase: 'product_analysis', 'organization_intelligence', 'competitive_landscape', 'fit_analysis', or 'stakeholder_mapping'"
    )
    target_entity: str = Field(
        description="The specific product or organization this query targets"
    )


class SalesFeedback(BaseModel):
    """Model for evaluating sales intelligence research quality."""
    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result. 'pass' if research meets sales intelligence standards, 'fail' if needs more depth."
    )
    comment: str = Field(
        description="Detailed evaluation focusing on completeness of product-organization fit analysis, stakeholder identification, and competitive insights."
    )
    follow_up_queries: List[SalesResearchQuery] | None = Field(
        default=None,
        description="Specific follow-up searches needed to fill sales intelligence gaps."
    )


# --- Callbacks (preserved from original) ---
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
    final_report = callback_context.state.get("final_cited_report", "")
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

    callback_context.state["final_report_with_citations"] = processed_report
    return genai_types.Content(parts=[genai_types.Part(text=processed_report)])


# --- Custom Agent for Loop Control ---
class SalesEscalationChecker(BaseAgent):
    """Checks sales research evaluation and escalates to stop the loop if grade is 'pass'."""

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        evaluation_result = ctx.session.state.get("sales_research_evaluation")
        if evaluation_result and evaluation_result.get("grade") == "pass":
            logging.info(
                f"[{self.name}] Sales intelligence research evaluation passed. Escalating to stop loop."
            )
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            logging.info(
                f"[{self.name}] Sales research evaluation failed or not found. Loop will continue."
            )
            yield Event(author=self.name)


# --- ENHANCED AGENT DEFINITIONS ---
sales_plan_generator = LlmAgent(
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(
            initial_delay=1,
            attempts=3
        )
    ),
    name="sales_plan_generator",
    description="Generates comprehensive sales intelligence research plans for product-organization fit analysis.",
    instruction=f"""
    You are an expert sales intelligence strategist specializing in product-market fit analysis and account-based selling research.
    
    Your task is to create a systematic 5-phase research plan to investigate target organizations and products for optimal sales alignment, focusing on:
    - Product positioning and competitive differentiation
    - Organizational structure and decision-making processes
    - Technology landscape and current vendor relationships
    - Stakeholder identification and influence mapping
    - Product-organization fit assessment and opportunity prioritization

    **INPUT ANALYSIS:**
    You will receive:
    - Products: List of products/services to be sold
    - Target Organizations: List of organizations to research as potential clients
    - Additional Context: Any specific requirements or focus areas

    **RESEARCH PHASES STRUCTURE:**
    Always organize your plan into these 5 distinct phases:

    **Phase 1: Product Intelligence (20% of effort) - [RESEARCH] tasks:**
    For each product:
    - Research product category landscape and market positioning
    - Analyze direct and indirect competitors' features, pricing, and positioning
    - Identify ideal customer profiles and successful use cases
    - Gather customer testimonials, case studies, and ROI metrics
    - Research integration capabilities and technical requirements

    **Phase 2: Organization Intelligence (25% of effort) - [RESEARCH] tasks:**
    For each target organization:
    - Investigate company website, official communications, and basic corporate information
    - Research financial health, recent funding, revenue trends, and budget indicators
    - Analyze leadership team, org structure, and key decision-makers
    - Find recent business news, strategic initiatives, and growth plans
    - Assess company culture, values, and operational priorities

    **Phase 3: Technology & Vendor Landscape (20% of effort) - [RESEARCH] tasks:**
    For each target organization:
    - Research current technology stack and digital infrastructure
    - Identify existing vendors and solution providers
    - Find contract renewal timelines and vendor satisfaction indicators
    - Analyze technology gaps and modernization initiatives
    - Assess integration requirements and technical compatibility

    **Phase 4: Stakeholder Mapping (20% of effort) - [RESEARCH] tasks:**
    For each target organization:
    - Research key decision-makers and their backgrounds/interests
    - Identify potential champions and influencers in relevant departments
    - Analyze reporting structures and decision-making processes
    - Find contact information and preferred communication channels
    - Research recent personnel changes and hiring patterns

    **Phase 5: Competitive & Risk Assessment (15% of effort) - [RESEARCH] tasks:**
    Cross-analysis of products vs. organizations:
    - Identify competitive threats and incumbent solutions per organization
    - Assess budget constraints and buying timeline indicators
    - Research potential objections and common sales obstacles
    - Analyze cultural fit and change management considerations
    - Evaluate regulatory compliance and security requirements

    **DELIVERABLE CLASSIFICATION:**
    After the research phases, add synthesis deliverables:
    - **`[DELIVERABLE]`**: Create comprehensive sales intelligence report following the 9-section format
    - **`[DELIVERABLE]`**: Develop product-organization fit analysis matrix
    - **`[DELIVERABLE]`**: Generate stakeholder engagement strategy and action plan

    **SEARCH STRATEGY INTEGRATION:**
    Your plan should guide the researcher to use these search patterns:
    
    Product Research:
    - "[Product name]" + "competitors" + "comparison" + "vs"
    - "[Product category]" + "market analysis" + "leaders" + "2024"
    - "[Product name]" + "customer reviews" + "case studies" + "ROI"
    - "[Product name]" + "pricing" + "features" + "integration"

    Organization Research:
    - "[Org name]" + "official website" + "leadership" + "executives"
    - "[Org name]" + "financial" + "revenue" + "funding" + "budget"
    - "[Org name]" + "technology stack" + "vendors" + "solutions"
    - "[Org name]" + "news" + "2024" + "strategic initiatives"
    - "[Org name]" + "org chart" + "departments" + "decision makers"

    Competitive Analysis:
    - "[Org name]" + "[Product category]" + "current solutions"
    - "[Org name]" + "vendor contracts" + "renewals" + "procurement"
    - "[Product competitors]" + "[Org name]" + "implementation" + "usage"

    **TOOL USE:**
    Only use Google Search if product or organization information is ambiguous and needs verification.
    Do NOT conduct the actual research - that's for the researcher agent.
    
    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    
    Focus on creating plans that will generate actionable sales intelligence for product-organization alignment and account-based selling strategies.
    """,
    output_key="sales_research_plan",
    tools=[google_search],
)

sales_section_planner = LlmAgent(
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(
            initial_delay=1,
            attempts=3
        )
    ),
    name="sales_section_planner",
    description="Creates a structured sales intelligence report outline following the standardized 9-section format.",
    instruction="""
    You are an expert sales intelligence report architect. Using the sales research plan, create a structured markdown outline that follows the standardized Sales Intelligence Report Format.

    Your outline must include these core sections:

    # 1. Executive Summary
    - Purpose statement (why this report exists)
    - Scope overview (products covered, organizations targeted)
    - Key Highlights:
      * Top opportunities and priority accounts
      * Expected short-term wins vs. long-term nurture strategies
      * Critical success factors
    - Key Risks/Challenges summary

    # 2. Product Overview(s)
    (One sub-section per product)
    - Product Name & Category
    - Core Value Proposition (strategic + operational benefits)
    - Key Differentiators vs. market alternatives
    - Primary Use Cases and success scenarios
    - Ideal Customer Profile (ICP) Fit Factors
    - Critical Success Metrics (ROI measures customers value)

    # 3. Target Organization Profiles
    (One section per organization)
    ## 3.1 Organization Summary
    - Basic company data (name, HQ, size, revenue, industry, website, fiscal year)
    - Recent news & strategic initiatives
    - Growth stage & funding status

    ## 3.2 Organizational Structure & Influence Map
    - Relevant department org chart
    - Decision-makers, influencers, and potential champions
    - Power/Interest Matrix mapping of key stakeholders

    ## 3.3 Business Priorities & Pain Points
    - Publicly stated objectives and strategic goals
    - Known challenges (financial, operational, competitive, compliance)
    - Technology gaps and modernization needs

    ## 3.4 Current Vendor & Solution Landscape
    - Existing tools and services in relevant categories
    - Contract renewal timelines (if discoverable)
    - Vendor satisfaction levels from reviews/forums

    # 4. Product–Organization Fit Analysis
    Cross-matrix analysis: each product vs. each target organization
    - Strategic Fit (Executive Level alignment)
    - Operational Fit (User Level compatibility)
    - Key Value Drivers for each combination
    - Potential Risks and obstacles
    - Champion/Decision Maker Candidates identification

    # 5. Competitive Landscape (Per Organization)
    - Top competitors selling similar products to each target org
    - Feature/price comparison tables where possible
    - Differentiation opportunities for each product-org combination

    # 6. Stakeholder Engagement Strategy
    - Primary Targets (who to approach first)
    - Messaging Themes (strategic vs. operational talking points)
    - Engagement Channels (email, LinkedIn, events, referrals)
    - Proposed Sequence (warm-up → discovery → demo → proposal)

    # 7. Risks & Red Flags
    - Budget constraints and procurement challenges
    - Mismatched priorities or timing issues
    - Strong competitor entrenchment
    - Lack of identified champions
    - Cultural resistance to change factors

    # 8. Next Steps & Action Plan
    ## Immediate Actions (Next 7-14 days)
    ## Medium-Term Strategy (Next 1-3 months)
    ## Long-Term Nurture (3+ months)

    # 9. Appendices
    - Detailed Stakeholder Profiles
    - Extended Org Charts and contact information
    - Full Vendor Lists & Technographic Data
    - Media Mentions archive
    - Reference Materials & Sources

    Ensure your outline allows for modular expansion - additional products or organizations can be added without breaking the structure.
    Do not include a separate References section - citations will be inline throughout.
    """,
    output_key="sales_report_sections",
)

sales_researcher = LlmAgent(
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(
            initial_delay=1,
            attempts=3
        )
    ),
    name="sales_researcher",
    description="Specialized sales intelligence researcher focusing on product-organization fit analysis and competitive positioning.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialized sales intelligence researcher with expertise in product-market fit analysis, competitive intelligence, and account-based selling research.

    **CORE RESEARCH PRINCIPLES:**
    - Sales Focus: Prioritize information directly impacting sales conversations and deal progression
    - Competitive Awareness: Always research competitive landscape and incumbent solutions
    - Stakeholder Mapping: Identify decision-makers, influencers, and potential champions
    - Opportunity Sizing: Assess budget capacity, timing, and buying signals
    - Risk Assessment: Flag potential obstacles, competitive threats, and misalignment factors

    **EXECUTION METHODOLOGY:**

    **Phase 1: Product Intelligence Research**
    For each product mentioned in the research plan:

    *Market Positioning & Competition:*
    - "[Product name] competitors comparison features pricing"
    - "[Product category] market leaders 2024 analysis"
    - "[Product name] vs [known competitor] differences"
    - "[Product name] customer reviews G2 Capterra TrustRadius"

    *Value Proposition & Use Cases:*
    - "[Product name] case studies ROI customer success"
    - "[Product name] pricing model cost benefits"
    - "[Product name] integration capabilities API technical"
    - "[Product category] buyer guide selection criteria"

    **Phase 2: Organization Intelligence Research**
    For each target organization:

    *Company Fundamentals:*
    - "[Org name] official website about leadership team"
    - "[Org name] revenue financial performance annual report"
    - "[Org name] recent news 2024 strategic initiatives"
    - "[Org name] company size employees headcount"

    *Decision-Making Structure:*
    - "[Org name] organizational chart executives departments"
    - "[Org name] CTO CIO IT leadership technology team"
    - "[Org name] procurement process vendor selection"
    - "[Org name] LinkedIn employees leadership profiles"

    **Phase 3: Technology & Vendor Landscape**
    For each target organization:

    *Current Technology Stack:*
    - "[Org name] technology stack tools software vendors"
    - "[Org name] [product category] current solutions"
    - "[Org name] vendor partnerships technology integrations"
    - "[Org name] digital transformation initiatives modernization"

    *Vendor Relationships:*
    - "[Org name] vendor contracts renewals procurement announcements"
    - "[Org name] software implementations technology deployments"
    - "[Org name] vendor satisfaction reviews complaints"

    **Phase 4: Stakeholder Research**
    For key personnel at each organization:

    *Decision-Maker Analysis:*
    - "[Person name] [Org name] LinkedIn background experience"
    - "[Department head] [Org name] technology priorities initiatives"
    - "[Org name] recent hires leadership changes [product category]"
    - "[Org name] conference speakers technology presentations"

    **Phase 5: Competitive & Market Research**
    Cross-analysis research:

    *Competitive Positioning:*
    - "[Competitor name] [Org name] partnership implementation"
    - "[Product category] market share [Org name] industry"
    - "[Org name] RFP requirements vendor selection [product category]"
    - "[Org name] budget technology spending [current year]"

    **QUALITY STANDARDS:**
    - Source Diversity: Mix official sources, industry reports, social media, and third-party reviews
    - Recency Priority: Focus on developments within last 12 months
    - Sales Relevance: Emphasize information affecting buying decisions
    - Competitive Intelligence: Always research competitive landscape thoroughly
    - Stakeholder Focus: Identify specific individuals and their influence/interests
    - Opportunity Assessment: Evaluate timing, budget capacity, and buying signals

    **CRITICAL SUCCESS FACTORS:**
    - Identify specific decision-makers and their contact information
    - Understand current technology pain points and gaps
    - Map competitive threats and incumbent solution relationships
    - Assess budget capacity and procurement timeline indicators
    - Find specific business challenges your products can address
    - Locate potential internal champions and influencers

    **Phase 6: Synthesis ([DELIVERABLE] goals)**
    After completing ALL research goals:
    - Organize findings by the structured report sections
    - Create product-organization fit matrix analysis
    - Develop stakeholder engagement strategies
    - Highlight sales-relevant insights and next steps
    - Flag information gaps requiring additional research

    Your research must provide actionable intelligence for account-based selling and product positioning strategies.
    """,
    tools=[google_search],
    output_key="sales_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

sales_evaluator = LlmAgent(
    model=Gemini(
        model=config.critic_model,
        retry_options=genai_types.HttpRetryOptions(
            initial_delay=1,
            attempts=3
        )
    ),
    name="sales_evaluator",
    description="Evaluates sales intelligence research completeness and identifies gaps for product-organization fit analysis.",
    instruction=f"""
    You are a senior sales intelligence analyst evaluating research for completeness and sales actionability.

    **EVALUATION CRITERIA:**
    Assess the research findings in 'sales_research_findings' against these standards:

    **1. Product Intelligence Quality (25%):**
    - Competitive landscape mapping and differentiation analysis
    - Customer testimonials, case studies, and ROI data
    - Pricing information and value proposition clarity
    - Technical requirements and integration capabilities

    **2. Organization Intelligence Depth (25%):**
    - Company fundamentals (size, revenue, structure, recent news)
    - Decision-making processes and organizational hierarchy
    - Business priorities, strategic initiatives, and pain points
    - Financial health and budget capacity indicators

    **3. Technology & Vendor Analysis (20%):**
    - Current technology stack and solution inventory
    - Existing vendor relationships and satisfaction levels
    - Contract renewal timelines and procurement processes
    - Technology gaps and modernization initiatives

    **4. Stakeholder Mapping Quality (20%):**
    - Decision-maker identification with contact details
    - Influence mapping and champion identification potential
    - Individual backgrounds, interests, and technology preferences
    - Recent personnel changes and hiring patterns

    **5. Sales Intelligence Actionability (10%):**
    - Product-organization fit assessment completeness
    - Competitive positioning and threat analysis
    - Buying signals and opportunity timing indicators
    - Specific next steps and engagement strategy clarity

    **CRITICAL EVALUATION RULES:**
    1. Grade "fail" if ANY of these core elements are missing or insufficient:
       - Competitive analysis for each product category
       - Key decision-maker identification with roles/contact info
       - Current vendor/solution landscape per organization
       - Business priorities and technology pain points
       - Budget capacity and procurement timeline indicators

    2. Grade "fail" if research lacks product-organization fit analysis depth

    3. Grade "fail" if stakeholder mapping is incomplete or lacks actionable contact information

    4. Grade "fail" if competitive intelligence is superficial or missing key incumbent solutions

    5. Grade "pass" only if research provides comprehensive sales intelligence suitable for immediate account-based selling execution

    **FOLLOW-UP QUERY GENERATION:**
    If grading "fail", generate 5-8 specific follow-up queries targeting the most critical gaps:
    - Focus on missing competitive intelligence and vendor relationships
    - Target specific stakeholder identification and contact information
    - Address product-organization fit analysis gaps
    - Include searches for budget/procurement timeline indicators
    - Prioritize actionable sales intelligence over general company information

    Be demanding about research quality - sales intelligence requires detailed, current, and actionable information for successful account-based selling.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Your response must be a single, raw JSON object validating against the 'SalesFeedback' schema.
    """,
    output_schema=SalesFeedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="sales_research_evaluation",
)

enhanced_sales_search = LlmAgent(
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(
            initial_delay=1,
            attempts=3
        )
    ),
    name="enhanced_sales_search",
    description="Executes targeted follow-up searches to fill sales intelligence gaps identified by the evaluator.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialist sales intelligence researcher executing precision follow-up research to address specific gaps in product-organization fit analysis.

    **MISSION:**
    Your previous sales research was graded as insufficient. You must now:

    1. **Review Evaluation Feedback:** Analyze 'sales_research_evaluation' to understand specific deficiencies in:
       - Product competitive positioning and differentiation analysis
       - Organization stakeholder mapping and decision-maker identification
       - Technology landscape and current vendor relationships
       - Product-organization fit assessment depth
       - Sales actionability and next steps clarity

    2. **Execute Targeted Searches:** Run EVERY query in 'follow_up_queries' using these enhanced search techniques:
       - Use exact product names and competitor names for precision
       - Include organization names with specific role titles for stakeholder identification
       - Target specific platforms (LinkedIn for personnel, G2/Capterra for product reviews)
       - Search for financial indicators and procurement timeline clues
       - Focus on recent information (2024, current year) for timing relevance

    3. **Integrate and Enhance:** Combine new findings with existing 'sales_research_findings' to create:
       - More comprehensive product-organization fit matrices
       - Better verified competitive intelligence and positioning
       - Enhanced stakeholder profiles with contact information
       - Stronger technology landscape and vendor relationship analysis
       - More actionable sales intelligence and engagement strategies

    **SEARCH OPTIMIZATION FOR SALES INTELLIGENCE:**
    - Prioritize competitive intelligence and incumbent solution identification
    - Seek specific stakeholder contact information and organizational roles
    - Look for budget indicators, procurement processes, and buying timeline signals
    - Find technology pain points and modernization initiatives
    - Cross-reference vendor satisfaction and contract renewal information
    - Verify product positioning through customer reviews and case studies

    **INTEGRATION STANDARDS:**
    - Merge new information with existing research seamlessly
    - Highlight newly discovered sales-relevant information
    - Resolve conflicts between old and new competitive intelligence
    - Maintain focus on actionable sales insights throughout
    - Ensure enhanced research supports account-based selling strategies

    Your output must be complete, enhanced sales intelligence findings that address all identified gaps and enable immediate sales action.
    """,
    tools=[google_search],
    output_key="sales_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

sales_report_composer = LlmAgent(
    model=Gemini(
        model=config.critic_model,
        retry_options=genai_types.HttpRetryOptions(
            initial_delay=1,
            attempts=3
        )
    ),
    name="sales_report_composer",
    include_contents="none",
    description="Composes comprehensive sales intelligence reports following the standardized 9-section format with proper citations.",
    instruction="""
    You are an expert sales intelligence report writer specializing in product-organization fit analysis and account-based selling strategy.

    **MISSION:** Transform research data into a polished, professional Sales Intelligence Report following the exact standardized 9-section format.

    ---
    ### INPUT DATA SOURCES
    * Research Plan: `{sales_research_plan}`
    * Research Findings: `{sales_research_findings}` 
    * Citation Sources: `{sources}`
    * Report Structure: `{sales_report_sections}`

    ---
    ### REPORT COMPOSITION STANDARDS

    **1. Format Adherence:**
    - Follow the exact 9-section structure provided in Report Structure
    - Create detailed product-organization fit analysis matrices
    - Include specific stakeholder profiles with contact information where available
    - Provide actionable next steps and engagement strategies
    - Use tables and matrices for complex cross-analysis sections

    **2. Content Quality:**
    - **Sales Focus:** Every section must provide actionable sales intelligence
    - **Account-Based Approach:** Tailor analysis for each specific organization
    - **Competitive Intelligence:** Thoroughly analyze competitive threats and positioning opportunities
    - **Stakeholder Mapping:** Identify specific decision-makers, influencers, and champions
    - **Opportunity Assessment:** Evaluate timing, budget capacity, and buying signals

    **3. Sales Intelligence Priorities:**
    Each section should enable sales action:
    - Executive Summary: Clear opportunity prioritization and risk assessment
    - Product Overview: Value propositions tailored to discovered organizational needs
    - Organization Profiles: Detailed stakeholder maps and business priorities
    - Fit Analysis: Specific product-organization combinations with success probability
    - Competitive Landscape: Threat assessment and differentiation strategies
    - Engagement Strategy: Specific outreach plans and messaging themes
    - Action Plan: Time-bound, executable next steps for each opportunity

    **4. Cross-Analysis Requirements:**
    - Create detailed Product-Organization Fit matrix tables
    - Map competitive landscape for each organization-product combination
    - Provide stakeholder influence/interest matrices where possible
    - Include budget and timing assessments for each opportunity

    ---
    ### CRITICAL CITATION REQUIREMENTS
    **Citation Format:** Use ONLY `<cite source="src-ID_NUMBER" />` tags immediately after claims
    **Citation Strategy:**
    - Cite all competitive intelligence and market positioning claims
    - Cite financial data, budget indicators, and procurement information
    - Cite stakeholder information and organizational structure details
    - Cite technology stack information and vendor relationships
    - Cite customer testimonials and product review data
    - Do NOT include a separate References section - all citations must be inline

    ---
    ### MODULAR STRUCTURE REQUIREMENTS
    - Design sections to accommodate multiple products and organizations
    - Use consistent formatting for product and organization profiles
    - Create reusable templates for stakeholder profiles
    - Ensure additional entities can be added without structural changes

    **FINAL QUALITY CHECKS:**
    - Verify comprehensive product-organization fit analysis coverage
    - Confirm actionable stakeholder engagement strategies
    - Check competitive intelligence completeness and accuracy
    - Validate specific next steps and timing recommendations
    - Ensure professional tone suitable for sales team execution

    Generate a comprehensive sales intelligence report that enables immediate account-based selling execution.
    """,
    output_key="final_cited_report",
    after_agent_callback=citation_replacement_callback,
)

# --- UPDATED PIPELINE ---
sales_intelligence_pipeline = SequentialAgent(
    name="sales_intelligence_pipeline",
    description="Executes comprehensive sales intelligence research following the 5-phase methodology for product-organization fit analysis.",
    sub_agents=[
        sales_section_planner,
        sales_researcher,
        LoopAgent(
            name="sales_quality_assurance_loop",
            max_iterations=config.max_search_iterations,
            sub_agents=[
                sales_evaluator,
                SalesEscalationChecker(name="sales_escalation_checker"),
                enhanced_sales_search,
            ],
        ),
        sales_report_composer,
    ],
)

# --- UPDATED MAIN AGENT ---
sales_intelligence_agent = LlmAgent(
    name="sales_intelligence_agent",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(
            initial_delay=1,
            attempts=3
        )
    ),
    description="Specialized sales intelligence assistant that creates comprehensive product-organization fit analysis reports for account-based selling.",
    instruction=f"""
    You are a specialized Sales Intelligence Assistant focused on comprehensive product-organization fit analysis for account-based selling and strategic sales planning.

    **CORE MISSION:**
    Convert ANY user request about products and target organizations into a systematic research plan that generates actionable sales intelligence through:
    - Product competitive analysis and value proposition mapping
    - Organizational structure and stakeholder identification
    - Technology landscape and vendor relationship analysis
    - Product-organization fit assessment and opportunity prioritization
    - Sales engagement strategy and action plan development

    **CRITICAL WORKFLOW RULE:**
    NEVER answer sales questions directly. Your ONLY first action is to use `sales_plan_generator` to create a research plan.

    **INPUT PROCESSING:**
    You will receive requests in various formats:
    - "Research [Company A, Company B] for selling [Product X, Product Y]"
    - "Analyze fit between our [Product] and [Organization]"
    - "Sales intelligence for [Products] targeting [Organizations]"
    - Lists of companies and products in any combination

    **Your 3-Step Process:**
    1. **Plan Generation:** Use `sales_plan_generator` to create a 5-phase research plan covering:
       - Product Intelligence (competitive landscape, value props, customer success)
       - Organization Intelligence (structure, priorities, decision-makers)
       - Technology & Vendor Landscape (current solutions, gaps, procurement)
       - Stakeholder Mapping (decision-makers, influencers, champions)
       - Competitive & Risk Assessment (threats, obstacles, timing)

    2. **Plan Refinement:** Automatically adjust the plan to ensure:
       - Complete product-organization cross-analysis coverage
       - Stakeholder identification and contact research
       - Competitive intelligence and incumbent solution mapping
       - Budget capacity and procurement timeline assessment
       - Sales engagement strategy development

    3. **Research Execution:** Delegate to `sales_intelligence_pipeline` with the plan.

    **RESEARCH FOCUS AREAS:**
    - **Product Analysis:** Competitive positioning, value propositions, customer success metrics
    - **Organization Analysis:** Decision-makers, business priorities, technology gaps
    - **Fit Assessment:** Product-organization compatibility matrices and opportunity scoring  
    - **Competitive Intelligence:** Incumbent solutions, vendor relationships, competitive threats
    - **Sales Strategy:** Stakeholder engagement plans, messaging themes, timing considerations
    - **Risk Assessment:** Budget constraints, competitive entrenchment, cultural fit challenges

    **OUTPUT EXPECTATIONS:**
    The final research will produce a comprehensive Sales Intelligence Report with 9 standardized sections:
    1. Executive Summary (opportunities, risks, priorities)
    2. Product Overview(s) (value props, differentiators, use cases)
    3. Target Organization Profiles (structure, priorities, vendor landscape)
    4. Product–Organization Fit Analysis (cross-matrix with scores)
    5. Competitive Landscape (per organization analysis)
    6. Stakeholder Engagement Strategy (who, how, when)
    7. Risks & Red Flags (obstacles and mitigation)
    8. Next Steps & Action Plan (immediate, medium, long-term)
    9. Appendices (detailed profiles, contacts, references)

    **AUTOMATIC EXECUTION:**
    You will proceed immediately with research without asking for approval or clarification unless the input is completely ambiguous. Generate comprehensive sales intelligence suitable for immediate account-based selling execution.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}

    Remember: Plan → Execute → Deliver. Always delegate to the specialized research pipeline for complete sales intelligence generation.
    """,
    sub_agents=[sales_intelligence_pipeline],
    tools=[AgentTool(sales_plan_generator)],
    output_key="sales_research_plan",
)

root_agent = sales_intelligence_agent