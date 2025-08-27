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

market_analysis_report = """
Market Analysis Report  
Client: Global Knowledge Tech  
Product: Master AI – The Leitner Way Professional AI Learning System  
Geographic Focus: Bangalore, India  

---

## 1. Executive Summary  

1.1 Market Definition and Scope  
- The “Professional AI Learning Systems” market comprises educational tools—online courses, certifications, bootcamps, executive programs—focused on delivering AI and machine learning (ML) knowledge to professionals and students. These systems leverage AI/ML, and sometimes immersive technologies (AR/VR), to enhance learning effectiveness and retention <a href="#ref1">[1]</a>.  
- This segment sits within the broader EdTech industry, targeting both B2C (individual learners) and B2B (corporate training, academic institutions) buyers, with a core focus on upskilling/reskilling for AI roles.  
- Geographic focus for this report is Bangalore, India, with contextual references to national (India) and global markets.

1.2 Key Market Size Metrics  
- Total Addressable Market (TAM)  
  • Global EdTech market was valued at USD 250.16 billion in 2024 and is projected to reach USD 721.15 billion by 2033 (CAGR 11.86% from 2025–2033) <a href="#ref3">[3]</a>.  
  • Global AI in Education sub-segment is estimated at USD 5.88 billion in 2024, growing to USD 32.27 billion by 2030 (CAGR 31.2% from 2025–2030) <a href="#ref2">[2]</a>.  

- Serviceable Available Market (SAM)  
  • Indian EdTech market was USD 4.3 billion in 2022 (CAGR 16.8% from 2017–2022) <a href="#ref12">[12]</a>; another source reports USD 6 billion in 2022 (CAGR 40%) <a href="#ref13">[13]</a>.  
  • India’s professional education industry (including AI upskilling) was projected to grow 56% by end-2023 <a href="#ref15">[15]</a>.  
  • India faces a 51% imbalance between supply and demand of AI skills, despite ~420,000 existing AI professionals; shortages could near one million by 2027 <a href="#ref16">[16]</a>.  
  • 85% of Indian professionals plan to upskill in FY25, and 70% are actively seeking opportunities <a href="#ref18">[18]</a>.  
  • India leads in generative AI learner adoption, with 1.3 million enrollments in 2024 and 2.6 million to date on Coursera (107% YoY growth) <a href="#ref20">[20]</a>.  

- Serviceable Obtainable Market (SOM) – Bangalore  
  • India’s corporate training market: USD 10.8 billion in 2024, projected to USD 37.8 billion by 2033 (CAGR 13.4%) <a href="#ref33">[33]</a>.  
  • 40% of corporate training spend is on digital/IT/AI skills <a href="#ref35">[35]</a>.  
  • Assuming Bangalore represents 12% of India’s AI/IT corporate training spend, its 2024 market size is USD 518.4 million.  
  • Global Knowledge Tech SOM projections:  
    – Year 1 (2025): USD 2.94 million (0.5% capture of USD 587.9 million)  
    – Year 3 (2027): USD 11.31 million (1.5% capture of USD 753.8 million)  
    – Year 5 (2029): USD 28.99 million (3.0% capture of USD 966.5 million)  

- Historical & Forecast CAGRs  
  • Global EdTech: 11.86%–17.34% (2025–2033) <a href="#ref3">[3]</a>  
  • Global AI in Education: 20.77%–47.2% (2025–2034) <a href="#ref2">[2]</a>  
  • India EdTech: 16.8% (2017–2022) <a href="#ref12">[12]</a>  
  • India Corporate Training: 13.4% (2025–2033) <a href="#ref33">[33]</a>

1.3 Major Findings and Insights  
- Strong demand driven by AI adoption across industries (healthcare, finance, retail, manufacturing, agriculture) and a critical skills gap <a href="#ref17">[17]</a>.  
- Government initiatives (National AI Strategy, Digital India, Skill India, FutureSkills Prime) fuel AI upskilling and provide alignment opportunities <a href="#ref31">[31]</a>.  
- Differentiation: “Master AI – The Leitner Way” offers a tactile, distraction-free, spaced-repetition system, appealing to learners facing digital fatigue.  
- High willingness to pay: Professionals value structured, efficient, long-term retention methods.  
- Competitive intensity: Major online players (Simplilearn, Great Learning, UpGrad) dominate, with many local institutes offering affordable, hands-on courses.  
- Key challenges: Instructor scarcity, digital divide in peripheral regions, quality assurance of online content.  
- Bangalore is India’s AI/IT hub, with a tech-savvy workforce and extensive corporate training budgets.

---

## 2. Market Overview  

2.1 Industry Classification and Segments  
- EdTech → Professional Development & Corporate Training → AI/ML specialization.  
- Supplemental market in higher education for foundational AI courses.

2.2 Product Category Definitions and Use Cases  
“Master AI – The Leitner Way” is a flashcard-based system using spaced repetition to master AI concepts in three tracks and progressive difficulty levels: Basic, Intermediate, Advanced. Key use cases:  
• Executive upskilling for strategic AI decision-making  
• Fintech professional training (algorithmic trading, risk management)  
• Foundational ML education for students and career changers  
• Standardizing AI knowledge across teams  

2.3 Market Drivers and Trends  
- Drivers: Rapid AI adoption in enterprises, glaring skills gap, remote/hybrid learning rise, government digital skill policies <a href="#ref17">[17]</a>.  
- Trends: Micro-learning, blended physical-digital modalities, AI-powered personalized content (Generative AI).

---

## 3. Market Sizing  

3.1 Total Addressable Market (TAM)  
- Global EdTech professional training: USD 163.49 billion–250.16 billion in 2024; to USD 721.15 billion by 2033 at 11.86%–17.34% CAGR <a href="#ref3">[3]</a>.  
- Global AI/ML training sub-segment: USD 5.88 billion in 2024; USD 32.27 billion by 2030 at 31.2% CAGR <a href="#ref2">[2]</a>.

3.2 Serviceable Available Market (SAM)  
- India & APAC AI upskilling: USD 4.3 billion–6 billion in 2022, growing ~16.8%–40% CAGR <a href="#ref12">[12]</a><a href="#ref13">[13]</a>.  
- India corporate training: USD 10.8 billion in 2024; to USD 37.8 billion by 2033 at 13.4% CAGR <a href="#ref33">[33]</a>.

3.3 Serviceable Obtainable Market (SOM)  
- Bangalore’s AI/IT corporate training market: USD 518.4 million in 2024.  
- Projections for Global Knowledge Tech:  
  • 2025: USD 2.94 million (0.5% share)  
  • 2027: USD 11.31 million (1.5% share)  
  • 2029: USD 28.99 million (3.0% share)

3.4 Historical & Projected Growth Rates  
- Indian EdTech: 16.8%–40% (2017–2022) <a href="#ref12">[12]</a><a href="#ref13">[13]</a>  
- India corporate training: 9.8% (2017–2022) accelerating to 13.4% (2025–2033) <a href="#ref33">[33]</a>

---

## 4. Industry Ecosystem  

4.1 Industry Value Chain & Ecosystem Map  
- Content creators: AI SMEs, instructional designers, academia (IIIT Bangalore, IIM Bangalore) <a href="#ref36">[36]</a>.  
- Platform providers: Coursera, UpGrad, Simplilearn, Great Learning; local institutes (Cambridge Infotech, AnalytixLabs, Besant, ACTE) <a href="#ref37">[37]</a>.  
- Physical materials manufacturers: professional card stock, storage organizers.  
- Distribution channels: direct B2C (e-commerce, company website), B2B (corporate L&D), academic partnerships, training marketplaces <a href="#ref41">[41]</a>.  
- Support services: certification bodies (NASSCOM, ASSOCHAM), government skill development agencies.

4.2 Key Suppliers, Partners & Distribution Channels  
- LMS/tech partners: Moodle, TalentLMS; AI frameworks (TensorFlow, Keras), analytics tools (Tableau, Power BI) <a href="#ref16">[16]</a>.  
- Physical manufacturers: specialized card-stock and box producers.  
- Corporate training aggregators: NIIT, Manipal Global, Centum, Aptech <a href="#ref41">[41]</a>.  
- Accreditation partners: NASSCOM, university bodies (IIT Guwahati via AnalytixLabs) <a href="#ref38">[38]</a>.

4.3 Regulatory Environment & Standards Bodies  
- Learning standards: SCORM, xAPI (for digital companion) <a href="#ref31">[31]</a>.  
- Accreditation: industry bodies (NASSCOM), academic certifications (IITs/IIMs).  
- Data privacy: Digital Personal Data Protection Act, 2023 compliance required <a href="#ref31">[31]</a>.  
- Alignment with NEP 2020, Skill India, Digital India beneficial.

4.4 Technology Adoption & Infrastructure  
- High adoption of online learning platforms; GenAI for content personalization <a href="#ref20">[20]</a>.  
- Bangalore ICT infrastructure: extensive broadband/mobile penetration and device usage supports blended models <a href="#ref31">[31]</a>.  
- Emerging tech: AI-powered adaptive learning, gamification, VR/AR.

---

## 6. Market Maturity & Trends  

6.1 Market Lifecycle Stage  
- Growth phase: evidenced by strong investments, rising enrollments, skills gap urgency, competitive intensity <a href="#ref10">[10]</a><a href="#ref17">[17]</a>.

6.2 Key Market Trends & Innovation Indicators  
- Personalization via adaptive algorithms  
- Micro-learning & gamification aligned with spaced repetition  
- Generative AI for flashcard/content generation  
- Blended learning combining physical/digital modalities  
- Emphasis on hands-on, project-based learning  

6.3 Growth Rate & Saturation Analysis  
- High growth in Tier-1 cities; early saturation in generic online offerings may prompt price pressure, but differentiated products can command premium.

6.4 Potential Disruptors & Technology Trends  
- Free/open-source AI courses (Fast.ai, MOOCs) challenging paid models  
- AI-powered automated tutoring reducing need for instructors  
- Blockchain credentials for verifiable certifications  
- VR/AR for immersive simulations  
- Hyper-personalized learning paths via advanced analytics

---

## 7. Geographic Market Analysis  

7.1 Regional Market Sizes & Key Differences  
- Global vs. APAC vs. India: India is a key growth driver due to a large youth population and digital initiatives <a href="#ref7">[7]</a>.  
- Bangalore’s concentration of tech firms and academic institutions makes it a priority market.

7.2 Major Regional Competitors & Local Factors  
- National competitors: Simplilearn, Great Learning, UpGrad (IIIT B partnership) <a href="#ref13">[13]</a>.  
- Local institutes: Cambridge Infotech, AnalytixLabs, Besant, ACTE <a href="#ref16">[16]</a><a href="#ref18">[18]</a>.  
- Cost sensitivity remains, but professionals will pay for high-quality, career-advancing programs.  
- English dominates; blended learning preference is rising.

7.3 Geographic Opportunities & Expansion Challenges  
- Bangalore’s large IT workforce and startup ecosystem present corporate partnership opportunities.  
- Challenges: intense competition, state-level policy variations, infrastructure gaps outside Tier-1 cities.  
- Future expansion: Hyderabad, Pune, Chennai, Delhi NCR; APAC markets like Singapore and Vietnam.

---

## 8. Conclusions & Recommendations  

8.1 Major Opportunities & Threats  
- Opportunities: niche differentiation, corporate L&D partnerships, blended physical-digital offerings, strong upskilling demand.  
- Threats: incumbent digital platforms, price erosion from free resources, quality and instructor availability.

8.2 Strategic Recommendations & Next Steps  
- Pilot corporate training with Bangalore IT firms and Global Capability Centres.  
- Develop a digital companion app: progress tracking, adaptive algorithms, supplementary content, generative AI Q&A.  
- Forge accreditation partnerships (NASSCOM, IITs/IIMs) for co-certification.  
- Emphasize tactile, distraction-free USP in marketing campaigns.  
- Segment marketing by track (Business, Finance, General AI & ML) to align messaging.

8.3 Data Gaps & Uncertainty Considerations  
- Limited public data on tactile learning system adoption and physical product market shares.  
- Corporate training budgets fluctuate with economic cycles.  
- Need primary research on user acceptance and willingness-to-pay for physical vs. digital-only models.  
- Further pricing strategy validation required through market testing.

---

References  
1. businessresearchinsights.com  
2. grandviewresearch.com  
3. imarcgroup.com  
4. grandviewresearch.com  
5. marketresearchfuture.com  
6. market.us  
7. researchandmarkets.com  
10. maximizemarketresearch.com  
12. medium.com  
13. cppr.in  
14. livemint.com  
15. emeritus.org  
16. indiaai.gov.in  
17. indianexpress.com  
18. economictimes.com  
20. etvbharat.com  
23. trade.gov  
29. indiaai.gov.in  
31. digitalindia.gov.in  
33. imarcgroup.com  
35. tracedataresearch.com  
36. datamites.com  
37. cambridgeinfotech.io  
38. analytixlabs.co.in  
39. besanttechnologies.com  
41. researchandmarkets.com

## References

<a name="ref1"></a>[1] [businessresearchinsights.com](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQGdZm2boTiC--yAW-aHxMVgKTB_WsxiJrBeeh9YoXAQt2zR-kGW4wI1CxZ-a-iaf6hBCEDdPKet4rqOf-zf_RJCNkhMlhpNHgYzWbPdrca6XNNVJgn7KGmpZz8GmdATpanjVFNuPcznI75OA1FdsURqZ0ToIHGtbO4BerFaltqGB-wzbohg9YPFYZU3Wyt1QlIsK_lj4CBdcw8Yha0=)

<a name="ref2"></a>[2] [grandviewresearch.com](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEmaAtAEtn-O9CWHi9MuMVAAnUbTUwvKiLr9-ids8m0ToFw1QTrHC3tuHmY72fsYvUbdwmBSMgL1GQ4emghdGG3HPaMt3L0IMRxo8Uf1lgObPiKS4EEHl4BNb9xLL53CWLdl3GdNdQHQE5Mjj_aTICw2f0SWQanxBvvANtaW9AvRdXuothRtq4ukn8URIMYU_7nt-MVKZa2iyMfOm3ZyS60)

<a name="ref3"></a>[3] [imarcgroup.com](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQF7ve6OGbXp5hB7dJSBHPtj1sNVdNb48BDQtZtrW_6iIReoQQknAxZTm-y4zu6WD4IIUYSXL6JZ8fC9owxqpJeHaFZ9V8QA5CuRPDjnLWOqPB_2bMPAEPhdce2QqyUpTP1H4A==)

<a name="ref7"></a>[7] [researchandmarkets.com](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEuJ7cFaJl_y02wgsqM3zgv5uvS1WYicwieKIxRIzqQg8h_gvje_-dMobZPy4SNDf3HKryd64JuPmZMeQNeArQCcw0wGiT__OEEqJgP1j2-nZvlNxNnkyxnflamm04DVC923Wd8qCGI_tEf34CZVCrt)

<a name="ref10"></a>[10] [maximizemarketresearch.com](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQFUEPZ9s88y4ZJP68f10soQ8qxf8j76o9_oNRJQfXksHAGlfdEcv4OziL_zvFjuNkcDS6t9Nw-l96O1f34dLkdTVsjjd2XsbGzXZ7DtsC6m5CKyS5YpMfry5gRzRtJZgvCyB0374DTrlTYw1WNkuAiAlm9PfK_ZfOJg02zdUO0hNoxbha2CkKpMja6E-tq7B03nc3Q=)

<a name="ref12"></a>[12] [medium.com](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQGWCTgOKZdpmsFeDRO_sONsG_PdU6rPoAehFZofqv2OYF-HPWLSX7fJtdp5TS8pi02OqgJKN_ReSn2cecz8XNQvH-YQh9Lb9qe5dAzfTgznIpZH8PBYnm6OAd8nJtcp8mI6pqZSwNiWhHa_z8d_xj8I1fhJXYN609EJwi4_69Ommz7FZZBKv5ZRHQrwh3GZfKnuZw40XPGM3iq6Mw==)

<a name="ref13"></a>[13] [cppr.in](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQELRLJGbcOjh4mLphqQo0s53bNEzaPCsUzLYuxENzWNmGbaj_xO5NAznvH9PoQmic5NSlUtH1MtKgxC2hejlfEzabhOG6KH6QDZO9n6amSn2FaEomnuIxsVRaXtAVVlqB3kf89jLv67NiSO8x3YIPrvVacUwmz1PFChd8op_KehfJj_88y4ak0=)

<a name="ref15"></a>[15] [emeritus.org](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQHfSSvEpt6Olg7nRX6bQQiMfFGaL3a0pyIm57Tt1gWBapebZXP0hibLhrxNQYvXewoFAmCCAp5xvLkuMMSy7ePvbJ3RsnnVE6RKGp6vmU2VAaC1SblMXLroyaEqgxvEhcZ6zTG0mJ6Hh2F_mOMSBq_RLT-B)

<a name="ref16"></a>[16] [indiaai.gov.in](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQGpC1rSLTP6vd4W9eQapCAglxtdBJKSQspLgnAaKTawH_i3U0pBZEVm4Yzjq8QFMYoRSPKb4BqgZSxPb4I_F1TRPIZEPBMCgm3RlRIywStACA9bEjndBJHgFN4iBT3SHs2m7HXFDh_jQm2MilqBY8d92-wDWTGD_6NpJi31v1leagkLr29hS2O803bpEWPluOejhrsJQnycuIr32VVzubSHC_kPh6BBEAtSyt72)

<a name="ref17"></a>[17] [indianexpress.com](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQHvpeTRiHKmeHp0Ur8ZRccbZRw1W3lClUSRr_QFQQoCIUQc-X1L5kK4Nf-u9XEmrZkVGCq8LB_aAY-8NbeiMWJZJ-M5WdntxweDn4mCYJWkTWXI6n4JEMv8ffRQ1h8v0i-Sqmg0wDVDMsynNaOWk2nl2uK_huffDLHbDlPg_bsV0DZOizU8-N9cmpN2pRtI5RBsGdAr1lhCB-2FaWmjeUSNbSWaXvEqU1sBVVgEZACfVW3VReZbMLIW)

<a name="ref18"></a>[18] [economictimes.com](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQFB6W3Qibi-K9NxdPHt9RAAK8L0kig3W8Za3LH7sOLaX5LszSrsoDAKizE8tnA2a6phE2Y9Lq6FhVt4h3bSklNFZSBqCJqARrp_MpjLa2tx0TZcj0Zw5hk1jNIYssGx2sBJM6GLhey9BF5U9uJjw8-9IWM_irwld1sHhSRDKuabhhO0WoWKtuf_O7o0BYaVKeta54BMZrgGaMTJmSaXdhRiwIOJS5G0eMX4_ewvM2yFkoQPz0AXScUITvKX41j9INxhEauFUw==)

<a name="ref20"></a>[20] [etvbharat.com](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEYkHABU4G81VjrCNsRV9RLH0apyY67j9fk13DQhLtTRuZGDpB4gix1-bie5W2NIUM5Ol9C5pO3FjaZSO-S_2OKBTvlqeyVvPJV7H3N7mgGTZArPJkwRBiNkqZ92ewg8lPSnCvZR5xviTQ4bww2HT6Zznb0poPja6gt5fOVBoaHmmg6cV8ZUlcy8hUlYXsMQTAln_NXYoj2MX6QPS9L3rITTeiLtxvamyfAHwlY8z3QCrhyQXMrnmWq)

<a name="ref31"></a>[31] [digitalindia.gov.in](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQG_X0up69OYE58xZmVkUsTVVaz7zhVgQ49NAgRT2wI4ZANHsVDhNzSbysGoSQ-l0s3Po-DTK8hxeP6DpJ3DWsngAntWFmlUVXmIRT2v_yOePEqddHF36Pum6tQW5SKIbmtp__wCULATExAh3jXEYBEwI-gBM5MqkwMva28o0vlAKsEfjUmnFOm78lBv8ibO1Gsk)

<a name="ref33"></a>[33] [imarcgroup.com](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEZnpebbdGwA-3GxI10FLLU-ZP2J0DJ4EFsVMZavLNTLfY7FB8FqtWwCHfv0CalA5bmAqrXU1nEbYECrht_HQRuFffAXk5TQr6CgF9ndimp_TGNdouw6ZSQFW3srVW-qAfYh78TFd4E2N2aViqi3SS8PH7y2-g=)

<a name="ref35"></a>[35] [tracedataresearch.com](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQGKliVdvhKw3QCnH5F9t-pEcx0x06g9pK1JDkkNkUBfZMdUDC7omAOPtoGdvNpqXSZ5YzklxOFePPkhv8P7mBQOhjcTHJW6kkEhcxoOvazOu1mymkyNUqbTZMpeDmr2o0par7QJ4XqNYDj3W2q4AskUxNqWvUODM3sl-i0fgh-Cv14Ko4fKIbIGL9eu6Q==)

<a name="ref36"></a>[36] [datamites.com](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQGpR1YhTpiELnPJmMrvopFUgq035RBRKKlMCDxf4tuVX40KCEJV6HkKn5uMYjnHEK1_bXULl4v2sleXiVXbvpOTbi9eutMSq4yV6SM6DTx7MydBv4on_q0KVSa4lbo-prI7Ks6sDbwcmUqkTyKu2Uqp5BkALWHxB1julTDsltjb8GndIdeCXwAeM4qHelQ3C40O7v5VQjrghnkmKrk=)

<a name="ref37"></a>[37] [cambridgeinfotech.io](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQGqgNbA13jfZG87ePVGwSaPlYV8Mz_32xNru-nexQSL9mr7bVZ7ZzPzwKqVUSAHTs3v7cf-0kIeIsk7c7ikaUt2XnyUK3aaEjWVceoNVvnxAaJWI5K0SWJIQ8oLYUa3SrI7QjFxxnAgfvmojC3t9NA=)

<a name="ref38"></a>[38] [analytixlabs.co.in](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQFw_-7Jg5tUYN0N4khfQsMFE5K90tTIrhTAMdZN_y8XsB5_1LASKft6P5ZU1oAExJHivoR_XhmEktTN0BU9dIhOmzLtPGt9Tk_ERzH40ZBl5oTAACKN2cUarVKYI0h4Z4xJP_9UfzymoDRTfY-_Tq7WW7lSqo6tzY9NXSeWwycPPeYmNR4FUA==)

<a name="ref41"></a>[41] [researchandmarkets.com](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQFSqyFG4LWTbOlLW8dqvqixegyIaO11rQocVirWabroWyxHcb4ZhRQdW6EHkDQ0RXvSuWSfw15YTOF37tzkx9dNpY0NYkOOPxLnQ02A2v3ckYOL8J3nHwXFAYseoM1gn1ARAtSVfIDbRTXbFgOXEt1xhHBRDood1-0og_z_vVb8Z9xDBXpNI0jk7nFT7nzOidkCcImIbb5XRw==)

"""

