import React from 'react';
import { FadeLoader } from 'react-spinners';
import styled, { useTheme } from 'styled-components';
import { useLoading } from "../../LoadingContext";
import { appTheme, color, space, zIndex } from "../../styles/theme";

const LoaderContainer = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: ${color("overlay")};
  z-index: ${zIndex("loader")};
`;

const Logo = styled.img`
  width: 100px; 
  height: 100px;
  margin-bottom: ${space("lg")};
`;

const LoaderWrapper = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
`;

const LoaderOffsetWrapper = styled.div`
  position: relative;
  left: 5px; /* 로더를 오른쪽으로 5px 이동 */
`;

const LoaderText = styled.p`
  margin-top: ${space("lg")};
  font-size: 1rem;
  font-weight: 600;
  color: ${color("text")};
`;

const GlobalLoader = ({ text }) => {
  const { isLoading } = useLoading();
  const theme = useTheme();

  if (!isLoading) return null;

  return (
    <LoaderContainer>
      <LoaderWrapper>
        <Logo src={`${process.env.PUBLIC_URL}/android-chrome-192x192.png`} alt="Loading Logo" />
        <LoaderOffsetWrapper>
          <FadeLoader color={theme?.colors?.primary || appTheme.colors.primary} loading={isLoading} size={60} />
        </LoaderOffsetWrapper>
        {text && <LoaderText>{text}</LoaderText>}
      </LoaderWrapper>
    </LoaderContainer>
  );
};

export default GlobalLoader;
