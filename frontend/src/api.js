// frontend/src/api.js
const BASE_URL = "http://localhost:8000";

export async function checkStatus() {
  const res = await fetch(`${BASE_URL}/api/status`);
  const data = await res.json();
  return data;
}