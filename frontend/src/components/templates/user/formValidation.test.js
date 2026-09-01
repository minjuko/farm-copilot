import {
  EMAIL_ERROR,
  PASSWORD_CONFIRMATION_ERROR,
  PASSWORD_ERROR,
  getEmailError,
  getLoginValidation,
  getLoginPasswordError,
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

test("login requires a password but accepts existing credentials outside the new-password policy", () => {
  expect(getLoginPasswordError("")).not.toBe("");
  expect(getLoginPasswordError("existing-password")).toBe("");
  expect(getLoginValidation({ email: "farmer@example.com", password: "existing-password" }))
    .toEqual({ email: "", password: "" });
});

test("login keeps the existing email policy and signup keeps the new-password policy", () => {
  expect(getLoginValidation({ email: "farmer", password: "existing-password" }).email)
    .toBe(EMAIL_ERROR);
  expect(getSignupValidation({
    username: "farmer",
    email: "farmer@example.com",
    verification_code: "123456",
    password1: "existing-password",
    password2: "existing-password",
  }).password1).toBe(PASSWORD_ERROR);
});
