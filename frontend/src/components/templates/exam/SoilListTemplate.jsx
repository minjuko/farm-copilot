import React, { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import styled from "styled-components";
import { FaTrash } from 'react-icons/fa';
import ConfirmModal from "../../atoms/ConfirmModal";
import { getSoilCropData, deleteSoilData } from "../../../apis/predict";
import { useLoading } from "../../../LoadingContext";
import Pagination from "../../molecules/Pagination";
import useAsyncResource from "../../../hooks/useAsyncResource";

const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.5rem 0.8rem;
  background-color: #f9f9f9;
  min-height: 100vh;
`;

const SessionList = styled.div`
  width: 100%;
  padding: 1rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  max-width: 75rem;
`;

const SessionItem = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.625rem;
  border: 1px solid #ccc;
  border-radius: 0.625rem;
  background-color: #fff;
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.1);
  cursor: pointer;
  position: relative;
  margin: 0 0.5rem;

  @media (max-width: 37.5rem) {
    flex-direction: column;
    align-items: flex-start;
  }
`;

const SessionInfo = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.3125rem;

  @media (max-width: 37.5rem) {
    gap: 0.125rem;
  }
`;

const SessionDate = styled.div`
  font-size: 0.875rem;
  color: #888;
`;

const DeleteButton = styled.button`
  background: none;
  border: none;
  color: #e53e3e;
  cursor: pointer;
  font-size: 1.125rem;
  position: absolute;
  top: 0.625rem;
  right: 0.625rem;

  &:hover {
    color: #c53030;
  }
`;

const AddButton = styled.button`
  background-color: #4aaa87;
  color: white;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 0.3125rem;
  cursor: pointer;
  font-size: 1.3rem;
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.1);
  margin-top: 0.2rem;

  &:hover {
    background-color: #3b8b6d;
  }

  @media (max-width: 37.5rem) {
    padding: 0.5rem 1rem;
    font-size: 1rem;
  }
`;

const PaginationContainer = styled.div`
  display: flex;
  justify-content: center;

  .pagination {
    display: flex;
    list-style: none;
    padding: 0;
  }

  .pagination li {
    margin: 0 0.3125rem;
  }

  .pagination li a {
    padding: 0.5rem 0.75rem;
    border: 1px solid #ddd;
    border-radius: 0.25rem;
    cursor: pointer;
    color: #4aaa87;
    text-decoration: none;
    transition: background-color 0.3s, color 0.3s;
  }

  .pagination li a:hover {
    background-color: #f5f5f5;
    color: #3e8e75;
  }

  .pagination li.active a {
    background-color: #4aaa87;
    color: white;
    border: none;
  }

  .pagination li.previous a,
  .pagination li.next a {
    color: #888;
  }

  .pagination li.disabled a {
    color: #ccc;
    cursor: not-allowed;
  }
`;

const NoDataText = styled.p`
  font-size: 1rem;
  color: #888;
  margin-top: 2rem;
`;

const formatDateTime = (dateString) => {
  const options = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  };
  return new Date(dateString).toLocaleDateString('ko-KR', options);
};

const getSoilHistoryError = () => (
  "토양 분석 내역을 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
);

const SoilListTemplate = () => {
  const { setIsLoading } = useLoading();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [actionError, setActionError] = useState("");
  const navigate = useNavigate();
  const sessionsPerPage = 4;
  const loadSoilHistory = useCallback(async () => {
    const response = await getSoilCropData();
    if (!Array.isArray(response?.data)) throw new Error("MALFORMED_SOIL_HISTORY");
    return response.data;
  }, []);
  const {
    data: soilData,
    error: loadError,
    setData: setSoilData,
  } = useAsyncResource(loadSoilHistory, {
    getError: getSoilHistoryError,
    initialData: [],
  });

  const handleSoilDataClick = (data) => {
    navigate(`/soil_details/${data.session_id}`, {
      state: { soilData: data.soil_data, fertilizerData: data.fertilizer_data, crop: data.crop_name, crop_add: data.detailed_address },
    });
  };

  const handleDeleteSoilData = async () => {
    try {
      setActionError("");
      setIsLoading(true);
      await deleteSoilData(selectedSessionId);
      setSoilData((current) => current.filter(soil => soil.session_id !== selectedSessionId));
      closeModal();
    } catch {
      setActionError("토양 데이터 삭제에 실패했습니다. 다시 시도해주세요.");
    } finally {
      setIsLoading(false);
    }
  };

  const openModal = (sessionId) => {
    setSelectedSessionId(sessionId);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedSessionId(null);
  };

  const handleAddClick = () => {
    navigate('/soil');
  };

  const handlePageChange = ({ selected }) => {
    setCurrentPage(selected);
  };

  const indexOfLastSession = (currentPage + 1) * sessionsPerPage;
  const indexOfFirstSession = indexOfLastSession - sessionsPerPage;
  const currentSessions = Object.keys(soilData.reduce((acc, item) => {
    if (!acc[item.session_id]) {
      acc[item.session_id] = [];
    }
    acc[item.session_id].push(item);
    return acc;
  }, {})).slice(indexOfFirstSession, indexOfLastSession);

  const pageCount = Math.ceil(Object.keys(soilData.reduce((acc, item) => {
    if (!acc[item.session_id]) {
      acc[item.session_id] = [];
    }
    acc[item.session_id].push(item);
    return acc;
  }, {})).length / sessionsPerPage);

  return (
    <PageContainer>
      <AddButton onClick={handleAddClick}>새 토양 데이터 추가</AddButton>
      {(loadError || actionError) ? (
        <NoDataText role="alert">{loadError || actionError}</NoDataText>
      ) : currentSessions.length === 0 ? (
        <NoDataText>목록이 존재하지 않습니다. 첫 토양 분석을 진행해보세요</NoDataText>
      ) : (
        <SessionList>
          {currentSessions.map(sessionId => (
            <SessionItem key={sessionId} onClick={() => handleSoilDataClick(soilData.find(soil => soil.session_id === sessionId))}>
              <SessionInfo>
                <SessionDate>{formatDateTime(soilData.find(soil => soil.session_id === sessionId).created_at)}</SessionDate>
                <div><strong>작물:</strong> {soilData.find(soil => soil.session_id === sessionId).crop_name}</div>
                <div><strong>주소:</strong> {soilData.find(soil => soil.session_id === sessionId).address}</div>
                <div><strong>상세 주소:</strong> {soilData.find(soil => soil.session_id === sessionId).detailed_address}</div>
              </SessionInfo>
              <DeleteButton onClick={(e) => {
                e.stopPropagation();
                openModal(sessionId);
              }}>
                <FaTrash />
              </DeleteButton>
            </SessionItem>
          ))}
        </SessionList>
      )}
      <Pagination currentPage={currentPage} pageCount={pageCount} onPageChange={handlePageChange} />
      <ConfirmModal
        isOpen={isModalOpen}
        onRequestClose={closeModal}
        title="삭제 확인"
        content="정말로 이 토양 데이터를 삭제하시겠습니까?"
        onConfirm={handleDeleteSoilData}
        closeModal={closeModal}
        confirmText="삭제"
        cancelText="취소"
        confirmColor="#e53e3e"
        confirmHoverColor="#c53030"
        cancelColor="#4aaa87"
        cancelHoverColor="#3b8b6d"
      />
    </PageContainer>
  );
};

export default SoilListTemplate;
