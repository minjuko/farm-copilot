import { useEffect, useRef, useState } from "react";
import { fetchCapabilities, normalizeCapability } from "../../../apis/capabilities";
import { getApiErrorMessage, getServiceErrorMessage } from "../../../apis/error";
import {
  getCropNames,
  getSoilExamData,
  getSoilFertilizerInfo,
  searchSoilAddresses,
} from "../../../apis/predict";
import { useLoading } from "../../../LoadingContext";
import { buildFertilizerPayload, isFertilizerNotFound } from "./soilFlow";

const resetResultState = (setters) => {
  setters.setSoilData([]);
  setters.setSelectedSample(null);
  setters.setFertilizerData(null);
  setters.setIsFertilizerUnavailable(false);
};

export const useSoilAnalysis = () => {
  const { setIsLoading } = useLoading();
  const [cropName, setCropName] = useState("");
  const [cropNames, setCropNames] = useState([]);
  const [address, setAddress] = useState("");
  const [addressResults, setAddressResults] = useState([]);
  const [soilData, setSoilData] = useState([]);
  const [selectedSample, setSelectedSample] = useState(null);
  const [fertilizerData, setFertilizerData] = useState(null);
  const [isFertilizerUnavailable, setIsFertilizerUnavailable] = useState(false);
  const [error, setError] = useState(null);
  const [isErrorModalOpen, setIsErrorModalOpen] = useState(false);
  const [isSoilLoading, setIsSoilLoading] = useState(false);
  const [isFertilizerLoading, setIsFertilizerLoading] = useState(false);
  const [isAddressSearching, setIsAddressSearching] = useState(false);
  const [serviceCapability, setServiceCapability] = useState({
    status: "checking",
    available: false,
  });
  const soilRequestInFlight = useRef(false);
  const fertilizerRequestInFlight = useRef(false);

  const resultSetters = {
    setSoilData,
    setSelectedSample,
    setFertilizerData,
    setIsFertilizerUnavailable,
  };

  const showError = (message) => {
    setError(message);
    setIsErrorModalOpen(true);
  };

  useEffect(() => {
    let isActive = true;
    fetchCapabilities()
      .then((response) => {
        if (isActive) setServiceCapability(normalizeCapability(response?.data, "soil"));
      })
      .catch(() => {
        if (isActive) setServiceCapability({ status: "limited", available: false });
      });
    return () => { isActive = false; };
  }, []);

  useEffect(() => {
    let isActive = true;
    getCropNames()
      .then((response) => {
        if (isActive) setCropNames(Array.isArray(response?.data?.crop_names) ? response.data.crop_names : []);
      })
      .catch(() => {
        if (isActive) showError("작물 이름을 불러오는 중 오류가 발생했습니다.");
      });
    return () => { isActive = false; };
  }, []);

  const changeCropName = (value) => {
    setCropName(value);
    resetResultState(resultSetters);
  };

  const selectCrop = (value) => {
    setCropName(value);
    resetResultState(resultSetters);
  };

  const changeAddress = (value) => {
    setAddress(value);
    setAddressResults([]);
    resetResultState(resultSetters);
  };

  const searchAddress = async () => {
    if (!serviceCapability.available || isAddressSearching) return;
    if (!address.trim()) {
      showError("검색할 주소를 입력해 주세요.");
      return;
    }
    try {
      setIsAddressSearching(true);
      const response = await searchSoilAddresses(address.trim());
      const addressResults = response?.data?.results;
      if (!Array.isArray(addressResults) || addressResults.length === 0) {
        setAddressResults([]);
        showError("검색된 주소가 없습니다.");
        return;
      }
      setAddress(response?.data?.normalized_query || address.trim());
      setAddressResults(addressResults);
      setError(null);
    } catch (requestError) {
      setAddressResults([]);
      showError(getApiErrorMessage(
        requestError,
        "주소 검색 서비스를 사용할 수 없습니다. 잠시 후 다시 시도해주세요."
      ));
    } finally {
      setIsAddressSearching(false);
    }
  };

  const fetchSoilExamData = async (selectedAddress = address) => {
    if (!serviceCapability.available) {
      showError("토양 분석 외부 API가 설정되지 않아 현재 실시간 조회를 지원하지 않습니다.");
      return;
    }
    if (soilRequestInFlight.current) return;
    if (!cropNames.includes(cropName) || !selectedAddress.trim()) {
      showError("작물 이름과 주소를 정확히 입력해 주세요.");
      return;
    }

    try {
      soilRequestInFlight.current = true;
      setIsSoilLoading(true);
      setIsLoading(true);
      resetResultState(resultSetters);
      const response = await getSoilExamData(cropName, selectedAddress.trim());
      const soilItems = response?.data?.soil_data;
      if (!Array.isArray(soilItems) || soilItems.length === 0) {
        showError("현재 주소에 해당하는 데이터가 없습니다.");
        return;
      }
      setSoilData(soilItems);
      setError(null);
    } catch (requestError) {
      setSoilData([]);
      showError(getApiErrorMessage(
        requestError,
        "토양 분석 서비스를 사용할 수 없습니다. 잠시 후 다시 시도해주세요."
      ));
    } finally {
      soilRequestInFlight.current = false;
      setIsSoilLoading(false);
      setIsLoading(false);
    }
  };

  const selectAddress = (addressResult) => {
    const selectedAddress = addressResult.display_name || addressResult.address_name;
    setAddress(selectedAddress);
    setAddressResults([]);
    fetchSoilExamData(selectedAddress);
  };

  const selectSample = async (sampleIndex) => {
    if (!serviceCapability.available || fertilizerRequestInFlight.current) return;
    const selectedSoilSample = soilData[Number(sampleIndex)];
    if (!selectedSoilSample) return;
    setSelectedSample(selectedSoilSample);
    setFertilizerData(null);
    setIsFertilizerUnavailable(false);

    const { payload, error: payloadError } = buildFertilizerPayload({
      cropName,
      address: address.trim(),
      soilItem: selectedSoilSample,
    });
    if (payloadError) {
      showError(payloadError);
      return;
    }

    try {
      fertilizerRequestInFlight.current = true;
      setIsFertilizerLoading(true);
      setIsLoading(true);
      const response = await getSoilFertilizerInfo(payload);
      const fertilizerItems = response?.data?.data;
      if (!Array.isArray(fertilizerItems) || fertilizerItems.length === 0) {
        setIsFertilizerUnavailable(true);
        return;
      }
      setFertilizerData(fertilizerItems);
      setError(null);
    } catch (requestError) {
      if (isFertilizerNotFound(requestError)) {
        setIsFertilizerUnavailable(true);
      } else {
        showError(getServiceErrorMessage(
          requestError,
          "비료 추천 서비스를 사용할 수 없습니다. 잠시 후 다시 시도해주세요."
        ));
      }
      setFertilizerData(null);
    } finally {
      fertilizerRequestInFlight.current = false;
      setIsFertilizerLoading(false);
      setIsLoading(false);
    }
  };

  return {
    address,
    addressResults,
    changeAddress,
    changeCropName,
    closeErrorModal: () => setIsErrorModalOpen(false),
    cropName,
    cropNames,
    error,
    isErrorModalOpen,
    fertilizerData,
    isFertilizerUnavailable,
    isAddressSearching,
    isFertilizerLoading,
    isSoilLoading,
    searchAddress,
    selectAddress,
    selectCrop,
    selectSample,
    selectedSample,
    serviceCapability,
    soilData,
  };
};
