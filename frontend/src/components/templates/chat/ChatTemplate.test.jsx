import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { fetchChatHistory, sendChatMessage } from "../../../apis/chat";
import ChatTemplate from "./ChatTemplate";
import { CHATBOT_LIMITED_MESSAGE } from "./chatFlow";

jest.mock("react-router-dom", () => ({
  useParams: () => ({ sessionid: "session-1" }),
  useLocation: () => ({ search: "?session_name=농업GPT" }),
  useNavigate: () => jest.fn(),
}));
jest.mock("../../../apis/chat", () => ({
  fetchChatHistory: jest.fn(),
  sendChatMessage: jest.fn(),
}));
jest.mock("../../../AuthContext", () => ({
  useAuth: () => ({ status: "unauthenticated", user: null }),
}));

const submitQuestion = (question) => {
  fireEvent.change(screen.getByPlaceholderText("질문을 입력하세요"), {
    target: { value: question },
  });
  fireEvent.click(screen.getByRole("button", { name: "질문 보내기" }));
};

beforeEach(() => {
  jest.clearAllMocks();
  fetchChatHistory.mockResolvedValue({ data: [] });
});

test("blocks whitespace-only questions", () => {
  render(<ChatTemplate />);
  submitQuestion("   ");
  expect(screen.getByRole("alert")).toHaveTextContent("질문을 입력해주세요");
  expect(sendChatMessage).not.toHaveBeenCalled();
});

test("shows 503 as limited state without adding a fake assistant response", async () => {
  sendChatMessage.mockRejectedValue({ response: { status: 503, data: { message: "internal detail" } } });
  render(<ChatTemplate />);
  expect(screen.queryByText("안녕하세요 무엇을 도와드릴까요?")).not.toBeInTheDocument();
  submitQuestion("감자 재배법은?");

  expect(await screen.findByRole("alert")).toHaveTextContent(CHATBOT_LIMITED_MESSAGE);
  expect(screen.getAllByText(CHATBOT_LIMITED_MESSAGE)).toHaveLength(1);
  expect(screen.getByText("감자 재배법은?")).toBeInTheDocument();
});

test("allows retry after unavailable and adds assistant only on valid success", async () => {
  sendChatMessage
    .mockRejectedValueOnce({ response: { status: 503, data: {} } })
    .mockResolvedValueOnce({ data: { answer: "성공 답변", timestamp: "2026-01-01T00:00:00Z" } });
  render(<ChatTemplate />);
  submitQuestion("첫 질문");
  await screen.findByRole("alert");
  submitQuestion("재시도 질문");

  expect(await screen.findByText("성공 답변")).toBeInTheDocument();
  expect(sendChatMessage).toHaveBeenCalledTimes(2);
});

test("blocks duplicate submits while a request is in flight", async () => {
  sendChatMessage.mockReturnValue(new Promise(() => {}));
  render(<ChatTemplate />);
  const input = screen.getByPlaceholderText("질문을 입력하세요");
  fireEvent.change(input, { target: { value: "중복 질문" } });
  const button = screen.getByRole("button", { name: "질문 보내기" });
  fireEvent.click(button);
  fireEvent.click(button);

  await waitFor(() => expect(sendChatMessage).toHaveBeenCalledTimes(1));
});
