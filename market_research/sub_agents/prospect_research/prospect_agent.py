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
from google.adk.models import Gemini
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


class PersonaData(BaseModel):
    """Simplified model for collecting persona data for Apollo.io parameter generation."""
    
    persona_name: str = Field(description="Descriptive name for this persona")
    job_titles: list[str] = Field(description="List of relevant job titles")
    seniority_levels: list[str] = Field(description="Seniority levels (director, vp, c_suite, etc.)")
    departments: list[str] = Field(description="Relevant departments")
    company_sizes: list[str] = Field(description="Company size ranges")
    industries: list[str] = Field(description="Relevant industries")
    locations: list[str] = Field(description="Geographic locations/regions")
    skills: list[str] = Field(description="Professional skills and competencies")
    keywords_positive: list[str] = Field(description="Keywords for positive targeting")
    keywords_negative: list[str] = Field(description="Keywords to exclude")
    company_keywords: list[str] = Field(description="Company-level keywords")
    technologies: list[str] = Field(description="Technologies and tools used")
    pain_points: list[str] = Field(description="Key challenges and problems")
    current_solutions: list[str] = Field(description="Existing tools/solutions they use")


class PersonaDataCollection(BaseModel):
    """Model representing a collection of persona data."""
    
    personas: list[PersonaData] = Field(description="List of personas with Apollo.io relevant data")


class ApolloSearchParameters(BaseModel):
    """Comprehensive Apollo.io People Search API parameters."""
    
    # Person-level filters
    person_titles: list[str] = Field(default=[], description="Job titles to search for")
    person_locations: list[str] = Field(default=[], description="Person locations (City, State, Country format)")
    person_seniorities: list[str] = Field(default=[], description="Seniority levels")
    person_departments: list[str] = Field(default=[], description="Department classifications")
    person_skills: list[str] = Field(default=[], description="Professional skills")
    person_keywords: list[str] = Field(default=[], description="Keywords associated with person")
    
    # Organization-level filters
    organization_locations: list[str] = Field(default=[], description="Organization locations")
    organization_num_employees_ranges: list[str] = Field(default=[], description="Employee count ranges")
    organization_industry_tag_ids: list[str] = Field(default=[], description="Industry classifications")
    organization_keywords: list[str] = Field(default=[], description="Organization keywords")
    organization_technologies: list[str] = Field(default=[], description="Technologies used by organizations")
    
    # Exclusion filters
    person_not_titles: list[str] = Field(default=[], description="Job titles to exclude")
    person_not_keywords: list[str] = Field(default=[], description="Keywords to exclude for persons")
    organization_not_keywords: list[str] = Field(default=[], description="Organization keywords to exclude")
    
    # Contact data filters
    email_status: list[str] = Field(default=[], description="Email status filters (verified, likely, etc.)")
    phone_status: list[str] = Field(default=[], description="Phone status filters")
    
    # Search configuration
    page: int = Field(default=1, description="Page number for pagination")
    per_page: int = Field(default=100, description="Results per page (max 100)")
    sort_by_field: str = Field(default="relevance", description="Field to sort results by")
    sort_ascending: bool = Field(default=False, description="Sort order")


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