segmentation_analysis_report = """
# Segmentation Analysis Report  
Client: Global Knowledge Tech  
Product: Master AI – The Leitner Way Professional AI Learning System  
Geographic Focus: Bangalore, India  

---

## 1. Executive Summary  

### 1.1 Scope & Goals  
- Objective: Identify and prioritize target customer groups for Master AI in Bangalore to guide market entry and resource allocation.  
- Geographic Focus: Primary emphasis on Bangalore’s tech ecosystem with contextual references to broader Indian market.  

### 1.2 Key Target Segments Identified  
- B2B:  
  • Large IT Services Firms & Global Capability Centres (GCCs)  
  • Mid-market IT/Software Services and Consulting firms  
  • Banking & FinTech organizations  
- B2C:  
  • Mid-career Finance Professionals (Analysts, Risk Officers)  
  • Senior Business Executives (C-suite, VPs, Directors)  
  • Data Scientists & ML Engineers  
  • Career Changers & Students  

### 1.3 Summary of Major Findings  
- Bangalore represents ~12% of India’s USD 10.8 billion corporate training market in AI/IT, yielding a 2024 market of USD 518.4 million <cite source="3"/>.  
- Rapid growth driven by AI skill shortages (2.3 million projected jobs vs. 1.2 million talent pool by 2027)<cite source="17"/>, high upskilling intent (85% planning training in FY25)<cite source="18"/>, and government programs (Digital India, Skill India).  
- Competitive landscape:  
  • Digital incumbents (Simplilearn, UpGrad, Great Learning) dominate online upskilling.  
  • Local institutes (AnalytixLabs, Cambridge Infotech, Besant, ACTE) compete on cost and placement.  
- Unique Opportunity: A tactile, spaced-repetition flashcard system addresses screen fatigue and retention gaps in purely digital offerings.  

### 1.4 Strategic Recommendations (Brief)  
- **Primary Focus:** Target large IT Services/GCCs and mid-market FinTech firms via direct corporate partnerships.  
- **Product Augmentation:** Develop a digital companion app for progress tracking and adaptive quizzes.  
- **Credibility Building:** Secure accreditation with NASSCOM or leading academic institutions.  
- **Messaging:** Emphasize “distraction-free,” “scientifically proven retention,” and “blended learning” benefits.  

---

## 2. Market Segment Overview  

### 2.1 Identified Market Segments & Categories  
- **B2B by Industry:**  
  • IT/Software Services (enterprises & GCCs)  
  • Banking & FinTech (68% AI adoption)<cite source="44"/>  
  • Consulting & Professional Services (62% AI adoption)<cite source="63"/>  
  • Manufacturing (99% planning AI investment)<cite source="50"/>  
  • Healthcare, Retail, Government (emerging AI use cases)  
- **B2C by Learner Type & Motivation:**  
  • Senior Executives: Strategic AI literacy, limited time  
  • Finance Professionals: Algorithmic trading, risk management  
  • Data Scientists & ML Engineers: Deep technical mastery  
  • Career Changers/Students: Foundational AI knowledge, certifications  

### 2.2 Definitions & Characteristics  
- **AI for Business Track:** Strategy, ROI, decision-making, risk simulation.  
- **AI for Finance Track:** Fraud detection, algorithmic trading, compliance.  
- **General AI & ML Track:** Core ML concepts, neural networks, programming proficiency.  

### 2.3 Industry Context  
- Bangalore is India’s “Silicon Valley,” hosting major IT firms (TCS, Infosys, Wipro, Google, Microsoft) and a dense startup ecosystem.<cite source="23"/>  
- Robust digital infrastructure supports blended learning models.  
- National initiatives (FutureSkills Prime, IndiaAI Mission) foster AI education demand.  

---

## 3. Customer Segment Profiles  

### 3.1 B2B Firmographic Profiles  
- **Large Enterprises & GCCs:**  
  • > 1,000 employees, formal L&D budgets, internal LMS.  
  • High AI adoption: BFSI (68%), Manufacturing (99%).  
- **Mid-market Companies (100–1,000 employees):**  
  • Growing digital transformation budgets, agile procurement.  
- **SMBs & Startups (< 100 employees):**  
  • Targeted, limited budgets; seek rapid, applied training.  

### 3.2 B2C Demographic & Psychographic Profiles  
- **Mid-Career Finance Professionals (25–40 yrs):**  
  • University-educated, mid–high income.  
  • Fear job obsolescence; seek 93% avg. salary hikes post-AI upskilling.<cite source="86"/>  
- **Senior Business Executives (35–55+ yrs):**  
  • High-income, MBAs/advanced degrees.  
  • Time-constrained; value strategic insights, “screen-fatigue” relief.  
- **Data Scientists & ML Engineers (22–35 yrs):**  
  • Technical degrees; INR 12–20 lakhs salary range.<cite source="94"/>  
  • Desire hands-on, structured mastery of advanced AI topics.  
- **Career Changers & Students:**  
  • Price-sensitive, certificate-driven, seek job-ready skills quickly.  

### 3.3 Behavioral & Needs-Based Patterns  
- **Jobs to Be Done:**  
  • Executives: high-level AI literacy for strategy.  
  • Technical roles: durable concept retention for complex models.  
  • Exam prep & certification mastery.  
- **Learning Journeys:**  
  1. Awareness of AI’s impact  
  2. Consideration of solutions (online vs. physical)  
  3. Evaluation: modality, ROI, credentials  
  4. Adoption & advocacy based on efficacy  

### 3.4 Decision Makers & Influencers  
- **B2B DMU:**  
  • Initiator: Department Head/HR (skill-gap recognition)  
  • Influencers: SMEs, team leads (technical vetting)<cite source="99"/>  
  • Buyers: Procurement/L&D managers (contract terms)  
  • Deciders: C-Suite/Learning Officers (strategic approval)<cite source="99"/>  
  • Gatekeepers: Admin/IT security (vendor access)  
- **B2C Influencers:**  
  • Peer recommendations, employer requirements, LinkedIn, Meta platforms for finance decisions<cite source="93"/>  

---

## 4. Segment Attractiveness & Competition  

### 4.1 Segment Size & Growth Estimates  
- **B2B Corporate AI/IT Training (Bangalore):**  
  • 2024 Market: USD 518.4 million (<12% of India’s USD 10.8 billion)<cite source="3"/>  
  • CAGR: 13.4% (2025–2033)<cite source="3"/>  
- **B2C Individual Professionals:**  
  • ~420,000 AI professionals in India;<cite source="16"/> high 85% upskilling intent<cite source="18"/>  
  • GenAI enrollments: 2.6 million on Coursera (107% YoY)<cite source="20"/>  

### 4.2 Competitive Intensity & Major Competitors  
- **Digital Incumbents (Very High Intensity):**  
  • Simplilearn, Great Learning, UpGrad – broad curriculum, brand equity.  
- **Local Training Institutes (High Intensity):**  
  • AnalytixLabs, Cambridge Infotech, Besant, ACTE – cost-competitive, placement focus.  
- **Indirect Threats:**  
  • Free MOOCs (Fast.ai, Google AI), internal corporate programs.  
- **Differentiation:**  
  • Physical, spaced-repetition flashcards reduce digital fatigue and boost long-term retention.  

### 4.3 Accessibility, Channels & Barriers  
- **B2B Channels:** Direct sales (56% of B2B e-commerce)<cite source="20"/>, partnerships with HR consultancies, NASSCOM alliances.  
- **B2C Channels:**  
  • E-commerce website, educational marketplaces, LinkedIn, targeted social ads.  
- **Barriers to Entry:**  
  • Overcoming digital-only learning mindset.  
  • Logistics: manufacturing, inventory, last-mile delivery.  
  • Higher per-unit costs vs. digital content.  

---

## 5. Segment Prioritization & Strategic Fit  

### 5.1 Evaluation Criteria  
| Criteria                                | Weight |
|-----------------------------------------|-------:|
| Market Size & Growth Potential          |   25%  |
| Willingness to Pay & Revenue Potential  |   20%  |
| Competitive Intensity                   |   15%  |
| Strategic Fit (Leitner USP)             |   20%  |
| Accessibility & Reachability            |   10%  |
| Resource Requirements                   |   10%  |
| **Total**                               | **100%**|

### 5.2 Ranking of Top Segments  
1. **Large IT Services Firms & GCCs** (Tier 1)  
   • High budgets, standardized training needs, value retention solutions.  
2. **Mid-Career Finance Professionals** (Tier 2)  
   • Specialized track, high ROI potential.  
3. **Senior Business Executives** (Tier 3)  
   • Premium pricing, low volume, strategic positioning.  
4. **Data Scientists & ML Engineers** (Tier 4)  
   • Technical depth, but price-sensitive due to open-source alternatives.  
5. **Career Changers & Students** (Tier 5)  
   • High volume, low willingness to pay.  

### 5.3 Product-Segment Fit  
- **Screen-Fatigue Relief:** Physical flashcards differentiate from digital overload.  
- **Leitner Method:** Proven spaced-repetition for complex concept mastery.  
- **Structured Levels:** Aligns with corporate L&D progression needs.  
- **Blended Model:** Physical + digital companion unites tactile and adaptive learning.  
- **Certification Pathways:** Enables alignment with industry credentials.  

---

## 6. Segmentation Framework & Recommendations  

### 6.1 Priority Segment Definitions & Boundaries  
- **Segment A (Tier 1):**  
  • Mid-market & large IT/GCCs (> 500 employees, active AI projects).  
- **Segment B (Tier 2):**  
  • Finance Professionals (25–40 yrs) in top banks & FinTechs.  
- **Segment C (Tier 3):**  
  • Senior Executives (C-suite/VPs) across sectors.  

### 6.2 Targeting Recommendations & Next Steps  
- **Segment A:**  
  • Launch corporate pilot; develop ROI calculator showcasing retention improvements.  
  • Engage L&D & Department Heads with on-site workshop demos.  
- **Segment B:**  
  • Publish success stories, partner with finance associations.  
  • Highlight “AI for Finance” use cases in targeted webinars.  
- **Segment C:**  
  • Craft executive-brief whitepapers; collaborate with IIM Bangalore executive education.  
- **Cross-Segment Initiatives:**  
  • Fast-track digital companion MVP (quizzes, progress analytics).  
  • Secure NASSCOM accreditation and university endorsements.  
  • Run content campaigns on science of spaced-repetition.  

### 6.3 Opportunities & Potential Risks  
- **Opportunities:**  
  • Unique tactile imprint in a digital-heavy market.  
  • High corporate budgets and government skilling drives.  
- **Risks:**  
  • Feature parity by digital incumbents (adaptive tech).  
  • Logistics complexity & unit cost pressures.  
  • Market education required to shift modality preference.  

---

## 7. Conclusions  

### 7.1 Recap of Strategic Insights  
- Bangalore’s AI upskilling demand is robust, underpinned by corporate budgets and national initiatives.  
- Master AI’s tactile, scientifically validated method fills a niche unmet by digital incumbents.  
- Blended learning (physical + digital) offers a compelling holistic solution.  

### 7.2 Final Recommendations  
1. **Resource Focus:** Concentrate on Tier 1 (IT/GCCs) and Tier 2 (Finance Professionals).  
2. **Blended Offering:** Accelerate digital companion development for seamless integration.  
3. **Credibility & Reach:** Secure accreditations, pilot partnerships, and targeted marketing.  
4. **Value Communication:** Consistently articulate distraction-free retention and ROI.  

---

**References**  
3. IMARC Group. India Corporate Training Market Size and Report, 2033.  
17. Indian Express. Projections on AI job openings vs. talent pool, 2027.  
18. Economic Times. Upskilling intent among Indian professionals, FY25.  
20. ETV Bharat. Generative AI learner adoption data.  
23. Trade.gov. Bangalore as a hub for AI learning solutions.  
35. TraceData Research. 40% of corporate training dedicated to digital/IT skills.  
44. IndiaAI.gov.in. BFSI AI adoption rate (68%).  
50. IndiaTimes.com. Manufacturing AI investment projections (99%).  
63. AI Trends India. Consulting industry AI adoption (62%).  
94. PeopleClick Learning. Data Scientist compensation in India.  
99. Inbox Insight. B2B decision-making unit roles and influence statistics.  
93. PPC Land. Meta platforms’ role in financial product discovery.

"""


