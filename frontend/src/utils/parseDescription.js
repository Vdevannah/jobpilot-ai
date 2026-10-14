// Splits a stored job description into paragraphs (and, within a
// paragraph, lines and simple bullet lists) for readable rendering --
// without ever inventing structure the text doesn't already contain.
//
// Why this matters: src/utils.py's clean_html_text() (used by the
// Greenhouse/Lever collectors, see src/greenhouse.py and src/lever.py)
// strips all HTML tags and then collapses ALL whitespace -- including the
// single space it inserts at block-tag/line boundaries -- into one
// space-joined line. So every description actually stored today has zero
// newlines: it is genuinely one unstructured paragraph, with no reliable
// way to recover the original headings, paragraph breaks, or bullets from
// the flattened text alone. Guessing structure back in (e.g. treating
// sentences or phrases as fake headings) would fabricate structure that
// was never there.
//
// This function still handles \n-delimited text correctly, in case that
// ever changes upstream or a description is supplied some other way:
//   - blank-line-separated blocks become paragraphs
//   - a block whose every line starts with "-", "*", or "•" becomes a list
//   - a block's remaining single newlines become line breaks within a
//     paragraph
// Today, with zero newlines, every description still resolves to exactly
// one paragraph block -- preserving that limitation rather than hiding it.
const BULLET_PATTERN = /^[-*•]\s+/;

export function parseDescription(text) {
  if (typeof text !== "string" || text.trim() === "") return [];

  const normalized = text.replace(/\r\n/g, "\n");
  const blocks = normalized
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter((block) => block !== "");

  return blocks.map((block) => {
    const lines = block
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line !== "");

    const isList = lines.length > 1 && lines.every((line) => BULLET_PATTERN.test(line));
    if (isList) {
      return { type: "list", items: lines.map((line) => line.replace(BULLET_PATTERN, "")) };
    }

    return { type: "paragraph", lines };
  });
}
