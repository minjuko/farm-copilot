import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { fetchCapabilities } from "../../apis/capabilities";
import MainTemplate from "./MainTemplate";

jest.mock("../../apis/capabilities", () => ({
  fetchCapabilities: jest.fn(),
  normalizeCapability: (payload, name) => payload[name] || {
    status: "limited", available: false, reason: "unavailable",
  },
}));

test("renders feature cards without environment status labels", async () => {
  fetchCapabilities.mockResolvedValue({
    data: {
      detection: { status: "available", available: true },
      prediction: { status: "available", available: true },
      chatbot: { status: "archived", available: false },
      soil: { status: "limited", available: false },
    },
  });

  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <MainTemplate />
    </MemoryRouter>,
  );

  expect(screen.getByText("병해충 진단")).toBeInTheDocument();
  expect(screen.queryByText("AVAILABLE")).not.toBeInTheDocument();
});

test("renders feature cards when capability lookup fails", async () => {
  fetchCapabilities.mockRejectedValue(new Error("offline"));

  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <MainTemplate />
    </MemoryRouter>,
  );

  expect(screen.getByText("토양 분석")).toBeInTheDocument();
  expect(screen.queryByText("LIMITED")).not.toBeInTheDocument();
});
