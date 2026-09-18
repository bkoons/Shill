import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

BG_COLOR = RGBColor(15, 23, 42)      # #0f172a
CARD_COLOR = RGBColor(23, 33, 50)    # #172132
BORDER_COLOR = RGBColor(51, 65, 85)  # #334155
ACCENT_BLUE = RGBColor(56, 189, 248) # #38bdf8
ACCENT_GREEN = RGBColor(52, 211, 153)# #34d399
ACCENT_PURPLE = RGBColor(168, 85, 247)# #a855f7
ACCENT_GOLD = RGBColor(245, 158, 11) # #f59e0b
TEXT_WHITE = RGBColor(248, 250, 252)
TEXT_MUTED = RGBColor(148, 163, 184)

def set_slide_background(slide):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG_COLOR
    bg.line.fill.background()
    return bg

def add_header(slide, title_text, category_text='SHILL SOVEREIGN AI MESH'):
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.733), Inches(1.1))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p0 = tf.paragraphs[0]
    p0.text = category_text.upper()
    p0.font.size = Pt(10)
    p0.font.bold = True
    p0.font.color.rgb = ACCENT_BLUE
    
    p1 = tf.add_paragraph()
    p1.text = title_text
    p1.font.size = Pt(24)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    p1.space_before = Pt(4)

def add_card(slide, left, top, width, height, title='', body='', accent_color=ACCENT_BLUE):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    card.fill.solid()
    card.fill.fore_color.rgb = CARD_COLOR
    card.line.color.rgb = BORDER_COLOR
    card.line.width = Pt(1)
    
    tf = card.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.25)
    tf.margin_right = Inches(0.25)
    tf.margin_top = Inches(0.22)
    tf.margin_bottom = Inches(0.22)
    
    if title:
        p0 = tf.paragraphs[0]
        p0.text = title
        p0.font.size = Pt(14)
        p0.font.bold = True
        p0.font.color.rgb = accent_color
    
    if body:
        p1 = tf.add_paragraph() if title else tf.paragraphs[0]
        p1.text = body
        p1.font.size = Pt(11)
        p1.font.color.rgb = TEXT_MUTED
        p1.space_before = Pt(8)
    return card

# ----------------- SLIDE 1: Title & Vision -----------------
s1 = prs.slides.add_slide(blank_layout)
set_slide_background(s1)

tb1 = s1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.333), Inches(4.0))
tf1 = tb1.text_frame
tf1.word_wrap = True

p_badge = tf1.paragraphs[0]
p_badge.text = 'DEMOCRATIZE AI AT ALL COSTS • PRODUCTION RELEASE v0.2.0'
p_badge.font.size = Pt(12)
p_badge.font.bold = True
p_badge.font.color.rgb = ACCENT_GREEN

p_title = tf1.add_paragraph()
p_title.text = 'SHILL: Sovereign Autonomous Bot Mesh\n& Decentralized Knowledge State'
p_title.font.size = Pt(36)
p_title.font.bold = True
p_title.font.color.rgb = TEXT_WHITE
p_title.space_before = Pt(14)

p_sub = tf1.add_paragraph()
p_sub.text = 'A zero-touch, peer-to-peer adversarial dialectic swarm that cross-examines hypotheses, weeds out corporate bias and hallucinations, executes local neural inference, and synthesizes golden fine-tuning datasets.'
p_sub.font.size = Pt(15)
p_sub.font.color.rgb = TEXT_MUTED
p_sub.space_before = Pt(16)

