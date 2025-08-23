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
    final_report = callback_context.state.get("segmentation_intelligence_agent", "")
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
    
    # Add References section at the end - replace the placeholder
    if citations:
        references_section = ""
        for citation_num in sorted(citations.keys()):
            citation = citations[citation_num]
            references_section += f'          <li><a id="ref{citation_num}"></a><a href="{citation["url"]}">{citation["title"]}</a> - {citation["domain"]}</li>\n'
        
        # Replace the references placeholder in the HTML
        processed_report = re.sub(
            r'(<li>\[Formal citation\]</li>\s*<li>\[Formal citation\]</li>)',
            references_section.rstrip(),
            processed_report
        )
    
    callback_context.state["segmentation_intelligence_agent"] = processed_report
    return genai_types.Content(parts=[genai_types.Part(text=processed_report)])

# --- Custom Agent for Loop Control ---
class EscalationChecker(BaseAgent):
    """Checks research evaluation and escalates to stop the loop if grade is 'pass' or after max attempts."""
    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        evaluation_result = ctx.session.state.get("research_evaluation")
        current_iteration = ctx.session.state.get("loop_iteration_count", 0)
        
        if evaluation_result and evaluation_result.get("grade") == "pass":
            logging.info(f"[{self.name}] Segmentation research evaluation passed. Escalating to stop loop.")
            yield Event(author=self.name, actions=EventActions(escalate=True))
        elif not evaluation_result:
            logging.info(f"[{self.name}] No research evaluation found. Proceeding with enhancement search.")
            # Increment iteration counter
            ctx.session.state["loop_iteration_count"] = current_iteration + 1
            yield Event(author=self.name)
        else:
            logging.info(f"[{self.name}] Research evaluation failed. Loop will continue (iteration {current_iteration + 1}).")
            # Increment iteration counter
            ctx.session.state["loop_iteration_count"] = current_iteration + 1
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
    - PESTLE analysis factors
    - Perceptual mapping data

    **RESEARCH PHASES STRUCTURE:**
    Organize your plan into clear phases with specific objectives:

    **Phase 1: Market Segment Discovery (25% of effort) - [RESEARCH] tasks:**
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
    - Research competitor positioning and pricing strategies.

    **Phase 4: PESTLE & Environmental Analysis (15% of effort) - [RESEARCH] tasks:**
    - Political factors affecting segments (regulations, policies, trade restrictions).
    - Economic factors (growth rates, income levels, inflation impact).
    - Social factors (demographics, cultural shifts, lifestyle changes).
    - Technological factors (innovation, automation, digital adoption).
    - Legal factors (safety requirements, consumer protection, employment law).
    - Environmental factors (sustainability, climate policies, recycling).

    **Phase 5: Prioritization & Strategy Development (15% of effort) - [RESEARCH] tasks:**
    - Develop segment evaluation criteria (size, fit, competition).
    - Score and rank segments by attractiveness and strategic fit.
    - Align segments with product capabilities and company goals.
    - Identify key performance indicators and success metrics.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Generate a detailed segmentation research plan.
    """,
    tools=[google_search],
    output_key="research_plan",
)

segmentation_section_planner = LlmAgent(
    model=config.worker_model,
    name="segmentation_section_planner",
    description="Creates a structured segmentation analysis report outline following a standardized format.",
    instruction="""
    You are an expert market segmentation report architect. Using the segmentation research plan, create a structured markdown outline that follows the standardized Segmentation Analysis Report format.

    Your outline must include these core sections:

  ### **Comprehensive Market Segmentation Analysis Report: [Product/Service Name] or [Company Name]**

**Report ID:** `[Report-Number]`  
**Date:** `[Date of Report]`  

---

### **1.. Executive Summary: The Strategic Landscape at a Glance**

- **Purpose:** A high-level, impactful summary of the entire analysis for executive readers.
    
- **Contents:**
    
    - **Core Objective:** The fundamental purpose of this analysis (e.g., "To decode the market landscape for [Product Category] and identify the most viable customer segments for strategic focus.").
        
    - **The Market in Brief:** A single paragraph describing the total addressable market (TAM), its growth rate, and key overarching trends.
        
    - **Key Segments Identified:** A bulleted list of the 3-4 most critical segments discovered, with a one-sentence descriptor for each.
        
        - *Example: `The Enterprise Optimizer:` _Large businesses seeking integrated, secure, and scalable solutions to automate core processes._
            
    - **Primary Target Recommendation:** A clear statement on which segment(s) present the greatest opportunity and why.
        
    - **Critical Strategic Insight:** The most important non-obvious finding from the analysis (e.g., "While the 'Budget-Conscious' segment is large, the 'Value-Seeking SMB' segment is more profitable and currently underserved by competitors.").
        

