import React, { useState } from 'react';
import styled from 'styled-components';
import { useNavigate, useParams } from 'react-router-dom';
import { Bar, Line } from 'react-chartjs-2';
import Chart from 'chart.js/auto';
import { CategoryScale, TimeScale } from 'chart.js';
import ChartDataLabels from 'chartjs-plugin-datalabels';
import 'chartjs-adapter-date-fns';
import { ko } from 'date-fns/locale';
import GlobalLoader from "../../atoms/GlobalLoader";
import { finiteNumberOrZero, formatKoreanCurrency } from './predictionFlow';
import useSessionDetails from './useSessionDetails';

Chart.register(CategoryScale, TimeScale, ChartDataLabels);

const CHART_FONT = 'Freesentation, sans-serif';

const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.5rem;
  box-sizing: border-box;
  overflow: auto;
`;

const LayoutContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 18px;
  width: 100%;
  max-width: 900px;
`;

const SectionContainer = styled.div`
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start; 
  justify-content: center;
  margin: 0.5rem 0;
  flex: 1;
`;

const CropDetailContainer = styled.section`
  width: 100%;
  padding: 1.5rem;
  background: #fff;
  border: 2px solid #c8ded5;
  border-radius: 0 12px 12px 12px;
  box-shadow: 0 8px 24px rgba(35, 74, 58, 0.18);

  @media (max-width: 600px) {
    padding: 1rem;
  }
`;

const CropSelectorSection = styled.div`
  width: 100%;
  margin-top: 1.25rem;

  h3 {
    margin: 0 0 0.65rem;
  }
`;

const CropReportHeader = styled.header`
  display: flex;
  align-items: baseline;
  gap: 0.65rem;
  margin: 0 0 1rem;
  text-align: left;

  @media (max-width: 600px) {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.15rem;
  }
`;

const CropReportTitle = styled.h2`
  margin: 0;
  color: #4aaa87;
  font-size: 1.15rem;
  font-weight: 750;
`;

const CropReportGuide = styled.p`
  margin: 0;
  color: #66736e;
  font-size: 0.9rem;
`;

const KpiGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.75rem;

`;

const KpiCard = styled.div`
  grid-column: ${props => (props.$primary ? '1 / -1' : 'auto')};
  min-width: 0;
  padding: 0.9rem;
  background: ${props => (props.$primary ? '#4aaa87' : '#f8faf9')};
  color: ${props => (props.$primary ? '#fff' : '#263a32')};
  border: 1px solid ${props => (props.$primary ? '#4aaa87' : '#dfe8e4')};
  border-radius: 10px;

  @media (max-width: 600px) {
    padding: 0.75rem;
  }
`;

const KpiLabel = styled.p`
  margin: 0 0 0.35rem;
  font-size: 0.9rem;
  font-weight: 600;
  opacity: 0.85;

  @media (max-width: 600px) {
    font-size: 0.78rem;
    white-space: nowrap;
  }
`;

const KpiValue = styled.p`
  margin: 0;
  font-size: clamp(1rem, 2.8vw, 1.35rem);
  font-weight: 800;
  white-space: nowrap;
`;

const ForecastCard = styled.div`
  margin-bottom: 0.5rem;
  padding: 0.9rem;
  background: #4aaa87;
  color: #fff;
  border: 1px solid #4aaa87;
  border-radius: 10px;
`;

const ForecastLabel = styled.p`
  margin: 0 0 0.25rem;
  color: #fff;
  font-weight: 600;
  opacity: 0.85;
`;

const ForecastValue = styled.p`
  margin: 0;
  color: #fff;
  font-size: clamp(1rem, 2.8vw, 1.35rem);
  font-weight: 800;
  white-space: nowrap;
`;

const InfoTableContainer = styled.div`
  width: 100%;
  margin-bottom: 0.5rem;
  overflow: auto;
