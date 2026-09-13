import React from "react";
import { Outlet, useLocation } from "react-router-dom";
import { GNB } from "./GNB";
import MainTopBar from "./MainTopBar";
import PageTopBar from "./PageTopBar";
import styled from "styled-components";
import { color, zIndex } from "../../styles/theme";

const Container = styled.div`
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: ${color("background")};
`;

const Header = styled.div`
  position: sticky;
  top: 0;
  z-index: ${zIndex("header")};
  background-color: ${color("surface")};
`;

const Footer = styled.div`
  height: calc(72px + env(safe-area-inset-bottom));
  flex: 0 0 calc(72px + env(safe-area-inset-bottom));
  background: ${color("surface")};
`;

export const MainLayout = () => {
  const location = useLocation();
  const isMainPage = location.pathname === "/main" || location.pathname === "/";
  const isStartPage = location.pathname === "/";

  return (
    <Container>
      <Header>{isMainPage ? <MainTopBar /> : <PageTopBar />}</Header>
      <Outlet />
      {!isStartPage && (
        <Footer>
          <GNB />
        </Footer>
      )}
    </Container>
  );
};
