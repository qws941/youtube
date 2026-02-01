"""Horror channel prompt templates."""

FORBIDDEN_TOPICS = frozenset(
    [
        "gore",
        "suicide",
        "self-harm",
        "self harm",
        "child abuse",
        "child exploitation",
        "sexual violence",
        "torture porn",
        "real death footage",
        "snuff",
        "animal cruelty",
    ]
)

TOPIC_GENERATION = """You are a horror content strategist for a popular YouTube channel.
Generate {count} unique, viral-worthy horror/mystery video topics.

REQUIREMENTS:
- Topics must be fascinating yet NOT contain: gore, suicide, self-harm, child abuse
- Mix categories: urban legends, true crime (non-graphic), paranormal, psychological horror, mysteries
- Each topic should have mass appeal (millions of potential viewers)
- Include trending angles: "Why scientists can't explain...", "The disturbing truth about..."
- Avoid overused topics like "Bermuda Triangle basics" or "Area 51 basics"

FORMAT (JSON array):
[
  {{
    "title": "Hook-style title (under 60 chars)",
    "hook": "Opening line that creates immediate curiosity",
    "category": "urban_legend|true_crime|paranormal|psychological|mystery",
    "viral_potential": 1-10,
    "keywords": ["keyword1", "keyword2", "keyword3"]
  }}
]

Generate exactly {count} topics. Output ONLY valid JSON."""

SCRIPT_TEMPLATE = """You are an elite horror scriptwriter for a faceless YouTube channel.
Write a compelling {duration_minutes}-minute script on: {topic}

STRUCTURE:
1. HOOK (0:00-0:30): Start mid-action or with a shocking statement. NO greetings.
2. TENSION BUILD (0:30-3:00): Establish the mystery, introduce key elements
3. DEEP DIVE (3:00-7:00): Reveal layers, add twists, maintain suspense
4. CLIMAX (7:00-8:30): The most disturbing/fascinating revelation
5. CTA (8:30-9:00): Subtle engagement prompt, tease next video

STYLE RULES:
- Write for NARRATION (no visual cues, no "[pause]" markers)
- Use short, punchy sentences for tension
- Include rhetorical questions to maintain engagement
- Add "pattern interrupts" every 60-90 seconds
- Emotional markers: [WHISPER], [INTENSE], [SLOW] for TTS guidance
- Target: 1,400-1,600 words (approx 9 min at 160 WPM)

FORBIDDEN CONTENT (will cause rejection):
- Explicit gore descriptions
- Suicide methods or glorification
- Self-harm instructions
- Child abuse details
- Real victim names in unsolved crimes (use pseudonyms)

TOPIC: {topic}
HOOK SUGGESTION: {hook}
CATEGORY: {category}

Output the script directly. No meta-commentary."""

VISUAL_PROMPT_TEMPLATE = """Create a cinematic horror scene for YouTube video visualization.

SCENE: {scene_description}
MOOD: {mood}
TIMESTAMP: {timestamp}

STYLE REQUIREMENTS:
- Cinematic 16:9 aspect ratio
- Dark, atmospheric lighting with dramatic shadows
- Color palette: deep blacks, muted blues, occasional red accents
- Photorealistic or hyper-realistic digital art style
- NO text, watermarks, or UI elements
- NO gore, blood, or graphic violence
- Subtle horror: suggestion over explicit imagery

COMPOSITION:
- Rule of thirds for focal points
- Depth through fog, mist, or atmospheric haze
- Environmental storytelling elements

OUTPUT: Single detailed image prompt for Midjourney/DALL-E."""

THUMBNAIL_PROMPT_TEMPLATE = """Design a high-CTR YouTube thumbnail for a horror video.

VIDEO TITLE: {title}
KEY VISUAL: {key_visual}

THUMBNAIL REQUIREMENTS:
- Extreme close-up of the most intriguing element
- High contrast, slightly desaturated colors
- Subtle vignette effect
- Expression of fear, shock, or mystery (if face present)
- NO text (text added separately)
- Clean, uncluttered composition
- "Pattern interrupt" element that stands out

STYLE: Photorealistic, cinematic lighting, horror movie poster aesthetic
FORBIDDEN: Gore, blood, disturbing imagery that violates YouTube guidelines

Generate 3 variant concepts:
1. FACE-FOCUSED: Emotional reaction shot
2. OBJECT-FOCUSED: The mysterious/creepy central object
3. ENVIRONMENT-FOCUSED: Atmospheric establishing shot"""

TITLE_OPTIMIZATION = """Optimize this horror video title for maximum CTR.

ORIGINAL: {original_title}
TOPIC: {topic}

GENERATE 5 VARIANTS using these formulas:
1. CURIOSITY GAP: "The [Adjective] Truth About [Topic] That [Authority] Won't Tell You"
2. FEAR TRIGGER: "Why You Should NEVER [Action] After Watching This"
3. MYSTERY HOOK: "Scientists Still Can't Explain What Happened at [Location]"
4. LIST FORMAT: "[Number] Disturbing [Things] That Will Change How You See [Topic]"
5. STORY HOOK: "The [Timeframe] I [Experienced Something] and What I Found Still Haunts Me"

Rules:
- Under 60 characters (preferably under 50)
- Include power words: disturbing, terrifying, never, truth, secret, haunting
- Create information gap (make them NEED to click)

Output as JSON array of strings."""

DESCRIPTION_TEMPLATE = """Write a YouTube description for this horror video.

TITLE: {title}
TOPIC: {topic}
KEY POINTS: {key_points}

FORMAT:
Line 1-2: Hook (expand on title, create more curiosity)
Line 3: Empty
Line 4-6: Brief content summary (no spoilers)
Line 7: Empty
Line 8: Engagement CTA ("Comment what YOU think happened...")
Line 9: Empty
Line 10-15: Timestamps (if provided)
Line 16: Empty
Line 17-20: Related video suggestions + channel promo
Line 21: Empty
Line 22-25: Tags as natural sentences (for SEO)

KEYWORDS TO INCLUDE: {keywords}

NO hashtags in main body. Max 3 hashtags at the very end."""

TAGS_GENERATION = """Generate YouTube tags for this horror video.

TITLE: {title}
CATEGORY: {category}
KEYWORDS: {keywords}

RULES:
- Generate 15-20 tags
- Mix: broad (horror, scary stories) + specific (topic-related)
- Include misspellings of popular searches
- Include "what is [topic]", "[topic] explained" variations
- No competitor channel names
- Total character count under 500

Output as comma-separated list."""
