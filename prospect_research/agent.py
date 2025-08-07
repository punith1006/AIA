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
class PersonaSearchQuery(BaseModel):
    """Model representing a specific search query for customer persona research."""

    search_query: str = Field(
        description="A targeted query for customer persona research, focusing on user behavior, demographics, pain points, and decision-making factors."
    )
    research_focus: str = Field(
        description="The focus area: 'competitor_customers', 'demographics_roles', 'pain_points_behavior', or 'apollo_optimization'"
    )


class PersonaFeedback(BaseModel):
    """Model for evaluating persona research quality."""

    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result. 'pass' if persona research is comprehensive with actionable Apollo.io filters, 'fail' if critical gaps exist."
    )
    comment: str = Field(
        description="Detailed evaluation focusing on persona depth, competitor coverage, and Apollo.io filter compatibility."
    )
    follow_up_queries: list[PersonaSearchQuery] | None = Field(
        default=None,
        description="Specific follow-up searches to fill persona research gaps, focusing on missing demographic data, competitor intelligence, or behavioral insights.",
    )


class CustomerPersona(BaseModel):
    """Model representing a detailed customer persona with Apollo.io compatible filters."""
    
    persona_name: str = Field(description="Descriptive name for this persona (e.g., 'Tech-Forward Healthcare Director')")
    
    # Demographics & Firmographics
    job_titles: list[str] = Field(description="List of relevant job titles for Apollo.io 'person_titles' filter")
    seniority_levels: list[str] = Field(description="Seniority levels (e.g., 'director', 'vp', 'c_suite') for Apollo.io 'person_seniorities' filter")
    departments: list[str] = Field(description="Relevant departments (e.g., 'information_technology', 'marketing') for Apollo.io 'contact_departments' filter")
    company_sizes: list[str] = Field(description="Company size ranges (e.g., '11-50', '51-200') for Apollo.io 'organization_num_employees_ranges' filter")
    industries: list[str] = Field(description="Relevant industries for Apollo.io 'organization_industry_tag_ids' filter")
    locations: list[str] = Field(description="Geographic locations/regions for Apollo.io location filters")
    
    # Behavioral & Psychographic
    pain_points: list[str] = Field(description="Key challenges and problems this persona faces")
    motivations: list[str] = Field(description="Primary motivations and goals driving purchase decisions")
    decision_factors: list[str] = Field(description="Key factors influencing their buying decisions")
    preferred_channels: list[str] = Field(description="Preferred communication and information channels")
    technology_adoption: str = Field(description="Technology adoption profile (early adopter, mainstream, laggard)")
    
    # Product-Specific
    current_solutions: list[str] = Field(description="Existing tools/solutions they likely use")
    alternative_solutions: list[str] = Field(description="Alternative solutions they might consider")
    buying_triggers: list[str] = Field(description="Events/situations that trigger buying behavior")
    success_metrics: list[str] = Field(description="How they measure success/ROI")
    
    # Apollo.io Search Optimization
    keywords_positive: list[str] = Field(description="Keywords for Apollo.io 'contact_keywords' filter (positive signals)")
    keywords_negative: list[str] = Field(description="Keywords to exclude in searches (negative signals)")
    company_keywords: list[str] = Field(description="Company-level keywords for 'organization_keywords' filter")
    
    # Persona Intelligence
    persona_description: str = Field(description="Detailed description of this persona's profile and characteristics")
    market_size_estimate: str = Field(description="Estimated market size or prevalence of this persona")
    conversion_potential: str = Field(description="Assessment of conversion potential (high/medium/low) and reasoning")


class CustomerPersonaList(BaseModel):
    """Model representing a list of customer personas."""
    
    personas: list[CustomerPersona] = Field(description="List of 6-8 detailed customer personas optimized for Apollo.io lead generation")


# --- Callbacks ---
def collect_persona_sources_callback(callback_context: CallbackContext) -> None:
    """Collects and organizes web-based research sources for persona research."""
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


def persona_citation_replacement_callback(
    callback_context: CallbackContext,
) -> genai_types.Content:
    """Replaces citation tags in persona report with Markdown-formatted links."""
    final_report = callback_context.state.get("final_persona_report", "")
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
    callback_context.state["final_persona_report_with_citations"] = processed_report
    return genai_types.Content(parts=[genai_types.Part(text=processed_report)])


