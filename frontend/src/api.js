const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

const getToken = () => localStorage.getItem("token");

const safeJson = async (response) => {
  try {
    return await response.json();
  } catch (err) {
    return {};
  }
};

const handleResponse = async (response) => {
  const data = await safeJson(response);
  if (response.status === 401) {
    const detail = data?.detail;
    if (detail?.error === "signed_out_elsewhere") {
      localStorage.setItem("signed_out_message", detail.message || "You were signed out.");
    }
    localStorage.removeItem("token");
    window.location.href = "/login";
  }
  if (response.status === 403) {
    window.location.href = "/dashboard";
  }
  if (!response.ok) {
    const message = data?.detail || data?.message || "Request failed";
    throw new Error(message);
  }
  return data;
};

const request = async (method, path, body, options = {}) => {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const token = options.token ?? getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined
  });
  return handleResponse(response);
};

export const api = {
  get: (path, options) => request("GET", path, undefined, options),
  post: (path, body, options) => request("POST", path, body, options),
  put: (path, body, options) => request("PUT", path, body, options),
  del: (path, body, options) => request("DELETE", path, body, options)
};
