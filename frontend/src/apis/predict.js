import { instance } from "./client";

export const fetchDetectionSessions = () => {
  return instance.get("/detect/list_detection_sessions/");
};

export const fetchSessionDetails = (sessionId) => {
  return instance.get(`/detect/detection_session_details/${sessionId}/`);
};

export const deleteDetectionSession = (sessionId) => {
  return instance.delete(`/detect/delete_detection_session/${sessionId}/`);
};

export const uploadImage = (file) => {
  const formData = new FormData();
  formData.append("image", file);

  return instance.post("/detect/upload/", formData);
};

export const getSoilCropData = () => {
  return instance.get('/soil/crop_data/');
};

export const getSoilDataDetails = (sessionId) => {
  return instance.get(`/soil/crop_data/${sessionId}/`);
};

export const deleteSoilData = (sessionId) => {
  return instance.delete(`/soil/delete_soil_data/${sessionId}/`);
};

export const getCropNames = () => {
  return instance.get('/soil/get-crop-names/');
};

export const searchSoilAddresses = (query) => {
  return instance.get('/soil/address-search/', { params: { query } });
};

export const getSoilExamData = (cropName, address) => {
  return instance.post('/soil/soil_exam/', { crop_name: cropName, address });
};

export const getSoilFertilizerInfo = (soilPayload) => {
  return instance.post('/soil/get-soil-fertilizer-info/', soilPayload);
};
