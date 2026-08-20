import { buildFertilizerPayload, formatSoilValue } from "./soilFlow";

const selectedSoilItem = {
  No: 17,
  PNU_Nm: "완주군 이서면 용서리 672-12",
  ACID: "6.1",
  OM: "25",
  VLDPHA: "310",
  POSIFERT_K: "0.42",
  POSIFERT_CA: "5.2",
  POSIFERT_MG: "1.3",
  VLDSIA: "120",
  SELC: "1.2",
  ELCD: "legacy-value",
};

test("builds fertilizer input from one selected SoilExam item and consumes SELC", () => {
  const { payload, error } = buildFertilizerPayload({
    cropName: "감자",
    address: "완주군 이서면 용서리 672-12",
    soilItem: selectedSoilItem,
  });
  expect(error).toBeUndefined();
  expect(payload).toEqual({
    crop_code: "감자", address: "완주군 이서면 용서리 672-12",
    acid: "6.1", om: "25", vldpha: "310", posifert_K: "0.42",
    posifert_Ca: "5.2", posifert_Mg: "1.3", vldsia: "120",
    selc: "1.2", PNU_Nm: "완주군 이서면 용서리 672-12",
  });
  expect(payload).not.toHaveProperty("ELCD");
});

test("does not replace a missing soil value with a fabricated zero", () => {
  const { payload } = buildFertilizerPayload({
    cropName: "감자", address: "완주군",
    soilItem: { ...selectedSoilItem, SELC: undefined },
  });
  expect(payload.selc).toBeUndefined();
});

test.each([null, undefined, "", "not-a-number"])(
  "formats malformed soil value %p without throwing or displaying NaN",
  (value) => expect(formatSoilValue(value)).toBe("N/A")
);

test("requires a selected SoilExam item before fertilizer submission", () => {
  expect(buildFertilizerPayload({ cropName: "감자", address: "완주군", soilItem: null }).error)
    .toMatch(/토양 항목/);
});
