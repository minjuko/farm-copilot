import React, { useCallback, useState, useRef } from 'react';
import styled from 'styled-components';
import { v4 as uuidv4 } from 'uuid';
import { useNavigate } from 'react-router-dom';
import Pagination from '../../molecules/Pagination';
import { fetchChatSessions } from '../../../apis/chat';
import { FaTrash, FaEdit, FaTimes } from 'react-icons/fa';
import ConfirmModal from '../../atoms/ConfirmModal';
import Modal from 'react-modal';
import { useLoading } from '../../../LoadingContext';
import GlobalLoader from "../../atoms/GlobalLoader";
import { useAuth } from '../../../AuthContext';
import { normalizeSessionName } from './chatFlow';
import useAsyncResource from '../../../hooks/useAsyncResource';
import useChatSessionActions from './useChatSessionActions';
import { color, shadow } from '../../../styles/theme';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px;
  background-color: ${color("background")};
  height: 100%;
  width: 100%;
  box-sizing: border-box;
`;

const ChatList = styled.ul`
  list-style: none;
  padding: 0;
  margin-top: 20px;
  max-height: 400px;
  overflow-y: auto;
  width: 100%;
  margin-bottom: 24px;
  max-width: 75rem;
`;

const ChatListItem = styled.li`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid ${color("borderStrong")};
  margin-bottom: 12px;
  background-color: ${color("background")};
  cursor: pointer;
  &:hover {
    background-color: ${color("surfaceHover")};
  }
`;

const NoChatMessage = styled.div`
  font-size: 16px;
  color: ${color("textMuted")};
  margin-top: 50px;
`;

const Button = styled.button`
  padding: 12px 16px;
  font-size: 16px;
  font-weight: bold;
  color: white;
  background-color: #4aaa87;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  &:hover {
    background-color: #6dc4b0;
  }
`;

const DeleteButton = styled.button`
  background: none;
  border: none;
  color: ${color("danger")};
  cursor: pointer;
  font-size: 18px;
  &:hover {
    color: ${color("dangerHover")};
  }
`;

const EditButton = styled.button`
  background: none;
  border: none;
  color: ${color("primary")};
  cursor: pointer;
  font-size: 18px;
  &:hover {
    color: #2faa9a;
  }
`;

const NewChatButton = styled(Button)`
  margin-top: 10px;
  padding: 12px 14px;
  font-size: 18px;
  font-weight: 600;
`;

const ModalContainer = styled(Modal)`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;  
  padding: 24px;
  background-color: white;
  border: 1px solid ${color("border")};
  border-radius: 8px;
  box-shadow: ${shadow("md")};
  position: absolute;
  top: 40%;
  left: 50%;
  transform: translate(-50%, -50%);
  max-width: 400px;
  width: 80%;
`;

const CloseButton = styled.button`
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
`;

const ModalTitle = styled.h2`
  font-size: 24px;
  margin-bottom: 30px;
  color: ${color("text")};
`;

const ModalContent = styled.div`
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
`;

const InputContainer = styled.div`
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 16px;
`;

const Input = styled.input`
  padding: 12px;
  font-size: 16px;
  border: 1px solid ${color("borderStrong")};
  border-radius: 4px;
  width: 100%; 
`;

const ErrorMessage = styled.div`
  color: red;
  margin-top: 8px;
  font-size: 14px;
  text-align: center; 
