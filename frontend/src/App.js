import React from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./AuthContext";
import { LoadingProvider } from "./LoadingContext";
import AuthRoute from "./components/layouts/AuthRoute";
import { MainLayout } from "./components/layouts/MainLayout";
import NoAuthRoute from "./components/layouts/NoAuthRoute";
import { protectedAnalysisRoutes } from "./routes/analysisRoutes";
import { protectedCommunityRoutes, publicCommunityRoutes } from "./routes/communityRoutes";
import { renderRouteEntries } from "./routes/routeUtils";
import {
  guestOnlyRoutes,
  notFoundRoute,
  protectedUserRoutes,
  publicUserRoutes,
} from "./routes/userRoutes";

const protectedRoutes = [
  ...protectedUserRoutes,
  ...protectedCommunityRoutes,
  ...protectedAnalysisRoutes,
];

function App() {
  return (
    <LoadingProvider>
      <AuthProvider>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route element={<MainLayout />}>
              {renderRouteEntries(publicUserRoutes)}
              {renderRouteEntries(publicCommunityRoutes)}

              <Route element={<NoAuthRoute />}>
                {renderRouteEntries(guestOnlyRoutes)}
              </Route>

              <Route element={<AuthRoute />}>
                {renderRouteEntries(protectedRoutes)}
              </Route>

              <Route path={notFoundRoute.path} element={notFoundRoute.element} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </LoadingProvider>
  );
}

export default App;
