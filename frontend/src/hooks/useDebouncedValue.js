import { useEffect, useState } from "react";

// Returns `value`, updated only after it has stopped changing for `delayMs`.
// Used to avoid firing an API request on every keystroke in a search box.
export function useDebouncedValue(value, delayMs = 300) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
