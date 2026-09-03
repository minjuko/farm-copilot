import { instance } from "./client";

const ensureCsrfToken = () => instance.get("/login/auth_check/");

export const checkUsername = (username) => {
  return instance.get("/login/check_username/", { params: { username } });
};

export const sendVerificationEmail = async (email) => {
  await ensureCsrfToken();
  return instance.post("/login/send_verification_email/", { email });
};

export const signupUser = async (formData) => {
  await ensureCsrfToken();
  return instance.post("/login/signup/", formData);
};

export const loginUser = async (email, password) => {
  await ensureCsrfToken();
  return instance.post("/login/login/", { email, password });
};

export const checkAuthStatus = () => {
  return instance.get("/login/auth_check/");
};

export const logoutUser = () => {
  return instance.post("/login/logout/");
};

export const changePassword = (formData) => {
  return instance.post("/login/change_password/", formData);
};

export const changeUsername = (newUsername) => {
  return instance.post("/login/change_username/", { new_username: newUsername });
};

export const deleteAccount = (password) => {
  return instance.post("/login/delete_account/", { password });
};

export const requestPasswordReset = async (email) => {
  await ensureCsrfToken();
  return instance.post("/login/password_reset/", { email });
};

export const confirmPasswordReset = async (uid, token, newPassword) => {
  await ensureCsrfToken();
  return instance.post("/login/password_reset_confirm/", {
    uid,
    token,
    new_password: newPassword,
  });
};

