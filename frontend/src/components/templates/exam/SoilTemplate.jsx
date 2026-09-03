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
