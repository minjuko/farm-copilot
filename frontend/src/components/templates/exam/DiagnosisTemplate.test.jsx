import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { uploadImage } from "../../../apis/predict";
import DiagnosisTemplate from "./DiagnosisTemplate";
import { fetchCapabilities } from "../../../apis/capabilities";

const mockNavigate = jest.fn();
const mockSetIsLoading = jest.fn();

jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));
jest.mock("../../../apis/predict", () => ({ uploadImage: jest.fn() }));
jest.mock("../../../apis/capabilities", () => ({
  fetchCapabilities: jest.fn(),
  normalizeCapability: (payload, name) => payload[name],
}));
jest.mock("../../../LoadingContext", () => ({
  useLoading: () => ({ isLoading: false, setIsLoading: mockSetIsLoading }),
}));
jest.mock("../../atoms/GlobalLoader", () => () => <div>loading</div>);
jest.mock("../../atoms/CustomModal", () => ({ isOpen, content }) => (
  isOpen ? <div role="alert">{content}</div> : null
));

const selectValidImage = () => {
  const input = screen.getByLabelText("카메라 이미지 선택");
  const image = new File(["image"], "crop.jpg", { type: "image/jpeg" });
  fireEvent.change(input, { target: { files: [image] } });
};

beforeAll(() => {
  URL.createObjectURL = jest.fn(() => "blob:preview");
  URL.revokeObjectURL = jest.fn();
});

beforeEach(() => {
  jest.clearAllMocks();
  fetchCapabilities.mockResolvedValue({
    data: { detection: { status: "available", available: true, reason: null } },
  });
});

test("navigates only after a valid detected response", async () => {
  uploadImage.mockResolvedValue({
    data: { session_id: 42, pest_name: "탄저병", confidence: 91.25 },
  });
  render(<DiagnosisTemplate />);
  expect(screen.getByText(/고추: 탄저병, 흰가루병/)).toBeInTheDocument();
  expect(screen.getByText(/정상 여부나 목록에 없는 작물·질병은 판별을 보장하지 않습니다/)).toBeInTheDocument();
  expect(screen.queryByText(/6개 출력 인덱스/)).not.toBeInTheDocument();
  selectValidImage();

  const button = await screen.findByRole("button", { name: /진단하기/ });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);

  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith(
    "/info/42",
    expect.objectContaining({ state: expect.any(Object) })
  ));
});

test.each([
  [400, "No pest was detected in the uploaded image.", "지원 대상 질병을 확인하지 못했습니다"],
  [503, "Image detection model is not available.", "진단 모델"],
])("keeps HTTP %s diagnosis failures out of the success route", async (status, message, expected) => {
  uploadImage.mockRejectedValue({ response: { status, data: { message } } });
  render(<DiagnosisTemplate />);
  selectValidImage();
  const button = await screen.findByRole("button", { name: /진단하기/ });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);

  expect(await screen.findByRole("alert")).toHaveTextContent(expected);
  expect(mockNavigate).not.toHaveBeenCalled();
});

test("reports a malformed success payload instead of rendering it", async () => {
  uploadImage.mockResolvedValue({ data: { session_id: 42, pest_name: "탄저병", confidence: null } });
  render(<DiagnosisTemplate />);
  selectValidImage();
  const button = await screen.findByRole("button", { name: /진단하기/ });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);

  expect(await screen.findByRole("alert")).toHaveTextContent("응답 형식");
  expect(mockNavigate).not.toHaveBeenCalled();
});

test("shows a connection message for a network failure", async () => {
  uploadImage.mockRejectedValue(new Error("offline"));
  render(<DiagnosisTemplate />);
  selectValidImage();
  const button = await screen.findByRole("button", { name: /진단하기/ });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);

  expect(await screen.findByRole("alert")).toHaveTextContent("연결을 확인");
});

test("does not navigate to details for mapping-unavailable 503", async () => {
  uploadImage.mockRejectedValue({
    response: {
      status: 503,
      data: { message: "병해 탐지 모델의 상세정보 매핑이 준비되지 않았습니다." },
    },
  });
  const { container } = render(<DiagnosisTemplate />);
  selectValidImage(container);
  const button = await screen.findByRole("button", { name: /진단하기/ });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);

  expect(await screen.findByRole("alert")).toHaveTextContent("상세정보 연결");
  expect(mockNavigate).not.toHaveBeenCalled();
});

test("blocks duplicate upload clicks while a request is in flight", async () => {
  uploadImage.mockReturnValue(new Promise(() => {}));
  const { container } = render(<DiagnosisTemplate />);
  selectValidImage(container);
  const button = await screen.findByRole("button", { name: /진단하기/ });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);
  fireEvent.click(button);

  await waitFor(() => expect(uploadImage).toHaveBeenCalledTimes(1));
});

test("blocks diagnosis while the model capability is limited", async () => {
  fetchCapabilities.mockResolvedValue({
    data: { detection: { status: "limited", available: false, reason: "not_configured" } },
  });
  render(<DiagnosisTemplate />);
  selectValidImage();

  const button = await screen.findByRole("button", { name: /진단하기/ });
  await waitFor(() => expect(button).toBeDisabled());
  expect(screen.getByRole("status")).toHaveTextContent("진단 모델이 준비되지 않아");
  expect(screen.getByRole("button", { name: "상태 다시 확인" })).toBeEnabled();
  expect(uploadImage).not.toHaveBeenCalled();
});

test("rechecks the model capability and enables diagnosis when it becomes available", async () => {
  fetchCapabilities
    .mockResolvedValueOnce({ data: { detection: { status: "limited", available: false } } })
    .mockResolvedValueOnce({ data: { detection: { status: "available", available: true } } });
  render(<DiagnosisTemplate />);

  const retry = await screen.findByRole("button", { name: "상태 다시 확인" });
  fireEvent.click(retry);

  await waitFor(() => expect(fetchCapabilities).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(screen.getByRole("button", { name: /진단하기/ })).toBeEnabled());
  expect(screen.queryByText(/진단 모델이 준비되지 않아/)).not.toBeInTheDocument();
});

test("distinguishes a capability request error and retries", async () => {
  fetchCapabilities.mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce({ data: { detection: { status: "available", available: true } } });
  render(<DiagnosisTemplate />);

  expect(await screen.findByRole("alert")).toHaveTextContent("연결을 확인한 뒤 다시 시도");
  fireEvent.click(screen.getByRole("button", { name: "상태 다시 확인" }));
  await waitFor(() => expect(fetchCapabilities).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(screen.getByRole("button", { name: /진단하기/ })).toBeEnabled());
  expect(uploadImage).not.toHaveBeenCalled();
});
