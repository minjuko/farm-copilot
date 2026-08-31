import React from "react";
import { Route } from "react-router-dom";

export const renderRouteEntries = (routes) => routes.map(({ path, element }) => (
  <Route key={path} path={path} element={element} />
));