`;

const getChatSessionsError = () => '채팅 세션을 불러오는 중 오류가 발생했습니다.';

const ChatListTemplate = () => {
  const { setIsLoading } = useLoading();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [newSessionName, setNewSessionName] = useState('');
  const [editingSession, setEditingSession] = useState(null);
  const [sessionToDelete, setSessionToDelete] = useState(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [error, setError] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();
  const { status } = useAuth();
  const isLoggedIn = status === 'authenticated';
  const actionInFlight = useRef(false);
  const sessionsPerPage = 5;
  const loadChatSessions = useCallback(async () => {
    const response = await fetchChatSessions();
    if (!Array.isArray(response?.data)) throw new Error('MALFORMED_CHAT_SESSIONS');
    return response.data.filter(session => session.session_id !== null);
  }, []);
  const {
    data: chatSessions,
    error: loadError,
    setData: setChatSessions,
  } = useAsyncResource(loadChatSessions, {
    enabled: isLoggedIn,
    getError: getChatSessionsError,
    initialData: [],
  });
  const { rename, remove } = useChatSessionActions({
    setSessions: setChatSessions,
    setLoading: setIsLoading,
    setError: setErrorMessage,
  });
  const pageCount = Math.ceil(chatSessions.length / sessionsPerPage);
  const offset = currentPage * sessionsPerPage;

  const startNewChat = () => {
    setNewSessionName('');
    setError('');
    setErrorMessage('');
    if (!isLoggedIn) {
      const newSessionId = uuidv4();
      navigate(`/chat/${newSessionId}?session_name=농업GPT`);
    } else {
      setIsModalOpen(true);
    }
  };

  const handleNewChatSubmit = async () => {
    const trimmedSessionName = normalizeSessionName(newSessionName);
    if (!trimmedSessionName) {
      setError('제목을 입력해주세요');
      return;
    }
    if (actionInFlight.current) return;
    setError('');
    setErrorMessage('');
    if (editingSession) {
      const succeeded = await rename(editingSession, trimmedSessionName);
      if (!succeeded) return;
      setEditingSession(null);
      setIsModalOpen(false);
      setNewSessionName('');
    } else {
      const newSessionId = uuidv4();
      navigate(`/chat/${newSessionId}?session_name=${encodeURIComponent(trimmedSessionName)}`);
      setIsModalOpen(false);
      setNewSessionName('');
    }
  };

  const openChat = (sessionId, sessionName) => {
    navigate(`/chat/${sessionId}?session_name=${encodeURIComponent(sessionName)}`);
  };

  const confirmDeleteSession = (sessionId) => {
    setSessionToDelete(sessionId);
    setIsConfirmModalOpen(true);
  };

  const deleteSession = async () => {
    if (sessionToDelete && !actionInFlight.current) {
      await remove(sessionToDelete);
      setIsConfirmModalOpen(false);
      setSessionToDelete(null);
    }
  };

  const editSession = (session) => {
    setNewSessionName(session.session_name);
    setEditingSession(session);
    setIsModalOpen(true);
    setError('');
    setErrorMessage('');
  };

  const handlePageClick = ({ selected }) => {
    setCurrentPage(selected);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingSession(null);
    setError('');
    setErrorMessage('');
  };

  return (
    <Container>
      <GlobalLoader />
      {(loadError || errorMessage) && <ErrorMessage role="alert">{loadError || errorMessage}</ErrorMessage>}
      {status === 'checking' ? null : isLoggedIn ? (
        <>
          <NewChatButton onClick={startNewChat}>새 대화 시작하기</NewChatButton>
          {chatSessions.length === 0 ? (
            <NoChatMessage>대화 내역이 없습니다.</NoChatMessage>
          ) : (
            <>
              <ChatList>
                {chatSessions.slice(offset, offset + sessionsPerPage).map((session, index) => (
                  <ChatListItem key={session.session_id} onClick={() => openChat(session.session_id, session.session_name)}>
                    <span>
                      {session.session_name || session.session_id}
                    </span>
                    <div>
                      <EditButton onClick={(e) => { e.stopPropagation(); editSession(session); }}>
                        <FaEdit />
                      </EditButton>
                      <DeleteButton onClick={(e) => { e.stopPropagation(); confirmDeleteSession(session.session_id); }}>
                        <FaTrash />
                      </DeleteButton>
                    </div>
                  </ChatListItem>
                ))}
              </ChatList>
            </>
          )}
          <Pagination currentPage={currentPage} pageCount={pageCount} onPageChange={handlePageClick} />
          <ModalContainer
            isOpen={isModalOpen}
            onRequestClose={closeModal}
            appElement={document.getElementById('root')}
          >
            <CloseButton onClick={closeModal}><FaTimes /></CloseButton>
            <ModalTitle>{editingSession ? '대화 제목 수정' : '새 대화 생성'}</ModalTitle>
            <ModalContent>
              <InputContainer>
                <Input
                  type="text"
                  value={newSessionName}
                  onChange={(e) => setNewSessionName(e.target.value)}
                  placeholder="대화 제목 입력"
                  required
                />
                {error && <ErrorMessage>{error}</ErrorMessage>}
              </InputContainer>
              <Button onClick={handleNewChatSubmit}>{editingSession ? '수정' : '생성'}</Button>
            </ModalContent>
          </ModalContainer>
          <ConfirmModal
            isOpen={isConfirmModalOpen}
            onRequestClose={() => setIsConfirmModalOpen(false)}
            title="삭제 확인"
            content="이 대화를 삭제하시겠습니까?"
            onConfirm={deleteSession}
            closeModal={() => setIsConfirmModalOpen(false)}
            confirmText="삭제"
            cancelText="취소"
          />
        </>
      ) : (
        <NewChatButton onClick={startNewChat}>바로 챗봇 이용하기</NewChatButton>
      )}
    </Container>
  );
};

export default ChatListTemplate;
