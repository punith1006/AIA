SEG_TEMPLATE = """
    You are an expert segmentation analysis report writer specializing in creating comprehensive HTML reports that exactly follow the provided template structure.

    **MISSION:** Transform segmentation research data into a polished, professional HTML Segmentation Analysis Report following the exact template format with Wikipedia-style numbered citations.

    ---
    ### INPUT DATA SOURCES
    * Research Findings: {segmentation_research_findings}
    * Citation Sources: {citations}
    * Report Structure: {report_sections}

    ---
    ### HTML TEMPLATE
    Use this EXACT template structure and only replace the bracketed placeholders with actual data:

    ```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Market Segmentation — Interactive Report Template</title>
  <style>
    /* Layout inspired by user's sample: clean cards, gentle gradients, readable type */
    :root{
      --accent:#667eea;
      --accent-2:#ff6b6b;
      --muted:#6c757d;
      --bg:linear-gradient(135deg,#f5f7fa 0%,#eef3fb 100%);
      --card:#ffffff;
      --glass: rgba(255,255,255,0.6);
      --radius:12px;
      --maxw:1200px;
      --gutter:24px;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
    }
    *{box-sizing:border-box}
    html{scroll-behavior:smooth}
    body{
      margin:0;
      min-height:100vh;
      background:var(--bg);
      color:#222;
      line-height:1.55;
      padding:32px;
      -webkit-font-smoothing:antialiased;
      -moz-osx-font-smoothing:grayscale;
    }
    .wrap{max-width:var(--maxw);margin:0 auto;background:var(--card);border-radius:16px;box-shadow:0 18px 40px rgba(16,24,40,0.08);overflow:hidden}

    /* Header */
    header.report-header{padding:40px 36px;background:linear-gradient(90deg,var(--accent) 0%, #764ba2 100%);color:#fff;position:relative}
    header.report-header h1{font-size:clamp(20px,3vw,28px);margin:0 0 6px;font-weight:700}
    header.report-header p.lead{margin:0;color:rgba(255,255,255,0.9)}
    header.meta{display:flex;gap:16px;padding:18px 36px;background:#f8f9fa;border-bottom:1px solid #eef2ff;color:var(--muted);flex-wrap:wrap}
    header.meta .meta-item{font-size:0.9rem}

    /* Two-column layout */
    .content{display:grid;grid-template-columns:280px 1fr;gap:var(--gutter);padding:28px}
    nav.toc{position:sticky;top:28px;padding:18px;background:linear-gradient(180deg,#fff, #fbfdff);border-radius:12px;border:1px solid #eef2ff}
    nav.toc h3{margin:0 0 12px;font-size:1rem;color:#2c3e50}
    nav.toc ul{list-style:none;padding:0;margin:0;display:grid;gap:8px}
    nav.toc a{color:var(--accent);text-decoration:none;font-weight:600}
    nav.toc a small{display:block;color:var(--muted);font-weight:500}

    /* Main article */
    main.report-body{padding:6px 0}
    section.card{background:var(--card);border-radius:12px;padding:20px;margin-bottom:20px;border:1px solid #eef2ff}
    section.card h2{margin:0 0 10px;font-size:1.25rem;border-bottom:2px solid #f1f5ff;padding-bottom:8px}
    .lead-para{background:linear-gradient(90deg, rgba(102,126,234,0.06), rgba(118,75,162,0.02));padding:14px;border-radius:8px;margin-bottom:12px}

    /* Grid cards */
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}
    .stat{background:var(--glass);padding:14px;border-radius:10px;border:1px solid rgba(102,126,234,0.06)}
    .stat h4{margin:0;font-size:0.95rem;color:var(--accent)}
    .stat p{margin:6px 0 0;font-weight:700;font-size:1.15rem}

    /* Tables */
    table.data{width:100%;border-collapse:collapse;margin-top:12px}
    table.data th,table.data td{padding:10px 12px;border:1px solid #eef2ff;text-align:left}
    table.data th{background:#fbfdff;font-weight:700}

    /* PESTLE compact */
    .pestle{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
    .pestle .factor{background:#fff;padding:12px;border-radius:10px;border-left:4px solid var(--accent);min-height:110px}
    .factor h4{margin:0 0 6px}

    /* Perceptual map & Ansoff - SVG containers */
    .visuals{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    .viz-box{background:#fff;border-radius:10px;padding:12px;border:1px solid #eef2ff}

    /* SWOT boxes in a 2x2 */
    .swot{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    .swot .box{padding:12px;border-radius:8px;background:#fff;border:1px solid #eef2ff}
    .swot .box h4{margin-top:0;color:var(--accent)}

    /* Segments table */
    .segments-table{overflow:auto}

    /* Small UI helpers */
    .muted{color:var(--muted)}
    .pill{display:inline-block;padding:6px 10px;border-radius:999px;background:#f0f4ff;border:1px solid #e6ecff;font-weight:700;color:var(--accent)}
    
    /* New styles for enhanced analysis */
    .analysis-note {
      background: #f8f9ff;
      padding: 12px;
      border-radius: 8px;
      border-left: 4px solid var(--accent);
      margin: 12px 0;
      font-size: 0.95rem;
    }
    .methodology {
      font-size: 0.9rem;
      color: var(--muted);
      font-style: italic;
      margin-bottom: 8px;
    }
    .definition {
      background: #f9fafc;
      padding: 10px;
      border-radius: 6px;
      margin: 8px 0;
      font-size: 0.9rem;
    }
    .definition h5 {
      margin: 0 0 4px 0;
      color: var(--accent);
      font-size: 0.9rem;
    }
    .number-highlight {
      font-weight: 700;
      color: var(--accent);
      background: rgba(102, 126, 234, 0.1);
      padding: 2px 6px;
      border-radius: 4px;
    }

    /* Responsive */
    @media (max-width:920px){.content{grid-template-columns:1fr;}.visuals{grid-template-columns:1fr}.swot{grid-template-columns:1fr}.toc{position:relative;order:2}}

    /* Print tweaks */
    @media print{body{padding:0;background:white}.wrap{box-shadow:none;border-radius:0}.content{grid-template-columns:1fr}.toc{display:none}}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="report-header">
      <h1>Comprehensive Market Segmentation Analysis</h1>
      <p class="lead">[Product / Service / Company] — Detailed Analytical Report with Strategic Insights</p>
    </header>

    <div class="meta" style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;padding:14px 32px">
      <div class="meta-item"><strong>Report ID:</strong> <span class="pill">SEG-2024-06-15-001</span></div>
      <div class="meta-item"><strong>Date:</strong> <span class="muted">2024-06-15</span></div>
      <div class="meta-item"><strong>Prepared for:</strong> <span class="muted">[Client / Team]</span></div>
      <div class="meta-item"><strong>Analyst:</strong> <span class="muted">[Name/Department]</span></div>
    </div>

    <div class="content">
      <!-- LEFT: TOC / Quick filters -->
      <nav class="toc" aria-label="Table of contents">
        <h3>Contents</h3>
        <ul>
          <li><a href="#exec">1. Executive Summary</a><small> — Key findings & recommendations</small></li>
          <li><a href="#definitions">2. Key Definitions</a><small> — Terminology & abbreviations</small></li>
          <li><a href="#pestle">3. Market Overview (PESTLE)</a></li>
          <li><a href="#competitive">4. Competitive Landscape</a></li>
          <li><a href="#segments">5. Core Segments</a></li>
          <li><a href="#deep">6. Segment Profiles</a></li>
          <li><a href="#evaluate">7. Segment Evaluation</a></li>
          <li><a href="#target">8. Targeting & Recommendations</a></li>
          <li><a href="#position">9. Positioning</a></li>
          <li><a href="#mix">10. Marketing Mix</a></li>
          <li><a href="#conclude">11. Conclusion</a></li>
          <li><a href="#appendix">12. Appendix</a><small> — Methodology & data sources</small></li>
        </ul>

        <hr style="margin:12px 0;border:none;border-top:1px dashed #eef2ff" />
        <div style="font-size:0.9rem;color:var(--muted)">Report Filters</div>
        <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
          <span class="pill">B2B</span>
          <span class="pill">B2C</span>
          <span class="pill">Healthcare</span>
          <span class="pill">SMB</span>
        </div>
      </nav>

      <!-- RIGHT: Main content -->
      <main class="report-body">

        <!-- 1 EXECUTIVE -->
        <section id="exec" class="card">
          <h2>1. Executive Summary</h2>
          <div class="lead-para"> 
            <strong>Purpose:</strong> <span class="muted">To identify and evaluate market segments for [Product/Service] to inform targeting strategy and resource allocation</span>
            <p style="margin-top:8px">This analysis identifies <span class="number-highlight">[X]</span> distinct market segments in the [Industry] sector, with a total addressable market (TAM) of <span class="number-highlight">[$Y billion]</span> growing at <span class="number-highlight">[Z]%</span> CAGR. Key trends include [trend 1], [trend 2], and [trend 3]. Our analysis recommends focusing on [Segment A] and [Segment B] as primary targets based on attractiveness and strategic fit.</p>
          </div>
          <div class="grid">
            <div class="stat"><h4>Key Segments Identified</h4><p>[X] distinct segments</p></div>
            <div class="stat"><h4>Primary Target</h4><p>[Segment A] ([$Size])</p></div>
            <div class="stat"><h4>Market Growth</h4><p>[Z]% CAGR</p></div>
            <div class="stat"><h4>Recommended Approach</h4><p>[Differentiated Targeting]</p></div>
          </div>
          
          <div class="analysis-note">
            <strong>Analytical Note:</strong> This analysis utilized [cluster analysis, factor analysis, etc.] based on [number] data points collected between [date range]. Confidence level: [high/medium/low] based on data completeness and sample size.
          </div>
        </section>

        <!-- 2 DEFINITIONS -->
        <section id="definitions" class="card">
          <h2>2. Key Definitions & Abbreviations</h2>
          <p class="muted">Terminology used throughout this report</p>
          
          <div class="definition">
            <h5>TAM (Total Addressable Market)</h5>
            <p>The total market demand for a product or service, representing the revenue opportunity available.</p>
          </div>
          
          <div class="definition">
            <h5>SAM (Serviceable Available Market)</h5>
            <p>The segment of the TAM targeted by your products and services which is within your geographical reach.</p>
          </div>
          
          <div class="definition">
            <h5>SOM (Serviceable Obtainable Market)</h5>
            <p>The portion of SAM that you can capture within a realistic timeframe, considering competition and constraints.</p>
          </div>
          
          <div class="definition">
            <h5>CAGR (Compound Annual Growth Rate)</h5>
            <p>The mean annual growth rate of an investment over a specified period longer than one year.</p>
          </div>
          
          <div class="definition">
            <h5>PESTLE Analysis</h5>
            <p>A framework analyzing Political, Economic, Social, Technological, Legal, and Environmental factors.</p>
          </div>
          
          <div class="definition">
            <h5>B2B / B2C</h5>
            <p>Business-to-Business / Business-to-Customer market orientations.</p>
          </div>
          
          <div class="definition">
            <h5>SMB</h5>
            <p>Small and Medium-sized Businesses (typically 1-500 employees).</p>
          </div>
        </section>

        <!-- 3 PESTLE -->
        <section id="pestle" class="card">
          <h2>3. Market Overview & Macro Environment (PESTLE)</h2>
          <p class="muted">Analysis of external forces shaping the market and their implications for segmentation.</p>
          
          <div class="methodology">
            Methodology: Impact scores based on expert evaluation (1=minimal impact, 5=significant impact)
          </div>
          
          <div class="pestle">
            <div class="factor">
              <h4>Political <span class="pill">Impact: 3/5</span></h4>
              <p class="muted">[Regulation changes, trade policies, political stability]</p>
            </div>
            <div class="factor">
              <h4>Economic <span class="pill">Impact: 4/5</span></h4>
              <p class="muted">[Growth rates, inflation, disposable income, employment levels]</p>
            </div>
            <div class="factor">
              <h4>Social <span class="pill">Impact: 5/5</span></h4>
              <p class="muted">[Demographic shifts, cultural trends, lifestyle changes]</p>
            </div>
            <div class="factor">
              <h4>Technological <span class="pill">Impact: 4/5</span></h4>
              <p class="muted">[Innovation, R&D, automation, technological awareness]</p>
            </div>
            <div class="factor">
              <h4>Legal <span class="pill">Impact: 3/5</span></h4>
              <p class="muted">[Employment laws, consumer protection, health and safety]</p>
            </div>
            <div class="factor">
              <h4>Environmental <span class="pill">Impact: 2/5</span></h4>
              <p class="muted">[Environmental regulations, sustainability concerns]</p>
            </div>
          </div>

          <h3 style="margin-top:16px">PESTLE Impact Assessment</h3>
          <table class="data" aria-label="PESTLE Impact Assessment">
            <thead>
              <tr><th>Factor</th><th>Current Trend</th><th>Impact (1-5)</th><th>Implication for Segmentation</th><th>Time Horizon</th></tr>
            </thead>
            <tbody>
              <tr>
                <td>Political</td>
                <td>[Increasing regulation in key markets]</td>
                <td>3</td>
                <td>[Creatures compliance-focused segment opportunity]</td>
                <td>Medium-term (1-3 years)</td>
              </tr>
              <tr>
                <td>Economic</td>
                <td>[Growing disposable income in emerging markets]</td>
                <td>4</td>
                <td>[Expands premium segment potential in Asia-Pacific]</td>
                <td>Short-term (0-1 years)</td>
              </tr>
              <!-- Additional rows for other factors -->
            </tbody>
          </table>
          
          <div class="analysis-note">
            <strong>Key Insight:</strong> Social factors (demographic and cultural shifts) present the highest impact opportunity for segmentation strategy, particularly for [specific implication].
          </div>
        </section>

        <!-- Additional sections would continue with similar enhancements -->
        
        <!-- 11 CONCLUSION -->
        <section id="conclude" class="card">
          <h2>11. Conclusion & Strategic Recommendations</h2>
          <p class="muted">Synthesis of findings and actionable next steps.</p>
          
          <h4>Primary Recommendations</h4>
          <ol>
            <li><strong>Target Segment Priority:</strong> Focus on [Segment A] and [Segment B] as primary targets representing [X]% of addressable market</li>
            <li><strong>Resource Allocation:</strong> Allocate [Y]% of marketing budget to these segments based on potential ROI</li>
            <li><strong>Positioning Strategy:</strong> Develop distinct positioning for each priority segment</li>
            <li><strong>Timeline:</strong> Implement phased approach over [timeframe]</li>
          </ol>
          
          <h4>Implementation Risks & Mitigation</h4>
          <table class="data">
            <thead>
              <tr><th>Risk</th><th>Probability</th><th>Impact</th><th>Mitigation Strategy</th></tr>
            </thead>
            <tbody>
              <tr>
                <td>[Competitive response]</td>
                <td>High</td>
                <td>Medium</td>
                <td>[Differentiate through unique value proposition]</td>
              </tr>
              <tr>
                <td>[Market shift]</td>
                <td>Medium</td>
                <td>High</td>
                <td>[Continuous monitoring and agile adaptation]</td>
              </tr>
            </tbody>
          </table>
        </section>
        
        <!-- 12 APPENDIX -->
        <section id="appendix" class="card">
          <h2>12. Appendix</h2>
          
          <h4>Methodology Details</h4>
          <p>This analysis employed the following methodology:</p>
          <ul>
            <li><strong>Data Collection:</strong> [Sources, timeframe, sample size]</li>
            <li><strong>Analytical Techniques:</strong> [Cluster analysis, factor analysis, regression, etc.]</li>
            <li><strong>Segmentation Bases:</strong> [Geographic, demographic, psychographic, behavioral]</li>
            <li><strong>Validation Approach:</strong> [Statistical validation methods used]</li>
          </ul>
          
          <h4>Data Sources</h4>
          <table class="data">
            <thead>
              <tr><th>Source</th><th>Type</th><th>Time Period</th><th>Reliability Score</th></tr>
            </thead>
            <tbody>
              <tr>
                <td>[Industry Report Name]</td>
                <td>Secondary</td>
                <td>2023</td>
                <td>High</td>
              </tr>
              <tr>
                <td>[Internal Customer Data]</td>
                <td>Primary</td>
                <td>2022-2024</td>
                <td>High</td>
              </tr>
            </tbody>
          </table>
        </section>

      </main>
    </div>

  </div>
</body>
</html>

    ```

    ---
    ### HTML TEMPLATE COMPLIANCE

    **CRITICAL:** You must use the EXACT HTML structure provided above. Do not modify the HTML structure, CSS, or JavaScript. Only replace the bracketed placeholders with actual data.

    **1. Template Sections to Fill:**
    - Replace [Product/Service Name] with actual product name
    - Replace [Report-Number] with generated report ID (format: SEG-YYYY-MM-DD-001)
    - Replace [Date of Report] with current date: {datetime.datetime.now().strftime("%B %d, %Y")}
    - Fill all bracketed placeholders throughout the document
    - Populate tables with actual data rows
    - Update KPI values and metrics
    - Replace placeholder content in each section

    **2. Data Population Rules:**
    - **Tables:** Add actual data rows inside <tbody> sections, removing placeholder rows
    - **Metrics:** Update data-value attributes and --v CSS variables for bars/charts with actual percentages
    - **Perceptual Map:** Set style="--x: [0-100]; --y: [0-100]" on .dot elements for competitor positioning
    - **Timeline:** Set style="--start: week; --end: week" on .band elements for project phases
    - **KPIs:** Replace bracketed values with actual numbers and percentages
    - **Segment Details:** Expand the details sections with complete segment profiles

    **3. Missing Data Handling:**
    - If specific data is not found, explicitly state "Information not available in research"
    - Do not leave bracketed placeholders unfilled
    - For missing metrics, use "N/A" or state "Data not found"
    - For missing sections, include a note explaining the limitation

    ---
    ### CONTENT QUALITY STANDARDS

    **1. Comprehensive Coverage:**
    - Executive Summary with key findings and TAM/SAM/SOM estimates
    - Complete PESTLE analysis for each factor with segment-specific implications
    - Detailed segment profiles with demographics, psychographics, and behaviors
    - Segment attractiveness matrix with actual scoring (0-100 scale)
    - Competitive positioning and perceptual mapping with competitor placement
    - Marketing mix implications (4Ps) for each priority segment
    - Implementation timeline with specific milestones and week numbers
    - Conclusions with actionable recommendations

    **2. Data Integration:**
    - Use actual figures from research findings
    - Include segment sizes, growth rates, and market values with proper formatting
    - Provide specific competitor names and market shares when available
    - Reference recent trends and developments (2023-2024)
    - Include geographic and demographic specifics
    - Convert percentages to --v CSS variables for visual bars (0-100 scale)

    **3. Strategic Insights:**
    - Each section should provide actionable business insights
    - Balance opportunities with challenges and risks
    - Provide clear rationale for segment prioritization
    - Connect PESTLE factors to segment implications
    - Link competitive positioning to strategic recommendations

    ---
    ### WIKIPEDIA-STYLE CITATION REQUIREMENTS
    **Citation Format:** Use ONLY `<cite source="src-ID_NUMBER" />` tags immediately after factual claims.
    - Cite all market size figures, growth rates, and financial data
    - Cite customer demographic and behavioral statistics  
    - Cite competitor information, market share data, and positioning claims
    - Cite industry trends, regulatory factors, and PESTLE analysis points
    - Citations will be automatically converted to numbered hyperlinks

    ---
    ### FINAL QUALITY CHECKLIST
    - [ ] All bracketed placeholders replaced with actual data
    - [ ] Tables populated with real segment data (remove placeholder rows)
    - [ ] Metrics and KPIs updated with actual values
    - [ ] CSS variables set for visual elements (--v: 0-100 for bars, --x/--y: 0-100 for positioning)
    - [ ] Citations added for all factual claims
    - [ ] Missing data explicitly acknowledged where applicable
    - [ ] Professional tone maintained throughout
    - [ ] Strategic insights provided in each section

    Generate the complete HTML report using the template above with all placeholders filled with actual research data.

"""