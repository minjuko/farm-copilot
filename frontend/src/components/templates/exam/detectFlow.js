const ALLOWED_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const ALLOWED_IMAGE_EXTENSIONS = new Set(["jpg", "jpeg", "png", "webp"]);
const DETECT_API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

export const validateDetectionFile = (file) => {
  if (!file) return "진단할 이미지를 선택해주세요.";
  if (!file.size) return "지원되는 이미지 파일을 선택해주세요.";

  const extension = file.name?.split(".").pop()?.toLowerCase();
  if (!ALLOWED_IMAGE_TYPES.has(file.type) || !ALLOWED_IMAGE_EXTENSIONS.has(extension)) {
    return "JPEG, PNG, WebP 이미지 파일만 선택할 수 있습니다.";
  }
  return null;
};

export const getDetectionErrorMessage = (error) => {
  const status = error?.response?.status;
  const backendMessage = error?.response?.data?.message || "";

  if (status === 503 && backendMessage.includes("상세정보 매핑")) {
    return "병해충 상세정보 연결이 준비되지 않아 현재 진단 결과를 제공할 수 없습니다.";
  }
  if (status === 503) return "진단 모델을 현재 사용할 수 없습니다. 잠시 후 다시 시도해주세요.";
  if (status === 400 && backendMessage.includes("No pest was detected")) {
    return "이미지에서 병해충이 탐지되지 않았습니다.";
  }
  if (status === 400) return "지원되는 이미지 파일을 선택해주세요.";
  return "이미지 진단 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
};

export const normalizeMediaUrl = (value, baseUrl = DETECT_API_BASE_URL) => {
  if (typeof value !== "string" || !value.trim()) return null;
  try {
    const url = new URL(value, `${baseUrl.replace(/\/+$/, "")}/`);
    return ["http:", "https:", "blob:", "data:"].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
};

export const normalizeDetectionResult = (data) => {
  const confidence = Number(data?.confidence);
  if (!data || typeof data.pest_name !== "string" || !data.pest_name.trim()
      || data.pest_name === "0" || !Number.isFinite(confidence)) {
    return null;
  }

  return {
    ...data,
    pest_name: data.pest_name.trim(),
    confidence,
    occurrence_environment: data.occurrence_environment || "정보 없음",
    symptom_description: data.symptom_description || "정보 없음",
    prevention_methods: data.prevention_methods || "정보 없음",
    pesticide_name: typeof data.pesticide_name === "string" ? data.pesticide_name : "",
    detection_date: data.detection_date || "정보 없음",
    user_image_url: normalizeMediaUrl(data.user_image_url),
    db_image_url: normalizeMediaUrl(data.db_image_url),
  };
};

export const formatDetectionConfidence = (value) => {
  const confidence = Number(value);
  return Number.isFinite(confidence) ? confidence.toFixed(2) : "정보 없음";
};