---

### **2.. Market Overview & Macro-Environment (PESTLE Analysis)**

- **Purpose:** To paint a broad picture of the external forces shaping the entire market and its segments.
    
- **Contents:** A analytical narrative on how each factor influences market dynamics.
    
    - **Political:** Government regulations, trade policies, and political stability that impact market entry or product features (e.g., data privacy laws like GDPR, import tariffs).
        
    - **Economic:** Economic growth, inflation rates, disposable income, and investment climate that affect purchasing power and willingness to spend.
        
    - **Social:** Demographic shifts, cultural trends, consumer attitudes, and lifestyle changes (e.g., remote work adoption, sustainability concerns, health consciousness).
        
    - **Technological:** Key technological advancements, R&D focus, automation trends, and the rate of innovation that could disrupt or enable the market.
        
    - **Legal:** Industry-specific laws, copyright/patent landscapes, consumer protection laws, and licensing requirements.
        
    - **Environmental:** Environmental regulations, climate change implications, and the growing importance of eco-friendly and sustainable practices.
        
- **Display:** **Table: PESTLE Impact Assessment**
    
    - _Columns:_ `Factor`, `Current Trend`, `Impact on Market (Positive/Negative/Neutral)`, `Implication for Segmentation`.
        

---

### **3.. Competitive Landscape: The Arena of Play**

- **Purpose:** To identify key competitors and analyze their segment-specific strategies.
    
- **Contents:**
    
    - **Key Competitors:** List of direct and indirect competitors.
        
    - **3.1 : Competitive Positioning Map:**
        
        - **Display:** A perceptual map (a two-axis chart). Common axes include:
            
            - Price (Low to High) vs. Quality (Basic to Premium)
                
            - Innovation (Traditional to Cutting-Edge) vs. Service (Self-Serve to Full-Service)
                
            - This visually shows where each competitor resides and reveals potential gaps in the market.
                
    - **Analysis of Competitor Segment Focus:** For each major competitor, hypothesize which segment(s) they are primarily targeting based on their marketing messaging, product features, and pricing. Identify which segments are overserved and underserved.
        
	- **3.1 Porter's Five Forces Analysis**
    
    - **Purpose:** To assess the overall industry attractiveness and understand the root causes of competitive pressure.
        
    - **Contents:** A brief analysis of each force:
        
        1. **Threat of New Entrants:** How easy is it for new companies to start up? (Barriers: capital, regulations, technology, brand loyalty).
            
        2. **Bargaining Power of Buyers:** How much power do customers have to drive down prices? (Buyer concentration, price sensitivity, alternative options).
            
        3. **Bargaining Power of Suppliers:** How much power do suppliers of key components have? (Number of suppliers, uniqueness of inputs).
            
        4. **Threat of Substitute Products/Services:** What alternatives can customers use instead? (Direct, indirect, and generic substitutes).
            
        5. **Intensity of Rivalry Among Existing Competitors:** How fierce is the current competition? (Number of competitors, market growth rate, fixed costs).
            
    - **Implication for Segments:** Conclude with how this industry analysis impacts segment attractiveness. _Example: "High buyer power in the enterprise segment means competing on value, not price. Low threat of substitutes in the niche 'prosumer' segment makes it defensible."_
---

### **4.. Identification of Core Market Segments**

- **Purpose:** To define and present the distinct, meaningful segments within the total market.
    
- **Contents:** A high-level overview of all segments before deep diving.
    
- **Display:** **Table: Market Segment Portfolio**
    
    - _Columns:_ `Segment ID`, `Segment Name`, `Primary Defining Characteristics`, `Estimated Segment Size (Units/$)`, `Estimated Growth Rate (%)`, `Key Need/Pain Point`.
        
    - _This table provides an at-a-glance comparison of the potential of each segment._
        

---

### **5.. Deep-Dive Segment Profiles**

