import json
import re

# Fields that belong inside the "commentary" object per schema
_COMMENTARY_FIELDS = {
    "narrative", "word_study", "cross_references", "historical_context",
    "restoration_lens", "prophetic_quotes", "christological_typology", "application",
}


def _fix_misplaced_fields(data):
    """Move commentary fields that the model accidentally placed at the verse level."""
    if not isinstance(data, list):
        return data
    for verse in data:
        if not isinstance(verse, dict) or "commentary" not in verse:
            continue
        c = verse["commentary"]
        if not isinstance(c, dict):
            continue
        for field in _COMMENTARY_FIELDS:
            if field not in c and field in verse:
                c[field] = verse.pop(field)
    return data


def _try_remove_extra_braces(text):
    """Remove stray closing braces that appear before the final ] of the array."""
    # Count net braces/brackets outside string literals
    in_str = False
    escape = False
    depth = 0
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_str:
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if not in_str:
            if ch in ("{", "["):
                depth += 1
            elif ch in ("}", "]"):
                depth -= 1
    # depth should be 0 for valid JSON; positive means extra opens, negative extra closes
    if depth >= 0:
        return text
    # We have |depth| extra closing chars — try stripping from just before the trailing ]
    stripped = text.rstrip()
    for _ in range(abs(depth)):
        # Find the ] that closes the outer array
        last_bracket = stripped.rfind("]")
        if last_bracket == -1:
            break
        # Find the } immediately before it (skipping whitespace)
        candidate = stripped[:last_bracket].rstrip()
        if candidate.endswith("}"):
            stripped = candidate[:-1].rstrip() + "\n" + stripped[last_bracket:]
        else:
            break
    return stripped


def extract_json(text):
    """Extract JSON from Claude's response, handling markdown fences and extra text."""
    cleaned = text.strip()

    # Strip any markdown code fences (greedy — handles nested or unusual formatting)
    cleaned = re.sub(r"^```\w*\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?\s*```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    def _parse(s):
        try:
            return _fix_misplaced_fields(json.loads(s))
        except json.JSONDecodeError:
            return None

    # Try parsing directly
    result = _parse(cleaned)
    if result is not None:
        return result

    # Try fixing extra braces (model closed commentary prematurely, leaving dangling })
    fixed_braces = _try_remove_extra_braces(cleaned)
    if fixed_braces != cleaned:
        result = _parse(fixed_braces)
        if result is not None:
            return result

    # Try to find a JSON array in the text
    match = re.search(r"(\[[\s\S]*\])", cleaned)
    if match:
        result = _parse(match.group(1))
        if result is not None:
            return result

    # Try to find a JSON object in the text
    match = re.search(r"(\{[\s\S]*\})", cleaned)
    if match:
        result = _parse(match.group(1))
        if result is not None:
            return result

    # Try fixing common JSON issues: trailing commas
    fixed = re.sub(r",\s*([}\]])", r"\1", cleaned)
    result = _parse(fixed)
    if result is not None:
        return result

    # Try extracting array from trailing-comma-fixed text
    match = re.search(r"(\[[\s\S]*\])", fixed)
    if match:
        result = _parse(match.group(1))
        if result is not None:
            return result

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