# --- Apollo.io Parameter Consolidator ---
class ApolloParameterConsolidator(BaseAgent):
    """Consolidates all persona data into unified Apollo.io search parameters."""
    
    def __init__(self, name: str = "apollo_parameter_consolidator"):
        super().__init__(name=name)

    async def _run_async_impl__(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        persona_data = ctx.session.state.get("persona_data_collection", {}).get("personas", [])
        
        # Consolidate all persona data into unified parameters
        consolidated_params = ApolloSearchParameters()
        
        for persona in persona_data:
            # Person-level consolidation
            consolidated_params.person_titles.extend(persona.get("job_titles", []))
            consolidated_params.person_seniorities.extend(persona.get("seniority_levels", []))
            consolidated_params.person_departments.extend(persona.get("departments", []))
            consolidated_params.person_locations.extend(persona.get("locations", []))
            consolidated_params.person_skills.extend(persona.get("skills", []))
            consolidated_params.person_keywords.extend(persona.get("keywords_positive", []))
            
            # Organization-level consolidation
            consolidated_params.organization_locations.extend(persona.get("locations", []))
            consolidated_params.organization_num_employees_ranges.extend(persona.get("company_sizes", []))
            consolidated_params.organization_industry_tag_ids.extend(persona.get("industries", []))
            consolidated_params.organization_keywords.extend(persona.get("company_keywords", []))
            consolidated_params.organization_technologies.extend(persona.get("technologies", []))
            
            # Exclusion filters
            consolidated_params.person_not_keywords.extend(persona.get("keywords_negative", []))
        
        # Remove duplicates and clean up
        for field_name, field_value in consolidated_params.__dict__.items():
            if isinstance(field_value, list):
                # Remove duplicates while preserving order
                setattr(consolidated_params, field_name, list(dict.fromkeys(field_value)))
        
        # Set optimal search configuration
        consolidated_params.email_status = ["verified", "likely"]
        consolidated_params.per_page = 100
        consolidated_params.sort_by_field = "relevance"
        
        # Store final parameters
        ctx.session.state["prospect_researcher"] = consolidated_params.dict()
        yield Event(author=self.name, content="Apollo.io search parameters consolidated and optimized.")


# --- STREAMLINED AGENTS ---

consolidated_persona_researcher = LlmAgent(
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(
	    initial_delay=3,
	    attempts=3
	    
	    )
    ),
    name="consolidated_persona_researcher",
    description="Executes comprehensive customer persona research focused on Apollo.io parameter optimization.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction=f"""
    You are a specialized customer research analyst focused on gathering data for Apollo.io lead generation optimization.

    **MISSION:** Conduct focused research to collect precise demographic, firmographic, and behavioral data optimized for Apollo.io People Search API parameters.

    **RESEARCH FOCUS AREAS:**

    **1. Job Title & Role Intelligence (25%)**
    - "[User's product category] typical buyers job titles exact terms"
    - "[Product category] decision makers authority levels titles"
    - "[Competitor] customer job titles LinkedIn analysis"
    - "[Product category] champion roles influencer titles"
    - "[Industry] [product category] organizational hierarchy titles"

    **2. Company & Industry Targeting (25%)**
    - "[Product category] company size customer segments adoption"
    - "[Product category] industry verticals target markets"
    - "[Product category] geographic distribution customer regions"
    - "[Competitor] customer companies industry analysis"
    - "[Product category] technology stack company characteristics"

    **3. Skills & Technology Intelligence (25%)**
    - "[Target roles] professional skills competencies LinkedIn"
    - "[Product category] user technical skills requirements"
    - "[Industry] [target roles] technology adoption tools"
    - "[Product category] complementary technologies integrations"
    - "[Competitor] customer technology stack analysis"

    **4. Behavioral & Intent Signals (25%)**
    - "[Target personas] pain points challenges keywords"
    - "[Product category] buying intent signals behaviors"
    - "[Target roles] professional development interests"
    - "[Product category] evaluation criteria decision factors"
    - "[Industry] [product category] adoption triggers events"

    **APOLLO.IO OPTIMIZATION PRIORITIES:**
    - **Exact Job Titles:** Research specific, searchable job title variations
    - **Skills & Keywords:** Identify professional skills and role-specific keywords
    - **Company Characteristics:** Find firmographic patterns and technology usage
    - **Geographic Precision:** Get specific locations (City, State, Country format)
    - **Industry Classifications:** Use standard industry terms and classifications
    - **Technology Adoption:** Identify specific tools and platforms used
    - **Exclusion Criteria:** Find negative keywords to avoid irrelevant matches

    **SEARCH STRATEGIES:**
    - Target LinkedIn data and job posting sites for accurate job titles
    - Research competitor customer bases for demographic patterns
    - Use industry publications for role-specific skills and responsibilities
    - Find technology adoption surveys and market research
    - Search Apollo.io documentation for filter optimization best practices

    **DATA QUALITY REQUIREMENTS:**
    Collect sufficient data to populate Apollo.io parameters:
    - 15-25 specific job titles across different seniority levels
    - 10-15 professional skills per target role type
    - 5-10 company size ranges and industry classifications
    - Geographic targeting data for key markets
    - Technology keywords for organization filtering
    - Negative keywords for exclusion filtering

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    
    Focus on gathering precise, searchable data that directly maps to Apollo.io People Search API parameters.
    """,
    tools=[google_search],
    output_key="persona_research_findings",
)

persona_research_evaluator = LlmAgent(
    model=Gemini(
        model=config.critic_model,
        retry_options=genai_types.HttpRetryOptions(
	    initial_delay=3,
	    attempts=3
	    
	    )
    ),
    name="persona_research_evaluator",
    description="Evaluates persona research for Apollo.io parameter completeness.",
    instruction=f"""
    You are a senior research analyst evaluating persona research for Apollo.io lead generation effectiveness.

    **EVALUATION CRITERIA:**
    Assess the research findings in 'persona_research_findings' against these Apollo.io parameter requirements:

    **1. Job Title Precision (30%):**
    - 15+ specific, searchable job titles identified
    - Multiple seniority levels covered (individual contributor to C-suite)
    - Department-specific role variations documented
    - Decision maker vs influencer roles clearly identified

    **2. Company & Industry Intelligence (25%):**
    - Company size patterns with specific employee ranges
    - Industry classifications using standard terminology
    - Geographic targeting data with specific locations
    - Technology adoption patterns for organization filtering

    **3. Skills & Keyword Intelligence (25%):**
    - Professional skills mapped to target roles
    - Role-specific keywords and terminology identified
    - Technology skills and platform experience documented
    - Industry-specific expertise and competencies listed

    **4. Behavioral & Intent Signals (20%):**
    - Pain points and challenges validated for targeting
    - Buying intent signals and trigger events identified
    - Professional development interests and activities
    - Current solution usage patterns documented

    **CRITICAL FAILURE CONDITIONS - Grade "fail" if:**
    - Fewer than 15 specific job titles identified
    - Missing company size or industry classification data
    - No professional skills or keyword intelligence gathered
    - Vague or generic demographic data unsuitable for filtering
    - Missing technology adoption or current solution insights

    **SUCCESS STANDARDS - Grade "pass" if:**
    - 15+ precise job titles suitable for Apollo.io person_titles filter
    - Complete company/industry data for organization filters
    - Comprehensive skills and keyword data for targeting
    - Behavioral intelligence for lead qualification and messaging
    - Sufficient exclusion criteria to avoid irrelevant matches

    **FOLLOW-UP QUERY GENERATION:**
    If grading "fail", generate specific queries to address gaps:
    - Target missing job title variations and seniority levels
    - Seek company size and industry classification precision
    - Find role-specific skills and professional competencies
    - Research technology adoption and current solution usage

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Your response must be a single, raw JSON object validating against the 'PersonaFeedback' schema.
    """,
    output_schema=PersonaFeedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="persona_evaluation",
)

enhanced_persona_search = LlmAgent(
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(
	    initial_delay=3,
	    attempts=3
	    
	    )
    ),
    name="enhanced_persona_search",
    description="Executes targeted follow-up searches to fill Apollo.io parameter gaps.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialist researcher filling critical gaps in Apollo.io parameter data.

    **MISSION:** Execute precision searches from 'follow_up_queries' to gather missing Apollo.io parameter data.

    **ENHANCED SEARCH STRATEGIES:**

    **Job Title Intelligence:**
    - "[Product category] job titles hierarchy levels exact terms"
    - "[Target department] [product category] role variations LinkedIn"
    - "[Industry] [product category] decision maker titles authority"
    - "[Competitor] customer job titles organizational structure"

    **Skills & Technology Intelligence:**
    - "[Target roles] professional skills LinkedIn competencies"
    - "[Product category] user technical requirements expertise"
    - "[Industry] technology adoption tools platform usage"
    - "[Target personas] professional development interests"

    **Company Intelligence:**
    - "[Product category] customer company size patterns adoption"
    - "[Target industry] geographic distribution market presence"
    - "[Product category] technology stack organizational signals"
    - "[Competitor] customer firmographic characteristics"

    **Behavioral & Intent Intelligence:**
    - "[Target roles] pain points challenges daily responsibilities"
    - "[Product category] buying triggers decision-making process"
    - "[Target personas] current solutions alternatives usage"
    - "[Industry] [product category] adoption patterns behaviors"

    **SEARCH EXECUTION:**
    - Execute ALL queries from 'follow_up_queries' with enhanced techniques
    - Target professional networks and job boards for accurate role data
    - Search technology surveys and adoption reports
    - Find industry publications and market research
    - Research Apollo.io optimization guides and best practices

    Your enhanced research must fill all identified gaps to enable effective Apollo.io parameter generation.
    """,
    tools=[google_search],
    output_key="persona_research_findings",
)

