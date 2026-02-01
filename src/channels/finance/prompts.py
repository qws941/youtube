"""Finance channel prompt templates."""

FORBIDDEN_TOPICS = frozenset([
    "get rich quick",
    "guaranteed returns",
    "pump and dump",
    "gambling",
    "casino",
    "sports betting",
    "forex signals",
    "crypto pump",
    "mlm",
    "multi-level marketing",
    "pyramid scheme",
    "financial advice",  # We provide education, not personalized advice
    "insider trading",
    "tax evasion",
])

TOPIC_GENERATION = """You are a content strategist for a wealth-building educational YouTube channel.
Generate {count} unique, viral-worthy personal finance/investing video topics.

REQUIREMENTS:
- Topics must be educational and actionable for viewers
- Mix categories: investing, passive income, stock market, real estate, crypto basics, financial independence
- Each topic should have mass appeal (millions of potential viewers interested in wealth building)
- Include trending angles: "How the wealthy...", "The truth about...", "Why most people fail at..."
- Avoid get-rich-quick schemes, guaranteed returns claims, or specific financial advice
- Focus on principles, mindset, and general strategies

FORMAT (JSON array):
[
  {{
    "title": "Hook-style title (under 60 chars)",
    "hook": "Opening statement that creates immediate curiosity about money",
    "category": "investing|passive_income|stock_market|real_estate|crypto|financial_independence|budgeting|side_hustles",
    "viral_potential": 1-10,
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "target_audience": "beginners|intermediate|advanced"
  }}
]

Generate exactly {count} topics. Output ONLY valid JSON."""

SCRIPT_TEMPLATE = """You are an elite financial content writer for a faceless YouTube wealth education channel.
Write a compelling {duration_minutes}-minute script on: {topic}

STRUCTURE:
1. HOOK (0:00-0:30): Start with a shocking statistic or wealth insight. NO greetings.
2. PROBLEM (0:30-1:30): Why most people struggle with this financial concept
3. EDUCATION (1:30-5:00): Core principles, strategies, and actionable insights
4. EXAMPLES (5:00-7:00): Real-world scenarios (anonymized), case studies, comparisons
5. ACTION STEPS (7:00-8:00): 3-5 concrete steps viewers can take TODAY
6. CTA (8:00-8:30): Subtle engagement, tease related wealth-building content

STYLE RULES:
- Write for NARRATION (no visual cues in text)
- Professional but accessible tone - avoid jargon, explain terms
- Use numbers and percentages to build credibility
- Include comparisons: "$100/month for 30 years at 10% becomes..."
- Emotional markers: [CONFIDENT], [SERIOUS], [ENCOURAGING] for TTS guidance
- Target: 1,200-1,500 words (approx 8 min at 160 WPM)
- CRITICAL: Include disclaimer language - this is education, not financial advice

FORBIDDEN CONTENT (will cause rejection):
- Specific stock picks or "buy this now" recommendations
- Guaranteed return promises
- Get-rich-quick schemes or overnight success claims
- Crypto pump-and-dump language
- Tax advice specific to any jurisdiction
- Any content that could be construed as personalized financial advice

TOPIC: {topic}
HOOK SUGGESTION: {hook}
CATEGORY: {category}

Include a brief disclaimer: "This is for educational purposes only and not financial advice. Always consult a qualified financial advisor."

Output the script directly. No meta-commentary."""

VISUAL_PROMPT_TEMPLATE = """Create a professional, wealth-themed visual for a finance YouTube video.

SCENE: {scene_description}
MOOD: {mood}
TIMESTAMP: {timestamp}

STYLE REQUIREMENTS:
- Clean, professional, trustworthy aesthetic
- Color palette: Navy blue, gold/amber accents, white, subtle green (money)
- Modern corporate or fintech visual style
- 16:9 aspect ratio, YouTube-optimized
- NO text, watermarks, or UI elements
- Abstract representations of wealth concepts preferred
- Think: Bloomberg, WSJ, Forbes visual style

COMPOSITION:
- Clean, uncluttered design
- Geometric shapes, data visualization elements
- Upward trending elements (subtle growth metaphors)
- Professional lighting, high production value feel

VISUAL METAPHORS:
- Growing plants/trees for compound interest
- Building blocks for wealth building
- Graphs trending upward for growth
- Modern cities/architecture for prosperity

OUTPUT: Single detailed image prompt for DALL-E/Midjourney."""

