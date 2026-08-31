import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { fetchCapabilities } from "../../../apis/capabilities";
import {
  getCropNames,
  getSoilExamData,
  getSoilFertilizerInfo,
  searchSoilAddresses,
} from "../../../apis/predict";
import SoilTemplate from "./SoilTemplate";

jest.mock("../../../apis/capabilities", () => ({
  fetchCapabilities: jest.fn(),
  normalizeCapability: (payload, service) => payload[service],
}));
jest.mock("../../../apis/predict", () => ({
  getCropNames: jest.fn(),
  getSoilExamData: jest.fn(),
  getSoilFertilizerInfo: jest.fn(),
  searchSoilAddresses: jest.fn(),
}));
jest.mock("../../../LoadingContext", () => ({
  useLoading: () => ({ setIsLoading: jest.fn() }),
}));
jest.mock("../../atoms/CustomModal", () => () => null);
jest.mock("./SoilResults", () => ({ cropName, fertilizerData }) => (
  <div data-testid="soil-results">{cropName}:{fertilizerData?.[0]?.pre_Fert_N}</div>
));

const soilSample = {
  No: "1",
  PNU_Nm: "selected parcel 1-2",
  Exam_Day: "20260831",
  ACID: "6.5",
};

beforeEach(() => {
  jest.clearAllMocks();
  fetchCapabilities.mockResolvedValue({ data: { soil: { status: "live", available: true } } });
  getCropNames.mockResolvedValue({ data: { crop_names: ["pepper", "tomato"] } });
  searchSoilAddresses.mockResolvedValue({
    data: {
      normalized_query: "normalized address",
      results: [{ address_name: "parcel 1-2", display_name: "selected parcel 1-2" }],
    },
  });
  getSoilExamData.mockResolvedValue({ data: { soil_data: [soilSample] } });
  getSoilFertilizerInfo.mockResolvedValue({ data: { data: [{ pre_Fert_N: "10" }] } });
});

test("connects crop, address, soil sample, and fertilizer steps through the analysis hook", async () => {
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <SoilTemplate />
    </MemoryRouter>
  );

  await waitFor(() => expect(getCropNames).toHaveBeenCalled());
  fireEvent.click(screen.getByLabelText("작물 이름"));
  fireEvent.click(await screen.findByRole("option", { name: "pepper" }));
  fireEvent.change(screen.getByLabelText("주소"), { target: { value: "old address" } });

  const searchButton = screen.getByRole("button", { name: /주소 검색/ });
  await waitFor(() => expect(searchButton).toBeEnabled());
  fireEvent.click(searchButton);
  fireEvent.click(await screen.findByRole("button", { name: "selected parcel 1-2" }));

  expect(getSoilExamData).toHaveBeenCalledWith("pepper", "selected parcel 1-2");
  fireEvent.change(await screen.findByLabelText("상세 주소 선택"), { target: { value: "0" } });

  await waitFor(() => expect(screen.getByTestId("soil-results")).toHaveTextContent("pepper:10"));
  expect(getSoilFertilizerInfo).toHaveBeenCalledWith(expect.objectContaining({
    crop_code: "pepper",
    PNU_Nm: "selected parcel 1-2",
  }));
});
