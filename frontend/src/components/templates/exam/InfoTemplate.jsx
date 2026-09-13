import React, { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import styled from "styled-components";
import { fetchSessionDetails } from "../../../apis/predict";
import { formatDetectionConfidence, normalizeDetectionResult } from "./detectFlow";

const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;

  @media (min-width: 768px) {
    padding: 1.5rem;
  }
`;

const LayoutContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: 100%;
  max-width: 56.25rem; 
`;

const SectionTitle = styled.h2`
  font-size: 1.5rem;
  color: #28775a;
  margin: 0.25rem 0 0.5rem;
`;

const ImageContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  max-width: 100%;
  height: 8rem;
  overflow: hidden;
  border-radius: 0.45rem;
  margin-bottom: 0.5rem;

  @media (min-width: 768px) {
    height: 16rem;
  }
`;

const ImageLabel = styled.div`
  font-weight: bold;
  color: #4aaa87;
  margin-bottom: 0.5rem;
  text-align: center;
`;

const Image = styled.img`
  width: 100%;
  height: 100%;
  /* 두 이미지 모두 패널 너비를 채우도록 확대하고, 사용자 이미지만 상단 기준을 유지합니다. */
  object-fit: cover;
  object-position: ${props => (props.$crop ? "center top" : "center")};
`;

const InfoContainer = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  @media (max-width: 48rem) { 
    grid-template-columns: 1fr;
  }
`;

const SingleRowContainer = styled.div`
  display: flex;
  gap: 0.75rem;
  width: 100%;
  justify-content: center;
`;

const ImagePanel = styled.div`
  flex: 0 0 calc((100% - 0.75rem) / 2);
  width: calc((100% - 0.75rem) / 2);
  min-width: 0;
  text-align: center;
`;

const SummaryGrid = styled.div`
  width: 100%;
  display: grid;
`;

const SummaryCard = styled.div`
  min-width: 0;
  padding: 0.8rem 1rem;
  box-sizing: border-box;
  background: #fff;
  color: #263a32;
  border: 1px solid #c8ded5;
  border-left: 5px solid #4aaa87;
  border-radius: 0.625rem;
  box-shadow: 0 0.25rem 0.75rem rgba(35, 74, 58, 0.12);
`;

const SummaryLabel = styled.p`
  margin: 0 0 0.2rem;
  color: #4aaa87;
  font-size: 0.86rem;
  font-weight: 700;
  opacity: 0.88;
`;

const SummaryValue = styled.p`
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 1.5rem;
  font-weight: 800;
  color: #28775a;

  @media (max-width: 600px) {
    font-size: 1.2rem;
  }
`;

const SummaryMeta = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 0.55rem;
`;

const SummaryMetaItem = styled.span`
  display: inline-flex;
  gap: 0.3rem;
  align-items: baseline;
  padding: 0.3rem 0.6rem;
  background: #f1f7f4;
  color: #466158;
  font-size: 0.82rem;
  border: 1px solid #9fc4b4;
  border-radius: 999px;
`;

const SummaryMetaLabel = styled.span`
  color: #66736e;
`;

const SummaryMetaValue = styled.strong`
  font-weight: 700;
`;

const Divider = styled.hr`
  width: 100%;
  height: 1px;
  background-color: #ccc;
  margin: 0.35rem 0;
`;

const InfoBox = styled.div`
  background-color: #fbfdfc;
  padding: 0.8rem 1rem;
  border-radius: 0.625rem;
  box-shadow: 0 0.25rem 0.75rem rgba(35, 74, 58, 0.12);
  flex: 1;
  border: 1px solid #c8ded5;
`;

const InfoLabel = styled.p`
  font-weight: bold;
  color: #4aaa87;
  margin: 0 0 0.4rem;
`;

const InfoText = styled.p`
  margin: 0;
  line-height: 1.5;
  color: #263a32;
`;

const Table = styled.table`
  width: 100%;
  min-width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  margin-top: 0.65rem;
  font-size: 0.82rem;
`;

const TableWrap = styled.div`
  width: 100%;
  overflow-x: auto;
`;

const TableHeader = styled.th`
  border: 1px solid #ccc;
  padding: 0.45rem;
  background-color: #f0f0f0;
  color: #333;
  white-space: normal;
  overflow-wrap: anywhere;

  &:nth-child(1) {
    width: 24%;
  }

  &:nth-child(2) {
    width: 56%;
  }

  &:nth-child(3) {
    width: 20%;
  }
`;

const TableCell = styled.td`
  border: 1px solid #ccc;
  padding: 0.45rem;
  color: #333;
  vertical-align: top;
  overflow-wrap: anywhere;
  word-break: break-word;
`;

const BackButton = styled.button`
  background-color: #4aaa87;
  color: white;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 0.625rem;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.1);
  margin-top: 1.25rem;

  &:hover {
    background-color: #3b8b6d;
  }
