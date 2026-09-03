import React, { useCallback, useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import styled from "styled-components";
import { useDropzone } from "react-dropzone";
import { uploadImage } from "../../../apis/predict";
import {
  getDetectionErrorMessage,
  normalizeDetectionResult,
  validateDetectionFile,
} from "./detectFlow";
import { FaCamera, FaFile } from "react-icons/fa";
import CustomModal from '../../atoms/CustomModal';
import GlobalLoader from '../../atoms/GlobalLoader';
import { useLoading } from "../../../LoadingContext";
import useServiceCapability from "../../../hooks/useServiceCapability";
import { color, shadow } from "../../../styles/theme";

const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.5rem;

  @media (min-width: 768px) {
    padding: 3rem; 
  }
`;

const Content = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 38rem; 
  position: relative;

  @media (min-width: 768px) {
    max-width: 48rem; 
  }
`;

const UploadText = styled.p`
  font-size: 1rem;
  color: ${color("text")};

  @media (min-width: 768px) {
    font-size: 1.25rem; 
  }
`;

const ButtonWrapper = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  max-width: 18rem;
  margin-top: 1rem;

  @media (min-width: 768px) {
    max-width: 22rem;
    margin-top: 1.5rem; 
  }
`;

const UploadButton = styled.div`
  display: flex;
  align-items: center;
  background-color: white;
  border: 1px solid ${color("primary")};
  border-radius: 5px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  gap: 0.5rem;
  flex: 1;
  justify-content: center;
  margin: 0 0.25rem;

  transition: background-color 0.3s, border-color 0.3s;

  &:hover {
    background-color: ${color("primarySoft")};
    border-color: ${color("primaryHover")};
  }

  @media (min-width: 768px) {
    padding: 0.75rem 1.5rem; 
  }
`;

const CameraButton = styled.div`
  display: flex;
  align-items: center;
  background-color: white;
  border: 1px solid ${color("primary")};
  border-radius: 5px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  gap: 0.5rem;
  flex: 1;
  justify-content: center;
  margin: 0 0.25rem;

  transition: background-color 0.3s, border-color 0.3s;

  &:hover {
    background-color: ${color("primarySoft")};
    border-color: ${color("primaryHover")};
  }

  @media (min-width: 768px) {
    padding: 0.75rem 1.5rem; 
  }
`;

const UploadContainer = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border: 1px solid ${color("primary")};
  width: 18rem;
  max-width: 33rem;
  height: 18rem;
  text-align: center;
  margin-bottom: 1.25rem;
  margin-top: 1.25rem;
  background-color: ${color("surface")};
  border-radius: 0.625rem;
  overflow: hidden;
  cursor: pointer;

  @media (min-width: 768px) {
    width: 22rem; 
    height: 22rem; 
  }
`;

const ImagePreview = styled.img`
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 0.625rem;
`;

const PlaceholderIcon = styled.div`
  font-size: 3rem;
  color: ${color("disabled")};

  @media (min-width: 768px) {
    font-size: 4rem; 
  }
`;

const PlaceholderText = styled.p`
  font-size: 1rem;
  color: ${color("textMuted")};

  @media (min-width: 768px) {
    font-size: 1.25rem; 
  }
`;

const ButtonContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1.5rem;
  max-width: 30rem;
  margin-top: 0.5rem;

  @media (min-width: 768px) {
    gap: 2rem;
    margin-top: 1rem;
  }
`;

const DiagnoseButton = styled.button`
  background-color: ${color("primary")};
  color: white;
  padding: 0.75rem 2.5rem;
  border: none;
  border-radius: 0.3rem;
  cursor: pointer;
  font-size: 1.2rem;
  font-weight: 600;
  box-shadow: ${shadow("sm")};
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;

  transition: background-color 0.3s;

  &:hover {
    background-color: ${color("primaryHover")};
  }

  @media (min-width: 768px) {
    padding: 1rem 3rem;
    font-size: 1.4rem; 
  }
`;

const ExplanationText = styled.p`
  font-size: 0.8rem;
  color: ${color("textMuted")};
  text-align: center;
`;

const DiagnosisTemplate = () => {
  const { setIsLoading, isLoading } = useLoading();
  const [image, setImage] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState("");
  const navigate = useNavigate();
  const cameraInputRef = useRef(null);
  const fileInputRef = useRef(null);
  const uploadInFlight = useRef(false);
  const serviceCapability = useServiceCapability("detection");

  const selectFile = useCallback((file) => {
    const validationError = validateDetectionFile(file);
    if (validationError) {
      setImage(null);
      setSelectedFile(null);
      setModalContent(validationError);
      setIsModalOpen(true);
      return;
    }
    setImage(URL.createObjectURL(file));
    setSelectedFile(file);
  }, []);

  useEffect(() => () => {
    if (image) URL.revokeObjectURL(image);
  }, [image]);

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    selectFile(file);
  }, [selectFile]);

  const { getRootProps, getInputProps } = useDropzone({
    onDrop,
    onDropRejected: () => {
      setImage(null);
      setSelectedFile(null);
      setModalContent("JPEG, PNG, WebP 이미지 파일만 선택할 수 있습니다.");
      setIsModalOpen(true);
    },
    accept: {
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "image/webp": [".webp"],
    },
    multiple: false,
    noClick: true,
  });

  const handleDiagnose = async () => {
    if (!serviceCapability.available) {
      setModalContent("LIMITED · 진단 모델이 준비된 환경에서만 실행할 수 있습니다.");
      setIsModalOpen(true);
      return;
    }
    const validationError = validateDetectionFile(selectedFile);
    if (validationError) {
      setModalContent(validationError);
      setIsModalOpen(true);
      return;
    }
    if (uploadInFlight.current) return;

    try {
      uploadInFlight.current = true;
      setIsLoading(true);
      const response = await uploadImage(selectedFile);
      const diagnosisResult = normalizeDetectionResult(response?.data);
      if (!diagnosisResult) {
        throw new Error("MALFORMED_DETECTION_RESPONSE");
      }
      const resultPath = diagnosisResult.session_id
        ? `/info/${diagnosisResult.session_id}`
        : '/info';
      navigate(resultPath, { state: { diagnosisResult } });
    } catch (error) {
      setModalContent(getDetectionErrorMessage(error));
      setIsModalOpen(true);
    } finally {
      uploadInFlight.current = false;
      setIsLoading(false);
    }
  };

  const handleOpenCamera = () => {
    if (cameraInputRef.current) {
      cameraInputRef.current.click();
    }
  };

  const handleOpenFileDialog = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleCameraInputChange = (event) => {
    const file = event.target.files[0];
    selectFile(file);
    event.target.value = "";
  };

  const handleFileInputChange = (event) => {
    const file = event.target.files[0];
    selectFile(file);
    event.target.value = "";
  };

  return (
    <PageContainer>
      {isLoading && <GlobalLoader text="AI 진단 중입니다." />}
      <Content>
        <UploadText>병해충 진단을 위한 사진을 업로드해주세요</UploadText>
        <ExplanationText>
          &#60;탐지 가능 병해충 목록&#62;<br/>
          고추: 탄저병, 흰가루병<br/>
          오이: 노균병, 흰가루병<br/>
          토마토: 잿빛곰팡이병, 흰가루병
        </ExplanationText>
        <ButtonWrapper>
          <UploadButton onClick={handleOpenFileDialog}>
            <FaFile />
            파일 업로드
          </UploadButton>
          <CameraButton onClick={handleOpenCamera}>
            <FaCamera />
            촬영
          </CameraButton>
        </ButtonWrapper>
        <UploadContainer {...getRootProps()}>
          <input {...getInputProps()} ref={fileInputRef} onChange={handleFileInputChange} />
          {image ? (
            <ImagePreview src={image} alt="Uploaded" />
          ) : (
            <>
              <PlaceholderIcon>
                <FaFile />
              </PlaceholderIcon>
              <PlaceholderText>업로드한 사진이 여기에 표시됩니다</PlaceholderText>
            </>
          )}
        </UploadContainer>
        <ButtonContainer>
          <DiagnoseButton
            onClick={handleDiagnose}
            disabled={isLoading || !serviceCapability.available}
          >
            <FaFile />
            진단하기
          </DiagnoseButton>
        </ButtonContainer>
        <input
          type="file"
          aria-label="카메라 이미지 선택"
          accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
          capture="camera"
          ref={cameraInputRef}
          style={{ display: 'none' }}
          onChange={handleCameraInputChange}
        />
      </Content>
      <CustomModal
        isOpen={isModalOpen}
        onRequestClose={() => setIsModalOpen(false)}
        title="알림"
        content={modalContent}
        showConfirmButton={false}
      />
    </PageContainer>
  );
};

export default DiagnosisTemplate;
