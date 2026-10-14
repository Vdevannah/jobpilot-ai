import { useId, useState } from "react";
import { parseDescription } from "../utils/parseDescription";
import "./JobDescription.css";

const PREVIEW_CHAR_LIMIT = 600;

// A short, plain preview string truncated at a word boundary -- or null
// when the description is already short enough that no preview/expand
// toggle is needed at all. Collapsing to flat text for the preview (rather
// than a truncated version of the structured blocks) keeps the "is this
// short enough to need a preview" decision, and the truncation itself,
// simple and consistent regardless of how many paragraphs/lists the full
// description has.
function buildPreview(blocks, limit) {
  const flatText = blocks
    .map((block) => (block.type === "list" ? block.items.join(" ") : block.lines.join(" ")))
    .join(" ");

  if (flatText.length <= limit) return null;

  const truncated = flatText.slice(0, limit);
  const lastSpace = truncated.lastIndexOf(" ");
  const trimmed = lastSpace > 0 ? truncated.slice(0, lastSpace) : truncated;
  return `${trimmed.trim()}…`;
}

// Renders a job description as React elements built from plain-text
// segments (utils/parseDescription) -- never via dangerouslySetInnerHTML --
// so literal HTML-looking text in the stored description (e.g. "<script>")
// is always shown as inert text, never parsed or executed. Paragraph
// breaks, line breaks, and simple bullet lists are preserved exactly when
// the text already contains them; nothing is invented when it doesn't (see
// utils/parseDescription.js for why today's real data never does).
export default function JobDescription({ text }) {
  const [expanded, setExpanded] = useState(false);
  const contentId = useId();
  const blocks = parseDescription(text);
  if (blocks.length === 0) return null;

  const preview = buildPreview(blocks, PREVIEW_CHAR_LIMIT);
  const isTruncatable = preview !== null;
  const showFull = expanded || !isTruncatable;

  return (
    <div className="job-description">
      <div id={contentId} className="job-description__content">
        {showFull ? (
          blocks.map((block, index) =>
            block.type === "list" ? (
              <ul key={index} className="job-description__list">
                {block.items.map((item, itemIndex) => (
                  <li key={itemIndex}>{item}</li>
                ))}
              </ul>
            ) : (
              <p key={index} className="job-description__paragraph">
                {block.lines.map((line, lineIndex) => (
                  <span key={lineIndex}>
                    {line}
                    {lineIndex < block.lines.length - 1 ? <br /> : null}
                  </span>
                ))}
              </p>
            ),
          )
        ) : (
          <p className="job-description__paragraph">{preview}</p>
        )}
      </div>

      {isTruncatable && (
        <button
          type="button"
          className="job-description__toggle"
          aria-expanded={expanded}
          aria-controls={contentId}
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "Show less" : "Read full description"}
        </button>
      )}
    </div>
  );
}
