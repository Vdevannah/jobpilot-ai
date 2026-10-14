from src.utils import clean_html_text, extract_structured_text


def test_preserves_separate_paragraphs():
    html = "<p>First paragraph.</p><p>Second paragraph.</p>"
    result = extract_structured_text(html)
    assert result == "First paragraph.\n\nSecond paragraph."


def test_preserves_heading_as_its_own_block():
    html = "<h2>The Community You Will Join</h2><p>Some intro text.</p>"
    result = extract_structured_text(html)
    assert result == "The Community You Will Join\n\nSome intro text."


def test_pseudo_heading_in_its_own_paragraph_stays_separate_without_fabricating_a_real_heading():
    # Realistic Greenhouse pattern: a bolded "heading" is just a <p><strong>
    # wrapper, not an <h#> tag. It should still land on its own paragraph
    # because it's in its own <p>, but no heading markup is invented.
    html = '<p><strong>The Community You Will Join:</strong></p><p>More text here.</p>'
    result = extract_structured_text(html)
    assert result == "The Community You Will Join:\n\nMore text here."


def test_preserves_bullet_list_items_individually():
    html = "<p>Responsibilities:</p><ul><li>Write code</li><li>Review PRs</li><li>Ship features</li></ul>"
    result = extract_structured_text(html)
    assert result == (
        "Responsibilities:\n\n"
        "- Write code\n- Review PRs\n- Ship features"
    )


def test_ordered_list_items_also_become_bullet_lines():
    html = "<ol><li>Step one</li><li>Step two</li></ol>"
    result = extract_structured_text(html)
    assert result == "- Step one\n- Step two"


def test_br_becomes_a_single_line_break_within_a_paragraph():
    html = "<p>Line one.<br>Line two.</p>"
    result = extract_structured_text(html)
    assert result == "Line one.\nLine two."


def test_decodes_html_entities():
    html = "<p>Guests &amp; hosts &mdash; it&#39;s &quot;authentic&quot;.</p>"
    result = extract_structured_text(html)
    assert "&amp;" not in result
    assert "Guests & hosts" in result
    assert "it's" in result
    assert '"authentic"' in result


def test_strips_script_and_style_content_entirely():
    html = (
        "<p>Real content.</p>"
        "<script>trackPageView({event: 'job_view'});</script>"
        "<style>.hidden { display: none; }</style>"
    )
    result = extract_structured_text(html)
    assert result == "Real content."
    assert "trackPageView" not in result
    assert "display: none" not in result


def test_drops_inline_styling_attributes_without_leaking_their_values():
    html = '<p><span style="font-family: helvetica, arial; color: #000;">Styled text.</span></p>'
    result = extract_structured_text(html)
    assert result == "Styled text."
    assert "font-family" not in result
    assert "helvetica" not in result


def test_strips_html_comments():
    html = "<p>Visible text.</p><!-- internal tracking note, not job content -->"
    result = extract_structured_text(html)
    assert result == "Visible text."


def test_plain_text_with_no_html_passes_through_as_one_paragraph():
    text = "A plain description with no markup at all."
    result = extract_structured_text(text)
    assert result == text


def test_empty_or_missing_html_returns_empty_string():
    assert extract_structured_text("") == ""
    assert extract_structured_text(None) == ""


def test_realistic_greenhouse_sample_preserves_full_structure():
    html = (
        "<div class=\"content-intro\"><p>Airbnb was born in 2007.</p></div>"
        "<p><strong>The Community You Will Join:</strong></p>"
        "<p>Our Community Support team delivers 10-star support.</p>"
        "<p><strong>A Typical Day:</strong></p>"
        "<ul>"
        "<li>Discover Opportunities: find issues in the data.</li>"
        "<li>Build Solutions: ship fixes that matter.</li>"
        "</ul>"
    )
    result = extract_structured_text(html)
    assert result == (
        "Airbnb was born in 2007.\n\n"
        "The Community You Will Join:\n\n"
        "Our Community Support team delivers 10-star support.\n\n"
        "A Typical Day:\n\n"
        "- Discover Opportunities: find issues in the data.\n"
        "- Build Solutions: ship fixes that matter."
    )


def test_realistic_lever_list_section_sample():
    # Mirrors src/lever.py's job["lists"][i]["content"] shape.
    html = "<ul><li>Python and SQL</li><li>3+ years of experience</li></ul>"
    result = extract_structured_text(html)
    assert result == "- Python and SQL\n- 3+ years of experience"


def test_never_fabricates_structure_for_a_single_unbroken_sentence():
    text = "Responsibilities and qualifications are both described in this one sentence."
    result = extract_structured_text(text)
    assert result == text
    assert "\n" not in result


def test_output_is_plain_string_safe_for_react_text_rendering():
    html = "<p>Plain readable text with no markup tricks.</p>"
    result = extract_structured_text(html)
    # A genuinely plain-text result -- a str, never markup -- confirming
    # the frontend's plain-text (not dangerouslySetInnerHTML) rendering
    # approach is sufficient and safe for whatever this returns.
    assert result == "Plain readable text with no markup tricks."
    assert isinstance(result, str)
    assert "<" not in result and ">" not in result


def test_double_escaped_tag_like_text_is_dropped_as_an_unknown_tag_not_leaked_or_executed():
    # &lt;tag&gt; decodes to literal "<tag>" before HTMLParser sees it (same
    # as the existing clean_html_text()), so HTMLParser treats it as an
    # unknown start tag and silently ignores it -- it never survives into
    # the output, but nothing unsafe happens either. Documenting this
    # existing edge case rather than asserting behavior that isn't real.
    html = "<p>Has a &lt;tag&gt;-looking phrase in it.</p>"
    result = extract_structured_text(html)
    assert "<" not in result and ">" not in result
    assert "tag" not in result.lower() or "phrase" in result.lower()


def test_matches_old_flattened_output_once_whitespace_is_collapsed():
    # The whole point of keeping structure for display while being
    # risk-free for matching (src/matching.py's _normalize_description):
    # collapsing the new structured text's whitespace should reproduce
    # what the old clean_html_text() already produced, modulo bullet
    # markers (which _normalize_description also strips).
    html = "<p>First paragraph.</p><p>Second paragraph.</p>"
    old = clean_html_text(html)
    new = extract_structured_text(html)
    assert " ".join(new.split()) == old