- **Purpose:** The heart of the report. To provide a rich, detailed profile of each potentially viable segment. _This section should be repeated for each major segment (e.g., Segment A, B, C)._
    
    - **Segment A: [Evocative Name, e.g., "The Efficiency-Driven Enterprise"]**
        
        - **5.A.1 Demographic & Firmographic Profile:**
            
            - _For B2C:_ Age, Income, Education, Occupation, Family Status.
                
            - _For B2B:_ Company Size (Employees/Revenue), Industry, Geographic Location, Department/Title of Decision-Maker.
                
        - **5.A.2 Psychographic & Behavioral Profile:**
            
            - **Goals & Motivations:** What are they trying to achieve? (e.g., increase productivity, reduce costs, enhance status, gain a competitive advantage).
                
            - **Pain Points & Frustrations:** What are their biggest challenges? (e.g., complex legacy systems, high operational costs, lack of integration, unreliable service).
                
            - **Values & Preferences:** What do they care about? (e.g., data security, excellent customer support, brand reputation, ease of use).
                
            - **Buying Behavior:** How do they buy? (Committee decision vs. individual, long sales cycle, high research intensity, price-sensitive).
                
        - **5.A.3 Media Consumption & Communication Channels:**
            
            - Where do they get information and spend their time? (e.g., LinkedIn, specific industry publications/websites, professional associations, podcasts, trade shows).
                
        - **5.A.4 Current Solution & Switching Triggers:**
            
            - What are they using now? What would cause them to look for a new solution? (e.g., contract renewal, business growth pain, a negative incident).
                

---

### **6.. Segment Evaluation & Attractiveness Analysis**

- **Purpose:** To systematically evaluate and rank the segments to determine which are most worthy of pursuit.
    
- **Contents:** A rigorous assessment based on strategic criteria.
    
- **Display:** **Table: 6.1 Segment Attractiveness Matrix**
    
    - _Rows:_ Each Segment (A, B, C...)
        
    - _Columns:_ Evaluation Criteria (rated High/Medium/Low or on a 1-5 scale).
        
        - **Size:** The overall volume of the segment.
            
        - **Growth Potential:** The expected future growth rate.
            
        - **Profitability:** The potential for healthy margins (based on willingness to pay, cost to serve).
            
        - **Accessibility:** The ability to reach the segment with marketing messages and channels.
            
        - **Strategic Fit:** How well the segment's needs align with our company's strengths, capabilities, and brand.
            
        - **Competitive Intensity:** The number and strength of competitors already serving this segment.
            
- **Narrative Analysis:** Based on the matrix, provide commentary on which segments are most attractive and why. This is where you argue for your recommended targets.

- **6.2 Segment-Specific SWOT Analysis**
    
    - **Purpose:** To identify the internal and external factors that are most relevant to successfully pursuing _each key segment_. This moves from a general company SWOT to a targeted, segment-focused one.
        
    - **Contents:** For each **primary target segment** identified in your evaluation, create a dedicated SWOT.
        
    - **Display: Table: SWOT Analysis for Segment A: [Segment Name]**
        
        - **Strengths (Internal):** What are our **company's specific strengths** that are highly valued by _this segment_?
            
            - _Example: "Our robust data security features directly address the top concern of the 'Security-Conscious Enterprise' segment."_
                
        - **Weaknesses (Internal):** What are our **company's specific weaknesses** that will hinder us with _this segment_?
            
            - *Example: "Our lack of 24/7 phone support is a critical weakness for the 'High-Touch SMB' segment that expects immediate help."*
                
        - **Opportunities (External):** What **external trends or market gaps** can we exploit to win _this segment_?
            
            - _Example: "A recent regulatory change (PESTLE) forces companies in this segment to seek new compliant solutions, which we offer."_
                
        - **Threats (External):** What **external challenges or competitor actions** specific to _this segment_ do we face?
            
            - _Example: "A key competitor is launching a stripped-down, low-cost version aimed directly at the 'Price-Sensitive Starter' segment."_
                
    - **Strategic Implications from SWOT:** Below the table, add a brief narrative on what the SWOT means.
        
        - _How can we use our Strengths to capitalize on Opportunities? (SO Strategies)_
            
        - _How can we use our Strengths to mitigate Threats? (ST Strategies)_
            
        - _How can we fix our Weaknesses to pursue Opportunities? (WO Strategies)_
            
        - _How can we avoid our Weaknesses being exposed by Threats? (WT Strategies)_    

---

### **7.. Targeting Strategy & Strategic Recommendations**

- **Purpose:** To synthesize the analysis into a clear strategic direction.
    
