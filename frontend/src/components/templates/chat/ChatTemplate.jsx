import React, { useState, useEffect, useRef } from 'react';
import styled, { css } from 'styled-components';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { fetchChatHistory, sendChatMessage } from '../../../apis/chat';
import { useAuth } from '../../../AuthContext';
import {
  buildChatPayload,
  getChatErrorMessage,
  normalizeChatHistory,
  normalizeChatResponse,
} from './chatFlow';
import SyncLoader from 'react-spinners/SyncLoader';
import { IoMenu } from "react-icons/io5";
import { FaPaperPlane } from "react-icons/fa";

const Container = styled.div`
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100%;
  background-color: #ffffff;
  box-sizing: border-box;
  overflow: hidden;
  padding-bottom: 4.375rem; 
  min-height: auto;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem; 
  background-color: #4AAA87;
  color: white;
  font-size: 1.25rem; 
  font-weight: bold;
  position: relative;

  @media (max-width: 768px) {
    font-size: 1.125rem; 
    padding: 0.75rem;
  }
`;

const Title = styled.div`
  flex: 1;
  text-align: center;
`;

const ChatListButton = styled.button`
  position: absolute;
  left: 0.3125rem; 
  padding: 0.625rem 0.75rem; 
  font-weight: 600;
  color: white;
  background-color: #4AAA87;
  border: none;
  border-radius: 1.25rem; 
  cursor: pointer;

  svg {
    margin-bottom: -0.125rem; 
  }
`;

const ChatBox = styled.div`
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 1rem; 
  background-color: #E6F8E0;
  overflow-y: auto;
`;

const MessageList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0;
`;

const MessageContainer = styled.li`
  display: flex;
  align-items: flex-start;
  margin-bottom: 0.75rem; 
  justify-content: ${({ isUser }) => (isUser ? 'flex-end' : 'flex-start')};

  @media (max-width: 768px) {
    margin-bottom: 0.5rem; 
  }
`;

const Message = styled.div`
  max-width: 70%;
  display: flex;
  flex-direction: column;
  align-items: ${({ isUser }) => (isUser ? 'flex-end' : 'flex-start')};
  padding: 0.625rem 0.875rem; 
  border-radius: 1.25rem; 
  background-color: ${({ isUser }) => (isUser ? '#F7FE2E' : 'white')};
  position: relative;
  box-shadow: 0 0.0625rem 0.0625rem rgba(0, 0, 0, 0.1); 
  word-break: break-word;
  margin-top: 0.5rem;

  @media (max-width: 768px) {
    padding: 0.5rem 0.625rem; 
  }
`;

const MessageText = styled.div`
  flex: 1;
`;

const MessageTime = styled.small`
  margin-top: 0.25rem;
  font-size: 0.8em;
  color: #666;
  ${({ isUser }) => isUser ? css`align-self: flex-end;` : css`align-self: flex-start;`}
`;

const ProfileImage = styled.img`
  width: 3.125rem; 
  height: 3.125rem; 
  border-radius: 50%;
  margin-right: ${({ isUser }) => (isUser ? '0' : '0.625rem')}; 
  margin-left: ${({ isUser }) => (isUser ? '0.625rem' : '0')}; 

  @media (max-width: 768px) {
    width: 2.5rem; 
    height: 2.5rem; 
    margin-right: ${({ isUser }) => (isUser ? '0' : '0.375rem')};
    margin-left: ${({ isUser }) => (isUser ? '0.375rem' : '0')}; 
  }
`;

const InputBox = styled.form`
  display: flex;
  align-items: center; 
  padding: 1.25rem 0.75rem; 
  background-color: #f0f0f0;
  border-top: 1px solid #ddd;
  width: 100%;
  box-sizing: border-box;
  position: fixed;
  bottom: 60px; 
  left: 0;
  right: 0;

  @media (max-width: 768px) {
    padding: 1rem; 
  }
`;

const Input = styled.input`
  flex-grow: 1;
  padding: 0.8rem; 
  border: 1px solid #ddd;
  border-radius: 1rem; 
  margin-right: 0.5rem; 
  font-size: 1rem; 
  &:focus {
    outline: none;
    border-color: #4aaa87;
  }

  @media (max-width: 768px) {
    padding: 0.6rem; 
    margin-right: 0.25rem;
  }
`;

const Button = styled.button`
  flex-shrink: 0;
  padding: 0.625rem 1rem; 
  font-size: 0.875rem; 
  color: white;
  background-color: #4aaa87;
  border: none;
  border-radius: 1rem;
  cursor: pointer;
  &:hover {
    background-color: #6dc4b0;
  }

  @media (max-width: 768px) {
    padding: 0.5rem 0.75rem; 
    font-size: 0.75rem; 
  }
