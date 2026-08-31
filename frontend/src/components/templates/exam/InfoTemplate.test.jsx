import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { fetchSessionDetails } from "../../../apis/predict";
import InfoTemplate from "./InfoTemplate";

jest.mock("../../../apis/predict", () => ({
  fetchSessionDetails: jest.fn(),
}));

const result = {
  session_id: "42",
  pest_name: "pepper disease",
  confidence: 91.25,
  occurrence_environment: "humid",
  symptom_description: "spots",
  prevention_methods: "ventilate",
  pesticide_name: "product A",
  detection_date: "2026-08-31 10:00",
};

beforeEach(() => {
  jest.clearAllMocks();
  window.scrollTo = jest.fn();
});

const renderDetail = (path = "/info/42", state) => render(
  <MemoryRouter
    initialEntries={[{ pathname: path, state }]}
    future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
  >
    <Routes>
      <Route path="/info" element={<InfoTemplate />} />
      <Route path="/info/:sessionId" element={<InfoTemplate />} />
    </Routes>
  </MemoryRouter>
);

test("restores a diagnosis detail from its URL after a direct visit", async () => {
  fetchSessionDetails.mockResolvedValue({ data: result });

  renderDetail();

  expect(screen.getByText("진단 결과를 불러오는 중입니다.")).toBeInTheDocument();
  expect(await screen.findByText("pepper disease")).toBeInTheDocument();
  expect(fetchSessionDetails).toHaveBeenCalledWith("42");
});

test("shows a not-found state when the URL session no longer exists", async () => {
  fetchSessionDetails.mockRejectedValue({ response: { status: 404 } });

  renderDetail();

  expect(await screen.findByText("진단 결과를 찾을 수 없습니다.")).toBeInTheDocument();
});

test("keeps the legacy state-only result route compatible", async () => {
  renderDetail("/info", { diagnosisResult: result });

  expect(screen.getByText("pepper disease")).toBeInTheDocument();
  await waitFor(() => expect(fetchSessionDetails).not.toHaveBeenCalled());
});
