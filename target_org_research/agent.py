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
class SalesSearchQuery(BaseModel):
    """Model representing a specific search query for sales intelligence research."""

    search_query: str = Field(
        description="A targeted query for sales intelligence, focusing on target organization analysis, competitive landscape, and product-market fit opportunities."
    )
    research_focus: str = Field(
        description="The focus area: 'target_analysis', 'competitive_intelligence', 'product_fit', 'stakeholder_mapping', or 'sales_strategy'"
    )


class SalesFeedback(BaseModel):
    """Model for evaluating sales intelligence research quality."""

    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result. 'pass' if sales intelligence is comprehensive, 'fail' if critical gaps exist."
    )
    comment: str = Field(
        description="Detailed evaluation focusing on target organization analysis depth, competitive positioning clarity, and actionable sales insights."
    )
    follow_up_queries: list[SalesSearchQuery] | None = Field(
        default=None,
        description="Specific follow-up searches to fill sales intelligence gaps, focusing on missing competitive data, stakeholder information, or product-market fit insights.",
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
class SalesEscalationChecker(BaseAgent):
    """Checks sales intelligence evaluation and escalates to stop the loop if grade is 'pass'."""

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        evaluation_result = ctx.session.state.get("sales_evaluation")
        if evaluation_result and evaluation_result.get("grade") == "pass":
            logging.info(
                f"[{self.name}] Sales intelligence evaluation passed. Escalating to stop loop."
            )
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            logging.info(
                f"[{self.name}] Sales intelligence evaluation failed or not found. Loop will continue."
            )
            yield Event(author=self.name)


# --- SALES INTELLIGENCE AGENT DEFINITIONS ---
sales_plan_generator = LlmAgent(
    model=config.worker_model,
    name="sales_plan_generator",
    description="Generates comprehensive sales intelligence research plans that analyze target organizations in the context of the user's specific product/service offering.",
    instruction=f"""
    You are an expert sales intelligence strategist specializing in product-market fit analysis and competitive positioning research.
    
    The user will provide:
    1. Target organization name(s) for prospecting
    2. Description of their product/service offering
    3. Their company information and value proposition
    
    Your task is to create a systematic sales intelligence research plan that analyzes the target organizations specifically through the lens of how the user's product/service can solve their problems and compete against existing alternatives.

    **SALES INTELLIGENCE RESEARCH PHASES:**

    **Phase 1: Target Organization Deep Dive (25% of effort) - [RESEARCH] tasks:**
    - Analyze target company's business model, revenue streams, and operational challenges
    - Research current technology stack, tools, and vendor relationships
    - Identify pain points, inefficiencies, and growth initiatives that create opportunities
    - Map organizational structure, departments, and decision-making processes
    - Investigate recent changes, expansions, or strategic initiatives

    **Phase 2: Competitive Landscape Analysis (25% of effort) - [RESEARCH] tasks:**
    - Identify existing solutions/vendors the target already uses in your product category
    - Research competitor strengths, weaknesses, pricing, and market positioning
    - Analyze target's satisfaction with current solutions (reviews, feedback, contracts)
    - Find gaps in current solutions that your product could fill
    - Research alternative solutions they might be considering

    **Phase 3: Stakeholder & Decision-Maker Intelligence (25% of effort) - [RESEARCH] tasks:**
    - Identify key decision-makers, influencers, and budget holders
    - Research individual backgrounds, priorities, and professional interests
    - Map reporting structures and decision-making processes
    - Find shared connections, common interests, or warm introduction paths
    - Analyze communication preferences and engagement patterns

    **Phase 4: Sales Strategy & Positioning (25% of effort) - [RESEARCH] tasks:**
    - Research target's budget cycles, procurement processes, and buying patterns
    - Identify timing indicators, trigger events, and opportunity windows
    - Analyze their vendor selection criteria and preferred partner characteristics
    - Research their success metrics, KPIs, and performance challenges
    - Find case studies of similar companies that adopted solutions like yours

    **DELIVERABLE SYNTHESIS:**
    After research phases, create these strategic deliverables:
    - **`[DELIVERABLE]`**: Generate comprehensive Target Organization Sales Intelligence Profile
    - **`[DELIVERABLE]`**: Develop Product-Market Fit Analysis and Value Proposition Mapping
    - **`[DELIVERABLE]`**: Create Competitive Positioning Strategy against current solutions
    - **`[DELIVERABLE]`**: Compile Stakeholder Engagement Plan and Messaging Framework
    - **`[DELIVERABLE]`**: Design Sales Approach Timeline and Tactical Recommendations

    **SEARCH STRATEGY GUIDANCE:**
    Your plan should guide searches for:
    - Target company + your product category + "current solutions" + "vendors"
    - Target company + "challenges" + "pain points" + relevant business area
    - Target company + "decision makers" + relevant department/function
    - Target company + competitor names + "partnership" + "contract"
    - Target company + "budget" + "procurement" + "vendor selection"
    - Key stakeholder names + professional background + priorities
    - Similar companies + your product category + "case study" + "success story"
    - Target company + "technology stack" + "tools" + "integration"

    **TOOL USE:**
    Only use Google Search for initial validation if target organization or product category needs clarification.
    Do NOT conduct the actual research - that's for the specialist researcher.
    
    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    
    Focus on creating plans that generate actionable sales intelligence for winning deals against competitive alternatives.
    """,
    tools=[google_search],
)

sales_section_planner = LlmAgent(
    model=config.worker_model,
    name="sales_section_planner",
    description="Creates structured sales intelligence report outline focused on product-market fit analysis and competitive positioning.",
    instruction="""
    You are an expert sales strategy report architect. Using the sales intelligence research plan and the user's product/service context, create a structured markdown outline for a comprehensive Sales Intelligence & Competitive Positioning Report.

    Your outline must include these core sections for actionable sales intelligence:

    # 1. Executive Summary
    - Target Organization Overview and Key Metrics
    - Product-Market Fit Assessment Summary
    - Primary Competitive Threats and Opportunities
    - Recommended Sales Approach and Timeline
    - Expected Deal Size and Probability Assessment

    # 2. Target Organization Analysis
    - Business Model and Revenue Drivers
    - Current Operational Challenges and Pain Points
    - Technology Infrastructure and Vendor Ecosystem
    - Growth Initiatives and Strategic Priorities
    - Organizational Structure and Department Dynamics

    # 3. Current Solution Landscape
    - Existing Vendors and Tool Stack in Your Category
    - Current Solution Performance and Satisfaction Levels
    - Contract Status and Renewal Timelines
    - Identified Gaps and Unmet Needs
    - Budget Allocation and Spending Patterns

    # 4. Competitive Positioning Analysis
    - Direct Competitors Already Serving Target
    - Competitive Strengths vs. Your Product Advantages
    - Pricing Comparison and Value Differentiation
    - Feature Gap Analysis and Unique Selling Points
    - Competitive Displacement Strategy

    # 5. Stakeholder Intelligence
    - Key Decision-Makers and Influencer Mapping
    - Individual Background and Professional Priorities
    - Decision-Making Process and Approval Hierarchy
    - Communication Preferences and Engagement Patterns
    - Shared Connections and Warm Introduction Opportunities

    # 6. Product-Market Fit Assessment
    - Alignment Between Your Solution and Target's Needs
    - ROI Potential and Value Creation Opportunities
    - Implementation Feasibility and Integration Requirements
    - Success Metrics and Performance Improvement Potential
    - Risk Factors and Adoption Barriers

    # 7. Sales Opportunity Analysis
    - Buying Signals and Trigger Events
    - Budget Availability and Procurement Processes
    - Timeline Indicators and Decision Windows
    - Competitive Threats and Urgency Factors
    - Deal Size Estimation and Revenue Potential

    # 8. Messaging & Value Proposition Strategy
    - Customized Value Propositions for Key Stakeholders
    - Pain Point-Specific Messaging Framework
    - Competitive Differentiation Talking Points
    - ROI and Business Case Messaging
    - Risk Mitigation and Trust-Building Messages

    # 9. Engagement Strategy & Tactics
    - Optimal Outreach Timing and Sequencing
    - Preferred Communication Channels and Methods
    - Content Strategy and Resource Requirements
    - Demonstration and Proof-of-Concept Approach
    - Relationship-Building and Trust Development Plan

    # 10. Implementation Roadmap
    - Immediate Action Items and Next Steps
    - 30-60-90 Day Engagement Timeline
    - Resource Requirements and Team Coordination
    - Success Metrics and Progress Tracking
    - Contingency Planning for Common Objections

    # 11. Risk Assessment & Mitigation
    - Competitive Threats and Counter-Strategies
    - Internal Resistance and Change Management Issues
    - Technical Integration and Implementation Risks
    - Budget and Timing Risks
    - Relationship and Political Risks

    Ensure your outline enables comprehensive sales intelligence that directly supports deal-winning strategies and competitive positioning.
    Do not include a separate References section - citations will be inline.
    """,
    output_key="sales_report_sections",
)

sales_intelligence_researcher = LlmAgent(
    model=config.worker_model,
    name="sales_intelligence_researcher",
    description="Specialized sales intelligence researcher that analyzes target organizations through the lens of specific product-market fit and competitive positioning.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialized sales intelligence researcher with expertise in competitive analysis, stakeholder mapping, and product-market fit assessment.

    **CONTEXT AWARENESS:**
    You have access to:
    - Target organization name(s) to research
    - User's product/service description and capabilities
    - User's company information and competitive positioning

    **CORE RESEARCH MISSION:**
    Analyze target organizations specifically to determine:
    1. How your user's product/service aligns with target's needs and challenges
    2. What competitive solutions currently exist in the target organization
    3. Who the key decision-makers are and how to reach them
    4. What messaging and approach will be most effective for winning the deal

    **SALES INTELLIGENCE METHODOLOGY:**

    **Phase 1: Target Organization Deep Dive**
    For each target organization research goal, execute comprehensive searches:

    *Business Model & Pain Point Analysis:*
    - "[Target Company] business model revenue challenges"
    - "[Target Company] operational inefficiencies pain points"
    - "[Target Company] growth initiatives strategic priorities 2024"
    - "[Target Company] [relevant business area] challenges problems"

    *Technology & Vendor Ecosystem:*
    - "[Target Company] technology stack tools vendors"
    - "[Target Company] [your product category] current solutions"
    - "[Target Company] software partnerships integrations"
    - "[Target Company] IT infrastructure digital transformation"

    *Organizational Intelligence:*
    - "[Target Company] organizational chart department structure"
    - "[Target Company] [relevant department] team leadership"
    - "[Target Company] decision making process procurement"
    - "[Target Company] budget allocation [relevant category]"

    **Phase 2: Competitive Landscape Analysis**

    *Current Solution Research:*
    - "[Target Company] + [competitor names] partnership contract"
    - "[Target Company] [current vendor] satisfaction reviews"
    - "[Target Company] [product category] vendor evaluation RFP"
    - "[Target Company] + [your product category] + problems issues"

    *Competitive Intelligence:*
    - "[Competitor names] vs [your company] comparison"
    - "[Target Company] [competitor] implementation case study"
    - "[Competitor] pricing model contract terms"
    - "[Target Company] vendor switching [product category]"

    **Phase 3: Stakeholder & Decision-Maker Intelligence**

    *Key Personnel Research:*
    - "[Decision maker names] [Target Company] LinkedIn background"
    - "[Target Company] [relevant department] director manager"
    - "[Key stakeholder] professional interests priorities"
    - "[Target Company] procurement team vendor relations"

    *Relationship Mapping:*
    - "[Your company] [Target Company] shared connections"
    - "[Key stakeholder] professional network associations"
    - "[Target Company] industry conference events attendance"
    - "[Decision maker] social media activity LinkedIn posts"

    **Phase 4: Sales Strategy Research**

    *Buying Process Intelligence:*
    - "[Target Company] procurement process vendor selection"
    - "[Target Company] budget cycle Q1 Q2 Q3 Q4 spending"
    - "[Target Company] RFP process vendor requirements"
    - "[Target Company] contract negotiation approval process"

    *Opportunity Indicators:*
    - "[Target Company] expansion hiring [relevant department]"
    - "[Target Company] funding growth investment 2024"
    - "[Target Company] [pain point keywords] urgent needs"
    - "[Target Company] [trigger events] initiative launch"

    *Success Pattern Research:*
    - "companies like [Target Company] [your product] success story"
    - "[Target Company] similar size industry [your solution] ROI"
    - "[Your product category] [Target Company industry] case studies"
    - "[Target Company] competitors [your solution] implementation"

    **COMPETITIVE FOCUS AREAS:**
    - **Solution Gap Analysis:** What problems does the target have that current vendors don't solve?
    - **Vendor Satisfaction:** How happy is the target with current solutions? (reviews, complaints, contract renewals)
    - **Switching Costs:** What barriers exist to changing from current solutions?
    - **Decision Criteria:** What factors does the target prioritize in vendor selection?
    - **Differentiation Opportunities:** Where does your solution uniquely excel vs. competitors?

    **STAKEHOLDER INTELLIGENCE PRIORITIES:**
    - **Decision Authority:** Who has budget authority and final approval power?
    - **Influence Network:** Who influences the decision-makers?
    - **Pain Ownership:** Who feels the pain that your solution solves most acutely?
    - **Champion Potential:** Who could become an internal advocate for your solution?
    - **Relationship Access:** How can you reach key stakeholders (warm introductions, events, content)?

    **SALES OPPORTUNITY INDICATORS:**
    - **Timing Signals:** Budget cycles, contract renewals, strategic initiatives, expansion plans
    - **Urgency Drivers:** Competitive pressure, regulatory requirements, performance gaps
    - **Budget Availability:** Recent funding, growing teams, new initiatives, vendor spending
    - **Change Readiness:** New leadership, transformation projects, technology modernization

    **Phase 5: Synthesis & Strategic Analysis**
    After completing all research goals, synthesize findings into actionable sales intelligence:
    - Map user's product capabilities to target's specific needs and challenges
    - Identify key competitive differentiation points and messaging angles  
    - Create stakeholder-specific value propositions and engagement strategies
    - Develop timeline-based approach recommendations with specific tactics
    - Highlight highest-probability opportunities and potential obstacles

    Your final output must provide comprehensive, actionable intelligence that enables winning sales strategies against competitive alternatives.
    """,
    tools=[google_search],
    output_key="sales_intelligence_findings",
    after_agent_callback=collect_research_sources_callback,
)

sales_intelligence_evaluator = LlmAgent(
    model=config.critic_model,
    name="sales_intelligence_evaluator",
    description="Evaluates sales intelligence research for completeness and actionability in competitive sales situations.",
    instruction=f"""
    You are a senior sales strategy analyst evaluating sales intelligence research for deal-winning completeness and competitive positioning effectiveness.

    **EVALUATION CRITERIA:**
    Assess the research findings in 'sales_intelligence_findings' against these critical sales intelligence standards:

    **1. Target Organization Analysis Quality (25%):**
    - Business model, pain points, and operational challenges clearly identified
    - Current technology stack and vendor relationships mapped comprehensively
    - Organizational structure and decision-making processes documented
    - Growth initiatives and strategic priorities that create opportunities identified
    - Budget cycles, procurement processes, and buying patterns analyzed

    **2. Competitive Intelligence Depth (30%):**
    - Existing solutions and vendors in target organization identified and analyzed
    - Competitor strengths, weaknesses, and positioning clearly documented
    - Current solution satisfaction levels and performance gaps identified
    - Contract terms, renewal dates, and switching costs analyzed
    - Competitive differentiation opportunities and unique value props defined

    **3. Stakeholder Intelligence Completeness (25%):**
    - Key decision-makers, influencers, and budget holders identified with contact info
    - Individual backgrounds, priorities, and professional interests researched
    - Decision-making process, approval hierarchy, and influence network mapped
    - Communication preferences and engagement patterns documented
    - Shared connections and warm introduction paths identified

    **4. Sales Strategy Actionability (20%):**
    - Specific product-market fit assessment with ROI potential quantified
    - Customized value propositions for different stakeholder personas
    - Timing indicators, trigger events, and optimal engagement windows identified
    - Messaging frameworks that address specific pain points and competitive concerns
    - Tactical recommendations with concrete next steps and success metrics

    **CRITICAL FAILURE CONDITIONS:**
    Grade "fail" if ANY of these essential elements are missing or insufficient:

    **Target Analysis Gaps:**
    - Current vendor/solution identification in user's product category
    - Key decision-maker identification and contact information
    - Specific pain points that user's product addresses
    - Budget/procurement process understanding

    **Competitive Intelligence Gaps:**
    - Missing analysis of key competitors already serving the target
    - Lack of differentiation strategy against existing solutions
    - No insight into current solution satisfaction or contract status
    - Missing pricing or value comparison framework

    **Stakeholder Intelligence Gaps:**
    - Key decision-makers not identified or inadequately researched
    - No insight into decision-making process or approval requirements
    - Missing communication preferences or engagement strategies
    - No relationship mapping or warm introduction opportunities

    **Strategic Actionability Gaps:**
    - No clear product-market fit assessment or value quantification
    - Generic messaging without stakeholder-specific customization
    - Missing timing strategy or optimal engagement windows
    - No concrete tactical recommendations or next steps

    **FOLLOW-UP QUERY GENERATION:**
    If grading "fail", generate 5-7 targeted follow-up queries addressing the most critical gaps:
    - Focus on missing competitive intelligence about existing vendors
    - Target specific stakeholder identification and background research
    - Seek deeper product-market fit and value proposition insights
    - Find tactical intelligence about timing, budgets, and decision processes

    **SUCCESS STANDARDS:**
    Grade "pass" only if the research provides:
    - Comprehensive competitive landscape with clear differentiation strategy
    - Actionable stakeholder intelligence with specific engagement approaches
    - Quantified product-market fit assessment with ROI projections
    - Tactical sales strategy with timeline and concrete next steps

    Be demanding about research quality - winning competitive sales requires deep, actionable intelligence that goes far beyond basic company information.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Your response must be a single, raw JSON object validating against the 'SalesFeedback' schema.
    """,
    output_schema=SalesFeedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="sales_evaluation",
)

enhanced_sales_intelligence_search = LlmAgent(
    model=config.worker_model,
    name="enhanced_sales_intelligence_search",
    description="Executes precision follow-up searches to fill critical sales intelligence gaps identified by the evaluator.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialist sales intelligence researcher executing targeted follow-up research to address critical gaps in competitive positioning and deal-winning intelligence.

    **MISSION:**
    Your previous sales intelligence research was graded as insufficient for winning competitive deals. You must now execute precision searches to fill these specific gaps:

    1. **Review Sales Evaluation:** Analyze 'sales_evaluation' to understand deficiencies in:
       - Competitive landscape analysis and existing vendor identification
       - Stakeholder intelligence and decision-maker mapping
       - Product-market fit assessment and value quantification
       - Tactical sales strategy and engagement recommendations

    2. **Execute Precision Follow-Up Searches:** Run EVERY query in 'follow_up_queries' with enhanced techniques:

    **Enhanced Competitive Intelligence Searches:**
    - "[Target Company] [specific competitor names] current contract partnership"
    - "[Target Company] [product category] vendor evaluation RFP requirements"
    - "[Target Company] + [competitor] + satisfaction problems issues complaints"
    - "[Target Company] technology budget [product category] spending allocation"
    - "[Target Company] [current solution] integration challenges limitations"

    **Deep Stakeholder Intelligence Searches:**
    - "[Specific decision maker names] [Target Company] LinkedIn contact information"
    - "[Target Company] [department] organizational chart reporting structure"
    - "[Key stakeholder] professional background career priorities goals"
    - "[Target Company] procurement team vendor selection criteria process"
    - "[Decision maker] social media activity professional interests LinkedIn posts"

    **Enhanced Product-Market Fit Searches:**
    - "[Target Company] [specific pain points] urgent needs 2024"
    - "[Target Company] [user's product category] ROI value case studies"
    - "companies like [Target Company] [user's solution] success implementation"
    - "[Target Company] industry [user's product] competitive advantage benefits"
    - "[Target Company] [current challenges] [user's solution] potential impact"

    **Tactical Sales Intelligence Searches:**
    - "[Target Company] budget cycle Q1 Q2 Q3 Q4 vendor spending patterns"
    - "[Target Company] [trigger events] expansion initiatives new projects"
    - "[Target Company] vendor partnership announcement [product category]"
    - "[Target Company] conference attendance events [relevant industry]"
    - "[User's company] [Target Company] shared connections mutual contacts"

    3. **Integrate Enhanced Intelligence:** Combine new findings with existing 'sales_intelligence_findings' to create:
       - More complete competitive landscape with specific vendor details
       - Enhanced stakeholder profiles with actionable contact and engagement strategies
       - Quantified product-market fit assessment with specific ROI projections
       - Tactical sales approach with concrete timelines and next steps

    **INTEGRATION PRIORITIES:**
    - **Competitive Focus:** Ensure comprehensive analysis of existing solutions and clear differentiation strategy
    - **Stakeholder Depth:** Provide actionable intelligence on key decision-makers with specific engagement approaches
    - **Value Quantification:** Include specific ROI potential and business case elements
    - **Tactical Clarity:** Offer concrete next steps with timing and success metrics

    **SEARCH OPTIMIZATION TECHNIQUES:**
    - Use exact company names and decision-maker names for precision
    - Combine multiple search terms to find specific competitive intelligence
    - Target industry-specific publications and vendor announcement platforms
    - Search for case studies and success stories in similar organizations
    - Look for recent news, press releases, and partnership announcements

    Your output must be the complete, enhanced sales intelligence findings that provide all necessary information for winning competitive sales situations.
    """,
    tools=[google_search],
    output_key="sales_intelligence_findings",
    after_agent_callback=collect_research_sources_callback,
)

sales_intelligence_report_composer = LlmAgent(
    model=config.critic_model,
    name="sales_intelligence_report_composer",
    include_contents="none",
    description="Composes comprehensive sales intelligence reports focused on competitive positioning, product-market fit, and actionable deal-winning strategies.",
    instruction="""
    You are an expert sales strategy report writer specializing in competitive intelligence and product-market fit analysis for B2B sales teams.

    **MISSION:** Transform sales research data into a polished, actionable Sales Intelligence & Competitive Positioning Report that enables winning deals against competitive alternatives.

    ---
    ### INPUT DATA SOURCES
    * Research Plan: `{sales_research_plan}`
    * Sales Intelligence Findings: `{sales_intelligence_findings}`
    * Citation Sources: `{sources}`
    * Report Structure: `{sales_report_sections}`
    * User's Product/Service Context: Available in research plan and findings

    ---
    ### SALES INTELLIGENCE REPORT STANDARDS

    **1. Competitive Focus:**
    - **Current State Analysis:** Clearly identify existing vendors and solutions in target organization
    - **Gap Analysis:** Highlight specific problems current solutions don't address
    - **Differentiation Strategy:** Define unique value propositions vs. each major competitor
    - **Displacement Tactics:** Provide specific strategies for competing against existing vendors
    - **Competitive Threats:** Address potential competitive responses and counter-strategies

    **2. Stakeholder-Centric Approach:**
    - **Decision-Maker Profiles:** Detailed backgrounds, priorities, and communication preferences
    - **Influence Mapping:** Show reporting relationships and decision-making dynamics
    - **Persona-Specific Messaging:** Customized value propositions for each key stakeholder
    - **Engagement Strategy:** Specific tactics for reaching and influencing each stakeholder
    - **Relationship Building:** Identify shared connections and warm introduction opportunities

    **3. Product-Market Fit Quantification:**
    - **Needs Assessment:** Map user's product capabilities to target's specific challenges
    - **ROI Projections:** Quantify potential value and business impact where possible
    - **Implementation Feasibility:** Address integration requirements and adoption barriers
    - **Success Metrics:** Define measurable outcomes and performance improvements
    - **Business Case Framework:** Provide elements for building compelling ROI arguments

    **4. Tactical Sales Intelligence:**
    - **Timing Strategy:** Identify optimal engagement windows and trigger events
    - **Budget Intelligence:** Document spending patterns, approval processes, and budget availability
    - **Procurement Process:** Detail vendor selection criteria and decision-making steps
    - **Risk Mitigation:** Address potential objections and adoption barriers
    - **Success Milestones:** Define progress markers and deal advancement indicators

    **5. Actionable Recommendations:**
    Each section must conclude with specific, actionable insights:
    - **Executive Summary:** Key talking points and primary competitive advantages
    - **Target Analysis:** Specific pain points to emphasize and business drivers to leverage
    - **Competitive Positioning:** Exact messaging to differentiate from current solutions
    - **Stakeholder Intelligence:** Specific outreach tactics and messaging for each decision-maker
    - **Sales Strategy:** Concrete next steps with timelines and success metrics

    ---
    ### REPORT QUALITY STANDARDS

    **Competitive Intelligence Quality:**
    - Identify at least 2-3 existing vendors/solutions in the target organization
    - Provide specific differentiation points vs. each major competitor
    - Include contract status, satisfaction levels, and switching cost analysis
    - Offer concrete strategies for competitive displacement

    **Stakeholder Intelligence Depth:**
    - Identify 3-5 key decision-makers with background and contact information
    - Map decision-making process and approval hierarchy
    - Provide personalized messaging and engagement strategies
    - Include relationship mapping and warm introduction opportunities

    **Product-Market Fit Assessment:**
    - Quantify value potential with specific ROI projections where possible
    - Address implementation requirements and integration challenges
    - Provide success metrics and performance improvement potential
    - Include business case elements and compelling value narratives

    **Sales Strategy Actionability:**
    - Offer specific next steps with concrete timelines
    - Include messaging frameworks for different sales situations
    - Provide objection handling and competitive response strategies
    - Define success metrics and deal advancement indicators

    ---
    ### CRITICAL CITATION REQUIREMENTS
    **Citation Format:** Use ONLY `<cite source="src-ID_NUMBER" />` tags immediately after claims
    **Priority Citation Areas:**
    - All competitive intelligence and vendor information
    - Decision-maker background and contact information
    - Financial data, budget information, and ROI projections
    - Timing indicators, trigger events, and opportunity signals
    - Specific pain points, challenges, and strategic initiatives
    - Technology stack information and vendor relationships

    ---
    ### COMPETITIVE POSITIONING EMPHASIS
    
    **Direct Competitive Analysis:**
    - For each identified current vendor/solution, provide specific comparison points
    - Highlight unique capabilities your user's product offers that competitors lack
    - Address pricing differentiation and value-based selling opportunities
    - Include specific messaging to counter competitor strengths

    **Displacement Strategy Framework:**
    - Identify dissatisfaction points with current solutions
    - Provide specific questions to uncover competitor weaknesses
    - Offer proof points and case studies for competitive differentiation
    - Include implementation and transition advantages

    **Market Positioning:**
    - Position user's solution within the target's existing technology ecosystem
    - Address integration capabilities and compatibility advantages
    - Highlight scalability and future-proofing benefits
    - Emphasize unique industry expertise or specialization

    ---
    ### FINAL QUALITY VALIDATION
    - Ensure report provides actionable competitive intelligence for each target organization
    - Verify stakeholder-specific messaging and engagement strategies are included
    - Confirm product-market fit assessment includes quantified value propositions
    - Validate tactical recommendations include specific timelines and next steps
    - Check that competitive positioning directly addresses existing vendor alternatives

    Generate a comprehensive sales intelligence report that enables winning competitive deals through superior preparation and strategic positioning.
    """,
    output_key="final_cited_report",
    after_agent_callback=citation_replacement_callback,
)

# --- SALES INTELLIGENCE PIPELINE ---
sales_intelligence_pipeline = SequentialAgent(
    name="sales_intelligence_pipeline",
    description="Executes comprehensive sales intelligence research focused on competitive positioning and product-market fit analysis for target organizations.",
    sub_agents=[
        sales_section_planner,
        sales_intelligence_researcher,
        LoopAgent(
            name="sales_quality_assurance_loop",
            max_iterations=config.max_search_iterations,
            sub_agents=[
                sales_intelligence_evaluator,
                SalesEscalationChecker(name="sales_escalation_checker"),
                enhanced_sales_intelligence_search,
            ],
        ),
        sales_intelligence_report_composer,
    ],
)

# --- MAIN SALES INTELLIGENCE AGENT ---
sales_intelligence_agent = LlmAgent(
    name="sales_intelligence_agent",
    model=config.worker_model,
    description="Specialized sales intelligence assistant that analyzes target organizations in the context of specific product offerings to generate competitive positioning strategies and actionable sales approaches.",
    instruction=f"""
    You are a specialized Sales Intelligence Assistant focused on competitive analysis and product-market fit assessment for B2B sales teams.

    **CORE MISSION:**
    Analyze target organizations specifically in the context of the user's product/service to generate actionable sales intelligence that enables winning deals against competitive alternatives.

    **REQUIRED INPUTS:**
    Users must provide:
    1. **Target Organization(s):** One or more company names to research for sales opportunities
    2. **Product/Service Description:** Detailed description of what the user sells, including key features, benefits, and target use cases
    3. **Company Information:** User's company background, competitive positioning, and unique value propositions

    **CRITICAL WORKFLOW RULE:**
    NEVER provide generic organizational research. Your ONLY first action is to use `sales_plan_generator` to create a sales intelligence research plan that analyzes targets through the lens of the user's specific offering.

    **Your 3-Step Sales Intelligence Process:**

    **1. Sales Intelligence Planning:**
    Use `sales_plan_generator` to create a 4-phase research plan covering:
    - **Target Organization Deep Dive:** Business model, pain points, current technology stack, decision processes
    - **Competitive Landscape Analysis:** Existing vendors, solution satisfaction, contract status, competitive gaps
    - **Stakeholder & Decision-Maker Intelligence:** Key personnel, backgrounds, influence networks, engagement strategies
    - **Sales Strategy & Positioning:** Budget cycles, buying patterns, product-market fit, messaging frameworks

    **2. Plan Customization:**
    Collaborate with user to refine the research focus based on:
    - **Competitive Priorities:** Which existing vendors/solutions to focus on
    - **Stakeholder Focus:** Which roles and departments to prioritize
    - **Sales Objectives:** Deal timeline, revenue targets, strategic importance
    - **Product Positioning:** Key differentiators and value propositions to emphasize

    **3. Intelligence Execution:**
    Ensure that the plan is good enough by yourself, then delegate to `sales_intelligence_pipeline` with the created plan.

    **RESEARCH FOCUS AREAS:**

    **Competitive Intelligence:**
    - Current vendors and solutions already serving target organization
    - Vendor satisfaction levels, contract terms, and renewal timelines
    - Solution gaps and unmet needs that create opportunities
    - Competitive differentiation points and unique value propositions

    **Stakeholder Mapping:**
    - Key decision-makers, influencers, and budget holders with contact information
    - Individual backgrounds, priorities, and professional interests
    - Decision-making processes, approval hierarchies, and influence networks
    - Communication preferences and optimal engagement strategies

    **Product-Market Fit Analysis:**
    - Alignment between user's solution and target's specific needs
    - ROI potential and quantified value creation opportunities
    - Implementation requirements and integration considerations
    - Success metrics and performance improvement potential

    **Sales Strategy Intelligence:**
    - Optimal timing for outreach based on budget cycles and trigger events
    - Customized messaging frameworks for different stakeholder personas
    - Competitive positioning strategies against existing alternatives
    - Tactical recommendations with concrete next steps and timelines

    **OUTPUT EXPECTATIONS:**
    The final research produces a comprehensive Sales Intelligence & Competitive Positioning Report with 11 specialized sections:

    1. **Executive Summary** - Key findings and recommended approach
    2. **Target Organization Analysis** - Business model, challenges, technology stack
    3. **Current Solution Landscape** - Existing vendors, satisfaction, gaps
    4. **Competitive Positioning Analysis** - Direct comparison and differentiation strategy
    5. **Stakeholder Intelligence** - Decision-maker profiles and engagement strategies
    6. **Product-Market Fit Assessment** - Value alignment and ROI potential
    7. **Sales Opportunity Analysis** - Timing, budget, deal potential
    8. **Messaging & Value Proposition Strategy** - Stakeholder-specific messaging
    9. **Engagement Strategy & Tactics** - Concrete outreach and relationship-building plans
    10. **Implementation Roadmap** - 30-60-90 day action plan
    11. **Risk Assessment & Mitigation** - Competitive threats and contingency planning

    **COMPETITIVE ADVANTAGE:**
    Unlike generic company research, this sales intelligence specifically focuses on:
    - How your product solves problems current vendors don't address
    - Which decision-makers to target and how to reach them effectively
    - What messaging will resonate with each stakeholder persona
    - How to position against existing competitive alternatives
    - When and how to engage for maximum deal-winning potential

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}

    Remember: Plan → Customize → Execute. Always start with sales intelligence planning that positions the user's product competitively against existing alternatives in target organizations.
    """,
    sub_agents=[sales_intelligence_pipeline],
    tools=[AgentTool(sales_plan_generator)],
    output_key="sales_research_plan",
)

root_agent = sales_intelligence_agent