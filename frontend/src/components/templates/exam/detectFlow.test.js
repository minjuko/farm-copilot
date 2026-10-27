import {
  formatDetectionConfidence,
  formatDetectionConfidencePercent,
  classifyDetectionError,
  getDetectionErrorMessage,
  normalizeDetectionResult,
  normalizeDetectionHistory,
  normalizeMediaUrl,
  validateDetectionFile,
} from "./detectFlow";

const file = (name, type, size = 10) => ({ name, type, size });

test("requires an image and accepts only the backend JPEG/PNG/WebP contract", () => {
  expect(validateDetectionFile(null)).toMatch(/선택/);
  expect(validateDetectionFile(file("crop.gif", "image/gif"))).toMatch(/JPEG/);
  expect(validateDetectionFile(file("crop.jpg", "text/plain"))).toMatch(/JPEG/);
  expect(validateDetectionFile(file("crop.jpg", "image/png"))).toMatch(/JPEG/);
  expect(validateDetectionFile(file("crop.webp", "image/webp"))).toBeNull();
});

test("enforces the server upload size limit in the browser", () => {
  expect(validateDetectionFile(file("crop.jpg", "image/jpeg", 10 * 1024 * 1024))).toBeNull();
  expect(validateDetectionFile(file("crop.jpg", "image/jpeg", 10 * 1024 * 1024 + 1)))
    .toMatch(/10 MiB/);
});

test.each([
  [400, "Uploaded file is not a valid image.", "10 MiB"],
  [400, "No pest was detected in the uploaded image.", "지원 대상 질병을 확인하지 못했습니다"],
  [503, "Image detection model is not available.", "진단 모델"],
  [503, "병해 탐지 모델의 상세정보 매핑이 준비되지 않았습니다.", "상세정보 연결"],
])("maps Detect %s failures to a controlled message", (status, message, expected) => {
  expect(getDetectionErrorMessage({ response: { status, data: { message } } })).toContain(expected);
});

test("explains server-side upload size and image decoding rejections", () => {
  const error = { response: { status: 400, data: { message: "Image dimensions must not exceed 20 megapixels." } } };
  expect(classifyDetectionError(error).status).toBe("invalid_image");
  expect(getDetectionErrorMessage(error)).toContain("2천만 픽셀");
});

test("normalizes relative media URLs against the API origin", () => {
  expect(normalizeMediaUrl("/media/pest/image.jpg", "http://localhost:8000/api"))
    .toBe("http://localhost:8000/media/pest/image.jpg");
  expect(normalizeMediaUrl(undefined)).toBeNull();
});

test("rejects malformed and legacy fake-normal success results", () => {
  expect(normalizeDetectionResult({ session_id: 1, pest_name: "0", confidence: 0 })).toBeNull();
  expect(normalizeDetectionResult({ session_id: 1, pest_name: "탄저병", confidence: undefined })).toBeNull();
  expect(normalizeDetectionResult({ pest_name: "탄저병", confidence: 91 })).toBeNull();
});

test("normalizes a valid result without NaN or nullable detail crashes", () => {
  const result = normalizeDetectionResult({ session_id: 1, pest_name: "탄저병", confidence: "91.25" });
  expect(result).toMatchObject({
    pest_name: "탄저병",
    confidence: 91.25,
    occurrence_environment: "정보 없음",
    user_image_url: null,
  });
  expect(formatDetectionConfidence(undefined)).toBe("정보 없음");
});

test.each([null, undefined, "", "not-a-number", NaN, Infinity, -0.01, 100.01])(
  "rejects confidence outside the backend 0..100 contract: %p",
  (confidence) => {
    expect(normalizeDetectionResult({ session_id: 1, pest_name: "탄저병", confidence })).toBeNull();
    expect(formatDetectionConfidencePercent(confidence)).toBe("정보 없음");
  }
);

test.each([
  [0, "0.00%"],
  ["60", "60.00%"],
  [91.256, "91.26%"],
  [100, "100.00%"],
])("formats API confidence %p as a 0..100 percentage", (confidence, expected) => {
  expect(formatDetectionConfidencePercent(confidence)).toBe(expected);
});

test("rejects an entire malformed history instead of rendering a partial fake result", () => {
  expect(normalizeDetectionHistory([
    { session_id: 1, pest_name: "탄저병", confidence: 91 },
    { session_id: 2, pest_name: "흰가루병", confidence: null },
  ])).toBeNull();
});

test("classifies existing HTTP and client-side failure contracts", () => {
  expect(classifyDetectionError({ response: { status: 400, data: { message: "No pest was detected in the uploaded image." } } }).status)
    .toBe("no_detection");
  expect(classifyDetectionError({ response: { status: 503, data: {} } }).status)
    .toBe("service_unavailable");
  expect(classifyDetectionError({ code: "MALFORMED_DETECTION_RESPONSE" }).status)
    .toBe("invalid_response");
  expect(classifyDetectionError(new Error("offline")).status).toBe("request_failed");
  expect(getDetectionErrorMessage({ response: { status: 401 } })).toContain("로그인이 필요합니다");
  expect(getDetectionErrorMessage({ response: { status: 403 } })).toContain("접근할 권한");
});
