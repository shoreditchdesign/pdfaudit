import axios from "axios";
import type { AuditStartResponse, AuditStatusResponse, HealthResponse } from "../types/api";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await api.get<HealthResponse>("/health");
  return response.data;
}

export async function startAudit(payload: {
  urls: string[];
  use_adobe: boolean;
}): Promise<AuditStartResponse> {
  const response = await api.post<AuditStartResponse>("/audit", payload);
  return response.data;
}

export async function fetchAuditStatus(jobId: string): Promise<AuditStatusResponse> {
  const response = await api.get<AuditStatusResponse>(`/audit/${jobId}/status`);
  return response.data;
}

export function getReportUrl(jobId: string): string {
  return `${api.defaults.baseURL}/audit/${jobId}/report`;
}

