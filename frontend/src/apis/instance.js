// instance.js
import axios from "axios";
import { notifyUnauthorized } from "./authSession";

export const BASE_URL =
  process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";
export const instance = axios.create({
  baseURL: BASE_URL,
  timeout: 50000,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

const getCookie = (name) => {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
};

instance.interceptors.request.use((config) => {
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  }
  const csrftoken = getCookie("csrftoken");
  if (csrftoken) {
    config.headers["X-CSRFToken"] = csrftoken;
  }
  return config;
});

export const handleResponseError = (error) => {
  if (error?.response?.status === 401) {
    notifyUnauthorized();
  }
  return Promise.reject(error);
};

instance.interceptors.response.use((response) => response, handleResponseError);
