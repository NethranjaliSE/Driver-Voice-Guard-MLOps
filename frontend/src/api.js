// Dev server (VITE_API_URL set in frontend/.env.local) talks to a separate
// backend on :8000. A production build with no VITE_API_URL set (e.g. the
// combined Docker image served by the same FastAPI process) uses relative
// paths instead, since frontend and API share an origin there.
const API_BASE =
  import.meta.env.VITE_API_URL || (import.meta.env.PROD ? "" : "http://localhost:8000");

async function handleResponse(res) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function analyzeVoice(fileOrBlob) {
  const form = new FormData();
  form.append("file", fileOrBlob, fileOrBlob.name || "recording.webm");
  const res = await fetch(`${API_BASE}/analyze/voice`, {
    method: "POST",
    body: form,
  });
  return handleResponse(res);
}

export async function startSession() {
  const res = await fetch(`${API_BASE}/session/start`);
  return handleResponse(res);
}

export async function sendChunk(sessionId, blob) {
  const form = new FormData();
  form.append("file", blob, "chunk.webm");
  const res = await fetch(`${API_BASE}/session/${sessionId}/chunk`, {
    method: "POST",
    body: form,
  });
  return handleResponse(res);
}

export async function getSessionReport(sessionId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/report`);
  return handleResponse(res);
}

export async function downloadReportPdf(sessionId) {
  const res = await fetch(`${API_BASE}/report/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `driver_safety_report_${sessionId.slice(0, 8)}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return handleResponse(res);
}

export async function fetchModelInfo() {
  const res = await fetch(`${API_BASE}/model/info`);
  return handleResponse(res);
}
