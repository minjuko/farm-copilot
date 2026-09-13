import React from "react";
import { useNavigate } from "react-router-dom";
import styled from "styled-components";
import CustomModal from "../../atoms/CustomModal";
import AddressSearch from "./AddressSearch";
import CropAutocomplete from "./CropAutocomplete";
import SoilResults from "./SoilResults";
import SoilSampleSelect from "./SoilSampleSelect";
import { useSoilAnalysis } from "./useSoilAnalysis";

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  padding: 32px 24px 24px;
  box-sizing: border-box;
  background-color: #f9f9f9;
  min-height: 100vh;
  @media (max-width: 768px) {
    padding: 16px;
  }
`;

const BoxContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: stretch;
  background-color: #fff;
  padding: 24px;
  border: 1px solid #e1e9e5;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(35, 74, 58, 0.08);
  width: 100%;
  max-width: 600px;
  box-sizing: border-box;
  @media (max-width: 768px) { padding: 20px 16px; }
`;
const Toast = styled.div`
  position: fixed;
  top: 76px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1200;
  width: max-content;
  max-width: calc(100vw - 32px);
  padding: 12px 18px;
  box-sizing: border-box;
  border-radius: 999px;
  background: #263a32;
  color: #fff;
  box-shadow: 0 8px 24px rgba(22, 44, 35, 0.22);
  font-size: 0.9rem;
  font-weight: 600;
  text-align: center;
`;

const SoilTemplate = () => {
  const navigate = useNavigate();
  const analysis = useSoilAnalysis();
  const serviceAvailable = analysis.serviceCapability.available;
  const hasValidCrop = analysis.cropNames.includes(analysis.cropName);
  const hasAddress = Boolean(analysis.address.trim());
  const sampleGuidance = !hasValidCrop && !hasAddress
    ? "작물 이름과 주소를 먼저 입력해주세요."
    : !hasValidCrop
      ? "작물 이름을 목록에서 선택해주세요."
      : !hasAddress
        ? "주소를 입력해주세요."
        : analysis.isSoilLoading
          ? "상세 주소를 불러오고 있습니다."
          : "주소 검색 버튼을 눌러 상세 주소를 불러와주세요.";

  return (
    <Container>
      {analysis.toastMessage && <Toast role="status">{analysis.toastMessage}</Toast>}
      <BoxContainer>
        <CropAutocomplete
          cropName={analysis.cropName}
          cropNames={analysis.cropNames}
          onChange={analysis.changeCropName}
          onSelect={analysis.selectCrop}
        />
        <AddressSearch
          address={analysis.address}
          disabled={analysis.isAddressSearching || analysis.isSoilLoading || !serviceAvailable}
          isSearching={analysis.isAddressSearching}
          onChange={analysis.changeAddress}
          onSearch={analysis.searchAddress}
          onSelect={analysis.selectAddress}
          results={analysis.addressResults}
        />
        <SoilSampleSelect
          disabled={analysis.isFertilizerLoading || !serviceAvailable}
          guidance={sampleGuidance}
          onSelect={analysis.selectSample}
          samples={analysis.soilData}
          selectedSample={analysis.selectedSample}
        />
      </BoxContainer>
      <CustomModal
        isOpen={analysis.isErrorModalOpen}
        onRequestClose={analysis.closeErrorModal}
        title="오류"
        content={analysis.error}
        onConfirm={analysis.closeErrorModal}
        showConfirmButton={false}
        isError
        overlayStyles={{ zIndex: 1103 }}
        contentStyles={{ zIndex: 1104 }}
      />
      {analysis.selectedSample && (
        <SoilResults
          cropName={analysis.cropName}
          selectedSoilSample={analysis.selectedSample}
          fertilizerData={analysis.fertilizerData}
          isFertilizerUnavailable={analysis.isFertilizerUnavailable}
          isFertilizerLoading={analysis.isFertilizerLoading}
          handleBackToList={() => navigate("/soil-list")}
        />
      )}
    </Container>
  );
};

export default SoilTemplate;