`;

const SectionTitle = styled.h3`
  font-size: 1.5rem;
  color: #4aaa87;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;

  @media (max-width: 600px) {
    font-size: 1.2rem;
  }
`;

const InfoTable = styled.table`
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  border: 2px solid #c8ded5;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(35, 74, 58, 0.18);

  th, td {
    padding: 12px;
    border-right: 1px solid #b8c9c1;
    border-bottom: 1px solid #b8c9c1;
    text-align: left;
    font-size: 1.2rem; 
  }

  tr:last-child td {
    border-bottom: 0;
  }

  td:last-child {
    border-right: 0;
  }

  td:first-child {
    width: 40%;
    font-weight: 600;
    background-color: #f1f7f4;
  }

  td:last-child { width: 50%; }

  @media (max-width: 768px) {
    th, td {
      font-size: 1.0rem; 
      padding: 8px;
    }
  }
`;

const ExplanationText = styled.p`
  font-size: 0.8rem;
  color: #666;
`;

const ChartContainer = styled.div`
  background-color: #fbfdfc;
  padding: 1rem;
  margin: 0.4rem 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(35, 74, 58, 0.12);
  width: 100%;
  max-width: 800px;
  height: ${props => (props.$tall ? '360px' : '360px')};
  overflow: auto;
  border: 1px solid #e1ebe7;

  @media (min-width: 768px) {
    height: ${props => (props.$tall ? '400px' : '420px')};
  }
`;

const Tabs = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  justify-content: flex-start;
  margin: 0 0 -2px;
  position: relative;
  z-index: 1;
`;

const TabButton = styled.button`
  background-color: ${props => (props.$active ? '#4aaa87' : '#eef6f2')};
  color: ${props => (props.$active ? '#fff' : '#587168')};
  border: 2px solid ${props => (props.$active ? '#3b8b6d' : '#dce9e4')};
  border-bottom-color: ${props => (props.$active ? '#4aaa87' : '#c8ded5')};
  padding: 12px 24px;
  margin: 0;
  border-radius: 9px 9px 0 0;
  font-size: 1rem;
  font-weight: ${props => (props.$active ? '750' : '500')};
  box-shadow: ${props => (props.$active ? '0 4px 10px rgba(40, 119, 90, 0.24)' : 'none')};
  cursor: pointer;
  transition: background-color 0.3s, color 0.3s, transform 0.3s, box-shadow 0.3s;

  &:hover {
    background-color: ${props => (props.$active ? '#3b8b6d' : '#e2f2eb')};
    color: ${props => (props.$active ? '#fff' : '#28775a')};
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  }
`;

const ErrorText = styled.p`
  font-size: 1rem;
  font-weight: 300;
  color: #666;
`;

const Loader = styled.div`
  border: 4px solid #f3f3f3;
  border-radius: 50%;
  border-top: 4px solid #3498db;
  width: 40px;
  height: 40px;
  -webkit-animation: spin 2s linear infinite;
  animation: spin 2s linear infinite;

  @-webkit-keyframes spin {
    0% { -webkit-transform: rotate(0deg); }
    100% { -webkit-transform: rotate(360deg); }
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const ButtonContainer = styled.div`
  display: flex;
  justify-content: center;
  width: 100%;
`;

const Button = styled.button`
  background-color: #4aaa87;
  color: white;
  padding: 1rem 2.5rem;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1.2rem;
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.1);
  margin-bottom: 1rem;

  &:hover {
    background-color: #3b8b6d;
  }

  @media (max-width: 600px) {
    padding: 0.8rem 1.8rem;
    font-size: 1rem;
  }
