import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../../AuthContext";

const NoAuthRoute = () => {
  const { status } = useAuth();

  if (status === "checking") {
    return null;
  }

  if (status === "authenticated") {
    return <Navigate to="/main" replace />;
  }

  return <Outlet />;
};

export default NoAuthRoute;
