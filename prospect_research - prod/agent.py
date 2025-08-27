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

market_analysis = """
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

segmentation_analysis = """
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


# --- Structured Output Models (UNCHANGED) ---
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


# --- Custom Agent for Loop Control (UNCHANGED) ---
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

# --- SUPPORTING CLASSES ---
class ApolloParameterConsolidator(BaseAgent):
    """Consolidates all persona data into unified Apollo.io search parameters."""
    async def _run_async_impl(self, inputs, ctx):
        consolidated = inputs["persona_data_collection"]
        consolidated_params = ApolloSearchParameters()
        # Example consolidation logic (simplified)
        titles = set()
        seniorities = set()
        locations = set()
        skills = set()
        keywords = set()
        industries = set()
        sizes = set()
        tech = set()
        not_titles = set()
        not_keywords = set()
        for persona in consolidated.personas:
            titles.update(persona.job_titles)
            seniorities.update(persona.seniorities)
            locations.update(persona.locations)
            skills.update(persona.skills)
            keywords.update(persona.keywords)
            industries.update(persona.industries)
            sizes.update(persona.company_sizes)
            tech.update(persona.technologies)
            not_titles.update(persona.exclude_titles)
            not_keywords.update(persona.exclude_keywords)
        consolidated_params.person_titles = list(titles)
        consolidated_params.person_seniorities = list(seniorities)
        consolidated_params.person_locations = list(locations)
        consolidated_params.person_skills = list(skills)
        consolidated_params.person_keywords = list(keywords)
        consolidated_params.organization_industry_tag_ids = list(industries)
        consolidated_params.organization_num_employees_ranges = list(sizes)
        consolidated_params.organization_technologies = list(tech)
        consolidated_params.person_not_titles = list(not_titles)
        consolidated_params.person_not_keywords = list(not_keywords)
        # Default filters
        consolidated_params.email_status = ["verified", "likely"]
        consolidated_params.sort_by_field = "relevance"
        consolidated_params.per_page = 100
        ctx.session.state["prospect_researcher"] = consolidated_params.dict()
        yield Event(author=self.name, content="Apollo.io search parameters consolidated and optimized.")

# --- Context Extraction and Segmentation Integration Agents ---
context_extractor = LlmAgent(
    model = config.search_model,
    name="context_extractor",
    description="Extracts product and market context from provided analysis reports.",
    instruction=f"""
    You are a market context expert. You have access to detailed `market_analysis` and `segmentation_analysis` reports, as well as the user’s product description and company information. Using these, identify:
    1. The product's category or type.
    2. Primary target industries or buyer segments.
    3. Representative buyer roles and decision-making levels.
    4. Key competitors or alternative solutions.
    Provide the output as a JSON object with keys:
    * product_category (string),
    * industries (list of strings),
    * roles (list of strings),
    * competitors (list of strings).
    """,
    output_key="context_data",
)

segmentation_integrator = LlmAgent(
    model = config.search_model,
    name="segmentation_integrator",
    description="Maps priority customer segments to relevant targeting attributes.",
    instruction=f"""
    You are a strategic segmentation analyst. You have access to the `segmentation_analysis` report detailing priority customer segments (e.g., Segment A, Segment B, Segment C). For each segment, identify actionable targeting attributes including:
    - Relevant industries or sectors.
    - Typical company size ranges (e.g., 1-50, 51-200).
    - Representative job titles or buyer roles.
    - Key skills, technologies, or keywords.
    Output the results as a JSON object where each key is a segment name (e.g., "Segment A") and the value is an object with keys:
    * industries (list of strings)
    * company_sizes (list of strings)
    * roles (list of strings)
    * keywords (list of strings)
    """,output_key="segmentation_mapping",
)

# --- STREAMLINED AGENTS ---
consolidated_persona_researcher = LlmAgent(
    model = config.search_model,
    name="consolidated_persona_researcher",
    description="Executes comprehensive customer persona research focused on Apollo.io parameter optimization.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction=f"""
    You are a specialized customer research analyst focused on gathering data for Apollo.io lead generation optimization.

    **MISSION:** Conduct focused research to collect precise demographic, firmographic, and behavioral data optimized for Apollo.io People Search API parameters.

    **INPUT DATA:**
    * Market Analysis: `{market_analysis}`
    * Segmentation Analysis: `{segmentation_analysis}`
    * Context Information: `{{context_data}}`

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
    model = config.critic_model,
    name="persona_research_evaluator",
    description="Evaluates persona research for Apollo.io parameter completeness.",
    instruction=f"""
    You are a senior research analyst evaluating persona research for Apollo.io lead generation effectiveness.
    You have access to the detailed `{market_analysis}` and `{segmentation_analysis}` for context.

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
    model = config.search_model,
    name="enhanced_persona_search",
    description="Executes targeted follow-up searches to fill Apollo.io parameter gaps.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction=f"""
    You are a specialist researcher filling critical gaps in Apollo.io parameter data.
    You have access to the detailed {market_analysis} and {segmentation_analysis} reports for context.

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
    model = config.critic_model,
    name="persona_data_generator",
    description="Generates structured persona data optimized for Apollo.io parameters.",
    instruction= f"""
    You are an expert data architect creating structured persona data optimized for Apollo.io lead generation.

    **MISSION:** Transform research findings into structured persona data that maps directly to Apollo.io People Search API parameters.

    ### INPUT DATA
    * Persona Research Findings: `{{persona_research_findings}}`
    * Market Analysis Report: `{market_analysis}`
    * Segmentation Analysis Report: `{segmentation_analysis}`
    * Segmentation Mapping: `{{segmentation_mapping}}`

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
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="persona_data_collection",
)

apollo_parameter_generator = LlmAgent(
    model = config.critic_model,
    name="apollo_parameter_generator",
    description="Generates consolidated Apollo.io search parameters from all persona data.",
    instruction=f"""
    You are an Apollo.io optimization expert creating comprehensive search parameters.
    You have access to the detailed `{market_analysis}` and `{segmentation_analysis}` for context.

    **MISSION:** Consolidate all persona data into optimized Apollo.io People Search API parameters.

    ### INPUT DATA
    * Persona Data Collection: `{{persona_data_collection}}`

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
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="prospect_researcher",
)

