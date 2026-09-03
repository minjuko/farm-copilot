import React, { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import styled from "styled-components";
import { fetchDetectionSessions, deleteDetectionSession } from "../../../apis/predict";
import { FaTrash, FaPlus } from 'react-icons/fa';
import ConfirmModal from '../../atoms/ConfirmModal';
import Pagination from '../../molecules/Pagination';
import { useLoading } from "../../../LoadingContext";
import GlobalLoader from "../../atoms/GlobalLoader";
import useAsyncResource from "../../../hooks/useAsyncResource";
import { EmptyState, ListPage } from "../../../styles/primitives";
import { color, shadow } from "../../../styles/theme";
import {
  formatDetectionConfidence,
  normalizeMediaUrl,
} from "./detectFlow";

const Content = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 75rem; 
  margin-top: 1rem;

  @media (max-width: 48rem) { 
    max-width: 37.5rem; 
  }

  @media (max-width: 30rem) { 
    max-width: 100%;
  }
`;

const SessionList = styled.div`
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.7rem; 
  max-width: 75rem;
`;

const SessionItem = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.625rem;
  border: 1px solid ${color("borderStrong")};
  border-radius: 0.625rem; 
  background-color: ${color("background")};
  box-shadow: ${shadow("sm")};
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  &:hover {
    background-color: ${color("surfaceHover")};
    transform: translateY(-0.125rem); 
    box-shadow: 0 0.25rem 0.5rem rgba(0, 0, 0, 0.2);
  }
  flex-wrap: wrap;
  font-size: clamp(0.8rem, 2.5vw, 1.2rem); 
  position: relative;
`;

const SessionInfo = styled.div`
  display: flex;
  flex-direction: column;
  padding: 0.8rem 0.35rem; 
  gap: 0.3125rem; 
  flex: 1;
  min-width: 9.375rem; 
  font-size: clamp(0.9rem, 2.5vw, 1.2rem); 
`;

const SessionImage = styled.img`
  width: 5rem; 
  height: 5rem; 
  object-fit: cover;
  border-radius: 0.3125rem; 
  margin-right: 0.625rem; 
  flex-shrink: 0;

  @media (max-width: 48rem) { 
    margin-bottom: 0.5rem; 
    margin-right: 0;
  }

  @media (max-width: 30rem) { 
    margin-bottom: 0rem; 
    margin-right: 0;
  }
`;

const DeleteButton = styled.button`
  position: absolute;
  top: 0.7rem; 
  right: 0.5rem; 
  background: none;
  border: none;
  color: ${color("danger")};
  cursor: pointer;
  font-size: 1.2rem; 

  &:hover {
    color: ${color("dangerHover")};
  }
`;

const AddButtonContainer = styled.button`
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 0.5rem 1rem;
  margin-top: 0.5rem;
  background-color: ${color("primary")};
  color: white;
  border: none;
  border-radius: 0.3rem;
  box-shadow: ${shadow("sm")};
  transition: background-color 0.3s;
  font-size: clamp(1rem, 2.5vw, 1.2rem);

  &:hover {
    background-color: ${color("primaryFocus")};
  }

  &:focus {
    outline: none;
    box-shadow: 0 0 0 0.1875rem rgba(58, 151, 212, 0.5);
  }

  &:active {
    background-color: ${color("primaryFocus")};
  }
`;

const AddButtonIcon = styled(FaPlus)`
  margin-right: 0.5rem; 
`;

const AddButtonText = styled.span`
  font-size: 1rem;
  font-weight: 600;
`;

const getDiagnosisHistoryError = () => (
  "진단 내역을 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
);

const DiagnosisListTemplate = () => {
  const { setIsLoading } = useLoading();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [sessionIdToDelete, setSessionIdToDelete] = useState(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);
  const [actionError, setActionError] = useState("");
  const navigate = useNavigate();

  const loadSessions = useCallback(async () => {
    const response = await fetchDetectionSessions();
    if (!Array.isArray(response?.data)) throw new Error("MALFORMED_DETECTION_HISTORY");
    return response.data;
  }, []);
  const {
    data: sessions,
    error: loadError,
    isLoading,
    setData: setSessions,
  } = useAsyncResource(loadSessions, {
    getError: getDiagnosisHistoryError,
    initialData: [],
  });

  const sessionsPerPage = 4;
  const pageCount = Math.ceil(sessions.length / sessionsPerPage);
  const offset = currentPage * sessionsPerPage;

  const handleSessionClick = (sessionId) => {
    navigate(`/info/${sessionId}`);
  };

  const handleDeleteSession = async () => {
    try {
      setActionError("");
      setIsLoading(true);
      setIsDeleting(true);
      await deleteDetectionSession(sessionIdToDelete);
      setSessions((current) => current.filter(session => session.session_id !== sessionIdToDelete));
      setIsModalOpen(false);
    } catch (error) {
      setActionError("세션 삭제에 실패했습니다. 다시 시도해주세요.");
    } finally {
      setIsLoading(false);
      setIsDeleting(false);
    }
  };

  const handleAddClick = () => {
    navigate('/diagnosis');
  };

  const handleOpenDeleteModal = (sessionId) => {
    setSessionIdToDelete(sessionId);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handlePageClick = ({ selected }) => {
    setCurrentPage(selected);
  };

  return (
    <ListPage>
      {(isLoading || isDeleting) && <GlobalLoader />}
      <AddButtonContainer onClick={handleAddClick} aria-label="새 진단 시작하기">
        <AddButtonIcon />
        <AddButtonText>새 진단 시작하기</AddButtonText>
      </AddButtonContainer>

      <Content>
        {(loadError || actionError) ? (
          <EmptyState $error={Boolean(loadError || actionError)} role="alert">{loadError || actionError}</EmptyState>
        ) : sessions.length === 0 ? (
          <EmptyState>진단 목록이 존재하지 않습니다. 첫 진단을 시작해보세요!</EmptyState>
        ) : (
          <>
            <SessionList>
              {sessions.slice(offset, offset + sessionsPerPage).map(session => (
                <SessionItem key={session.session_id} onClick={() => handleSessionClick(session.session_id)} tabIndex="0" aria-label={`${session.pest_name || "정보 없음"} 진단 결과 보기`}>
                  {normalizeMediaUrl(session.user_image_url) && (
                    <SessionImage
                      src={normalizeMediaUrl(session.user_image_url)}
                      alt={session.pest_name || "진단 이미지"}
                      onError={(event) => { event.currentTarget.style.display = "none"; }}
                    />
                  )}
                  <SessionInfo>
                    <div><strong>질병명:</strong> {session.pest_name && session.pest_name !== "0" ? session.pest_name : "정보 없음"}</div>
                    <div><strong>진단 날짜:</strong> {session.detection_date || "정보 없음"}</div>
                    <div><strong>AI 모델 정확도:</strong> {formatDetectionConfidence(session.confidence)}</div>
                  </SessionInfo>
                  <DeleteButton onClick={(e) => {
                    e.stopPropagation();
                    handleOpenDeleteModal(session.session_id);
                  }} aria-label="세션 삭제">
                    <FaTrash />
                  </DeleteButton>
                </SessionItem>
              ))}
            </SessionList>
            <Pagination currentPage={currentPage} pageCount={pageCount} onPageChange={handlePageClick} />
          </>
        )}
      </Content>
      <ConfirmModal
        isOpen={isModalOpen}
        onRequestClose={handleCloseModal}
        title="삭제 확인"
        content="이 항목을 삭제하시겠습니까?"
        onConfirm={handleDeleteSession}
        closeModal={handleCloseModal}
        confirmText="삭제"
        cancelText="취소"
        confirmColor="#e53e3e"
        confirmHoverColor="#c53030"
        cancelColor="#4aaa87"
        cancelHoverColor="#3b8b6d"
      />
    </ListPage>
  );
};

export default DiagnosisListTemplate;
