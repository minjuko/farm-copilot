import {
  formatDetectionConfidence,
  getDetectionErrorMessage,
  normalizeDetectionResult,
  normalizeMediaUrl,
  validateDetectionFile,
} from "./detectFlow";

const file = (name, type, size = 10) => ({ name, type, size });

test("requires an image and accepts only the backend JPEG/PNG/WebP contract", () => {
  expect(validateDetectionFile(null)).toMatch(/선택/);
  expect(validateDetectionFile(file("crop.gif", "image/gif"))).toMatch(/JPEG/);
  expect(validateDetectionFile(file("crop.jpg", "text/plain"))).toMatch(/JPEG/);
  expect(validateDetectionFile(file("crop.webp", "image/webp"))).toBeNull();
});

test.each([
  [400, "Uploaded file is not a valid image.", "지원되는 이미지"],
  [400, "No pest was detected in the uploaded image.", "탐지되지 않았습니다"],
  [503, "Image detection model is not available.", "진단 모델"],
  [503, "병해 탐지 모델의 상세정보 매핑이 준비되지 않았습니다.", "상세정보 연결"],
])("maps Detect %s failures to a controlled message", (status, message, expected) => {
  expect(getDetectionErrorMessage({ response: { status, data: { message } } })).toContain(expected);
});

test("normalizes relative media URLs against the API origin", () => {
  expect(normalizeMediaUrl("/media/pest/image.jpg", "http://localhost:8000/api"))
    .toBe("http://localhost:8000/media/pest/image.jpg");
  expect(normalizeMediaUrl(undefined)).toBeNull();
});

test("rejects malformed and legacy fake-normal success results", () => {
  expect(normalizeDetectionResult({ pest_name: "0", confidence: 0 })).toBeNull();
  expect(normalizeDetectionResult({ pest_name: "탄저병", confidence: undefined })).toBeNull();
});

test("normalizes a valid result without NaN or nullable detail crashes", () => {
  const result = normalizeDetectionResult({ pest_name: "탄저병", confidence: "91.25" });
  expect(result).toMatchObject({
    pest_name: "탄저병",
    confidence: 91.25,
    occurrence_environment: "정보 없음",
    user_image_url: null,
  });
  expect(formatDetectionConfidence(undefined)).toBe("정보 없음");
});
