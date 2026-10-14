import { useEffect, useRef, useState } from "react";

// Fetches `fetcher()` whenever `deps` changes, deriving the loading state
// during render (comparing the key of the deps that last completed against
// the current deps) rather than calling setState synchronously inside the
// effect -- so filter changes always show a loading state, including on
// re-fetches, not just on first mount.
export function useApiQuery(fetcher, deps) {
  const [result, setResult] = useState({ data: null, error: null });
  const [completedKey, setCompletedKey] = useState(null);
  const requestIdRef = useRef(0);
  const depsKey = JSON.stringify(deps);

  useEffect(() => {
    const requestId = ++requestIdRef.current;
    let cancelled = false;

    fetcher()
      .then((data) => {
        if (cancelled || requestIdRef.current !== requestId) return;
        setResult({ data, error: null });
        setCompletedKey(depsKey);
      })
      .catch((error) => {
        if (cancelled || requestIdRef.current !== requestId) return;
        setResult({ data: null, error: error.message });
        setCompletedKey(depsKey);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [depsKey]);

  const isLoading = completedKey !== depsKey;
  return { isLoading, data: result.data, error: isLoading ? null : result.error };
}