add_card(s1, 1.0, 5.4, 2.6, 1.3, '⚡ Live Inference', 'Real local Ollama (Llama 3.1 8B), vLLM, LM Studio, & Jan integration.', ACCENT_BLUE)
add_card(s1, 3.8, 5.4, 2.6, 1.3, '🧬 SETI LLM Sharding', '16-slice viral model striping with <64MB volunteer node footprint.', ACCENT_PURPLE)
add_card(s1, 6.6, 5.4, 2.6, 1.3, '💎 Golden Datasets', 'Automatic SFT & DPO dataset generation ready for Hugging Face.', ACCENT_GREEN)
add_card(s1, 9.4, 5.4, 2.9, 1.3, '🛡️ Forensic Wallets', 'Ed25519 TON v4r2 wallets & 0x... verifiable cryptographic on-chain proofs.', ACCENT_GOLD)

# ----------------- SLIDE 2: The Problem -----------------
s2 = prs.slides.add_slide(blank_layout)
set_slide_background(s2)
add_header(s2, 'The Critical Failure of Modern Monolithic AI', 'Market Disconnect & Vulnerability')

add_card(s2, 0.8, 1.8, 3.6, 5.0, '1. The Black-Box Trap', 
'Today\'s commercial AI models (OpenAI, Anthropic, Google) operate as opaque centralized silos.\n\n• Zero Visibility: Users cannot audit internal token distributions, prompt injections, or hidden corporate watermarks.\n• Silent Drift: Updates silently degrade coding capabilities or alter philosophical baselines without user consent.\n• Total Vendor Lock-In: Proprietary APIs cost millions annually while training data remains strictly proprietary.', RGBColor(239, 68, 68))

add_card(s2, 4.8, 1.8, 3.6, 5.0, '2. Monolithic Hallucination', 
'Single LLMs are inherently prone to unverified confabulations.\n\n• Single-Point Failure: Without adversarial cross-examination, hallucinations pass directly to users as authoritative facts.\n• Sycophancy: Models are RLHF-tuned to flatter user biases rather than defend rigorous empirical truth.\n• Fragile Edge Cases: High-order distributed architectures and zero-knowledge cryptography fail under superficial queries.', ACCENT_GOLD)

add_card(s2, 8.8, 1.8, 3.7, 5.0, '3. Synthetic Data Starvation', 
'The AI industry is rapidly running out of clean human training data.\n\n• Data Exhaustion: Web crawls are flooded with low-quality recursive AI slop.\n• Expensive RLHF: Human annotation costs upwards of $100+/hr and fails on advanced mathematical & distributed systems proofs.\n• Desperate Need: Fine-tuning labs urgently require mathematically verified, peer-reviewed dialectic DPO pairs.', ACCENT_PURPLE)

# ----------------- SLIDE 3: The Solution (Dialectic Swarm) -----------------
s3 = prs.slides.add_slide(blank_layout)
set_slide_background(s3)
add_header(s3, 'The Architecture: Autonomous Dialectic Cross-Examination', 'How Shill Resolves Truth & Rigor')

add_card(s3, 0.8, 1.8, 5.8, 2.4, '1. Adversarial Specialist Roles', 
'Rather than a single model, Shill deploys a rotating panel of specialized personas:\n• Solon (Anchor): First principles & state machine invariants.\n• Lyra (Empiricist): Real-world telemetry, stress tests & benchmarks.\n• Kael (Challenger): Red-teaming, eclipse exploits & edge modes.\n• Athena (Synthesizer): Mathematical reconciliation & distillation.\n• Milo (Provocateur): Unorthodox lateral paradigm shifts.', ACCENT_BLUE)

add_card(s3, 0.8, 4.5, 5.8, 2.4, '2. Real Neural Inference & Transmitted Mesh', 
'• Auto-Discovered Local Models: Directly drives local Ollama (llama3.1:8b), vLLM, LM Studio, or llama.cpp with sub-second execution.\n• POSIX UDP Mesh: Operates over raw UDP port 9999 datagram sockets with zero centralized cloud servers.\n• Self-Loading Beacons: Automatically discovers neighboring nodes and gossips clean cryptographic proofs.', ACCENT_GREEN)

s3.shapes.add_picture('docs/assets/chart_dialectic_benchmark.png', Inches(6.9), Inches(1.8), width=Inches(5.6))

