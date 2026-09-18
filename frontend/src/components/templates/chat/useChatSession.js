import { useEffect, useState } from "react";
import { fetchChatbotStatus, fetchChatHistory } from "../../../apis/chat";
import { normalizeChatHistory } from "./chatFlow";

export default function useChatSession(sessionId, authStatus) {
  const [messages, setMessages] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [chatbotStatus, setChatbotStatus] = useState("checking");
  const [statusRequestVersion, setStatusRequestVersion] = useState(0);

  useEffect(() => {
    let isActive = true;
    setChatbotStatus("checking");
    fetchChatbotStatus().then(({ data }) => isActive && setChatbotStatus(data?.status || "limited"))
      .catch(() => isActive && setChatbotStatus("error"));
    return () => { isActive = false; };
  }, [statusRequestVersion]);

  useEffect(() => {
    if (authStatus === "unauthenticated") { setMessages([]); return undefined; }
    if (authStatus !== "authenticated") return undefined;
    let isActive = true;
    fetchChatHistory(sessionId).then(({ data: chatHistory }) => {
      const orderedMessages = normalizeChatHistory(chatHistory);
      if (!orderedMessages) throw new Error("MALFORMED_CHAT_HISTORY");
      if (isActive) { setMessages(orderedMessages); setErrorMessage(""); }
    }).catch(() => isActive && setErrorMessage("채팅 기록을 불러오는 중 오류가 발생했습니다."));
    return () => { isActive = false; };
  }, [sessionId, authStatus]);

  return {
    messages,
    setMessages,
    errorMessage,
    setErrorMessage,
    chatbotStatus,
    retryChatbotStatus: () => setStatusRequestVersion((version) => version + 1),
  };
}
