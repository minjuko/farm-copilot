export const CHATBOT_LIMITED_MESSAGE =
  "챗봇 데이터와 외부 서비스가 준비되지 않아 현재 이용할 수 없습니다.";

export const buildChatPayload = ({ question, sessionId, sessionName }) => {
  const trimmedQuestion = typeof question === "string" ? question.trim() : "";
  if (!trimmedQuestion) return { error: "질문을 입력해주세요." };
  if (!sessionId) return { error: "대화 세션 정보가 올바르지 않습니다." };

  return {
    payload: {
      question: trimmedQuestion,
      session_id: sessionId,
      session_name: (sessionName || "농업GPT").trim() || "농업GPT",
    },
  };
};

export const normalizeChatResponse = (data) => {
  if (typeof data?.answer !== "string" || !data.answer.trim()) return null;
  return {
    isUser: false,
    text: data.answer,
    timestamp: data.timestamp || new Date().toISOString(),
  };
};

export const normalizeChatHistory = (data) => {
  if (!Array.isArray(data)) return null;
  return data.flatMap((chat) => {
    if (typeof chat?.question !== "string" || typeof chat?.answer !== "string") return [];
    const timestamp = chat.timestamp || new Date().toISOString();
    return [
      { isUser: true, text: chat.question, timestamp },
      { isUser: false, text: chat.answer, timestamp },
    ];
  });
};

export const getChatErrorMessage = (error) => {
  if (error?.response?.status === 503) return CHATBOT_LIMITED_MESSAGE;
  if (error?.response?.status === 400) return "질문을 확인한 후 다시 입력해주세요.";
  return "챗봇 요청을 처리하지 못했습니다. 잠시 후 다시 시도해주세요.";
};

export const normalizeSessionName = (value) => (
  typeof value === "string" ? value.trim() : ""
);
