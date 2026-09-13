import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import styled from "styled-components";
import CustomModal from "../atoms/CustomModal";
import TopBarLoader from "../atoms/TopBarLoader";
import { useLoading } from "../../LoadingContext";
import { useAuth } from "../../AuthContext";
import { color, radius, shadow } from "../../styles/theme";

const TopBars = styled.nav`
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 60px;
  box-sizing: border-box;
  background-color: ${color("surface")};
  padding: 10px 16px;
  border-bottom: 2px solid ${color("borderStrong")};
  box-shadow: 0 4px 14px rgba(35, 74, 58, 0.14);
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
  color: ${color("primary")};
  margin-left: 8px;
`;

const RightSection = styled.div`
  display: flex;
  align-items: center;
  position: relative;
`;

const TopBarButton = styled.button`
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 8px 18px;
  background-color: ${color("primary")};
  color: #ffffff;
  font-family: 'Freesentation', sans-serif;
  font-weight: 600;
  border: none;
  border-radius: ${radius("sm")};
  font-size: 0.9rem;
  box-shadow: ${shadow("sm")};
  cursor: pointer;
`;

const UsernameText = styled.span`
  font-size: 0.9rem;
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
      setModalContent("로그아웃 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
      setIsModalOpen(true);
    }
    setIsLoading(false);
  };

  const handleCloseModal = () => {
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
      <CustomModal isOpen={isModalOpen} onRequestClose={handleCloseModal} title="알림" content={modalContent} />
    </TopBars>
  );
};

export default MainTopBar;
