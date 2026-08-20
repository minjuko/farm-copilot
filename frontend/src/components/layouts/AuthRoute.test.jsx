import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "../../AuthContext";
import { checkAuthStatus, logoutUser } from "../../apis/user";
import AuthRoute from "./AuthRoute";
import NoAuthRoute from "./NoAuthRoute";

jest.mock("../../apis/user", () => ({
  checkAuthStatus: jest.fn(),
  logoutUser: jest.fn(),
}));

const Location = () => {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
};

const AuthControls = () => {
  const { status, establishSession, logout } = useAuth();
  return (
    <>
      <div data-testid="status">{status}</div>
      <button onClick={() => establishSession({ username: "farmer" })}>login</button>
      <button onClick={logout}>logout</button>
    </>
  );
};

const renderRoutes = (initialPath, extra = null) => render(
  <MemoryRouter initialEntries={[initialPath]}>
    <AuthProvider>
      <Location />
      {extra}
      <Routes>
        <Route element={<AuthRoute />}>
          <Route path="/mypage" element={<div>mypage</div>} />
          <Route path="/my_posts" element={<div>my posts</div>} />
          <Route path="/my_commented_posts" element={<div>my commented posts</div>} />
          <Route path="/cropselection" element={<div>prediction sessions</div>} />
          <Route path="/sessiondetails/:sessionId" element={<div>prediction detail</div>} />
          <Route path="/soil" element={<div>soil exam</div>} />
          <Route path="/soillist" element={<div>soil list</div>} />
          <Route path="/soil_details" element={<div>soil detail</div>} />
          <Route path="/diagnosis" element={<div>detect upload</div>} />
          <Route path="/diagnosislist" element={<div>detect history</div>} />
          <Route path="/info" element={<div>detect result</div>} />
        </Route>
        <Route element={<NoAuthRoute />}>
          <Route path="/login" element={<div>login page</div>} />
        </Route>
        <Route path="/main" element={<div>main page</div>} />
        <Route path="/password-reset-confirm" element={<div>reset confirm</div>} />
        <Route path="*" element={<Navigate to="/main" />} />
      </Routes>
    </AuthProvider>
  </MemoryRouter>
);

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
});

test("does not redirect a protected route while auth is checking", async () => {
  let resolveCheck;
  checkAuthStatus.mockReturnValue(new Promise((resolve) => { resolveCheck = resolve; }));

  renderRoutes("/mypage");

  expect(screen.getByTestId("location")).toHaveTextContent("/mypage");
  expect(screen.queryByText("mypage")).not.toBeInTheDocument();
  expect(screen.queryByText("login page")).not.toBeInTheDocument();

  await act(async () => {
    resolveCheck({ data: { is_authenticated: false } });
  });
  expect(await screen.findByText("login page")).toBeInTheDocument();
});

test("blocks unauthenticated users from protected routes", async () => {
  checkAuthStatus.mockResolvedValue({ data: { is_authenticated: false } });
  renderRoutes("/mypage");
  expect(await screen.findByText("login page")).toBeInTheDocument();
  expect(screen.getByTestId("location")).toHaveTextContent("/login");
});

test("allows authenticated users into protected routes", async () => {
  checkAuthStatus.mockResolvedValue({ data: { is_authenticated: true, username: "farmer" } });
  renderRoutes("/mypage");
  expect(await screen.findByText("mypage")).toBeInTheDocument();
});

test("login and logout update shared auth state immediately", async () => {
  checkAuthStatus.mockResolvedValue({ data: { is_authenticated: false } });
  logoutUser.mockResolvedValue({ data: { status: "success" } });
  renderRoutes("/main", <AuthControls />);

  await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"));
  fireEvent.click(screen.getByText("login"));
  expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
  fireEvent.click(screen.getByText("logout"));
  await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"));
  expect(logoutUser).toHaveBeenCalledTimes(1);
});

test("password reset confirm remains public for unauthenticated users", async () => {
  checkAuthStatus.mockResolvedValue({ data: { is_authenticated: false } });
  renderRoutes("/password-reset-confirm?uid=uid&token=token", <AuthControls />);
  expect(await screen.findByText("reset confirm")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"));
});

test("auth check failures become controlled unauthenticated state", async () => {
  checkAuthStatus.mockRejectedValue(new Error("network"));
  renderRoutes("/main", <AuthControls />);
  await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"));
});

test.each(["/my_posts", "/my_commented_posts"])("protects community route %s", async (path) => {
  checkAuthStatus.mockResolvedValue({ data: { is_authenticated: false } });
  renderRoutes(path);
  expect(await screen.findByText("login page")).toBeInTheDocument();
});

test.each(["/cropselection", "/sessiondetails/session-1"])("protects prediction route %s", async (path) => {
  checkAuthStatus.mockResolvedValue({ data: { is_authenticated: false } });
  renderRoutes(path);
  expect(await screen.findByText("login page")).toBeInTheDocument();
});

test.each(["/soil", "/soillist", "/soil_details"])("protects soil route %s", async (path) => {
  checkAuthStatus.mockResolvedValue({ data: { is_authenticated: false } });
  renderRoutes(path);
  expect(await screen.findByText("login page")).toBeInTheDocument();
});

test.each(["/diagnosis", "/diagnosislist", "/info"])("protects Detect route %s", async (path) => {
  checkAuthStatus.mockResolvedValue({ data: { is_authenticated: false } });
  renderRoutes(path);
  expect(await screen.findByText("login page")).toBeInTheDocument();
});