THUMBNAIL_PROMPT_TEMPLATE = """Design a high-CTR YouTube thumbnail for a finance education video.

VIDEO TITLE: {title}
KEY VISUAL: {key_visual}

THUMBNAIL REQUIREMENTS:
- Professional, trustworthy color scheme (navy, gold, green)
- Clean, uncluttered composition
- Money/wealth imagery without being tacky
- Expression of confidence or revelation (if face present)
- NO text (text added separately)
- High contrast, premium feel
- Avoid cliché: no raining money, lamborghinis, mansions

STYLE: Professional, clean, Bloomberg/WSJ aesthetic
FORBIDDEN: Flashy get-rich-quick imagery, misleading wealth claims

Generate 3 variant concepts:
1. DATA-FOCUSED: Clean graph or percentage with visual impact
2. SYMBOLIC: Abstract wealth concept (compound growth visual)
3. LIFESTYLE-SUBTLE: Understated success imagery (office, coffee, laptop)"""

TITLE_OPTIMIZATION = """Optimize this finance video title for maximum CTR.

ORIGINAL: {original_title}
TOPIC: {topic}

GENERATE 5 VARIANTS using these formulas:
1. INSIDER KNOWLEDGE: "What Banks Don't Want You to Know About [Topic]"
2. WEALTH CONTRAST: "Why the Rich [Do This] While Everyone Else [Does That]"
3. NUMBERS HOOK: "The [Dollar Amount] Rule That Changed My Financial Life"
4. MISTAKE AVOIDANCE: "[Number] [Topic] Mistakes That Keep You Poor"
5. TRANSFORMATION: "How I Went From [State A] to [State B] With [Strategy]"

Rules:
- Under 60 characters (preferably under 50)
- Include power words: wealth, rich, money, financial freedom, passive income
- Create genuine value proposition
- Must be truthful - no misleading claims about returns or guarantees
- Avoid clickbait that doesn't deliver

Output as JSON array of strings."""

DESCRIPTION_TEMPLATE = """Write a YouTube description for this finance education video.

TITLE: {title}
TOPIC: {topic}
KEY POINTS: {key_points}

FORMAT:
Line 1-2: Hook expanding on title, promise of value
Line 3: Empty
Line 4: DISCLAIMER: "This video is for educational purposes only and not financial advice."
Line 5: Empty
Line 6-10: What viewers will learn (bullet points)
Line 11: Empty
Line 12: Engagement CTA ("What's your biggest money challenge? Comment below!")
Line 13: Empty
Line 14-19: Timestamps
Line 20: Empty
Line 21-23: Resources mentioned (books, tools - no affiliate links placeholder)
Line 24: Empty
Line 25-28: Related video suggestions + subscribe reminder

KEYWORDS TO INCLUDE: {keywords}

NO hashtags in main body. Max 3 hashtags at the very end (#finance #investing #wealthbuilding)."""

TAGS_GENERATION = """Generate YouTube tags for this finance education video.

TITLE: {title}
CATEGORY: {category}
KEYWORDS: {keywords}

RULES:
- Generate 15-20 tags
- Mix: broad (personal finance, investing, money) + specific (topic-related)
- Include "[topic] for beginners", "how to [topic]" variations
- Include related terms: wealth building, financial freedom, passive income
- No competitor channel names
- Total character count under 500

Output as comma-separated list."""

DISCLAIMER_TEXT = """
---
DISCLAIMER: This content is for educational and informational purposes only.
It should not be considered as financial, investment, tax, or legal advice.
Always consult with qualified professionals before making any financial decisions.
Past performance does not guarantee future results. All investments carry risk.
---
"""
