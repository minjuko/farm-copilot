export const getApiErrorMessage = (error, fallbackMessage) => {
  const responseData = error?.response?.data;

  if (typeof responseData === "string" && responseData.trim()) {
    return responseData;
  }

  return responseData?.message || responseData?.error || fallbackMessage;
};

export const getServiceErrorMessage = (error, fallbackMessage) => {
  if (error?.response?.status >= 500) return fallbackMessage;
  return getApiErrorMessage(error, fallbackMessage);
};