`;

const parsePesticideDetails = (value) => value.split(/\r?\n/)
  .map((entry) => entry.trim())
  .filter(Boolean)
  .map((entry) => {
    const match = entry.match(/^(.+?)\((.+?),\s*([^,]+),\s*수확\s*(.+?)·(\d+회)\)$/);
    if (!match) {
      const basicMatch = entry.match(/^(.+?)\((.+?),\s*([^,]+)\)$/);
      if (!basicMatch) return { name: entry, ingredient: "-", dosage: "-", preHarvest: "-", maxUses: "-" };
      return { name: basicMatch[1].trim(), ingredient: basicMatch[2].trim(), dosage: basicMatch[3].trim(), preHarvest: "-", maxUses: "-" };
    }
    return {
      name: match[1].trim(),
      ingredient: match[2].trim(),
      dosage: match[3].trim(),
      preHarvest: `수확 ${match[4].trim()}`,
      maxUses: match[5].trim(),
    };
  });

const PesticideNote = styled.p`
  margin: 0.65rem 0 0;
  color: #66736e;
  font-size: 0.78rem;
  line-height: 1.5;
`;

const SourceFooter = styled.footer`
  width: 100%;
  max-width: 56.25rem;
  margin-top: 0.75rem;
  color: #66736e;
  font-size: 0.78rem;
  line-height: 1.5;
  text-align: left;

  p {
    margin: 0.15rem 0;
  }

  a {
    color: #28775a;
    font-weight: 600;
  }
