export const buildFertilizerPayload = ({ cropName, address, soilItem }) => {
  if (!soilItem || typeof soilItem !== "object") {
    return { error: "상세 주소의 토양 항목을 선택해주세요." };
  }

  return {
    payload: {
      crop_code: cropName,
      address,
      acid: soilItem.ACID,
      om: soilItem.OM,
      vldpha: soilItem.VLDPHA,
      posifert_K: soilItem.POSIFERT_K,
      posifert_Ca: soilItem.POSIFERT_CA,
      posifert_Mg: soilItem.POSIFERT_MG,
      vldsia: soilItem.VLDSIA,
      selc: soilItem.SELC,
      PNU_Nm: soilItem.PNU_Nm,
    },
  };
};

export const formatSoilValue = (value) => {
  if (value === null || value === undefined || value === "") return "N/A";
  const parsedValue = Number(value);
  if (!Number.isFinite(parsedValue)) return "N/A";
  if (Number.isInteger(parsedValue)) return parsedValue.toString();
  return parsedValue.toFixed(1);
};

export const isFertilizerNotFound = (error) => error?.response?.status === 404;

export const formatSoilSampleLabel = (sample) => {
  const address = sample?.PNU_Nm || "주소 정보 없음";
  const rawDate = String(sample?.Exam_Day || "");
  const examDate = /^\d{8}$/.test(rawDate)
    ? `${rawDate.slice(0, 4)}-${rawDate.slice(4, 6)}-${rawDate.slice(6, 8)}`
    : "미상";
  const sampleNumber = sample?.No ? ` · 시료 ${sample.No}` : "";
  return `${address} · 검사일 ${examDate}${sampleNumber}`;
};
