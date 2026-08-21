import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import styled from "styled-components";
import CustomModal from "../atoms/CustomModal";
import TopBarLoader from "../atoms/TopBarLoader";
import { useLoading } from "../../LoadingContext";
import { useAuth } from "../../AuthContext";

const TopBars = styled.nav`
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f3f4f6;
  padding: 12px;
  border-bottom: 1px solid #c8c5c5;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  position: sticky;
  z-index: 1000;
`;

const LogoContainer = styled.div`
  display: flex;
  align-items: center;
  cursor: ${({ $disableClick }) => ($disableClick ? "default" : "pointer")};
`;

const LogoImage = styled.img`
  width: 40px;
`;

const LogoText = styled.div`
  font-size: 20px;
  font-weight: 800;
  color: #4aaa87;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
  margin-left: 8px;
`;

const RightSection = styled.div`
  display: flex;
  align-items: center;
  position: relative; /* 추가 */
`;

const TopBarButton = styled.button`
  position: relative; /* 추가 */
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 20px;
  background-color: #4aaa87;
  color: #ffffff;
  font-family: 'Freesentation', sans-serif;
  font-weight: 600;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  cursor: pointer;
`;

const UsernameText = styled.span`
  font-size: 16px;
  margin-right: 10px;
  display: flex;
  align-items: center;
`;

const GrayText = styled.span`
  margin-left: 1px;
  color: dimgray;
`;

const MainTopBar = () => {
  const { setIsLoading, isLoading } = useLoading();
  const { status, user, logout } = useAuth();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const isStartPage = location.pathname === "/";

  const handleLogout = async () => {
    setIsLoading(true);
    try {
      await logout();
      setModalContent("로그아웃이 완료되었습니다.");
      setIsModalOpen(true);
    } catch {
      console.error("Failed to logout");
    }
    setIsLoading(false);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    navigate("/");
  };

  const handleLogoClick = () => {
    if (!isStartPage) {
      navigate("/main");
    }
  };

  return (
    <TopBars>
      <LogoContainer onClick={handleLogoClick} $disableClick={isStartPage}>
        <LogoImage src={`${process.env.PUBLIC_URL}/android-chrome-192x192.png`} alt="Logo" />
        <LogoText>꾼꾼농사꾼</LogoText>
      </LogoContainer>
      <RightSection>
        {status === "checking" ? (
          <TopBarLoader color="white" />
        ) : status === "authenticated" ? (
          <>
            <UsernameText>
              {user?.username}
              <GrayText>님</GrayText>
            </UsernameText>
            <TopBarButton onClick={handleLogout}>
              {isLoading ? <TopBarLoader color="white"/> : '로그아웃'}
            </TopBarButton>
          </>
        ) : (
          <TopBarButton onClick={() => navigate("/login")}>
            {isLoading ? <TopBarLoader color="white"/> : '로그인'}
          </TopBarButton>
        )}
      </RightSection>
      <CustomModal isOpen={isModalOpen} onRequestClose={closeModal} title="알림" content={modalContent} />
    </TopBars>
  );
};

export default MainTopBar;
