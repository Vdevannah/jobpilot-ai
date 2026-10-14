import { useCallback, useRef, useState } from "react";

// Unlike useApiQuery, this never fetches on mount or when deps change --
// only when `run()` is called, so AI preview requests happen only on
// explicit user action (e.g. a button click), never automatically.
export function useLazyRequest(requestFn) {
  const [state, setState] = useState({ status: "idle", data: null, error: null });
  const requestIdRef = useRef(0);

  const run = useCallback(
    async (...args) => {
      const requestId = ++requestIdRef.current;
      setState({ status: "loading", data: null, error: null });
      try {
        const data = await requestFn(...args);
        if (requestIdRef.current !== requestId) return;
        setState({ status: "success", data, error: null });
      } catch (error) {
        if (requestIdRef.current !== requestId) return;
        setState({ status: "error", data: null, error: error.message });
      }
    },
    [requestFn],
  );

  const reset = useCallback(() => {
    requestIdRef.current += 1;
    setState({ status: "idle", data: null, error: null });
  }, []);

  return {
    status: state.status,
    data: state.data,
    error: state.error,
    isIdle: state.status === "idle",
    isLoading: state.status === "loading",
    run,
    reset,
  };
}
