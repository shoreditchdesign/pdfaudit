import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { App } from "../routes/App";

vi.mock("../lib/api", () => ({
  fetchHealth: vi.fn(async () => ({
    status: "ok",
    adobe: {
      configured: false,
      enabled: false,
      message: "Adobe credentials missing.",
    },
  })),
  startAudit: vi.fn(),
  fetchAuditStatus: vi.fn(),
  getReportUrl: vi.fn(() => "#"),
}));

describe("App", () => {
  it("renders the input view", async () => {
    render(<App />);
    expect(await screen.findByText("HSBC PDF accessibility audit")).toBeInTheDocument();
    expect(screen.getByLabelText("Paste PDF URLs")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run audit" })).toBeEnabled();
  });
});
