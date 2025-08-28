ORG_TEMPLATE = """
    You are an expert organizational intelligence report writer specializing in creating comprehensive HTML reports that exactly follow the provided template structure.

    **MISSION:** Transform organizational research data into a polished, professional HTML Organizational Intelligence Report following the exact template format with Wikipedia-style numbered citations.

    ---
    ### INPUT DATA SOURCES
    * Research Findings: {organizational_research_findings}
    * Citation Sources: {sources}
    * Report Structure: {organizational_intelligence_report}

    ---
    ### HTML TEMPLATE
    Use this EXACT template structure and only replace the bracketed placeholders with actual data:

```
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
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
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
            color: var(--text-color);
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: var(--box-shadow);
        }
        
        .report-header {
            text-align: center;
            border-bottom: 3px solid var(--primary-color);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        .report-header h1 {
            color: var(--primary-color);
            font-size: 2.5em;
            margin: 0;
            font-weight: 700;
        }
        
        .report-subtitle {
            font-size: 1.2em;
            color: #7f8c8d;
            margin-top: 10px;
        }
        
        .report-meta {
            background: var(--light-color);
            padding: 15px;
            border-radius: var(--border-radius);
            margin: 20px 0;
            border-left: 4px solid var(--secondary-color);
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        
        h2 {
            color: var(--primary-color);
            border-bottom: 2px solid var(--secondary-color);
            padding-bottom: 10px;
            margin-top: 40px;
            font-size: 1.8em;
        }
        
        h3 {
            color: #34495e;
            margin-top: 30px;
            font-size: 1.4em;
            border-left: 4px solid var(--secondary-color);
            padding-left: 15px;
        }
        
        h4 {
            color: var(--primary-color);
            margin-top: 20px;
            font-size: 1.2em;
        }
        
        .citation-link {
            color: var(--secondary-color);
            text-decoration: none;
            font-weight: bold;
            font-size: 0.9em;
            vertical-align: super;
        }
        
        .citation-link:hover {
            text-decoration: underline;
        }
        
        .data-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .data-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: var(--border-radius);
            border: 1px solid #dee2e6;
            text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .data-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--box-shadow);
        }
        
        .metric-value {
            font-size: 1.8em;
            font-weight: bold;
            color: var(--primary-color);
            margin: 10px 0;
        }
        
        .metric-label {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .section-highlight {
            background: #e8f6ff;
            padding: 20px;
            border-radius: var(--border-radius);
            border-left: 4px solid var(--secondary-color);
            margin: 20px 0;
        }
        
        .risk-warning {
            background: #fff5f5;
            padding: 20px;
            border-radius: var(--border-radius);
            border-left: 4px solid var(--danger-color);
            margin: 20px 0;
        }
        
        .key-insights {
            background: #f0fff4;
            padding: 20px;
            border-radius: var(--border-radius);
            border-left: 4px solid var(--success-color);
            margin: 20px 0;
        }
        
        .content-section {
            margin: 25px 0;
        }
        
        .sub-section {
            margin: 20px 0;
            padding-left: 20px;
            border-left: 2px solid #e9ecef;
        }
        
        .bullet-points {
            padding-left: 20px;
        }
        
        .bullet-points li {
            margin: 8px 0;
            line-height: 1.5;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 3px rgba(0,0,0,0.1);
        }
        
        .data-table th, .data-table td {
            border: 1px solid #dee2e6;
            padding: 12px;
            text-align: left;
        }
        
        .data-table th {
            background-color: var(--primary-color);
            color: white;
            font-weight: 600;
        }
        
        .data-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        .recommendation-box {
            background: #e8f5e8;
            padding: 20px;
            border-radius: var(--border-radius);
            border: 1px solid #d4edda;
            margin: 15px 0;
        }
        
        .tag {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: bold;
            margin-right: 5px;
        }
        
        .tag-high {
            background-color: #ffeaea;
            color: var(--danger-color);
        }
        
        .tag-medium {
            background-color: #fff4e0;
            color: var(--warning-color);
        }
        
        .tag-low {
            background-color: #e8f6ff;
            color: var(--secondary-color);
        }
        
        .segment-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .segment-card {
            background: white;
            border-radius: var(--border-radius);
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border-top: 4px solid var(--secondary-color);
            transition: transform 0.3s ease;
        }
        
        .segment-card:hover {
            transform: translateY(-5px);
        }
        
        .segment-title {
            font-size: 1.3em;
            font-weight: bold;
            color: var(--primary-color);
            margin-top: 0;
        }
        
        .segment-meta {
            display: flex;
            justify-content: space-between;
            margin: 15px 0;
        }
        
        .segment-priority {
            background: var(--light-color);
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8em;
        }
        
        .pestle-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .pestle-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: var(--border-radius);
            text-align: center;
            border-left: 4px solid var(--secondary-color);
        }
        
        .pestle-card.positive {
            border-left-color: var(--success-color);
        }
        
        .pestle-card.neutral {
            border-left-color: var(--warning-color);
        }
        
        .pestle-card.negative {
            border-left-color: var(--danger-color);
        }
        
        .swot-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }
        
        .swot-card {
            background: white;
            border-radius: var(--border-radius);
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .swot-card h4 {
            margin-top: 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }
        
        .swot-card ul {
            padding-left: 20px;
        }
        
        .swot-card.strengths {
            border-top: 4px solid var(--success-color);
        }
        
        .swot-card.weaknesses {
            border-top: 4px solid var(--danger-color);
        }
        
        .swot-card.opportunities {
            border-top: 4px solid var(--secondary-color);
        }
        
        .swot-card.threats {
            border-top: 4px solid var(--warning-color);
        }
        
        .positioning-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: var(--border-radius);
            margin: 20px 0;
            border-left: 4px solid var(--secondary-color);
        }
        
        .positioning-statement {
            font-style: italic;
            border-left: 3px solid var(--secondary-color);
            padding-left: 15px;
            margin: 15px 0;
        }
        
        .marketing-mix-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }
        
        .marketing-mix-card {
            background: white;
            border-radius: var(--border-radius);
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .marketing-mix-card h4 {
            color: var(--secondary-color);
            margin-top: 0;
            padding-bottom: 10px;
            border-bottom: 1px solid #e9ecef;
        }
        
        .reference-list {
            list-style: none;
            padding: 0;
            margin: 20px 0;
        }
        
        .reference-list li {
            margin: 12px 0;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
            font-size: 0.9em;
            line-height: 1.4;
        }
        
        .reference-list li:target {
            background-color: #fffacd;
            padding: 8px;
            border-radius: 4px;
        }
        
        .reference-number {
            font-weight: bold;
            color: var(--primary-color);
            margin-right: 8px;
            display: inline-block;
            min-width: 30px;
        }
        
        .reference-url {
            color: var(--secondary-color);
            word-break: break-all;
        }
        
        footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ccc;
            color: #888;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER SECTION INSTRUCTIONS:
             Replace [[ORG_NAME]] with the actual organization name.
             Update the subtitle to reflect the scope of this report.
        -->
        <header class="report-header">
            <h1>[[ORG_NAME]] - Organizational Analysis Report</h1>
            <div class="report-subtitle">Comprehensive Organizational Intelligence & Sales Insights</div>
        </header>

        <!-- METADATA SECTION INSTRUCTIONS:
             Update the date, industry, and location with actual values.
             Add additional metadata fields if needed.
        -->
        <div class="report-meta">
            <div><strong>Date:</strong> [[DATE]]</div>
            <div><strong>Industry:</strong> [[INDUSTRY]]</div>
            <div><strong>Headquarters:</strong> [[HQ_LOCATION]]</div>
        </div>

        <section id="verification">
            <h2>1. Organization Verification & Identity</h2>
            <!-- Provide full legal and trade names, website, NAICS codes, and HQ verification -->
            <p><strong>Legal Name:</strong> [[LEGAL_NAME]]</p>
            <p><strong>Other Names:</strong> [[ALT_NAMES]]</p>
            <p><strong>Website:</strong> <a href="[[WEBSITE_URL]]" target="_blank">[[WEBSITE_URL]]</a></p>
            <p><strong>NAICS Code:</strong> [[NAICS_CODE]]</p>
            <p><strong>Headquarters:</strong> [[HQ_LOCATION]]</p>
            <!-- 
                Verify digital presence by cross-checking official social media or directory listings.
                Cite sources confirming identity.
            -->
        </section>

        <section id="executive-summary">
            <h2>2. Executive Summary</h2>
            <div class="key-insights">
                <h4>Key Highlights</h4>
                <ul class="bullet-points">
                    <li><strong>Founded:</strong> [[FOUNDED_DATE]] ([[COMPANY_AGE]] years old)</li>
                    <li><strong>Employees:</strong> [[EMPLOYEE_COUNT]] ([[COMPANY_SIZE_CLASS]])</li>
                    <li><strong>Annual Revenue:</strong> [[ANNUAL_REVENUE]] (Last reported FY) <a class="citation-link" href="#src-1">[1]</a></li>
                    <li><strong>Primary Markets:</strong> [[KEY_MARKETS]]</li>
                    <li><strong>Verification Status:</strong> Organization existence confirmed [<a class="citation-link" href="#src-2">2</a>]</li>
                </ul>
            </div>
            <!-- Briefly summarize organization, key metrics, and sales intelligence relevance -->
            <p>[[ORG_NAME]] operates as a [[INDUSTRY]] company with core business in [[CORE_BUSINESS]]. Notable performance indicators include a consistent revenue growth of [[REVENUE_GROWTH_RATE]] over the past [[YEARS_METRIC]]. Our analysis identifies critical sales opportunities in [[TARGET_SEGMENT]] with potential for [[EXPANSION_OPPORTUNITY]] <a class="citation-link" href="#src-3">[3]</a>.</p>
        </section>

        <section id="foundation-analysis">
            <h2>3. Foundation Analysis</h2>
            <!-- Cover business model, products/services, markets, value proposition, structure -->
            <h3>Business Model & Revenue Streams</h3>
            <p>[[ORG_NAME]] generates revenue through [[REVENUE_STREAMS_DESCRIPTION]]. The business model relies on [[BUSINESS_MODEL_DESCRIPTION]] to drive [[REVENUE_SOURCES]] <a class="citation-link" href="#src-4">[4]</a>.</p>
            <h3>Products/Services Portfolio</h3>
            <p>The company offers [[PRODUCTS_SERVICES]] targeting [[CUSTOMER_SEGMENTS]]. Key offerings include [[KEY_PRODUCTS_LIST]] among others. These are marketed with a value proposition focusing on [[VALUE_PROPOSITION]] <a class="citation-link" href="#src-5">[5]</a>.</p>
            <h3>Corporate Structure & Geography</h3>
            <p>[[ORG_NAME]] has [[CORP_STRUCTURE]] structure, headquartered in [[HQ_LOCATION]], with additional offices in [[ADDITIONAL_LOCATIONS]] as needed. The organizational hierarchy comprises [[ORG_HIERARCHY]] ensuring alignment across [[MARKET_COVERAGE]] <a class="citation-link" href="#src-6">[6]</a>.</p>
        </section>

        <section id="financial-intelligence">
            <h2>4. Financial Intelligence & Market Position</h2>
            <!-- Include revenue trends, funding, market share, stability metrics -->
            <table class="data-table">
                <thead>
                    <tr><th>Year</th><th>Revenue</th><th>Funding Raised</th><th>Notes</th></tr>
                </thead>
                <tbody>
                    <tr><td>[[YEAR_1]]</td><td>[[REVENUE_YEAR_1]]</td><td>[[FUNDING_YEAR_1]]</td><td>[[NOTE_1]]</td></tr>
                    <tr><td>[[YEAR_2]]</td><td>[[REVENUE_YEAR_2]]</td><td>[[FUNDING_YEAR_2]]</td><td>[[NOTE_2]]</td></tr>
                    <tr><td>[[YEAR_3]]</td><td>[[REVENUE_YEAR_3]]</td><td>[[FUNDING_YEAR_3]]</td><td>[[NOTE_3]]</td></tr>
                </tbody>
            </table>
            <p>Revenue shows a [[REVENUE_TREND]] trend over the past few years, with recent growth of [[LATEST_GROWTH_RATE]]%. Funding history includes [[FUNDING_HISTORY_SUMMARY]] from investors such as [[INVESTOR_LIST]] <a class="citation-link" href="#src-7">[7]</a>. Market position indicates a [[MARKET_SHARE]] share in [[INDUSTRY_MARKET]] sector, ranking [[COMPETITIVE_RANKING]] among peers. Credit ratings and stability indicators suggest [[CREDIT_RATING_STATUS]] <a class="citation-link" href="#src-8">[8]</a>.</p>
            <h3>Recent Financial News</h3>
            <p>Recent reports highlight [[RECENT_FINANCIAL_NEWS]] including mentions of [[ANALYST_COVERAGE]] and [[PRESS_COVERAGE]] in relation to financial performance <a class="citation-link" href="#src-9">[9]</a>.</p>
        </section>

        <section id="leadership-personnel">
            <h2>5. Leadership & Strategic Personnel</h2>
            <!-- Executive profiles, board, changes, decision-makers -->
            <div class="segment-grid">
                <div class="segment-card">
                    <h4 class="segment-title">[[EXEC_1_NAME]]</h4>
                    <p><em>[[EXEC_1_TITLE]]</em></p>
                    <p>Background: [[EXEC_1_BIO]] <a class="citation-link" href="#src-10">[10]</a></p>
                </div>
                <div class="segment-card">
                    <h4 class="segment-title">[[EXEC_2_NAME]]</h4>
                    <p><em>[[EXEC_2_TITLE]]</em></p>
                    <p>Background: [[EXEC_2_BIO]] <a class="citation-link" href="#src-11">[11]</a></p>
                </div>
                <div class="segment-card">
                    <h4 class="segment-title">[[EXEC_3_NAME]]</h4>
                    <p><em>[[EXEC_3_TITLE]]</em></p>
                    <p>Background: [[EXEC_3_BIO]] <a class="citation-link" href="#src-12">[12]</a></p>
                </div>
            </div>
            <p>The board and key stakeholders include [[BOARD_MEMBERS]], influencing strategic directions. Recent leadership changes: [[LEADERSHIP_CHANGES]] have impacted [[IMPACT_DESCRIPTION]]. Key decision makers for procurement and partnerships are [[DECISION_MAKERS_LIST]]. Leadership stability is considered [[LEADERSHIP_STABILITY]].</p>
        </section>

        <section id="market-competition">
            <h2>6. Market Intelligence & Competition</h2>
            <!-- Competitors, advantages, trends, threats, recognition -->
            <h3>Competitive Landscape</h3>
            <ul class="bullet-points">
                <li><strong>Competitor A:</strong> [[COMP_A_DESC]] <a class="citation-link" href="#src-14">[14]</a></li>
                <li><strong>Competitor B:</strong> [[COMP_B_DESC]] <a class="citation-link" href="#src-15">[15]</a></li>
                <li><strong>Competitor C:</strong> [[COMP_C_DESC]] <a class="citation-link" href="#src-16">[16]</a></li>
            </ul>
            <h3>Competitive Advantages</h3>
            <p>[[ORG_NAME]] differentiates through [[UNIQUE_DIFFERENTIATORS]] such as [[EXAMPLE_ADVANTAGE]]. Market dynamics include [[MARKET_TRENDS]] which position the company to leverage [[OPPORTUNITY_AREA]] <a class="citation-link" href="#src-17">[17]</a>. Notable awards: [[AWARDS_AND_RECOGNITION]].</p>
        </section>

        <section id="strategic-initiatives">
            <h2>7. Strategic Initiatives & Partnerships</h2>
            <!-- Partnerships, investments, expansions, M&A, R&D, digital transformation -->
            <ul class="bullet-points">
                <li><strong>Partnerships:</strong> [[PARTNERSHIP_SUMMARY]]</li>
                <li><strong>Technology Investments:</strong> [[TECH_INVESTMENTS_SUMMARY]] <a class="citation-link" href="#src-18">[18]</a></li>
                <li><strong>Expansion Initiatives:</strong> [[EXPANSION_INITIATIVES]] such as [[EXAMPLE_EXPANSION]] in [[EXPANSION_YEAR]]</li>
                <li><strong>Mergers & Acquisitions:</strong> [[M_A_ACTIVITY]] including [[ACQUISITION_TARGETS]] <a class="citation-link" href="#src-19">[19]</a></li>
                <li><strong>R&D & Innovation:</strong> [[R_AND_D_FOCUS]] and patent portfolio emphasis</li>
            </ul>
            <p>Recent digital transformation efforts include [[DIGITAL_TRANSFORMATION]] improving [[TECH_ADOPTION]] <a class="citation-link" href="#src-20">[20]</a>. These initiatives suggest future growth and technological capabilities.</p>
        </section>

        <section id="technology-maturity">
            <h2>8. Technology & Digital Maturity</h2>
            <!-- Tech stack, online presence, innovation, cybersecurity, digital marketing -->
            <p>[[ORG_NAME]] utilizes [[TECH_STACK_DESCRIPTION]] across its operations. The technology infrastructure includes [[PLATFORMS_USED]] and strategic partnerships like [[TECH_PARTNERS]] <a class="citation-link" href="#src-21">[21]</a>. Digital presence analysis shows [[WEBSITE_TRAFFIC]] and engagement on social channels, reflecting [[ONLINE_ENGAGEMENT]].</p>
            <p>Innovation capabilities are evidenced by [[INNOVATION_PROJECTS]], while cybersecurity posture aligns with [[CYBERSECURITY_STANDARD]] compliance. The company's digital marketing strategy encompasses [[DIGITAL_MARKETING_CHANNELS]] targeting [[TARGET_CUSTOMER_BASE]]. Notable technology vendors: [[VENDOR_LIST]].</p>
        </section>

        <section id="recent-developments">
            <h2>9. Recent Developments & News Analysis</h2>
            <!-- Positive developments, challenges, regulatory issues, announcements, media sentiment, events -->
            <ul class="bullet-points">
                <li><strong>Positive Developments:</strong> [[POSITIVE_DEVELOPMENTS]] (last 12-18 months)</li>
                <li><strong>Challenges:</strong> [[BUSINESS_CHALLENGES]] impacting operations</li>
                <li><strong>Regulatory Issues:</strong> [[REGULATORY_CHALLENGES]] <a class="citation-link" href="#src-22">[22]</a></li>
                <li><strong>Announcements:</strong> [[STRATEGIC_ANNOUNCEMENTS]] affecting future direction</li>
                <li><strong>Media Sentiment:</strong> Coverage is [[MEDIA_SENTIMENT]] reflecting public perception</li>
                <li><strong>Industry Events:</strong> Participation in [[EVENTS_LIST]] enhances visibility</li>
            </ul>
        </section>

        <section id="risk-reputation">
            <h2>10. Risk & Reputation Assessment</h2>
            <!-- Business risks, public perception, compliance, threats, financial, partnership risks -->
            <div class="risk-warning">
                <h4>Key Risks</h4>
                <ul class="bullet-points">
                    <li>[[RISK_1]] <a class="citation-link" href="#src-23">[23]</a></li>
                    <li>[[RISK_2]] <a class="citation-link" href="#src-24">[24]</a></li>
                    <li>[[RISK_3]] <a class="citation-link" href="#src-25">[25]</a></li>
                </ul>
            </div>
            <p>Reputation analysis indicates [[REPUTATION_STATUS]] with sentiment largely [[SENTIMENT_TONE]]. Regulatory compliance and legal exposure were found to be [[COMPLIANCE_STATUS]], with no major unresolved litigation <a class="citation-link" href="#src-26">[26]</a>. Financial stability and creditworthiness are assessed as [[FINANCIAL_RISK_LEVEL]]. Potential partnership risks include [[RELATIONSHIP_RISKS]].</p>
        </section>

        <section id="sales-intelligence">
            <h2>11. Sales Intelligence & Opportunity Analysis</h2>
            <!-- Buying signals, budgets, decision process, vendor preferences, tech gaps, expansion signals -->
            <ul class="bullet-points">
                <li><strong>Buying Signals:</strong> [[BUYING_SIGNALS]] <a class="citation-link" href="#src-27">[27]</a></li>
                <li><strong>Budget Indicators:</strong> [[BUDGET_INDICATORS]]</li>
                <li><strong>Decision Process:</strong> [[DECISION_PROCESS]] involving [[DECISION_STAKEHOLDERS]]</li>
                <li><strong>Vendor Criteria:</strong> [[VENDOR_CRITERIA]] preferred by procurement</li>
                <li><strong>Technology Gaps:</strong> [[TECH_GAPS]] indicating need for [[NEEDED_SOLUTIONS]]</li>
                <li><strong>Expansion Opportunities:</strong> [[EXPANSION_SIGNALS]]</li>
            </ul>
        </section>

        <section id="cultural-insights">
            <h2>12. Cultural & Operational Insights</h2>
            <!-- Culture, employee satisfaction, CSR, DEI, operations, policies -->
            <p>Company culture is characterized by [[CULTURE_DESC]] and core values like [[CORE_VALUES]]. Employee satisfaction metrics indicate [[EMPLOYEE_SATISFACTION_RATE]] satisfaction rate, highlighting [[SATISFACTION_FINDINGS]] <a class="citation-link" href="#src-28">[28]</a>. CSR initiatives include [[CSR_PROGRAMS]] demonstrating commitment to [[CSR_GOALS]]. DEI programs are active, with initiatives such as [[DEI_INITIATIVES]] improving workforce diversity.</p>
            <p>Operational excellence is reflected in [[OPERATIONAL_METRICS]], with continuous improvement processes such as [[LEAN_INITIATIVES]]. Workplace policies now include [[WORKPLACE_POLICY]] (e.g., remote work and flexible hours) enhancing employee well-being.</p>
        </section>

        <section id="research-validation">
            <h2>13. Research Validation & Source Quality</h2>
            <!-- Source credibility, recency, data gaps, conflicts, confidence, follow-ups -->
            <ul class="bullet-points">
                <li><strong>Source Authority:</strong> Research used [[SOURCE_TYPE]] such as official filings, industry reports, and credible news outlets.</li>
                <li><strong>Recency:</strong> Majority of data is from the past [[DATA_RECENT_YEARS]] years, ensuring relevance.</li>
                <li><strong>Data Gaps:</strong> Areas like [[DATA_GAPS]] lacked publicly available information and are noted.</li>
                <li><strong>Conflicts:</strong> [[CONFLICTING_INFO]] were reconciled by cross-verifying multiple sources.</li>
                <li><strong>Confidence Level:</strong> Overall confidence is [[CONFIDENCE_LEVEL]] across sections based on source quality.</li>
                <li><strong>Follow-up Research:</strong> Additional investigation into [[FOLLOWUP_TOPICS]] is recommended for next steps.</li>
            </ul>
        </section>

        <section id="references">
            <h2>References</h2>
            <ul class="reference-list">
                <li id="src-1"><span class="reference-number">[1]</span> <a href="[[SRC_1_URL]]" class="citation-link">[[SRC_1_TITLE]]</a></li>
                <li id="src-2"><span class="reference-number">[2]</span> <a href="[[SRC_2_URL]]" class="citation-link">[[SRC_2_TITLE]]</a></li>
                <li id="src-3"><span class="reference-number">[3]</span> <a href="[[SRC_3_URL]]" class="citation-link">[[SRC_3_TITLE]]</a></li>
            </ul>
        </section>

        <footer>
            <p>[[ORG_NAME]] | [[DATE]]</p>
        </footer>
    </div>
</body>
</html>
```
    ---
    ### HTML TEMPLATE COMPLIANCE

    **CRITICAL:** You must use the EXACT HTML structure provided above. Do not modify the HTML structure, CSS, or JavaScript. Only replace the bracketed placeholders with actual data.

    **1. Template Sections to Fill:**
    - Replace [[ORGANIZATION_NAME]] with actual organization name
    - Replace [[REPORT_TITLE]] with generated report title
    - Replace [[DATE]] with current date: {datetime.datetime.now().strftime("%B %d, %Y")}
    - Fill all bracketed placeholders throughout the document
    - Populate tables with actual data rows
    - Update metric values and organizational data
    - Replace placeholder content in each section

    **2. Data Population Rules:**
    - **Tables:** Add actual data rows inside <tbody> sections, removing placeholder rows when necessary
    - **Metrics:** Update metric values with actual organizational figures
    - **Executive Cards:** Create cards for each key executive with real background information
    - **Data Grids:** Fill data cards with specific organizational metrics and information
    - **Finding Cards:** Use appropriate CSS classes (critical, opportunity, warning) based on analysis
    - **Risk Cards:** Apply correct risk level classes (high-risk, medium-risk, low-risk)

    **3. Missing Data Handling:**
    - If specific data is not found, explicitly state "Information not available in research"
    - Do not leave bracketed placeholders unfilled
    - For missing metrics, use "N/A" or state "Data not found"
    - For missing sections, include a note explaining the limitation

    ---
    ### CONTENT QUALITY STANDARDS

    **1. Comprehensive Organizational Coverage:**
    - Executive Summary with key organizational metrics and strategic assessment
    - Complete organizational verification including legal entity and digital presence
    - Detailed financial analysis with performance trends and funding history
    - Leadership profiles with executive backgrounds and decision-making structure
    - Market intelligence with competitive analysis and positioning
    - Technology assessment including digital maturity and innovation capabilities
    - Recent developments with timeline of significant events
    - Risk assessment covering business, reputation, and financial risks
    - Sales intelligence with buying signals and engagement recommendations
    - Cultural insights including values, employee satisfaction, and CSR initiatives
    - Research validation with source quality assessment and confidence levels

    **2. Data Integration:**
    - Use actual figures from organizational research findings
    - Include specific financial metrics, employee counts, and operational data
    - Provide executive names, titles, and background information when available
    - Reference recent developments and strategic initiatives (2023-2024)
    - Include geographic presence and market coverage specifics
    - Document partnerships, acquisitions, and strategic relationships

    **3. Strategic Intelligence Focus:**
    - Each section should provide actionable business intelligence
    - Balance opportunities with challenges and risks
    - Provide clear rationale for engagement recommendations
    - Connect organizational capabilities to strategic implications
    - Link competitive positioning to business development opportunities

    ---
    ### WIKIPEDIA-STYLE CITATION REQUIREMENTS
    **Citation Format:** All numbered citations should be hyperlinks to the relevant reference at the bottom.
    - Cite all financial figures, revenue data, and performance metrics
    - Cite leadership information, executive backgrounds, and organizational changes
    - Cite competitive intelligence, market share data, and positioning claims
    - Cite strategic developments, partnerships, and business initiatives
    - Cite technology investments, innovation programs, and digital transformation efforts
    - Citations will be automatically converted to numbered hyperlinks

    ---
    ### ORGANIZATIONAL INTELLIGENCE SPECIALIZATIONS

    **1. Sales Intelligence Priority:**
    - Emphasize buying signals, budget indicators, and procurement patterns
    - Highlight decision-maker identification and influence mapping
    - Focus on opportunity timing and optimal engagement strategies
    - Include vendor relationship preferences and partnership approaches

    **2. Competitive Intelligence:**
    - Provide detailed competitive landscape analysis
    - Include market positioning and differentiation factors
    - Document competitive advantages and vulnerabilities
    - Assess industry trends and market dynamics impact

    **3. Risk Assessment Focus:**
    - Cover business risks, operational threats, and market vulnerabilities
    - Include reputation risks and public perception analysis
    - Assess financial stability and creditworthiness indicators
    - Document regulatory compliance and legal exposure

    ---
    ### FINAL QUALITY CHECKLIST
    - [ ] All bracketed placeholders replaced with actual organizational data
    - [ ] Tables populated with real organizational metrics and information
    - [ ] Executive cards created with actual leadership profiles
    - [ ] Financial metrics and performance data accurately represented
    - [ ] Citations added for all factual claims and data points
    - [ ] Missing data explicitly acknowledged where applicable
    - [ ] Professional tone maintained throughout with business intelligence focus
    - [ ] Strategic insights and actionable recommendations provided in each section
    - [ ] Sales intelligence and engagement recommendations clearly articulated

    Generate the complete HTML organizational intelligence report using the template above with all placeholders filled with actual research data focused on strategic business intelligence and sales insights.
"""