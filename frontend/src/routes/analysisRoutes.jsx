import React from "react";
import ChatListTemplate from "../components/templates/chat/ChatListTemplate";
import ChatTemplate from "../components/templates/chat/ChatTemplate";
import CropSelectionPage from "../components/templates/crop/CropSelectionPage";
import CropTest from "../components/templates/crop/CropTest";
import SessionDetails from "../components/templates/crop/SessionDetails";
import DiagnosisListTemplate from "../components/templates/exam/DiagnosisListTemplate";
import DiagnosisTemplate from "../components/templates/exam/DiagnosisTemplate";
import InfoTemplate from "../components/templates/exam/InfoTemplate";
import SoilDataDetails from "../components/templates/exam/SoilDataDetails";
import SoilListTemplate from "../components/templates/exam/SoilListTemplate";
import SoilTemplate from "../components/templates/exam/SoilTemplate";

export const predictionRoutes = [
  { path: "/crop-selection", element: <CropSelectionPage /> },
  { path: "/crop-test", element: <CropTest /> },
  { path: "/session-details/:sessionId", element: <SessionDetails /> },
];

export const diagnosisRoutes = [
  { path: "/diagnosis", element: <DiagnosisTemplate /> },
  { path: "/diagnosis-list", element: <DiagnosisListTemplate /> },
  { path: "/info", element: <InfoTemplate /> },
  { path: "/info/:sessionId", element: <InfoTemplate /> },
];

export const soilRoutes = [
  { path: "/soil", element: <SoilTemplate /> },
  { path: "/soil-list", element: <SoilListTemplate /> },
  { path: "/soil-details", element: <SoilDataDetails /> },
  { path: "/soil-details/:sessionId", element: <SoilDataDetails /> },
];

export const chatRoutes = [
  { path: "/chat-list", element: <ChatListTemplate /> },
  { path: "/chat/:sessionId", element: <ChatTemplate /> },
];

export const protectedAnalysisRoutes = [
  ...predictionRoutes,
  ...diagnosisRoutes,
  ...soilRoutes,
  ...chatRoutes,
];
