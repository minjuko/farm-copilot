import React, { useState } from "react";
import styled from "styled-components";
import { Link } from "react-router-dom";
import { FaChevronLeft, FaChevronRight } from "react-icons/fa";
import { color, radius, shadow, space } from "../../styles/theme";

const Container = styled.div`
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 760px;
  gap: ${space("xl")};
  margin: 0 auto;
  padding: ${space("lg")} ${space("md")} 96px;
  box-sizing: border-box;
`;

const GuideBanner = styled.section`
  position: relative;
  height: 166px;
  padding: ${space("lg")} 52px;
  overflow: hidden;
  color: #244d3e;
  background: linear-gradient(135deg, #e0f2e9 0%, #f4faf7 58%, #e8f3ee 100%);
  border: 1px solid ${color("borderStrong")};
  border-radius: ${radius("lg")};
  box-shadow: ${shadow("md")};
  box-sizing: border-box;

  &::after {
    content: "";
    position: absolute;
    right: -38px;
    bottom: -62px;
    width: 170px;
    height: 170px;
    border-radius: 50%;
    background: rgba(74, 170, 135, 0.13);
  }
`;

const GuideEyebrow = styled.div`
  margin-bottom: ${space("xs")};
  color: ${color("primaryHover")};
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.08em;
`;

const GuideTitle = styled.h1`
  position: relative;
  z-index: 1;
  margin: 0;
  font-size: clamp(1.15rem, 4vw, 1.45rem);
  line-height: 1.35;
`;

const GuideText = styled.p`
  position: relative;
  z-index: 1;
  margin: ${space("sm")} 0 0;
  color: ${color("textMuted")};
  font-size: 0.98rem;
`;

const GuideContent = styled(Link)`
  position: relative;
  z-index: 1;
  display: block;
  color: inherit;
  text-decoration: none;
`;

const SlideButton = styled.button`
  position: absolute;
  top: 50%;
  ${({ $right }) => ($right ? "right: 12px;" : "left: 12px;")}
  z-index: 2;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  padding: 0;
  color: ${color("primaryHover")};
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid ${color("border")};
  border-radius: 50%;
  transform: translateY(-50%);
  cursor: pointer;
`;

const Indicators = styled.div`
  position: absolute;
  left: 50%;
  bottom: 10px;
  z-index: 2;
  display: flex;
  gap: 6px;
  transform: translateX(-50%);
`;

const Indicator = styled.button`
  width: ${({ $active }) => ($active ? "20px" : "7px")};
  height: 7px;
  padding: 0;
  background: ${({ $active, theme }) => $active
    ? theme?.colors?.primary || "#4aaa87"
    : theme?.colors?.borderStrong || "#afc7bc"};
  border: 0;
  border-radius: 999px;
  cursor: pointer;
`;

const GridContainer = styled.div`
  display: grid;
  column-gap: ${space("md")};
  row-gap: ${space("lg")};
  grid-template-columns: repeat(2, minmax(0, 1fr));
`;

const MenuCard = styled(Link)`
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 128px;
  padding: ${space("lg")} ${space("md")};
  text-decoration: none;
  text-align: center;
  color: ${color("text")};
  background-color: ${color("surface")};
  border: 1px solid ${color("border")};
  border-radius: ${radius("lg")};
  box-shadow: ${shadow("sm")};
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: ${shadow("md")};
  }

  h2 {
    margin: 0;
    font-size: clamp(1.15rem, 4vw, 1.35rem);
    color: ${color("primary")};
  }

  p {
    margin: 0.5rem 0 0;
    font-size: 0.96rem;
    color: ${color("textMuted")};
  }
`;

const ListContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${space("md")};
`;

const ListItem = styled(Link)`
  display: block;
  padding: ${space("md")} ${space("lg")};
  text-decoration: none;
  color: ${color("text")};
  background-color: ${color("surface")};
  border: 1px solid ${color("border")};
  border-radius: ${radius("md")};
  box-shadow: ${shadow("sm")};

  h2 {
    margin: 0;
    font-size: 1rem;
    color: ${color("primary")};
  }
`;

const services = [
  { key: "detection", to: "/diagnosis-list", title: "병해충 진단", description: "작물 이미지로 병해충 진단" },
  { key: "prediction", to: "/crop-selection", title: "수익 예측", description: "작물 수익 미리 계산해보기" },
  { key: "chatbot", to: "/chat-list", title: "농업 GPT", description: "농업 전문 챗봇" },
  { key: "soil", to: "/soil-list", title: "토양 분석", description: "토양 분석과 비료 추천" },
];

const guides = [
  { to: "/diagnosis-list", eyebrow: "병해충 진단", title: "사진 한 장으로 병해충을 확인해보세요", text: "작물 사진을 올리면 진단 결과와 질병 정보를 한눈에 볼 수 있어요." },
  { to: "/crop-selection", eyebrow: "수익 예측", title: "작물 조합별 예상 소득을 비교해보세요", text: "재배 면적과 지역을 기준으로 작물 조합의 예상 수익을 확인할 수 있어요." },
  { to: "/chat-list", eyebrow: "농업 GPT", title: "궁금한 농업 정보를 바로 물어보세요", text: "농업과 관련된 질문에 답해드려요." },
  { to: "/soil-list", eyebrow: "토양 분석", title: "내 토양에 맞는 비료 정보를 확인해보세요", text: "주소와 작물을 선택해 최근 토양 검사 결과와 추천 정보를 살펴보세요." },
];

const MainTemplate = () => {
  const [guideIndex, setGuideIndex] = useState(0);
  const moveGuide = (direction) => {
    setGuideIndex((current) => (current + direction + guides.length) % guides.length);
  };

  return (
    <Container>
      <GuideBanner aria-roledescription="carousel" aria-label="서비스 이용 안내">
        <SlideButton onClick={() => moveGuide(-1)} aria-label="이전 안내">
          <FaChevronLeft />
        </SlideButton>
        <GuideContent to={guides[guideIndex].to} aria-label={`${guides[guideIndex].eyebrow} 페이지로 이동`}>
          <GuideEyebrow>{guides[guideIndex].eyebrow}</GuideEyebrow>
          <GuideTitle>{guides[guideIndex].title}</GuideTitle>
          <GuideText>{guides[guideIndex].text}</GuideText>
        </GuideContent>
        <SlideButton $right onClick={() => moveGuide(1)} aria-label="다음 안내">
          <FaChevronRight />
        </SlideButton>
        <Indicators aria-label="안내 선택">
          {guides.map((guide, index) => (
            <Indicator
              key={guide.title}
              $active={guideIndex === index}
              onClick={() => setGuideIndex(index)}
              aria-label={`${index + 1}번째 안내`}
              aria-current={guideIndex === index ? "true" : undefined}
            />
          ))}
        </Indicators>
      </GuideBanner>
      <GridContainer>
        {services.map((service) => (
            <MenuCard key={service.key} to={service.to}>
              <h2>{service.title}</h2>
              <p>{service.description}</p>
            </MenuCard>
        ))}
      </GridContainer>
      <ListContainer>
        <ListItem to="/my-page"><h2>마이페이지</h2></ListItem>
        <ListItem to="/board"><h2>커뮤니티</h2></ListItem>
      </ListContainer>
    </Container>
  );
};

export default MainTemplate;
