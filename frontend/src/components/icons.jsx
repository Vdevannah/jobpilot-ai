// Small, consistent stroke-style icon set for primary navigation. Kept as
// inline SVG (no icon-library dependency) so every icon shares the same
// viewBox, stroke width, and line caps.
const BASE_PROPS = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": "true",
};

export function DashboardIcon(props) {
  return (
    <svg {...BASE_PROPS} {...props}>
      <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
      <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
    </svg>
  );
}

export function SearchIcon(props) {
  return (
    <svg {...BASE_PROPS} {...props}>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="M19.5 19.5 15.3 15.3" />
    </svg>
  );
}

export function StarIcon(props) {
  return (
    <svg {...BASE_PROPS} {...props}>
      <path d="M12 3.5 14.6 9 20.5 9.8 16.3 14 17.3 20 12 17.1 6.7 20 7.7 14 3.5 9.8 9.4 9Z" />
    </svg>
  );
}

export function ResumeIcon(props) {
  return (
    <svg {...BASE_PROPS} {...props}>
      <path d="M7 3.5h7l3.5 3.5V20a0.5 0.5 0 0 1-0.5 0.5H7A0.5 0.5 0 0 1 6.5 20V4a0.5 0.5 0 0 1 0.5-0.5Z" />
      <path d="M14 3.5V7h3.5" />
      <path d="M9 12h6M9 15.5h6M9 8.5h3" />
    </svg>
  );
}

export function InsightsIcon(props) {
  return (
    <svg {...BASE_PROPS} {...props}>
      <path d="M12 3.5v3M12 17.5v3M3.5 12h3M17.5 12h3M6 6l2 2M18 6l-2 2M6 18l2-2M18 18l-2-2" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export function MenuIcon(props) {
  return (
    <svg {...BASE_PROPS} {...props}>
      <path d="M4 6.5h16M4 12h16M4 17.5h16" />
    </svg>
  );
}

export function BriefcaseIcon(props) {
  return (
    <svg {...BASE_PROPS} {...props}>
      <rect x="3" y="7.5" width="18" height="12" rx="1.8" />
      <path d="M8.5 7.5V6a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v1.5" />
      <path d="M3 12.5h18" />
    </svg>
  );
}

export function BuildingIcon(props) {
  return (
    <svg {...BASE_PROPS} {...props}>
      <rect x="4.5" y="3.5" width="11" height="17" rx="1" />
      <path d="M8 7.5h.01M12 7.5h.01M8 11h.01M12 11h.01M8 14.5h.01M12 14.5h.01" />
      <path d="M15.5 10.5H19a1 1 0 0 1 1 1V20h-4.5" />
    </svg>
  );
}

export function MapPinIcon(props) {
  return (
    <svg {...BASE_PROPS} {...props}>
      <path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21Z" />
      <circle cx="12" cy="9.5" r="2.3" />
    </svg>
  );
}

export function SourceIcon(props) {
  return (
    <svg {...BASE_PROPS} {...props}>
      <path d="M4 7.5 12 3.5l8 4L12 11.5Z" />
      <path d="M4 12l8 4 8-4M4 16.5l8 4 8-4" />
    </svg>
  );
}

export function ArrowRightIcon(props) {
  return (
    <svg {...BASE_PROPS} {...props}>
      <path d="M4.5 12h15M13 5.5 19.5 12 13 18.5" />
    </svg>
  );
}
