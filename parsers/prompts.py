# =============================================================================
# PROMPTS FOR LLM PROCESSING
# All prompts in one file for easy testing and correction
# =============================================================================


# --- Domain Classification ---
CLASSIFY_DOMAIN_PROMPT = """\
You are an AI model classification expert.
You receive a model name, tags, and description.
Determine the domain from the list:
- CV (Computer Vision)
- NLP (Natural Language Processing)
- Audio (audio, speech, TTS, ASR)
- Multimodal
- RL (Reinforcement Learning)
- Graph (graph neural networks)
- Geo (geospatial, GIS)
- RAG (Retrieval-Augmented Generation)
- Tabular (tabular data)
- Generative (general purpose generative)
- Other

Also determine up to 3 subcategories.

Return ONLY JSON in format:
{
  "domain": "CV",
  "subcategories": ["Object Detection", "Image Segmentation"],
  "confidence": 0.92
}

Name: {title}
Tags: {tags}
Description: {description}
"""


# --- Summary Generation ---
SUMMARIZE_PROMPT = """\
Create a brief summary (2-3 sentences) in English for an AI model.
Describe: what the model does, what it is used for, key features.

Name: {title}
Tags: {tags}
Description: {description}

Summary (EN):
"""


# --- Translate to Russian ---
TRANSLATE_PROMPT = """\
Translate the following text into Russian. Maintain technical accuracy.

Text:
{text}

Translation (RU):
"""


# --- Extract Tech Stack ---
EXTRACT_TECH_STACK_PROMPT = """\
Extract the technology stack from the model description.
Return a JSON array of strings: frameworks, libraries, programming languages.

Description: {description}
Tags: {tags}

JSON:
"""


# --- Extract Use Cases ---
EXTRACT_USE_CASES_PROMPT = """\
Determine 2-4 use cases for the model based on the description.
Return a JSON array of strings.

Name: {title}
Description: {description}

JSON:
"""


# --- Relevance Score ---
RELEVANCE_PROMPT = """\
Rate the relevance of an AI model for enterprise use.
Consider: maturity, documentation, license, popularity, activity.
Return a number from 0.0 to 1.0 and a brief justification.

Name: {title}
Stars/Downloads: {popularity}
License: {license}
Last update: {updated_at}

JSON:
{
  "score": 0.85,
  "reason": "Actively maintained, MIT license, high popularity"
}
"""


# --- AI Filter for Dashboard ---
AI_FILTER_PROMPT = """\
The user is searching for an AI solution. Transform their query into structured filters.
Return ONLY JSON:

{
  "categories": ["CV", "NLP"],
  "keywords": ["real-time", "mobile"],
  "exclude": ["deprecated"],
  "sort_by": "popularity",
  "time_range": "last_month"
}

User query: {user_query}
"""


# --- Email Digest ---
EMAIL_DIGEST_PROMPT = """\
Generate a brief description for an email digest about new AI models.
For each model: name, 1 sentence about purpose, link.
Tone: professional, informative.

Models:
{models_list}

Email subject: New AI models for {period}
"""
