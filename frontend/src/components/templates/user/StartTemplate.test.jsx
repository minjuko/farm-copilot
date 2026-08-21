import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../../AuthContext";
import StartTemplate from "./StartTemplate";

jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: jest.fn(),
}));

jest.mock("../../../AuthContext", () => ({
  useAuth: jest.fn(),
}));

test("offers only the regular login path", () => {
  const navigate = jest.fn();
  useNavigate.mockReturnValue(navigate);
  useAuth.mockReturnValue({ status: "unauthenticated" });

  render(<StartTemplate />);

  expect(screen.queryByText(/테스트 계정/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "로그인하러가기" }));
  expect(navigate).toHaveBeenCalledWith("/login");
});
