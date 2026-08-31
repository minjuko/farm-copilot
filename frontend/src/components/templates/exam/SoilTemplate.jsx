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
  padding: 24px;
  background-color: #f9f9f9;
  min-height: 160vh;
  @media (max-width: 768px) { padding: 16px; }
`;

const BoxContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  background-color: #fff;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 600px;
  @media (max-width: 768px) { padding: 12px; }
`;

const Divider = styled.hr`
  width: 100%;
  max-width: 600px;
  border: 1px solid #ccc;
`;

const ServiceNotice = styled.div`
  width: 100%;
  max-width: 600px;
  box-sizing: border-box;
  margin-bottom: 1rem;
  padding: 0.75rem;
  text-align: center;
  color: ${({ $available }) => ($available ? "#1f6b4f" : "#5d4a00")};
  background-color: ${({ $available }) => ($available ? "#e8f5e9" : "#fff8e1")};
  border-radius: 6px;
`;

const Help = styled.p`
  color: #7f8c8d;
  font-size: 0.875rem;
  margin-top: 0.625rem;
`;

const SoilTemplate = () => {
  const navigate = useNavigate();
  const analysis = useSoilAnalysis();
  const serviceAvailable = analysis.serviceCapability.available;

  return (
    <Container>
      <ServiceNotice $available={serviceAvailable} role="status">
        {serviceAvailable
          ? "LIVE · 토양 검사 및 비료 처방 외부 API가 설정되어 있습니다."
          : "LIMITED · 외부 API가 설정된 환경에서만 실시간 토양 분석을 제공합니다."}
      </ServiceNotice>
      <BoxContainer>
        <Help>토양 분석을 위한 작물 이름과 주소를 입력하세요.</Help>
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
          onSelect={analysis.selectSample}
          samples={analysis.soilData}
        />
      </BoxContainer>
      <Divider />
      <CustomModal
        isOpen={analysis.errorModalIsOpen}
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
          fertilizerUnavailable={analysis.fertilizerUnavailable}
          isFertilizerLoading={analysis.isFertilizerLoading}
          handleBackToList={() => navigate("/soillist")}
        />
      )}
    </Container>
  );
};

export default SoilTemplate;
