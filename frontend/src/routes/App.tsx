import { Download, FileSearch2 } from "lucide-react";
import { ResultsTable } from "@/components/ResultsTable";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useAuditFlow } from "@/hooks/useAuditFlow";
import { getReportUrl } from "@/lib/api";

function badgeVariant(status: string) {
  if (status === "COMPLETED" || status === "ok" || status === "PASS") return "success" as const;
  if (status === "FAILED" || status === "FAIL") return "destructive" as const;
  if (status === "RUNNING" || status === "NEEDS_MANUAL_REVIEW") return "warning" as const;
  return "default" as const;
}

export function App() {
  const {
    health,
    screen,
    useAdobe,
    setUseAdobe,
    inputValue,
    setInputValue,
    urls,
    validUrls,
    canSubmit,
    jobId,
    status,
    submitting,
    error,
    runAudit,
    runAgain,
  } = useAuditFlow();

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 p-4 md:p-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div className="space-y-2">
              <CardTitle>HSBC PDF accessibility audit</CardTitle>
              <CardDescription>
                Paste public PDF URLs, run the audit pipeline, and export the workbook output.
              </CardDescription>
            </div>
            <div className="flex flex-col gap-2 md:items-end">
              <Badge variant={badgeVariant(health?.status ?? "Loading")}>
                API: {health?.status ?? "Loading"}
              </Badge>
              <Badge variant={health?.adobe.configured ? "success" : "warning"}>
                Adobe: {health?.adobe.configured ? "Configured" : "Unavailable"}
              </Badge>
            </div>
          </div>
        </CardHeader>
      </Card>

      {error ? (
        <Alert className="border-destructive/30 text-destructive">
          <AlertTitle>Audit issue</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{screen === "results" ? "Results" : screen === "progress" ? "Progress" : "New audit"}</CardTitle>
          <CardDescription>
            {screen === "input"
              ? "Use one URL per line. The audit starts as soon as the batch is submitted."
              : screen === "progress"
                ? `Tracking job ${jobId}`
                : "Review the completed run and download the generated report."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {screen === "input" ? (
            <>
              <div className="flex items-center justify-between gap-4 rounded-md border p-4">
                <div className="space-y-1">
                  <Label htmlFor="adobe-switch">Adobe API checks</Label>
                  <p className="text-sm text-muted-foreground">
                    Enable Adobe checks when credentials are configured.
                  </p>
                </div>
                <Switch
                  checked={useAdobe}
                  onCheckedChange={setUseAdobe}
                  disabled={!health?.adobe.configured}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="url-list">PDF URLs</Label>
                <Textarea
                  id="url-list"
                  aria-label="Paste PDF URLs"
                  value={inputValue}
                  onChange={(event) => setInputValue(event.target.value)}
                  rows={14}
                />
                <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                  <span>Total: {urls.length}</span>
                  <span>Valid: {validUrls.length}</span>
                  <span>Max batch: 100</span>
                </div>
              </div>

              <Separator />

              <Button onClick={() => void runAudit()} disabled={!canSubmit || submitting} className="gap-2">
                <FileSearch2 className="h-4 w-4" />
                {submitting ? "Starting audit..." : "Run audit"}
              </Button>
            </>
          ) : null}

          {screen !== "input" && status ? (
            <>
              <div className="grid gap-4 md:grid-cols-4">
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">Stage</p>
                    <p className="mt-2 text-2xl font-semibold">{status.stage}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">Completed</p>
                    <p className="mt-2 text-2xl font-semibold">{status.counts.completed}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">Failed</p>
                    <p className="mt-2 text-2xl font-semibold">{status.counts.failed}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">Queued</p>
                    <p className="mt-2 text-2xl font-semibold">{status.counts.queued}</p>
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-2">
                <Progress value={status.counts.completed + status.counts.failed} max={status.counts.total} />
                <p className="text-sm text-muted-foreground">
                  {status.counts.completed + status.counts.failed} of {status.counts.total} processed
                </p>
              </div>

              <ResultsTable rows={status.documents} />

              {screen === "results" ? (
                <div className="flex flex-col gap-3 md:flex-row">
                  <a
                    href={jobId ? getReportUrl(jobId) : "#"}
                    className={buttonVariants({ variant: "default" })}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    Download report
                  </a>
                  <Button variant="outline" onClick={runAgain}>
                    Start another audit
                  </Button>
                </div>
              ) : null}
            </>
          ) : null}
        </CardContent>
      </Card>
    </main>
  );
}
