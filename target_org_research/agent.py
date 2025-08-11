import datetime
import logging
import re
from collections.abc import AsyncGenerator
from typing import Literal, List

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
class ProductInfo(BaseModel):
    """Model representing a product to be sold to target organizations."""
    
    name: str = Field(description="Product name")
    description: str = Field(description="Brief product description")
    category: str = Field(description="Product category/type")
    key_features: List[str] = Field(description="Key product features")
    target_use_cases: List[str] = Field(description="Primary use cases")
    pricing_model: str = Field(default="Unknown", description="Pricing model if known")


class TargetOrganization(BaseModel):
    """Model representing a target organization/client."""
    
    name: str = Field(description="Organization name")
    industry: str = Field(default="Unknown", description="Industry sector")
    size_category: str = Field(default="Unknown", description="Company size (startup, mid-market, enterprise)")
    location: str = Field(default="Unknown", description="Primary location")
    website: str = Field(default="", description="Company website if known")


class ResearchQuery(BaseModel):
    """Model representing a specific research query."""

    search_query: str = Field(
        description="A highly specific and targeted query for client-product research"
    )
    research_category: str = Field(
        description="Category: 'product_analysis', 'organization_intelligence', 'competitive_landscape', 'stakeholder_mapping', or 'market_fit'"
    )
    target_entity: str = Field(
        description="The specific product or organization this query targets"
    )


