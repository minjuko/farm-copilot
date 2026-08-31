import { useEffect, useState } from "react";
import { fetchChatbotStatus, fetchChatHistory } from "../../../apis/chat";
import { normalizeChatHistory } from "./chatFlow";

export default function useChatSession(sessionId, authStatus) {
  const [messages, setMessages] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [chatbotStatus, setChatbotStatus] = useState("checking");

  useEffect(() => {
    let active = true;
    fetchChatbotStatus().then(({ data }) => active && setChatbotStatus(data?.status || "limited"))
      .catch(() => active && setChatbotStatus("limited"));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (authStatus === "unauthenticated") { setMessages([]); return undefined; }
    if (authStatus !== "authenticated") return undefined;
    let active = true;
    fetchChatHistory(sessionId).then(({ data }) => {
      const ordered = normalizeChatHistory(data);
      if (!ordered) throw new Error("MALFORMED_CHAT_HISTORY");
      if (active) { setMessages(ordered); setErrorMessage(""); }
    }).catch(() => active && setErrorMessage("채팅 기록을 불러오는 중 오류가 발생했습니다."));
    return () => { active = false; };
  }, [sessionId, authStatus]);

  return { messages, setMessages, errorMessage, setErrorMessage, chatbotStatus };
}