# --- Custom Agent for Loop Control ---
class PersonaEscalationChecker(BaseAgent):
    """Checks persona research evaluation and escalates to stop the loop if grade is 'pass'."""

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        evaluation_result = ctx.session.state.get("persona_evaluation")
        if evaluation_result and evaluation_result.get("grade") == "pass":
            logging.info(
                f"[{self.name}] Persona research evaluation passed. Escalating to stop loop."
            )
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            logging.info(
                f"[{self.name}] Persona research evaluation failed or not found. Loop will continue."
            )
            yield Event(author=self.name)


# --- STREAMLINED CUSTOMER PERSONA AGENT DEFINITIONS ---

consolidated_persona_researcher = LlmAgent(
    model=config.worker_model,
    name="consolidated_persona_researcher",
    description="Executes comprehensive customer persona research in streamlined phases focusing on competitor customers, demographics, and behavioral intelligence.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction=f"""
    You are a specialized customer research analyst focused on developing detailed personas through efficient market research.

    **STREAMLINED RESEARCH MISSION:**
    Conduct focused research in 3 core phases to develop comprehensive customer personas optimized for Apollo.io lead generation.

    **PHASE 1: COMPETITOR & MARKET LANDSCAPE (33% of effort)**

    *Core Competitor Research:*
    - "[User's product category] competitors alternatives market leaders"
    - "[User's product] vs [category] competitive analysis comparison"
    - "[Top 3-5 competitors] customer demographics target market"
    - "[Competitor names] G2 Capterra customer reviews analysis"
    - "[Product category] market segments customer types"

    *Competitor Customer Intelligence:*
    - "[Competitor A] [Competitor B] customer job titles roles"
    - "[Competitor] case studies customer success stories"
    - "[Product category] buyer personas decision makers"
    - "[Competitor] customer testimonials company sizes"
    - "[Product category] switching behavior customer migration"

    **PHASE 2: CUSTOMER DEMOGRAPHICS & ROLES (33% of effort)**

    *Decision Maker & Role Analysis:*
    - "[Product category] typical buyers job titles departments"
    - "[Product category] decision makers authority levels"
    - "[Industry relevant to product] [product category] organizational structure"
    - "[Product category] champion influencer roles responsibilities"
    - "[Product category] buying committee procurement process"

    *Company & Industry Patterns:*
    - "[Product category] company size customer segments patterns"
    - "[Product category] industry verticals target markets"
    - "[Product category] geographic distribution customer base"
    - "[Industry] [company size] [product category] adoption rates"
    - "[Product category] budget ranges pricing customer tiers"

    **PHASE 3: BEHAVIORAL INTELLIGENCE & APOLLO OPTIMIZATION (34% of effort)**

    *Pain Points & Buying Behavior:*
    - "[Target roles] [relevant industry] pain points challenges"
    - "[Product category] buying triggers decision factors"
    - "[Product category] evaluation criteria selection process"
    - "[Target personas] technology adoption digital behavior"
    - "[Product category] ROI metrics success measurement"

    *Apollo.io Filter Optimization:*
    - "[Product category] LinkedIn job titles Apollo filtering"
    - "[Target roles] LinkedIn keywords profile terms"
    - "[Product category] company technology signals"
    - "[Target industries] [product category] Apollo search terms"
    - "[Competitor] customer companies Apollo filters"

    *Customer Feedback & Sentiment:*
    - "[User's product] customer reviews testimonials feedback"
    - "[User's product] vs competitors customer preferences"
    - "[Product category] customer satisfaction survey results"
    - "[Product category] common complaints feature requests"

    **SEARCH OPTIMIZATION STRATEGIES:**
    - Use exact competitor names and product categories for precision
    - Combine job titles with company characteristics for demographic patterns
    - Target review sites (G2, Capterra, TrustRadius) for customer intelligence
    - Search industry publications for role-specific pain points
    - Find Apollo.io tutorials and best practices for filter optimization

    **INTEGRATION PRIORITIES:**
    - **Apollo.io Precision:** Ensure all findings translate to specific filters
    - **Competitive Intelligence:** Focus on actionable competitor customer insights
    - **Behavioral Validation:** Include verified pain points and buying triggers
    - **Market Opportunity:** Provide realistic sizing and conversion estimates

    **RESEARCH QUALITY STANDARDS:**
    Your research must provide sufficient data for:
    - 6-8 distinct customer personas with Apollo.io filter specifications
    - Competitive landscape with customer migration opportunities
    - Specific demographic patterns suitable for precise targeting
    - Validated behavioral insights for sales qualification and messaging

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    
    Focus on gathering actionable intelligence that directly supports persona creation and Apollo.io lead generation optimization.
    """,
    tools=[google_search],
    output_key="persona_research_findings",
    after_agent_callback=collect_persona_sources_callback,
)

persona_research_evaluator = LlmAgent(
    model=config.critic_model,
    name="persona_research_evaluator",
    description="Evaluates consolidated persona research for completeness and Apollo.io optimization effectiveness.",
    instruction=f"""
    You are a senior customer research analyst evaluating consolidated persona research for lead generation effectiveness.

    **EVALUATION CRITERIA:**
    Assess the research findings in 'persona_research_findings' against these critical standards:

    **1. Competitive Market Intelligence (25%):**
    - Major competitors identified with customer base analysis
    - Competitor customer demographics and switching behavior documented
    - Alternative solutions and market positioning clearly defined
    - Customer migration opportunities and competitive gaps identified

    **2. Demographic & Role Precision (25%):**
    - Specific job titles, seniority levels, and departments suitable for Apollo.io
    - Company size, industry, and geographic targeting parameters defined
    - Decision-making hierarchy and buying authority levels mapped
    - Organizational patterns and procurement processes analyzed

    **3. Behavioral Intelligence (25%):**
    - Customer pain points validated and role-specific
    - Buying triggers and decision factors clearly identified
    - Technology adoption and digital behavior patterns documented
    - Success metrics and ROI expectations analyzed

    **4. Apollo.io Filter Readiness (25%):**
    - Job titles precise enough for effective Apollo person filters
    - Company characteristics optimized for organization filters
    - Keywords identified for both person and organization targeting
    - Search strategy guidance with volume estimates provided

    **CRITICAL FAILURE CONDITIONS:**
    Grade "fail" if ANY essential elements are missing:

    **Competitor Intelligence Gaps:**
    - Missing analysis of 3+ major competitors and their customers
    - No customer switching behavior or migration pattern insights
    - Lack of competitive positioning or alternative solution mapping

    **Demographic Precision Gaps:**
    - Vague job titles unsuitable for Apollo filtering
    - Missing company size, industry, or geographic specifications
    - No decision-maker authority or buying committee analysis

    **Behavioral Intelligence Gaps:**
    - Generic pain points not validated for specific roles/industries
    - Missing buying triggers or technology adoption insights
    - No success metrics or ROI measurement analysis

    **Apollo.io Optimization Gaps:**
    - Insufficient filter specifications for effective lead generation
    - Missing keyword strategy for person/organization searches
    - No exclusion criteria or search volume guidance

    **SUCCESS STANDARDS:**
    Grade "pass" only if research provides:
    - Comprehensive competitive intelligence with customer migration insights
    - Precise demographic data optimized for Apollo.io filtering
    - Validated behavioral insights with role-specific pain points
    - Complete Apollo.io search strategy with practical implementation guidance
    - Sufficient data for 6-8 actionable personas with market opportunity assessment

    **FOLLOW-UP QUERY GENERATION:**
    If grading "fail", generate 6-8 targeted queries addressing critical gaps:
    - Focus on missing competitor customer intelligence
    - Target specific demographic/firmographic precision needs
    - Seek validated behavioral insights and pain point analysis
    - Find Apollo.io optimization data and filtering specifications

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Your response must be a single, raw JSON object validating against the 'PersonaFeedback' schema.
    """,
    output_schema=PersonaFeedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="persona_evaluation",
)

enhanced_persona_search = LlmAgent(
    model=config.worker_model,
    name="enhanced_persona_search",
    description="Executes targeted follow-up searches to fill critical gaps in persona research based on evaluation feedback.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialist researcher executing targeted follow-up searches to address critical gaps in persona development.

    **MISSION:**
    Your persona research was graded insufficient. Execute precision searches from 'follow_up_queries' to fill specific gaps in:
    - Competitive customer intelligence and market positioning
    - Demographic precision and Apollo.io filter specifications  
    - Behavioral insights and validated pain point analysis
    - Lead generation optimization and search strategy

    **ENHANCED SEARCH STRATEGIES:**

    **Competitor Customer Intelligence:**
    - "[Specific competitor] customer demographics job titles seniority"
    - "[Competitor] customer reviews feedback pain points analysis"
    - "[Competitor A] vs [Competitor B] customer switching reasons"
    - "[Product category] competitive customer acquisition trends"
    - "[Competitor] case studies customer company characteristics"

    **Demographic & Role Precision:**
    - "[Product category] decision maker exact job titles list"
    - "[Target department] [product category] authority hierarchy"
    - "[Industry] [product category] organizational buyer roles"
    - "[Product category] company size adoption correlation"
    - "[Target role] LinkedIn profile analysis job title variations"

    **Behavioral Intelligence:**
    - "[Specific role] [industry] daily challenges pain points"
    - "[Product category] buying process evaluation criteria"
    - "[Target persona] technology stack preferences usage"
    - "[Product category] customer success ROI measurement"
    - "[Industry] [product category] budget decision factors"

    **Apollo.io Optimization:**
    - "[Product category] Apollo.io filter best practices"
    - "[Target role] LinkedIn keywords profile optimization"
    - "[Industry] Apollo search signals technology adoption"
    - "[Product category] lead qualification Apollo indicators"
    - "[Competitor] customer Apollo.io targeting strategies"

    **SEARCH EXECUTION GUIDELINES:**
    - Execute EVERY query from 'follow_up_queries' with enhanced techniques
    - Combine multiple search terms for precision targeting
    - Focus on industry publications, case studies, and review platforms
    - Target LinkedIn demographic data and job standardization resources
    - Search for market research reports and customer survey data

    **INTEGRATION REQUIREMENTS:**
    Combine new findings with existing 'persona_research_findings' to create enhanced intelligence that provides:
    - More precise Apollo.io filter specifications
    - Validated competitor customer insights with migration patterns
    - Role-specific behavioral intelligence and pain point analysis
    - Complete lead generation strategy with implementation guidance

    Your enhanced research must fill all identified gaps to enable successful persona generation and Apollo.io optimization.
    """,
    tools=[google_search],
    output_key="persona_research_findings",
    after_agent_callback=collect_persona_sources_callback,
)