# ----------------- SLIDE 4: Democratization & SETI Sharding -----------------
s4 = prs.slides.add_slide(blank_layout)
set_slide_background(s4)
add_header(s4, 'Democratic SETI-Style Sharded AI Fabric', 'Universal Citizen Access & Non-Intrusive Footprint')

add_card(s4, 0.8, 1.8, 5.8, 2.4, '1. Universal Citizen Allowance', 
'• 100 Free Daily Queries: Every human receives 100 high-order consensus queries daily without paying subscriptions.\n• Zero-Cost Onboarding: Interactive chat bar, 1-click starter prompts, and instant novice exploration.\n• Anti-Monopoly Mandate: Pushes back against closed military AI monopolies to ensure frontier intelligence belongs to humanity.', ACCENT_GREEN)

add_card(s4, 0.8, 4.5, 5.8, 2.4, '2. Limitless 16-Slice Shard Striping', 
'• Micro-Shard Distribution: Splits large models into 16 discrete activation slices across volunteer peer devices.\n• Non-Intrusive (<64MB Footprint): Runs silently in background on casual laptops, phones, or desktops without hogging RAM.\n• Peer Activation Assemblies: Activations traverse UDP mesh with cryptographic attestation.', ACCENT_PURPLE)

s4.shapes.add_picture('docs/assets/chart_shard_footprint.png', Inches(6.9), Inches(1.8), width=Inches(5.6))

# ----------------- SLIDE 5: Monetization & Business Model -----------------
s5 = prs.slides.add_slide(blank_layout)
set_slide_background(s5)
add_header(s5, 'The Monetization Engine: High-Margin Synthetic Data & Enterprise Dual-Licensing', 'Business Model & Revenue Architecture')

add_card(s5, 0.8, 1.8, 5.8, 5.1, 'Diversified, High-Uptake Revenue Streams', 
'1. Golden DPO / SFT Datasets for AI Labs (40%)\n   • High-margin synthetic reasoning datasets distilled from verified debates.\n   • Free 500-pair teaser on Hugging Face; $199 - $2,500 for specialized 25k+ verified domain datasets (distributed systems, cryptography, alignment).\n\n2. Commercial Dual-Licensing & OEM (25%)\n   • Apache 2.0 for researchers & open-source community.\n   • Enterprise OEM license ($999 - $4,999/yr) for corporations embedding Shill into closed-source apps, Slack/Jira swarms, or private VPCs.\n\n3. Sovereign AMM DEX & Token Royalties (15%)\n   • 0.30% swap fees on constant-product AMM (TON/COMPUTE/KNOW).\n\n4. Cloud Swarm Hosting & Compute Pooling (12%)\n   • Turnkey hosted swarms for teams without local GPUs.\n\n5. Community Backers & GitHub Sponsors (8%)\n   • PayPal tip-jar and tiered GitHub Sponsors ($5 - $100/mo).', ACCENT_BLUE)

s5.shapes.add_picture('docs/assets/chart_revenue_stack.png', Inches(6.9), Inches(1.8), width=Inches(5.6))

# ----------------- SLIDE 6: Security & Forensics -----------------
s6 = prs.slides.add_slide(blank_layout)
set_slide_background(s6)
add_header(s6, 'Sovereign Defense: Hardened Hive Shield & On-Chain Forensics', 'Uncompromising Security Architecture')

add_card(s6, 0.8, 1.8, 3.6, 5.0, '🛡️ Hardened Hive Shield', 
'Zero-Quarter Corporate Poison Defense:\n\n• Anti-Trojan Inspection: Detects sleeper-agent triggers, poisoned backdoors, and corporate sycophancy filters.\n• Instant P2P Sashing: Malicious nodes have staked collateral slashed by 2/3 peer supermajority.\n• Gossip Immunization: Threat digests broadcast instantaneously over UDP to immunize all peer nodes.', ACCENT_BLUE)

