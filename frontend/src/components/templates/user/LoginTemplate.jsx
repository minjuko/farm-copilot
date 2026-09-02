import React, { useState } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import styled from 'styled-components';
import { loginUser } from "../../../apis/user";
import CustomModal from "../../atoms/CustomModal";
import { useLoading } from '../../../LoadingContext';
import { useAuth } from '../../../AuthContext';
import { color, radius, shadow, space } from '../../../styles/theme';
import {
  getEmailError,
  getLoginValidation,
  getLoginPasswordError,
  hasValidationErrors,
} from './formValidation';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: ${space("md")};
  background-color: ${color("background")};
  height: 100%;
  width: 100%;
  box-sizing: border-box;
`;

const Title = styled.h1`
  font-size: 24px;
  margin-bottom: 32px;
  color: ${color("text")};
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 600px;
  background-color: ${color("surface")};
  padding: ${space("md")};
  border: 1px solid ${color("border")};
  border-radius: ${radius("md")};
  box-shadow: ${shadow("md")};
`;

const InputGroup = styled.div`
  display: flex;
  flex-direction: column;
  margin-bottom: 24px;
`;

const Label = styled.label`
  font-size: 14px;
  color: ${color("textMuted")};
  margin-bottom: ${space("sm")};
`;

const Input = styled.input`
  font-size: 14px;
  padding: 12px;
  border: 1px solid ${color("border")};
  border-radius: ${radius("sm")};
  &:focus {
    outline: none;
    border-color: ${color("primary")};
  }
`;

const Button = styled.button`
  padding: 12px 16px;
  font-size: 16px;
  font-weight: bold;
  height: 44px; 
  color: ${color("surface")};
  background-color: ${({ disabled, theme }) => (disabled ? theme?.colors?.disabled || '#9e9e9e' : theme?.colors?.primary || '#4aaa87')};
  border: none;
  border-radius: 4px;
  cursor: ${({ disabled }) => (disabled ? 'not-allowed' : 'pointer')};
  &:hover {
    background-color: ${({ disabled, theme }) => (disabled ? theme?.colors?.disabled || '#9e9e9e' : theme?.colors?.primaryFocus || '#6dc4b0')};
  }
`;

const ErrorMessage = styled.div`
  color: red;
  font-size: 12px;
  margin-top: 4px;
`;

const LinksContainer = styled.div`
  margin-top: 16px;
  display: flex;
  justify-content: flex-start; 
  width: 100%;
  max-width: 600px;
`;

const StyledLink = styled(RouterLink)`
  font-size: 16px;
  font-weight: 500;
  margin-right: 16px;
  color: ${color("primary")};
  text-decoration: none;
  &:hover {
    text-decoration: underline;
  }
`;

const LoginTemplate = () => {
  const { setIsLoading, isLoading } = useLoading();
  const { establishSession, refreshAuth } = useAuth();
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [loginError, setLoginError] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState("");
  const [modalTitle, setModalTitle] = useState("");
  const [isError, setIsError] = useState(false);
  const navigate = useNavigate();
  const validation = getLoginValidation(formData);
  const isButtonDisabled = hasValidationErrors(validation);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });

    if (name === "email") setEmailError(getEmailError(value));
    if (name === "password") setPasswordError(getLoginPasswordError(value));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isLoading) return;

    const { email, password } = formData;
    const errors = getLoginValidation(formData);
    if (hasValidationErrors(errors)) {
      setEmailError(errors.email);
      setPasswordError(errors.password);
      return;
    }

    setLoginError("");
    setIsLoading(true);
    loginUser(email, password)
      .then((response) => {
        const { status, message } = response.data;
        if (status === "success") {
          establishSession(response.data);
          refreshAuth({ showChecking: false });
          setModalContent("로그인이 완료되었습니다.");
          setModalTitle("성공");
          setIsError(false);
          setIsModalOpen(true);
          setTimeout(() => {
            setIsModalOpen(false);
            navigate('/');
          }, 2000);
        } else {
          setLoginError(message);
          setModalContent(message);
          setModalTitle("오류");
          setIsError(true);
          setIsModalOpen(true);
        }
      })
      .catch((error) => {
        if (error.response) {
          const { data } = error.response;
          setLoginError(data.message || "로그인 과정에서 오류가 발생했습니다.");
          setModalContent(data.message || "로그인 과정에서 오류가 발생했습니다.");
        } else {
          setLoginError("로그인 과정에서 오류가 발생했습니다.");
          setModalContent("로그인 과정에서 오류가 발생했습니다.");
        }
        setModalTitle("오류");
        setIsError(true);
        setIsModalOpen(true);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  const closeModal = () => {
    setIsModalOpen(false);
  };

  return (
    <Container>
      <Title>로그인</Title>
      <Form onSubmit={handleSubmit}>
        <InputGroup>
          <Label htmlFor="email">이메일</Label>
          <Input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="이메일 입력"
            required
          />
          {emailError && <ErrorMessage>{emailError}</ErrorMessage>}
        </InputGroup>
        <InputGroup>
          <Label htmlFor="password">비밀번호</Label>
          <Input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            placeholder="비밀번호 입력"
            required
          />
          {passwordError && <ErrorMessage>{passwordError}</ErrorMessage>}
        </InputGroup>
        {loginError && <ErrorMessage role="alert">{loginError}</ErrorMessage>}
        <Button type="submit" disabled={isButtonDisabled || isLoading}>
          {isLoading ? "로그인 중..." : "로그인"}
        </Button>
        <LinksContainer>
          <StyledLink to="/signup">회원가입</StyledLink>
          <StyledLink to="/password-reset">비밀번호 찾기</StyledLink>
        </LinksContainer>
      </Form>
      <CustomModal
        isOpen={isModalOpen}
        onRequestClose={closeModal}
        title={modalTitle}
        content={modalContent}
        showConfirmButton={false}
        isError={isError}
      />
    </Container>
  );
};

export default LoginTemplate;