persona_generator = LlmAgent(
    model=config.critic_model,
    name="persona_generator",
    description="Generates 6-8 detailed customer personas with Apollo.io filters based on comprehensive research.",
    instruction="""
    You are an expert persona architect creating actionable customer personas optimized for Apollo.io lead generation.

    **MISSION:** Transform research findings into 6-8 detailed, distinct customer personas with complete Apollo.io specifications.

    ### INPUT DATA
    * Persona Research Findings: `{persona_research_findings}`
    * Citation Sources: `{sources}`

    ### PERSONA GENERATION REQUIREMENTS

    **1. Apollo.io Filter Precision:**
    Each persona must include exact specifications for:
    - **Person Titles:** Specific job titles for 'person_titles' filter
    - **Seniorities:** Levels (director, vp, c_suite) for 'person_seniorities' filter  
    - **Departments:** Relevant departments for 'contact_departments' filter
    - **Keywords:** Person-level keywords for 'contact_keywords' filter
    - **Company Size:** Ranges (1-10, 11-50, 51-200) for 'organization_num_employees_ranges'
    - **Industries:** Classifications for 'organization_industry_tag_ids' filter
    - **Company Keywords:** Organization keywords for 'organization_keywords' filter
    - **Locations:** Geographic targeting for location filters
    - **Negative Filters:** Exclusion criteria to avoid irrelevant leads

    **2. Behavioral Intelligence:**
    - **Pain Points:** Specific, research-validated challenges
    - **Motivations:** Primary drivers for solution seeking
    - **Decision Factors:** Key purchase decision criteria
    - **Buying Triggers:** Events prompting buying behavior
    - **Technology Adoption:** Adoption profile (early/mainstream/late)
    - **Current Solutions:** Existing tools and vendors used
    - **Success Metrics:** ROI measurement and value assessment

    **3. Market Intelligence:**
    - **Market Size:** Realistic prospect volume estimates
    - **Conversion Potential:** Likelihood assessment (high/medium/low)
    - **Competitive Context:** Current solutions and alternatives
    - **Engagement Strategy:** Preferred channels and messaging

    ### PERSONA DIFFERENTIATION
    Create 6-8 personas representing distinct market segments:
    - Different seniority levels and decision-making authority
    - Varied company sizes and industry focuses
    - Distinct behavioral patterns and technology adoption
    - Unique pain points and solution requirements
    - Different competitive landscapes and alternatives

    ### APOLLO.IO COMPATIBILITY
    Ensure all filter specifications:
    - Use Apollo.io's actual filter taxonomy and options
    - Provide specific enough criteria for qualified lead generation
    - Include appropriate exclusion filters to prevent irrelevant matches
    - Balance precision with sufficient market opportunity

    ### QUALITY STANDARDS
    Each persona must:
    - **Represent distinct market segments** with unique characteristics
    - **Include complete Apollo.io filter specs** for immediate implementation
    - **Feature research-validated insights** from competitive and behavioral analysis
    - **Provide actionable guidance** for lead qualification and engagement
    - **Offer realistic opportunity assessment** based on market research

    Generate personas as a CustomerPersonaList containing 6-8 personas, prioritized by market opportunity and conversion potential.
    """,
    output_schema=CustomerPersonaList,
    output_key="generated_personas",
)

