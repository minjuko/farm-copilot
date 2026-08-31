import { useCallback, useEffect, useRef, useState } from "react";
import { useLoading } from "../LoadingContext";

const identityError = (error) => error;

const useAsyncResource = (
  loader,
  { enabled = true, getError = identityError, initialData = null, useGlobalLoading = true } = {}
) => {
  const { beginLoading, setIsLoading: setGlobalLoading } = useLoading();
  const [data, setData] = useState(initialData);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const mountedRef = useRef(true);
  const requestIdRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      requestIdRef.current += 1;
    };
  }, []);

  const execute = useCallback(async () => {
    if (!enabled) return undefined;
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    let finishGlobalLoading = () => {};

    if (useGlobalLoading) {
      if (beginLoading) {
        finishGlobalLoading = beginLoading();
      } else {
        setGlobalLoading(true);
        finishGlobalLoading = () => setGlobalLoading(false);
      }
    }

    if (mountedRef.current) {
      setIsLoading(true);
      setError(null);
    }

    try {
      const nextData = await loader();
      if (mountedRef.current && requestIdRef.current === requestId) setData(nextData);
      return nextData;
    } catch (requestError) {
      if (mountedRef.current && requestIdRef.current === requestId) setError(getError(requestError));
      return undefined;
    } finally {
      finishGlobalLoading();
      if (mountedRef.current && requestIdRef.current === requestId) setIsLoading(false);
    }
  }, [beginLoading, enabled, getError, loader, setGlobalLoading, useGlobalLoading]);

  useEffect(() => {
    execute();
  }, [execute]);

  return { data, error, isLoading, refetch: execute, setData };
};

export default useAsyncResource;
