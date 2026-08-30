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

test("shows backend capability state on every feature card", async () => {
  fetchCapabilities.mockResolvedValue({
    data: {
      detection: { status: "available", available: true },
      prediction: { status: "available", available: true },
      chatbot: { status: "archived", available: false },
      soil: { status: "limited", available: false },
    },
  });

  render(<MemoryRouter><MainTemplate /></MemoryRouter>);

  expect((await screen.findAllByText("AVAILABLE"))).toHaveLength(2);
  expect(screen.getByText("ARCHIVED")).toBeInTheDocument();
  expect(screen.getByText("LIMITED")).toBeInTheDocument();
  expect(fetchCapabilities).toHaveBeenCalledTimes(1);
});

test("fails closed when capability lookup fails", async () => {
  fetchCapabilities.mockRejectedValue(new Error("offline"));

  render(<MemoryRouter><MainTemplate /></MemoryRouter>);

  expect((await screen.findAllByText("LIMITED"))).toHaveLength(4);
});
