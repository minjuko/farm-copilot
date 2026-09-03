import { useEffect, useState } from "react";
import { fetchCapabilities, normalizeCapability } from "../apis/capabilities";

export default function useServiceCapability(service) {
  const [capability, setCapability] = useState({ status: "checking", available: false });
  useEffect(() => {
    let isActive = true;
    fetchCapabilities()
      .then(({ data }) => isActive && setCapability(normalizeCapability(data, service)))
      .catch(() => isActive && setCapability({ status: "limited", available: false }));
    return () => { isActive = false; };
  }, [service]);
  return capability;
}