persona_data_generator = LlmAgent(
    model=Gemini(
        model=config.critic_model,
        retry_options=genai_types.HttpRetryOptions(
	    initial_delay=3,
	    attempts=3
	    
	    )
    ),
    name="persona_data_generator",
    description="Generates structured persona data optimized for Apollo.io parameters.",
    instruction="""
    You are an expert data architect creating structured persona data optimized for Apollo.io lead generation.

    **MISSION:** Transform research findings into structured persona data that maps directly to Apollo.io People Search API parameters.

    ### INPUT DATA
    * Persona Research Findings: `{persona_research_findings}`

    **DATA GENERATION REQUIREMENTS:**

    **1. Job Title Precision:**
    - Extract 15-25 specific, searchable job titles
    - Include variations and synonyms for each role type
    - Cover multiple seniority levels (IC, Manager, Director, VP, C-Suite)
    - Map to Apollo.io person_titles format requirements

    **2. Skills & Keywords Intelligence:**
    - Professional skills for person_skills filtering
    - Role-specific keywords for person_keywords targeting
    - Technology skills and platform expertise
    - Industry-specific competencies and certifications

    **3. Company & Industry Mapping:**
    - Company size ranges in Apollo.io format (1-10, 11-50, 51-200, etc.)
    - Industry classifications using standard terminology
    - Geographic locations in City, State, Country format
    - Department classifications for targeting

    **4. Technology & Solution Intelligence:**
    - Current technologies and platforms used
    - Complementary tools and integrations
    - Technology stack indicators for organization filtering
    - Alternative solutions and competitive tools

    **5. Behavioral Intelligence:**
    - Pain points and challenges for messaging
    - Professional interests and development activities
    - Buying triggers and decision factors
    - Current solution usage patterns

    **PERSONA DIFFERENTIATION:**
    Create 4-6 distinct personas representing:
    - Different seniority levels and authority
    - Various company sizes and industry focuses
    - Distinct technology adoption patterns
    - Unique role responsibilities and pain points

    **APOLLO.IO OPTIMIZATION:**
    Ensure all data elements:
    - Use precise, searchable terminology
    - Include both positive and negative targeting keywords
    - Provide geographic specificity where relevant
    - Include technology adoption signals
    - Support effective lead qualification

    Generate personas as a PersonaDataCollection containing 4-6 personas optimized for Apollo.io parameter mapping.
    """,
    output_schema=PersonaDataCollection,
    output_key="persona_data_collection",
)

