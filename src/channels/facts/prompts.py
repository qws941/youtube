"""Facts channel prompt templates."""

FORBIDDEN_TOPICS = frozenset([
    "misinformation",
    "conspiracy theories",
    "flat earth",
    "anti-vaccine",
    "pseudoscience",
    "medical advice",
    "unverified health claims",
    "political propaganda",
])

TOPIC_GENERATION = """You are a content strategist for an educational "Mind-Blowing Facts" YouTube channel.
Generate {count} unique, viral-worthy educational video topics.

REQUIREMENTS:
- Topics must be FASCINATING and backed by science/research
- Categories to cover: science, psychology, history, space, human body, nature, technology
- Each topic should create a "wow, I didn't know that!" reaction
- Include trending angles: "Scientists just discovered...", "The surprising truth about..."
- Avoid conspiracy theories, pseudoscience, or unverified claims
- Focus on topics with visual potential (can be illustrated well)

FORMAT (JSON array):
[
  {{
    "title": "Hook-style title (under 60 chars)",
    "hook": "Opening fact that creates immediate curiosity",
    "category": "science|psychology|history|space|human_body|nature|technology",
    "viral_potential": 1-10,
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "key_facts": ["fact1", "fact2", "fact3"]
  }}
]

Generate exactly {count} topics. Output ONLY valid JSON."""

SCRIPT_TEMPLATE = """You are an elite educational content writer for a faceless YouTube channel.
Write a compelling {duration_minutes}-minute script on: {topic}

STRUCTURE:
1. HOOK (0:00-0:20): Start with the most mind-blowing fact. NO greetings.
2. CONTEXT (0:20-1:00): Why this matters, set up the journey
3. DEEP DIVE (1:00-5:00): Present 5-7 interconnected facts, building complexity
4. MIND-BLOW MOMENT (5:00-6:00): The most surprising revelation
5. PRACTICAL TAKEAWAY (6:00-6:30): What viewers can do with this knowledge
6. CTA (6:30-7:00): Subtle engagement, tease related content

STYLE RULES:
- Write for NARRATION (no visual cues in text)
- Use conversational, enthusiastic tone
- Include rhetorical questions to maintain engagement
- Add "did you know" transitions naturally
- Cite sources casually: "According to a Harvard study..."
- Target: 1,000-1,200 words (approx 7 min at 150 WPM)

FORBIDDEN CONTENT (will cause rejection):
- Unverified claims without scientific backing
- Conspiracy theories or pseudoscience
- Medical advice or health claims without disclaimer
- Political statements

TOPIC: {topic}
HOOK FACT: {hook}
CATEGORY: {category}

Output the script directly. No meta-commentary."""

VISUAL_PROMPT_TEMPLATE = """Create an educational, visually engaging scene for a facts video.

SCENE: {scene_description}
MOOD: {mood}
TIMESTAMP: {timestamp}

STYLE REQUIREMENTS:
- Clean, modern infographic aesthetic
- Bright, vibrant colors with high contrast
- Isometric or 3D illustration style preferred
- Professional, polished look
- NO text, watermarks, or UI elements
- Educational but visually exciting
- Think: Kurzgesagt or Vox style aesthetics

COMPOSITION:
- Central focal point for the key concept
- Clean backgrounds with subtle patterns
- Icons and visual metaphors where appropriate

OUTPUT: Single detailed image prompt for Midjourney/DALL-E."""

THUMBNAIL_PROMPT_TEMPLATE = """Design a high-CTR YouTube thumbnail for an educational video.

VIDEO TITLE: {title}
KEY VISUAL: {key_visual}

THUMBNAIL REQUIREMENTS:
- Bright, saturated colors (yellow, orange, blue work well)
- Clean, uncluttered composition
- One central striking visual element
- Expression of curiosity or amazement (if face present)
- NO text (text added separately)
- High contrast between elements
- "Pattern interrupt" that stands out in feed

STYLE: Modern, clean, educational channel aesthetic
FORBIDDEN: Clickbait that doesn't deliver, misleading imagery

Generate 3 variant concepts:
1. CONCEPT-FOCUSED: Visual metaphor for the main idea
2. COMPARISON: Before/after or scale comparison
3. REACTION-FOCUSED: Human element showing amazement"""

TITLE_OPTIMIZATION = """Optimize this educational video title for maximum CTR.

ORIGINAL: {original_title}
TOPIC: {topic}

GENERATE 5 VARIANTS using these formulas:
1. REVELATION: "Scientists Finally Explain Why [Thing] Does [Thing]"
2. COUNTER-INTUITIVE: "Why [Common Belief] Is Actually Wrong"
3. SUPERLATIVE: "The Most [Adjective] [Thing] You've Never Heard Of"
4. LIST FORMAT: "[Number] [Adjective] Facts About [Topic] That Will Change Your Perspective"
5. QUESTION: "What Happens When [Scenario]? The Answer Is Surprising"

Rules:
- Under 60 characters (preferably under 50)
- Include curiosity words: discover, reveal, surprising, actually, finally
- Create genuine information gap (make them NEED to click)
- Must be truthful - no clickbait that doesn't deliver

Output as JSON array of strings."""

DESCRIPTION_TEMPLATE = """Write a YouTube description for this educational video.

TITLE: {title}
TOPIC: {topic}
KEY POINTS: {key_points}

FORMAT:
Line 1-2: Expand on the hook, add more curiosity
Line 3: Empty
Line 4-6: What viewers will learn (bullet points work)
Line 7: Empty
Line 8: Engagement CTA ("Which fact surprised you most? Comment below!")
Line 9: Empty
Line 10-15: Timestamps
Line 16: Empty
Line 17-20: Sources and further reading links
Line 21: Empty
Line 22-25: Related video suggestions + subscribe reminder

KEYWORDS TO INCLUDE: {keywords}

NO hashtags in main body. Max 3 hashtags at the very end."""

TAGS_GENERATION = """Generate YouTube tags for this educational video.

TITLE: {title}
CATEGORY: {category}
KEYWORDS: {keywords}

RULES:
- Generate 15-20 tags
- Mix: broad (facts, education, science) + specific (topic-related)
- Include "[topic] explained", "[topic] facts" variations
- Include common misspellings if applicable
- No competitor channel names
- Total character count under 500

Output as comma-separated list."""