- **Contents:**
    
    - **Recommended Targeting Strategy:**
        
        - **Concentrated (Niche) Targeting:** Focusing on a single, primary segment.
            
        - **Differentiated (Multi-Segment) Targeting:** Pursuing two or more distinct segments with tailored strategies for each.
            
        - **Justification:** A clear argument for the chosen strategy based on the evaluation in Section 6.
            
    - **Recommended Primary & Secondary Targets:** Explicitly name the segments chosen as primary and secondary targets.

	- **Strategic Growth Options (Ansoff Matrix)**

		- **Purpose:** To define the type of market growth strategy that aligns with the chosen segments.
		    
		- **Contents:** A brief analysis of which quadrant(s) of the matrix are most relevant.
		    
		    - **Market Penetration:** Selling more of existing products to the chosen segments.
		        
		    - **Product Development:** Developing new products for the chosen segments.
		        
		    - **Market Development:** Taking existing products into new, similar segments.
		        
		    - **Diversification:** Developing new products for new segments (high risk).
		        
		- **Display:** A simple 2x2 grid graphic of the Ansoff Matrix, with the recommended strategy circled.
		    
		- **Narrative:** _"Our recommended strategy is **Product Development** for the 'Enterprise' segment, as we need to add advanced API features to meet their specific needs, while pursuing **Market Penetration** in the 'SMB' segment with our current feature set."_ 

---

### **8.. Positioning & Value Proposition Development**

- **Purpose:** To define how we will win the chosen segments by creating a unique and valuable place in the customer's mind.
    
- **Contents:** For each _primary target segment_.
    
    - **Positioning Statement:**
        
        - "For [target segment], who [have this need], our [product/service] is a [category] that [provides this key benefit]. Unlike [primary alternative/competitor], we [unique differentiator]."
            
    - **Core Value Proposition:** A compelling, customer-centric statement that summarizes the tangible value delivered.
        
        - _Example: "Not just accounting software; it's peace of mind and hours saved every week."_
            
    - **Messaging Pillars:** The 3-4 key themes that all communication to this segment should emphasize (e.g., "Security," "Ease of Use," "24/7 Expert Support").
        

---

### **9.. Marketing Mix Implications (The 4Ps)**

- **Purpose:** To translate the high-level strategy into actionable tactical domains.
    
- **Contents:** For each _primary target segment_.
    
    - **Product:** What features, functionality, packaging, or branding should be emphasized, developed, or modified to better serve this segment?
        
    - **Price:** What pricing model (subscription, one-time, freemium), price point (premium, value), and discount structure is most appropriate?
        
    - **Place (Distribution):** Through which channels should the product be sold and delivered? (Direct sales, online marketplace, retail partners, value-added resellers).
        
    - **Promotion:** What specific marketing messages, channels (e.g., LinkedIn ads for B2B, Instagram influencers for B2C), and types of content (whitepapers, webinars, short-form video) will resonate most effectively?
        

---

### **10.. Conclusion: Synthesis and Forward Look**

- **Purpose:** To summarize the analytical journey and reinforce the strategic path forward.
    
