import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

const LoadingContext = createContext(null);

export const useLoading = () => {
  const context = useContext(LoadingContext);
  if (!context) throw new Error("useLoading must be used within a LoadingProvider");
  return context;
};

export const LoadingProvider = ({ children }) => {
  const [loadingCount, setLoadingCount] = useState(0);

  const beginLoading = useCallback(() => {
    setLoadingCount((count) => count + 1);
    let finished = false;

    return () => {
      if (finished) return;
      finished = true;
      setLoadingCount((count) => Math.max(0, count - 1));
    };
  }, []);

  const endLoading = useCallback(() => {
    setLoadingCount((count) => Math.max(0, count - 1));
  }, []);

  // Transitional API for existing screens. Each true/false pair now changes
  // a request counter, so one completed request cannot hide another loader.
  const setIsLoading = useCallback((nextValue) => {
    setLoadingCount((count) => nextValue ? count + 1 : Math.max(0, count - 1));
  }, []);

  const withLoading = useCallback(async (operation) => {
    const finishLoading = beginLoading();
    try {
      return await operation();
    } finally {
      finishLoading();
    }
  }, [beginLoading]);

  const value = useMemo(() => ({
    beginLoading,
    endLoading,
    isLoading: loadingCount > 0,
    loadingCount,
    setIsLoading,
    withLoading,
  }), [beginLoading, endLoading, loadingCount, setIsLoading, withLoading]);

  return <LoadingContext.Provider value={value}>{children}</LoadingContext.Provider>;
};
