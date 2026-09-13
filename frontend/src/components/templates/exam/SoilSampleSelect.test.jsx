import { fireEvent, render, screen } from "@testing-library/react";
import SoilSampleSelect from "./SoilSampleSelect";

test("shows the detailed-address selector before an address search", () => {
  render(
    <SoilSampleSelect
      disabled={false}
      guidance="작물 이름과 주소를 먼저 입력해주세요."
      onSelect={jest.fn()}
      samples={[]}
      selectedSample={null}
    />
  );

  const selector = screen.getByLabelText("상세 주소 선택");
  expect(selector).toBeDisabled();
  expect(screen.getByText("주소를 검색하면 상세 주소가 표시됩니다")).toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent("작물 이름과 주소를 먼저 입력해주세요.");
});

test("keeps the placeholder selected until the user chooses a soil sample", () => {
  const onSelect = jest.fn();
  const samples = [{ No: "1", PNU_Nm: "서울특별시 서초구 내곡동 1-890", Exam_Day: "20240101" }];
  render(
    <SoilSampleSelect
      disabled={false}
      guidance=""
      onSelect={onSelect}
      samples={samples}
      selectedSample={null}
    />
  );

  const selector = screen.getByLabelText("상세 주소 선택");
  expect(selector).toHaveValue("");
  fireEvent.change(selector, { target: { value: "0" } });
  expect(onSelect).toHaveBeenCalledWith("0");
});
