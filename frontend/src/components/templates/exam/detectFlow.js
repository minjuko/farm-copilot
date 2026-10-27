const ALLOWED_IMAGE_TYPES_BY_EXTENSION = {
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
};
export const MAX_DETECTION_UPLOAD_BYTES = 10 * 1024 * 1024;
const DETECT_API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

export const validateDetectionFile = (file) => {
  if (!file) return "진단할 이미지를 선택해주세요.";
  if (!file.size) return "지원되는 이미지 파일을 선택해주세요.";

  if (file.size > MAX_DETECTION_UPLOAD_BYTES) return "\uc774\ubbf8\uc9c0 \ud30c\uc77c\uc740 10 MiB \uc774\ud558\ub85c \uc120\ud0dd\ud574\uc8fc\uc138\uc694.";

  const extension = file.name?.split(".").pop()?.toLowerCase();
  if (ALLOWED_IMAGE_TYPES_BY_EXTENSION[extension] !== file.type) {
    return "JPEG, PNG, WebP 이미지 파일만 선택할 수 있습니다.";
  }
  return null;
};

export const getDetectionErrorMessage = (error) => {
  const outcome = classifyDetectionError(error);

  if (outcome.status === "invalid_response") {
    return "진단 결과 응답 형식이 올바르지 않습니다. 잠시 후 다시 시도해주세요.";
  }
  if (outcome.status === "service_unavailable" && outcome.isMappingUnavailable) {
    return "병해충 상세정보 연결이 준비되지 않아 현재 진단 결과를 제공할 수 없습니다.";
  }
  if (outcome.status === "service_unavailable") return "진단 모델을 현재 사용할 수 없습니다. 잠시 후 다시 시도해주세요.";
  if (outcome.status === "no_detection") {
    return "이미지에서 지원 대상 질병을 확인하지 못했습니다. 선명한 잎과 병징이 보이도록 촬영해 다른 이미지로 다시 시도해 주세요. 이 결과만으로 정상 여부를 판단할 수는 없습니다.";
  }
  if (outcome.status === "invalid_image") return "JPEG, PNG, WebP 형식의 손상되지 않은 10 MiB 이하 이미지를 선택해주세요. 이미지 해상도는 2천만 픽셀 이하여야 합니다.";
  if (outcome.status === "invalid_request") return "지원되는 이미지 파일을 선택해주세요.";
  if (outcome.status === "unauthorized") return "로그인이 필요합니다. 로그인한 뒤 다시 시도해 주세요.";
  if (outcome.status === "forbidden") return "이 진단 정보에 접근할 권한이 없습니다.";
  if (outcome.status === "request_failed") return "서버에 연결할 수 없습니다. 연결을 확인한 뒤 다시 시도해주세요.";
  return "이미지 진단 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
};

export const classifyDetectionError = (error) => {
  if (error?.code === "MALFORMED_DETECTION_RESPONSE") {
    return { status: "invalid_response" };
  }

  const httpStatus = error?.response?.status;
  const backendMessage = error?.response?.data?.message || "";
  if (httpStatus === 400 && backendMessage.includes("No pest was detected")) {
    return { status: "no_detection" };
  }
  if (httpStatus === 400 && [
    "Uploaded file is not a valid image.",
    "Only JPEG, PNG, and WebP images are allowed.",
    "Uploaded image is empty.",
    "Image file must be 10 MiB or smaller.",
    "Image dimensions must not exceed 20 megapixels.",
  ].some((message) => backendMessage.includes(message))) {
    return { status: "invalid_image" };
  }
  if (httpStatus === 503) {
    return {
      status: "service_unavailable",
      isMappingUnavailable: backendMessage.includes("상세정보 매핑"),
    };
  }
  if (httpStatus === 401) return { status: "unauthorized" };
  if (httpStatus === 403) return { status: "forbidden" };
  if (httpStatus === 400) return { status: "invalid_request" };
  if (!error?.response) return { status: "request_failed" };
  return { status: "error" };
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

export const normalizeDetectionResult = (detectionPayload) => {
  const rawConfidence = detectionPayload?.confidence;
  const acceptsConfidenceType = typeof rawConfidence === "number"
    || (typeof rawConfidence === "string" && rawConfidence.trim() !== "");
  const confidence = acceptsConfidenceType ? Number(rawConfidence) : Number.NaN;
  const sessionId = detectionPayload?.session_id;
  const hasSessionId = (typeof sessionId === "number" && Number.isInteger(sessionId) && sessionId > 0)
    || (typeof sessionId === "string" && sessionId.trim() !== "");
  if (!detectionPayload || typeof detectionPayload.pest_name !== "string" || !detectionPayload.pest_name.trim()
      || detectionPayload.pest_name === "0" || !hasSessionId || !Number.isFinite(confidence)
      || confidence < 0 || confidence > 100) {
    return null;
  }

  return {
    ...detectionPayload,
    pest_name: detectionPayload.pest_name.trim(),
    confidence,
    occurrence_environment: detectionPayload.occurrence_environment || "정보 없음",
    symptom_description: detectionPayload.symptom_description || "정보 없음",
    prevention_methods: detectionPayload.prevention_methods || "정보 없음",
    pesticide_name: Array.isArray(detectionPayload.pesticide_name)
      ? detectionPayload.pesticide_name.filter(Boolean).join("\n")
      : (typeof detectionPayload.pesticide_name === "string" ? detectionPayload.pesticide_name : ""),
    information_source: detectionPayload.information_source || "",
    information_source_url: detectionPayload.information_source_url || "",
    reference_image_license: detectionPayload.reference_image_license || "",
    detection_date: detectionPayload.detection_date || "정보 없음",
    user_image_url: normalizeMediaUrl(detectionPayload.user_image_url),
    db_image_url: normalizeMediaUrl(detectionPayload.db_image_url),
  };
};

export const normalizeDetectionHistory = (payload) => {
  if (!Array.isArray(payload)) return null;
  const sessions = payload.map(normalizeDetectionResult);
  return sessions.every(Boolean) ? sessions : null;
};

export const formatDetectionConfidence = (value) => {
  const acceptsType = typeof value === "number"
    || (typeof value === "string" && value.trim() !== "");
  const confidence = acceptsType ? Number(value) : Number.NaN;
  return Number.isFinite(confidence) && confidence >= 0 && confidence <= 100
    ? confidence.toFixed(2)
    : "정보 없음";
};

export const formatDetectionConfidencePercent = (value) => {
  const formatted = formatDetectionConfidence(value);
  return formatted === "정보 없음" ? formatted : `${formatted}%`;
};
