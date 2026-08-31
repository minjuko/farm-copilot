import React from "react";
import MainTemplate from "../components/templates/MainTemplate";
import NotFound from "../components/templates/NotFound";
import LoginTemplate from "../components/templates/user/LoginTemplate";
import PasswordResetConfirmTemplate from "../components/templates/user/PasswordResetConfirmTemplate";
import PasswordResetTemplate from "../components/templates/user/PasswordResetTemplate";
import PolicyAgreement from "../components/templates/user/PolicyAgreement";
import PrivacyPolicyPage from "../components/templates/user/PrivacyPolicyPage";
import StartTemplate from "../components/templates/user/StartTemplate";
import TermsOfService from "../components/templates/user/TermsOfService";
import MyPageTemplate from "../components/templates/user/MyPageTemplate";

export const publicUserRoutes = [
  { path: "/", element: <StartTemplate /> },
  { path: "/main", element: <MainTemplate /> },
  { path: "/privacy-policy", element: <PrivacyPolicyPage /> },
  { path: "/terms-of-service", element: <TermsOfService /> },
  { path: "/password-reset-confirm", element: <PasswordResetConfirmTemplate /> },
];

export const guestOnlyRoutes = [
  { path: "/signup", element: <PolicyAgreement /> },
  { path: "/login", element: <LoginTemplate /> },
  { path: "/password_reset", element: <PasswordResetTemplate /> },
];

export const protectedUserRoutes = [
  { path: "/mypage", element: <MyPageTemplate /> },
];

export const notFoundRoute = { path: "*", element: <NotFound /> };