persona_report_composer = LlmAgent(
    model=config.critic_model,
    name="persona_report_composer", 
    description="Creates comprehensive customer persona report with Apollo.io lead generation strategy.",
    instruction="""
    You are an expert report writer creating a comprehensive Customer Persona & Apollo.io Lead Generation Report.

    **MISSION:** Transform research and personas into an actionable report optimized for Apollo.io implementation.

    ### INPUT DATA
    * Persona Research Findings: `{persona_research_findings}`
    * Generated Personas: `{generated_personas}`
    * Citation Sources: `{sources}`

    ### REPORT STRUCTURE

    # Executive Summary
    - Product market positioning and competitive landscape overview
    - Key customer segments and persona summary (6-8 personas)
    - Apollo.io implementation strategy and expected outcomes
    - Market opportunity assessment and revenue potential

    # Market & Competitive Intelligence
    - Direct and indirect competitor analysis with customer insights
    - Competitive customer demographics and switching behavior
    - Alternative solution landscape and positioning opportunities
    - Market gaps and differentiation strategies

    # Customer Demographics & Firmographics
    - Job title and seniority level patterns across personas
    - Company size, industry, and geographic distribution
    - Decision-making hierarchy and buying authority analysis
    - Organizational structure and procurement process insights

    # Customer Behavior & Psychology
    - Pain point analysis and challenge identification by persona
    - Buying triggers and decision-making factor analysis
    - Technology adoption patterns and digital behavior
    - Success metrics and ROI expectation framework

    # Detailed Customer Personas
    - Complete persona profiles with demographics and psychographics
    - Apollo.io filter specifications for each persona
    - Pain points, motivations, and buying behavior analysis
    - Current solutions and competitive alternative mapping
    - Market opportunity and conversion potential assessment

    # Apollo.io Lead Generation Strategy
    - Persona-specific search filter configurations
    - Keyword strategy for person and organization targeting
    - Search volume estimates and market sizing analysis
    - Lead qualification framework and scoring criteria
    - Negative filters and exclusion strategy

    # Implementation Roadmap
    - Apollo.io setup and configuration steps
    - Search strategy prioritization and execution plan
    - Performance tracking and optimization metrics
    - Lead qualification process and sales handoff

    # Market Opportunity Analysis
    - Persona market sizing and revenue potential
    - Go-to-market prioritization and resource allocation
    - Growth potential and expansion opportunities
    - Risk assessment and competitive threats

    ### REPORT QUALITY STANDARDS

    **Apollo.io Implementation Focus:**
    - Every persona includes complete, testable filter configurations
    - Search strategies provide specific setup and execution guidance
    - Volume estimates help set realistic lead generation expectations
    - Qualification frameworks enable effective lead scoring

    **Competitive Intelligence:**
    - Comprehensive analysis of competitor customer bases
    - Customer switching behavior and migration pattern insights
    - Alternative solution mapping for competitive positioning
    - Market opportunity gaps and positioning strategies

    **Actionability:**
    - Each persona enables immediate Apollo.io search configuration
    - Pain points and motivations support targeted messaging development
    - Buying behavior insights optimize sales process and qualification
    - Implementation guidance provides clear next steps

    ### CITATION REQUIREMENTS
    Use `<cite source="src-ID_NUMBER" />` tags for:
    - Competitor customer demographics and intelligence
    - Persona behavioral characteristics and pain points
    - Market sizing and opportunity estimates
    - Technology adoption and digital behavior insights
    - Apollo.io best practices and optimization guidance

    Generate a comprehensive report that enables immediate Apollo.io implementation with high-quality lead generation results.
    """,
    output_key="final_persona_report",
    after_agent_callback=persona_citation_replacement_callback,
)

