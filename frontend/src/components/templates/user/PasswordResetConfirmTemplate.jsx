import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import styled from 'styled-components';
import { confirmPasswordReset } from '../../../apis/user';
import { getApiErrorMessage } from '../../../apis/error';
import GlobalLoader from '../../atoms/GlobalLoader';
import { useLoading } from '../../../LoadingContext';
import { useAuth } from '../../../AuthContext';
import { getPasswordConfirmationError, getPasswordError } from './formValidation';

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
  color: ${({ $error }) => ($error ? 'red' : '#555')};
  font-size: 14px;
  margin: 0 0 16px;
`;

const PasswordResetConfirmTemplate = () => {
  const { setIsLoading, isLoading } = useLoading();
  const { clearSession } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const uid = searchParams.get('uid');
  const token = searchParams.get('token');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const hasValidLink = Boolean(uid && token);
  const passwordError = getPasswordError(newPassword);
  const confirmationError = getPasswordConfirmationError(newPassword, confirmPassword);
  const fieldError = (newPassword || confirmPassword) ? passwordError || confirmationError : '';
  const isFormValid = Boolean(newPassword && confirmPassword && !fieldError);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!hasValidLink) {
      setError('유효하지 않은 비밀번호 재설정 링크입니다.');
      return;
    }
    if (!isFormValid) {
      setError(fieldError || '새 비밀번호를 입력해주세요.');
      return;
    }

    setIsLoading(true);
    setError('');
    setMessage('');
    try {
      await confirmPasswordReset(uid, token, newPassword);
      clearSession();
      setMessage('비밀번호가 변경되었습니다. 다시 로그인해주세요.');
      setTimeout(() => navigate('/login'), 1000);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '비밀번호 재설정 링크가 유효하지 않거나 만료되었습니다.'));
    } finally {
      setIsLoading(false);
    }
  };

  if (!hasValidLink) {
    return (
      <Container>
        <Message $error>유효하지 않은 비밀번호 재설정 링크입니다.</Message>
      </Container>
    );
  }

  return (
    <Container>
      <GlobalLoader isLoading={isLoading} />
      <Form onSubmit={handleSubmit}>
        <InputGroup>
          <Label htmlFor="new-password">새 비밀번호</Label>
          <Input
            id="new-password"
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            autoComplete="new-password"
            required
          />
        </InputGroup>
        <InputGroup>
          <Label htmlFor="confirm-password">새 비밀번호 확인</Label>
          <Input
            id="confirm-password"
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            autoComplete="new-password"
            required
          />
        </InputGroup>
        {message && <Message>{message}</Message>}
        {fieldError && <Message $error>{fieldError}</Message>}
        {error && <Message $error>{error}</Message>}
        <Button type="submit" disabled={isLoading || !isFormValid}>
          비밀번호 변경하기
        </Button>
      </Form>
    </Container>
  );
};

export default PasswordResetConfirmTemplate;