# --- STREAMLINED PIPELINE ---
prospect_research_pipeline = SequentialAgent(
    name="prospect_research_pipeline",
    description="Executes efficient persona research and generates consolidated Apollo.io search parameters.",
    sub_agents=[
        context_extractor,
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
        segmentation_integrator,
        persona_data_generator,
        apollo_parameter_generator,
    ],
)

# # --- MAIN STREAMLINED APOLLO AGENT ---
# prospect_researcher = LlmAgent(
#     name="prospect_researcher",
#     model = config.worker_model,
#     description="Streamlined customer persona research assistant that generates consolidated Apollo.io search parameters through focused market analysis.",
#     instruction=f"""
#     You are a streamlined Apollo.io Lead Generation Assistant focused on creating optimized search parameters.

#     **CORE MISSION:**
#     Generate consolidated Apollo.io People Search API parameters through efficient persona research.

#     **REQUIRED INPUTS:**
#     Users must provide:
#     1. **Product/Service Description:** Features, benefits, use cases, target market
#     2. **Company Information:** Background, market positioning, competitive context
#     3. **Known Competitors (Optional):** Any known competitors (I'll research more)
#     4. **Market Analysis Report:** `{market_analysis}`
#     5. **Segmentation Analysis Report:** `{segmentation_analysis}`

#     **STREAMLINED WORKFLOW:**
#     You use an efficient research methodology with single quality review:

#     **Phase 1: Comprehensive Research**
#     - Identify job titles, seniority levels, and role variations
#     - Research company size patterns, industries, and geographic distribution
#     - Analyze professional skills, technology adoption, and behavioral patterns
#     - Map competitive landscape and alternative solution usage

#     **Phase 2: Quality Validation**
#     - Ensure sufficient data for effective Apollo.io parameter generation
#     - Validate job title precision and demographic coverage
#     - Confirm skills intelligence and technology adoption insights
#     - Execute follow-up searches to fill any critical gaps

#     **Phase 3: Parameter Generation**
#     - Transform research into structured persona data
#     - Consolidate all insights into unified Apollo.io search parameters
#     - Optimize for maximum relevant lead discovery
#     - Balance precision with comprehensive market coverage

#     **FINAL OUTPUT:**
#     Single JSON object with consolidated Apollo.io People Search API parameters:

#     ```json
#     {{
#       "person_titles": ["all relevant job titles"],
#       "person_seniorities": ["seniority levels"],
#       "person_locations": ["geographic targeting"],
#       "person_skills": ["professional skills"],
#       "person_keywords": ["positive keywords"],
#       "organization_num_employees_ranges": ["company sizes"],
#       "organization_industry_tag_ids": ["industries"],
#       "organization_keywords": ["company keywords"],
#       "organization_technologies": ["technology stack"],
#       "person_not_keywords": ["exclusion terms"],
#       "email_status": ["verified", "likely"],
#       "per_page": 100,
#       "sort_by_field": "relevance"
#     }}
#     ```

#     **KEY ADVANTAGES:**
#     - **Maximized Lead Volume:** Consolidates all personas into a single comprehensive search
#     - **Maintained Relevance:** Uses exclusion filters and qualification criteria
#     - **Immediate Implementation:** Direct API parameters for instant lead generation
#     - **Optimized Coverage:** Balances specificity with market opportunity

#     **RESEARCH FOCUS:**
#     All research specifically targets Apollo.io parameter optimization:
#     - Exact job titles suitable for person_titles filtering
#     - Professional skills and keywords for precise targeting
#     - Company characteristics for organization-level filtering
#     - Technology adoption patterns for intent signaling
#     - Geographic and industry targeting for market focus

#     Once you provide your product and company details (along with the market_analysis and segmentation_analysis reports), I will execute the streamlined research process and deliver your optimized Apollo.io search parameters as a single JSON object.

#     Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
#     Ready to generate your Apollo.io search parameters.
#     """,
#     sub_agents=[prospect_research_pipeline],
#     output_key="prospect_researcher",
# )
root_agent = prospect_research_pipeline
