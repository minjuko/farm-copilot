const toFiniteNumber = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

export const isValidRatioTotal = (ratios) => {
  const total = ratios.reduce((sum, ratio) => sum + ratio, 0);
  return Math.abs(total - 1) < 1e-9;
};

export const buildPredictionPayload = ({ landArea, region, crops, sessionId }) => {
  const normalizedLandArea = toFiniteNumber(landArea);
  if (normalizedLandArea == null || normalizedLandArea <= 0) {
    return { error: "경작 면적은 0보다 큰 숫자로 입력해주세요." };
  }
  if (!region || !region.trim()) {
    return { error: "지역을 선택해주세요." };
  }
  if (!Array.isArray(crops) || crops.length === 0) {
    return { error: "작물을 하나 이상 추가해주세요." };
  }

  const cropNames = crops.map((crop) => crop.name?.trim()).filter(Boolean);
  const cropRatios = crops.map((crop) => toFiniteNumber(crop.ratio));
  if (cropNames.length !== crops.length || cropRatios.some((ratio) => ratio == null || ratio <= 0)) {
    return { error: "작물 비율은 0보다 큰 숫자로 입력해주세요." };
  }
  if (new Set(cropNames).size !== cropNames.length) {
    return { error: "같은 작물은 중복해서 추가할 수 없습니다." };
  }
  if (!isValidRatioTotal(cropRatios)) {
    return { error: "작물 비율의 합은 1이 되어야 합니다." };
  }

  return { payload: {
    land_area: normalizedLandArea,
    crop_names: cropNames,
    crop_ratios: cropRatios,
    region: region.trim(),
    session_id: sessionId,
  } };
};

export const finiteNumberOrZero = (value) => {
  const number = toFiniteNumber(value);
  return number ?? 0;
};

export const removeCropAt = (crops, index) => crops.filter((_, cropIndex) => cropIndex !== index);

export const normalizePredictionResult = (predictionPayload) => ({
  ...predictionPayload,
  land_area: finiteNumberOrZero(predictionPayload?.land_area),
  total_income: finiteNumberOrZero(predictionPayload?.total_income),
  results: Array.isArray(predictionPayload?.results) ? predictionPayload.results.map((cropResult) => ({
    ...cropResult,
    adjusted_data: cropResult?.adjusted_data && typeof cropResult.adjusted_data === "object" ? cropResult.adjusted_data : {},
    crop_chart_data: Array.isArray(cropResult?.crop_chart_data) ? cropResult.crop_chart_data : [],
    price: finiteNumberOrZero(cropResult?.price),
    r2_score: finiteNumberOrZero(cropResult?.r2_score),
    rmse: finiteNumberOrZero(cropResult?.rmse),
  })) : [],
});
