import {
  EMAIL_ERROR,
  PASSWORD_CONFIRMATION_ERROR,
  PASSWORD_ERROR,
  getEmailError,
  getLoginValidation,
  getPasswordConfirmationError,
  getPasswordError,
  getSignupValidation,
  hasValidationErrors,
  isValidEmail,
  isValidPassword,
} from "./formValidation";

test.each([
  ["farmer@example.com", true],
  ["farmer", false],
  ["@example.com", false],
])("validates email %s", (email, expected) => {
  expect(isValidEmail(email)).toBe(expected);
});

test.each([
  ["farm123!", true],
  ["FARM123!", false],
  ["farmer!!", false],
  ["farmer12", false],
])("validates the shared password contract", (password, expected) => {
  expect(isValidPassword(password)).toBe(expected);
});

test("returns consistent field messages", () => {
  expect(getEmailError("invalid")).toBe(EMAIL_ERROR);
  expect(getPasswordError("weak")).toBe(PASSWORD_ERROR);
  expect(getPasswordConfirmationError("farm123!", "different1!")).toBe(PASSWORD_CONFIRMATION_ERROR);
});

test("validates login and signup forms without component state", () => {
  expect(hasValidationErrors(getLoginValidation({ email: "farmer@example.com", password: "farm123!" }))).toBe(false);
  expect(hasValidationErrors(getSignupValidation({
    username: "farmer",
    email: "farmer@example.com",
    verification_code: "123456",
    password1: "farm123!",
    password2: "farm123!",
  }))).toBe(false);
  expect(hasValidationErrors(getSignupValidation({
    username: "",
    email: "bad",
    verification_code: "",
    password1: "weak",
    password2: "different",
  }))).toBe(true);
});