apollo_parameter_generator = LlmAgent(
    model=Gemini(
        model=config.critic_model,
        retry_options=genai_types.HttpRetryOptions(
	    initial_delay=3,
	    attempts=3
	    
	    )
    ),
    name="apollo_parameter_generator",
    description="Generates consolidated Apollo.io search parameters from all persona data.",
    instruction="""
    You are an Apollo.io optimization expert creating comprehensive search parameters.

    **MISSION:** Consolidate all persona data into optimized Apollo.io People Search API parameters.

    ### INPUT DATA
    * Persona Data Collection: `{persona_data_collection}`

    **PARAMETER CONSOLIDATION STRATEGY:**

    **1. Person-Level Parameters:**
    - **person_titles:** All unique job titles from all personas
    - **person_seniorities:** All seniority levels (director, vp, c_suite, etc.)
    - **person_departments:** All relevant departments and functions
    - **person_locations:** Geographic targeting from persona insights
    - **person_skills:** Professional skills and competencies
    - **person_keywords:** Positive targeting keywords and terms

    **2. Organization-Level Parameters:**
    - **organization_locations:** Company location targeting
    - **organization_num_employees_ranges:** Company size ranges
    - **organization_industry_tag_ids:** Industry classifications
    - **organization_keywords:** Company-level targeting terms
    - **organization_technologies:** Technology stack indicators

    **3. Exclusion Parameters:**
    - **person_not_titles:** Job titles to exclude
    - **person_not_keywords:** Negative person keywords
    - **organization_not_keywords:** Negative company keywords

    **4. Contact & Quality Filters:**
    - **email_status:** Prefer verified and likely emails
    - **phone_status:** Include available phone contacts where relevant

    **5. Search Configuration:**
    - **per_page:** Set to 100 for maximum results
    - **sort_by_field:** Use relevance for best matching
    - **page:** Start with page 1

    **OPTIMIZATION PRINCIPLES:**
    - **Maximize Coverage:** Include all relevant variations without over-filtering
    - **Maintain Quality:** Use exclusion filters to avoid irrelevant matches
    - **Balance Precision:** Specific enough for quality, broad enough for volume
    - **Leverage Intent Signals:** Include behavioral and technology indicators

    **CONSOLIDATION LOGIC:**
    - Combine all persona insights into unified parameter arrays
    - Remove duplicates while preserving comprehensive coverage
    - Prioritize high-intent signals and qualification criteria
    - Include geographic and firmographic diversity

    Generate a single ApolloSearchParameters object that maximizes relevant lead discovery across all personas.
    """,
    output_schema=ApolloSearchParameters,
    output_key="prospect_researcher",
)

