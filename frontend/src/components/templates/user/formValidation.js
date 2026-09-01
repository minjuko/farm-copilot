export const EMAIL_ERROR = "올바른 이메일 형식을 입력하세요.";
export const PASSWORD_ERROR = "비밀번호는 영소문자, 숫자, 특수문자를 하나 이상 포함하여 8자 이상으로 입력하세요.";
export const PASSWORD_CONFIRMATION_ERROR = "비밀번호와 비밀번호 확인이 일치하지 않습니다.";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PASSWORD_PATTERN = /^(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;

export const isValidEmail = (value) => EMAIL_PATTERN.test(String(value || "").trim());
export const isValidPassword = (value) => PASSWORD_PATTERN.test(String(value || ""));

export const getEmailError = (value, { required = true } = {}) => {
  if (!String(value || "").trim()) return required ? "이메일을 입력해주세요." : "";
  return isValidEmail(value) ? "" : EMAIL_ERROR;
};

export const getPasswordError = (value, { required = true } = {}) => {
  if (!value) return required ? "비밀번호를 입력해주세요." : "";
  return isValidPassword(value) ? "" : PASSWORD_ERROR;
};

export const getPasswordConfirmationError = (password, confirmation) => {
  if (!confirmation) return "비밀번호 확인을 입력해주세요.";
  return password === confirmation ? "" : PASSWORD_CONFIRMATION_ERROR;
};

export const getLoginPasswordError = (value) => (
  String(value || "").length ? "" : getPasswordError(value)
);

export const getLoginValidation = ({ email, password }) => ({
  email: getEmailError(email),
  password: getLoginPasswordError(password),
});

export const getSignupValidation = ({ username, email, verification_code, password1, password2 }) => ({
  username: String(username || "").trim() ? "" : "닉네임을 입력해주세요.",
  email: getEmailError(email),
  verification_code: String(verification_code || "").trim() ? "" : "인증번호를 입력해주세요.",
  password1: getPasswordError(password1),
  password2: getPasswordConfirmationError(password1, password2),
});

export const hasValidationErrors = (errors) => Object.values(errors).some(Boolean);
