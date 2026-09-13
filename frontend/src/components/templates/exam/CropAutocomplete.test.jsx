import { fireEvent, render, screen } from "@testing-library/react";
import CropAutocomplete from "./CropAutocomplete";

test("shows all crops when reopening an already selected crop", () => {
  render(
    <CropAutocomplete
      cropName="가지(노지)"
      cropNames={["가지(노지)", "감자", "땅콩"]}
      onChange={jest.fn()}
      onSelect={jest.fn()}
    />
  );

  fireEvent.click(screen.getByLabelText("작물 이름"));

  expect(screen.getByRole("option", { name: "가지(노지)" })).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "감자" })).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "땅콩" })).toBeInTheDocument();
});

test("filters the list after the user starts typing", () => {
  const onChange = jest.fn();
  const { rerender } = render(
    <CropAutocomplete
      cropName="가지(노지)"
      cropNames={["가지(노지)", "감자", "땅콩"]}
      onChange={onChange}
      onSelect={jest.fn()}
    />
  );

  fireEvent.change(screen.getByLabelText("작물 이름"), { target: { value: "감" } });
  expect(onChange).toHaveBeenCalledWith("감");
  rerender(
    <CropAutocomplete
      cropName="감"
      cropNames={["가지(노지)", "감자", "땅콩"]}
      onChange={onChange}
      onSelect={jest.fn()}
    />
  );

  expect(screen.getByRole("option", { name: "감자" })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: "땅콩" })).not.toBeInTheDocument();
});
