import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  FaHome,
  FaBug,
  FaChartLine,
  FaUser,
  FaCommentDots,
} from "react-icons/fa";
import styled from "styled-components";

const Nav = styled.nav`
  position: fixed;
  bottom: 0;
  z-index: 50;
  width: 100%;
  background-color: #f3f4f6;
  border-top: 1px solid #e5e7eb;
`;

const Wrapper = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 8px 26px;
`;

const MenuLink = styled(Link)`
  flex: 1;
  text-align: center;
  text-decoration: none;
`;

const IconWrapper = styled.div`
  display: inline-block;
  color: ${({ $isActive }) => ($isActive ? "#4AAA87" : "#9ca3af")};
`;

const MenuText = styled.div`
  font-size: 12px;
  font-weight: bold;
  color: ${({ $isActive }) => ($isActive ? "#4AAA87" : "#6b7280")};
`;

const ChatIconWrapper = styled.button`
  position: relative;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background-color: #4AAA87;
  border: 0;
  padding: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: -40px;
  z-index: 1;
  cursor: pointer;
`;

const ChatIcon = styled(FaCommentDots)`
  color: #fff;
  font-size: 24px;
`;

export const GNB = () => {
  const [currentPage, setCurrentPage] = useState("/");
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    setCurrentPage(location.pathname);
  }, [location]);

  const handleChatIconClick = () => {
    navigate("/chat-list");
  };

  return (
    <Nav>
      <Wrapper>
        <MenuLink to="/main" className={currentPage === "/main" ? "active" : ""}>
          <IconWrapper $isActive={currentPage === "/main"}>
            <FaHome size={24} />
          </IconWrapper>
          <MenuText $isActive={currentPage === "/main"}>홈</MenuText>
        </MenuLink>
        <MenuLink to="/diagnosis-list" className={currentPage === "/diagnosis-list" ? "active" : ""}>
          <IconWrapper $isActive={currentPage === "/diagnosis-list"}>
            <FaBug size={24} />
          </IconWrapper>
          <MenuText $isActive={currentPage === "/diagnosis-list"}>병해충 진단</MenuText>
        </MenuLink>
        <ChatIconWrapper
          onClick={handleChatIconClick}
          aria-label="농업 GPT 열기"
        >
          <ChatIcon />
        </ChatIconWrapper>
        <MenuLink
          to="/crop-selection"
          className={currentPage === "/crop-selection" ? "active" : ""}
        >
          <IconWrapper $isActive={currentPage === "/crop-selection"}>
            <FaChartLine size={24} />
          </IconWrapper>
          <MenuText $isActive={currentPage === "/crop-selection"}>수익 예측</MenuText>
        </MenuLink>
        <MenuLink
          to="/my-page"
          className={currentPage === "/my-page" ? "active" : ""}
        >
          <IconWrapper $isActive={currentPage === "/my-page"}>
            <FaUser size={24} />
          </IconWrapper>
          <MenuText $isActive={currentPage === "/my-page"}>MY</MenuText>
        </MenuLink>
      </Wrapper>
    </Nav>
  );
};