`;

const costItems = [
  { key: "총중간재비", label: "재료·운영비" },
  { key: "고용노동비", label: "고용 노동비" },
  { key: "토지임차료", label: "토지 임차료" },
  { key: "위탁영농비", label: "위탁 영농비" },
  { key: "농기계·시설 임차료", label: "농기계·시설 임차료" }
];

const cropColors = [
  { background: 'rgba(74, 170, 135, 0.76)', border: '#28775a' },
  { background: 'rgba(72, 128, 190, 0.76)', border: '#315f91' },
  { background: 'rgba(231, 156, 62, 0.76)', border: '#a86418' },
  { background: 'rgba(147, 105, 190, 0.76)', border: '#704498' },
  { background: 'rgba(210, 94, 112, 0.76)', border: '#9f3f50' }
];

const getCropColor = (cropName) => {
  const colorIndex = Array.from(cropName || '').reduce(
    (sum, character) => sum + character.charCodeAt(0),
    0
  );
  return cropColors[colorIndex % cropColors.length];
};

const generateBarChartData = (adjustedData, cropName) => {
  const cropColor = getCropColor(cropName);
  const costs = costItems
    .map(item => ({ label: item.label, value: finiteNumberOrZero(adjustedData?.[item.key]) }))
    .filter(item => item.value > 0)
    .sort((a, b) => b.value - a.value);

  return {
    labels: costs.map(item => item.label),
    datasets: [
      {
        label: `${cropName} 예상 비용`,
        data: costs.map(item => item.value),
        backgroundColor: cropColor.background,
        borderColor: cropColor.border,
        borderWidth: 1,
        borderRadius: 5,
      }
    ]
  };
};

const generateLineChartData = (cropChartData, cropName, additionalPrice) => {
  const points = cropChartData
    .map((pricePoint) => ({ date: new Date(pricePoint.tm), price: finiteNumberOrZero(pricePoint.price) }))
    .filter(point => !Number.isNaN(point.date.getTime()))
    .sort((a, b) => a.date - b.date);
  const lastDate = points.length ? points[points.length - 1].date : new Date();
  const forecastDate = new Date(lastDate);
  forecastDate.setDate(forecastDate.getDate() + 1);
  const labels = [...points.map(point => point.date), forecastDate];
  const priceValues = [...points.map(point => point.price), null];

  return {
    labels,
    datasets: [
      {
        label: `${cropName} 일일 도매가격`,
        data: priceValues,
        fill: false,
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.12)',
        tension: 0.2,
        order: 1,
        pointRadius: 0,
        pointHitRadius: 8
      },
      {
        label: `내일 예상 도매가격: ${finiteNumberOrZero(additionalPrice).toLocaleString()}원/kg`,
        data: [...Array(points.length).fill(null), finiteNumberOrZero(additionalPrice)],
        fill: false,
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgb(255, 99, 132)',
        showLine: false,
        order: 10,
        pointRadius: 6,
        pointHoverRadius: 8
      }
    ]
  };
};

const lineChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: {
      type: 'time',
      time: {
        unit: 'month',
        displayFormats: { month: 'M월' },
        tooltipFormat: 'yyyy년 M월 d일'
      },
      adapters: {
        date: { locale: ko }
      },
      title: {
        display: true,
        text: '날짜',
        font: { family: CHART_FONT, size: 14, weight: '600' }
      },
      ticks: {
        font: { family: CHART_FONT, size: 12 }
      }
    },
    y: {
      title: {
        display: true,
        text: '도매가격 (원/kg)',
        font: { family: CHART_FONT, size: 14, weight: '600' }
      },
      ticks: {
        font: { family: CHART_FONT, size: 12 },
        callback: value => `${Number(value).toLocaleString()}원`
      }
    }
  },
  plugins: {
    datalabels: {
      display: false
    },
    legend: {
      labels: {
        color: 'black',
        font: { family: CHART_FONT, size: 13 }
      },
      display: true
    }
  }
};

const barChartOptions = {
  indexAxis: 'y',
  maintainAspectRatio: false,
  layout: {
    padding: { right: 72 }
  },
  scales: {
    x: {
      title: {
        display: true,
        text: '예상 비용 (원)',
        font: { family: CHART_FONT, size: 14, weight: '600' }
      },
      ticks: {
        color: '#333',
        font: { family: CHART_FONT, size: 12 },
        callback: value => `${Number(value).toLocaleString()}원`
      }
    },
    y: {
      ticks: {
        color: '#333',
        font: { family: CHART_FONT, size: 13, weight: '500' }
      }
    }
  },
  plugins: {
    tooltip: {
      callbacks: {
        label: function(context) {
          let label = context.dataset.label || '';
          if (label) {
            label += ': ';
          }
          label += `${Math.round(context.raw).toLocaleString()}원`;
          return label;
        }
      }
    },
    legend: {
      labels: {
        color: 'black',
        font: { family: CHART_FONT, size: 13 }
      }
    },
    datalabels: {
      display: true,
      align: 'right',
      anchor: 'end',
      offset: 4,
      color: '#33443d',
      font: { family: CHART_FONT, size: 11, weight: '600' },
      formatter: function(value) {
        return `${Math.round(value).toLocaleString()}원`;
      }
    }
  }
};

const SessionDetails = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [selectedCropIndex, setSelectedCropIndex] = useState(0);
  const [barChartData, setBarChartData] = useState(null);
  const [lineChartData, setLineChartData] = useState(null);
  const [isChartLoading, setIsChartLoading] = useState(false);
  const { sessionDetails, errorMessage, isFetching, isLoading } = useSessionDetails(sessionId);

  const updateCharts = (details, index) => {
    if (!details.results[index]) return;
    const cropNames = details.results.map((cropResult) => cropResult.crop_name);
    const additionalPrices = details.results.map((cropResult) => cropResult.price);
    const barData = generateBarChartData(details.results[index].adjusted_data, cropNames[index]);
    setBarChartData(barData);
    const lineData = generateLineChartData(details.results[index].crop_chart_data, cropNames[index], additionalPrices[index]);
    setLineChartData(lineData);
  };

  React.useEffect(() => {
    if (sessionDetails) updateCharts(sessionDetails, 0);
  }, [sessionDetails]);

  const handleTabClick = (index) => {
    setSelectedCropIndex(index);
    setIsChartLoading(true);

    if (sessionDetails) {
      updateCharts(sessionDetails, index);
    }

    setIsChartLoading(false);
  };

  const handleBackToList = () => {
    navigate('/crop-selection');
  };


  if (isFetching || isLoading) {
    return <PageContainer><GlobalLoader /><Loader /></PageContainer>;
  }
  if (errorMessage) {
    return <PageContainer><ErrorText role="alert">{errorMessage}</ErrorText></PageContainer>;
  }
  if (!sessionDetails || !barChartData || !lineChartData) {
    return <PageContainer><ErrorText>표시할 예측 결과가 없습니다.</ErrorText></PageContainer>;
  }

  const cropNames = sessionDetails.results.map((cropResult) => cropResult.crop_name);
  const adjustedDataList = sessionDetails.results.map((cropResult) => cropResult.adjusted_data);
  const selectedCrop = sessionDetails.results[selectedCropIndex];
  const allocatedArea = finiteNumberOrZero(selectedCrop.allocated_area);

  return (
    <PageContainer>
      {isLoading && <GlobalLoader />}
      <LayoutContainer>
        <SectionContainer>
          <InfoTableContainer>
            <SectionTitle>작물 조합 예상 소득</SectionTitle>
            <InfoTable>
              <tbody>
                <tr>
                  <td>지역</td>
                  <td>{sessionDetails.region}</td>
                </tr>
                <tr>
                  <td>선택한 작물</td>
                  <td>{cropNames.join(', ')}</td>
                </tr>
                <tr>
                  <td>토지 면적</td>
                  <td>{finiteNumberOrZero(sessionDetails.land_area).toLocaleString()} 평</td>
                </tr>
                <tr>
                  <td>연간 예상 소득</td>
                  <td>{formatKoreanCurrency(sessionDetails.total_income)}</td>
                </tr>
              </tbody>
            </InfoTable>
          </InfoTableContainer>
          <CropSelectorSection>
            <SectionTitle>작물별 상세 정보</SectionTitle>
            <Tabs aria-label="상세 정보를 확인할 작물 선택">
              {cropNames.map((cropName, index) => (
                <TabButton
                  key={cropName}
                  $active={index === selectedCropIndex}
                  aria-pressed={index === selectedCropIndex}
                  onClick={() => handleTabClick(index)}
                >
                  {cropName}
                </TabButton>
              ))}
            </Tabs>
          </CropSelectorSection>
          <CropDetailContainer>
            {isChartLoading ? (
              <Loader />
            ) : (
              <>
              <CropReportHeader>
                <CropReportTitle>{cropNames[selectedCropIndex]} 예상 소득</CropReportTitle>
                <CropReportGuide>{allocatedArea.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}평 기준 · 연간 예상</CropReportGuide>
              </CropReportHeader>
              <KpiGrid>
                <KpiCard $primary>
                  <KpiLabel>예상 소득</KpiLabel>
                  <KpiValue>{formatKoreanCurrency(adjustedDataList[selectedCropIndex]["소득 (원)"])}</KpiValue>
                </KpiCard>
                <KpiCard>
                  <KpiLabel>예상 총수입</KpiLabel>
                  <KpiValue>{formatKoreanCurrency(adjustedDataList[selectedCropIndex]["총수입 (원)"])}</KpiValue>
                </KpiCard>
                <KpiCard>
                  <KpiLabel>예상 경영비</KpiLabel>
                  <KpiValue>{formatKoreanCurrency(adjustedDataList[selectedCropIndex]["총경영비"])}</KpiValue>
                </KpiCard>
              </KpiGrid>
              <ExplanationText>* 예상 소득 = 예상 총수입 - 예상 경영비</ExplanationText>
              <SectionTitle>예상 비용</SectionTitle>
              <ExplanationText>* 아래 항목의 합계가 예상 경영비입니다.</ExplanationText>
              <ChartContainer $tall>
                {Object.keys(adjustedDataList[selectedCropIndex]).length > 0 ? (
                  <Bar data={barChartData} options={barChartOptions} />
                ) : (
                  <ErrorText>차트 데이터를 불러오는 과정에서 문제가 생겼습니다.</ErrorText>
                )}
              </ChartContainer>
              <SectionTitle>내일 도매가격 전망</SectionTitle>
              <ForecastCard>
                <ForecastLabel>{cropNames[selectedCropIndex]} 1kg 기준</ForecastLabel>
                  <ForecastValue>{finiteNumberOrZero(selectedCrop.price).toLocaleString()}원</ForecastValue>
              </ForecastCard>
              <ExplanationText>
                * 최근 도매가격 흐름을 바탕으로 계산한 참고값입니다.
              </ExplanationText>
              <SectionTitle>최근 1년간 일별 도매가격 추이</SectionTitle>
              <ChartContainer>
                {selectedCrop.crop_chart_data.length > 0 ? (
                  <Line
                    data={lineChartData}
                    options={lineChartOptions}
                  />
                ) : (
                  <ErrorText>가격 정보를 불러오지 못했습니다.</ErrorText>
                )}
              </ChartContainer>
              <ExplanationText>* 기상, 품질, 출하량과 시장 상황에 따라 실제 소득과 도매가격은 달라질 수 있습니다.</ExplanationText>
              </>
            )}
          </CropDetailContainer>
        </SectionContainer>
        <ButtonContainer>
          <Button onClick={handleBackToList}>목록으로 돌아가기</Button>
        </ButtonContainer>
      </LayoutContainer>
    </PageContainer>
  );
};

export default SessionDetails;
