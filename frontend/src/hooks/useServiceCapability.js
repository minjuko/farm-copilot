import { useCallback, useEffect, useState } from "react";
import { fetchCapabilities, normalizeCapability } from "../apis/capabilities";

export default function useServiceCapability(service) {
  const [capability, setCapability] = useState({ status: "checking", available: false });
  const [requestVersion, setRequestVersion] = useState(0);
  useEffect(() => {
    let isActive = true;
    setCapability({ status: "checking", available: false });
    fetchCapabilities()
      .then(({ data }) => isActive && setCapability(normalizeCapability(data, service)))
      .catch(() => isActive && setCapability({ status: "error", available: false }));
    return () => { isActive = false; };
  }, [service, requestVersion]);
  const retry = useCallback(() => setRequestVersion((version) => version + 1), []);
  return { ...capability, retry };
}
