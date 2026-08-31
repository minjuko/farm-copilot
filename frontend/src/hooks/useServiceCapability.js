import { useEffect, useState } from "react";
import { fetchCapabilities, normalizeCapability } from "../apis/capabilities";

export default function useServiceCapability(service) {
  const [capability, setCapability] = useState({ status: "checking", available: false });
  useEffect(() => {
    let active = true;
    fetchCapabilities()
      .then(({ data }) => active && setCapability(normalizeCapability(data, service)))
      .catch(() => active && setCapability({ status: "limited", available: false }));
    return () => { active = false; };
  }, [service]);
  return capability;
}
