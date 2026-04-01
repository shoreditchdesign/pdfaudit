import { useEffect, useRef, useState } from "react";
import { fetchAuditStatus, fetchHealth, startAudit } from "../lib/api";
import { sampleUrls } from "../lib/sample";
import type { AuditStatusResponse, HealthResponse } from "../types/api";

export type Screen = "input" | "progress" | "results";

export function useAuditFlow() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [screen, setScreen] = useState<Screen>("input");
  const [useAdobe, setUseAdobe] = useState(true);
  const [inputValue, setInputValue] = useState(sampleUrls.join("\n"));
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<AuditStatusResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<number | null>(null);

  const urls = inputValue
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const validUrls = urls.filter((url) => /^https?:\/\//.test(url));

  useEffect(() => {
    void fetchHealth()
      .then((response) => {
        setHealth(response);
        if (!response.adobe.configured) {
          setUseAdobe(false);
        }
      })
      .catch(() => {
        setError("Could not reach the backend health endpoint.");
      });
  }, []);

  useEffect(() => {
    if (!jobId || screen !== "progress") {
      return;
    }

    const poll = async () => {
      try {
        const next = await fetchAuditStatus(jobId);
        setStatus(next);
        if (next.error) {
          setError(next.error);
        }
        if (next.stage === "COMPLETED" || next.stage === "FAILED" || next.stage === "CANCELLED") {
          setScreen("results");
          if (intervalRef.current) {
            window.clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        }
      } catch {
        setError("Could not fetch audit status.");
      }
    };

    void poll();
    intervalRef.current = window.setInterval(() => {
      void poll();
    }, 1500);

    return () => {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [jobId, screen]);

  async function runAudit() {
    setSubmitting(true);
    setError(null);
    try {
      const response = await startAudit({ urls: validUrls, use_adobe: useAdobe });
      setJobId(response.job_id);
      setStatus({
        job_id: response.job_id,
        stage: "QUEUED",
        use_adobe: useAdobe,
        cancelled: false,
        report_ready: false,
        counts: {
          total: validUrls.length,
          queued: validUrls.length,
          running: 0,
          completed: 0,
          failed: 0,
          cancelled: 0,
        },
        documents: validUrls.map((url) => ({
          url,
          stage: "QUEUED",
          result: null,
          message: "Queued for processing",
        })),
        summary: null,
        error: null,
      });
      setScreen("progress");
    } catch {
      setError("Could not start the audit. Check that the backend is running and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function runAgain() {
    setJobId(null);
    setStatus(null);
    setError(null);
    setScreen("input");
  }

  return {
    health,
    screen,
    useAdobe,
    setUseAdobe,
    inputValue,
    setInputValue,
    urls,
    validUrls,
    canSubmit: validUrls.length > 0 && validUrls.length === urls.length && urls.length <= 100,
    jobId,
    status,
    submitting,
    error,
    runAudit,
    runAgain,
  };
}
