import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../../AuthContext";

const AuthRoute = () => {
  const { status } = useAuth();

  if (status === "checking") {
    return null;
  }

  if (status === "authenticated") {
    return <Outlet />;
  }

  return <Navigate to="/login" replace />;
};

export default AuthRoute;
