import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { getSoilDataDetails } from "../../../apis/predict";
import SoilDataDetails from "./SoilDataDetails";

jest.mock("../../../apis/predict", () => ({
  getSoilDataDetails: jest.fn(),
}));

const detail = {
  session_id: "soil-42",
  crop_name: "pepper",
  detailed_address: "parcel 1-2",
  soil_data: { acid: "6.5" },
  fertilizer_data: { pre_Fert_N: "10" },
};

beforeEach(() => jest.clearAllMocks());

const renderDetail = (path = "/soil-details/soil-42", state) => render(
  <MemoryRouter
    initialEntries={[{ pathname: path, state }]}
    future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
  >
    <Routes>
      <Route path="/soil-details" element={<SoilDataDetails />} />
      <Route path="/soil-details/:sessionId" element={<SoilDataDetails />} />
    </Routes>
  </MemoryRouter>
);

test("restores soil details from the session URL", async () => {
  getSoilDataDetails.mockResolvedValue({ data: detail });

  renderDetail();

  expect(screen.getByText("토양 분석 결과를 불러오는 중입니다.")).toBeInTheDocument();
  expect(await screen.findByText("pepper")).toBeInTheDocument();
  expect(getSoilDataDetails).toHaveBeenCalledWith("soil-42");
});

test("shows a controlled not-found state", async () => {
  getSoilDataDetails.mockRejectedValue({ response: { status: 404 } });

  renderDetail();

  expect(await screen.findByText("토양 분석 결과를 찾을 수 없습니다.")).toBeInTheDocument();
});

test("keeps the state-only detail route compatible", () => {
  renderDetail("/soil-details", {
    soilData: detail.soil_data,
    fertilizerData: detail.fertilizer_data,
    crop: detail.crop_name,
    detailedAddress: detail.detailed_address,
  });

  expect(screen.getByText("pepper")).toBeInTheDocument();
  expect(getSoilDataDetails).not.toHaveBeenCalled();
});
