import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import styled from "styled-components";
import { FaArrowLeft, FaUser, FaSignInAlt, FaSignOutAlt } from "react-icons/fa";
import CustomModal from "../atoms/CustomModal";
import TopBarLoader from "../atoms/TopBarLoader";
import { useLoading } from "../../LoadingContext";
import { useAuth } from "../../AuthContext";
import { color } from "../../styles/theme";

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

const LeftSection = styled.div`
  display: flex;
  align-items: center;
`;

const LogoContainer = styled.div`
  display: flex;
  align-items: center;
  margin-left: 1px; 
`;

const LogoImage = styled.img`
  width: 40px;
`;

const Title = styled.div`
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  font-size: 1.125rem;
  font-weight: 800;
  color: ${color("text")};
`;

const BackButton = styled.button`
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  width: 36px;
  height: 36px;
  color: ${color("text")};
`;

const RightSection = styled.div`
  display: flex;
  align-items: center;
  position: relative;
`;

const IconButton = styled.button`
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  font-size: 20px;
  color: ${color("primary")};
  cursor: pointer;
  margin-left: 4px;
  width: 36px;
  height: 36px;
`;

const PageTopBar = () => {
  const { setIsLoading, isLoading } = useLoading();
  const { status, user, logout } = useAuth();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState("");
  const navigate = useNavigate();
  const location = useLocation();

  const pageTitles = {
    "/board": "커뮤니티",
    "/buy-board": "커뮤니티",
    "/sell-board": "커뮤니티",
    "/exchange-board": "커뮤니티",
    "/post/create": "게시글 작성",
    "/post/:id": "커뮤니티",
    "/chat-list": "대화 목록",
    "/my-page": "마이페이지",
    "/post/edit/:id": "게시글 수정",
    "/my-commented-posts": "내가 댓글 단 글",
    "/my-posts": "내가 작성한 글",
    "/soil": "토양 분석",
    "/diagnosis": "병해충 진단",
    "/info": "병해충 진단 결과",
    "/info/:sessionId": "병해충 진단 결과",
    "/crop-test": "작물조합 등록",
    "/diagnosis-list": "병해충 진단 목록",
    "/crop-selection": "작물 조합 목록",
    "/soil-list": "토양 데이터 목록",
    "/soil-details": "토양 데이터 상세",
    "/soil-details/:sessionId": "토양 데이터 상세",
    "/session-details/:sessionId": "수익 예측 결과",
    "/signup": "회원가입",
    "/password-reset": "비밀번호 찾기",
  };

  const noBackButtonPages = [
    "/post/:id",
    "/post/create"
  ];

  const getPageTitle = () => {
    const pathname = location.pathname;
    const pathKeys = Object.keys(pageTitles);

    for (const pathKey of pathKeys) {
      const regex = new RegExp(`^${pathKey.replace(/:\w+/g, "[^/]+")}$`);
      if (regex.test(pathname)) {
        return pageTitles[pathKey];
      }
    }

    const searchParams = new URLSearchParams(location.search);
    const postType = searchParams.get('post_type');
    if (pathname.startsWith('/post/create') && postType) {
      return "게시글 작성";
    }

    if (/^\/chat\/[\w-]+$/.test(pathname)) {
      return "농업GPT";
    }

    return "";
  };

  const pageTitle = getPageTitle();
  const showBackButton = !noBackButtonPages.some((page) => {
    const regex = new RegExp(`^${page.replace(/:\w+/g, "\\w+")}$`);
    return regex.test(location.pathname) && !location.pathname.startsWith("/post/create");
  });

  const handleLogout = async () => {
    setIsLoading(true);
     try {
      await logout();
      setModalContent("로그아웃이 완료되었습니다.");
      setIsModalOpen(true);
    }  catch {
      setModalContent("로그아웃 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
      setIsModalOpen(true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    navigate("/");
  };

  const handleBackClick = () => {
    navigate(-1);
  };

  return (
    <>
      <TopBars>
        <LeftSection>
          {showBackButton && (
            <BackButton onClick={handleBackClick}>
              <FaArrowLeft />
            </BackButton>
          )}
          <LogoContainer onClick={() => navigate("/main")}>
            <LogoImage src={`${process.env.PUBLIC_URL}/android-chrome-192x192.png`} alt="Logo" />
          </LogoContainer>
        </LeftSection>
        <Title>{pageTitle}</Title>
        <RightSection>
          {status === "checking" ? (
            <TopBarLoader color="#4aaa87" />
          ) : status === "authenticated" ? (
            isLoading ? (
              <TopBarLoader color="#4aaa87" />
            ) : (
              <>
                <IconButton onClick={() => navigate("/my-page")}>
                  <FaUser title={`${user?.username || ""}님`} />
                </IconButton>
                <IconButton onClick={handleLogout}>
                  <FaSignOutAlt title="로그아웃" />
                </IconButton>
              </>
            )
          ) : (
            isLoading ? (
              <TopBarLoader color="#4aaa87" />
            ) : (
              <IconButton onClick={() => navigate("/login")}>
                <FaSignInAlt title="로그인" />
              </IconButton>
            )
          )}
        </RightSection>
        <CustomModal isOpen={isModalOpen} onRequestClose={handleCloseModal} title="알림" content={modalContent} />
      </TopBars>
    </>
  );
};

export default PageTopBar;