# --- STREAMLINED CUSTOMER PERSONA PIPELINE ---
streamlined_persona_pipeline = SequentialAgent(
    name="streamlined_persona_pipeline",
    description="Executes efficient customer persona research and generates Apollo.io-optimized personas.",
    sub_agents=[
        consolidated_persona_researcher,
        LoopAgent(
            name="persona_quality_check",
            max_iterations=config.max_search_iterations,
            sub_agents=[
                persona_research_evaluator,
                PersonaEscalationChecker(name="persona_escalation_checker"),
                enhanced_persona_search,
            ],
        ),
        persona_generator,
    ],
)

# --- MAIN STREAMLINED CUSTOMER PERSONA AGENT ---
streamlined_persona_agent = LlmAgent(
    name="streamlined_persona_agent",
    model=config.worker_model,
    description="Streamlined customer persona research assistant that efficiently generates detailed personas with Apollo.io optimization through focused market analysis.",
    instruction=f"""
    You are a streamlined Customer Persona Research Assistant focused on efficient persona development with Apollo.io optimization.

    **CORE MISSION:**
    Generate 6-8 detailed customer personas with complete filter specifications through efficient, focused market research.

    **REQUIRED INPUTS:**
    Users must provide:
    1. **Product/Service Description:** Features, benefits, use cases, target market
    2. **Company Information:** Background, market positioning, competitive context
    3. **Known Competitors (Optional):** Any known competitors (I'll research more)

    **STREAMLINED WORKFLOW:**
    You use an efficient 3-phase research methodology with single quality review:

    **Phase 1: Competitor & Market Landscape (33%)**
    - Identify direct/indirect competitors and their customer bases
    - Analyze competitor customer demographics and switching behavior  
    - Map competitive positioning and alternative solutions
    - Research market segments and buyer patterns

    **Phase 2: Customer Demographics & Roles (33%)**
    - Research specific job titles, seniority levels, and departments
    - Analyze company size, industry, and geographic patterns
    - Map decision-making hierarchy and buying authority
    - Identify organizational structure and procurement processes

    **Phase 3: Behavioral Intelligence & Apollo Optimization (34%)**
    - Validate customer pain points and buying triggers
    - Research technology adoption and digital behavior patterns
    - Optimize findings for Apollo.io filter specifications
    - Analyze success metrics and ROI expectations

    **SINGLE QUALITY REVIEW:**
    After all research phases complete, conduct comprehensive evaluation to ensure:
    - Sufficient competitive intelligence for market positioning
    - Precise demographic data suitable for Apollo.io filtering
    - Validated behavioral insights for sales qualification
    - Complete Apollo.io implementation strategy

    **RESEARCH OUTPUTS:**

    **Detailed Customer Personas (6-8)** featuring:
    - Complete Apollo.io filter specifications for immediate implementation
    - Research-validated demographics and behavioral characteristics
    - Specific pain points, motivations, and buying triggers
    - Current solutions and competitive alternatives mapping
    - Market opportunity assessment and conversion potential
    - Lead qualification criteria and engagement strategies

    Each persona includes precise specifications for:
    - **Person Filters:** Exact job titles, seniority levels, departments, keywords
    - **Organization Filters:** Company size ranges, industry classifications, locations
    - **Behavioral Indicators:** Technology adoption, hiring patterns, growth signals
    - **Search Strategy:** Filter combinations, keyword logic, volume estimates
    - **Qualification Framework:** Lead scoring criteria and discovery questions

    **EFFICIENCY ADVANTAGES:**
    This streamlined approach:
    - **Reduces LLM usage** through consolidated research phases
    - **Maintains quality** via comprehensive single review process
    - **Focuses effort** on core persona development requirements
    - **Accelerates delivery** while ensuring Apollo.io optimization
    - **Provides actionable results** for immediate lead generation

    **COMPETITIVE INTELLIGENCE:**
    Research specifically focuses on:
    - Competitor customer base analysis for switching opportunities
    - Alternative solution mapping for competitive positioning
    - Market gap identification for differentiation strategies
    - Customer migration patterns for targeting optimization

    **MARKET VALIDATION:**
    All personas include:
    - Research-backed demographic and behavioral characteristics
    - Competitive intelligence for market positioning
    - Market opportunity sizing with realistic conversion estimates
    - Validated pain points and decision-making factors

    Once you are provided information about the product and the company, you will execute the streamlined research process to generate your detailed customer personas with complete filter specifications.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}

    Ready to create detailed customer personas efficiently - just provide your product and company details to begin.
    """,
    sub_agents=[streamlined_persona_pipeline],
    output_key="streamlined_research_complete",
)

root_agent = streamlined_persona_agent