import {
  CHATBOT_LIMITED_MESSAGE,
  buildChatPayload,
  getChatErrorMessage,
  normalizeChatHistory,
  normalizeChatResponse,
  normalizeSessionName,
} from "./chatFlow";

test.each(["", "   ", null])("blocks empty chat question %p", (question) => {
  expect(buildChatPayload({ question, sessionId: "session-1" }).error).toMatch(/질문/);
});

test("trims a valid question and excludes frontend user identity", () => {
  const { payload } = buildChatPayload({
    question: "  감자 재배법은?  ", sessionId: "session-1", sessionName: "  농사 상담  ",
  });
  expect(payload).toEqual({
    question: "감자 재배법은?",
    session_id: "session-1",
    session_name: "농사 상담",
  });
  expect(payload).not.toHaveProperty("user_id");
});

test("maps archived backend 503 without exposing infrastructure detail", () => {
  const error = { response: { status: 503, data: { message: "OPENAI_API_KEY and Chroma missing" } } };
  expect(getChatErrorMessage(error)).toBe(CHATBOT_LIMITED_MESSAGE);
  expect(getChatErrorMessage(error)).not.toMatch(/OpenAI|Chroma|RAG/i);
});

test("rejects malformed success without creating an assistant message", () => {
  expect(normalizeChatResponse({ answer: undefined })).toBeNull();
  expect(normalizeChatResponse({ answer: "   " })).toBeNull();
});

test("normalizes valid success and history only from backend answers", () => {
  expect(normalizeChatResponse({ answer: "답변", timestamp: "now" })).toEqual({
    isUser: false, text: "답변", timestamp: "now",
  });
  expect(normalizeChatHistory([{ question: "질문", answer: "답변", timestamp: "now" }]))
    .toHaveLength(2);
});

test("trims session names", () => {
  expect(normalizeSessionName("  새 이름  ")).toBe("새 이름");
  expect(normalizeSessionName("   ")).toBe("");
});