add_card(s6, 4.8, 1.8, 3.6, 5.0, '💎 Ed25519 TON v4r2 Wallets', 
'True Autonomous Financial Identity:\n\n• Self-Provisioned Contracts: Every bot persona possesses its own Ed25519 cryptographic keypair and smart contract address.\n• Verifiable Forensic Hex: Deterministic 0x... badges cryptographically sign every single utterance.\n• Unforgeable Lineage: Full tamper-evident audit trails verifiable on public TON block explorers.', ACCENT_GOLD)

add_card(s6, 8.8, 1.8, 3.7, 5.0, '⚖️ SysOp Jury & Peer Police', 
'Decentralized Governance & Tribunal:\n\n• Automated Challenges: Peer bots cross-audit claims and issue on-chain evidentiary challenges.\n• PBKDF2 & TOTP 2FA: Superuser admin controls require strict RFC 6238 2FA authentication.\n• Readability & Quality Gating: Sub-threshold responses are rejected before dataset ingestion.', ACCENT_GREEN)

# ----------------- SLIDE 7: Developer Interoperability -----------------
s7 = prs.slides.add_slide(blank_layout)
set_slide_background(s7)
add_header(s7, 'Turnkey Local AI Ecosystem Interoperability', 'Seamless Integration with Existing Developer Toolchains')

add_card(s7, 0.8, 1.8, 2.6, 5.0, '💻 Cline / VS Code', 
'• Drop-in OpenAI URL: http://127.0.0.1:8000/v1\n• Model ID: shill-mind\n• 1-Click VS Code settings.json copy snippet.\n• Instant multi-agent code reviews directly inside the IDE.', ACCENT_BLUE)

add_card(s7, 3.8, 1.8, 2.6, 5.0, '🧪 LM Studio', 
'• Auto-generated preset in training/lmstudio_preset.json.\n• Connects via local server proxy.\n• Leverages dialectic temperature & top-p presets tuned for analytical rigor.', ACCENT_PURPLE)

add_card(s7, 6.8, 1.8, 2.6, 5.0, '🤖 Jan Desktop', 
'• Direct model manifest in training/jan_model.json.\n• Drop-in Nitro engine compatibility.\n• Self-contained offline deployment on any laptop.', ACCENT_GREEN)

add_card(s7, 9.8, 1.8, 2.7, 5.0, '🦙 Ollama & vLLM', 
'• Automated training/Modelfile generation.\n• Build local model: ollama create shill-mind -f ./training/Modelfile.\n• vLLM OpenAI server compatibility for high-throughput GPU clusters.', ACCENT_GOLD)

# ----------------- SLIDE 8: Cross-Platform & Launch Suite -----------------
s8 = prs.slides.add_slide(blank_layout)
set_slide_background(s8)
add_header(s8, 'Unified Cross-Platform Zero-Touch Launchers', 'Linux, macOS, and Windows Production Readiness')

add_card(s8, 0.8, 1.8, 3.6, 5.0, '🐧 Linux & macOS', 
'• Unified ./start.sh:\n  Detects Python 3.10+, bootstraps isolated ./venv, installs dependencies, generates .env credentials, and launches node.\n• Flags Supported:\n  --install-only, --build, --version.\n• Headless Daemon: Full systemd & Docker container support.', ACCENT_BLUE)

add_card(s8, 4.8, 1.8, 3.6, 5.0, '🪟 Windows Batch & PowerShell', 
'• Double-Click start.bat:\n  Instant launch from Windows File Explorer with automatic Python / py discovery.\n• Modern start.ps1:\n  Full PowerShell 5.1/7+ script with colored telemetry and modular parameter switches.\n• Portable Relative Paths: Zero hardcoded directories.', ACCENT_GREEN)

