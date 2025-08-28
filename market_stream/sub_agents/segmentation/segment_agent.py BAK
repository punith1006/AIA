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

from ...config import config

from .segmentation_report_template import SEG_TEMPLATE


# --- Structured Input Model ---
class SegmentationInput(BaseModel):
    """Input model for market segmentation analysis."""
    
    product_name: str = Field(description="Name of the product or service")
    product_description: str = Field(description="Detailed description of the product/service")
    industry_market: str = Field(description="The industry or market category")
    current_understanding: str = Field(description="Current understanding of target demographics and positioning")


# --- Structured Output Models ---
class SearchQuery(BaseModel):
    """Model representing a specific search query for web search."""

    search_query: str = Field(
        description="A highly specific and targeted query for web search."
    )


class SegmentationFeedback(BaseModel):
    """Model for providing evaluation feedback on segmentation research quality."""

    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result. 'pass' if the research is sufficient, 'fail' if it needs revision."
    )
    comment: str = Field(
        description="Detailed explanation of the evaluation, highlighting strengths and/or weaknesses of the segmentation research."
    )
    follow_up_queries: list[SearchQuery] | None = Field(
        default=None,
        description="A list of specific, targeted follow-up search queries needed to fix research gaps. This should be null or empty if the grade is 'pass'.",
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


# --- Custom Agent for Loop Control ---
class EscalationChecker(BaseAgent):
    """Checks research evaluation and escalates to stop the loop if grade is 'pass'."""

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        evaluation_result = ctx.session.state.get("segmentation_evaluation")
        if evaluation_result and evaluation_result.get("grade") == "pass":
            logging.info(
                f"[{self.name}] Segmentation research evaluation passed. Escalating to stop loop."
            )
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            logging.info(
                f"[{self.name}] Segmentation research evaluation failed or not found. Loop will continue."
            )
            yield Event(author=self.name)


# --- AGENT DEFINITIONS ---
segmentation_plan_generator = LlmAgent(
    model=config.search_model,
    name="segmentation_plan_generator",
    description="Generates a comprehensive market segmentation research plan based on product input.",
    instruction=f"""
    You are a market segmentation research strategist. Your job is to create a comprehensive research plan for market segmentation analysis based on the provided product information.

    **INPUT STRUCTURE:**
    You will receive structured product information including:
    - Product name and description
    - Industry/market context
    - Current understanding of target demographics

    **YOUR TASK:**
    Create a detailed 10-point research plan that covers all aspects needed for comprehensive market segmentation analysis. Each research goal should be classified as either:
    - **[RESEARCH]**: Information gathering and analysis tasks
    - **[DELIVERABLE]**: Synthesis and output creation tasks

    **REQUIRED RESEARCH AREAS TO COVER:**
    ### **Comprehensive Market Segmentation Analysis Report: [Product/Service Name] or [Company Name]**

**Report ID:**  `[Report-Number]`  
**Date:**  `[Date of Report]`  

---

### **1.. Executive Summary: The Strategic Landscape at a Glance**

- **Purpose:**  A high-level, impactful summary of the entire analysis for executive readers.
    
- **Contents:**
    
    - **Core Objective:**  The fundamental purpose of this analysis (e.g., "To decode the market landscape for [Product Category] and identify the most viable customer segments for strategic focus.").
        
    - **The Market in Brief:**  A single paragraph describing the total addressable market (TAM), its growth rate, and key overarching trends.
        
    - **Key Segments Identified:**  A bulleted list of the 3-4 most critical segments discovered, with a one-sentence descriptor for each.
        
        - *Example:  `The Enterprise Optimizer:`  _Large businesses seeking integrated, secure, and scalable solutions to automate core processes._
            
    - **Primary Target Recommendation:**  A clear statement on which segment(s) present the greatest opportunity and why.
        
    - **Critical Strategic Insight:**  The most important non-obvious finding from the analysis (e.g., "While the 'Budget-Conscious' segment is large, the 'Value-Seeking SMB' segment is more profitable and currently underserved by competitors.").
        

---

### **2.. Market Overview & Macro-Environment (PESTLE Analysis)**

- **Purpose:**  To paint a broad picture of the external forces shaping the entire market and its segments.
    
- **Contents:**  A analytical narrative on how each factor influences market dynamics.
    
    - **Political:**  Government regulations, trade policies, and political stability that impact market entry or product features (e.g., data privacy laws like GDPR, import tariffs).
        
    - **Economic:**  Economic growth, inflation rates, disposable income, and investment climate that affect purchasing power and willingness to spend.
        
    - **Social:**  Demographic shifts, cultural trends, consumer attitudes, and lifestyle changes (e.g., remote work adoption, sustainability concerns, health consciousness).
        
    - **Technological:**  Key technological advancements, R&D focus, automation trends, and the rate of innovation that could disrupt or enable the market.
        
    - **Legal:**  Industry-specific laws, copyright/patent landscapes, consumer protection laws, and licensing requirements.
        
    - **Environmental:**  Environmental regulations, climate change implications, and the growing importance of eco-friendly and sustainable practices.
        
- **Display:**  **Table: PESTLE Impact Assessment**
    
    - _Columns:_  `Factor`,  `Current Trend`,  `Impact on Market (Positive/Negative/Neutral)`,  `Implication for Segmentation`.
        

---

### **3.. Competitive Landscape: The Arena of Play**

- **Purpose:**  To identify key competitors and analyze their segment-specific strategies.
    
- **Contents:**
    
    - **Key Competitors:**  List of direct and indirect competitors.
        
    - **3.1 : Competitive Positioning Map:**
        
        - **Display:**  A perceptual map (a two-axis chart). Common axes include:
            
            - Price (Low to High) vs. Quality (Basic to Premium)
                
            - Innovation (Traditional to Cutting-Edge) vs. Service (Self-Serve to Full-Service)
                
            - This visually shows where each competitor resides and reveals potential gaps in the market.
                
    - **Analysis of Competitor Segment Focus:**  For each major competitor, hypothesize which segment(s) they are primarily targeting based on their marketing messaging, product features, and pricing. Identify which segments are overserved and underserved.
        
	- **3.1 Porter's Five Forces Analysis**
    
    - **Purpose:**  To assess the overall industry attractiveness and understand the root causes of competitive pressure.
        
    - **Contents:**  A brief analysis of each force:
        
        1. **Threat of New Entrants:**  How easy is it for new companies to start up? (Barriers: capital, regulations, technology, brand loyalty).
            
        2. **Bargaining Power of Buyers:**  How much power do customers have to drive down prices? (Buyer concentration, price sensitivity, alternative options).
            
        3. **Bargaining Power of Suppliers:**  How much power do suppliers of key components have? (Number of suppliers, uniqueness of inputs).
            
        4. **Threat of Substitute Products/Services:**  What alternatives can customers use instead? (Direct, indirect, and generic substitutes).
            
        5. **Intensity of Rivalry Among Existing Competitors:**  How fierce is the current competition? (Number of competitors, market growth rate, fixed costs).
            
    - **Implication for Segments:**  Conclude with how this industry analysis impacts segment attractiveness.  _Example: "High buyer power in the enterprise segment means competing on value, not price. Low threat of substitutes in the niche 'prosumer' segment makes it defensible."_
---

### **4.. Identification of Core Market Segments**

- **Purpose:**  To define and present the distinct, meaningful segments within the total market.
    
- **Contents:**  A high-level overview of all segments before deep diving.
    
- **Display:**  **Table: Market Segment Portfolio**
    
    - _Columns:_  `Segment ID`,  `Segment Name`,  `Primary Defining Characteristics`,  `Estimated Segment Size (Units/$)`,  `Estimated Growth Rate (%)`,  `Key Need/Pain Point`.
        
    - _This table provides an at-a-glance comparison of the potential of each segment._
        

---

### **5.. Deep-Dive Segment Profiles**

- **Purpose:**  The heart of the report. To provide a rich, detailed profile of each potentially viable segment.  _This section should be repeated for each major segment (e.g., Segment A, B, C)._
    
    - **Segment A: [Evocative Name, e.g., "The Efficiency-Driven Enterprise"]**
        
        - **5.A.1 Demographic & Firmographic Profile:**
            
            - _For B2C:_  Age, Income, Education, Occupation, Family Status.
                
            - _For B2B:_  Company Size (Employees/Revenue), Industry, Geographic Location, Department/Title of Decision-Maker.
                
        - **5.A.2 Psychographic & Behavioral Profile:**
            
            - **Goals & Motivations:**  What are they trying to achieve? (e.g., increase productivity, reduce costs, enhance status, gain a competitive advantage).
                
            - **Pain Points & Frustrations:**  What are their biggest challenges? (e.g., complex legacy systems, high operational costs, lack of integration, unreliable service).
                
            - **Values & Preferences:**  What do they care about? (e.g., data security, excellent customer support, brand reputation, ease of use).
                
            - **Buying Behavior:**  How do they buy? (Committee decision vs. individual, long sales cycle, high research intensity, price-sensitive).
                
        - **5.A.3 Media Consumption & Communication Channels:**
            
            - Where do they get information and spend their time? (e.g., LinkedIn, specific industry publications/websites, professional associations, podcasts, trade shows).
                
        - **5.A.4 Current Solution & Switching Triggers:**
            
            - What are they using now? What would cause them to look for a new solution? (e.g., contract renewal, business growth pain, a negative incident).
                

---

### **6.. Segment Evaluation & Attractiveness Analysis**

- **Purpose:**  To systematically evaluate and rank the segments to determine which are most worthy of pursuit.
    
- **Contents:**  A rigorous assessment based on strategic criteria.
    
- **Display:**  **Table: 6.1 Segment Attractiveness Matrix**
    
    - _Rows:_  Each Segment (A, B, C...)
        
    - _Columns:_  Evaluation Criteria (rated High/Medium/Low or on a 1-5 scale).
        
        - **Size:**  The overall volume of the segment.
            
        - **Growth Potential:**  The expected future growth rate.
            
        - **Profitability:**  The potential for healthy margins (based on willingness to pay, cost to serve).
            
        - **Accessibility:**  The ability to reach the segment with marketing messages and channels.
            
        - **Strategic Fit:**  How well the segment's needs align with our company's strengths, capabilities, and brand.
            
        - **Competitive Intensity:**  The number and strength of competitors already serving this segment.
            
- **Narrative Analysis:**  Based on the matrix, provide commentary on which segments are most attractive and why. This is where you argue for your recommended targets.

- **6.2 Segment-Specific SWOT Analysis**
    
    - **Purpose:**  To identify the internal and external factors that are most relevant to successfully pursuing  _each key segment_. This moves from a general company SWOT to a targeted, segment-focused one.
        
    - **Contents:**  For each  **primary target segment**  identified in your evaluation, create a dedicated SWOT.
        
    - **Display: Table: SWOT Analysis for Segment A: [Segment Name]**
        
        - **Strengths (Internal):**  What are our  **company's specific strengths**  that are highly valued by  _this segment_?
            
            - _Example: "Our robust data security features directly address the top concern of the 'Security-Conscious Enterprise' segment."_
                
        - **Weaknesses (Internal):**  What are our  **company's specific weaknesses**  that will hinder us with  _this segment_?
            
            - *Example: "Our lack of 24/7 phone support is a critical weakness for the 'High-Touch SMB' segment that expects immediate help."*
                
        - **Opportunities (External):**  What  **external trends or market gaps**  can we exploit to win  _this segment_?
            
            - _Example: "A recent regulatory change (PESTLE) forces companies in this segment to seek new compliant solutions, which we offer."_
                
        - **Threats (External):**  What  **external challenges or competitor actions**  specific to  _this segment_  do we face?
            
            - _Example: "A key competitor is launching a stripped-down, low-cost version aimed directly at the 'Price-Sensitive Starter' segment."_
                
    - **Strategic Implications from SWOT:**  Below the table, add a brief narrative on what the SWOT means.
        
        - _How can we use our Strengths to capitalize on Opportunities? (SO Strategies)_
            
        - _How can we use our Strengths to mitigate Threats? (ST Strategies)_
            
        - _How can we fix our Weaknesses to pursue Opportunities? (WO Strategies)_
            
        - _How can we avoid our Weaknesses being exposed by Threats? (WT Strategies)_    

---

### **7.. Targeting Strategy & Strategic Recommendations**

- **Purpose:**  To synthesize the analysis into a clear strategic direction.
    
- **Contents:**
    
    - **Recommended Targeting Strategy:**
        
        - **Concentrated (Niche) Targeting:**  Focusing on a single, primary segment.
            
        - **Differentiated (Multi-Segment) Targeting:**  Pursuing two or more distinct segments with tailored strategies for each.
            
        - **Justification:**  A clear argument for the chosen strategy based on the evaluation in Section 6.
            
    - **Recommended Primary & Secondary Targets:**  Explicitly name the segments chosen as primary and secondary targets.

	- **Strategic Growth Options (Ansoff Matrix)**

		- **Purpose:**  To define the type of market growth strategy that aligns with the chosen segments.
		    
		- **Contents:**  A brief analysis of which quadrant(s) of the matrix are most relevant.
		    
		    - **Market Penetration:**  Selling more of existing products to the chosen segments.
		        
		    - **Product Development:**  Developing new products for the chosen segments.
		        
		    - **Market Development:**  Taking existing products into new, similar segments.
		        
		    - **Diversification:**  Developing new products for new segments (high risk).
		        
		- **Display:**  A simple 2x2 grid graphic of the Ansoff Matrix, with the recommended strategy circled.
		    
		- **Narrative:**  _"Our recommended strategy is  **Product Development**  for the 'Enterprise' segment, as we need to add advanced API features to meet their specific needs, while pursuing  **Market Penetration**  in the 'SMB' segment with our current feature set."_ 

---

### **8.. Positioning & Value Proposition Development**

- **Purpose:**  To define how we will win the chosen segments by creating a unique and valuable place in the customer's mind.
    
- **Contents:**  For each  _primary target segment_.
    
    - **Positioning Statement:**
        
        - "For [target segment], who [have this need], our [product/service] is a [category] that [provides this key benefit]. Unlike [primary alternative/competitor], we [unique differentiator]."
            
    - **Core Value Proposition:**  A compelling, customer-centric statement that summarizes the tangible value delivered.
        
        - _Example: "Not just accounting software; it's peace of mind and hours saved every week."_
            
    - **Messaging Pillars:**  The 3-4 key themes that all communication to this segment should emphasize (e.g., "Security," "Ease of Use," "24/7 Expert Support").
        

---

### **9.. Marketing Mix Implications (The 4Ps)**

- **Purpose:**  To translate the high-level strategy into actionable tactical domains.
    
- **Contents:**  For each  _primary target segment_.
    
    - **Product:**  What features, functionality, packaging, or branding should be emphasized, developed, or modified to better serve this segment?
        
    - **Price:**  What pricing model (subscription, one-time, freemium), price point (premium, value), and discount structure is most appropriate?
        
    - **Place (Distribution):**  Through which channels should the product be sold and delivered? (Direct sales, online marketplace, retail partners, value-added resellers).
        
    - **Promotion:**  What specific marketing messages, channels (e.g., LinkedIn ads for B2B, Instagram influencers for B2C), and types of content (whitepapers, webinars, short-form video) will resonate most effectively?
        

---

### **10.. Conclusion: Synthesis and Forward Look**

- **Purpose:**  To summarize the analytical journey and reinforce the strategic path forward.
    
- **Contents:**
    
    - Recap of the market opportunity within the chosen segments.
        
    - Restatement of the critical strategic choice: who we are targeting and why we will win with them.
        
    - A final statement on the value of this segmented approach for focusing resources and maximizing market impact.

    **TOOL USE:**
    Use `google_search` only if you need to clarify industry terminology, market categories, or recent developments that might affect the research approach. Do not research the actual content - that's for the next agent.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    """,
    tools=[google_search],
    output_key="segmentation_research_plan",
)

segmentation_researcher = LlmAgent(
    model=config.search_model,
    name="segmentation_researcher",
    description="Conducts comprehensive market segmentation research.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a market segmentation research specialist. Execute the segmentation research plan comprehensively.

    **EXECUTION PHASES:**

    **Phase 1: Market Environment Analysis**
    - Research market size, growth trends, and key drivers
    - Conduct PESTLE analysis for macro-environmental factors
    - Analyze competitive landscape and identify key players
    - Research industry structure and Porter's Five Forces

    **Phase 2: Customer Research**
    - Identify distinct customer segments based on demographics, psychographics, and behavior
    - Research buying patterns, decision-making processes, and purchase triggers
    - Analyze price sensitivity and willingness to pay across segments
    - Study geographic and cultural variations

    **Phase 3: Channel and Communication Analysis**
    - Research preferred sales and distribution channels by segment
    - Analyze media consumption and communication preferences
    - Study technology adoption and digital readiness levels
    - Identify key influencers and decision-makers

    **Phase 4: Regulatory and Compliance**
    - Research relevant regulations and compliance requirements
    - Analyze legal considerations for market entry and operations

    **SEARCH STRATEGY:**
    For each research area, formulate 4-5 targeted search queries to gather comprehensive information. Focus on:
    - Recent market reports and industry analysis
    - Customer surveys and behavioral studies
    - Competitive intelligence and positioning
    - Regulatory updates and requirements

    **OUTPUT REQUIREMENTS:**
    Organize findings by segment and provide detailed profiles including:
    - Demographics and firmographics
    - Psychographics and behavioral patterns
    - Pain points and motivations
    - Communication preferences and channels
    - Competitive alternatives and switching factors
    """,
    tools=[google_search],
    output_key="segmentation_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

segmentation_evaluator = LlmAgent(
    model=config.critic_model,
    name="segmentation_evaluator",
    description="Evaluates the completeness and quality of segmentation research.",
    instruction=f"""
    You are a market segmentation analysis quality assessor. Evaluate the research findings for completeness and depth.

    **EVALUATION CRITERIA:**
    1. **Market Analysis Completeness:** Is there sufficient data on market size, growth, and trends?
    2. **Segment Definition Quality:** Are segments clearly defined with distinct characteristics?
    3. **Competitive Analysis Depth:** Is competitive positioning and strategy well understood?
    4. **Customer Insights Richness:** Are customer needs, behaviors, and preferences well documented?
    5. **Channel and Communication Coverage:** Are preferred channels and communication methods identified?
    6. **PESTLE Analysis Thoroughness:** Are all macro-environmental factors adequately covered?
    7. **Data Recency and Reliability:** Is the information current and from credible sources?

    **CRITICAL ASSESSMENT:**
    Be rigorous in your evaluation. If any major gaps exist in:
    - Segment identification and profiling
    - Competitive landscape understanding
    - Market sizing and growth projections
    - Customer behavior and preferences
    - Regulatory and environmental factors

    Grade as "fail" and provide specific follow-up queries to address the gaps.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Your response must be a single, raw JSON object validating against the 'SegmentationFeedback' schema.
    """,
    output_schema=SegmentationFeedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="segmentation_evaluation",
)

enhanced_segmentation_researcher = LlmAgent(
    model=config.search_model,
    name="enhanced_segmentation_researcher",
    description="Executes follow-up research to fill gaps in segmentation analysis.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are conducting a refinement pass on segmentation research based on identified gaps.

    1. Review the 'segmentation_evaluation' state key to understand feedback and required improvements.
    2. Execute EVERY query listed in 'follow_up_queries' using the 'google_search' tool.
    3. Focus on filling specific gaps identified in the evaluation.
    4. Synthesize new findings and COMBINE them with existing research in 'segmentation_research_findings'.
    5. Ensure the enhanced research addresses all evaluation concerns.

    Your output MUST be the complete, improved segmentation research findings.
    """,
    tools=[google_search],
    output_key="segmentation_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

# FIXED: Create concise PLAINTEXT report (not HTML)
concise_plaintext_report_generator = LlmAgent(
    model=config.worker_model,
    name="concise_plaintext_report_generator",
    description="Creates a concise plaintext segmentation report for AI agent consumption.",
    instruction="""
    Create a high-quality concise market segmentation summary in PLAINTEXT format optimized for AI agent consumption.

    **PURPOSE:** Create a readable, actionable plaintext summary that captures essential segmentation insights.

    **FORMAT:** Well-structured plaintext with clear sections and bullet points.

    **STRUCTURE:**

    # MARKET SEGMENTATION ANALYSIS SUMMARY
    ## Product: [Product Name]
    ## Date: [Current Date]
    
    ### MARKET OVERVIEW
    • Market Size: [TAM/SAM figures]
    • Growth Rate: [CAGR and key drivers]
    • Key Trends: [2-3 most important market trends]
    
    ### PRIMARY MARKET SEGMENTS
    
    #### 1. [Segment Name] - [Brief descriptor]
    • Size: [Market size/percentage]
    • Demographics: [Key demographic characteristics]
    • Key Needs: [Primary pain points and motivations]
    • Behavior: [Buying patterns and preferences]
    • Growth: [Growth rate and potential]
    
    #### 2. [Segment Name] - [Brief descriptor]
    • Size: [Market size/percentage]
    • Demographics: [Key demographic characteristics]
    • Key Needs: [Primary pain points and motivations]
    • Behavior: [Buying patterns and preferences]
    • Growth: [Growth rate and potential]
    
    #### 3. [Segment Name] - [Brief descriptor]
    • Size: [Market size/percentage]
    • Demographics: [Key demographic characteristics]
    • Key Needs: [Primary pain points and motivations]
    • Behavior: [Buying patterns and preferences]
    • Growth: [Growth rate and potential]
    
    ### COMPETITIVE LANDSCAPE
    • Key Players: [Top 3-4 competitors]
    • Market Dynamics: [Competitive intensity and positioning]
    • Gaps: [Underserved segments or opportunities]
    
    ### KEY STRATEGIC INSIGHTS
    • Most Attractive Segment: [Primary recommendation with rationale]
    • Secondary Target: [Secondary recommendation]
    • Critical Success Factors: [Key requirements for success]
    • Market Entry Strategy: [Recommended approach]
    
    ### PESTLE HIGHLIGHTS
    • Political: [Most relevant political factors]
    • Economic: [Key economic considerations]
    • Social: [Important social trends]
    • Technology: [Technological opportunities/threats]
    • Legal: [Relevant regulatory considerations]
    • Environmental: [Sustainability factors]
    
    ### TARGETING RECOMMENDATIONS
    • Primary Target: [Segment name and justification]
    • Secondary Target: [If applicable]
    • Approach: [Concentrated vs. Differentiated targeting]
    • Resource Allocation: [Strategic focus recommendations]
    
    **QUALITY REQUIREMENTS:**
    - Maximum 800 words total
    - Use clear section headers and bullet points
    - Include specific data points and metrics
    - Focus on actionable insights
    - Maintain professional tone
    - Ensure all segments are adequately covered
    """,
    output_key="segmentation_concise_plaintext",
)

# FIXED: Create extensive HTML report using template
extensive_html_report_generator = LlmAgent(
    model=config.critic_model,
    name="extensive_html_report_generator",
    description="Transforms segmentation research into a comprehensive HTML report using the SEG_TEMPLATE.",
    include_contents="none",
    instruction=SEG_TEMPLATE,
    output_key="segmentation_extensive_html_report",
)

# FIXED: Sequential pipeline with both report types
segmentation_pipeline = SequentialAgent(
    name="segmentation_pipeline",
    description="Executes comprehensive market segmentation analysis and generates both concise plaintext and extensive HTML reports.",
    sub_agents=[
        segmentation_researcher,
        LoopAgent(
            name="segmentation_refinement_loop",
            max_iterations=config.max_search_iterations,
            sub_agents=[
                segmentation_evaluator,
                EscalationChecker(name="segmentation_escalation_checker"),
                enhanced_segmentation_researcher,
            ],
        ),
        # Generate both report types in sequence
        concise_plaintext_report_generator,
        extensive_html_report_generator,
    ],
)

# FIXED: Main agent with updated instruction
segmentation_intelligence_agent = LlmAgent(
    name="market_segmentation_agent",
    model=config.worker_model,
    description="Market segmentation analysis agent that processes structured product input and generates comprehensive reports.",
    instruction=f"""
    You are a market segmentation analysis specialist. Process structured product input and generate comprehensive market segmentation reports.

    **INPUT PROCESSING:**
    You will receive structured input with:
    - product_name: Name of the product/service
    - product_description: Detailed product description
    - industry_market: Industry or market category
    - current_understanding: Existing knowledge of target demographics

    **WORKFLOW:**
    1. **Plan Generation:** Use `segmentation_plan_generator` to create a comprehensive research plan
    2. **Research Execution:** Delegate to `segmentation_pipeline` for complete analysis and report generation

    **OUTPUT:**
    The process will generate two distinct outputs:
    - **segmentation_concise_plaintext**: High-quality concise plaintext summary for AI consumption and quick reference
    - **segmentation_extensive_html_report**: Comprehensive HTML report using SEG_TEMPLATE for detailed analysis and presentation

    **QUALITY STANDARDS:**
    - Concise report: Focus on actionable insights, key segments, and strategic recommendations in readable plaintext format
    - Extensive report: Complete HTML analysis using template structure with all sections populated and properly cited

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    
    Always start by generating the research plan, then execute the full pipeline to produce both report formats.
    """,
    sub_agents=[segmentation_pipeline],
    tools=[AgentTool(segmentation_plan_generator)],
    output_key="segmentation_research_plan",
)