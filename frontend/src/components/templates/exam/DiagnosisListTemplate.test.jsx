import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import {
  deleteDetectionSession,
  fetchDetectionSessions,
} from "../../../apis/predict";
import DiagnosisListTemplate from "./DiagnosisListTemplate";

const mockNavigate = jest.fn();
const mockSetIsLoading = jest.fn();

jest.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));
jest.mock("../../../apis/predict", () => ({
  deleteDetectionSession: jest.fn(),
  fetchDetectionSessions: jest.fn(),
}));
jest.mock("../../../LoadingContext", () => ({
  useLoading: () => ({ setIsLoading: mockSetIsLoading }),
}));
jest.mock("../../atoms/GlobalLoader", () => () => <div>loading</div>);
jest.mock("../../atoms/ConfirmModal", () => ({ isOpen, onConfirm }) => (
  isOpen ? <button type="button" onClick={onConfirm}>삭제 확정</button> : null
));
jest.mock("../../molecules/Pagination", () => () => null);

const session = {
  session_id: 42,
  pest_name: "고추 탄저병",
  detection_date: "2026-10-17 10:00",
  confidence: 91.25,
  user_image_url: "/media/pest_detections/example.jpg",
};

beforeEach(() => {
  jest.clearAllMocks();
  fetchDetectionSessions.mockResolvedValue({ data: [] });
  deleteDetectionSession.mockResolvedValue({ data: { success: "deleted" } });
});

test("shows the empty diagnosis history state", async () => {
  render(<DiagnosisListTemplate />);

  expect(await screen.findByText(/진단 목록이 존재하지 않습니다/)).toBeInTheDocument();
});

test("renders a valid history item with the shared confidence format", async () => {
  fetchDetectionSessions.mockResolvedValue({ data: [session] });
  render(<DiagnosisListTemplate />);

  expect(await screen.findByText("91.25%")).toBeInTheDocument();
  expect(screen.getByText("모델 예측 점수:")).toBeInTheDocument();
  expect(screen.getByText(/AI 예측 결과는 참고용입니다/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /고추 탄저병 진단 결과 보기/ }));
  expect(mockNavigate).toHaveBeenCalledWith("/info/42");
});

test("rejects a malformed history payload", async () => {
  fetchDetectionSessions.mockResolvedValue({
    data: [{ ...session, confidence: null }],
  });
  render(<DiagnosisListTemplate />);

  expect(await screen.findByRole("alert")).toHaveTextContent("진단 내역을 불러오지 못했습니다");
  expect(screen.queryByText("고추 탄저병")).not.toBeInTheDocument();
});

test("shows a clear authorization message when history is forbidden", async () => {
  fetchDetectionSessions.mockRejectedValue({ response: { status: 403 } });
  render(<DiagnosisListTemplate />);

  expect(await screen.findByRole("alert")).toHaveTextContent("진단 이력을 조회할 권한이 없습니다");
});

test("removes a session from the list after a successful delete", async () => {
  fetchDetectionSessions.mockResolvedValue({ data: [session] });
  render(<DiagnosisListTemplate />);

  fireEvent.click(await screen.findByRole("button", { name: "세션 삭제" }));
  fireEvent.click(screen.getByRole("button", { name: "삭제 확정" }));

  await waitFor(() => expect(deleteDetectionSession).toHaveBeenCalledWith(42));
  await waitFor(() => expect(screen.queryByText("고추 탄저병")).not.toBeInTheDocument());
});