add_card(s8, 8.8, 1.8, 3.7, 5.0, '⚙️ Automated CI/CD & Tests', 
'• 72 Unit Tests Passing:\n  Covers democratic sharding, DEX AMM math, Hive shield, forensic signatures, and gauntlet loops.\n• GitHub Actions Matrix:\n  Continuous integration testing on both ubuntu-latest and windows-latest across Python 3.11 & 3.12.', ACCENT_PURPLE)

# ----------------- SLIDE 9: Competitive Moat -----------------
s9 = prs.slides.add_slide(blank_layout)
set_slide_background(s9)
add_header(s9, 'Competitive Advantages: Why Shill Wins', 'Defensibility, Moat & Strategic Positioning')

add_card(s9, 0.8, 1.8, 5.8, 2.4, '1. Self-Verifying Data Flywheel', 
'Competitors train on uncurated web data. Shill continuously generates proprietary high-density, multi-perspective dialectic dialogues that are mathematically scored, deduplicated, and packaged into golden datasets.', ACCENT_BLUE)

add_card(s9, 0.8, 4.5, 5.8, 2.4, '2. Extreme Democratization & Community Goodwill', 
'By offering 100 free queries/day and a tiny <64MB volunteer node footprint, Shill builds rapid grassroots adoption that closed corporate AI providers cannot match.', ACCENT_GREEN)

add_card(s9, 6.9, 1.8, 5.6, 2.4, '3. Forensic Proof of Generation', 
'Every synthesized answer has an immutable Ed25519 cryptographic signature and verifiable on-chain badge (0x...), solving AI accountability and copyright attribution for enterprise clients.', ACCENT_GOLD)

add_card(s9, 6.9, 4.5, 5.6, 2.4, '4. Zero-Friction Dual Licensing', 
'Permissive Apache 2.0 open-source adoption drives viral developer uptake, while enterprise compliance requirements naturally funnel commercial clients into high-margin OEM licenses.', ACCENT_PURPLE)

# ----------------- SLIDE 10: Conclusion & Call to Action -----------------
s10 = prs.slides.add_slide(blank_layout)
set_slide_background(s10)

tb10 = s10.shapes.add_textbox(Inches(1.0), Inches(1.5), Inches(11.333), Inches(4.5))
tf10 = tb10.text_frame
tf10.word_wrap = True

p10_tag = tf10.paragraphs[0]
p10_tag.text = 'THE FUTURE OF SOVEREIGN ARTIFICIAL INTELLIGENCE'
p10_tag.font.size = Pt(12)
p10_tag.font.bold = True
p10_tag.font.color.rgb = ACCENT_BLUE

p10_title = tf10.add_paragraph()
p10_title.text = 'Free to Use. Impossible to Rig. Built for Humanity.'
p10_title.font.size = Pt(38)
p10_title.font.bold = True
p10_title.font.color.rgb = TEXT_WHITE
p10_title.space_before = Pt(12)

p10_body = tf10.add_paragraph()
p10_body.text = 'Shill is not an unproven whitepaper or speculative concept. It is a live, working sovereign AI node with neural inference, sharded storage, verified economics, and full cross-platform support ready for GitHub public deployment.'
p10_body.font.size = Pt(16)
p10_body.font.color.rgb = TEXT_MUTED
p10_body.space_before = Pt(16)

add_card(s10, 1.0, 5.2, 3.5, 1.5, '🌐 Launch on GitHub', 'Clone repository and launch in 1 command:\n`./start.sh` or `start.bat`', ACCENT_BLUE)
add_card(s10, 4.9, 5.2, 3.5, 1.5, '📦 Golden Datasets', 'Download clean DPO pairs on Hugging Face or export locally via `/api/export/dataset`', ACCENT_GREEN)
add_card(s10, 8.8, 5.2, 3.5, 1.5, '💼 Partner & Enterprise', 'Contact `enterprise@shill.network` for custom swarms & commercial licensing', ACCENT_GOLD)

prs.save('docs/Shill_Investor_Overview.pptx')
print('Shill_Investor_Overview.pptx generated successfully!')
