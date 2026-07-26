"""Query sanitization — docs/architecture/06-tool-architecture.md §6.6
(ACCB Mandatory Change 1): "incoming query text is checked against a
PII-pattern/entity-detection pass (applicant names, IC numbers, business
registration numbers, exact addresses) before the tool constructs an
outbound request; matches are generalized ... or the call is rejected ...
if it cannot be safely generalized. This is enforced programmatically at
the tool boundary ... not left as an instruction in the Market Agent's
system prompt."

**Coverage note, stated plainly rather than overclaimed:** the four
patterns below (IC number, business registration number, phone number,
email address, and a common street-address form) are genuine, deterministic
regex detection — real engineering, not a vendor decision, so they're fully
implemented here. **Free-text applicant/business *name* detection is not** —
that needs a real named-entity-recognition model, which is the same
category of open decision as ``tools/ocr``'s OCR engine or
``tools/documents``'s classifier: a vendor/model choice this repo hasn't
made yet, not something to fabricate with a fragile heuristic (e.g.
"any capitalized word") that would give false confidence rather than real
protection. ``sanitize_query`` accepts an optional ``name_detector``
callable for exactly that gap — production wiring must supply one before
the Market Agent is exposed to real applicant data end-to-end; until then,
callers should still generalize business/owner names out of queries at the
call site, upstream of this tool.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from shared.schemas import ToolInputError

# Malaysian NRIC: 123456-12-1234, or the 12-digit form with no separators.
_IC_NUMBER_RE = re.compile(r'\b\d{6}-\d{2}-\d{4}\b|\b\d{12}\b')
# Old ROC company registration format, e.g. "123456-X".
_BUSINESS_REG_RE = re.compile(r'\b\d{5,10}-[A-Za-z]\b')
# Malaysian mobile numbers, with or without country code/separators.
_PHONE_RE = re.compile(r'\b(?:\+?60|0)1\d[-\s]?\d{3,4}[-\s]?\d{4}\b')
_EMAIL_RE = re.compile(r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b')
# Common Malaysian street-address form: "No. 12, Jalan Ampang" / "Lot 5,
# Jalan SS2/1". Continuation words after "Jalan" are required to look like
# a proper-noun street name (capitalized) rather than matched unboundedly —
# an unbounded `.+`-style match here would just as happily swallow the rest
# of an unrelated sentence following the address (e.g. "... Jalan Ampang
# retail sector outlook" should stop at "Ampang", not eat "retail sector
# outlook" too).
_ADDRESS_RE = re.compile(
    r"\b(?i:No\.?|Lot)\s*\d+[A-Za-z]?,?\s+(?i:Jalan)\s+[A-Z][A-Za-z0-9']*"
    r"(?:[\s/][A-Z][A-Za-z0-9']*){0,3}"
)

_STRUCTURED_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    'ic_number': _IC_NUMBER_RE,
    'business_registration_number': _BUSINESS_REG_RE,
    'phone_number': _PHONE_RE,
    'email_address': _EMAIL_RE,
    'street_address': _ADDRESS_RE,
}

# Returns the detected-name spans (start, end) in ``query``, if any — no
# default; see the module docstring.
NameDetector = Callable[[str], list[tuple[int, int]]]


def sanitize_query(
    query: str,
    *,
    name_detector: NameDetector | None = None,
    min_informative_length: int = 3,
) -> str:
    """Strip structured PII from ``query``, generalizing it to whatever
    sector/industry/region terms remain. Raises ``ToolInputError`` — per
    §6.6, "the call is rejected ... if it cannot be safely generalized" —
    when nothing informative survives.
    """

    sanitized = query
    matched_categories: list[str] = []

    for category, pattern in _STRUCTURED_PII_PATTERNS.items():
        if pattern.search(sanitized):
            matched_categories.append(category)
            sanitized = pattern.sub(' ', sanitized)

    if name_detector is not None:
        spans = sorted(name_detector(sanitized), reverse=True)
        if spans:
            matched_categories.append('name')
        for start, end in spans:
            sanitized = sanitized[:start] + ' ' + sanitized[end:]

    sanitized = re.sub(r'\s+', ' ', sanitized).strip()

    if not sanitized or len(sanitized) < min_informative_length:
        raise ToolInputError(
            'Query could not be safely generalized after removing '
            f'{matched_categories or "nothing identifiable"} — rewrite as '
            'sector/industry/region terms before calling the search tool '
            '(docs/architecture/06-tool-architecture.md §6.6)'
        )
    return sanitized
