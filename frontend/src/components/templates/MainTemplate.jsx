import React, { useEffect, useState } from "react";
import styled from "styled-components";
import { Link } from "react-router-dom";
import { fetchCapabilities, normalizeCapability } from "../../apis/capabilities";

const Container = styled.div`
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 2rem;
  padding: 2rem;
`;

const GridContainer = styled.div`
  display: grid;
  gap: 2rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
`;

const MenuCard = styled(Link)`
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 120px;
  padding: 1rem 0.5rem;
  text-decoration: none;
  text-align: center;
  color: #333;
  background-color: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover {
    transform: translateY(-5px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  h2 {
    margin: 0;
    font-size: clamp(1.2rem, 5vw, 1.6rem);
    color: #4aaa87;
  }

  p {
    margin: 0.5rem 0 0;
    font-size: clamp(0.8rem, 3vw, 1rem);
    color: #666;
  }
`;

const StatusBadge = styled.span`
  position: absolute;
  top: 0.55rem;
  right: 0.55rem;
  padding: 0.2rem 0.45rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 700;
  color: ${({ $available }) => ($available ? "#176b48" : "#755800")};
  background: ${({ $available }) => ($available ? "#dff5ea" : "#fff1bd")};
`;

const ListContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const ListItem = styled(Link)`
  display: block;
  padding: 1rem;
  text-decoration: none;
  color: #333;
  background-color: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);

  h2 {
    margin: 0;
    font-size: clamp(1rem, 3vw, 1.2rem);
    color: #4aaa87;
  }
`;

const services = [
  { key: "detection", to: "/diagnosislist", title: "병해충 진단", description: "작물 이미지로 병해충 진단" },
  { key: "prediction", to: "/cropselection", title: "수익 예측", description: "작물 수익 미리 계산해보기" },
  { key: "chatbot", to: "/chatlist", title: "농업 GPT", description: "출처 기반 농업 전문 챗봇" },
  { key: "soil", to: "/soillist", title: "토양 분석", description: "토양 분석과 비료 추천" },
];

const statusLabel = (capability) => {
  if (capability.status === "checking") return "CHECKING";
  if (capability.available) return "AVAILABLE";
  return capability.status === "archived" ? "ARCHIVED" : "LIMITED";
};

const MainTemplate = () => {
  const [capabilities, setCapabilities] = useState(null);

  useEffect(() => {
    let active = true;
    fetchCapabilities()
      .then((response) => {
        if (active) setCapabilities(response?.data || {});
      })
      .catch(() => {
        if (active) setCapabilities({});
      });
    return () => { active = false; };
  }, []);

  return (
    <Container>
      <GridContainer>
        {services.map((service) => {
          const capability = capabilities === null
            ? { status: "checking", available: false }
            : normalizeCapability(capabilities, service.key);
          return (
            <MenuCard key={service.key} to={service.to}>
              <StatusBadge $available={capability.available}>
                {statusLabel(capability)}
              </StatusBadge>
              <h2>{service.title}</h2>
              <p>{service.description}</p>
            </MenuCard>
          );
        })}
      </GridContainer>
      <ListContainer>
        <ListItem to="/mypage"><h2>마이페이지</h2></ListItem>
        <ListItem to="/board"><h2>게시판</h2></ListItem>
      </ListContainer>
    </Container>
  );
};

export default MainTemplate;
