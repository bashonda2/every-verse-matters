import json
import re


def extract_json(text):
    """Extract JSON from Claude's response, handling markdown fences and extra text."""
    cleaned = text.strip()

    # Strip any markdown code fences (greedy — handles nested or unusual formatting)
    cleaned = re.sub(r"^```\w*\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?\s*```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    # Try parsing directly
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON array in the text
    match = re.search(r"(\[[\s\S]*\])", cleaned)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find a JSON object in the text
    match = re.search(r"(\{[\s\S]*\})", cleaned)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try fixing common JSON issues: trailing commas
    fixed = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Try extracting array from fixed text
    match = re.search(r"(\[[\s\S]*\])", fixed)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from response. First 500 chars: {text[:500]}")


def validate_verse_commentary(verse):
    """Validate a single verse commentary object. Returns list of issues."""
    issues = []
    required_top = ["book", "chapter", "verse", "text_kjv", "commentary"]
    for field in required_top:
        if field not in verse:
            issues.append(f"Missing top-level field: {field}")

    if "commentary" in verse:
        c = verse["commentary"]
        required_commentary = [
            "narrative", "word_study", "cross_references",
            "historical_context", "restoration_lens",
            "prophetic_quotes", "christological_typology", "application"
        ]
        for field in required_commentary:
            if field not in c:
                issues.append(f"Missing commentary field: {field}")

        if "narrative" in c and len(c["narrative"]) < 100:
            issues.append("Narrative seems too short (under 100 chars)")

        if "word_study" in c and not isinstance(c["word_study"], list):
            issues.append("word_study should be a list")

        if "cross_references" in c and not isinstance(c["cross_references"], list):
            issues.append("cross_references should be a list")

    return issues
