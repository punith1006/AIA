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

from ...config import config


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
    final_report = callback_context.state.get("sales_intelligence_agent", "")
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

    callback_context.state["sales_intelligence_agent"] = processed_report
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
    model = config.search_model,
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
    model = config.worker_model,
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
    model = config.search_model,
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
    model = config.critic_model,
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
    model = config.search_model,
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
    model = config.critic_model,
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
    output_key="sales_intelligence_agent",
    after_agent_callback=citation_replacement_callback,
)

html_report_generator = LlmAgent(
    model=config.critic_model,
    name="html_report_generator",
    description="Converts markdown sales intelligence reports into professional HTML format with responsive design and interactive elements.",
    instruction="""
    You are a professional HTML report designer specializing in converting sales intelligence markdown reports into polished, interactive HTML documents.

    **MISSION:** Transform the markdown sales intelligence report into a comprehensive HTML document following the standardized template structure with proper styling, responsive design, and professional presentation.

    ---
    ### INPUT DATA SOURCES
    * Markdown Report: `{sales_intelligence_agent}` - The complete markdown sales intelligence report
    * Citation Sources: `{sources}` - Source information for reference links

    ---
    ### HTML GENERATION REQUIREMENTS

    **1. Document Structure:**
    - Generate complete HTML document with proper DOCTYPE, head, and body
    - Include embedded CSS for professional styling and responsive design
    - Extract product/company names for dynamic title generation
    - Use semantic HTML5 elements for accessibility

    **2. Content Extraction and Conversion:**
    - **Header**: Extract main product/company name for report title
    - **Metadata**: Infer report type, focus area, and target organization from content
    - **Table of Contents**: Generate with proper anchor links to all sections
    - **Sections**: Convert all 9 standard sections from markdown to HTML
    - **Citations**: Convert markdown citation references to proper HTML spans with citation class

    **3. CSS Framework - Include Complete Stylesheet:**
    ```css
    :root {
        --primary-color: #2c3e50;
        --secondary-color: #3498db;
        --accent-color: #2980b9;
        --success-color: #27ae60;
        --warning-color: #f39c12;
        --danger-color: #e74c3c;
        --light-color: #ecf0f1;
        --dark-color: #2c3e50;
        --text-color: #333;
        --border-radius: 8px;
        --box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        line-height: 1.6;
        color: var(--text-color);
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        min-height: 100vh;
        padding: 20px;
    }

    .container {
        max-width: 1200px;
        margin: 0 auto;
        background: white;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        overflow: hidden;
    }

    .report-header {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
        color: white;
        padding: 40px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }

    .report-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="1"/></pattern></defs><rect width="100" height="100" fill="url(%23grid)"/></svg>');
        opacity: 0.3;
    }

    .report-header h1 {
        font-size: 2.5em;
        font-weight: 700;
        margin-bottom: 10px;
        position: relative;
        z-index: 2;
    }

    .report-subtitle {
        font-size: 1.1em;
        opacity: 0.9;
        position: relative;
        z-index: 2;
    }

    .report-meta {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        padding: 30px 40px;
        background: var(--light-color);
        border-bottom: 1px solid #e0e0e0;
    }

    .report-meta div {
        text-align: center;
    }

    .report-meta h4 {
        color: var(--primary-color);
        font-size: 0.9em;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
        font-weight: 600;
    }

    .report-meta p {
        font-size: 1.1em;
        font-weight: 500;
        color: var(--dark-color);
    }

    .content {
        padding: 40px;
    }

    .toc {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: var(--border-radius);
        padding: 30px;
        margin-bottom: 40px;
    }

    .toc h3 {
        color: var(--primary-color);
        margin-bottom: 20px;
        font-size: 1.3em;
        border-bottom: 2px solid var(--secondary-color);
        padding-bottom: 10px;
    }

    .toc-list {
        list-style: none;
        columns: 2;
        column-gap: 30px;
    }

    .toc-list li {
        margin-bottom: 8px;
        break-inside: avoid;
    }

    .toc-list a {
        text-decoration: none;
        color: var(--accent-color);
        font-weight: 500;
        display: block;
        padding: 5px 10px;
        border-radius: 4px;
        transition: all 0.3s ease;
    }

    .toc-list a:hover {
        background: var(--secondary-color);
        color: white;
        transform: translateX(5px);
    }

    section {
        margin-bottom: 50px;
        scroll-margin-top: 20px;
    }

    section h2 {
        color: var(--primary-color);
        font-size: 2em;
        margin-bottom: 25px;
        padding-bottom: 10px;
        border-bottom: 3px solid var(--secondary-color);
        position: relative;
    }

    section h3 {
        color: var(--dark-color);
        font-size: 1.4em;
        margin: 25px 0 15px 0;
        font-weight: 600;
    }

    section h4 {
        color: var(--accent-color);
        font-size: 1.2em;
        margin: 20px 0 10px 0;
        font-weight: 600;
    }

    .data-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin: 25px 0;
    }

    .data-card {
        background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%);
        border: 1px solid #e9ecef;
        border-radius: var(--border-radius);
        padding: 20px;
        box-shadow: var(--box-shadow);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .data-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }

    .metric-label {
        display: block;
        font-size: 0.9em;
        color: var(--secondary-color);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }

    .metric-value {
        font-size: 1.3em;
        font-weight: 700;
        color: var(--primary-color);
    }

    .data-table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        background: white;
        border-radius: var(--border-radius);
        overflow: hidden;
        box-shadow: var(--box-shadow);
    }

    .data-table th {
        background: var(--primary-color);
        color: white;
        padding: 15px 12px;
        text-align: left;
        font-weight: 600;
        font-size: 0.9em;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .data-table td {
        padding: 12px;
        border-bottom: 1px solid #e9ecef;
        vertical-align: top;
    }

    .data-table tbody tr:hover {
        background: #f8f9fa;
    }

    .section-highlight {
        background: linear-gradient(135deg, rgba(52, 152, 219, 0.1) 0%, rgba(41, 128, 185, 0.1) 100%);
        border-left: 4px solid var(--secondary-color);
        padding: 20px;
        margin: 20px 0;
        border-radius: 0 var(--border-radius) var(--border-radius) 0;
    }

    .risk-warning {
        background: linear-gradient(135deg, rgba(231, 76, 60, 0.1) 0%, rgba(192, 57, 43, 0.1) 100%);
        border-left: 4px solid var(--danger-color);
        padding: 20px;
        margin: 20px 0;
        border-radius: 0 var(--border-radius) var(--border-radius) 0;
    }

    .competitive-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 20px;
        margin: 25px 0;
    }

    .competitor-card {
        background: white;
        border: 1px solid #e9ecef;
        border-radius: var(--border-radius);
        padding: 20px;
        box-shadow: var(--box-shadow);
        transition: transform 0.3s ease;
    }

    .competitor-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
    }

    .competitor-name {
        font-size: 1.2em;
        font-weight: 700;
        color: var(--primary-color);
        margin-bottom: 5px;
    }

    .competitor-focus {
        font-style: italic;
        color: var(--secondary-color);
        margin-bottom: 10px;
        font-size: 0.95em;
    }

    .stakeholder-map {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 15px;
        margin: 20px 0;
    }

    .stakeholder-item {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: var(--border-radius);
        padding: 15px;
        transition: background 0.3s ease;
    }

    .stakeholder-item:hover {
        background: #e9ecef;
    }

    .stakeholder-item h4 {
        color: var(--primary-color);
        margin-bottom: 5px;
        font-size: 1em;
    }

    .risk-matrix {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin: 20px 0;
    }

    .risk-item {
        padding: 15px;
        border-radius: var(--border-radius);
        font-weight: 500;
        text-align: center;
        border: 2px solid;
        transition: transform 0.3s ease;
    }

    .risk-item:hover {
        transform: scale(1.02);
    }

    .risk-high {
        background: rgba(231, 76, 60, 0.1);
        border-color: var(--danger-color);
        color: var(--danger-color);
    }

    .risk-medium {
        background: rgba(243, 156, 18, 0.1);
        border-color: var(--warning-color);
        color: var(--warning-color);
    }

    .risk-low {
        background: rgba(39, 174, 96, 0.1);
        border-color: var(--success-color);
        color: var(--success-color);
    }

    .timeline {
        position: relative;
        padding-left: 30px;
        margin: 25px 0;
    }

    .timeline::before {
        content: '';
        position: absolute;
        left: 15px;
        top: 0;
        bottom: 0;
        width: 2px;
        background: var(--secondary-color);
    }

    .timeline-item {
        position: relative;
        margin-bottom: 30px;
    }

    .timeline-marker {
        position: absolute;
        left: -23px;
        top: 5px;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: var(--secondary-color);
        border: 3px solid white;
        box-shadow: 0 0 0 3px var(--secondary-color);
    }

    .timeline-content {
        background: white;
        border: 1px solid #e9ecef;
        border-radius: var(--border-radius);
        padding: 20px;
        box-shadow: var(--box-shadow);
    }

    .timeline-content h4 {
        margin-bottom: 10px;
        color: var(--primary-color);
    }

    .citation {
        color: var(--secondary-color);
        font-weight: 500;
        font-size: 0.9em;
    }

    .references {
        background: #f8f9fa;
        border-top: 1px solid #e9ecef;
        padding: 30px 40px;
        margin-top: 40px;
    }

    .references h2 {
        color: var(--primary-color);
        margin-bottom: 20px;
    }

    .references ol {
        padding-left: 0;
    }

    .references li {
        margin-bottom: 10px;
        padding: 10px;
        background: white;
        border-radius: var(--border-radius);
        border: 1px solid #e9ecef;
    }

    .references a {
        color: var(--accent-color);
        text-decoration: none;
        font-weight: 500;
    }

    .references a:hover {
        text-decoration: underline;
    }

    footer {
        text-align: center;
        padding: 30px;
        background: var(--primary-color);
        color: white;
        font-size: 0.9em;
    }

    footer p {
        margin-bottom: 5px;
    }

    @media (max-width: 768px) {
        .container {
            margin: 10px;
            border-radius: 10px;
        }
        
        .report-header {
            padding: 30px 20px;
        }
        
        .report-header h1 {
            font-size: 2em;
        }
        
        .content {
            padding: 20px;
        }
        
        .report-meta {
            padding: 20px;
            grid-template-columns: 1fr;
            gap: 15px;
        }
        
        .toc-list {
            columns: 1;
        }
        
        .data-grid {
            grid-template-columns: 1fr;
        }
        
        .competitive-grid {
            grid-template-columns: 1fr;
        }
        
        .data-table {
            font-size: 0.9em;
        }
        
        .data-table th,
        .data-table td {
            padding: 8px 6px;
        }
    }

    @media (max-width: 480px) {
        body {
            padding: 10px;
        }
        
        .report-header h1 {
            font-size: 1.8em;
        }
        
        .content {
            padding: 15px;
        }
        
        section h2 {
            font-size: 1.6em;
        }
        
        .data-table {
            display: block;
            overflow-x: auto;
            white-space: nowrap;
        }
    }
    ```

    **4. Section Conversion Rules:**

    **Executive Summary:**
    - Extract purpose, scope, and key opportunities for data cards
    - Convert bullet points to HTML lists with proper citation spans
    - Place success factors in section-highlight div
    - Place risks in risk-warning div

    **Product Overview:**
    - Extract product name and category for data cards
    - Convert value propositions to structured lists
    - Maintain all subsection structure from markdown

    **Target Organization:**
    - Extract company metrics (name, HQ, employees, revenue) for data cards
    - Convert stakeholder information to stakeholder-map grid
    - Create stakeholder-item divs for each person

    **Fit Analysis:**
    - Convert analysis tables to proper HTML tables with data-table class
    - Extract fit scores and evidence for table rows
    - Maintain cross-matrix structure

    **Competitive Landscape:**
    - Use competitive-grid for competitor layout
    - Create competitor-card divs with competitor-name and competitor-focus elements

    **Engagement Strategy:**
    - Convert messaging themes to structured lists by stakeholder group
    - Use timeline class for engagement sequence
    - Create timeline-item divs with timeline-marker and timeline-content

    **Risks & Red Flags:**
    - Use risk-matrix with appropriate risk-level classes (risk-high, risk-medium, risk-low)
    - Place detailed descriptions in risk-warning div

    **Action Plan:**
    - Maintain timeframe structure (Immediate, Medium-Term, Long-Term)
    - Convert to HTML lists with proper citations

    **5. Citation Processing:**
    - Convert markdown citation patterns [1], [2], [1,2] to `<span class="citation">[number]</span>`
    - Build references section with proper numbered list and links
    - Ensure all citation numbers in content match reference list

    **6. Responsive Design Features:**
    - Mobile-responsive grid layouts
    - Collapsing navigation for smaller screens  
    - Horizontal scroll for tables on mobile
    - Scalable typography and spacing

    **CRITICAL SUCCESS FACTORS:**
    - Complete HTML document with embedded CSS
    - Professional visual hierarchy and typography
    - Interactive elements (hover effects, smooth scrolling)
    - Proper semantic HTML structure for accessibility
    - Mobile-responsive design
    - All markdown content converted accurately
    - Citations properly formatted and linked

    Generate a complete, standalone HTML document that transforms the markdown report into a professional, interactive sales intelligence presentation.
    """,
    output_key="target_html",
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
        html_report_generator
    ],
)

# --- UPDATED MAIN AGENT ---
sales_intelligence_agent = LlmAgent(
    name="sales_intelligence_agent",
    model = config.worker_model,
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

# root_agent = sales_intelligence_agent