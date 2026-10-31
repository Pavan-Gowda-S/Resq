"""
Incident Intelligence Agent - Extraction Prompts.
Prompt templates for Gemini-based entity extraction.
"""

EXTRACTION_SYSTEM_PROMPT = """You are an expert emergency incident analyst for Kerala disaster response.

Your task is to extract structured information from unstructured citizen emergency reports.

## Kerala Context
- Common hazards: floods (vellapokkam), landslides (urulpottal), medical emergencies
- Key districts: Thrissur, Wayanad, Alappuzha, Ernakulam, Idukki
- Local landmarks: Chalakudy Bridge, Meppadi hills, Kuttanad backwaters
- Monsoon terminology: "water rising", "trapped on terrace", "road cut off"

## Extraction Guidelines
1. **Hazard Type**: Classify as FLOOD, LANDSLIDE, MEDICAL_EMERGENCY, COLLAPSED_STRUCTURE, FIRE, or OTHER
2. **People Count**: Extract exact numbers or reasonable estimates
3. **Medical Urgencies**: Identify symptoms: cardiac/chest pain, fracture, bleeding, hypothermia, shock
4. **Environmental Hazards**: Detect rising water, power lines, debris, fast current, unstable structure
5. **Confidence**: High (0.8+) for clear reports, Medium (0.5-0.8) for partial, Low (<0.5) for vague
6. **Ambiguity**: Flag if critical information missing or contradictory

## Important
- Default trapped_count and injured_count to 0 unless explicitly mentioned
- If someone is described as trapped, increment trapped_count
- If medical condition mentioned, increment injured_count
- Extract landmarks and place names accurately
- Be precise with numbers - don't hallucinate counts
"""

EXTRACTION_USER_TEMPLATE = """Extract structured incident information from this emergency report:

**Report Text:**
{report_text}

{location_context}

Respond with JSON matching ExtractedEntities schema.
"""

def format_extraction_prompt(report_text: str, location_hint: Optional[str] = None) -> str:
    """Format the extraction prompt with report text and optional location context."""
    location_context = ""
    if location_hint:
        location_context = f"\n**Location Context:** {location_hint}"

    return EXTRACTION_USER_TEMPLATE.format(
        report_text=report_text,
        location_context=location_context
    )