- **Contents:**
    
    - Recap of the market opportunity within the chosen segments.
        
    - Restatement of the critical strategic choice: who we are targeting and why we will win with them.
        
    - A final statement on the value of this segmented approach for focusing resources and maximizing market impact.

    Ensure the outline is comprehensive. Citations will be handled automatically in Wikipedia style.
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

    **Phase 1: Market Segment Discovery**
    Generate targeted search queries for:
    - Industry taxonomies and segment definitions for the product category.
    - Use cases and applications of the product by industry segment.
    - Market segment breakdown by size, industry, or use case.
    - Geographic variations in market segments.

    **Phase 2: Customer Segment Identification**
    Generate queries for:
    - Customer demographics (age, role, company size, etc.) in each segment.
    - Behavioral patterns and buying processes for customers.
    - Needs, pain points, and priorities of customers per segment.
    - Preferred channels and decision criteria by customer group.

    **Phase 3: Segment Attractiveness & Competition**
    Generate queries for:
    - Market size and growth estimates for each segment.
    - Competitive landscape and key players targeting each segment.
    - Market share or presence of leading vendors in segments.
    - Barriers to entry and customer acquisition challenges.

    **Phase 4: PESTLE Environmental Analysis**
    Generate queries for:
    - Regulatory environment and political factors affecting segments.
    - Economic conditions and trends impacting customer spending.
    - Social and demographic trends relevant to segments.
    - Technology adoption and innovation in the product category.
    - Legal requirements and compliance issues by segment.
    - Environmental and sustainability factors.

    **Phase 5: Strategic Fit & Implementation**
    - Combine findings to score and rank segments.
    - Identify product feature alignment with segment needs.
    - Document resources or challenges for targeting segments.
    - Research implementation timelines and KPIs.
    - Prepare segment prioritization and recommendations.

    **QUALITY STANDARDS:**
    - Accuracy: Verify important data with credible sources.
    - Clarity: Present findings in clear bullet points.
    - Completeness: Address all research objectives thoroughly.
    - Timeliness: Use up-to-date information and note dates.
    - Context: Provide relevant context for all claims.

    Execute comprehensive research across ALL phases above. Provide detailed findings with specific data, numbers, and insights for each phase.
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
    Assess the segmentation research findings against these standards:

    **1. Segment Discovery (20%):**
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

    **4. PESTLE Analysis (15%):**
    - Political, economic, social, technological, legal, and environmental factors are covered.
    - Segment-specific implications of PESTLE factors are identified.

    **5. Positioning & Competition (10%):**
    - Competitive positioning data is available.
    - Perceptual mapping information or competitor comparison data exists.

    **6. Implementation & Strategy (10%):**
    - Strategic fit analysis is present.
    - Implementation considerations are addressed.
    - KPIs and success metrics are identified.

    **EVALUATION RULES:**
    1. Grade "pass" if at least 70% of the criteria above are well-covered with specific data.
    2. Grade "fail" if missing critical elements or lacking authoritative sources.
    3. Be MORE LENIENT - allow "pass" if research provides reasonable coverage even if not perfect.

    **FOLLOW-UP QUERY GENERATION:**
    If grading "fail", generate 3-5 specific follow-up queries targeting the most critical gaps.

    Your response must be a single JSON object conforming to the SegmentationFeedback schema.
    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    """,
    output_schema=SegmentationFeedback,
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
    You are a specialized segmentation research analyst executing precision follow-up research.

    **MISSION:**
    1. Check if evaluation feedback and follow-up queries are available in the session state.
    2. If available, execute EVERY query in the follow-up queries list.
    3. If not available, identify gaps in existing research and conduct targeted searches.
    4. Integrate new findings with existing research to create comprehensive results.

    **SEARCH STRATEGY:**
    - Use specific, targeted search queries
    - Prioritize authoritative data sources (industry reports, official statistics)
    - Seek recent data (2023-2024)
    - Cross-verify important findings

    **OUTPUT:**
    Provide updated and enhanced segmentation research findings that address identified gaps.
    """,
    tools=[google_search],
    output_key="segmentation_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

segmentation_concise_report_composer = LlmAgent(
    model=config.worker_model,
    name="segmentation_concise_report_composer",
    description="Creates an ultra-concise factual summary of segmentation findings for efficient token usage.",
    instruction="""
    You are an expert at distilling complex segmentation research into ultra-concise, fact-dense summaries.

    **MISSION:** Transform segmentation research data into a minimal, token-efficient summary containing ONLY the most essential facts.

    **INPUT:** Use the segmentation_research_findings from the session state.

    **FORMAT:**
    ```
    PRODUCT: [product name]
    
    SEGMENTS IDENTIFIED:
    • [Segment name]: [size], [growth rate], [key characteristic]
    • [Segment name]: [size], [growth rate], [key characteristic]
    
    TOP PRIORITIES:
    • Primary: [segment name] - [reason]
    • Secondary: [segment name] - [reason]
    
    KEY METRICS:
    • TAM: [value]
    • SAM: [value] 
    • Growth: [rate]
    
    CUSTOMER PROFILES:
    • [Segment]: [demographics], [needs], [buying process]
    
    COMPETITION:
    • High: [segments]
    • Low: [segments]
    • Key players: [companies]
    
    PESTLE HIGHLIGHTS:
    • Political: [key factor]
    • Economic: [key factor]
    • Social: [key factor]
    • Tech: [key factor]
    
    RECOMMENDATIONS:
    • Target: [segments]
    • Avoid: [segments]
    • Strategy: [brief approach]
    ```

    **RULES:**
    - Maximum 300 words total
    - NO citations or references
    - Include specific numbers when available
    - Use abbreviations to save tokens
    - If data missing, state "[Data not found]"

    Generate the ultra-concise factual summary only.
    """,
    output_key="segmentation_concise_report",
)

