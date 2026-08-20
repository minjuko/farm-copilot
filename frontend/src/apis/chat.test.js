import { instance } from "./instance";
import { deleteChatSession, sendChatMessage, updateSessionName } from "./chat";

jest.mock("./instance", () => ({
  instance: { post: jest.fn(), patch: jest.fn(), delete: jest.fn() },
}));

beforeEach(() => jest.clearAllMocks());

test("sends the Backend chatbot payload through the shared instance", () => {
  const payload = { question: "질문", session_id: "session-1", session_name: "상담" };
  sendChatMessage(payload);
  expect(instance.post).toHaveBeenCalledWith("/selfchatbot/chatbot/", payload);
});

test("renames a session with PATCH and session_name payload", () => {
  updateSessionName("session-1", "새 이름");
  expect(instance.patch).toHaveBeenCalledWith("/selfchatbot/update_session_name/session-1/", {
    session_name: "새 이름",
  });
});

test("deletes a session with the Backend DELETE contract", () => {
  deleteChatSession("session-1");
  expect(instance.delete).toHaveBeenCalledWith("/selfchatbot/delete_session/session-1/");
});