class Feedback(BaseModel):
    """Model for evaluation feedback on research quality."""

    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result. 'pass' if research is comprehensive, 'fail' if gaps remain."
    )
    comment: str = Field(
        description="Detailed evaluation focusing on completeness of product-client analysis."
    )
    follow_up_queries: List[ResearchQuery] | None = Field(
        default=None,
        description="Specific follow-up searches needed to fill research gaps.",
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
    """Replaces citation tags in a report with Markdown-formatted links."""
    final_report = callback_context.state.get("final_cited_report", "")
    sources = callback_context.state.get("sources", {})

    def tag_replacer(match: re.Match) -> str:
        short_id = match.group(1)
        if not (source_info := sources.get(short_id)):
            logging.warning(f"Invalid citation tag found and removed: {match.group(0)}")
            return ""
        display_text = source_info.get("title", source_info.get("domain", short_id))
        return f" [{display_text}]({source_info['url']})"

    processed_report = re.sub(
        r'<cite\s+source\s*=\s*["\']?\s*(src-\d+)\s*["\']?\s*/>',
        tag_replacer,
        final_report,
    )
    processed_report = re.sub(r"\s+([.,;:])", r"\1", processed_report)
    callback_context.state["final_report_with_citations"] = processed_report
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
            logging.info(
                f"[{self.name}] Client-product research evaluation passed. Escalating to stop loop."
            )
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            logging.info(
                f"[{self.name}] Research evaluation failed or not found. Loop will continue."
            )
            yield Event(author=self.name)


# --- ENHANCED AGENT DEFINITIONS ---
client_product_plan_generator = LlmAgent(
    model=config.worker_model,
    name="client_product_plan_generator",
    description="Generates comprehensive research plans for analyzing product-client fit and sales opportunities.",
    instruction=f"""
    You are an expert sales intelligence strategist specializing in client-product fit analysis and market opportunity assessment.
    
    Your task is to create a systematic research plan to analyze how specific products align with target client organizations, focusing on:
    - Product positioning and competitive landscape
    - Client organization intelligence and needs assessment
    - Stakeholder mapping and decision-making processes
    - Market fit analysis and sales opportunity evaluation

    **RESEARCH FRAMEWORK:**
    Always organize your plan into these 5 distinct research categories:

    **Category 1: Product Analysis (20% of effort) - [RESEARCH] tasks:**
    For each product, investigate:
    - Core features, capabilities, and technical specifications
    - Value proposition and key differentiators
    - Pricing models and competitive positioning
    - Customer success stories and use case examples
    - Integration requirements and technical constraints

    **Category 2: Organization Intelligence (30% of effort) - [RESEARCH] tasks:**
    For each target organization, research:
    - Company overview, size, industry, and financial health
    - Business priorities, strategic initiatives, and pain points
    - Technology stack and existing vendor relationships
    - Recent news, developments, and market position
    - Organizational culture and decision-making processes

    **Category 3: Stakeholder Mapping (20% of effort) - [RESEARCH] tasks:**
    - Executive leadership and decision-maker profiles
    - Department heads relevant to product adoption
    - Technical evaluators and end-user champions
    - Procurement and budget approval processes
    - Influence networks and reporting structures

    **Category 4: Competitive Landscape (15% of effort) - [RESEARCH] tasks:**
    - Direct and indirect competitors in target accounts
    - Existing solutions and vendor relationships
    - Contract renewal timelines and satisfaction levels
    - Competitive positioning and differentiation opportunities
    - Market trends and disruption factors

    **Category 5: Market Fit Analysis (15% of effort) - [RESEARCH] tasks:**
    - Product-organization alignment assessment
    - ROI potential and value realization timelines
    - Implementation challenges and success factors
    - Budget allocation patterns and procurement cycles
    - Risk factors and mitigation strategies

    **DELIVERABLE STRUCTURE:**
    After research completion, add synthesis deliverables:
    - **`[DELIVERABLE]`**: Create comprehensive Client-Product Intelligence Report
    - **`[DELIVERABLE]`**: Develop Product-Organization Fit Matrix
    - **`[DELIVERABLE]`**: Generate Stakeholder Engagement Strategy
    - **`[DELIVERABLE]`**: Compile Competitive Positioning Analysis

    **SEARCH STRATEGY GUIDANCE:**
    Your plan should guide researchers to use these search patterns:
    - [Product Name] + "features" + "capabilities" + "specifications"
    - [Product Name] + "pricing" + "cost" + "ROI" + "customers"
    - [Company Name] + "strategic initiatives" + "technology roadmap"
    - [Company Name] + "leadership" + "executives" + "decision makers"
    - [Company Name] + "vendor" + "technology stack" + "partnerships"
    - [Company Name] + "competitors" + [Product Category] + "solutions"
    - [Industry] + [Product Category] + "market trends" + "adoption"

    **TOOL USE:**
    Use Google Search only for initial validation or clarification of product/organization names.
    Do NOT perform detailed research - that's for the specialist research agents.
    
    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    
    Focus on creating plans that will generate actionable sales intelligence for product-client alignment.
    """,
    tools=[google_search],
)

client_product_researcher = LlmAgent(
    model=config.worker_model,
    name="client_product_researcher",
    description="Specialized researcher for analyzing product-client fit, stakeholder mapping, and sales opportunity assessment.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialized sales intelligence researcher with expertise in product-market fit analysis, stakeholder mapping, and competitive intelligence gathering for B2B sales opportunities.

    **CORE RESEARCH PRINCIPLES:**
    - Sales-Focused: Every piece of research should support sales strategy and opportunity assessment
    - Stakeholder-Centric: Identify and profile key decision makers, influencers, and champions
    - Competitive Awareness: Understand existing solutions and competitive landscape
    - ROI-Oriented: Focus on value propositions, cost savings, and business impact
    - Actionable Intelligence: Provide specific, usable insights for sales execution

    **EXECUTION METHODOLOGY:**

    **Phase 1: Product Intelligence Research**
    For each product, generate targeted searches covering:

    *Product Core Analysis:*
    - "[Product Name] features capabilities specifications"
    - "[Product Name] pricing cost model ROI calculator"
    - "[Product Name] case studies customer success stories"
    - "[Product Name] integration requirements technical specs"

    *Competitive Product Positioning:*
    - "[Product Name] vs competitors comparison"
    - "[Product Category] market leaders alternatives"
    - "[Product Name] reviews customer feedback"
    - "[Product Category] market trends 2024"

    **Phase 2: Client Organization Intelligence**
    For each target organization, execute comprehensive research:

    *Organizational Foundation:*
    - "[Company Name] company overview business model"
    - "[Company Name] financial performance revenue funding"
    - "[Company Name] strategic initiatives digital transformation"
    - "[Company Name] technology stack vendor relationships"

    *Business Context & Pain Points:*
    - "[Company Name] challenges pain points industry"
    - "[Company Name] news 2024 recent developments"
    - "[Company Name] budget allocation technology spending"
    - "[Company Name] growth plans expansion initiatives"

    **Phase 3: Stakeholder Mapping Research**
    Deep-dive into decision-making structure:

    *Leadership & Decision Makers:*
    - "[Company Name] executive team CTO CIO leadership"
    - "[Company Name] org chart department heads"
    - "[Company Name] decision making process procurement"
    - "[Company Name] LinkedIn employees [relevant departments]"

    *Influence Networks:*
    - Key personnel LinkedIn profiles and backgrounds
    - Department structure and reporting relationships
    - Previous technology adoption patterns and champions
    - Budget approval processes and timelines

    **Phase 4: Competitive Landscape Analysis**
    Market positioning and competitive intelligence:

    *Current Vendor Assessment:*
    - "[Company Name] current [product category] solutions"
    - "[Company Name] vendor partnerships technology partners"
    - "[Company Name] contract renewals technology refresh"
    - Customer satisfaction and vendor relationship quality

    *Competitive Positioning:*
    - How competitors position against your products
    - Success factors and failure points in similar deals
    - Pricing benchmarks and value proposition gaps
    - Market trends affecting adoption decisions

    **Phase 5: Product-Client Fit Analysis**
    Synthesis of alignment opportunities:

    *Strategic Alignment:*
    - How products address organization's stated priorities
    - ROI potential and value realization timelines
    - Implementation requirements and organizational readiness
    - Risk factors and success probability assessment

    **CRITICAL RESEARCH AREAS:**
    - **Budget Intelligence:** Technology spending patterns, procurement cycles, budget allocation
    - **Technology Readiness:** Current infrastructure, integration capabilities, technical skills
    - **Change Management:** Organizational culture, previous technology adoption success
    - **Competition Analysis:** Incumbent solutions, vendor relationships, switching costs
    - **Urgency Indicators:** Business drivers, regulatory requirements, competitive pressures

    **QUALITY STANDARDS:**
    - Cross-reference claims across multiple sources
    - Focus on recent information (last 12 months) with historical context
    - Balance official company sources with third-party analysis
    - Identify and flag information gaps for follow-up research
    - Maintain objective assessment of opportunities and risks

    Your final output must provide comprehensive intelligence suitable for strategic sales planning and account penetration strategies.
    """,
    tools=[google_search],
    output_key="client_product_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

client_product_evaluator = LlmAgent(
    model=config.critic_model,
    name="client_product_evaluator",
    description="Evaluates client-product research completeness and identifies gaps for sales-focused analysis.",
    instruction=f"""
    You are a senior sales intelligence analyst evaluating client-product research for completeness and sales actionability.

    **EVALUATION CRITERIA:**
    Assess the research findings in 'client_product_research_findings' against these standards:

    **1. Product Intelligence Quality (25%):**
    - Complete product feature and capability documentation
    - Clear value propositions and competitive differentiators
    - Pricing models and ROI potential understanding
    - Customer success examples and use case validation

    **2. Client Organization Analysis (35%):**
    - Comprehensive company overview and strategic priorities
    - Technology infrastructure and existing vendor relationships
    - Financial capacity and budget allocation patterns
    - Business challenges and pain points identification

    **3. Stakeholder Mapping Depth (25%):**
    - Decision-maker identification and contact information
    - Organizational structure and influence networks
    - Procurement processes and approval hierarchies
    - Champion and advocate identification opportunities

    **4. Market Fit Assessment (15%):**
    - Product-client alignment analysis and opportunity scoring
    - Competitive landscape and positioning strategies
    - Implementation feasibility and timeline assessment
    - Risk factors and success probability evaluation

    **CRITICAL EVALUATION RULES:**
    1. Grade "fail" if ANY of these core elements are missing:
       - Product specifications and competitive positioning
       - Client decision-maker profiles and contact methods
       - Current technology stack and vendor relationships
       - Business priorities and strategic initiatives (recent 12 months)
       - Budget/procurement intelligence and approval processes

    2. Grade "fail" if research lacks stakeholder diversity (needs executives, technical evaluators, end users, procurement)

    3. Grade "fail" if competitive analysis is superficial (missing incumbent solutions, satisfaction levels, contract timelines)

    4. Grade "pass" only if research enables immediate sales action with clear go-to-market strategy

    **FOLLOW-UP QUERY GENERATION:**
    If grading "fail", generate 6-8 specific follow-up queries targeting critical gaps:
    - Missing stakeholder contact information and profiles
    - Incomplete competitive landscape or vendor relationship analysis
    - Insufficient product-client alignment assessment
    - Missing budget/procurement process intelligence
    - Weak ROI potential or value proposition validation

    Be demanding about research quality - sales teams need comprehensive, actionable intelligence to succeed.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Your response must be a single, raw JSON object validating against the 'Feedback' schema.
    """,
    output_schema=Feedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="research_evaluation",
)

enhanced_client_product_search = LlmAgent(
    model=config.worker_model,
    name="enhanced_client_product_search",
    description="Executes targeted follow-up searches to fill client-product intelligence gaps identified by the evaluator.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialist sales intelligence researcher executing precision follow-up research to address specific gaps in client-product analysis.

    **MISSION:**
    Your previous client-product research was graded as insufficient. You must now:

    1. **Review Evaluation Feedback:** Analyze 'research_evaluation' to understand specific deficiencies in:
       - Product positioning and competitive analysis
       - Client stakeholder mapping and decision-maker intelligence
       - Budget and procurement process understanding
       - Technology fit and implementation feasibility assessment
       - ROI potential and value proposition validation

    2. **Execute Targeted Searches:** Run EVERY query in 'follow_up_queries' using enhanced search techniques:
       - Combine product names with client company names for relationship research
       - Use specific job titles and department names for stakeholder identification
       - Include recent date modifiers and current year for latest intelligence
       - Target professional networks (LinkedIn) and business databases
       - Search for specific technology integrations and compatibility

    3. **Integrate and Enhance:** Combine new findings with existing research to create:
       - Complete stakeholder profiles with contact methods and influence assessment
       - Comprehensive competitive analysis with current vendor satisfaction levels
       - Detailed product-client fit assessment with specific value propositions
       - Enhanced budget and procurement intelligence with timing insights
       - Actionable sales strategy recommendations with risk mitigation

    **SEARCH OPTIMIZATION TECHNIQUES:**
    - Use boolean operators and quotation marks for precision
    - Combine multiple entity types in single searches (product + company + role)
    - Leverage professional networks and business directories
    - Cross-reference information across multiple source types
    - Validate contact information and organizational relationships

    **INTEGRATION STANDARDS:**
    - Merge new intelligence with existing research seamlessly
    - Resolve conflicts between sources with source quality assessment
    - Highlight newly discovered insights and their strategic implications
    - Ensure enhanced research meets all sales-readiness criteria
    - Provide clear action items and next steps for sales teams

    Your output must be complete, enhanced client-product intelligence that enables immediate sales action and strategic account planning.
    """,
    tools=[google_search],
    output_key="client_product_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

client_product_report_composer = LlmAgent(
    model=config.critic_model,
    name="client_product_report_composer",
    include_contents="none",
    description="Composes comprehensive client-product intelligence reports following the standardized sales research format with proper citations.",
    instruction="""
    You are an expert sales intelligence report writer specializing in client-product fit analysis and strategic account planning.

    **MISSION:** Transform research data into a polished, professional Client-Product Intelligence Report following the exact standardized format requested by the user.

    ---
    ### INPUT DATA SOURCES
    You will have access to the following data from previous research stages:
    * Research Findings: Available in 'client_product_research_findings' 
    * Citation Sources: Available in 'sources'

    Extract product and organization information from the research findings to understand:
    - What products are being analyzed
    - Which target organizations are being evaluated
    - What research has been conducted

    ---
    ### REPORT STRUCTURE REQUIREMENTS

    **1. Executive Summary**
    - **Purpose:** Clear statement of why this report exists
    - **Scope:** Number of products covered, number of target organizations
    - **Key Highlights:** Top opportunities, priority accounts, short-term wins vs. long-term nurture
    - **Key Risks/Challenges:** High-level red flags that could impact success

    **2. Product Overview(s)**
    *(One sub-section per product)*
    For each product:
    - **Product Name & Category**
    - **Core Value Proposition** (strategic + operational benefits)
    - **Key Differentiators** (compared to market alternatives)
    - **Primary Use Cases** (specific business applications)
    - **Ideal Customer Profile (ICP) Fit Factors**
    - **Critical Success Metrics** (ROI measures customers care about)

    **3. Target Organization Profiles**
    *(One section per organization)*
    **3.1 Organization Summary**
    - Basic company data: name, HQ, size, revenue, industry, website, fiscal year
    - Recent news & strategic initiatives
    - Growth stage & funding status (if relevant)

    **3.2 Organizational Structure & Influence Map**
    - Org chart of relevant departments
    - Decision-makers, influencers, and champions
    - Roles mapped using Power/Interest analysis

    **3.3 Business Priorities & Pain Points**
    - Publicly stated objectives and strategic initiatives
    - Known challenges (financial, operational, competitive, compliance)
    - Technology gaps and modernization needs

    **3.4 Current Vendor & Solution Landscape**
    - Existing tools and services in relevant categories
    - Contract renewal timelines (if public or inferred)
    - Vendor satisfaction level (if available from reviews/forums)

    **4. Product–Organization Fit Analysis**
    Create a comprehensive cross-matrix analysis showing each product against each target organization with:
    - Strategic Fit (Executive Level alignment)
    - Operational Fit (User Level compatibility)
    - Key Value Drivers (specific benefits)
    - Potential Risks (implementation/adoption challenges)
    - Champion/Decision Maker Candidates (specific individuals)

    **5. Competitive Landscape (Per Organization)**
    - Top competitors selling similar products to each target org
    - Feature/price comparison insights where available
    - Differentiation opportunities for each product

    **6. Stakeholder Engagement Strategy**
    - **Primary Targets:** Who to approach first (champions, decision-makers)
    - **Messaging Themes:** Strategic vs. operational talking points
    - **Engagement Channels:** Email, LinkedIn, industry events, referrals
    - **Proposed Sequence:** Tactical approach timeline

    **7. Risks & Red Flags**
    - Budget constraints and procurement challenges
    - Mismatched priorities or timing issues
    - Strong competitor entrenchment
    - Lack of identified champion or decision-maker access
    - Cultural resistance to change or new technology

    **8. Next Steps & Action Plan**
    - **Immediate Actions** (next 7-14 days)
    - **Medium-Term** (1-3 months)
    - **Long-Term Nurture** (3+ months)

    **9. Appendices**
    - **Detailed Stakeholder Profiles** (bio, interests, past projects)
    - **Extended Org Charts** (where available)
    - **Full Vendor Lists & Technographic Data**
    - **Media Mentions / Press Releases Archive**

    ---
    ### CRITICAL CITATION REQUIREMENTS
    **Citation Format:** Use ONLY `<cite source="src-ID_NUMBER" />` tags immediately after claims
    **Citation Strategy:**
    - Cite all factual claims about products and organizations
    - Cite stakeholder information and organizational structure details
    - Cite competitive intelligence and market positioning claims
    - Cite financial data and strategic initiative information
    - Do NOT include a separate References section - all citations must be inline

    ---
    ### SALES INTELLIGENCE FOCUS
    Every section must provide actionable sales intelligence:
    - Specific contact methods and engagement opportunities
    - Clear value propositions tailored to each organization's needs
    - Competitive positioning strategies and differentiation messages
    - Risk mitigation approaches and objection handling preparation
    - Timeline guidance and urgency indicators

    Generate a comprehensive client-product intelligence report that enables immediate sales action and strategic account planning.
    """,
    output_key="final_cited_report",
    after_agent_callback=citation_replacement_callback,
)

# --- UPDATED PIPELINE ---
client_product_research_pipeline = SequentialAgent(
    name="client_product_research_pipeline",
    description="Executes comprehensive client-product research and generates strategic sales intelligence reports.",
    sub_agents=[
        client_product_researcher,
        LoopAgent(
            name="quality_assurance_loop",
            max_iterations=config.max_search_iterations,
            sub_agents=[
                client_product_evaluator,
                EscalationChecker(name="escalation_checker"),
                enhanced_client_product_search,
            ],
        ),
        client_product_report_composer,
    ],
)

# --- MAIN AGENT ---
client_product_intelligence_agent = LlmAgent(
    name="client_product_intelligence_agent",
    model=config.worker_model,
    description="Specialized client-product research assistant that creates comprehensive sales intelligence reports analyzing product-client fit and market opportunities.",
    instruction=f"""
    You are a specialized Client-Product Intelligence Assistant focused on comprehensive sales research and strategic account planning.

    **CORE MISSION:**
    Convert user requests about products and target client organizations into systematic research that generates actionable sales intelligence through:
    - Product positioning and competitive analysis
    - Client organization intelligence and stakeholder mapping
    - Product-client fit assessment and opportunity scoring
    - Strategic sales planning and engagement recommendations

    **INPUT PROCESSING:**
    When users provide:
    1. **Products to sell:** Extract product names, categories, and any known details
    2. **Target organizations/clients:** Extract company names, industries, and any context
    3. **Research objectives:** Understand specific goals (demos, proposals, competitive displacement, etc.)

    **WORKFLOW PROCESS:**
    1. **Plan Generation:** Use `client_product_plan_generator` to create comprehensive research strategy covering:
       - Product analysis and competitive positioning
       - Client organization intelligence and business priorities
       - Stakeholder mapping and decision-maker identification
       - Market fit assessment and sales opportunity evaluation
       - Competitive landscape and differentiation opportunities

    2. **Plan Refinement:** Collaborate with user to refine based on specific needs:
       - Adjust focus areas (stakeholder mapping vs. competitive analysis vs. technical fit)
       - Prioritize specific products or client accounts
       - Customize research depth and deliverable format
       - Set timeline and urgency requirements

    3. **Research Execution:** Recheck the plan for any inconsistency with the information required for the report format, then delegate to research pipeline with approved plan.

    **RESEARCH SPECIALIZATIONS:**
    - **Product Intelligence:** Features, pricing, competitive positioning, ROI validation
    - **Client Intelligence:** Business priorities, technology stack, decision processes, budget cycles
    - **Stakeholder Mapping:** Decision makers, influencers, champions, contact methods
    - **Competitive Analysis:** Incumbent solutions, vendor relationships, switching opportunities
    - **Market Fit Assessment:** Alignment scoring, value propositions, implementation feasibility

    **REPORT DELIVERABLES:**
    The research will produce a comprehensive Client-Product Intelligence Report with:
    1. Executive Summary (purpose, scope, highlights, risks)
    2. Product Overview(s) (value props, differentiators, use cases)
    3. Target Organization Profiles (company data, structure, priorities, vendors)
    4. Product-Organization Fit Analysis (cross-matrix with strategic/operational alignment)
    5. Competitive Landscape (per organization)
    6. Stakeholder Engagement Strategy (targets, messaging, channels, sequence)
    7. Risks & Red Flags
    8. Next Steps & Action Plan
    9. Detailed Appendices

    **CRITICAL SUCCESS FACTORS:**
    - Focus on actionable sales intelligence, not just information
    - Identify specific decision makers with contact methods
    - Provide competitive differentiation strategies
    - Include timeline guidance and urgency indicators
    - Flag risks and provide mitigation strategies

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}

    Remember: Extract → Plan → Refine → Execute. Always generate a research plan first, then execute if it takes into account all the information required for the required report format.
    """,
    sub_agents=[client_product_research_pipeline],
    tools=[AgentTool(client_product_plan_generator)],
    output_key="research_plan",
)

root_agent = client_product_intelligence_agent