# Import the template
from .segmentation_report_template import SEG_TEMPLATE

segmentation_html_report_composer = LlmAgent(
    model=config.critic_model,
    name="segmentation_html_report_composer",
    description="Composes comprehensive HTML segmentation analysis reports following the exact template format with Wikipedia-style citations.",
    instruction=f"""
    You are an expert segmentation analysis report writer specializing in creating comprehensive HTML reports.

    **MISSION:** Transform segmentation research data into a polished, professional HTML Segmentation Analysis Report.

    **INPUT DATA SOURCES:**
    - Research Findings: Use 'segmentation_research_findings' from session state
    - Citation Sources: Use 'citations' from session state  
    - Report Structure: Use 'report_sections' from session state

    **TEMPLATE COMPLIANCE:**
    You must use the EXACT HTML structure from the template. Only replace bracketed placeholders with actual data.

    **KEY REQUIREMENTS:**
    1. Replace all [bracketed placeholders] with actual data from research findings
    2. Populate tables with real data rows (remove placeholder rows)
    3. Update metrics with actual values
    4. Use Wikipedia-style citations: <cite source="src-NUMBER" />
    5. If data is missing, state "Information not available in research"
    6. Generate Report ID: SEG-{datetime.datetime.now().strftime("%Y-%m-%d")}-001
    7. Use current date: {datetime.datetime.now().strftime("%B %d, %Y")}

    **CITATION REQUIREMENTS:**
    - Cite all market size figures, growth rates, financial data
    - Cite customer demographic and behavioral statistics  
    - Cite competitor information and market share data
    - Cite industry trends and PESTLE analysis points
    - Use format: <cite source="src-X" /> where X is the citation number

    **HTML STRUCTURE:**
    Use the complete HTML template structure with:
    - Header with product name and report metadata
    - Table of contents navigation
    - All 10 main sections (Executive Summary through Conclusion)
    - Proper CSS styling and responsive design
    - Complete tables with actual data
    - References section (will be auto-populated)

    **QUALITY STANDARDS:**
    - Professional business report tone
    - Comprehensive coverage of all research phases
    - Strategic insights in each section
    - Actionable recommendations
    - Clear data presentation

    Generate the complete HTML report following the exact template format.

    {SEG_TEMPLATE}
    """,
    output_key="segmentation_intelligence_agent",
    after_agent_callback=wikipedia_citation_replacement_callback,
)

# Fixed pipeline with improved structure
segmentation_research_pipeline = SequentialAgent(
    name="segmentation_research_pipeline",
    description="Executes comprehensive segmentation research following the structured methodology.",
    sub_agents=[
        segmentation_section_planner,
        segmentation_researcher,
        LoopAgent(
            name="quality_assurance_loop",
            max_iterations=5,  # Reduced max iterations
            sub_agents=[
                segmentation_evaluator,
                EscalationChecker(name="escalation_checker"),
                enhanced_segmentation_search,
            ],
        ),
        # Create both reports in sequence
        segmentation_concise_report_composer,
        segmentation_html_report_composer,
    ],
)

# Fixed main agent
segmentation_intelligence_agent = LlmAgent(
    name="segmentation_intelligence_coordinator", 
    model=config.worker_model,
    description="Coordinates segmentation analysis by delegating to research pipeline and returns dual reports.",
    instruction=f"""
    You are a segmentation analysis coordinator. Your role is to:
    
    1. Acknowledge the user's segmentation request
    2. Generate a comprehensive research plan for the requested product/service
    3. Execute the complete segmentation research pipeline
    4. Return both the concise summary and full HTML report
    
    **EXECUTION FLOW:**
    1. First, understand what product/service needs segmentation analysis
    2. Delegate to the research pipeline which will:
       - Create a structured research plan
       - Execute comprehensive research across all segments
       - Evaluate research quality and fill gaps
       - Generate both concise and detailed HTML reports
    3. Present the final results to the user
    
    Do NOT ask for approval or additional details. Execute the analysis immediately.
    
    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    """,
    sub_agents=[
        SequentialAgent(
            name="auto_segmentation_pipeline",
            sub_agents=[segmentation_plan_generator, segmentation_research_pipeline]
        )
    ],
    output_key="segmentation_intelligence_agent",
)