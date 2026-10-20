import React from "react";
import styled from "styled-components";

const Note = styled.p`
  margin: 0.5rem 0;
  color: #52655d;
  font-size: 0.85rem;
  line-height: 1.5;
`;

const DetectionCaution = () => (
  <Note>
    AI 예측 결과는 참고용입니다. 모델 점수는 정답 확률이나 전체 정확도가 아니며,
    실제 병해 여부는 재배 환경과 증상을 함께 확인해 주세요.
  </Note>
);

export default DetectionCaution;