`;

const InfoTemplate = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const [diagnosisResult, setDiagnosisResult] = useState(
    () => normalizeDetectionResult(location.state?.diagnosisResult)
  );
  const [isLoading, setIsLoading] = useState(Boolean(sessionId));
  const [loadError, setLoadError] = useState("");
  const [hasUserImageFailed, setHasUserImageFailed] = useState(false);
  const [hasDbImageFailed, setHasDbImageFailed] = useState(false);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  useEffect(() => {
    if (!sessionId) return undefined;

    let isActive = true;
    const loadResult = async () => {
      setIsLoading(true);
      setLoadError("");
      try {
        const response = await fetchSessionDetails(sessionId);
        const diagnosisResult = normalizeDetectionResult(response?.data);
        if (!diagnosisResult) throw new Error("MALFORMED_DETECTION_RESULT");
        if (isActive) setDiagnosisResult(diagnosisResult);
      } catch (error) {
        if (!isActive) return;
        setDiagnosisResult(null);
        setLoadError(error?.response?.status === 404
          ? "진단 결과를 찾을 수 없습니다."
          : "진단 결과를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.");
      } finally {
        if (isActive) setIsLoading(false);
      }
    };

    loadResult();
    return () => { isActive = false; };
  }, [sessionId]);

  if (isLoading && !diagnosisResult) {
    return <PageContainer><p>진단 결과를 불러오는 중입니다.</p></PageContainer>;
  }

  if (!diagnosisResult) {
    return (
      <PageContainer>
        <p>{loadError || "표시할 수 있는 진단 결과가 없습니다."}</p>
        <BackButton onClick={() => navigate('/diagnosis-list')}>목록으로 돌아가기</BackButton>
      </PageContainer>
    );
  }

  const {
    pest_name,
    occurrence_environment,
    symptom_description,
    prevention_methods,
    pesticide_name,
    information_source,
    information_source_url,
    confidence,
    user_image_url,
    db_image_url,
    detection_date
  } = diagnosisResult;

  const pesticides = parsePesticideDetails(pesticide_name);

  return (
    <PageContainer>
      <LayoutContainer>
        <SingleRowContainer>
          <ImagePanel>
            <ImageLabel>사용자 이미지</ImageLabel>
            <ImageContainer>
              {user_image_url && !hasUserImageFailed
                ? <Image $crop src={user_image_url} alt="사용자 진단 이미지" onError={() => setHasUserImageFailed(true)} />
                : <p>이미지를 표시할 수 없습니다.</p>}
            </ImageContainer>
          </ImagePanel>
          <ImagePanel>
            <ImageLabel>질병 이미지</ImageLabel>
            <ImageContainer $reference>
              {db_image_url && !hasDbImageFailed
                ? <Image src={db_image_url} alt="병해충 참고 이미지" onError={() => setHasDbImageFailed(true)} />
                : <p>이미지를 표시할 수 없습니다.</p>}
            </ImageContainer>
          </ImagePanel>
        </SingleRowContainer>
        <SummaryGrid aria-label="진단 요약">
          <SummaryCard $primary>
            <SummaryMeta>
              <SummaryMetaItem><SummaryMetaLabel>진단일</SummaryMetaLabel><SummaryMetaValue>{detection_date}</SummaryMetaValue></SummaryMetaItem>
              <SummaryMetaItem><SummaryMetaLabel>신뢰도</SummaryMetaLabel><SummaryMetaValue>{formatDetectionConfidence(confidence)}%</SummaryMetaValue></SummaryMetaItem>
            </SummaryMeta>
            <SummaryLabel $primary>질병명</SummaryLabel>
            <SummaryValue>{pest_name}</SummaryValue>
          </SummaryCard>
        </SummaryGrid>
            <Divider />
            <SectionTitle>{pest_name} 정보</SectionTitle>
            <InfoContainer>
              <InfoBox>
                <InfoLabel>발생 환경</InfoLabel>
                <InfoText>{occurrence_environment}</InfoText>
              </InfoBox>
              <InfoBox>
                <InfoLabel>증상 설명</InfoLabel>
                <InfoText>{symptom_description}</InfoText>
              </InfoBox>
              <InfoBox>
                <InfoLabel>예방 방법</InfoLabel>
                <InfoText>{prevention_methods}</InfoText>
              </InfoBox>
              <InfoBox>
              <InfoLabel>농약 방제 정보</InfoLabel>
                <TableWrap>
                <Table>
                  <thead>
                    <tr>
                      <TableHeader>농약명</TableHeader>
                      <TableHeader>유효성분</TableHeader>
                      <TableHeader>희석배수</TableHeader>
                    </tr>
                  </thead>
                  <tbody>
                    {(pesticides.length ? pesticides : [{ name: "정보 없음", ingredient: "-", dosage: "-", preHarvest: "-", maxUses: "-" }]).map((pesticide, index) => (
                      <tr key={index}>
                        <TableCell>{pesticide.name}</TableCell>
                        <TableCell>{pesticide.ingredient}</TableCell>
                        <TableCell>{pesticide.dosage}</TableCell>
                      </tr>
                    ))}
                  </tbody>
                </Table>
                </TableWrap>
                <PesticideNote>농촌진흥청 등록 정보 기준이며, 사용 전 제품 라벨과 최신 안전사용기준을 반드시 확인하세요.</PesticideNote>
              </InfoBox>
            </InfoContainer>
      </LayoutContainer>
      <BackButton onClick={() => navigate('/diagnosis-list')}>목록으로 돌아가기</BackButton>
      <SourceFooter>
        <p>
          본 서비스의 병해충 진단 결과 이미지는 <a href="https://rda.go.kr" target="_blank" rel="noopener noreferrer" style={{ textDecoration: "underline", color: "inherit" }}>농촌진흥청</a>에서 작성하여 공공누리 제2유형으로 개방한 공공저작물을 이용하였습니다.
        </p>
        <p>
          상세 질병 정보 출처: {information_source_url ? (
            <a href={information_source_url} target="_blank" rel="noopener noreferrer">
              {information_source || "농촌진흥청 국가농작물병해충관리시스템"}
            </a>
          ) : (information_source || "농촌진흥청 국가농작물병해충관리시스템")}
        </p>
      </SourceFooter>
    </PageContainer>
  );
};

export default InfoTemplate;
