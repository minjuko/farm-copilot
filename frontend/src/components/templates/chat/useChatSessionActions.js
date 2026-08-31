import { useRef } from "react";
import { deleteChatSession, updateSessionName } from "../../../apis/chat";

export default function useChatSessionActions({ setSessions, setLoading, setError }) {
  const inFlight = useRef(false);
  const rename = async (session, name) => {
    if (inFlight.current) return false;
    inFlight.current = true;
    setLoading(true); setError("");
    try {
      await updateSessionName(session.session_id, name);
      setSessions((current) => current.map((item) => item.session_id === session.session_id
        ? { ...item, session_name: name } : item));
      return true;
    } catch {
      setError("세션 이름을 업데이트하는 중 오류가 발생했습니다.");
      return false;
    } finally { inFlight.current = false; setLoading(false); }
  };
  const remove = async (sessionId) => {
    if (inFlight.current) return false;
    inFlight.current = true;
    setLoading(true); setError("");
    try {
      await deleteChatSession(sessionId);
      setSessions((current) => current.filter((item) => item.session_id !== sessionId));
      return true;
    } catch {
      setError("세션을 삭제하는 중 오류가 발생했습니다.");
      return false;
    } finally { inFlight.current = false; setLoading(false); }
  };
  return { rename, remove };
}
