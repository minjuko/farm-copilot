import React, { useState } from 'react';
import styled from 'styled-components';
import { requestPasswordReset } from '../../../apis/user';
import { getApiErrorMessage } from '../../../apis/error';
import GlobalLoader from '../../atoms/GlobalLoader';
import { useLoading } from '../../../LoadingContext';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px;
  margin-top: 20px;
  height: 100%;
  width: 100%;
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 600px;
  background-color: white;
  padding: 24px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
`;

const InputGroup = styled.div`
  display: flex;
  flex-direction: column;
  margin-bottom: 20px;
`;

const Label = styled.label`
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
`;

const Input = styled.input`
  font-size: 14px;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
`;

const Button = styled.button`
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 600;
  height: 44px;
  color: white;
  background-color: #4aaa87;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  &:disabled {
    background-color: #9e9e9e;
    cursor: not-allowed;
  }
`;

const Message = styled.p`
  color: ${({ $error }) => ($error ? 'red' : 'green')};
  font-size: 14px;
  margin: 0 0 16px;
`;

const validateEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

const PasswordResetTemplate = () => {
  const { setIsLoading, isLoading } = useLoading();
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!validateEmail(email)) {
      setError('유효한 이메일 주소를 입력해주세요.');
      setMessage('');
      return;
    }

    setIsLoading(true);
    setError('');
    setMessage('');
    try {
      await requestPasswordReset(email);
      setMessage('계정이 존재하면 비밀번호 재설정 링크가 이메일로 발송됩니다.');
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '비밀번호 재설정 요청에 실패했습니다.'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container>
      <GlobalLoader isLoading={isLoading} />
      <Form onSubmit={handleSubmit}>
        <InputGroup>
          <Label htmlFor="reset-email">이메일</Label>
          <Input
            type="email"
            id="reset-email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="이메일을 입력하세요"
            autoComplete="email"
            required
          />
        </InputGroup>
        {message && <Message>{message}</Message>}
        {error && <Message $error>{error}</Message>}
        <Button type="submit" disabled={isLoading || !email}>
          재설정 링크 보내기
        </Button>
      </Form>
    </Container>
  );
};

export default PasswordResetTemplate;
