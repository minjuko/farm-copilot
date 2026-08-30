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
  expect(screen.getByRole("status")).toHaveTextContent("LIMITED");
  expect(uploadImage).not.toHaveBeenCalled();
});
