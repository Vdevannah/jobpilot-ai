from html import unescape
from html.parser import HTMLParser


def is_us_location(location):
    us_states = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC"
    }
    us_state_names = {
        "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
        "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
        "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
        "maine", "maryland", "massachusetts", "michigan", "minnesota",
        "mississippi", "missouri", "montana", "nebraska", "nevada",
        "new hampshire", "new jersey", "new mexico", "new york",
        "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
        "pennsylvania", "rhode island", "south carolina", "south dakota",
        "tennessee", "texas", "utah", "vermont", "virginia", "washington",
        "west virginia", "wisconsin", "wyoming", "washington dc"
    }

    location_lower = location.lower()

    if "united states" in location_lower or "usa" in location_lower:
        return True

    if "," in location:
        state = location.split(",")[-1].strip()
        state_upper = state.upper()
        state_lower = state.lower()

        if state_upper in us_states or state_lower in us_state_names:
            return True

    return False


def matches_target_role(title, target_roles):
    title = title.lower()
    excluded_phrases = [
        "strategic finance",
        "financial planning",
        "investment banking"
    ]

    if any(phrase in title for phrase in excluded_phrases):
        return False

    return any(role.lower() in title for role in target_roles)


def deduplicate_jobs(jobs):
    unique_jobs = []
    seen = set()

    for job in jobs:
        key = (
            job["company"].strip().lower(),
            job["title"].strip().lower(),
            job["location"].strip().lower()
        )

        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    return unique_jobs


def clean_html_text(text):
    if not text:
        return ""

    class TextExtractor(HTMLParser):
        block_tags = {
            "address", "article", "blockquote", "dd", "div", "dl", "dt",
            "h1", "h2", "h3", "h4", "h5", "h6", "li", "ol", "p",
            "section", "ul",
        }

        def __init__(self):
            super().__init__()
            self.parts = []

        def handle_starttag(self, tag, attrs):
            if tag == "br" or tag in self.block_tags:
                self.parts.append(" ")

        def handle_endtag(self, tag):
            if tag in self.block_tags:
                self.parts.append(" ")

        def handle_data(self, data):
            self.parts.append(data)

    parser = TextExtractor()
    parser.feed(unescape(text))
    return " ".join("".join(parser.parts).split())


def extract_structured_text(html):
    """Converts job-posting HTML into readable plain text that preserves
    genuine paragraph breaks, headings, and bullet lists -- never inventing
    structure the source HTML doesn't already have.

    Unlike clean_html_text() (which flattens everything to one
    space-joined line), block-level containers (p, div, headings,
    blockquote, section, article, dd/dt/dl, and ul/ol as a whole) each
    become their own paragraph, separated from neighboring paragraphs by a
    blank line ("\\n\\n"). Within a list, each <li> becomes its own
    "- "-prefixed line inside that one list paragraph (not a separate
    paragraph per item), so a list reads as a list rather than being
    scattered. <br> is a single line break within the current paragraph.
    <script> and <style> tag contents are discarded entirely -- they are
    never real job content. HTML entities are decoded (html.unescape)
    before parsing, same as clean_html_text(). The result is built as a
    plain string (never raw HTML), safe to render as React text content.

    A plain-text input with no HTML tags at all (e.g. Lever's
    descriptionPlain, or any already-flattened stored description) passes
    through as a single paragraph, since there is no structure to find.
    """
    if not html:
        return ""

    class StructuredTextExtractor(HTMLParser):
        paragraph_tags = {
            "address", "article", "blockquote", "dd", "div", "dl", "dt",
            "h1", "h2", "h3", "h4", "h5", "h6", "ol", "p", "section", "ul",
        }
        skip_content_tags = {"script", "style"}

        def __init__(self):
            super().__init__()
            self.blocks = []
            self.current = []
            self.skip_depth = 0

        def _flush_block(self):
            text = "".join(self.current).strip()
            if text:
                self.blocks.append(text)
            self.current = []

        def handle_starttag(self, tag, attrs):
            if tag in self.skip_content_tags:
                self.skip_depth += 1
            elif tag == "br":
                self.current.append("\n")
            elif tag == "li":
                self.current.append("\n- ")
            elif tag in self.paragraph_tags:
                self._flush_block()

        def handle_endtag(self, tag):
            if tag in self.skip_content_tags:
                self.skip_depth = max(0, self.skip_depth - 1)
            elif tag in self.paragraph_tags:
                self._flush_block()

        def handle_data(self, data):
            if self.skip_depth == 0:
                self.current.append(data)

    parser = StructuredTextExtractor()
    parser.feed(unescape(html))
    parser._flush_block()

    normalized_blocks = []
    for block in parser.blocks:
        lines = (" ".join(line.split()) for line in block.split("\n"))
        lines = [line for line in lines if line]
        if lines:
            normalized_blocks.append("\n".join(lines))

    return "\n\n".join(normalized_blocks)
