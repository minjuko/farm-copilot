import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { uploadImage } from "../../../apis/predict";
import DiagnosisTemplate from "./DiagnosisTemplate";

const mockNavigate = jest.fn();
const mockSetIsLoading = jest.fn();

jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));
jest.mock("../../../apis/predict", () => ({ uploadImage: jest.fn() }));
jest.mock("../../../LoadingContext", () => ({
  useLoading: () => ({ isLoading: false, setIsLoading: mockSetIsLoading }),
}));
jest.mock("../../atoms/GlobalLoader", () => () => <div>loading</div>);
jest.mock("../../atoms/CustomModal", () => ({ isOpen, content }) => (
  isOpen ? <div role="alert">{content}</div> : null
));

const selectValidImage = (container) => {
  const input = container.querySelector('input[capture="camera"]');
  const image = new File(["image"], "crop.jpg", { type: "image/jpeg" });
  fireEvent.change(input, { target: { files: [image] } });
};

beforeAll(() => {
  URL.createObjectURL = jest.fn(() => "blob:preview");
  URL.revokeObjectURL = jest.fn();
});

beforeEach(() => jest.clearAllMocks());

test("does not navigate to details for mapping-unavailable 503", async () => {
  uploadImage.mockRejectedValue({
    response: {
      status: 503,
      data: { message: "병해 탐지 모델의 상세정보 매핑이 준비되지 않았습니다." },
    },
  });
  const { container } = render(<DiagnosisTemplate />);
  selectValidImage(container);
  fireEvent.click(screen.getByRole("button", { name: /진단하기/ }));

  expect(await screen.findByRole("alert")).toHaveTextContent("상세정보 연결");
  expect(mockNavigate).not.toHaveBeenCalled();
});

test("blocks duplicate upload clicks while a request is in flight", async () => {
  uploadImage.mockReturnValue(new Promise(() => {}));
  const { container } = render(<DiagnosisTemplate />);
  selectValidImage(container);
  const button = screen.getByRole("button", { name: /진단하기/ });
  fireEvent.click(button);
  fireEvent.click(button);

  await waitFor(() => expect(uploadImage).toHaveBeenCalledTimes(1));
});