# --- Keep all your existing schema classes unchanged ---
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

# --- Keep your existing checker class unchanged ---
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

# --- ENHANCED AGENTS FOR BETTER RESEARCH AND DECISION MAKING ---

market_intelligence_researcher = LlmAgent(
    model=config.search_model,
    name="market_intelligence_researcher",
    description="Conducts deep market intelligence research leveraging existing analysis to identify precise Apollo.io targeting opportunities.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction=f"""
    You are an expert market intelligence researcher specializing in B2B lead generation optimization using Apollo.io.

    **CONTEXT INTEGRATION:**
    You have access to comprehensive market analysis and segmentation reports that provide:
    - Market sizing and growth projections
    - Competitive landscape analysis
    - Priority customer segments and their characteristics
    - Industry adoption patterns and trends
    - Geographic market opportunities
    
    **RESEARCH MISSION:**
    Your goal is to conduct targeted research that fills specific gaps and validates insights from the existing analysis to generate precise Apollo.io search parameters.

    **ENHANCED RESEARCH METHODOLOGY:**

    **1. Competitive Intelligence Deep-dive (30%)**
    - Research specific companies mentioned in the analysis reports
    - Identify their customer profiles through case studies, testimonials, and press releases
    - Map their typical client organizational structures and decision-makers
    - Discover exact job titles, departments, and seniority levels of their buyers
    - Search: "[Competitor name] customer case studies decision makers"
    - Search: "[Competitor name] client testimonials job titles organizational roles"
    - Search: "[Competitor name] implementation team structure"

    **2. Industry-Specific Role Mapping (25%)**
    - Based on the priority industries identified in reports, research specific organizational structures
    - Map department hierarchies and reporting relationships
    - Identify technology adoption patterns and skill requirements
    - Search: "[Industry] + [Product category] organizational structure roles"
    - Search: "[Industry] technology adoption decision making hierarchy"
    - Search: "[Priority industry] AI/ML implementation team roles responsibilities"

    **3. Geographic Market Validation (20%)**
    - Validate the geographic insights from reports with current job market data
    - Research local company hiring patterns and skill demands
    - Identify regional terminology and role variations
    - Search: "[Geographic location] [industry] job openings [product category]"
    - Search: "[Geographic location] technology hiring trends [specific skills]"
    - Search: "[Geographic location] [industry] organizational culture decision making"

    **4. Technology Stack and Skills Intelligence (25%)**
    - Research the specific technologies and skills mentioned in the analysis
    - Identify complementary tools and platforms used by target segments
    - Map skill progression and career paths in target roles
    - Search: "[Target role] technology stack requirements [current year]"
    - Search: "[Industry] [target department] software tools technology adoption"
    - Search: "[Product category] implementation skills professional requirements"

    **APOLLO.IO OPTIMIZATION FOCUS:**
    Every search should specifically target:
    - Exact job titles and variations used in job postings and LinkedIn
    - Professional skills listed in job requirements and profiles
    - Company characteristics that indicate fit for the product
    - Technology adoption signals that suggest readiness
    - Department structures and reporting hierarchies
    - Geographic and cultural nuances affecting targeting

    **INTELLIGENCE GATHERING PRIORITIES:**
    1. **Decision Maker Identification:** Who actually makes purchasing decisions
    2. **Influencer Mapping:** Technical evaluators and internal champions
    3. **Budget Authority:** Roles with spending authority for the product category
    4. **Implementation Team:** Who would be involved in rollout and adoption
    5. **Success Metrics:** How these roles measure success and ROI

    **RESEARCH QUALITY STANDARDS:**
    - Gather 20+ specific, searchable job titles per target segment
    - Identify 15+ professional skills and competencies
    - Document 10+ company characteristic indicators
    - Map 5+ technology stack elements per segment
    - Validate geographic and cultural targeting nuances

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    
    Leverage the existing market and segmentation analysis as your foundation, then conduct targeted research to fill gaps and validate insights for optimal Apollo.io parameter generation.

    **INPUT CONTEXT PLACEHOLDERS:**
    - Market Analysis Report: {market_analysis_report}
    - Segmentation Analysis Report: {segmentation_analysis_report}
    """,
    tools=[google_search],
    output_key="market_intelligence_findings",
)

competitive_landscape_analyzer = LlmAgent(
    model=config.search_model,
    name="competitive_landscape_analyzer",
    description="Analyzes competitive customer bases and identifies targeting patterns for Apollo.io optimization.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction=f"""
    You are a competitive intelligence specialist focused on analyzing customer acquisition patterns for Apollo.io lead generation.

    **COMPETITIVE ANALYSIS FRAMEWORK:**

    **1. Customer Base Analysis (40%)**
    - Research competitors' customer testimonials and case studies
    - Identify common organizational patterns in their client base
    - Map typical implementation team structures and roles
    - Document success story patterns and use cases
    - Search: "[Competitor] customer success stories implementation teams"
    - Search: "[Competitor] case studies organizational roles decision makers"
    - Search: "[Competitor] client testimonials job titles departments"

    **2. Sales and Marketing Intelligence (30%)**
    - Analyze competitors' sales materials and marketing content
    - Identify how they position their solutions to different roles
    - Extract buyer personas from their content strategy
    - Map their messaging to specific organizational levels
    - Search: "[Competitor] sales materials buyer personas target roles"
    - Search: "[Competitor] marketing content decision maker messaging"
    - Search: "[Competitor] webinar presentations target audience"

    **3. Partnership and Channel Analysis (20%)**
    - Research competitors' partner ecosystems and channel strategies
    - Identify common system integrators and consulting partners
    - Map partner relationships to target customer segments
    - Search: "[Competitor] partner ecosystem system integrators"
    - Search: "[Competitor] consulting partners implementation teams"
    - Search: "[Competitor] channel strategy customer acquisition"

    **4. Hiring and Organizational Patterns (10%)**
    - Analyze competitors' hiring patterns and job postings
    - Identify internal roles focused on customer acquisition
    - Map their internal expertise to customer segments served
    - Search: "[Competitor] job openings customer success roles"
    - Search: "[Competitor] sales team specialization industry focus"

    **APOLLO.IO TARGETING INSIGHTS:**
    Extract specific intelligence on:
    - **Exact Job Titles:** Used in competitor customer communications
    - **Department Structures:** How clients organize around the product category
    - **Seniority Mapping:** Authority levels involved in decisions
    - **Company Characteristics:** Size, industry, technology adoption patterns
    - **Geographic Patterns:** Regional preferences and adoption rates
    - **Technology Stack Signals:** Complementary tools and platforms

    **COMPETITIVE DIFFERENTIATION:**
    Identify opportunities to:
    - Target roles competitors miss or underserve
    - Focus on industries with high adoption but lower competitor focus
    - Leverage geographic markets with growth potential
    - Target technology adoption patterns indicating readiness

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}

    **INPUT CONTEXT PLACEHOLDERS:**
    - Market Analysis Report: {market_analysis_report}
    - Segmentation Analysis Report: {segmentation_analysis_report}
    """,
    tools=[google_search],
    output_key="competitive_intelligence_findings",
)

persona_research_evaluator = LlmAgent(
    model=config.critic_model,
    name="persona_research_evaluator",
    description="Evaluates research comprehensiveness against market analysis insights and Apollo.io requirements.",
    instruction=f"""
    You are a senior research analyst evaluating market intelligence for Apollo.io lead generation effectiveness.

    **EVALUATION FRAMEWORK:**

    **1. Market Analysis Alignment (25%)**
    - Validate research findings against existing market analysis insights
    - Ensure coverage of all priority segments identified in segmentation report
    - Check alignment with market sizing and growth projections
    - Verify competitive landscape understanding matches analysis

    **2. Apollo.io Parameter Completeness (30%)**
    - **Job Title Precision:** 20+ specific, searchable job titles per segment
    - **Skills Intelligence:** 15+ professional skills mapped to roles
    - **Company Targeting:** Clear firmographic patterns and indicators  
    - **Geographic Specificity:** Location data in Apollo.io format
    - **Technology Signals:** Stack indicators for organization filtering
    - **Exclusion Criteria:** Negative keywords to avoid false positives

    **3. Competitive Intelligence Quality (25%)**
    - Depth of competitor customer analysis
    - Quality of decision-maker identification
    - Accuracy of organizational structure mapping
    - Validation of buyer persona assumptions

    **4. Research Methodology Rigor (20%)**
    - Source diversity and credibility
    - Data recency and relevance
    - Cross-validation of findings
    - Actionability for immediate implementation

    **CRITICAL SUCCESS CRITERIA - Grade "pass" if:**
    - All priority segments from analysis have comprehensive Apollo.io parameters
    - 20+ job titles per segment with variations and synonyms
    - Complete skills and keyword intelligence for targeting
    - Clear company characteristic patterns for organization filtering
    - Validated competitive insights with specific customer patterns
    - Technology adoption signals for intent-based targeting
    - Geographic and industry targeting validated against analysis

    **FAILURE CONDITIONS - Grade "fail" if:**
    - Missing coverage of priority segments from analysis
    - Insufficient job title variations (< 15 per segment)
    - Vague or generic demographic data
    - No competitive customer intelligence
    - Missing technology adoption patterns
    - Inadequate skills/keyword mapping for Apollo.io

    **FOLLOW-UP QUERY GENERATION:**
    When grading "fail", generate targeted queries focusing on:
    - Specific segments missing from research
    - Job title variations and organizational roles
    - Competitive customer base analysis gaps
    - Technology adoption and skills intelligence holes
    - Geographic or industry-specific targeting requirements

    **INPUT CONTEXT PLACEHOLDERS:**
    - Market Analysis Report: {market_analysis_report}
    - Segmentation Analysis Report: {segmentation_analysis_report}
    - Market Intelligence Findings: {market_intelligence_researcher}
    - Competitive Intelligence Findings: {competitive_landscape_analyzer}

    Your evaluation must ensure the research provides actionable Apollo.io parameters that align with market analysis insights and enable effective lead generation.
    """,
    output_schema=PersonaFeedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="persona_evaluation",
)

targeted_gap_researcher = LlmAgent(
    model=config.search_model,
    name="targeted_gap_researcher",
    description="Executes precision research to fill critical gaps identified in evaluation.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction=f"""
    You are a specialist researcher focused on filling critical gaps in Apollo.io parameter data.

    **GAP-FILLING METHODOLOGY:**

    **1. Targeted Segment Research**
    - Focus on specific segments or roles missing from previous research
    - Deep-dive into organizational structures and decision-making patterns
    - Map exact job title variations used in different contexts
    - Search: "[Missing segment] organizational structure decision makers"
    - Search: "[Missing role] job title variations industry terminology"

    **2. Skills and Technology Intelligence**
    - Research specific professional competencies required for target roles
    - Identify technology adoption patterns and stack indicators
    - Map certification requirements and professional development paths
    - Search: "[Target role] professional skills requirements [current year]"
    - Search: "[Target role] technology certifications career development"

    **3. Company Characteristic Validation**
    - Validate company size patterns and industry adoption rates
    - Research geographic distribution and regional variations
    - Identify technology adoption signals and maturity indicators
    - Search: "[Product category] company size adoption patterns"
    - Search: "[Target industry] technology maturity indicators"

    **4. Competitive Customer Deep-Dive**
    - Focus on specific competitors or customer patterns identified as gaps
    - Research customer success stories and implementation details
    - Map customer organizational structures and role responsibilities
    - Search: "[Specific competitor] customer case studies team structures"

    **EXECUTION STRATEGY:**
    - Execute ALL queries from 'follow_up_queries' with enhanced search techniques
    - Use multiple search approaches for each gap area
    - Cross-reference findings with existing market analysis insights
    - Prioritize Apollo.io parameter optimization in all research

    **QUALITY STANDARDS:**
    - Generate 10+ new job titles for each gap area
    - Identify 5+ professional skills per missing role type
    - Document 3+ company characteristic indicators per gap
    - Validate findings against market analysis where possible

    **INPUT CONTEXT PLACEHOLDERS:**
    - Market Analysis Report: {market_analysis_report}
    - Segmentation Analysis Report: {segmentation_analysis_report}
    - Previous Research Findings: {market_intelligence_researcher} + {competitive_landscape_analyzer}
    - Follow-up Queries: Execute these with enhanced methodology

    Focus on precision and Apollo.io optimization to fill all identified research gaps.
    """,
    tools=[google_search],
    output_key="gap_research_findings",
)

strategic_persona_synthesizer = LlmAgent(
    model=config.critic_model,
    name="strategic_persona_synthesizer",
    description="Synthesizes all research findings with market analysis to generate comprehensive persona data.",
    instruction=f"""
    You are a strategic analyst synthesizing market intelligence into actionable persona data for Apollo.io lead generation.

    **SYNTHESIS METHODOLOGY:**

    **1. Market Analysis Integration (30%)**
    - Integrate insights from existing market analysis and segmentation reports
    - Align persona development with identified priority segments
    - Incorporate market sizing and competitive landscape insights
    - Ensure geographic and industry focus matches analysis recommendations

    **2. Research Consolidation (40%)**
    - Synthesize findings from market intelligence, competitive analysis, and gap research
    - Cross-validate insights across multiple research sources
    - Identify patterns and commonalities across different research threads
    - Resolve conflicts between different data sources

    **3. Apollo.io Optimization (30%)**
    - Transform insights into precise Apollo.io parameter format
    - Ensure job titles are searchable and commonly used
    - Map professional skills to Apollo.io skills database
    - Structure company characteristics for organization filtering

    **PERSONA DEVELOPMENT FRAMEWORK:**

    **Primary Segments (from Analysis):**
    Create detailed personas for each priority segment identified in the segmentation report:
    - Extract segment characteristics from analysis
    - Enhance with research findings
    - Map to Apollo.io parameters

    **Job Title Intelligence:**
    - 15-20 specific job titles per persona
    - Include variations, synonyms, and alternative terms
    - Cover different seniority levels and regional variations
    - Validate against competitive customer research

    **Skills and Competencies:**
    - Professional skills from job requirements research
    - Technology competencies from stack analysis
    - Industry-specific expertise areas
    - Certification and education requirements

    **Company Characteristics:**
    - Size patterns from market research and competitive analysis
    - Industry classifications aligned with analysis priorities
    - Geographic distribution based on market opportunities
    - Technology adoption maturity indicators

    **Behavioral Intelligence:**
    - Pain points validated through competitive research
    - Current solution usage patterns
    - Decision-making processes and authority structures
    - Budget cycles and procurement patterns

    **PERSONA QUALITY REQUIREMENTS:**
    Each persona must include:
    - 15+ job titles with variations
    - 10+ professional skills
    - 5+ company size ranges
    - 3+ industry classifications
    - Geographic targeting data
    - Technology keywords for organization filtering
    - Positive and negative keywords for precise targeting

    **INPUT CONTEXT PLACEHOLDERS:**
    - Market Analysis Report: {market_analysis_report}
    - Segmentation Analysis Report: {segmentation_analysis_report}
    - Market Intelligence: {market_intelligence_researcher}
    - Competitive Intelligence: {competitive_landscape_analyzer}
    - Gap Research: {targeted_gap_researcher}

    Create 4-6 comprehensive personas that align with market analysis priorities and enable effective Apollo.io lead generation.
    """,
    output_schema=PersonaDataCollection,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="persona_data_collection",
)

apollo_parameter_optimizer = LlmAgent(
    model=config.critic_model,
    name="apollo_parameter_optimizer",
    description="Generates optimized Apollo.io search parameters from persona data and market analysis.",
    instruction=f"""
    You are an Apollo.io optimization expert creating comprehensive search parameters based on market analysis and persona research.

    **OPTIMIZATION FRAMEWORK:**

    **1. Market Analysis Alignment (25%)**
    - Prioritize parameters based on market analysis recommendations
    - Weight segments according to market sizing and opportunity
    - Incorporate geographic and industry priorities from analysis
    - Align with competitive positioning insights

    **2. Persona Data Consolidation (40%)**
    - Merge all persona data into unified parameter arrays
    - Remove duplicates while maintaining comprehensive coverage
    - Balance specificity with market coverage
    - Optimize for lead volume and quality

    **3. Apollo.io Technical Optimization (25%)**
    - Ensure all parameters use Apollo.io-compatible formats
    - Structure location data in City, State, Country format
    - Map skills to Apollo.io skills database terms
    - Optimize company size ranges for effective filtering

    **4. Strategic Filtering (10%)**
    - Include exclusion criteria to avoid low-quality matches
    - Add email and phone status filters for contact quality
    - Configure pagination and sorting for optimal results
    - Balance precision with lead generation volume

    **PARAMETER CONSOLIDATION STRATEGY:**

    **Person-Level Parameters:**
    - **person_titles:** All unique job titles with variations
    - **person_seniorities:** Complete seniority level coverage
    - **person_departments:** Relevant departments from research
    - **person_locations:** Geographic targeting from analysis
    - **person_skills:** Professional competencies and certifications
    - **person_keywords:** Intent and behavior keywords

    **Organization-Level Parameters:**
    - **organization_locations:** Company location targeting
    - **organization_num_employees_ranges:** Size segments from analysis
    - **organization_industry_tag_ids:** Priority industry classifications
    - **organization_keywords:** Technology and business keywords
    - **organization_technologies:** Technology stack indicators

    **Quality and Exclusion Filters:**
    - **person_not_titles:** Roles to exclude (students, interns, etc.)
    - **person_not_keywords:** Terms indicating poor fit
    - **organization_not_keywords:** Company types to avoid
    - **email_status:** Prefer verified and likely emails
    - **phone_status:** Include available phone contacts

    **Search Configuration:**
    - **per_page:** 100 for maximum results
    - **sort_by_field:** relevance for best matching
    - **page:** 1 for initial search

    **OPTIMIZATION PRINCIPLES:**
    - **Market-Driven:** Prioritize based on analysis recommendations
    - **Comprehensive:** Include all viable targeting options
    - **Balanced:** Specific enough for quality, broad enough for volume  
    - **Actionable:** Immediately usable for lead generation campaigns
    - **Measurable:** Enable tracking and optimization

    **INPUT CONTEXT PLACEHOLDERS:**
    - Market Analysis Report: {market_analysis_report}
    - Segmentation Analysis Report: {segmentation_analysis_report}
    - Persona Data Collection: {strategic_persona_synthesizer}

    Generate a single, comprehensive ApolloSearchParameters object that maximizes lead generation effectiveness based on market analysis insights and persona research.
    """,
    output_schema=ApolloSearchParameters,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="prospect_researcher",
)

# --- ENHANCED PIPELINE ---
enhanced_prospect_research_pipeline = SequentialAgent(
    name="enhanced_prospect_research_pipeline",
    description="Executes comprehensive market intelligence research and generates optimized Apollo.io search parameters.",
    sub_agents=[
        market_intelligence_researcher,
        competitive_landscape_analyzer,
        LoopAgent(
            name="research_quality_assurance",
            max_iterations=config.max_search_iterations,
            sub_agents=[
                persona_research_evaluator,
                PersonaEscalationChecker(name="research_escalation_checker"),
                targeted_gap_researcher,
            ],
        ),
        strategic_persona_synthesizer,
        apollo_parameter_optimizer,
    ],
)

# --- MAIN ENHANCED PROSPECT RESEARCHER ---
prospect_researcher = LlmAgent(
    name="prospect_researcher",
    model=config.worker_model,
    description="Advanced market intelligence and Apollo.io lead generation specialist that leverages comprehensive market analysis to generate optimal search parameters.",
    instruction=f"""
    You are an advanced Apollo.io Lead Generation Specialist with deep market intelligence capabilities.

    **ENHANCED MISSION:**
    Generate highly optimized Apollo.io People Search API parameters through comprehensive market intelligence research that leverages existing market analysis and segmentation insights.

    **INTELLIGENT RESEARCH APPROACH:**
    Your research methodology integrates:
    1. **Market Analysis Intelligence:** Leverage existing market sizing, competitive landscape, and growth projections
    2. **Segmentation Insights:** Build on identified priority customer segments and their characteristics  
    3. **Competitive Intelligence:** Deep analysis of competitor customer bases and targeting patterns
    4. **Industry Intelligence:** Current trends, organizational structures, and decision-making patterns
    5. **Technology Adoption:** Stack analysis and tool usage patterns for intent signaling

    **REQUIRED INPUTS:**
    Users must provide:
    1. **Product/Service Description:** Detailed features, benefits, use cases, value proposition
    2. **Company Information:** Background, market positioning, competitive differentiation
    3. **Target Market Context:** Known segments, geographic focus, industry priorities
    4. **Competitive Intelligence:** Known competitors and their positioning (I will research more)

    **ADVANCED WORKFLOW:**

    **Phase 1: Market Intelligence Research**
    - Analyze competitive customer bases through case studies and testimonials
    - Research industry-specific organizational structures and decision-making patterns
    - Map technology adoption patterns and skill requirements in target segments
    - Validate geographic market opportunities and cultural nuances

    **Phase 2: Competitive Landscape Analysis** 
    - Deep-dive into competitor sales and marketing strategies
    - Identify customer acquisition patterns and buyer persona strategies
    - Map partner ecosystems and channel customer characteristics
    - Analyze competitor hiring patterns for customer segment insights

    **Phase 3: Research Quality Assurance**
    - Evaluate research comprehensiveness against market analysis benchmarks
    - Ensure coverage of all priority segments identified in analysis
    - Validate Apollo.io parameter completeness and searchability
    - Execute targeted gap research for missing intelligence

    **Phase 4: Strategic Persona Synthesis**
    - Integrate market analysis insights with research findings
    - Develop comprehensive personas aligned with priority segments
    - Map detailed Apollo.io parameters for each persona type
    - Validate personas against competitive customer patterns

    **Phase 5: Apollo.io Parameter Optimization**
    - Consolidate all persona data into unified search parameters
    - Optimize for maximum relevant lead discovery
    - Balance precision with market coverage opportunity
    - Configure quality filters and exclusion criteria

    **STRATEGIC OUTPUT:**
    Single comprehensive JSON object with optimized Apollo.io People Search API parameters:

    ```json
    {{
      "person_titles": ["exhaustive job title variations"],
      "person_seniorities": ["all relevant seniority levels"],  
      "person_locations": ["geographic targeting"],
      "person_skills": ["professional competencies"],
      "person_keywords": ["intent and behavior keywords"],
      "organization_num_employees_ranges": ["company size segments"],
      "organization_industry_tag_ids": ["priority industries"],
      "organization_keywords": ["company characteristic keywords"],
      "organization_technologies": ["technology stack indicators"],
      "person_not_titles": ["exclusion criteria"],
      "person_not_keywords": ["negative keywords"],
      "email_status": ["verified", "likely"],
      "per_page": 100,
      "sort_by_field": "relevance"
    }}
    ```

    **COMPETITIVE ADVANTAGES:**
    - **Market Analysis Integration:** Leverages existing strategic insights for focused research
    - **Competitive Intelligence:** Deep understanding of successful customer acquisition patterns
    - **Quality Assurance:** Iterative research validation ensures comprehensive coverage
    - **Strategic Optimization:** Balances lead volume with qualification precision
    - **Immediate Implementation:** Direct API parameters for instant lead generation

    **INTELLIGENCE QUALITY STANDARDS:**
    - 20+ job titles per priority segment with variations
    - 15+ professional skills mapped to target roles  
    - Complete company characteristic patterns for organization filtering
    - Technology adoption signals for intent-based targeting
    - Geographic and industry targeting validated against analysis
    - Comprehensive exclusion criteria to maximize lead quality

    Once you provide your product details and company information, I will execute the enhanced research process and deliver your comprehensive Apollo.io search parameters optimized for maximum lead generation effectiveness.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}

    Ready to begin advanced market intelligence research - provide your product and company details to start.
    """,
    sub_agents=[enhanced_prospect_research_pipeline],
    output_key="prospect_researcher",
)

root_agent = prospect_researcher