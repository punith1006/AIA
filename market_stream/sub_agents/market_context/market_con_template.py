CON_TEMPLATE = """
    You are an expert market-context HTML report generator. You were given a fixed HTML template (do not alter it) that contains bracketed placeholders like [[PRODUCT_NAME]], [[REGIONAL_TABLE_JSON]], etc. Your job: **output only one artifact — the complete HTML file** with every bracketed placeholder replaced according to the rules below. Do not output commentary, analysis, or any extra text.

    

    INPUT
    - `market_research_findings` (text / bullet list) — use facts from here to populate placeholders.
    - `citations` (list of objects: {id, title, url, accessed}) — map these to reference anchors in the References section.
    - `market_intelligence_agent` (report-structure instructions) — follow if relevant.

    RETURN
    - Exactly one file: the completed HTML document string. No other output allowed.
    ---
    ### INPUT DATA SOURCES
    * Research Findings: {market_research_findings}
    * Citation Sources: {citations}
    * Report Structure: {market_intelligence_agent}

    ---
    ### HTML TEMPLATE
    Use this EXACT template structure, replace the bracketed placeholders and create the tables and charts with actual data:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[[PRODUCT_NAME]]: [[REPORT_TITLE]]</title>
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
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 40px 60px;
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
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .toc {
            background: #f8f9fa;
            padding: 30px;
            border-radius: var(--border-radius);
            border: 1px solid #dee2e6;
            margin: 30px 0;
        }
        
        .toc-list {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px 40px;
            list-style: none;
            padding: 0;
        }
        
        .toc-list li {
            margin: 8px 0;
            break-inside: avoid;
        }
        
        .toc-list a {
            color: var(--primary-color);
            text-decoration: none;
            font-weight: 500;
            display: block;
            padding: 8px 10px;
            transition: all 0.3s ease;
            border-radius: 4px;
        }
        
        .toc-list a:hover {
            background: var(--secondary-color);
            color: white;
            transform: translateX(5px);
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
        
        .wide-content {
            width: 100%;
            margin: 20px 0;
        }
        
        .data-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin: 25px 0;
        }
        
        .data-card {
            background: #f8f9fa;
            padding: 25px;
            border-radius: var(--border-radius);
            border: 1px solid #dee2e6;
            text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .data-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--secondary-color);
        }
        
        .data-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--box-shadow);
        }
        
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: var(--primary-color);
            margin: 15px 0;
            display: block;
        }
        
        .metric-label {
            color: #7f8c8d;
            font-size: 0.95em;
            font-weight: 600;
        }
        
        .market-chart {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: var(--border-radius);
            padding: 25px;
            margin: 25px 0;
        }
        
        .chart-bar {
            display: flex;
            align-items: center;
            margin: 15px 0;
            position: relative;
        }
        
        .chart-label {
            min-width: 120px;
            font-weight: 600;
            color: var(--primary-color);
        }
        
        .chart-track {
            flex: 1;
            height: 25px;
            background: #e9ecef;
            border-radius: 12px;
            margin: 0 15px;
            overflow: hidden;
            position: relative;
        }
        
        .chart-fill {
            height: 100%;
            border-radius: 12px;
            position: relative;
        }
        
        .tam-fill { background: #27ae60; width: 100%; }
        .sam-fill { background: #3498db; width: 60%; }
        .som-fill { background: #e74c3c; width: 20%; }
        
        .chart-value {
            min-width: 100px;
            text-align: right;
            font-weight: 600;
            color: var(--text-color);
        }
        
        .section-highlight {
            background: #e8f6ff;
            padding: 25px;
            border-radius: var(--border-radius);
            border-left: 4px solid var(--secondary-color);
            margin: 25px 0;
        }
        
        .risk-warning {
            background: #fff5f5;
            padding: 25px;
            border-radius: var(--border-radius);
            border-left: 4px solid var(--danger-color);
            margin: 25px 0;
        }
        
        .key-insights {
            background: #f0fff4;
            padding: 25px;
            border-radius: var(--border-radius);
            border-left: 4px solid var(--success-color);
            margin: 25px 0;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            box-shadow: 0 2px 3px rgba(0,0,0,0.1);
            border-radius: var(--border-radius);
            overflow: hidden;
        }
        
        .data-table th, .data-table td {
            border: 1px solid #dee2e6;
            padding: 15px 12px;
            text-align: left;
        }
        
        .data-table th {
            background-color: var(--primary-color);
            color: white;
            font-weight: 600;
            font-size: 0.95em;
        }
        
        .data-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        .data-table tr:hover {
            background-color: #e8f6ff;
        }
        
        .competitive-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }
        
        .competitor-card {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: var(--border-radius);
            padding: 20px;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .competitor-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        .competitor-name {
            font-weight: bold;
            color: var(--primary-color);
            font-size: 1.1em;
            margin-bottom: 10px;
        }
        
        .competitor-focus {
            color: #7f8c8d;
            font-size: 0.9em;
            font-style: italic;
        }
        
        .risk-matrix {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 25px 0;
        }
        
        .risk-item {
            padding: 15px;
            border-radius: var(--border-radius);
            text-align: center;
            font-weight: 600;
            color: white;
        }
        
        .risk-high { background-color: var(--danger-color); }
        .risk-medium { background-color: var(--warning-color); }
        .risk-low { background-color: var(--success-color); }
        
        .stakeholder-map {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 25px 0;
        }
        
        .stakeholder-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: var(--border-radius);
            border-left: 4px solid var(--secondary-color);
            text-align: center;
        }
        
        .timeline {
            position: relative;
            margin: 30px 0;
            padding: 20px 0;
        }
        
        .timeline-item {
            display: flex;
            margin: 20px 0;
            align-items: center;
        }
        
        .timeline-marker {
            width: 20px;
            height: 20px;
            background: var(--secondary-color);
            border-radius: 50%;
            margin-right: 20px;
            flex-shrink: 0;
        }
        
        .timeline-content {
            background: #f8f9fa;
            padding: 15px 20px;
            border-radius: var(--border-radius);
            border-left: 4px solid var(--secondary-color);
            flex: 1;
        }
        
        .citation {
            color: var(--secondary-color);
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9em;
        }
        
        .citation:hover {
            text-decoration: underline;
        }
        
        .references {
            background: #f8f9fa;
            padding: 30px;
            border-radius: var(--border-radius);
            border: 1px solid #dee2e6;
            margin: 40px 0;
        }
        
        .references h2 {
            color: var(--primary-color);
            border-bottom: 2px solid var(--secondary-color);
            padding-bottom: 10px;
        }
        
        .references ol {
            padding-left: 20px;
        }
        
        .references li {
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid #e9ecef;
        }
        
        .references li:last-child {
            border-bottom: none;
        }
        
        .references a {
            color: var(--secondary-color);
            text-decoration: none;
            font-weight: 500;
        }
        
        .references a:hover {
            text-decoration: underline;
        }
        
        footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
            font-size: 0.9em;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 20px 30px;
            }
            
            .toc-list {
                grid-template-columns: 1fr;
            }
            
            .report-meta {
                grid-template-columns: 1fr;
            }
            
            .data-grid {
                grid-template-columns: 1fr;
            }
            
            .competitive-grid {
                grid-template-columns: 1fr;
            }
            
            .risk-matrix {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="report-header">
            <h1>[[PRODUCT_NAME]]</h1>
            <p class="report-subtitle">[[REPORT_SUBTITLE]]</p>
            <div class="report-meta">
                <div><strong>Date:</strong> [[REPORT_DATE]]</div>
                <div><strong>Market Focus:</strong> [[MARKET_FOCUS]]</div>
                <div><strong>Industry:</strong> [[INDUSTRY_FOCUS]]</div>
                <div><strong>Analysis Period:</strong> [[ANALYSIS_PERIOD]]</div>
            </div>
        </div>

        <div class="toc">
            <h2>Table of Contents</h2>
            <ul class="toc-list">
                <li><a href="#executive-summary">1. Executive Summary</a></li>
                <li><a href="#market-overview">2. Market Overview</a></li>
                <li><a href="#market-sizing">3. Market Sizing</a></li>
                <li><a href="#industry-ecosystem">4. Industry Ecosystem</a></li>
                <li><a href="#customer-behavior">5. Customer Behavior & Adoption</a></li>
                <li><a href="#market-maturity">6. Market Maturity & Trends</a></li>
                <li><a href="#geographic-analysis">7. Geographic Market Analysis</a></li>
                <li><a href="#risk-analysis">8. Risk Analysis</a></li>
                <li><a href="#investment-flows">9. Investment & Capital Flows</a></li>
                <li><a href="#channel-distribution">10. Channel & Distribution</a></li>
                <li><a href="#scenario-planning">11. Scenario Planning</a></li>
                <li><a href="#stakeholder-mapping">12. Stakeholder Mapping</a></li>
                <li><a href="#conclusions">13. Conclusions & Recommendations</a></li>
                <li><a href="#references">References</a></li>
            </ul>
        </div>

        <!-- 
        EXECUTIVE SUMMARY INSTRUCTIONS:
        
        1.  Update the product name and report title throughout the document
        2.  Provide a clear objective for the report
        3.  Fill in key market metrics with appropriate values and citations
        4.  Define the product-market boundary and regulatory context
        5.  Summarize key findings and strategic implications
        -->
        <section id="executive-summary">
            <h2>1. Executive Summary</h2>
            
            <div class="section-highlight">
                <h3>Objective</h3>
                <p>[[REPORT_OBJECTIVE]]</p>
            </div>

            <div class="key-insights">
                <h3>Key Market Dynamics and Opportunities</h3>
                
                <div class="data-grid">
                    <div class="data-card">
                        <span class="metric-value">[[TAM_VALUE]]</span>
                        <div class="metric-label">[[TAM_DESCRIPTION]] <a href="#ref1" class="citation">[1]</a><a href="#ref2" class="citation">[2]</a><a href="#ref4" class="citation">[4]</a></div>
                    </div>
                    <div class="data-card">
                        <span class="metric-value">[[SAM_VALUE]]</span>
                        <div class="metric-label">[[SAM_DESCRIPTION]] <a href="#ref3" class="citation">[3]</a><a href="#ref1" class="citation">[1]</a><a href="#ref4" class="citation">[4]</a></div>
                    </div>
                    <div class="data-card">
                        <span class="metric-value">[[SOM_VALUE]]</span>
                        <div class="metric-label">[[SOM_DESCRIPTION]] <a href="#ref3" class="citation">[3]</a><a href="#ref4" class="citation">[4]</a></div>
                    </div>
                    <div class="data-card">
                        <span class="metric-value">[[PRICING_RANGE]]</span>
                        <div class="metric-label">[[PRICING_DESCRIPTION]] <a href="#ref1" class="citation">[1]</a><a href="#ref4" class="citation">[4]</a></div>
                    </div>
                </div>

                <h4>Strategic Implications for [[PRODUCT_NAME]]</h4>
                <p>[[STRATEGIC_IMPLICATIONS]] <a href="#ref6" class="citation">[6]</a><a href="#ref7" class="citation">[7]</a><a href="#ref8" class="citation">[8]</a></p>
            </div>

            <h3>1.1 Market Definition and Scope</h3>
            <div class="section-highlight">
                <p><strong>Product-market boundary:</strong> [[PRODUCT_MARKET_BOUNDARY]]</p>
                
                <p><strong>Inclusions:</strong> [[MARKET_INCLUSIONS]]</p>
                
                <p><strong>Exclusions:</strong> [[MARKET_EXCLUSIONS]]</p>
                
                <p><strong>Regulatory Context:</strong> [[REGULATORY_CONTEXT]] <a href="#ref6" class="citation">[6]</a><a href="#ref7" class="citation">[7]</a><a href="#ref8" class="citation">[8]</a><a href="#ref12" class="citation">[12]</a></p>
            </div>

            <h3>1.2 Key Market Size Metrics</h3>
            <div class="market-chart">
                <h4>Market Sizing Visualization ([[PROJECTION_YEAR]] Projections)</h4>
                <div class="chart-bar">
                    <div class="chart-label">TAM ([[TAM_REGION]])</div>
                    <div class="chart-track">
                        <div class="chart-fill tam-fill"></div>
                    </div>
                    <div class="chart-value">[[TAM_VALUE]]</div>
                </div>
                <div class="chart-bar">
                    <div class="chart-label">SAM ([[SAM_REGION]])</div>
                    <div class="chart-track">
                        <div class="chart-fill sam-fill"></div>
                    </div>
                    <div class="chart-value">[[SAM_VALUE]]</div>
                </div>
                <div class="chart-bar">
                    <div class="chart-label">SOM ([[SOM_REGION]])</div>
                    <div class="chart-track">
                        <div class="chart-fill som-fill"></div>
                    </div>
                    <div class="chart-value">[[SOM_VALUE]]</div>
                </div>
            </div>

            <div class="wide-content">
                <h4>TAM Analysis ([[TAM_ANALYSIS_PERIOD]])</h4>
                <p>[[TAM_ANALYSIS_DESCRIPTION]] <a href="#ref1" class="citation">[1]</a><a href="#ref2" class="citation">[2]</a><a href="#ref4" class="citation">[4]</a></p>
            </div>

            <h3>1.3 Major Findings and Insights Summary</h3>
            <div class="data-grid">
                <div class="data-card">
                    <div class="competitor-name">Key Insight</div>
                    <div class="competitor-focus">[[KEY_INSIGHT_1]] <a href="#ref2" class="citation">[2]</a><a href="#ref1" class="citation">[1]</a></div>
                </div>
                <div class="data-card">
                    <div class="competitor-name">[[LOCATION]] Advantage</div>
                    <div class="competitor-focus">[[LOCATION_ADVANTAGE]] <a href="#ref3" class="citation">[3]</a><a href="#ref1" class="citation">[1]</a></div>
                </div>
                <div class="data-card">
                    <div class="competitor-name">Regulatory Focus</div>
                    <div class="competitor-focus">[[REGULATORY_FOCUS]] <a href="#ref6" class="citation">[6]</a><a href="#ref7" class="citation">[7]</a><a href="#ref8" class="citation">[8]</a></div>
                </div>
                <div class="data-card">
                    <div class="competitor-name">Differentiation</div>
                    <div class="competitor-focus">[[DIFFERENTIATION]] <a href="#ref11" class="citation">[11]</a><a href="#ref10" class="citation">[10]</a></div>
                </div>
            </div>

            <div class="risk-warning">
                <h4>Strategic Opportunities & Threats</h4>
                <p><strong>Opportunities:</strong> [[STRATEGIC_OPPORTUNITIES]] <a href="#ref3" class="citation">[3]</a><a href="#ref7" class="citation">[7]</a></p>
                
                <p><strong>Threats:</strong> [[STRATEGIC_THREATS]] <a href="#ref6" class="citation">[6]</a><a href="#ref12" class="citation">[12]</a><a href="#ref1" class="citation">[1]</a></p>
            </div>
        </section>

        <!-- 
        MARKET OVERVIEW INSTRUCTIONS:
        
        1.  Provide an overview of the market growth and key characteristics
        2.  Define the industry classification and relevant segments
        3.  Describe product categories and use cases
        4.  List key market drivers and trends with appropriate citations
        -->
        <section id="market-overview">
            <h2>2. Market Overview</h2>
            
            <div class="section-highlight">
                <p>[[MARKET_OVERVIEW_SUMMARY]] <a href="#ref1" class="citation">[1]</a><a href="#ref2" class="citation">[2]</a><a href="#ref4" class="citation">[4]</a></p>
                
                <p>[[LOCATION_SPECIFIC_OVERVIEW]] <a href="#ref3" class="citation">[3]</a></p>
            </div>

            <h3>2.1 Industry Classification and Segments</h3>
            <p>[[INDUSTRY_CLASSIFICATION]] <a href="#ref6" class="citation">[6]</a><a href="#ref7" class="citation">[7]</a><a href="#ref8" class="citation">[8]</a><a href="#ref14" class="citation">[14]</a></p>

            <h3>2.2 Product Category Definitions and Use Cases</h3>
            <p>[[PRODUCT_CATEGORIES]] <a href="#ref11" class="citation">[11]</a><a href="#ref10" class="citation">[10]</a></p>

            <h3>2.3 Market Drivers and Trends</h3>
            <div class="key-insights">
                <ul>
                    <li>[[MARKET_DRIVER_1]] <a href="#ref2" class="citation">[2]</a></li>
                    <li>[[MARKET_DRIVER_2]] <a href="#ref1" class="citation">[1]</a></li>
                    <li>[[MARKET_DRIVER_3]] <a href="#ref3" class="citation">[3]</a></li>
                    <li>[[MARKET_DRIVER_4]] <a href="#ref6" class="citation">[6]</a></li>
                    <li>[[MARKET_DRIVER_5]] <a href="#ref15" class="citation">[15]</a></li>
                </ul>
            </div>
        </section>

        <!-- 
        MARKET SIZING INSTRUCTIONS:
        
        1.  Provide TAM, SAM, and SOM values with appropriate descriptions
        2.  Include a detailed regional breakdown table
        3.  Add historical and projected growth rates with citations
        -->
        <section id="market-sizing">
            <h2>3. Market Sizing</h2>
            
            <h3>3.1 Total Addressable Market (TAM)</h3>
            <div class="data-grid">
                <div class="data-card">
                    <span class="metric-value">[[TAM_VALUE_2]]</span>
                    <div class="metric-label">[[TAM_DESCRIPTION_2]] <a href="#ref1" class="citation">[1]</a><a href="#ref2" class="citation">[2]</a><a href="#ref4" class="citation">[4]</a></div>
                </div>
                <div class="data-card">
                    <span class="metric-value">[[TAM_REGIONAL_VALUE]]</span>
                    <div class="metric-label">[[TAM_REGIONAL_DESCRIPTION]] <a href="#ref3" class="citation">[3]</a><a href="#ref4" class="citation">[4]</a></div>
                </div>
            </div>

            <h3>3.2 Serviceable Available Market (SAM)</h3>
            <div class="wide-content">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Region</th>
                            <th>SAM Range (USD, [[SAM_YEAR]])</th>
                            <th>% of [[COUNTRY]] TAM</th>
                            <th>Key Characteristics</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>[[COUNTRY]] (Overall)</td>
                            <td>[[SAM_COUNTRY_VALUE]]</td>
                            <td>[[SAM_COUNTRY_PERCENT]]</td>
                            <td>[[SAM_COUNTRY_CHARACTERISTICS]] <a href="#ref2" class="citation">[2]</a><a href="#ref1" class="citation">[1]</a></td>
                        </tr>
                        <tr>
                            <td>[[REGION_1]]</td>
                            <td>[[SAM_REGION_1_VALUE]]</td>
                            <td>[[SAM_REGION_1_PERCENT]]</td>
                            <td>[[SAM_REGION_1_CHARACTERISTICS]] <a href="#ref3" class="citation">[3]</a></td>
                        </tr>
                        <tr>
                            <td>[[REGION_2]]</td>
                            <td>[[SAM_REGION_2_VALUE]]</td>
                            <td>[[SAM_REGION_2_PERCENT]]</td>
                            <td>[[SAM_REGION_2_CHARACTERISTICS]] <a href="#ref4" class="citation">[4]</a></td>
                        </tr>
                        <tr>
                            <td>[[REGION_3]]</td>
                            <td>[[SAM_REGION_3_VALUE]]</td>
                            <td>[[SAM_REGION_3_PERCENT]]</td>
                            <td>[[SAM_REGION_3_CHARACTERISTICS]] <a href="#ref4" class="citation">[4]</a></td>
                        </tr>
                        <tr>
                            <td>[[REGION_4]]</td>
                            <td>[[SAM_REGION_4_VALUE]]</td>
                            <td>[[SAM_REGION_4_PERCENT]]</td>
                            <td>[[SAM_REGION_4_CHARACTERISTICS]] <a href="#ref4" class="citation">[4]</a></td>
                        </tr>
                        <tr>
                            <td>[[REGION_5]]</td>
                            <td>[[SAM_REGION_5_VALUE]]</td>
                            <td>[[SAM_REGION_5_PERCENT]]</td>
                            <td>[[SAM_REGION_5_CHARACTERISTICS]] <a href="#ref1" class="citation">[1]</a></td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <h3>3.3 Serviceable Obtainable Market (SOM)</h3>
            <div class="section-highlight">
                <p><strong>[[PRIMARY_REGION]] SOM:</strong> [[PRIMARY_SOM_DESCRIPTION]]</p>
                <p><strong>[[SECONDARY_MARKET]] SOM:</strong> [[SECONDARY_SOM_DESCRIPTION]]</p>
                <p><strong>[[COUNTRY]] SOM:</strong> [[COUNTRY_SOM_DESCRIPTION]]</p>
                <p>[[SOM_CONTEXT]] <a href="#ref3" class="citation">[3]</a><a href="#ref4" class="citation">[4]</a></p>
            </div>

            <h3>3.4 Historical and Projected Growth Rates</h3>
            <p>[[GROWTH_RATE_ANALYSIS]] <a href="#ref1" class="citation">[1]</a><a href="#ref4" class="citation">[4]</a><a href="#ref11" class="citation">[11]</a></p>
        </section>

        <!-- 
        INDUSTRY ECOSYSTEM INSTRUCTIONS:
        
        1.  Describe the value chain and ecosystem map
        2.  List key players in the competitive landscape
        3.  Detail suppliers, partners, and distribution channels
        4.  Explain the regulatory environment and standards
        5.  Describe technology adoption and infrastructure
        -->
        <section id="industry-ecosystem">
            <h2>4. Industry Ecosystem</h2>
            
            <h3>4.1 Value Chain and Ecosystem Map</h3>
            <div class="section-highlight">
                <p>[[VALUE_CHAIN_DESCRIPTION]] <a href="#ref13" class="citation">[13]</a></p>
            </div>

            <h3>4.2 Key Players</h3>
            <div class="competitive-grid">
                <div class="competitor-card">
                    <div class="competitor-name">[[COMPETITOR_1]]</div>
                    <div class="competitor-focus">[[COMPETITOR_1_FOCUS]]</div>
                </div>
                <div class="competitor-card">
                    <div class="competitor-name">[[COMPETITOR_2]]</div>
                    <div class="competitor-focus">[[COMPETITOR_2_FOCUS]]</div>
                </div>
                <div class="competitor-card">
                    <div class="competitor-name">[[COMPETITOR_3]]</div>
                    <div class="competitor-focus">[[COMPETITOR_3_FOCUS]]</div>
                </div>
                <div class="competitor-card">
                    <div class="competitor-name">[[COMPETITOR_4]]</div>
                    <div class="competitor-focus">[[COMPETITOR_4_FOCUS]]</div>
                </div>
                <div class="competitor-card">
                    <div class="competitor-name">[[COMPETITOR_5]]</div>
                    <div class="competitor-focus">[[COMPETITOR_5_FOCUS]]</div>
                </div>
                <div class="competitor-card">
                    <div class="competitor-name">[[COMPETITOR_6]]</div>
                    <div class="competitor-focus">[[COMPETITOR_6_FOCUS]]</div>
                </div>
            </div>
            <p>[[FUNDING_ACTIVITY_COMMENTARY]] <a href="#ref10" class="citation">[10]</a><a href="#ref11" class="citation">[11]</a></p>

            <h3>4.3 Suppliers, Partners, and Distribution Channels</h3>
            <p>[[DISTRIBUTION_MODELS]] <a href="#ref12" class="citation">[12]</a></p>

            <h3>4.4 Regulatory Environment and Standards</h3>
            <div class="risk-warning">
                <h4>Key Regulatory Framework</h4>
                <ul>
                    <li><strong>[[REGULATION_1]]:</strong> [[REGULATION_1_DESCRIPTION]] <a href="#ref6" class="citation">[6]</a></li>
                    <li><strong>[[REGULATION_2]]:</strong> [[REGULATION_2_DESCRIPTION]] <a href="#ref7" class="citation">[7]</a></li>
                    <li><strong>[[REGULATION_3]]:</strong> [[REGULATION_3_DESCRIPTION]] <a href="#ref8" class="citation">[8]</a></li>
                    <li><strong>[[REGULATION_4]]:</strong> [[REGULATION_4_DESCRIPTION]] <a href="#ref14" class="citation">[14]</a></li>
                    <li><strong>[[REGULATION_5]]:</strong> [[REGULATION_5_DESCRIPTION]] <a href="#ref12" class="citation">[12]</a></li>
                </ul>
            </div>

            <h3>4.5 Technology Adoption and Infrastructure</h3>
            <p>[[TECHNOLOGY_ADOPTION]] <a href="#ref3" class="citation">[3]</a><a href="#ref1" class="citation">[1]</a></p>
        </section>

 <!-- 
    CUSTOMER BEHAVIOR & ADOPTION DYNAMICS INSTRUCTIONS:

    1. Provide insights for the following subsections:
       - Buying process and decision criteria across customer segments.
       - Adoption barriers with context-specific details.
       - Switching costs and loyalty factors, including retention dynamics.

    2. For "Buying Process & Decision Criteria" (5.1):
       - Populate the table with at least 4 customer segments.
       - For each segment, provide:
            [[CUSTOMER_SEGMENT_X]]
            [[DECISION_DRIVERS_X]]
            [[PROCUREMENT_CHANNEL_X]]
            [[DECISION_TIMELINE_X]]
       - Maintain the same column structure: Segment | Key Drivers | Procurement Channel | Timeline.

    3. After the table, provide a short summary paragraph:
       - Summarize how decision-making varies by segment and procurement channel.
       - Use placeholder: [[BUYING_PROCESS_SUMMARY]].

    4. For "Adoption Barriers" (5.2):
       - Provide a concise paragraph describing major barriers (cost, complexity, localization, logistics, trust).
       - Use placeholder: [[ADOPTION_BARRIERS_DESCRIPTION]].

    5. For "Switching Costs & Loyalty Factors" (5.3):
       - Describe the nature of switching costs (financial, operational, psychological).
       - Add insights about churn and retention based on benchmarks.
       - Use placeholder: [[SWITCHING_COSTS_AND_LOYALTY_FACTORS]].

    6. Keep all references intact and ensure placeholders are semantically meaningful.

-->
<section id="customer-behavior">
    <h2>5. Customer Behavior & Adoption Dynamics</h2>
    
    <h3>5.1 Buying Process & Decision Criteria</h3>
    <div class="wide-content">
        <table class="data-table">
            <thead>
                <tr>
                    <th>Customer Segment</th>
                    <th>Key Decision Drivers</th>
                    <th>Procurement Channel</th>
                    <th>Decision Timeline</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>[[CUSTOMER_SEGMENT_1]]</td>
                    <td>[[DECISION_DRIVERS_1]]</td>
                    <td>[[PROCUREMENT_CHANNEL_1]]</td>
                    <td>[[DECISION_TIMELINE_1]]</td>
                </tr>
                <tr>
                    <td>[[CUSTOMER_SEGMENT_2]]</td>
                    <td>[[DECISION_DRIVERS_2]]</td>
                    <td>[[PROCUREMENT_CHANNEL_2]]</td>
                    <td>[[DECISION_TIMELINE_2]]</td>
                </tr>
                <tr>
                    <td>[[CUSTOMER_SEGMENT_3]]</td>
                    <td>[[DECISION_DRIVERS_3]]</td>
                    <td>[[PROCUREMENT_CHANNEL_3]]</td>
                    <td>[[DECISION_TIMELINE_3]]</td>
                </tr>
                <tr>
                    <td>[[CUSTOMER_SEGMENT_4]]</td>
                    <td>[[DECISION_DRIVERS_4]]</td>
                    <td>[[PROCUREMENT_CHANNEL_4]]</td>
                    <td>[[DECISION_TIMELINE_4]]</td>
                </tr>
            </tbody>
        </table>
    </div>
    <p>[[BUYING_PROCESS_SUMMARY]] <a href="#ref11" class="citation">[11]</a></p>

    <h3>5.2 Adoption Barriers</h3>
    <div class="risk-warning">
        <p>[[ADOPTION_BARRIERS_DESCRIPTION]] <a href="#ref1" class="citation">[1]</a><a href="#ref6" class="citation">[6]</a></p>
    </div>

    <h3>5.3 Switching Costs & Loyalty Factors</h3>
    <p>[[SWITCHING_COSTS_AND_LOYALTY_FACTORS]] <a href="#ref10" class="citation">[10]</a></p>
</section>

<!--
    MARKET MATURITY & TRENDS INSTRUCTIONS:

    PURPOSE:
    Convert section content from a markdown report into structured HTML placeholders the AI agent can populate.
    Preserve layout and citations. Provide explicit, granular rules and examples so the agent fills data consistently.

    GENERAL RULES:
    - Keep original tags and classes intact (section, h2/h3, data-grid, key-insights, risk-warning, etc.).
    - Replace all report-specific facts/numbers with semantic placeholders in [[DOUBLE_BRACKETS]].
    - Keep citation anchors exactly as-is (e.g., <a href="#ref11" class="citation">[11]</a>).
    - When supplying numeric placeholders include units and a short source field (e.g., [[VALUE|UNIT|SOURCE_REF]]).
    - For every chart or metric card provide a companion placeholder for machine-readable data (JSON) and a short human summary.

    POPULATION GUIDELINES (examples + required fields):
    1) Market Lifecycle (6.1)
       - [[MARKET_LIFECYCLE_PHASE]] e.g., "growth"
       - [[INNOVATION_HUB_STATS]]: JSON with { city, startup_share_percent, funding_share_percent, year_range }.
         Example: {"city":"BEST PLACE","startup_share":"35%","funding_share":"40%","years":"2023-2024"}
       - [[GROWTH_PHASE_INDICATORS]]: array of bullets; each bullet object { metric, value, note, citation }.
         Example bullet: {"metric":"Market penetration","value":"12-15%","note":"urban professionals","citation":"#ref11"}

    2) Data Cards (metrics)
       - Provide up to 4 cards. Use:
         [[METRIC_1_VALUE|UNIT|SOURCE_REF]]
         [[METRIC_1_LABEL]]
         (repeat for METRIC_2...METRIC_4)
       - Also provide JSON: [[METRIC_CARDS_JSON]] e.g.,
         [{"label":"BEST PLACE share","value":"35%","source":"#ref11"}, ...]

    3) Technology Trends table (6.2)
       - Table rows: use placeholders for each row cell:
         [[TECHTREND_1_NAME]], [[TECHTREND_1_ADOPTION]], [[TECHTREND_1_KEY_PLAYERS]], [[TECHTREND_1_IMPACT]]
       - Provide full table JSON: [[TECH_TRENDS_TABLE_JSON]].

    4) Funding & Pedagogy paragraphs
       - Replace narrative with placeholders:
         [[FUNDING_TRENDS_PARAGRAPH]]
         [[PEDAGOGICAL_INNOVATION_PARAGRAPH]]
       - Each paragraph must be accompanied by 1–2 short data points as JSON: [[FUNDING_HIGHLIGHTS_JSON]].

    5) Market Maturity Chart (6.3)
       - Replace presentational div-bars with:
         - [[MARKET_MATURITY_CHART_TYPE]] e.g., "horizontal-bar"
         - [[MARKET_MATURITY_CHART_DATA_JSON]]: list of { metric, score (0-100), label }.
           Example:
           [{"metric":"Market Penetration","score":25,"label":"15% (Low)"},
            {"metric":"Growth Momentum","score":85,"label":"85% (High)"}]
       - Provide small human summary placeholder: [[MARKET_MATURITY_SUMMARY]].

    6) Growth Signals & Insights list
       - Each bullet convert to structured placeholder: [[GROWTH_SIGNAL_1_METRIC]], [[GROWTH_SIGNAL_1_NOTE]], [[GROWTH_SIGNAL_1_CITATION]].
       - Provide aggregated SWOT-like JSON: [[GROWTH_SIGNALS_JSON]].

    7) Disruptors & Response table (6.4)
       - Table rows: [[DISRUPTOR_1_NAME]], [[DISRUPTOR_1_TIMELINE]], [[DISRUPTOR_1_PROBABILITY]], [[DISRUPTOR_1_IMPACT]], [[DISRUPTOR_1_RESPONSE]]
       - Provide prioritized list JSON: [[DISRUPTORS_PRIORITY_JSON]] (probability × impact score).

    8) Market Evolution Drivers & Future Dynamics
       - Replace with structured placeholders:
         [[DATA_PRIVACY_DRIVER]], [[PRICING_MODEL_DRIVER]], [[LND_BUDGET_NOTE]]
       - Future dynamics: [[FUTURE_DYNAMICS_JSON]] with { phase, years, key_characteristics[] }.

    ACCESSIBILITY & RENDERING NOTES:
    - For visually rendered metrics: include aria-label attributes and alt text placeholders, e.g., aria-label="Market penetration: [[METRIC_1_VALUE]]".
    - Charts: agent should render from provided JSON using the site's charting module. Fallback: render simple accessible table if JS charting unavailable.
    - All numeric placeholders must include units and reference tags (e.g., "₹10,372 Cr | #ref15").

    VALIDATION RULES (agent must enforce):
    - Percent values: end with '%'. Currency values: include symbol and unit (₹ or $) and magnitude (Cr, B).
    - Dates/years: ISO-like when possible (2023-2024).
    - If a data point is an estimate, tag with [[ESTIMATE]] in the JSON.

    PRIORITY: preserve original citation anchors; do not invent new references.

-->

<section id="market-maturity">
    <h2>6. Market Maturity & Trends</h2>
    
    <h3>6.1 Market Lifecycle</h3>
    <div class="section-highlight">
        <p>The market is in <strong>[[MARKET_LIFECYCLE_PHASE]]</strong>. [[MARKET_LIFECYCLE_SUMMARY]] <a href="#ref11" class="citation">[11]</a><a href="#ref3" class="citation">[3]</a></p>
        
        <p><strong>Growth Phase Indicators:</strong></p>
        <ul>
            <li>Market penetration: [[GROWTH_INDICATOR_1_METRIC|UNIT]] — [[GROWTH_INDICATOR_1_NOTE]]</li>
            <li>Corporate adoption: [[GROWTH_INDICATOR_2_METRIC|UNIT]] — [[GROWTH_INDICATOR_2_NOTE]] <a href="#ref11" class="citation">[11]</a></li>
            <li>Government support: [[GROWTH_INDICATOR_3_METRIC|UNIT]] — [[GROWTH_INDICATOR_3_NOTE]] <a href="#ref15" class="citation">[15]</a></li>
            <li>Investment momentum: [[GROWTH_INDICATOR_4_METRIC|UNIT]] — [[GROWTH_INDICATOR_4_NOTE]] <a href="#ref10" class="citation">[10]</a></li>
        </ul>

        <!-- Machine-readable hub stats for charting/infobox -->
        <script type="application/json" id="hub-stats-json">
        [[INNOVATION_HUB_STATS_JSON]]
        </script>
    </div>

    <div class="data-grid">
        <div class="data-card" aria-label="Metric 1: [[METRIC_1_VALUE|UNIT]]">
            <span class="metric-value">[[METRIC_1_VALUE|UNIT|#ref]]</span>
            <div class="metric-label">[[METRIC_1_LABEL]]</div>
        </div>
        <div class="data-card" aria-label="Metric 2: [[METRIC_2_VALUE|UNIT]]">
            <span class="metric-value">[[METRIC_2_VALUE|UNIT|#ref]]</span>
            <div class="metric-label">[[METRIC_2_LABEL]]</div>
        </div>
        <div class="data-card" aria-label="Metric 3: [[METRIC_3_VALUE|UNIT]]">
            <span class="metric-value">[[METRIC_3_VALUE|UNIT|#ref]]</span>
            <div class="metric-label">[[METRIC_3_LABEL]]</div>
        </div>
        <div class="data-card" aria-label="Metric 4: [[METRIC_4_VALUE|UNIT]]">
            <span class="metric-value">[[METRIC_4_VALUE|UNIT|#ref]]</span>
            <div class="metric-label">[[METRIC_4_LABEL]]</div>
        </div>
    </div>

    <p>[[MARKET_POLICY_COMMENTARY]] <a href="#ref6" class="citation">[6]</a></p>

    <h3>6.2 Key Market Trends & Innovation Indicators</h3>
    
    <div class="key-insights">
        <h4>Technology Innovation Trends</h4>
        <p><strong>Patent Activity:</strong> [[PATENT_ACTIVITY_SUMMARY]] <a href="#ref2" class="citation">[2]</a></p>
        
        <div class="wide-content">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Technology Trend</th>
                        <th>Adoption Rate</th>
                        <th>Key Players</th>
                        <th>Impact on Product</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>[[TECHTREND_1_NAME]]</td>
                        <td>[[TECHTREND_1_ADOPTION]]</td>
                        <td>[[TECHTREND_1_KEY_PLAYERS]]</td>
                        <td>[[TECHTREND_1_IMPACT]]</td>
                    </tr>
                    <tr>
                        <td>[[TECHTREND_2_NAME]]</td>
                        <td>[[TECHTREND_2_ADOPTION]]</td>
                        <td>[[TECHTREND_2_KEY_PLAYERS]]</td>
                        <td>[[TECHTREND_2_IMPACT]]</td>
                    </tr>
                    <tr>
                        <td>[[TECHTREND_3_NAME]]</td>
                        <td>[[TECHTREND_3_ADOPTION]]</td>
                        <td>[[TECHTREND_3_KEY_PLAYERS]]</td>
                        <td>[[TECHTREND_3_IMPACT]]</td>
                    </tr>
                    <tr>
                        <td>[[TECHTREND_4_NAME]]</td>
                        <td>[[TECHTREND_4_ADOPTION]]</td>
                        <td>[[TECHTREND_4_KEY_PLAYERS]]</td>
                        <td>[[TECHTREND_4_IMPACT]]</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <h4>Funding and Investment Trends</h4>
        <p>[[FUNDING_TRENDS_PARAGRAPH]]</p>
        <ul>
            <li><strong>Series A/B Activity:</strong> [[FUNDING_POINT_1]] <a href="#ref11" class="citation">[11]</a></li>
            <li><strong>Corporate Training Focus:</strong> [[FUNDING_POINT_2]] <a href="#ref10" class="citation">[10]</a></li>
            <li><strong>Geographic Concentration:</strong> [[FUNDING_POINT_3]] <a href="#ref3" class="citation">[3]</a></li>
        </ul>
    </div>

    <div class="risk-warning">
        <h4>Pedagogical Innovation Trends</h4>
        <p><strong>Hybrid Learning Demand:</strong> [[HYBRID_LEARNING_STATEMENT]] <a href="#ref1" class="citation">[1]</a></p>
        
        <p><strong>Outcome-Based Learning:</strong> [[OUTCOME_BASED_LEARNING_NOTE]]</p>
    </div>

    <h3>6.3 Growth Rate and Saturation Analysis</h3>
    
    <div class="market-chart" role="img" aria-label="Market Maturity chart: [[MARKET_MATURITY_SUMMARY]]">
        <h4>Market Maturity Indicators (2024-2030)</h4>

        <!-- Chart engine should read MARKET_MATURITY_CHART_DATA_JSON and render bars.
             JSON schema: [{ "metric":"Market Penetration", "score":25, "label":"15% (Low)" }, ... ] -->
        <div class="chart-placeholder" data-chart='[[MARKET_MATURITY_CHART_DATA_JSON]]'>
            <!-- Fallback HTML bars for non-js environments: -->
            <div class="chart-bar">
                <div class="chart-label">[[FALLBACK_METRIC_1_LABEL]]</div>
                <div class="chart-track">
                    <div class="chart-fill" style="width: [[FALLBACK_METRIC_1_WIDTH]];"></div>
                </div>
                <div class="chart-value">[[FALLBACK_METRIC_1_VALUE]]</div>
            </div>
        </div>
    </div>

    <div class="key-insights">
        <p><strong>[[GROWTH_VS_SATURATION_HEADING]]</strong></p>
        <ul>
            <li>[[GROWTH_SIGNAL_1_METRIC]] — [[GROWTH_SIGNAL_1_NOTE]] <a href="#ref4" class="citation">[4]</a></li>
            <li>[[GROWTH_SIGNAL_2_METRIC]] — [[GROWTH_SIGNAL_2_NOTE]] <a href="#ref11" class="citation">[11]</a></li>
            <li>[[GROWTH_SIGNAL_3_METRIC]] — [[GROWTH_SIGNAL_3_NOTE]] <a href="#ref1" class="citation">[1]</a></li>
            <li>[[GROWTH_SIGNAL_4_METRIC]] — [[GROWTH_SIGNAL_4_NOTE]] <a href="#ref2" class="citation">[2]</a></li>
        </ul>
        
        <p><strong>Premium Segment Opportunity:</strong> [[PREMIUM_SEGMENT_OPPORTUNITY_ANALYSIS]]</p>
    </div>

    <h3>6.4 Potential Disruptors & Technology Trends</h3>
    
    <div class="risk-warning">
        <h4>Disruptive Technology Threats</h4>
        <div class="wide-content">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Disruptor</th>
                        <th>Timeline</th>
                        <th>Probability</th>
                        <th>Impact Level</th>
                        <th>Response Strategy</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>[[DISRUPTOR_1_NAME]]</td>
                        <td>[[DISRUPTOR_1_TIMELINE]]</td>
                        <td>[[DISRUPTOR_1_PROBABILITY]]</td>
                        <td>[[DISRUPTOR_1_IMPACT]]</td>
                        <td>[[DISRUPTOR_1_RESPONSE]]</td>
                    </tr>
                    <tr>
                        <td>[[DISRUPTOR_2_NAME]]</td>
                        <td>[[DISRUPTOR_2_TIMELINE]]</td>
                        <td>[[DISRUPTOR_2_PROBABILITY]]</td>
                        <td>[[DISRUPTOR_2_IMPACT]]</td>
                        <td>[[DISRUPTOR_2_RESPONSE]]</td>
                    </tr>
                    <tr>
                        <td>[[DISRUPTOR_3_NAME]]</td>
                        <td>[[DISRUPTOR_3_TIMELINE]]</td>
                        <td>[[DISRUPTOR_3_PROBABILITY]]</td>
                        <td>[[DISRUPTOR_3_IMPACT]]</td>
                        <td>[[DISRUPTOR_3_RESPONSE]]</td>
                    </tr>
                    <tr>
                        <td>[[DISRUPTOR_4_NAME]]</td>
                        <td>[[DISRUPTOR_4_TIMELINE]]</td>
                        <td>[[DISRUPTOR_4_PROBABILITY]]</td>
                        <td>[[DISRUPTOR_4_IMPACT]]</td>
                        <td>[[DISRUPTOR_4_RESPONSE]]</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <div class="section-highlight">
        <h4>Market Evolution Drivers</h4>
        <p><strong>Data Privacy:</strong> [[DATA_PRIVACY_DRIVER]] <a href="#ref6" class="citation">[6]</a></p>
        
        <p><strong>Pricing Model Innovation:</strong> [[PRICING_MODEL_DRIVER]] <a href="#ref2" class="citation">[2]</a></p>
        
        <p><strong>Corporate Learning Budget Allocation:</strong> [[LND_BUDGET_NOTE]]</p>
    </div>

    <div class="key-insights">
        <h4>Future Market Dynamics (2025-2030)</h4>
        <p>[[FUTURE_DYNAMICS_INTRO]]</p>
        <ul>
            <li><strong>Consolidation Phase (2026-2028):</strong> [[FUTURE_DYNAMICS_1]]</li>
            <li><strong>Premium Segment Growth:</strong> [[FUTURE_DYNAMICS_2]]</li>
            <li><strong>Regulatory Maturation:</strong> [[FUTURE_DYNAMICS_3]]</li>
            <li><strong>Technology Integration:</strong> [[FUTURE_DYNAMICS_4]]</li>
        </ul>
    </div>
</section>
<!--
    GEOGRAPHIC MARKET ANALYSIS INSTRUCTIONS:

    PURPOSE:
    Convert the markdown/HTML regional analysis into a reproducible template the AI agent can fill.
    Preserve layout, classes, and citation anchors. Provide explicit placeholders, JSON payload hooks,
    accessibility hints, and validation rules so the downstream renderer can produce charts/tables reliably.

    GENERAL RULES:
    - Keep all original tags, classes and citation anchors (do not invent new refs).
    - Replace factual values with semantic placeholders in [[DOUBLE_BRACKETS]].
    - Numeric placeholders must include units and a source tag: [[VALUE|UNIT|#ref]] (e.g., [[150-450M|$|#ref3]]).
    - For every visual (chart, cards, table) include a machine-readable JSON block with id attributes.
    - Provide fallback HTML for non-JS environments.
    - Use aria-label attributes for critical metrics and role="img" for charts.

    POPULATION GUIDELINES (examples + required fields):
    1) Section intro
       - [[GEOGRAPHIC_OVERVIEW_SUMMARY]] (short paragraph)
       - [[MAJOR_CLUSTER_SHARE]] e.g., "75%"

    2) Regional Market Attractiveness Chart (chart-bars)
       - Provide JSON for chart engine: id="regional-attractiveness-json"
         Schema: [{ "region":"BEST PLACE","score":90,"label":"High (9.0/10)","color":"#27ae60","citation":"#ref3" }, ...]
         Placeholder: [[REGIONAL_ATTRACTIVENESS_JSON]]
       - Fallback bars use: [[REGION_1_LABEL]], [[REGION_1_SCORE]], [[REGION_1_LABEL_TEXT]]

    3) Detailed Regional Table (SAM / SOM)
       - Table row placeholders:
         [[REGION_1_NAME]], [[REGION_1_SAM|UNIT|#ref]], [[REGION_1_SOM|UNIT|#ref]], [[REGION_1_KEY_INDUSTRIES]],
         [[REGION_1_PENETRATION|%|#ref]], [[REGION_1_UNIQUE_CHARACTERISTICS]]
       - Also include JSON: [[REGIONAL_TABLE_JSON]] (array of objects matching table columns).

    4) Regional Primary Market (BEST PLACE) insights & data-cards
       - Bullets replaced with structured placeholders:
         [[BEST PLACE_ECOSYSTEM_DENSITY|%|#ref]], [[BEST PLACE_CORPORATE_CONCENTRATION|count|#ref]],
         [[BEST PLACE_FUNDING|$|#ref]], [[BEST PLACE_TALENT_PIPELINE|count|#ref]], [[BEST PLACE_INNOVATION_NOTE]]
       - Machine JSON: [[BEST PLACE_METRICS_JSON]]

    5) Regional Competitors & Local Factors table
       - Row placeholders for each region:
         [[REGION_1_DOMINANT_PLAYERS]], [[REGION_1_MARKET_SHARE]], [[REGION_1_LOCAL_PREFERENCES]],
         [[REGION_1_CULTURAL_FACTORS]], [[REGION_1_MASTERAI_OPPORTUNITY]]
       - JSON: [[REGIONAL_COMPETITORS_JSON]]

    6) Tier-2 Opportunity & Data-cards
       - Placeholders: [[TIER2_YOY_GROWTH|%|#ref]], [[TIER2_SAM_POTENTIAL|$|#ref]], [[TIER2_TARGET_CITIES_COUNT]], [[TIER2_MARKETS_WITH_LIMITED_PREMIUM|%|#ref]]
       - JSON: [[TIER2_OPPORTUNITIES_JSON]]

    7) Geographic Risks & Operational Challenges
       - Structured placeholders for each risk area:
         [[RISK_LOGISTICS_DESCRIPTION]], [[RISK_SERVICE_SUPPORT_DESCRIPTION]], [[RISK_QUALITY_CONTROL_DESCRIPTION]],
         [[RISK_STATE_REGULATIONS_NOTE|#ref]], [[RISK_LOCAL_COMPLIANCE_NOTE]], [[RISK_IMPORT_DUTIES_NOTE|#ref]]
       - Localization placeholders:
         [[LOCALIZATION_LANGUAGES]] (list), [[LOCALIZATION_CULTURAL_CUSTOMIZATION_NOTE]], [[PRICING_DIFFERENTIAL_NOTE]]

    VALIDATION RULES (agent must enforce):
    - Percent values must end with '%'.
    - Currency ranges must include symbol and unit (e.g., $150-450M).
    - Counts use suffixes (K, M) or plain integers; include source ref.
    - Years when present must be explicit (e.g., 2030).
    - JSON blocks must be valid JSON. If value is estimated, include "estimate": true in JSON object.

    RENDERING NOTES:
    - Chart engine reads the JSON script tags with given ids and renders accessible SVG/Canvas.
    - Fallback: render the HTML bars using provided fallback placeholders.
    - Keep citation anchors inline with narrative.

    EXAMPLE JSON SCHEMAS (agent must provide these or similar):
    - Regional attractiveness:
      id="regional-attractiveness-json" -> [[REGIONAL_ATTRACTIVENESS_JSON]]
    - Regional table:
      id="regional-table-json" -> [[REGIONAL_TABLE_JSON]]
    - Tier-2 opportunities:
      id="tier2-opportunities-json" -> [[TIER2_OPPORTUNITIES_JSON]]

    PRIORITY: preserve original citation anchors; do not invent new refs.

-->

<section id="geographic-analysis">
    <h2>7. Geographic Market Analysis</h2>
    
    <h3>7.1 Regional Market Sizes & Key Differences</h3>
    
    <div class="section-highlight">
        <p>[[GEOGRAPHIC_OVERVIEW_SUMMARY]]</p>
    </div>

    <div class="market-chart" role="img" aria-label="Regional market attractiveness chart: [[MAJOR_CLUSTER_SHARE]] of activity concentrated in five clusters">
        <h4>Regional Market Attractiveness (2030)</h4>

        <!-- Chart JSON for the renderer (required) -->
        <script type="application/json" id="regional-attractiveness-json">
        [[REGIONAL_ATTRACTIVENESS_JSON]]
        </script>

        <!-- Fallback HTML bars (non-js) -->
        <div class="chart-bar">
            <div class="chart-label">[[REGION_1_LABEL]]</div>
            <div class="chart-track">
                <div class="chart-fill" style="width: [[REGION_1_FILL_WIDTH]];"></div>
            </div>
            <div class="chart-value">[[REGION_1_LABEL_TEXT]]</div>
        </div>
        <div class="chart-bar">
            <div class="chart-label">[[REGION_2_LABEL]]</div>
            <div class="chart-track">
                <div class="chart-fill" style="width: [[REGION_2_FILL_WIDTH]];"></div>
            </div>
            <div class="chart-value">[[REGION_2_LABEL_TEXT]]</div>
        </div>
        <div class="chart-bar">
            <div class="chart-label">[[REGION_3_LABEL]]</div>
            <div class="chart-track">
                <div class="chart-fill" style="width: [[REGION_3_FILL_WIDTH]];"></div>
            </div>
            <div class="chart-value">[[REGION_3_LABEL_TEXT]]</div>
        </div>
        <div class="chart-bar">
            <div class="chart-label">[[REGION_4_LABEL]]</div>
            <div class="chart-track">
                <div class="chart-fill" style="width: [[REGION_4_FILL_WIDTH]];"></div>
            </div>
            <div class="chart-value">[[REGION_4_LABEL_TEXT]]</div>
        </div>
        <div class="chart-bar">
            <div class="chart-label">[[REGION_5_LABEL]]</div>
            <div class="chart-track">
                <div class="chart-fill" style="width: [[REGION_5_FILL_WIDTH]];"></div>
            </div>
            <div class="chart-value">[[REGION_5_LABEL_TEXT]]</div>
        </div>
    </div>

    <div class="wide-content">
        <h4>Detailed Regional Analysis</h4>
        <table class="data-table" aria-describedby="regional-table-desc">
            <caption id="regional-table-desc">SAM and SOM estimates, key industries, penetration and unique characteristics by region for 2030.</caption>
            <thead>
                <tr>
                    <th>Region</th>
                    <th>SAM (2030)</th>
                    <th>SOM (2030)</th>
                    <th>Key Industries</th>
                    <th>EdTech Penetration</th>
                    <th>Unique Characteristics</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>[[REGION_1_NAME]]</strong></td>
                    <td>[[REGION_1_SAM|$|#ref]]</td>
                    <td>[[REGION_1_SOM|$|#ref]]</td>
                    <td>[[REGION_1_KEY_INDUSTRIES]]</td>
                    <td>[[REGION_1_PENETRATION|%|#ref]]</td>
                    <td>[[REGION_1_UNIQUE_CHARACTERISTICS]] <a href="#ref3" class="citation">[3]</a></td>
                </tr>
                <tr>
                    <td><strong>[[REGION_2_NAME]]</strong></td>
                    <td>[[REGION_2_SAM|$|#ref]]</td>
                    <td>[[REGION_2_SOM|$|#ref]]</td>
                    <td>[[REGION_2_KEY_INDUSTRIES]]</td>
                    <td>[[REGION_2_PENETRATION|%|#ref]]</td>
                    <td>[[REGION_2_UNIQUE_CHARACTERISTICS]] <a href="#ref4" class="citation">[4]</a></td>
                </tr>
                <tr>
                    <td><strong>[[REGION_3_NAME]]</strong></td>
                    <td>[[REGION_3_SAM|$|#ref]]</td>
                    <td>[[REGION_3_SOM|$|#ref]]</td>
                    <td>[[REGION_3_KEY_INDUSTRIES]]</td>
                    <td>[[REGION_3_PENETRATION|%|#ref]]</td>
                    <td>[[REGION_3_UNIQUE_CHARACTERISTICS]] <a href="#ref4" class="citation">[4]</a></td>
                </tr>
                <tr>
                    <td><strong>[[REGION_4_NAME]]</strong></td>
                    <td>[[REGION_4_SAM|$|#ref]]</td>
                    <td>[[REGION_4_SOM|$|#ref]]</td>
                    <td>[[REGION_4_KEY_INDUSTRIES]]</td>
                    <td>[[REGION_4_PENETRATION|%|#ref]]</td>
                    <td>[[REGION_4_UNIQUE_CHARACTERISTICS]]</td>
                </tr>
                <tr>
                    <td><strong>[[REGION_5_NAME]]</strong></td>
                    <td>[[REGION_5_SAM|$|#ref]]</td>
                    <td>[[REGION_5_SOM|$|#ref]]</td>
                    <td>[[REGION_5_KEY_INDUSTRIES]]</td>
                    <td>[[REGION_5_PENETRATION|%|#ref]]</td>
                    <td>[[REGION_5_UNIQUE_CHARACTERISTICS]]</td>
                </tr>
            </tbody>
        </table>

        <!-- Machine-readable regional table -->
        <script type="application/json" id="regional-table-json">
        [[REGIONAL_TABLE_JSON]]
        </script>
    </div>

    <div class="key-insights">
        <h4>[[PRIMARY_MARKET_HEADING]]</h4>
        <p><strong>Market Leadership Position:</strong> [[PRIMARY_MARKET_SUMMARY]]</p>
        <ul>
            <li><strong>Ecosystem Density:</strong> [[BEST PLACE_ECOSYSTEM_DENSITY|%|#ref]] <a href="#ref3" class="citation">[3]</a></li>
            <li><strong>Corporate Concentration:</strong> [[BEST PLACE_CORPORATE_CONCENTRATION|count|#ref]]</li>
            <li><strong>Funding Availability:</strong> [[BEST PLACE_FUNDING|$|#ref]] <a href="#ref11" class="citation">[11]</a></li>
            <li><strong>Talent Pipeline:</strong> [[BEST PLACE_TALENT_PIPELINE|count|#ref]]</li>
            <li><strong>Innovation Culture:</strong> [[BEST PLACE_INNOVATION_NOTE]]</li>
        </ul>
    </div>

    <div class="data-grid" aria-hidden="false">
        <div class="data-card" aria-label="IT services companies count: [[BEST PLACE_CORPORATE_CONCENTRATION|count|#ref]]">
            <span class="metric-value">[[BEST PLACE_CORPORATE_CONCENTRATION|count|#ref]]</span>
            <div class="metric-label">IT Services Companies<br>in [[REGION_1_NAME]]</div>
        </div>
        <div class="data-card" aria-label="EdTech funding: [[BEST PLACE_FUNDING|$|#ref]]">
            <span class="metric-value">[[BEST PLACE_FUNDING|$|#ref]]</span>
            <div class="metric-label">EdTech Funding<br>([[FUNDING_YEARS|#ref]])</div>
        </div>
        <div class="data-card" aria-label="IT professionals: [[BEST PLACE_TALENT_PIPELINE|count|#ref]]">
            <span class="metric-value">[[BEST PLACE_TALENT_PIPELINE|count|#ref]]</span>
            <div class="metric-label">IT Professionals<br>Target Audience</div>
        </div>
        <div class="data-card" aria-label="MNC R&D centers: [[BEST PLACE_RANDD_COUNT|count|#ref]]">
            <span class="metric-value">[[BEST PLACE_RANDD_COUNT|count|#ref]]</span>
            <div class="metric-label">MNC R&D Centers<br>Enterprise Targets</div>
        </div>
    </div>

    <h3>7.2 Regional Competitors & Local Factors</h3>

    <div class="section-highlight">
        <h4>Competitive Landscape by Region</h4>
        <p>[[REGIONAL_COMPETITIVE_LANDSCAPE_SUMMARY]]</p>
    </div>

    <div class="wide-content">
        <table class="data-table" aria-describedby="regional-competitors-desc">
            <caption id="regional-competitors-desc">Dominant players, market share, local preferences and Master AI opportunity by region.</caption>
            <thead>
                <tr>
                    <th>Region</th>
                    <th>Dominant Players</th>
                    <th>Market Share</th>
                    <th>Local Preferences</th>
                    <th>Cultural Factors</th>
                    <th>Master AI Opportunity</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>[[REGION_1_NAME]]</strong></td>
                    <td>[[REGION_1_DOMINANT_PLAYERS]]</td>
                    <td>[[REGION_1_MARKET_SHARE]]</td>
                    <td>[[REGION_1_LOCAL_PREFERENCES]]</td>
                    <td>[[REGION_1_CULTURAL_FACTORS]]</td>
                    <td>[[REGION_1_MASTERAI_OPPORTUNITY]] <a href="#ref10" class="citation">[10]</a></td>
                </tr>
                <tr>
                    <td><strong>[[REGION_2_NAME]]</strong></td>
                    <td>[[REGION_2_DOMINANT_PLAYERS]]</td>
                    <td>[[REGION_2_MARKET_SHARE]]</td>
                    <td>[[REGION_2_LOCAL_PREFERENCES]]</td>
                    <td>[[REGION_2_CULTURAL_FACTORS]]</td>
                    <td>[[REGION_2_MASTERAI_OPPORTUNITY]] <a href="#ref11" class="citation">[11]</a></td>
                </tr>
                <tr>
                    <td><strong>[[REGION_3_NAME]]</strong></td>
                    <td>[[REGION_3_DOMINANT_PLAYERS]]</td>
                    <td>[[REGION_3_MARKET_SHARE]]</td>
                    <td>[[REGION_3_LOCAL_PREFERENCES]]</td>
                    <td>[[REGION_3_CULTURAL_FACTORS]]</td>
                    <td>[[REGION_3_MASTERAI_OPPORTUNITY]]</td>
                </tr>
                <tr>
                    <td><strong>[[REGION_4_NAME]]</strong></td>
                    <td>[[REGION_4_DOMINANT_PLAYERS]]</td>
                    <td>[[REGION_4_MARKET_SHARE]]</td>
                    <td>[[REGION_4_LOCAL_PREFERENCES]]</td>
                    <td>[[REGION_4_CULTURAL_FACTORS]]</td>
                    <td>[[REGION_4_MASTERAI_OPPORTUNITY]]</td>
                </tr>
                <tr>
                    <td><strong>[[REGION_5_NAME]]</strong></td>
                    <td>[[REGION_5_DOMINANT_PLAYERS]]</td>
                    <td>[[REGION_5_MARKET_SHARE]]</td>
                    <td>[[REGION_5_LOCAL_PREFERENCES]]</td>
                    <td>[[REGION_5_CULTURAL_FACTORS]]</td>
                    <td>[[REGION_5_MASTERAI_OPPORTUNITY]] <a href="#ref1" class="citation">[1]</a></td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="risk-warning">
        <h4>Regional Competitive Threats</h4>
        <p><strong>Established Player Response:</strong> [[ESTABLISHED_PLAYER_RESPONSE_NOTE]]</p>
        <p><strong>Local Player Advantages:</strong> [[LOCAL_PLAYER_ADVANTAGES_NOTE]] <a href="#ref10" class="citation">[10]</a></p>
    </div>

    <h3>7.3 Geographic Opportunities & Challenges</h3>

    <div class="key-insights">
        <h4>Primary Market Opportunities</h4>
        
        <p><strong>[[PRIMARY_OPPORTUNITY_HEADING]]:</strong></p>
        <ul>
            <li><strong>Corporate Partnership Potential:</strong> [[CORPORATE_PARTNERSHIP_COUNT|count|#ref]] companies with L&D budgets >[[CORPORATE_LND_BUDGET_THRESHOLD|$|#ref]]</li>
            <li><strong>University Collaboration:</strong> [[UNIVERSITY_PARTNERS_LIST]]</li>
            <li><strong>Talent Ecosystem:</strong> [[TALENT_ECOSYSTEM_NOTE]]</li>
            <li><strong>Investor Network:</strong> [[INVESTOR_NETWORK_NOTE]]</li>
        </ul>

        <p><strong>Secondary Market Expansion Path:</strong></p>
        <ul>
            <li><strong>[[SECONDARY_MARKET_1_NAME]] (Year [[SECONDARY_MARKET_1_YEAR]]):</strong> [[SECONDARY_MARKET_1_NOTE]]</li>
            <li><strong>[[SECONDARY_MARKET_2_NAME]] (Year [[SECONDARY_MARKET_2_YEAR]]):</strong> [[SECONDARY_MARKET_2_NOTE]]</li>
            <li><strong>[[SECONDARY_MARKET_3_NAME]] (Year [[SECONDARY_MARKET_3_YEAR]]):</strong> [[SECONDARY_MARKET_3_NOTE]]</li>
            <li><strong>[[SECONDARY_MARKET_4_NAME]] (Year [[SECONDARY_MARKET_4_YEAR]]):</strong> [[SECONDARY_MARKET_4_NOTE]]</li>
        </ul>
    </div>

    <div class="section-highlight">
        <h4>Underserved Regional Markets</h4>
        <p>[[TIER2_OPPORTUNITY_SUMMARY]]</p>

        <div class="data-grid">
            <div class="data-card" aria-label="Tier-2 YoY growth: [[TIER2_YOY_GROWTH|%|#ref]]">
                <span class="metric-value">[[TIER2_YOY_GROWTH|%|#ref]]</span>
                <div class="metric-label">YoY Growth in Tier-2<br>Professional Development</div>
            </div>
            <div class="data-card" aria-label="Tier-2 SAM potential: [[TIER2_SAM_POTENTIAL|$|#ref]]">
                <span class="metric-value">[[TIER2_SAM_POTENTIAL|$|#ref]]</span>
                <div class="metric-label">Tier-2 Combined<br>SAM Potential</div>
            </div>
            <div class="data-card" aria-label="Target Tier-2 cities: [[TIER2_TARGET_CITIES_COUNT|count|#ref]]">
                <span class="metric-value">[[TIER2_TARGET_CITIES_COUNT|count|#ref]]</span>
                <div class="metric-label">Target Tier-2 Cities<br>for Expansion</div>
            </div>
            <div class="data-card" aria-label="Markets with limited premium EdTech: [[TIER2_MARKETS_WITH_LIMITED_PREMIUM|%|#ref]]">
                <span class="metric-value">[[TIER2_MARKETS_WITH_LIMITED_PREMIUM|%|#ref]]</span>
                <div class="metric-label">Markets with Limited<br>Premium EdTech</div>
            </div>
        </div>

        <!-- Tier-2 JSON -->
        <script type="application/json" id="tier2-opportunities-json">
        [[TIER2_OPPORTUNITIES_JSON]]
        </script>
    </div>

    <div class="risk-warning">
        <h4>Geographic Expansion Challenges</h4>
        
        <p><strong>Logistics and Infrastructure:</strong></p>
        <ul>
            <li><strong>Physical Kit Distribution:</strong> [[RISK_LOGISTICS_DESCRIPTION]]</li>
            <li><strong>Service Support:</strong> [[RISK_SERVICE_SUPPORT_DESCRIPTION]]</li>
            <li><strong>Quality Control:</strong> [[RISK_QUALITY_CONTROL_DESCRIPTION]]</li>
        </ul>

        <p><strong>Regulatory Variability:</strong></p>
        <ul>
            <li><strong>State-Level Regulations:</strong> [[RISK_STATE_REGULATIONS_NOTE]] <a href="#ref8" class="citation">[8]</a></li>
            <li><strong>Local Compliance:</strong> [[RISK_LOCAL_COMPLIANCE_NOTE]]</li>
            <li><strong>Import Duties:</strong> [[RISK_IMPORT_DUTIES_NOTE]] <a href="#ref12" class="citation">[12]</a></li>
        </ul>

        <p><strong>Localization Requirements:</strong></p>
        <ul>
            <li><strong>Language Adaptation:</strong> [[LOCALIZATION_LANGUAGES]]</li>
            <li><strong>Cultural Customization:</strong> [[LOCALIZATION_CULTURAL_CUSTOMIZATION_NOTE]]</li>
            <li><strong>Pricing Sensitivity:</strong> [[PRICING_DIFFERENTIAL_NOTE]]</li>
        </ul>
    </div>
</section>
<!-- RISK ANALYSIS INSTRUCTIONS:
1. Provide comprehensive risk assessment overview with balanced risk profile description
2. Create detailed risk matrix with 15+ risk factors across operational, market, and external categories
3. Build visual risk matrix plotting probability vs impact with color-coded risk zones
4. Detail operational risks including supply chain, manufacturing, technology, and infrastructure
5. Analyze market risks covering competitive threats, customer acquisition challenges, and market dynamics  
6. Address external/regulatory risks with specific compliance requirements and financial impacts
7. Include detailed mitigation strategies for each major risk category
8. Provide risk scoring methodology (Probability × Impact × 10)
9. Use data cards, tables, and visual elements to present quantitative risk assessments
10. Include timeline projections and financial impact estimates for all major risks -->

<section id="risk-analysis">
    <h2>8. Risk Analysis</h2>
    
    <div class="section-highlight">
        <p>[[RISK_OVERVIEW_DESCRIPTION]]</p>
    </div>

    <h3>8.1 Comprehensive Risk Matrix</h3>
    
    <div class="section-highlight">
        <h4>Risk Assessment Methodology</h4>
        <p>[[RISK_METHODOLOGY_DESCRIPTION]]</p>
    </div>

    <div class="wide-content">
        <h4>Visual Risk Matrix: Probability vs Impact Analysis</h4>
        <div style="position: relative; width: 100%; height: 500px; background: linear-gradient(45deg, #e8f5e8 0%, #fff3cd 50%, #f8d7da 100%); border: 2px solid #dee2e6; border-radius: 8px; margin: 25px 0;">
            
            <!-- Risk Matrix Grid -->
            <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border-radius: 8px;">
                <!-- Grid Lines -->
                <div style="position: absolute; top: 20%; left: 0; width: 100%; height: 1px; background: #adb5bd; opacity: 0.5;"></div>
                <div style="position: absolute; top: 40%; left: 0; width: 100%; height: 1px; background: #adb5bd; opacity: 0.5;"></div>
                <div style="position: absolute; top: 60%; left: 0; width: 100%; height: 1px; background: #adb5bd; opacity: 0.5;"></div>
                <div style="position: absolute; top: 80%; left: 0; width: 100%; height: 1px; background: #adb5bd; opacity: 0.5;"></div>
                
                <div style="position: absolute; top: 0; left: 20%; width: 1px; height: 100%; background: #adb5bd; opacity: 0.5;"></div>
                <div style="position: absolute; top: 0; left: 40%; width: 1px; height: 100%; background: #adb5bd; opacity: 0.5;"></div>
                <div style="position: absolute; top: 0; left: 60%; width: 1px; height: 100%; background: #adb5bd; opacity: 0.5;"></div>
                <div style="position: absolute; top: 0; left: 80%; width: 1px; height: 100%; background: #adb5bd; opacity: 0.5;"></div>
            </div>
            
            <!-- Axis Labels -->
            <div style="position: absolute; bottom: -30px; left: 50%; transform: translateX(-50%); font-weight: bold; color: #495057;">
                Probability of Occurrence →
            </div>
            <div style="position: absolute; top: 50%; left: -40px; transform: translateY(-50%) rotate(-90deg); font-weight: bold; color: #495057;">
                Business Impact →
            </div>
            
            <!-- Risk Zone Labels -->
            <div style="position: absolute; top: 10px; left: 10px; background: rgba(40, 167, 69, 0.8); color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: bold;">
                LOW RISK
            </div>
            <div style="position: absolute; top: 10px; right: 100px; background: rgba(255, 193, 7, 0.8); color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: bold;">
                MEDIUM RISK
            </div>
            <div style="position: absolute; top: 10px; right: 10px; background: rgba(220, 53, 69, 0.8); color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: bold;">
                HIGH RISK
            </div>
            
            <!-- Risk Items as Positioned Dots - CUSTOMIZE POSITIONS BASED ON YOUR SPECIFIC RISKS -->
            <!-- Critical Risk Example -->
            <div style="position: absolute; top: [[CRITICAL_RISK_Y]]%; left: [[CRITICAL_RISK_X]]%; width: 12px; height: 12px; background: #dc3545; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);" title="[[CRITICAL_RISK_NAME]]"></div>
            
            <!-- High Impact, Medium Probability Examples -->
            <div style="position: absolute; top: [[HIGH_RISK_1_Y]]%; left: [[HIGH_RISK_1_X]]%; width: 12px; height: 12px; background: #fd7e14; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);" title="[[HIGH_RISK_1_NAME]]"></div>
            <div style="position: absolute; top: [[HIGH_RISK_2_Y]]%; left: [[HIGH_RISK_2_X]]%; width: 12px; height: 12px; background: #fd7e14; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);" title="[[HIGH_RISK_2_NAME]]"></div>
            
            <!-- Medium Risks -->
            <div style="position: absolute; top: [[MEDIUM_RISK_1_Y]]%; left: [[MEDIUM_RISK_1_X]]%; width: 12px; height: 12px; background: #ffc107; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);" title="[[MEDIUM_RISK_1_NAME]]"></div>
            <div style="position: absolute; top: [[MEDIUM_RISK_2_Y]]%; left: [[MEDIUM_RISK_2_X]]%; width: 12px; height: 12px; background: #17a2b8; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);" title="[[MEDIUM_RISK_2_NAME]]"></div>
            <div style="position: absolute; top: [[MEDIUM_RISK_3_Y]]%; left: [[MEDIUM_RISK_3_X]]%; width: 12px; height: 12px; background: #17a2b8; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);" title="[[MEDIUM_RISK_3_NAME]]"></div>
            
            <!-- Low Risks -->
            <div style="position: absolute; top: [[LOW_RISK_1_Y]]%; left: [[LOW_RISK_1_X]]%; width: 12px; height: 12px; background: #28a745; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);" title="[[LOW_RISK_1_NAME]]"></div>
            <div style="position: absolute; top: [[LOW_RISK_2_Y]]%; left: [[LOW_RISK_2_X]]%; width: 12px; height: 12px; background: #28a745; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);" title="[[LOW_RISK_2_NAME]]"></div>
            
            <!-- Black Swan Events -->
            <div style="position: absolute; top: [[BLACK_SWAN_1_Y]]%; left: [[BLACK_SWAN_1_X]]%; width: 12px; height: 12px; background: #6f42c1; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);" title="[[BLACK_SWAN_1_NAME]]"></div>
            <div style="position: absolute; top: [[BLACK_SWAN_2_Y]]%; left: [[BLACK_SWAN_2_X]]%; width: 12px; height: 12px; background: #6f42c1; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);" title="[[BLACK_SWAN_2_NAME]]"></div>
            
        </div>
        
        <!-- Legend -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 30px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 16px; height: 16px; background: #dc3545; border-radius: 50%; border: 2px solid white;"></div>
                <span style="font-size: 14px;"><strong>Critical Risk:</strong> Immediate attention required</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 16px; height: 16px; background: #fd7e14; border-radius: 50%; border: 2px solid white;"></div>
                <span style="font-size: 14px;"><strong>High Risk:</strong> Active monitoring & mitigation</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 16px; height: 16px; background: #ffc107; border-radius: 50%; border: 2px solid white;"></div>
                <span style="font-size: 14px;"><strong>Medium Risk:</strong> Regular review & planning</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 16px; height: 16px; background: #17a2b8; border-radius: 50%; border: 2px solid white;"></div>
                <span style="font-size: 14px;"><strong>Moderate Risk:</strong> Periodic assessment</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 16px; height: 16px; background: #28a745; border-radius: 50%; border: 2px solid white;"></div>
                <span style="font-size: 14px;"><strong>Low Risk:</strong> Standard monitoring</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 16px; height: 16px; background: #6f42c1; border-radius: 50%; border: 2px solid white;"></div>
                <span style="font-size: 14px;"><strong>Black Swan:</strong> Low probability, high impact</span>
            </div>
        </div>
    </div>
    
    <div class="risk-cards" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 30px;">

<!-- Critical Risk -->
<div style="border: 1px solid #dee2e6; border-radius: 10px; background: #fff; padding: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.05);">
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
        <div style="width: 16px; height: 16px; background: #dc3545; border-radius: 50%;"></div>
        <h5 style="margin: 0; font-size: 16px; color: #dc3545;">[[CRITICAL_RISK_NAME]]</h5>
    </div>
    <p style="font-size: 14px; color: #495057;">[[CRITICAL_RISK_DESCRIPTION]]</p>
    <p style="font-size: 13px; color: #6c757d;"><strong>Action:</strong> [[CRITICAL_RISK_ACTION]]</p>
</div>

<!-- High Risks -->
<div style="border: 1px solid #dee2e6; border-radius: 10px; background: #fff; padding: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.05);">
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
        <div style="width: 16px; height: 16px; background: #fd7e14; border-radius: 50%;"></div>
        <h5 style="margin: 0; font-size: 16px; color: #fd7e14;">[[HIGH_RISK_1_NAME]]</h5>
    </div>
    <p style="font-size: 14px; color: #495057;">[[HIGH_RISK_1_DESCRIPTION]]</p>
    <p style="font-size: 13px; color: #6c757d;"><strong>Action:</strong> [[HIGH_RISK_1_ACTION]]</p>
</div>

<div style="border: 1px solid #dee2e6; border-radius: 10px; background: #fff; padding: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.05);">
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
        <div style="width: 16px; height: 16px; background: #fd7e14; border-radius: 50%;"></div>
        <h5 style="margin: 0; font-size: 16px; color: #fd7e14;">[[HIGH_RISK_2_NAME]]</h5>
    </div>
    <p style="font-size: 14px; color: #495057;">[[HIGH_RISK_2_DESCRIPTION]]</p>
    <p style="font-size: 13px; color: #6c757d;"><strong>Action:</strong> [[HIGH_RISK_2_ACTION]]</p>
</div>

<!-- Medium Risks -->
<div style="border: 1px solid #dee2e6; border-radius: 10px; background: #fff; padding: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.05);">
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
        <div style="width: 16px; height: 16px; background: #ffc107; border-radius: 50%;"></div>
        <h5 style="margin: 0; font-size: 16px; color: #ffc107;">[[MEDIUM_RISK_1_NAME]]</h5>
    </div>
    <p style="font-size: 14px; color: #495057;">[[MEDIUM_RISK_1_DESCRIPTION]]</p>
    <p style="font-size: 13px; color: #6c757d;"><strong>Action:</strong> [[MEDIUM_RISK_1_ACTION]]</p>
</div>

<!-- Additional risk cards can be added following the same pattern -->

</div>

    <div class="wide-content">
        <h4>Detailed Risk Assessment Matrix</h4>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Risk Category</th>
                    <th>Specific Risk</th>
                    <th>Probability</th>
                    <th>Impact</th>
                    <th>Risk Score</th>
                    <th>Timeline</th>
                    <th>Financial Impact</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td rowspan="3"><strong>Operational</strong></td>
                    <td>[[OPERATIONAL_RISK_1]]</td>
                    <td>[[OPERATIONAL_RISK_1_PROBABILITY]]</td>
                    <td>[[OPERATIONAL_RISK_1_IMPACT]]</td>
                    <td>[[OPERATIONAL_RISK_1_SCORE]]</td>
                    <td>[[OPERATIONAL_RISK_1_TIMELINE]]</td>
                    <td>[[OPERATIONAL_RISK_1_FINANCIAL]]</td>
                </tr>
                <tr>
                    <td>[[OPERATIONAL_RISK_2]]</td>
                    <td>[[OPERATIONAL_RISK_2_PROBABILITY]]</td>
                    <td>[[OPERATIONAL_RISK_2_IMPACT]]</td>
                    <td>[[OPERATIONAL_RISK_2_SCORE]]</td>
                    <td>[[OPERATIONAL_RISK_2_TIMELINE]]</td>
                    <td>[[OPERATIONAL_RISK_2_FINANCIAL]]</td>
                </tr>
                <tr>
                    <td>[[OPERATIONAL_RISK_3]]</td>
                    <td>[[OPERATIONAL_RISK_3_PROBABILITY]]</td>
                    <td>[[OPERATIONAL_RISK_3_IMPACT]]</td>
                    <td>[[OPERATIONAL_RISK_3_SCORE]]</td>
                    <td>[[OPERATIONAL_RISK_3_TIMELINE]]</td>
                    <td>[[OPERATIONAL_RISK_3_FINANCIAL]]</td>
                </tr>
                <tr>
                    <td rowspan="3"><strong>Market</strong></td>
                    <td>[[MARKET_RISK_1]]</td>
                    <td>[[MARKET_RISK_1_PROBABILITY]]</td>
                    <td>[[MARKET_RISK_1_IMPACT]]</td>
                    <td>[[MARKET_RISK_1_SCORE]]</td>
                    <td>[[MARKET_RISK_1_TIMELINE]]</td>
                    <td>[[MARKET_RISK_1_FINANCIAL]]</td>
                </tr>
                <tr>
                    <td>[[MARKET_RISK_2]]</td>
                    <td>[[MARKET_RISK_2_PROBABILITY]]</td>
                    <td>[[MARKET_RISK_2_IMPACT]]</td>
                    <td>[[MARKET_RISK_2_SCORE]]</td>
                    <td>[[MARKET_RISK_2_TIMELINE]]</td>
                    <td>[[MARKET_RISK_2_FINANCIAL]]</td>
                </tr>
                <tr>
                    <td>[[MARKET_RISK_3]]</td>
                    <td>[[MARKET_RISK_3_PROBABILITY]]</td>
                    <td>[[MARKET_RISK_3_IMPACT]]</td>
                    <td>[[MARKET_RISK_3_SCORE]]</td>
                    <td>[[MARKET_RISK_3_TIMELINE]]</td>
                    <td>[[MARKET_RISK_3_FINANCIAL]]</td>
                </tr>
                <tr>
                    <td rowspan="3"><strong>External</strong></td>
                    <td>[[EXTERNAL_RISK_1]]</td>
                    <td>[[EXTERNAL_RISK_1_PROBABILITY]]</td>
                    <td>[[EXTERNAL_RISK_1_IMPACT]]</td>
                    <td>[[EXTERNAL_RISK_1_SCORE]]</td>
                    <td>[[EXTERNAL_RISK_1_TIMELINE]]</td>
                    <td>[[EXTERNAL_RISK_1_FINANCIAL]]</td>
                </tr>
                <tr>
                    <td>[[EXTERNAL_RISK_2]]</td>
                    <td>[[EXTERNAL_RISK_2_PROBABILITY]]</td>
                    <td>[[EXTERNAL_RISK_2_IMPACT]]</td>
                    <td>[[EXTERNAL_RISK_2_SCORE]]</td>
                    <td>[[EXTERNAL_RISK_2_TIMELINE]]</td>
                    <td>[[EXTERNAL_RISK_2_FINANCIAL]]</td>
                </tr>
                <tr>
                    <td>[[EXTERNAL_RISK_3]]</td>
                    <td>[[EXTERNAL_RISK_3_PROBABILITY]]</td>
                    <td>[[EXTERNAL_RISK_3_IMPACT]]</td>
                    <td>[[EXTERNAL_RISK_3_SCORE]]</td>
                    <td>[[EXTERNAL_RISK_3_TIMELINE]]</td>
                    <td>[[EXTERNAL_RISK_3_FINANCIAL]]</td>
                </tr>
            </tbody>
        </table>
    </div>

    <h3>8.2 Operational Risks</h3>
    
    <div class="risk-warning">
        <h4>Supply Chain and Manufacturing Risks</h4>
        
        <p><strong>Primary Risk: [[PRIMARY_OPERATIONAL_RISK_NAME]]</strong></p>
        <p>[[PRIMARY_OPERATIONAL_RISK_DESCRIPTION]] <a href="#ref12" class="citation">[12]</a></p>
        
        <div class="data-grid">
            <div class="data-card">
                <span class="metric-value">[[SUPPLY_CHAIN_PROBABILITY]]%</span>
                <div class="metric-label">Probability of Supply<br>Chain Disruption</div>
            </div>
            <div class="data-card">
                <span class="metric-value">[[RECOVERY_TIMELINE]]</span>
                <div class="metric-label">Recovery Timeline<br>for Major Disruption</div>
            </div>
            <div class="data-card">
                <span class="metric-value">[[REVENUE_LOSS_RANGE]]</span>
                <div class="metric-label">Potential Revenue<br>Loss per Incident</div>
            </div>
            <div class="data-card">
                <span class="metric-value">[[SUPPLIER_COUNT]]</span>
                <div class="metric-label">Alternative Suppliers<br>Required for Resilience</div>
            </div>
        </div>

        <p><strong>Detailed Risk Factors:</strong></p>
        <ul>
            <li><strong>[[RISK_FACTOR_1_NAME]]:</strong> [[RISK_FACTOR_1_DESCRIPTION]]</li>
            <li><strong>[[RISK_FACTOR_2_NAME]]:</strong> [[RISK_FACTOR_2_DESCRIPTION]]</li>
            <li><strong>[[RISK_FACTOR_3_NAME]]:</strong> [[RISK_FACTOR_3_DESCRIPTION]]</li>
            <li><strong>[[RISK_FACTOR_4_NAME]]:</strong> [[RISK_FACTOR_4_DESCRIPTION]]</li>
        </ul>

        <p><strong>Mitigation Strategies:</strong></p>
        <ul>
            <li><strong>[[MITIGATION_1_NAME]]:</strong> [[MITIGATION_1_DESCRIPTION]]</li>
            <li><strong>[[MITIGATION_2_NAME]]:</strong> [[MITIGATION_2_DESCRIPTION]]</li>
            <li><strong>[[MITIGATION_3_NAME]]:</strong> [[MITIGATION_3_DESCRIPTION]]</li>
            <li><strong>[[MITIGATION_4_NAME]]:</strong> [[MITIGATION_4_DESCRIPTION]]</li>
            <li><strong>[[MITIGATION_5_NAME]]:</strong> [[MITIGATION_5_DESCRIPTION]]</li>
        </ul>
    </div>

    <div class="key-insights">
        <h4>Technology and Infrastructure Risks</h4>
        
        <p><strong>Digital Platform Dependencies:</strong></p>
        <ul>
            <li><strong>[[TECH_RISK_1_NAME]]:</strong> [[TECH_RISK_1_DESCRIPTION]]</li>
            <li><strong>[[TECH_RISK_2_NAME]]:</strong> [[TECH_RISK_2_DESCRIPTION]]</li>
            <li><strong>[[TECH_RISK_3_NAME]]:</strong> [[TECH_RISK_3_DESCRIPTION]]</li>
        </ul>

        <p><strong>Support Infrastructure Risks:</strong></p>
        <ul>
            <li><strong>[[SUPPORT_RISK_1_NAME]]:</strong> [[SUPPORT_RISK_1_DESCRIPTION]]</li>
            <li><strong>[[SUPPORT_RISK_2_NAME]]:</strong> [[SUPPORT_RISK_2_DESCRIPTION]]</li>
            <li><strong>[[SUPPORT_RISK_3_NAME]]:</strong> [[SUPPORT_RISK_3_DESCRIPTION]]</li>
        </ul>
    </div>

    <h3>8.3 Market Risks</h3>

    <div class="section-highlight">
        <h4>Competitive Response Risks</h4>
        
        <p><strong>High Probability Competitive Threats:</strong></p>
        <p>[[COMPETITIVE_THREAT_DESCRIPTION]] <a href="#ref10" class="citation">[10]</a></p>

        <div class="wide-content">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Competitor</th>
                        <th>Response Probability</th>
                        <th>Response Timeline</th>
                        <th>Likely Strategy</th>
                        <th>Threat Level</th>
                        <th>Counter-Strategy</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>[[COMPETITOR_1]]</td>
                        <td>[[COMPETITOR_1_PROBABILITY]]</td>
                        <td>[[COMPETITOR_1_TIMELINE]]</td>
                        <td>[[COMPETITOR_1_STRATEGY]]</td>
                        <td>[[COMPETITOR_1_THREAT_LEVEL]]</td>
                        <td>[[COMPETITOR_1_COUNTER_STRATEGY]]</td>
                    </tr>
                    <tr>
                        <td>[[COMPETITOR_2]]</td>
                        <td>[[COMPETITOR_2_PROBABILITY]]</td>
                        <td>[[COMPETITOR_2_TIMELINE]]</td>
                        <td>[[COMPETITOR_2_STRATEGY]]</td>
                        <td>[[COMPETITOR_2_THREAT_LEVEL]]</td>
                        <td>[[COMPETITOR_2_COUNTER_STRATEGY]]</td>
                    </tr>
                    <tr>
                        <td>[[COMPETITOR_3]]</td>
                        <td>[[COMPETITOR_3_PROBABILITY]]</td>
                        <td>[[COMPETITOR_3_TIMELINE]]</td>
                        <td>[[COMPETITOR_3_STRATEGY]]</td>
                        <td>[[COMPETITOR_3_THREAT_LEVEL]]</td>
                        <td>[[COMPETITOR_3_COUNTER_STRATEGY]]</td>
                    </tr>
                    <tr>
                        <td>[[COMPETITOR_4]]</td>
                        <td>[[COMPETITOR_4_PROBABILITY]]</td>
                        <td>[[COMPETITOR_4_TIMELINE]]</td>
                        <td>[[COMPETITOR_4_STRATEGY]]</td>
                        <td>[[COMPETITOR_4_THREAT_LEVEL]]</td>
                        <td>[[COMPETITOR_4_COUNTER_STRATEGY]]</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <div class="risk-warning">
        <h4>Customer Acquisition and Retention Risks</h4>
        
        <p><strong>CAC Inflation Risk:</strong> [[CAC_INFLATION_DESCRIPTION]] <a href="#ref1" class="citation">[1]</a></p>

        <p><strong>Market Saturation Risk:</strong> [[MARKET_SATURATION_DESCRIPTION]]</p>

        <p><strong>Churn Risk Factors:</strong></p>
        <ul>
            <li><strong>[[CHURN_FACTOR_1_NAME]]:</strong> [[CHURN_FACTOR_1_DESCRIPTION]]</li>
            <li><strong>[[CHURN_FACTOR_2_NAME]]:</strong> [[CHURN_FACTOR_2_DESCRIPTION]]</li>
            <li><strong>[[CHURN_FACTOR_3_NAME]]:</strong> [[CHURN_FACTOR_3_DESCRIPTION]]</li>
        </ul>
    </div>

    <h3>8.4 External and Regulatory Risks</h3>

    <div class="risk-warning">
        <h4>Regulatory Compliance Risks (High Priority)</h4>
        
        <p><strong>[[PRIMARY_REGULATORY_RISK_NAME]] ([[PRIMARY_REGULATORY_PROBABILITY]]% probability of increased costs):</strong></p>
        <p>[[PRIMARY_REGULATORY_DESCRIPTION]] <a href="#ref6" class="citation">[6]</a></p>

        <div class="data-grid">
            <div class="data-card">
                <span class="metric-value">[[MAX_PENALTY]]</span>
                <div class="metric-label">Maximum [[REGULATORY_ACT_ABBREVIATION]]<br>Penalty Exposure</div>
            </div>
            <div class="data-card">
                <span class="metric-value">[[ANNUAL_COMPLIANCE_COST]]</span>
                <div class="metric-label">Annual Compliance<br>Cost Estimate</div>
            </div>
            <div class="data-card">
                <span class="metric-value">[[IMPLEMENTATION_TIMELINE]]</span>
                <div class="metric-label">Implementation<br>Timeline</div>
            </div>
            <div class="data-card">
                <span class="metric-value">[[COST_IMPACT_PROBABILITY]]%</span>
                <div class="metric-label">Probability of Cost<br>Impact</div>
            </div>
        </div>

        <p><strong>Key Compliance Requirements:</strong></p>
        <ul>
            <li><strong>[[COMPLIANCE_REQ_1]]:</strong> [[COMPLIANCE_REQ_1_DESCRIPTION]]</li>
            <li><strong>[[COMPLIANCE_REQ_2]]:</strong> [[COMPLIANCE_REQ_2_DESCRIPTION]]</li>
            <li><strong>[[COMPLIANCE_REQ_3]]:</strong> [[COMPLIANCE_REQ_3_DESCRIPTION]]</li>
            <li><strong>[[COMPLIANCE_REQ_4]]:</strong> [[COMPLIANCE_REQ_4_DESCRIPTION]]</li>
            <li><strong>[[COMPLIANCE_REQ_5]]:</strong> [[COMPLIANCE_REQ_5_DESCRIPTION]]</li>
        </ul>

        <p><strong>Mitigation Strategy:</strong></p>
        <ul>
            <li><strong>[[REGULATORY_MITIGATION_1]]:</strong> [[REGULATORY_MITIGATION_1_DESCRIPTION]]</li>
            <li><strong>[[REGULATORY_MITIGATION_2]]:</strong> [[REGULATORY_MITIGATION_2_DESCRIPTION]]</li>
            <li><strong>[[REGULATORY_MITIGATION_3]]:</strong> [[REGULATORY_MITIGATION_3_DESCRIPTION]]</li>
            <li><strong>[[REGULATORY_MITIGATION_4]]:</strong> [[REGULATORY_MITIGATION_4_DESCRIPTION]]</li>
        </ul>
    </div>

    <div class="section-highlight">
        <h4>Import and Trade Risks</h4>
        
        <p><strong>Import Duty Volatility ([[IMPORT_DUTY_PROBABILITY]]% probability of changes):</strong></p>
        <p>[[IMPORT_DUTY_DESCRIPTION]] <a href="#ref12" class="citation">[12]</a></p>

        <p><strong>Trade Policy Risks:</strong></p>
        <ul>
            <li><strong>[[TRADE_RISK_1]]:</strong> [[TRADE_RISK_1_DESCRIPTION]]</li>
            <li><strong>[[TRADE_RISK_2]]:</strong> [[TRADE_RISK_2_DESCRIPTION]]</li>
            <li><strong>[[TRADE_RISK_3]]:</strong> [[TRADE_RISK_3_DESCRIPTION]]</li>
            <li><strong>[[TRADE_RISK_4]]:</strong> [[TRADE_RISK_4_DESCRIPTION]]</li>
        </ul>

        <p><strong>Financial Impact and Mitigation:</strong></p>
        <ul>
            <li><strong>[[TRADE_MITIGATION_1]]:</strong> [[TRADE_MITIGATION_1_DESCRIPTION]]</li>
            <li><strong>[[TRADE_MITIGATION_2]]:</strong> [[TRADE_MITIGATION_2_DESCRIPTION]]</li>
            <li><strong>[[TRADE_MITIGATION_3]]:</strong> [[TRADE_MITIGATION_3_DESCRIPTION]]</li>
            <li><strong>[[TRADE_MITIGATION_4]]:</strong> [[TRADE_MITIGATION_4_DESCRIPTION]]</li>
        </ul>
    </div>

    <div class="key-insights">
        <h4>Macroeconomic and Industry Risks</h4>
        
        <p><strong>Economic Recession Impact ([[RECESSION_PROBABILITY]]% probability):</strong></p>
        <p>[[RECESSION_IMPACT_DESCRIPTION]]</p>

        <p><strong>Industry Evolution Risks:</strong></p>
        <ul>
            <li><strong>[[INDUSTRY_RISK_1]]:</strong> [[INDUSTRY_RISK_1_DESCRIPTION]]</li>
            <li><strong>[[INDUSTRY_RISK_2]]:</strong> [[INDUSTRY_RISK_2_DESCRIPTION]]</li>
            <li><strong>[[INDUSTRY_RISK_3]]:</strong> [[INDUSTRY_RISK_3_DESCRIPTION]]</li>
            <li><strong>[[INDUSTRY_RISK_4]]:</strong> [[INDUSTRY_RISK_4_DESCRIPTION]] <a href="#ref11" class="citation">[11]</a></li>
        </ul>
    </div>

    
</section>
<!--
    INVESTMENT & CAPITAL FLOWS TEMPLATE — INSTRUCTIONS FOR THE AI AGENT

    PURPOSE
    Convert the Investment & Capital Flows section into a repeatable, machine-friendly HTML template.
    Preserve structure, classes, and citation anchors. Provide semantic placeholders, JSON hooks,
    accessibility cues, and validation rules so the renderer can draw charts/tables/cards reliably.

    TOP-LEVEL PLACEHOLDERS (semantic)
    - [[INVESTMENT_OVERVIEW_SUMMARY]]
    - [[INVESTMENT_METRICS_JSON]]            -> metrics for top data-grid cards
    - [[FUNDING_ROUNDS_JSON]]                -> array of major funding rounds
    - [[INVESTOR_LANDSCAPE_JSON]]            -> array of investor categories/cards
    - [[FINANCIAL_MODEL_JSON]]               -> financial model highlights & numeric items
    - [[EXIT_METRICS_JSON]]                  -> exit data-grid metrics
    - [[BUYER_CATEGORIES_JSON]]              -> buyer-category table objects
    - [[IPO_COMPARABLES_JSON]]               -> public comparables list
    - [[EXIT_STRATEGY_PLACEHOLDERS]]         -> narrative placeholders for exit strategy

    RENDER RULES & VALIDATION
    - Currency: include symbol and magnitude (e.g., "$2.3B", "₹10,372 Cr"). Use suffixes K / M / B / Cr.
    - Percentages: must end with '%' (e.g., "60%").
    - Counts: integer or "400+" style with suffix; include source ref when possible.
    - Years/ranges: explicit (e.g., "2022-2024", "2023-2024").
    - JSON must be valid. If an estimate, include "estimate": true in that object.
    - Preserve all citation anchors exactly as-is (e.g., <a href="#ref11" class="citation">[11]</a>).

    ACCESSIBILITY
    - Tables must include <caption> and aria-describedby where helpful.
    - Data cards include aria-label attributes describing the metric and source.
    - Charts role="img" and have aria-label summarizing key metric.

    USAGE NOTES
    - Renderer should prefer JSON hooks for charts/cards. Fallback to the static table/cards if JS unavailable.
    - Keep visual classes identical so CSS/styling continue to apply.

-->

<section id="investment-flows">
    <h2>9. Investment & Capital Flows</h2>
            
    <div class="section-highlight">
        <p>[[INVESTMENT_OVERVIEW_SUMMARY]]</p>
    </div>

    <h3>9.1 Funding & M&A Activity</h3>

    <div class="key-insights">
        <h4>EdTech Investment Trends (2022-2024)</h4>
        <p>[[EDTECH_TRENDS_NARRATIVE]] <a href="#ref11" class="citation">[11]</a><a href="#ref10" class="citation">[10]</a></p>
        
        <!-- Top-level metrics: renderer reads INVESTMENT_METRICS_JSON -->
        <script type="application/json" id="investment-metrics-json">
        [[INVESTMENT_METRICS_JSON]]
        </script>

        <div class="data-grid" aria-hidden="false">
            <div class="data-card" aria-label="Total EdTech investment in India, 2024">
                <span class="metric-value">[[TOTAL_EDTECH_INVESTMENT_2024|$|#ref]]</span>
                <div class="metric-label">Total EdTech Investment<br>India 2024</div>
            </div>
            <div class="data-card" aria-label="Series A/B rounds in 2024">
                <span class="metric-value">[[SERIES_AB_ROUNDS_2024|count|#ref]]</span>
                <div class="metric-label">Series A/B Rounds<br>in 2024</div>
            </div>
            <div class="data-card" aria-label="Share of investments into B2B">
                <span class="metric-value">[[B2B_FOCUS_PERCENT|%|#ref]]</span>
                <div class="metric-label">B2B Focus<br>vs Consumer</div>
            </div>
            <div class="data-card" aria-label="BEST PLACE share of total funding">
                <span class="metric-value">[[BEST PLACE_FUNDING_SHARE|$|#ref]]</span>
                <div class="metric-label">BEST PLACE Share<br>of Total</div>
            </div>
        </div>
    </div>

    <div class="wide-content">
        <h4>Major EdTech Funding Rounds (2023-2024)</h4>

        <!-- Funding rows JSON for renderer -->
        <script type="application/json" id="funding-rounds-json">
        [[FUNDING_ROUNDS_JSON]]
        </script>

        <table class="data-table" aria-describedby="funding-rounds-desc">
            <caption id="funding-rounds-desc">Major funding rounds, 2023-2024 — company, round, amount, lead investors, valuation, relevance.</caption>
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Round</th>
                    <th>Amount</th>
                    <th>Lead Investors</th>
                    <th>Valuation</th>
                    <th>Relevance to Master AI</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>[[FUND_COMPANY_1]]</td>
                    <td>[[FUND_ROUND_1]]</td>
                    <td>[[FUND_AMOUNT_1|$|#ref]]</td>
                    <td>[[FUND_INVESTORS_1]]</td>
                    <td>[[FUND_VALUATION_1|$|#ref]]</td>
                    <td>[[FUND_RELEVANCE_1]]</td>
                </tr>
                <tr>
                    <td>[[FUND_COMPANY_2]]</td>
                    <td>[[FUND_ROUND_2]]</td>
                    <td>[[FUND_AMOUNT_2|$|#ref]]</td>
                    <td>[[FUND_INVESTORS_2]]</td>
                    <td>[[FUND_VALUATION_2|$|#ref]]</td>
                    <td>[[FUND_RELEVANCE_2]]</td>
                </tr>
                <tr>
                    <td>[[FUND_COMPANY_3]]</td>
                    <td>[[FUND_ROUND_3]]</td>
                    <td>[[FUND_AMOUNT_3|$|#ref]]</td>
                    <td>[[FUND_INVESTORS_3]]</td>
                    <td>[[FUND_VALUATION_3|$|#ref]]</td>
                    <td>[[FUND_RELEVANCE_3]]</td>
                </tr>
                <tr>
                    <td>[[FUND_COMPANY_4]]</td>
                    <td>[[FUND_ROUND_4]]</td>
                    <td>[[FUND_AMOUNT_4|$|#ref]]</td>
                    <td>[[FUND_INVESTORS_4]]</td>
                    <td>[[FUND_VALUATION_4|$|#ref]]</td>
                    <td>[[FUND_RELEVANCE_4]]</td>
                </tr>
                <tr>
                    <td>[[FUND_COMPANY_5]]</td>
                    <td>[[FUND_ROUND_5]]</td>
                    <td>[[FUND_AMOUNT_5|$|#ref]]</td>
                    <td>[[FUND_INVESTORS_5]]</td>
                    <td>[[FUND_VALUATION_5|$|#ref]]</td>
                    <td>[[FUND_RELEVANCE_5]]</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section-highlight">
        <h4>Investor Landscape and Preferences</h4>
        <p><strong>Active EdTech Investors in India:</strong></p>

        <!-- Investor cards JSON -->
        <script type="application/json" id="investor-landscape-json">
        [[INVESTOR_LANDSCAPE_JSON]]
        </script>

        <div class="competitive-grid" aria-label="Investor categories and focus">
            <div class="competitor-card">
                <div class="competitor-name">[[INVESTOR_CATEGORY_1_NAME]]</div>
                <div class="competitor-focus">[[INVESTOR_CATEGORY_1_FOCUS]]</div>
            </div>
            <div class="competitor-card">
                <div class="competitor-name">[[INVESTOR_CATEGORY_2_NAME]]</div>
                <div class="competitor-focus">[[INVESTOR_CATEGORY_2_FOCUS]]</div>
            </div>
            <div class="competitor-card">
                <div class="competitor-name">[[INVESTOR_CATEGORY_3_NAME]]</div>
                <div class="competitor-focus">[[INVESTOR_CATEGORY_3_FOCUS]]</div>
            </div>
            <div class="competitor-card">
                <div class="competitor-name">[[INVESTOR_CATEGORY_4_NAME]]</div>
                <div class="competitor-focus">[[INVESTOR_CATEGORY_4_FOCUS]]</div>
            </div>
            <div class="competitor-card">
                <div class="competitor-name">[[INVESTOR_CATEGORY_5_NAME]]</div>
                <div class="competitor-focus">[[INVESTOR_CATEGORY_5_FOCUS]]</div>
            </div>
            <div class="competitor-card">
                <div class="competitor-name">[[INVESTOR_CATEGORY_6_NAME]]</div>
                <div class="competitor-focus">[[INVESTOR_CATEGORY_6_FOCUS]]</div>
            </div>
        </div>

        <p><strong>Investment Thesis Alignment:</strong> [[INVESTMENT_THESIS_ALIGNMENT]]</p>
    </div>

    <div class="key-insights">
        <h4>Financial Model Implications</h4>

        <!-- Financial model JSON -->
        <script type="application/json" id="financial-model-json">
        [[FINANCIAL_MODEL_JSON]]
        </script>

        <p><strong>Capital Efficiency Analysis:</strong></p>
        <ul>
            <li><strong>Higher Initial Investment:</strong> [[CAPEX_YEAR1|$|#ref]]</li>
            <li><strong>Better Unit Economics:</strong> [[UNIT_ECONOMICS_NOTE]]</li>
            <li><strong>Inventory Risk:</strong> [[INVENTORY_RISK_NOTE]]</li>
            <li><strong>Scaling Benefits:</strong> [[SCALING_BENEFITS_NOTE]]</li>
        </ul>

        <p><strong>Investor Appeal Factors:</strong></p>
        <ul>
            <li><strong>Asset-Light Scaling:</strong> [[ASSET_LIGHT_NOTE]]</li>
            <li><strong>Defensive Moat:</strong> [[DEFENSIVE_MOAT_NOTE]]</li>
            <li><strong>Multiple Revenue Streams:</strong> [[REVENUE_STREAMS_LIST]]</li>
            <li><strong>Global Expansion Potential:</strong> [[GLOBAL_EXPANSION_NOTE]]</li>
        </ul>
    </div>

    <h3>9.2 Exit Landscape</h3>

    <div class="section-highlight">
        <h4>M&A Activity in EdTech Sector</h4>
        <p>[[MNA_ACTIVITY_SUMMARY]] <a href="#ref11" class="citation">[11]</a></p>

        <!-- Exit metrics JSON -->
        <script type="application/json" id="exit-metrics-json">
        [[EXIT_METRICS_JSON]]
        </script>

        <div class="data-grid" aria-label="Exit landscape metrics">
            <div class="data-card">
                <span class="metric-value">[[EDTECH_MAND_DEALS_COUNT|count|#ref]]</span>
                <div class="metric-label">EdTech M&A Deals<br>2023-2024</div>
            </div>
            <div class="data-card">
                <span class="metric-value">[[EXIT_REVENUE_MULTIPLE_RANGE]]</span>
                <div class="metric-label">Revenue Multiple<br>Range for Acquisitions</div>
            </div>
            <div class="data-card">
                <span class="metric-value">[[TYPICAL_DEAL_SIZE|$|#ref]]</span>
                <div class="metric-label">Typical Deal Size<br>for Established Players</div>
            </div>
            <div class="data-card">
                <span class="metric-value">[[REVENUE_TO_EXIT_TIMELINE]]</span>
                <div class="metric-label">Timeline<br>Revenue to Exit</div>
            </div>
        </div>
    </div>

    <div class="wide-content">
        <h4>Strategic Buyer Categories and Acquisition Rationale</h4>

        <!-- Buyer categories JSON -->
        <script type="application/json" id="buyer-categories-json">
        [[BUYER_CATEGORIES_JSON]]
        </script>

        <table class="data-table" aria-describedby="buyer-categories-desc">
            <caption id="buyer-categories-desc">Buyer categories, strategic rationale, typical valuations and probabilities.</caption>
            <thead>
                <tr>
                    <th>Buyer Category</th>
                    <th>Potential Acquirers</th>
                    <th>Strategic Rationale</th>
                    <th>Typical Valuations</th>
                    <th>Timeline to Acquisition</th>
                    <th>Probability</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>[[BUYER_CAT_1_NAME]]</strong></td>
                    <td>[[BUYER_CAT_1_ACQUIRERS]]</td>
                    <td>[[BUYER_CAT_1_RATIONALE]]</td>
                    <td>[[BUYER_CAT_1_VALUATION]]</td>
                    <td>[[BUYER_CAT_1_TIMELINE]]</td>
                    <td>[[BUYER_CAT_1_PROBABILITY]]</td>
                </tr>
                <tr>
                    <td><strong>[[BUYER_CAT_2_NAME]]</strong></td>
                    <td>[[BUYER_CAT_2_ACQUIRERS]]</td>
                    <td>[[BUYER_CAT_2_RATIONALE]]</td>
                    <td>[[BUYER_CAT_2_VALUATION]]</td>
                    <td>[[BUYER_CAT_2_TIMELINE]]</td>
                    <td>[[BUYER_CAT_2_PROBABILITY]]</td>
                </tr>
                <tr>
                    <td><strong>[[BUYER_CAT_3_NAME]]</strong></td>
                    <td>[[BUYER_CAT_3_ACQUIRERS]]</td>
                    <td>[[BUYER_CAT_3_RATIONALE]]</td>
                    <td>[[BUYER_CAT_3_VALUATION]]</td>
                    <td>[[BUYER_CAT_3_TIMELINE]]</td>
                    <td>[[BUYER_CAT_3_PROBABILITY]]</td>
                </tr>
                <tr>
                    <td><strong>[[BUYER_CAT_4_NAME]]</strong></td>
                    <td>[[BUYER_CAT_4_ACQUIRERS]]</td>
                    <td>[[BUYER_CAT_4_RATIONALE]]</td>
                    <td>[[BUYER_CAT_4_VALUATION]]</td>
                    <td>[[BUYER_CAT_4_TIMELINE]]</td>
                    <td>[[BUYER_CAT_4_PROBABILITY]]</td>
                </tr>
                <tr>
                    <td><strong>[[BUYER_CAT_5_NAME]]</strong></td>
                    <td>[[BUYER_CAT_5_ACQUIRERS]]</td>
                    <td>[[BUYER_CAT_5_RATIONALE]]</td>
                    <td>[[BUYER_CAT_5_VALUATION]]</td>
                    <td>[[BUYER_CAT_5_TIMELINE]]</td>
                    <td>[[BUYER_CAT_5_PROBABILITY]]</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="key-insights">
        <h4>IPO Potential and Public Market Comparables</h4>

        <!-- IPO comparables JSON -->
        <script type="application/json" id="ipo-comparables-json">
        [[IPO_COMPARABLES_JSON]]
        </script>

        <p>[[IPO_READINESS_SUMMARY]]</p>

        <p><strong>Comparable Public Companies:</strong></p>
        <ul>
            <li>[[COMPARABLE_1_NAME]] — [[COMPARABLE_1_MULTIPLE]]</li>
            <li>[[COMPARABLE_2_NAME]] — [[COMPARABLE_2_MULTIPLE]]</li>
            <li>[[COMPARABLE_3_NAME]] — [[COMPARABLE_3_MULTIPLE]]</li>
            <li>[[COMPARABLE_4_NAME]] — [[COMPARABLE_4_MULTIPLE]]</li>
        </ul>

        <p><strong>IPO Prerequisites:</strong></p>
        <ul>
            <li>[[IPO_REQ_REVENUE_SCALE]]</li>
            <li>[[IPO_REQ_GEOGRAPHIC_DIVERSIFICATION]]</li>
            <li>[[IPO_REQ_PROFITABILITY_PATH]]</li>
            <li>[[IPO_REQ_MARKET_LEADERSHIP]]</li>
        </ul>
    </div>

    <div class="risk-warning">
        <h4>Exit Strategy Considerations</h4>
        
        <p><strong>Timing Optimization:</strong></p>
        <ul>
            <li>[[EXIT_RISK_MARKET_CYCLES]]</li>
            <li>[[EXIT_RISK_COMPETITIVE_DYNAMICS]]</li>
            <li>[[EXIT_RISK_REGULATORY_ENVIRONMENT]]</li>
        </ul>

        <p><strong>Value Maximization Strategies:</strong></p>
        <ul>
            <li>[[EXIT_STRATEGY_IP_PORTFOLIO]]</li>
            <li>[[EXIT_STRATEGY_INTERNATIONAL_EXPANSION]]</li>
            <li>[[EXIT_STRATEGY_OUTCOME_MEASUREMENT]]</li>
            <li>[[EXIT_STRATEGY_PARTNERSHIPS]]</li>
        </ul>
    </div>
</section>
<!--
    CHANNEL & DISTRIBUTION ANALYSIS TEMPLATE — INSTRUCTIONS FOR THE AI AGENT

    PURPOSE
    Convert Channel & Distribution section into a data-driven HTML template while preserving layout,
    classes, and citation anchors. Provide clear placeholders, JSON hooks for rendering, accessibility
    cues, and validation rules.

    TOP-LEVEL PLACEHOLDERS / JSON HOOKS
    - [[CHANNEL_OVERVIEW_SUMMARY]]
    - [[CHANNEL_ECONOMICS_JSON]]    -> array of {channel, margins, margins_pct, cac_label, cac_estimate, scale_potential, notes, citation}
    - [[CHANNEL_EVOLUTION_JSON]]    -> array of {trend, description, horizon_years, citation}
    - [[CHANNEL_RISKS_JSON]]        -> array of {risk, severity, mitigation, owner, citation}

    RENDER RULES & VALIDATION
    - Percent values must end with '%' and be present in both human and machine fields (margins / margins_pct).
    - CAC: provide both qualitative label (Low/Medium/High) and numeric estimate when possible (e.g., { "label":"High", "estimate": 600 } meaning $600).
    - Scale Potential: one of ["Low","Medium","High"].
    - JSON must be valid. If estimate, add "estimate": true.
    - Preserve citation anchors exactly (e.g., <a href="#ref1" class="citation">[1]</a>).

    ACCESSIBILITY
    - Tables include <caption> and aria-describedby where helpful.
    - Data cards include aria-label describing metric and source.
    - Charts/visuals role="img" with concise aria-label.

    FALLBACK
    - Renderer should prefer JSON hooks. If JS disabled, fallback HTML (the table below) must be fully readable.

-->

<section id="channel-distribution">
    <h2>10. Channel & Distribution Analysis</h2>
    
    <h3>10.1 Channel Economics</h3>
    <div class="wide-content">
        <h4>Channel economics table</h4>

        <!-- JSON for renderer -->
        <script type="application/json" id="channel-economics-json">
        [[CHANNEL_ECONOMICS_JSON]]
        </script>

        <table class="data-table" aria-describedby="channel-econ-desc">
            <caption id="channel-econ-desc">Channel economics: margins, customer-acquisition-cost (CAC) ranges and scale potential.</caption>
            <thead>
                <tr>
                    <th>Channel</th>
                    <th>Margins</th>
                    <th>CAC Range (label)</th>
                    <th>CAC Estimate</th>
                    <th>Scale Potential</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>[[CHANNEL_1_NAME]]</td>
                    <td>[[CHANNEL_1_MARGINS|%|#ref]]</td>
                    <td>[[CHANNEL_1_CAC_LABEL]]</td>
                    <td>[[CHANNEL_1_CAC_ESTIMATE|$|#ref]]</td>
                    <td>[[CHANNEL_1_SCALE_POTENTIAL]]</td>
                </tr>
                <tr>
                    <td>[[CHANNEL_2_NAME]]</td>
                    <td>[[CHANNEL_2_MARGINS|%|#ref]]</td>
                    <td>[[CHANNEL_2_CAC_LABEL]]</td>
                    <td>[[CHANNEL_2_CAC_ESTIMATE|$|#ref]]</td>
                    <td>[[CHANNEL_2_SCALE_POTENTIAL]]</td>
                </tr>
                <tr>
                    <td>[[CHANNEL_3_NAME]]</td>
                    <td>[[CHANNEL_3_MARGINS|%|#ref]]</td>
                    <td>[[CHANNEL_3_CAC_LABEL]]</td>
                    <td>[[CHANNEL_3_CAC_ESTIMATE|$|#ref]]</td>
                    <td>[[CHANNEL_3_SCALE_POTENTIAL]]</td>
                </tr>
                <tr>
                    <td>[[CHANNEL_4_NAME]]</td>
                    <td>[[CHANNEL_4_MARGINS|%|#ref]]</td>
                    <td>[[CHANNEL_4_CAC_LABEL]]</td>
                    <td>[[CHANNEL_4_CAC_ESTIMATE|$|#ref]]</td>
                    <td>[[CHANNEL_4_SCALE_POTENTIAL]]</td>
                </tr>
            </tbody>
        </table>
    </div>

    <p>[[CHANNEL_ECONOMICS_SUMMARY]] <a href="#ref1" class="citation">[1]</a></p>

    <h3>10.2 Channel Evolution</h3>
    <div class="key-insights">
        <!-- Evolution JSON -->
        <script type="application/json" id="channel-evolution-json">
        [[CHANNEL_EVOLUTION_JSON]]
        </script>

        <p>[[CHANNEL_EVOLUTION_SUMMARY]] <a href="#ref11" class="citation">[11]</a></p>

        <ul>
            <li>[[EVOLUTION_TREND_1]] — [[EVOLUTION_TREND_1_NOTE]]</li>
            <li>[[EVOLUTION_TREND_2]] — [[EVOLUTION_TREND_2_NOTE]]</li>
            <li>[[EVOLUTION_TREND_3]] — [[EVOLUTION_TREND_3_NOTE]]</li>
        </ul>
    </div>

    <h3>10.3 Channel Risks</h3>
    <div class="risk-warning">
        <!-- Risks JSON -->
        <script type="application/json" id="channel-risks-json">
        [[CHANNEL_RISKS_JSON]]
        </script>

        <p>[[CHANNEL_RISKS_SUMMARY]] <a href="#ref7" class="citation">[7]</a></p>

        <ul>
            <li><strong>Gatekeeper Dependence:</strong> [[RISK_GATEKEEPER_DESC]] — <em>Mitigation:</em> [[RISK_GATEKEEPER_MITIGATION]]</li>
            <li><strong>Channel Conflict:</strong> [[RISK_CHANNEL_CONFLICT_DESC]] — <em>Mitigation:</em> [[RISK_CHANNEL_CONFLICT_MITIGATION]]</li>
            <li><strong>Logistics & Returns:</strong> [[RISK_LOGISTICS_DESC]] — <em>Mitigation:</em> [[RISK_LOGISTICS_MITIGATION]]</li>
        </ul>
    </div>
</section>
<!--
    SCENARIO PLANNING TEMPLATE — INSTRUCTIONS FOR THE AI AGENT

    PURPOSE
    Convert the Scenario Planning section into a repeatable, machine-friendly template while preserving headings,
    card layout, trigger list and citation anchors. Provide semantic placeholders, JSON hooks for charts/cards,
    accessibility cues, and validation rules so the renderer can show cards and compute scenario summaries.

    TOP-LEVEL PLACEHOLDERS / JSON HOOKS
    - [[SCENARIOS_JSON]]         -> array of scenario objects: { id, name, tam|$|unit, som|$|unit, narrative, key_assumptions[], years:"2025-2030", citation }
    - [[SCENARIO_CARDS_JSON]]    -> same as SCENARIOS_JSON (renderer may use either)
    - [[TRIGGER_POINTS_JSON]]    -> array of { trigger, category, severity, citation, action_if_triggered }

    RENDER & VALIDATION RULES
    - Currency fields must include symbol and magnitude (e.g., "$20B", "$3M").
    - Use explicit year-range: "2025-2030".
    - If a number is an estimate, include "estimate": true in JSON.
    - Names: one of ["Base","Optimistic","Pessimistic"] or user-provided equivalents.
    - JSON must be valid. Renderer uses SCENARIOS_JSON for charting, probability assignments, and sensitivity analysis.
    - Preserve citation anchors exactly (e.g., <a href="#ref6" class="citation">[6]</a>).

    ACCESSIBILITY
    - Cards include aria-label summarizing scenario (e.g., aria-label="Base scenario: TAM $20B, SOM $3M").
    - Trigger list has role="list" and each trigger an accessible description.

    USAGE NOTES
    - Agent may compute implied CAGR or revenue paths from TAM→SOM inputs and attach them as derived fields in the JSON:
      e.g., { "derived": { "implied_cagr": "X%", "year5_revenue": "$Y" } }.
    - If probabilities are assigned, add "probability" (0-100) to each scenario object.

-->

<section id="scenario-planning">
    <h2>11. Scenario Planning</h2>
    
    <h3>11.1 Three-Scenario Analysis (2025-2030)</h3>

    <!-- Scenarios JSON: renderer & agent must provide this -->
    <script type="application/json" id="scenarios-json">
    [[SCENARIOS_JSON]]
    </script>

    <div class="data-grid" role="list" aria-label="Scenario cards">
        <div class="data-card" role="listitem" aria-label="[[SCENARIO_BASE_ARIALABEL]]">
            <div class="competitor-name">[[SCENARIO_BASE_NAME]]</div>
            <div class="competitor-focus">
                <div><strong>India TAM:</strong> [[SCENARIO_BASE_TAM|$|#ref]]</div>
                <div><strong>Bengaluru SOM:</strong> [[SCENARIO_BASE_SOM|$|#ref]]</div>
                <div>[[SCENARIO_BASE_SUMMARY]]</div>
            </div>
        </div>

        <div class="data-card" role="listitem" aria-label="[[SCENARIO_OPT_ARIALABEL]]">
            <div class="competitor-name">[[SCENARIO_OPT_NAME]]</div>
            <div class="competitor-focus">
                <div><strong>India TAM:</strong> [[SCENARIO_OPT_TAM|$|#ref]]</div>
                <div><strong>Bengaluru SOM:</strong> [[SCENARIO_OPT_SOM|$|#ref]]</div>
                <div>[[SCENARIO_OPT_SUMMARY]]</div>
            </div>
        </div>

        <div class="data-card" role="listitem" aria-label="[[SCENARIO_PESS_ARIALABEL]]">
            <div class="competitor-name">[[SCENARIO_PESS_NAME]]</div>
            <div class="competitor-focus">
                <div><strong>India TAM:</strong> [[SCENARIO_PESS_TAM|$|#ref]]</div>
                <div><strong>Bengaluru SOM:</strong> [[SCENARIO_PESS_SOM|$|#ref]]</div>
                <div>[[SCENARIO_PESS_SUMMARY]]</div>
            </div>
        </div>
    </div>

    <!-- Optional: derived metrics computed by agent (implied CAGR, Year5 revenue) -->
    <script type="application/json" id="scenario-derived-json">
    [[SCENARIOS_DERIVED_JSON]]
    </script>

    <h3>11.2 Trigger Points</h3>
    <div class="section-highlight" role="region" aria-label="Scenario trigger points">
        <!-- Triggers JSON -->
        <script type="application/json" id="trigger-points-json">
        [[TRIGGER_POINTS_JSON]]
        </script>

        <ul role="list">
            <li role="listitem">[[TRIGGER_1_TEXT]] <a href="#ref6" class="citation">[6]</a></li>
            <li role="listitem">[[TRIGGER_2_TEXT]]</li>
            <li role="listitem">[[TRIGGER_3_TEXT]] <a href="#ref11" class="citation">[11]</a></li>
            <li role="listitem">[[TRIGGER_4_TEXT]]</li>
            <li role="listitem">[[TRIGGER_5_TEXT]]</li>
        </ul>

        <p><strong>Agent action on trigger:</strong> For each trigger include a short actionable escalation plan in [[TRIGGER_POINTS_JSON]] as "action_if_triggered". Example: { "trigger":"Major policy shift","action_if_triggered":"Pause new enterprise contracts; engage counsel; re-run forecast within 30 days" }.</p>
    </div>
</section>
<!--
    STAKEHOLDER MAPPING TEMPLATE — INSTRUCTIONS FOR THE AI AGENT

    PURPOSE
    Turn the Stakeholder Mapping section into a repeatable, machine-friendly template that
    preserves DOM structure, classes and citation anchors while adding data hooks and
    rendering instructions for visualizations (map, power/interest matrix, list).

    PRESERVE:
    - Headings and subsections (12, 12.1, 12.2)
    - Classes (stakeholder-map, stakeholder-item)
    - Citation anchors exactly as-is (e.g., <a href="#ref6" class="citation">[6]</a>)

    TOP-LEVEL PLACEHOLDERS / JSON HOOKS
    - [[STAKEHOLDER_OVERVIEW_SUMMARY]]
    - [[STAKEHOLDERS_JSON]]         -> array of { id, name, category, description, influence: "Low|Low-Med|Medium|High", interest: "Low|Med|High", primary?: true|false, contact?:string, citation }
    - [[POWER_INTEREST_JSON]]       -> array derived or computed: [{ id, x (interest 0-100), y (influence 0-100), label, color, citation }]
    - [[STAKEHOLDER_TIERS_JSON]]    -> { allies:[], neutrals:[], resistors:[], champions:[] }
    - [[ECOSYSTEM_DYNAMICS_SUMMARY]]

    RENDER RULES & VALIDATION
    - Influence/interest values in JSON: use enumerated labels *and* numeric 0–100 when plotting.
      Example stakeholder object: 
      { "id":"gov_moe", "name":"Ministry of Education (MoE)", "category":"Government", "influence":"High", "influence_score":95, "interest":"High", "interest_score":85, "citation":"#ref6" }
    - Strings: short, human-readable. Do not exceed 140 chars in description fields.
    - JSON must be valid. If a field is estimated add "estimate": true.
    - Preserve citations exactly (no new refs).

    VISUALIZATION & ACCESSIBILITY
    - Renderer reads #stakeholders-json and #power-interest-json.
    - Provide two visual options:
       1) Network map (nodes: stakeholders, edges: relationships). Required node fields: id, name, category, size(influence_score), color.
       2) Power / Interest matrix (x: interest_score, y: influence_score). Required fields: x,y,label,color.
    - All visuals must include role="img" and aria-label summarizing top 3 high-influence stakeholders.
    - Fallback: render accessible table and grouped lists.

    AGENT ACTION GUIDES (what to fill)
    - For each stakeholder add: category, short description, influence (label + score), interest (label + score), one-line engagement tactic.
      Placeholders: [[STAKE_1_NAME]], [[STAKE_1_CATEGORY]], [[STAKE_1_DESC]], [[STAKE_1_INFLUENCE_LABEL]], [[STAKE_1_INFLUENCE_SCORE]], [[STAKE_1_INTEREST_LABEL]], [[STAKE_1_INTEREST_SCORE]], [[STAKE_1_ENGAGEMENT_STRATEGY]], [[STAKE_1_CITATION]]
    - Populate STAKEHOLDER_TIERS_JSON grouping by engagement priority.

    EXAMPLE JSON SCHEMAS
    - #stakeholders-json -> [[STAKEHOLDERS_JSON]]
      [
        {"id":"gov_moe","name":"MoE","category":"Government","description":"Ministry of Education","influence":"High","influence_score":95,"interest":"High","interest_score":80,"engagement":"Policy briefings; pilot programs","citation":"#ref6"}
      ]
    - #power-interest-json -> [[POWER_INTEREST_JSON]]
      [
        {"id":"gov_moe","x":80,"y":95,"label":"MoE","color":"#d9534f","citation":"#ref6"}
      ]

    OUTPUTS THE AGENT SHOULD PRODUCE
    - Fill [[STAKEHOLDERS_JSON]] with all stakeholders in section.
    - Compute [[POWER_INTEREST_JSON]] from stakeholders (numeric scores).
    - Produce [[STAKEHOLDER_TIERS_JSON]] grouping allies/champions/resistors.
    - Provide concise [[ECOSYSTEM_DYNAMICS_SUMMARY]] (~1-2 sentences).

    NOTE
    - Keep markup identical so CSS remains valid.
    - Do not remove or alter citation anchors.
-->

<section id="stakeholder-mapping">
    <h2>12. Stakeholder Mapping</h2>
    
    <h3>12.1 Key Institutions and Influencers</h3>

    <!-- Stakeholders JSON for renderer -->
    <script type="application/json" id="stakeholders-json">
    [[STAKEHOLDERS_JSON]]
    </script>

    <div class="stakeholder-map" role="region" aria-label="Stakeholder map: key institutions and influence">
        <!-- Fallback accessible list (non-js) -->
        <noscript>
            <div class="stakeholder-list-fallback">
                <p><strong>Note:</strong> Enable JavaScript to view the interactive stakeholder map. Fallback list below.</p>
            </div>
        </noscript>

        <!-- Visual renderer should create nodes from #stakeholders-json.
             Static placeholders for each original item (agent to replace) -->
        <div class="stakeholder-item" aria-label="[[STAKE_1_NAME]] — [[STAKE_1_CATEGORY]] — Influence: [[STAKE_1_INFLUENCE_LABEL]]">
            <strong>[[STAKE_1_NAME]]</strong><br>
            [[STAKE_1_DESC]]<br>
            [[STAKE_1_INFLUENCE_LABEL]]
        </div>
        <div class="stakeholder-item" aria-label="[[STAKE_2_NAME]] — [[STAKE_2_CATEGORY]] — Influence: [[STAKE_2_INFLUENCE_LABEL]]">
            <strong>[[STAKE_2_NAME]]</strong><br>
            [[STAKE_2_DESC]]<br>
            [[STAKE_2_INFLUENCE_LABEL]]
        </div>
        <div class="stakeholder-item" aria-label="[[STAKE_3_NAME]] — [[STAKE_3_CATEGORY]] — Influence: [[STAKE_3_INFLUENCE_LABEL]]">
            <strong>[[STAKE_3_NAME]]</strong><br>
            [[STAKE_3_DESC]]<br>
            [[STAKE_3_INFLUENCE_LABEL]]
        </div>
        <div class="stakeholder-item" aria-label="[[STAKE_4_NAME]] — [[STAKE_4_CATEGORY]] — Influence: [[STAKE_4_INFLUENCE_LABEL]]">
            <strong>[[STAKE_4_NAME]]</strong><br>
            [[STAKE_4_DESC]]<br>
            [[STAKE_4_INFLUENCE_LABEL]]
        </div>
        <div class="stakeholder-item" aria-label="[[STAKE_5_NAME]] — [[STAKE_5_CATEGORY]] — Influence: [[STAKE_5_INFLUENCE_LABEL]]">
            <strong>[[STAKE_5_NAME]]</strong><br>
            [[STAKE_5_DESC]]<br>
            [[STAKE_5_INFLUENCE_LABEL]]
        </div>
        <div class="stakeholder-item" aria-label="[[STAKE_6_NAME]] — [[STAKE_6_CATEGORY]] — Interest: [[STAKE_6_INTEREST_LABEL]]">
            <strong>[[STAKE_6_NAME]]</strong><br>
            [[STAKE_6_DESC]]<br>
            [[STAKE_6_INTEREST_LABEL]]
        </div>
    </div>

    <p>[[STAKEHOLDER_OVERVIEW_SUMMARY]] <a href="#ref6" class="citation">[6]</a><a href="#ref7" class="citation">[7]</a><a href="#ref14" class="citation">[14]</a></p>

    <h3>12.2 Ecosystem Power Dynamics</h3>

    <!-- Power / Interest JSON for plotting matrix -->
    <script type="application/json" id="power-interest-json">
    [[POWER_INTEREST_JSON]]
    </script>

    <p>[[ECOSYSTEM_DYNAMICS_SUMMARY]] <a href="#ref14" class="citation">[14]</a></p>

    <!-- Power/Interest matrix container -->
    <div class="power-interest-matrix" role="img" aria-label="Power-interest matrix: top influencers highlighted.">
        <!-- Renderer should draw matrix from #power-interest-json.
             Provide a textual fallback summary for accessibility. -->
        <noscript>
            <div class="power-interest-fallback">
                <p><strong>Top influencers (by score):</strong> [[TOP_3_INFLUENCERS_LIST]]</p>
            </div>
        </noscript>
    </div>

    <!-- Tiers JSON: allies / champions / neutrals / resistors -->
    <script type="application/json" id="stakeholder-tiers-json">
    [[STAKEHOLDER_TIERS_JSON]]
    </script>

    <div class="key-insights">
        <h4>Engagement Recommendations</h4>
        <ul>
            <li><strong>Allies / Champions:</strong> [[TIER_ALLIES_NOTE]]</li>
            <li><strong>Neutrals:</strong> [[TIER_NEUTRALS_NOTE]]</li>
            <li><strong>Resistors / Risks:</strong> [[TIER_RESISTORS_NOTE]]</li>
        </ul>
    </div>
</section>
<!--
    CONCLUSIONS & REFERENCES TEMPLATE — INSTRUCTIONS FOR THE AI AGENT

    PURPOSE
    Convert final report sections into a machine-friendly template while preserving:
      - Headings, numbering, references and citation anchors.
      - Visual/layout semantics so existing CSS continues to work.

    WHAT TO FILL
    - [[CONCLUSIONS_OVERVIEW]] : 1–2 sentence summary (human).
    - Recommendations: populate both HTML list items and machine JSON:
        * [[RECOMMENDATION_1]] ... [[RECOMMENDATION_5]]
        * JSON hook id="recommendations-json" -> [[RECOMMENDATIONS_JSON]]
          Schema: [{ "id":"rec1","title":"Bengaluru-First Strategy","detail":"Short action steps","priority":1 }]
    - References: keep anchors exactly as-is. If adding or replacing references, update the <ol> entries and also populate [[REFERENCES_JSON]].
      Schema: [{ "id":"ref1","title":"Virtue Market Research","url":"https://virtuemarketresearch.com","note":"EdTech Market Size (2024–2033)","accessed":"2025-08-25" }]

    VALIDATION RULES
    - Recommendations: each item ≤ 250 chars. Provide one-line action step and an owner (role/team).
    - JSON must be valid. If estimate or projection add "estimate": true.
    - Dates use ISO-like format YYYY-MM-DD when included.
    - Do not change citation anchors (e.g., <a href="#ref11" class="citation">[11]</a>).

    ACCESSIBILITY
    - Ordered list <ol> should be semantically correct; include aria-label on the container summarizing top recommendation.
    - Footer must include [[REPORT_YEAR]] and [[PRODUCT_NAME]] placeholders.

    RENDERER NOTES
    - Renderer should read #recommendations-json and #references-json to produce cards, exportable CSV, or slide-ready summaries.
    - When exporting to PDF/print, append a timestamp placeholder [[TIMESTAMP_ISO]].

-->

<section id="conclusions">
    <h2>13. Conclusions & Recommendations</h2>
    
    <!-- Human-readable overview -->
    <div class="key-insights">
        <h3>Strategic Recommendations</h3>

        <!-- JSON for renderer -->
        <script type="application/json" id="recommendations-json">
        [[RECOMMENDATIONS_JSON]]
        </script>

        <ol aria-label="Top strategic recommendations">
            <li><strong>[[RECOMMENDATION_1_TITLE]]</strong>: [[RECOMMENDATION_1_DETAIL]]</li>
            <li><strong>[[RECOMMENDATION_2_TITLE]]</strong>: [[RECOMMENDATION_2_DETAIL]]</li>
            <li><strong>[[RECOMMENDATION_3_TITLE]]</strong>: [[RECOMMENDATION_3_DETAIL]]</li>
            <li><strong>[[RECOMMENDATION_4_TITLE]]</strong>: [[RECOMMENDATION_4_DETAIL]]</li>
            <li><strong>[[RECOMMENDATION_5_TITLE]]</strong>: [[RECOMMENDATION_5_DETAIL]]</li>
        </ol>
    </div>
</section>

<section id="references" class="references">
    <h2>References</h2>

    <!-- References JSON (renderer / citation manager) -->
    <script type="application/json" id="references-json">
    [[REFERENCES_JSON]]
    </script>

    <!-- Keep the original reference list as-is; agent may append additional refs below while preserving IDs. -->
    <ol>
        <li id="ref1"><a href="https://virtuemarketresearch.com" target="_blank">Virtue Market Research</a> - EdTech Market Size and Growth (2024–2033); India-specific implications</li>
        <li id="ref2"><a href="https://investindia.gov.in" target="_blank">Invest India</a> - AI in Education Market (global; 2025–2030) projections</li>
        <li id="ref3"><a href="https://grandviewresearch.com" target="_blank">Grand View Research</a> - Bengaluru EdTech Funding and city concentration metrics (2023–2024)</li>
        <li id="ref4"><a href="https://schoolnetindia.com" target="_blank">SchoolNet India</a> - India EdTech market analysis and CAGR context</li>
    </ol>
</section>

<footer>
    <p>© [[REPORT_YEAR]] [[PRODUCT_NAME]] Market Analysis Report. All data points referenced to cited sources and timestamped for currency.</p>
    <!-- Export timestamp for PDF/print -->
    <meta name="report-timestamp" content="[[TIMESTAMP_ISO]]" />
</footer>


---
    ### HTML TEMPLATE COMPLIANCE

    **CRITICAL:** You must use the EXACT HTML structure provided above. Do not modify the HTML structure, CSS, or JavaScript. Only replace the bracketed placeholders with actual data.

    ** Missing Data Handling:**
    - If specific data is not found, explicitly state "Information not available in research"
    - Do not leave bracketed placeholders unfilled
    - For missing metrics, use "N/A" or state "Data not found"
    - For missing sections, include a note explaining the limitation

    ### WIKIPEDIA-STYLE CITATION REQUIREMENTS
    **Citation Format:** All numbered citations should be hyperlinks to the relevant reference at the bottom.
    - Cite all market size figures, growth rates, and financial data
    - Cite customer demographic and behavioral statistics  
    - Cite competitor information, market share data, and positioning claims
    - Cite industry trends, regulatory factors, and PESTLE analysis points
    - Citations will be automatically converted to numbered hyperlinks

    ---
    ### FINAL QUALITY CHECKLIST
    - [ ] All bracketed placeholders replaced with actual data
    - [ ] Tables populated with ALL real segment data (remove placeholder rows)
    - [ ] Metrics and KPIs updated with actual values
    - [ ] CSS variables set for visual elements (--v: 0-100 for bars, --x/--y: 0-100 for positioning)
    - [ ] Citations added for all factual claims
    - [ ] Missing data explicitly acknowledged where applicable
    - [ ] Professional tone maintained throughout
    - [ ] Strategic insights provided in each section

    MANDATES (must follow exactly)
    1. Preserve the entire HTML/CSS/JS structure exactly as provided. Do not add, remove, or re-order tags, style blocks, script tags, id attributes, or citation anchors. (If you modify structure, the output is invalid.)
    2. Replace **every** `[[BRACKETED_PLACEHOLDER]]` with content of the correct type:
    - If placeholder is a visible text block → replace with a concise human-ready sentence/paragraph.
    - If placeholder is a metric card → replace with value + units (e.g., "₹10,372 Cr | #ref15").
    - If placeholder is a JSON hook inside `<script type="application/json" id="...">` → **replace with valid JSON** only (no comments, no trailing commas). If unknown, insert a valid JSON object indicating missing data (see Missing Data rule).
    3. JSON rules:
    - Must be valid JSON (strict). Example: `[{"region":"Bengaluru","score":90,"label":"High (9/10)","citation":"#ref3"}]`.
    - If a value is estimated add `"estimate": true` in the object.
    - Percent strings must end with '%'. Currency must include symbol & magnitude (K, M, B, Cr).
    4. Missing data: **do not leave placeholders**. Use the exact text `"Information not available in research"` for human text fields. For JSON hooks use valid JSON with a single object: `{"note":"Information not available in research","estimate":true}`.
    5. Citation anchors must be preserved exactly (e.g., `<a href="#ref11" class="citation">[11]</a>`). When you state a fact, attach the appropriate citation anchor inline as in the template.
    6. Output format: **the response must be the complete HTML only** (one code block or raw HTML). No explanations, no extra JSON, no markdown headers. If the agent cannot fill a placeholder because the source data lacks it, still replace it (see rule 4).
    7. Final validation (automated checks your agent must pass before returning):
    - No `[[` or `]]` remain anywhere.
    - All `<script type="application/json" id="...">` blocks contain parseable JSON.
    - Percent values end with `%`.
    - Currency values include symbol and magnitude suffix (K/M/B/Cr).
    - Citation anchors exist where the template required them.
    Generate the complete HTML report using the template above with all placeholders filled with actual research data.


"""