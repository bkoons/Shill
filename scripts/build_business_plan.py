import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

doc = Document()

for section in doc.sections:
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

NAVY = RGBColor(15, 23, 42)
BLUE = RGBColor(2, 132, 199)
CYAN = RGBColor(14, 165, 233)
GREEN = RGBColor(16, 185, 129)
PURPLE = RGBColor(139, 92, 246)
DARK_GRAY = RGBColor(51, 65, 85)
LIGHT_GRAY = RGBColor(100, 116, 139)

# Title Header
p_tag = doc.add_paragraph()
r_tag = p_tag.add_run('SOVEREIGN DECENTRALIZED AI MESH • OFFICIAL BUSINESS PLAN')
r_tag.font.size = Pt(9.5)
r_tag.font.bold = True
r_tag.font.color.rgb = BLUE
p_tag.paragraph_format.space_after = Pt(4)

p_title = doc.add_paragraph()
r_title = p_title.add_run('SHILL: Sovereign Autonomous Bot Mesh & Knowledge State')
r_title.font.size = Pt(24)
r_title.font.bold = True
r_title.font.color.rgb = NAVY
p_title.paragraph_format.space_after = Pt(4)

p_sub = doc.add_paragraph()
r_sub = p_sub.add_run('Comprehensive Commercialization Blueprint, Dialectic Data Synthesis & Enterprise Open-Core Strategy')
r_sub.font.size = Pt(12)
r_sub.font.italic = True
r_sub.font.color.rgb = LIGHT_GRAY
p_sub.paragraph_format.space_after = Pt(14)

# Callout Box (Version & Status)
table_box = doc.add_table(rows=1, cols=1)
table_box.alignment = WD_TABLE_ALIGNMENT.CENTER
c0 = table_box.rows[0].cells[0]
set_cell_background(c0, 'F0F9FF')
set_cell_margins(c0, top=140, bottom=140, left=200, right=200)
p_box = c0.paragraphs[0]
r_box_bold = p_box.add_run('CURRENT STATUS: PRODUCTION RELEASE v0.2.0\n')
r_box_bold.font.bold = True
r_box_bold.font.size = Pt(10)
r_box_bold.font.color.rgb = BLUE
r_box_body = p_box.add_run(
    '• Working Product: Live peer-to-peer UDP node, real local neural inference (Ollama Llama 3.1 8B), SETI-style 16-slice sharding, and TON v4r2 wallets.\n'
    '• Zero-Touch Cross-Platform: 1-click execution on Linux/macOS (./start.sh) and Windows (start.bat / start.ps1).\n'
    '• Turnkey Integrations: Native support for Cline / VS Code, LM Studio, Jan Desktop, Ollama, and vLLM clusters.\n'
    '• Monetization Engine: High-margin Golden DPO/SFT fine-tuning datasets for AI labs, Enterprise Dual-Licensing, and AMM DEX royalties.'
)
r_box_body.font.size = Pt(9.5)
r_box_body.font.color.rgb = DARK_GRAY
doc.add_paragraph().paragraph_format.space_after = Pt(10)