`;

const ErrorMessage = styled.div`
  color: red;
  margin-top: 0.5rem; 
  font-size: 0.875rem; 
  text-align: center; 
`;

const LimitedNotice = styled.div`
  padding: 0.75rem;
  text-align: center;
  background-color: #fff8e1;
  color: #5d4a00;
`;

const ChatTemplate = () => {
  const { sessionid } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const sessionId = sessionid;
  const [errorMessage, setErrorMessage] = useState('');
  const { status } = useAuth();

  const chatBoxRef = useRef(null);
  const requestInFlight = useRef(false);

  const params = new URLSearchParams(location.search);
  const sessionName = params.get('session_name');

  useEffect(() => {
    if (status === 'authenticated') {
      const fetchHistory = async () => {
        try {
          const response = await fetchChatHistory(sessionId);
          const orderedMessages = normalizeChatHistory(response?.data);
          if (!orderedMessages) throw new Error('MALFORMED_CHAT_HISTORY');
          setMessages(orderedMessages);
          setErrorMessage('');
        } catch (error) {
          setErrorMessage('채팅 기록을 불러오는 중 오류가 발생했습니다.');
        }
      };

      fetchHistory();
    } else if (status === 'unauthenticated') {
      setMessages([]);
    }
  }, [sessionId, status]);

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const { payload, error } = buildChatPayload({
      question: inputValue,
      sessionId,
      sessionName,
    });
    if (error) {
      setErrorMessage(error);
      return;
    }
    if (requestInFlight.current) return;

    const userMessage = {
      isUser: true,
      text: payload.question,
      timestamp: new Date().toISOString()
    };
    setMessages((current) => [...current, userMessage]);
    setInputValue('');
    setErrorMessage('');
    requestInFlight.current = true;
    setLoading(true);

    try {
      const response = await sendChatMessage(payload);
      const botMessage = normalizeChatResponse(response?.data);
      if (!botMessage) throw new Error('MALFORMED_CHAT_RESPONSE');
      setMessages((prevMessages) => [...prevMessages, botMessage]);
    } catch (error) {
      setErrorMessage(getChatErrorMessage(error));
    } finally {
      requestInFlight.current = false;
      setLoading(false);
    }
  };

  return (
    <Container>
      <Header>
        <Title>{sessionName || '농업 GPT'}</Title>
        <ChatListButton onClick={() => navigate('/chatlist')}><IoMenu />  목록 보기</ChatListButton>
      </Header>
      <LimitedNotice>ARCHIVED / LIMITED · 환경이 준비된 경우에만 챗봇 답변을 제공합니다.</LimitedNotice>
      <ChatBox ref={chatBoxRef}>
        <MessageList>
          {messages.map((msg, index) => (
            <MessageContainer key={index} isUser={msg.isUser}>
              {!msg.isUser && <ProfileImage src={`${process.env.PUBLIC_URL}/android-chrome-192x192.png`} alt="Profile" />}
              <Message isUser={msg.isUser}>
                <MessageText>
                  {!msg.isUser ? (
                    <div dangerouslySetInnerHTML={{ __html: msg.text }} />
                  ) : (
                    <>
                      {msg.text}
                      <br/>
                    </>
                  )}
                </MessageText>
                <MessageTime isUser={msg.isUser}>{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</MessageTime>
              </Message>
              {msg.isUser && <ProfileImage src={`${process.env.PUBLIC_URL}/user_icon.jpg`} alt="Profile" isUser />}
            </MessageContainer>
          ))}
          {loading && (
            <MessageContainer isUser={false}>
              <ProfileImage src={`${process.env.PUBLIC_URL}/android-chrome-192x192.png`} alt="Profile" />
              <Message isUser={false} style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <span>답변을 불러오는 중입니다.</span>
                  <SyncLoader
                    color="#75e781"
                    loading={loading}
                    margin={2}
                    size={8}
                    speedMultiplier={0.7}
                    style={{ marginLeft: '10px' }}
                  />
                </div>
              </Message>
            </MessageContainer>
          )}
        </MessageList>
      </ChatBox>
      <InputBox onSubmit={handleSubmit}>
        <Input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="질문을 입력하세요"
          disabled={loading}
        />
        <Button type="submit" disabled={loading} aria-label="질문 보내기"><FaPaperPlane size="20px"/></Button>
      </InputBox>
      {errorMessage && <ErrorMessage role="alert">{errorMessage}</ErrorMessage>}
    </Container>
  );
};

export default ChatTemplate;
