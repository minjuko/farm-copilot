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
import { fetchCapabilities, normalizeCapability } from "../../../apis/capabilities";

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
  color: #333;

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
  border: 1px solid #4aaa87;
  border-radius: 5px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  gap: 0.5rem;
  flex: 1;
  justify-content: center;
  margin: 0 0.25rem;

  transition: background-color 0.3s, border-color 0.3s;

  &:hover {
    background-color: #e8f5e9;
    border-color: #388e3c;
  }

  @media (min-width: 768px) {
    padding: 0.75rem 1.5rem; 
  }
`;

const CameraButton = styled.div`
  display: flex;
  align-items: center;
  background-color: white;
  border: 1px solid #4aaa87;
  border-radius: 5px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  gap: 0.5rem;
  flex: 1;
  justify-content: center;
  margin: 0 0.25rem;

  transition: background-color 0.3s, border-color 0.3s;

  &:hover {
    background-color: #e8f5e9;
    border-color: #388e3c;
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
  border: 1px solid #4aaa87;
  width: 18rem;
  max-width: 33rem;
  height: 18rem;
  text-align: center;
  margin-bottom: 1.25rem;
  margin-top: 1.25rem;
  background-color: #fff;
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
  color: #ccc;

  @media (min-width: 768px) {
    font-size: 4rem; 
  }
`;

const PlaceholderText = styled.p`
  font-size: 1rem;
  color: #aaa;

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
  background-color: #4aaa87;
  color: white;
  padding: 0.75rem 2.5rem;
  border: none;
  border-radius: 0.3rem;
  cursor: pointer;
  font-size: 1.2rem;
  font-weight: 600;
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;

  transition: background-color 0.3s;

  &:hover {
    background-color: #3b8b6d;
  }

  @media (min-width: 768px) {
    padding: 1rem 3rem;
    font-size: 1.4rem; 
  }
`;

const ExplanationText = styled.p`
  font-size: 0.8rem;
  color: #666;
  text-align: center;
`;

const ServiceNotice = styled.div`
  width: 100%;
  box-sizing: border-box;
  margin-bottom: 1rem;
  padding: 0.75rem;
  text-align: center;
  border-radius: 6px;
  color: ${({ $available }) => ($available ? "#1f6b4f" : "#5d4a00")};
  background: ${({ $available }) => ($available ? "#e8f5e9" : "#fff8e1")};
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
  const [serviceCapability, setServiceCapability] = useState({
    status: "checking", available: false,
  });

  useEffect(() => {
    let active = true;
    fetchCapabilities()
      .then((response) => {
        if (active) {
          setServiceCapability(normalizeCapability(response?.data, "detection"));
        }
      })
      .catch(() => {
        if (active) setServiceCapability({ status: "limited", available: false });
      });
    return () => { active = false; };
  }, []);

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
      navigate('/info', { state: { diagnosisResult } });
    } catch (error) {
      setModalContent(getDetectionErrorMessage(error));
      setIsModalOpen(true);
    } finally {
      uploadInFlight.current = false;
      setIsLoading(false);
    }
  };

  const openCamera = () => {
    if (cameraInputRef.current) {
      cameraInputRef.current.click();
    }
  };

  const openFileDialog = () => {
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
        <ServiceNotice role="status" $available={serviceCapability.available}>
          {serviceCapability.available
            ? "AVAILABLE · 병해충 진단 모델이 준비되어 있습니다."
            : "LIMITED · 진단 모델이 준비된 환경에서만 실행할 수 있습니다."}
        </ServiceNotice>
        <UploadText>병해충 진단을 위한 사진을 업로드해주세요</UploadText>
        <ExplanationText>
          &#60;탐지 가능 병해충 목록&#62;<br/>
          고추: 탄저병, 흰가루병<br/>
          오이: 노균병, 흰가루병<br/>
          토마토: 잿빛곰팡이병, 흰가루병
        </ExplanationText>
        <ButtonWrapper>
          <UploadButton onClick={openFileDialog}>
            <FaFile />
            파일 업로드
          </UploadButton>
          <CameraButton onClick={openCamera}>
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
