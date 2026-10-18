import { expect, test, type Page, type Route } from "@playwright/test";

const workspaceId = "workspace-browser-test";
const firstDocumentId = "document-first";
const secondDocumentId = "document-second";
const firstQuote = "The cited finding is verified.";
const secondQuote = "A separate source confirms the result.";
const accessToken = "browser-test-token";

type CitationFixture = {
  id: string;
  index: number;
  document_id: string;
  filename: string;
  page_number: number;
  quote: string;
};

function samplePdf(text: string, textPage = 2): Buffer {
  const firstPageText = textPage === 1 ? text : "First page content";
  const secondPageText = textPage === 2 ? text : "Second page content";
  const firstPageContent = `BT\n/F1 18 Tf\n72 720 Td\n(${firstPageText}) Tj\nET`;
  const secondPageContent = `BT\n/F1 18 Tf\n72 720 Td\n(${secondPageText}) Tj\nET`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${Buffer.byteLength(firstPageContent, "ascii")} >>\nstream\n${firstPageContent}\nendstream`,
    `<< /Length ${Buffer.byteLength(secondPageContent, "ascii")} >>\nstream\n${secondPageContent}\nendstream`,
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];

  objects.forEach((object, index) => {
    offsets.push(Buffer.byteLength(pdf, "ascii"));
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });

  const xrefOffset = Buffer.byteLength(pdf, "ascii");
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets.slice(1)) {
    pdf += `${offset.toString().padStart(10, "0")} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;
  return Buffer.from(pdf, "ascii");
}

function citation(
  id: string,
  index: number,
  documentId: string,
  filename: string,
  quote: string,
): CitationFixture {
  return {
    id,
    index,
    document_id: documentId,
    filename,
    page_number: documentId === firstDocumentId ? 2 : 1,
    quote,
  };
}

const citations = [
  citation("citation-first", 1, firstDocumentId, "first.pdf", firstQuote),
  citation("citation-second", 2, secondDocumentId, "second.pdf", secondQuote),
];

async function preparePage(page: Page, answerCitations = citations) {
  await page.addInitScript(
    ({ token, selectedWorkspace }) => {
      window.localStorage.setItem("ari_access_token", token);
      window.localStorage.setItem("ari_selected_workspace_id", selectedWorkspace);
    },
    { token: accessToken, selectedWorkspace: workspaceId },
  );

  await page.route("**/api/**", async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (path === "/api/auth/me") {
      await route.fulfill({ json: { id: "user-browser-test", email: "browser@example.test" } });
    } else if (path === "/api/workspaces") {
      await route.fulfill({
        json: [{ id: workspaceId, name: "Browser Test Workspace", created_at: "2025-01-01T00:00:00Z" }],
      });
    } else if (path === `/api/workspaces/${workspaceId}/documents`) {
      await route.fulfill({
        json: [{
          id: firstDocumentId,
          filename: "first.pdf",
          status: "ready",
          page_count: 2,
          error_message: null,
          created_at: "2025-01-01T00:00:00Z",
        }],
      });
    } else if (path === `/api/workspaces/${workspaceId}/ask`) {
      await route.fulfill({
        json: {
          id: "answer-browser-test",
          question: "What does the source say?",
          abstained: false,
          abstain_reason: null,
          answer: "The sources support the result.",
          claims: [],
          citations: answerCitations,
          latency_ms: 12,
          model_version: "test",
          prompt_version: "test",
          retrieval_version: "test",
        },
      });
    } else {
      await route.fulfill({ status: 501, body: `Unexpected browser-test API request: ${path}` });
    }
  });

  await page.goto("/");
  await expect(page.getByRole("button", { name: /Browser Test Workspace/ })).toBeVisible();
  await expect(page.getByText("Ask this workspace")).toBeVisible();
  await page.getByLabel("Question").fill("What does the source say?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Answer" })).toBeVisible();
}

function documentFilePath(documentId: string) {
  return `/api/workspaces/${workspaceId}/documents/${documentId}/file`;
}

async function fulfillPdf(route: Route, text: string, textPage = 2) {
  await route.fulfill({
    status: 200,
    contentType: "application/pdf",
    body: samplePdf(text, textPage),
  });
}

test("opens the authenticated workspace PDF at its cited page and highlights the quote", async ({ page }) => {
  const fileRequests: Array<{ path: string; authorization: string | undefined }> = [];
  await preparePage(page);
  await page.route("**/api/workspaces/*/documents/*/file", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    fileRequests.push({ path, authorization: request.headers().authorization });
    await fulfillPdf(route, firstQuote);
  });

  await page.getByRole("button", { name: "Open first.pdf, page 2, citation 1" }).click();
  const viewer = page.getByRole("region", { name: `PDF viewer for ${firstDocumentId}` });
  await expect(viewer.getByText("PDF page 2 of 2")).toBeVisible();
  await expect(viewer.locator(".highlight")).toContainText(firstQuote);
  expect(fileRequests).toEqual([{
    path: documentFilePath(firstDocumentId),
    authorization: `Bearer ${accessToken}`,
  }]);
});

test("a late response for an earlier citation cannot replace the newly selected PDF", async ({ page }) => {
  let releaseFirstResponse!: () => void;
  let markFirstResponseSent!: () => void;
  const firstResponseGate = new Promise<void>((resolve) => {
    releaseFirstResponse = resolve;
  });
  const firstResponseSent = new Promise<void>((resolve) => {
    markFirstResponseSent = resolve;
  });
  await preparePage(page);
  await page.route("**/api/workspaces/*/documents/*/file", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === documentFilePath(firstDocumentId)) {
      await firstResponseGate;
      await fulfillPdf(route, firstQuote);
      markFirstResponseSent();
    } else if (path === documentFilePath(secondDocumentId)) {
      await fulfillPdf(route, secondQuote, 1);
    } else {
      await route.fulfill({ status: 404 });
    }
  });

  await page.getByRole("button", { name: "Open first.pdf, page 2, citation 1" }).click();
  await expect(page.getByText("Loading cited PDF…")).toBeVisible();
  await page.getByRole("button", { name: "Open second.pdf, page 1, citation 2" }).click();
  const secondViewer = page.getByRole("region", { name: `PDF viewer for ${secondDocumentId}` });
  await expect(secondViewer.getByText("PDF page 1 of 2")).toBeVisible();
  await expect(secondViewer.locator(".highlight")).toContainText(secondQuote);

  releaseFirstResponse();
  await firstResponseSent;
  await expect(page.getByRole("region", { name: `PDF viewer for ${secondDocumentId}` })).toBeVisible();
  await expect(page.getByRole("region", { name: `PDF viewer for ${firstDocumentId}` })).toHaveCount(0);
  await expect(secondViewer.locator(".highlight")).toContainText(secondQuote);
});

test("shows a useful error when the cited PDF is unavailable", async ({ page }) => {
  await preparePage(page, [citations[0]]);
  await page.route("**/api/workspaces/*/documents/*/file", async (route) => {
    await route.fulfill({ status: 404, json: { detail: "Not found" } });
  });

  await page.getByRole("button", { name: "Open first.pdf, page 2, citation 1" }).click();
  await expect(page.locator('p[role="alert"]')).toHaveText(
    "The cited PDF is no longer available in this workspace.",
  );
});
