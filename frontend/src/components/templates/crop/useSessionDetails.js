import { useCallback, useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { getSessionDetails } from "../../../apis/crop";
import { getServiceErrorMessage } from "../../../apis/error";
import { normalizePredictionResult } from "./predictionFlow";
import { useLoading } from "../../../LoadingContext";

export default function useSessionDetails(sessionId) {
  const location = useLocation();
  const navigate = useNavigate();
  const { setIsLoading, isLoading } = useLoading();
  const [sessionDetails, setSessionDetails] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isFetching, setIsFetching] = useState(true);

  const load = useCallback(async () => {
    const resolvedSessionId = sessionId || location.state?.session_id;
    if (!resolvedSessionId) {
      setErrorMessage("세션 ID가 없습니다. 목록에서 다시 선택해주세요.");
      setIsFetching(false);
      return;
    }
    try {
      setIsLoading(true);
      const response = await getSessionDetails(resolvedSessionId);
      const normalizedDetails = normalizePredictionResult(response.data);
      if (normalizedDetails.results.length === 0) {
        setErrorMessage("표시할 예측 결과가 없습니다.");
        return;
      }
      setSessionDetails(normalizedDetails);
    } catch (error) {
      if (error.response?.status === 401) navigate("/login");
      else setErrorMessage(getServiceErrorMessage(error, "세션 상세 정보를 불러오지 못했습니다."));
    } finally {
      setIsLoading(false);
      setIsFetching(false);
    }
  }, [location.state, navigate, sessionId, setIsLoading]);

  useEffect(() => { load(); }, [load]);

  return { sessionDetails, errorMessage, isFetching, isLoading };
}