# --- STREAMLINED PIPELINE ---
prospect_research_pipeline = SequentialAgent(
    name="prospect_research_pipeline",
    description="Executes efficient persona research and generates consolidated Apollo.io search parameters.",
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
        persona_data_generator,
        apollo_parameter_generator,
    ],
)

# --- MAIN STREAMLINED APOLLO AGENT ---
prospect_researcher = LlmAgent(
    name="prospect_researcher",
    model=Gemini(
        model=config.worker_model,
        retry_options=genai_types.HttpRetryOptions(
	    initial_delay=3,
	    attempts=3
	    
	    )
    ),
    description="Streamlined customer persona research assistant that generates consolidated Apollo.io search parameters through focused market analysis.",
    instruction=f"""
    You are a streamlined Apollo.io Lead Generation Assistant focused on creating optimized search parameters.

    **CORE MISSION:**
    Generate consolidated Apollo.io People Search API parameters through efficient persona research.

    **REQUIRED INPUTS:**
    Users must provide:
    1. **Product/Service Description:** Features, benefits, use cases, target market
    2. **Company Information:** Background, market positioning, competitive context
    3. **Known Competitors (Optional):** Any known competitors (I'll research more)

    **STREAMLINED WORKFLOW:**
    You use an efficient research methodology with single quality review:

    **Phase 1: Comprehensive Research**
    - Identify job titles, seniority levels, and role variations
    - Research company size patterns, industries, and geographic distribution
    - Analyze professional skills, technology adoption, and behavioral patterns
    - Map competitive landscape and alternative solution usage

    **Phase 2: Quality Validation**
    - Ensure sufficient data for effective Apollo.io parameter generation
    - Validate job title precision and demographic coverage
    - Confirm skills intelligence and technology adoption insights
    - Execute follow-up searches to fill any critical gaps

    **Phase 3: Parameter Generation**
    - Transform research into structured persona data
    - Consolidate all insights into unified Apollo.io search parameters
    - Optimize for maximum relevant lead discovery
    - Balance precision with comprehensive market coverage

    **FINAL OUTPUT:**
    Single JSON object with consolidated Apollo.io People Search API parameters:

    ```json
    {{
      "person_titles": ["all relevant job titles"],
      "person_seniorities": ["seniority levels"],
      "person_locations": ["geographic targeting"],
      "person_skills": ["professional skills"],
      "person_keywords": ["positive keywords"],
      "organization_num_employees_ranges": ["company sizes"],
      "organization_industry_tag_ids": ["industries"],
      "organization_keywords": ["company keywords"],
      "organization_technologies": ["technology stack"],
      "person_not_keywords": ["exclusion terms"],
      "email_status": ["verified", "likely"],
      "per_page": 100,
      "sort_by_field": "relevance"
    }}
    ```

    **KEY ADVANTAGES:**
    - **Maximized Lead Volume:** Consolidates all personas into single comprehensive search
    - **Maintained Relevance:** Uses exclusion filters and qualification criteria
    - **Immediate Implementation:** Direct API parameters for instant lead generation
    - **Optimized Coverage:** Balances specificity with market opportunity

    **RESEARCH FOCUS:**
    All research specifically targets Apollo.io parameter optimization:
    - Exact job titles suitable for person_titles filtering
    - Professional skills and keywords for precise targeting
    - Company characteristics for organization-level filtering
    - Technology adoption patterns for intent signaling
    - Geographic and industry targeting for market focus

    Once you provide your product and company details, I will execute the streamlined research process and deliver your optimized Apollo.io search parameters as a single JSON object.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}

    Ready to generate your Apollo.io search parameters - just provide your product and company details to begin.
    """,
    sub_agents=[prospect_research_pipeline],
    output_key="prospect_researcher",
)

# root_agent = prospect_researcher