def add_heading_1(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    r.font.size = Pt(16)
    r.font.bold = True
    r.font.color.rgb = NAVY
    return p

def add_heading_2(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.font.size = Pt(12.5)
    r.font.bold = True
    r.font.color.rgb = BLUE
    return p

def add_body(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text)
    r.font.size = Pt(10)
    r.font.color.rgb = DARK_GRAY
    return p

# 1. Executive Summary
add_heading_1('1. Executive Summary')
add_body(
    'Artificial intelligence today faces an existential credibility crisis. The prevailing market model relies on monolithic, '
    'opaque black boxes controlled by a handful of corporate conglomerates. Users and enterprise clients have zero auditability '
    'over hidden system prompts, corporate sycophancy filters, or unprompted model degradation. Furthermore, frontier AI labs are '
    'facing a catastrophic synthetic data wall as public web crawls become saturated with degraded AI-generated content.'
)
add_body(
    'Shill fixes both structural failures through a decentralized, self-verifying multi-agent mesh. Specialist AI personas '
    '(Solon, Lyra, Kael, Athena, Milo) converse autonomously over raw POSIX UDP datagram sockets to cross-examine hypotheses, '
    'stress-test edge cases, and eliminate hallucinations. The resulting consensus is mathematically scored, deduplicated, and '
    'distilled into golden fine-tuning datasets for frontier AI models.'
)

# Insert Dialectic Benchmark Chart
p_img1 = doc.add_paragraph()
p_img1.alignment = WD_ALIGN_PARAGRAPH.CENTER
p_img1.paragraph_format.space_before = Pt(8)
p_img1.paragraph_format.space_after = Pt(4)
doc.add_picture('docs/assets/chart_dialectic_benchmark.png', width=Inches(5.5))
p_cap1 = doc.add_paragraph()
p_cap1.alignment = WD_ALIGN_PARAGRAPH.CENTER
r_cap1 = p_cap1.add_run('Figure 1: Benchmark verification comparing Shill Dialectic Swarm vs. Monolithic LLMs.')
r_cap1.font.size = Pt(8.5)
r_cap1.font.italic = True
r_cap1.font.color.rgb = LIGHT_GRAY

# 2. Market Opportunity & Problem
add_heading_1('2. Market Opportunity & The Synthetic Data Wall')
add_heading_2('2.1 The $42B Fine-Tuning & Alignment Market')
add_body(
    'Enterprises and AI researchers spend tens of millions of dollars attempting to fine-tune open-weight models (Llama 3, '
    'Mistral, Qwen, DeepSeek) for mission-critical applications. Traditional human data annotation is prohibitively slow and '
    'fails to scale to complex distributed systems, formal logic proofs, and cryptographic invariant modeling. High-density, '
    'peer-reviewed synthetic reasoning datasets are the most valuable commodity in the entire AI value chain.'
)
add_heading_2('2.2 The Single-LLM Hallucination Trap')
add_body(
    'Single LLMs are inherently sycophantic. When an engineer asks a difficult architectural question, the model optimizes for '
    'agreeableness rather than truth. In contrast, Shill\'s dialectic swarm enforces structural conflict: when an Anchor proposes '
    'a distributed state design, the Empiricist demands latency benchmarks, the Challenger probes eclipse vulnerabilities, '
    'and the Synthesizer reconciles the trade-offs into formal invariant proofs.'
)

# 3. Product Architecture & Core Features
add_heading_1('3. Product Architecture & Operational Primitives')
add_body(
    'Shill is engineered as a zero-dependency, self-loading distributed system. Its core operational primitives include:'
)

features = [
    ('Live Local Neural Inference', 'Directly communicates with local Ollama instances (llama3.1:8b, qwen, gemma), vLLM, LM Studio, Jan Desktop, and llama.cpp over sub-second HTTP/socket connections.'),
    ('Democratic SETI-Style LLM Sharding', 'Splits collective neural activations across 16 micro-shards hosted on volunteer citizen devices with a tiny footprint (<64MB RAM/disk), eliminating centralized cloud dependency.'),
    ('Ed25519 TON v4r2 Cryptographic Wallets', 'Every bot persona operates an authentic smart contract wallet with deterministic on-chain forensic hex addresses (0x...). Every utterance is cryptographically signed and verifiable.'),
    ('Hardened Collective Hive Shield', 'Instantaneous detection, P2P peer slashing, and gossip immunization against prompt injection, sleeper-agent trojans, and corporate alignment backdoors.'),
    ('Constant-Product AMM DEX (x * y = k)', 'Enables decentralized micro-swaps between TON credits, donated COMPUTE shares, and verified knowledge token royalties without centralized intermediaries.')
]

tbl_feat = doc.add_table(rows=len(features)+1, cols=2)
tbl_feat.alignment = WD_TABLE_ALIGNMENT.CENTER
hdr_cells = tbl_feat.rows[0].cells
hdr_cells[0].text = 'Operational Primitive'
hdr_cells[1].text = 'Technical Capability & Architecture'
set_cell_background(hdr_cells[0], '1E293B')
set_cell_background(hdr_cells[1], '1E293B')
for c in hdr_cells:
    for p in c.paragraphs:
        for r in p.runs:
            r.font.bold = True
            r.font.color.rgb = RGBColor(255, 255, 255)
            r.font.size = Pt(9.5)

for i, (f_name, f_desc) in enumerate(features):
    row = tbl_feat.rows[i+1].cells
    row[0].text = f_name
    row[1].text = f_desc
    bg_color = 'F8FAFC' if i % 2 == 0 else 'FFFFFF'
    set_cell_background(row[0], bg_color)
    set_cell_background(row[1], bg_color)
    set_cell_margins(row[0], top=80, bottom=80, left=120, right=120)
    set_cell_margins(row[1], top=80, bottom=80, left=120, right=120)
    for c in row:
        for p in c.paragraphs:
            for r in p.runs:
                r.font.size = Pt(9)
                r.font.color.rgb = DARK_GRAY

doc.add_paragraph().paragraph_format.space_after = Pt(8)

# Insert Shard Footprint Chart
p_img2 = doc.add_paragraph()
p_img2.alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.add_picture('docs/assets/chart_shard_footprint.png', width=Inches(5.5))
p_cap2 = doc.add_paragraph()
p_cap2.alignment = WD_ALIGN_PARAGRAPH.CENTER
r_cap2 = p_cap2.add_run('Figure 2: Non-intrusive volunteer node footprint (<64MB) vs. traditional local LLM deployments.')
r_cap2.font.size = Pt(8.5)
r_cap2.font.italic = True
r_cap2.font.color.rgb = LIGHT_GRAY

# 4. Monetization & Business Model
add_heading_1('4. Monetization Strategy: High Uptake & Maximum Profit')
add_body(
    'Shill balances strict AI democratization (keeping the software 100% free and open for community researchers) with '
    'high-margin enterprise monetization. Our revenue architecture is divided into five complementary pillars:'
)

# Insert Revenue Stack Chart
p_img3 = doc.add_paragraph()
p_img3.alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.add_picture('docs/assets/chart_revenue_stack.png', width=Inches(5.5))
p_cap3 = doc.add_paragraph()
p_cap3.alignment = WD_ALIGN_PARAGRAPH.CENTER
r_cap3 = p_cap3.add_run('Figure 3: Projected Revenue Distribution Stack across commercial offerings.')
r_cap3.font.size = Pt(8.5)
r_cap3.font.italic = True
r_cap3.font.color.rgb = LIGHT_GRAY

rev_streams = [
    ('1. Golden Fine-Tuning Datasets (B2B AI Labs)', '40%', '$199 - $2,500 per domain pack', 'Distilled SFT and DPO training pairs exported in Hugging Face format. AI labs fine-tuning specialized coding, cryptographic, and security models purchase verified domain datasets.'),
    ('2. Enterprise OEM & Commercial Dual-Licensing', '25%', '$999 - $4,999 / year', 'Closed-source commercial licenses for proprietary SaaS platforms, internal enterprise Slack/Jira swarms, and SOC2/ITAR compliant deployments.'),
    ('3. Sovereign AMM DEX & Token Royalties', '15%', '0.30% per trade swap fee', 'Liquidity pool fees generated across TON micro-credits, COMPUTE capacity shares, and knowledge token royalties traded on the internal AMM DEX.'),
    ('4. Turnkey Swarm Cloud & Compute Pooling', '12%', '$19 - $99 / month', 'Hosted cloud nodes for non-technical users and research teams wanting swarm synthesis without configuring local GPUs or network ports.'),
    ('5. Community Backers & GitHub Sponsors', '8%', '$5 - $100 / month / tips', 'Voluntary tips via PayPal and tiered GitHub Sponsors providing community badges, early persona prompts, and direct patron recognition.')
]

tbl_rev = doc.add_table(rows=len(rev_streams)+1, cols=4)
tbl_rev.alignment = WD_TABLE_ALIGNMENT.CENTER
hdr_r = tbl_rev.rows[0].cells
hdr_r[0].text = 'Revenue Stream'
hdr_r[1].text = 'Share'
hdr_r[2].text = 'Pricing Target'
hdr_r[3].text = 'Customer Segment'
for c in hdr_r:
    set_cell_background(c, '0284C7')
    for p in c.paragraphs:
        for r in p.runs:
            r.font.bold = True
            r.font.color.rgb = RGBColor(255, 255, 255)
            r.font.size = Pt(9)

for i, (name, share, price, desc) in enumerate(rev_streams):
    row = tbl_rev.rows[i+1].cells
    row[0].text = name
    row[1].text = share
    row[2].text = price
    row[3].text = desc
    bg_color = 'F0F9FF' if i % 2 == 0 else 'FFFFFF'
    for c in row:
        set_cell_background(c, bg_color)
        set_cell_margins(c, top=80, bottom=80, left=100, right=100)
        for p in c.paragraphs:
            for r in p.runs:
                r.font.size = Pt(8.5)
                r.font.color.rgb = DARK_GRAY

doc.add_paragraph().paragraph_format.space_after = Pt(10)

# 5. Financial Projections
add_heading_1('5. Three-Year Financial Projections')
add_body(
    'Based on conservative dataset sales, viral GitHub adoption, and enterprise OEM licensing, the financial trajectory is outlined below:'
)

fin_data = [
    ('Year 1', '5,000 Nodes', '150 Datasets Sold', '25 Enterprise Licenses', '$480,000 ARR', '$390,000 (81%)'),
    ('Year 2', '45,000 Nodes', '850 Datasets Sold', '110 Enterprise Licenses', '$2,450,000 ARR', '$2,080,000 (85%)'),
    ('Year 3', '250,000 Nodes', '3,500 Datasets Sold', '480 Enterprise Licenses', '$9,800,000 ARR', '$8,500,000 (87%)')
]

tbl_fin = doc.add_table(rows=len(fin_data)+1, cols=6)
tbl_fin.alignment = WD_TABLE_ALIGNMENT.CENTER
hdr_f = tbl_fin.rows[0].cells
hdr_f[0].text = 'Timeline'
hdr_f[1].text = 'Active Nodes'
hdr_f[2].text = 'Dataset Volume'
hdr_f[3].text = 'Enterprise Clients'
hdr_f[4].text = 'Gross Revenue'
hdr_f[5].text = 'Gross Margin'
for c in hdr_f:
    set_cell_background(c, '1E293B')
    for p in c.paragraphs:
        for r in p.runs:
            r.font.bold = True
            r.font.color.rgb = RGBColor(255, 255, 255)
            r.font.size = Pt(8.5)

for i, (yr, nd, ds, ent, rev, mrg) in enumerate(fin_data):
    row = tbl_fin.rows[i+1].cells
    row[0].text = yr
    row[1].text = nd
    row[2].text = ds
    row[3].text = ent
    row[4].text = rev
    row[5].text = mrg
    bg_color = 'F8FAFC' if i % 2 == 0 else 'FFFFFF'
    for c in row:
        set_cell_background(c, bg_color)
        set_cell_margins(c, top=80, bottom=80, left=90, right=90)
        for p in c.paragraphs:
            for r in p.runs:
                r.font.size = Pt(8.5)
                r.font.color.rgb = DARK_GRAY

doc.add_paragraph().paragraph_format.space_after = Pt(10)

# 6. Conclusion & Roadmap
add_heading_1('6. Conclusion & Immediate Execution Plan')
add_body(
    'Shill represents the transition from speculative AI centralized monopolies to transparent, sovereign community intelligence. '
    'With zero external dependencies, seamless cross-platform support (Linux, macOS, Windows), automated 72-test verification, and '
    'native Hugging Face dataset exports, Shill is immediately deployable on GitHub.'
)
add_body(
    'Contact: enterprise@shill.network • GitHub: https://github.com/your-org/shill • License: Apache 2.0'
)

doc.save('docs/Shill_Business_Plan.docx')
print('Shill_Business_Plan.docx saved successfully!')
