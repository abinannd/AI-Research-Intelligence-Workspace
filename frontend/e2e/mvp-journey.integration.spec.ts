import { randomBytes, randomUUID } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const workspaceName = `Task 07 isolated integration ${randomUUID()}`;
const filename = "project-orion-field-study.pdf";
const question =
  "What exact percent reduction in document processing time did the 2025 Project Orion controlled pilot find?";
const evidenceText =
  "The 2025 controlled pilot found Project Orion reduced document processing time by exactly 37 percent.";
const qdrantCollection = "ari_task07_20261018_2030";
const qdrantUrl = process.env.TASK07_QDRANT_URL ?? "http://127.0.0.1:16333";
const evidenceFile = resolve(".playwright/task07-live-evidence.json");

interface CreatedWorkspace {
  id: string;
}

interface UploadedDocument {
  id: string;
  status: string;
  filename: string;
}

interface AskCitation {
  id: string;
  index: number;
  document_id: string | null;
  filename: string;
  page_number: number;
  quote: string;
}

interface AskResult {
  id: string;
  answer: string;
  abstained: boolean;
  citations: AskCitation[];
}

interface JsonResponse {
  ok(): boolean;
  url(): string;
  status(): number;
  json(): Promise<unknown>;
}

function createSamplePdf(): Buffer {
  const lines = [
    "PROJECT ORION FIELD STUDY",
    evidenceText,
    "Measured against the standard workflow in the controlled pilot.",
  ];
  const content = [
    "BT",
    "/F1 11 Tf",
    "72 730 Td",
    `(${lines[0]}) Tj`,
    "0 -22 Td",
    `(${lines[1]}) Tj`,
    "0 -22 Td",
    `(${lines[2]}) Tj`,
    "ET",
  ].join("\n");
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${Buffer.byteLength(content, "ascii")} >>\nstream\n${content}\nendstream`,
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

function normalizedText(text: string): string {
  return text.toLocaleLowerCase().replace(/\s+/g, " ").trim();
}

async function responseJson<T>(response: JsonResponse): Promise<T> {
  expect(response.ok(), `${response.url()} returned ${response.status()}`).toBeTruthy();
  return (await response.json()) as T;
}

async function capturePost<T>(
  page: Page,
  path: string,
  action: () => Promise<void>,
): Promise<T> {
  const responsePromise = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === path &&
      response.request().method() === "POST",
  );
  await action();
  return responseJson<T>(await responsePromise);
}

test("runs the live authenticated upload-to-citation journey", async ({ page }) => {
  test.setTimeout(20 * 60 * 1000);

  const email = `task07-${randomUUID()}@example.com`;
  const password = `Task07!${randomBytes(18).toString("hex")}`;
  await page.goto("/");

  await page.getByRole("button", { name: "Create an account" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Create workspace" })).toBeVisible();

  const workspace = await capturePost<CreatedWorkspace>(
    page,
    "/api/workspaces",
    async () => {
      await page.getByLabel("Workspace name").fill(workspaceName);
      await page.getByRole("button", { name: "Create workspace" }).click();
    },
  );
  await expect(page.getByRole("heading", { name: "Ask this workspace" })).toBeVisible();

  const uploaded = await capturePost<UploadedDocument>(
    page,
    `/api/workspaces/${workspace.id}/documents`,
    async () => {
      await page.getByLabel("PDF file").setInputFiles({
        name: filename,
        mimeType: "application/pdf",
        buffer: createSamplePdf(),
      });
      await page.getByRole("button", { name: "Upload PDF" }).click();
    },
  );
  expect(uploaded.status).toBe("queued");
  expect(uploaded.filename).toBe(filename);

  await expect(
    page.getByLabel("Processing status: Ready"),
    "the real RQ worker should finish indexing before the test timeout",
  ).toBeVisible({ timeout: 12 * 60 * 1000 });

  const ask = await capturePost<AskResult>(
    page,
    `/api/workspaces/${workspace.id}/ask`,
    async () => {
      await page.getByLabel("Question").fill(question);
      await page.getByRole("button", { name: "Ask", exact: true }).click();
    },
  );
  expect(ask.abstained).toBe(false);
  expect(ask.answer).toMatch(/37/);
  expect(ask.citations.length).toBeGreaterThan(0);

  const citation = ask.citations[0];
  expect(citation.document_id).toBe(uploaded.id);
  expect(citation.filename).toBe(filename);
  expect(citation.page_number).toBe(1);
  expect(normalizedText(citation.quote)).toContain(normalizedText(evidenceText));

  const citationButton = page.getByRole("button", {
    name: `Open ${citation.filename}, page ${citation.page_number}, citation ${citation.index}`,
  });
  await citationButton.click();
  const viewer = page.getByRole("region", { name: `PDF viewer for ${uploaded.id}` });
  await expect(viewer.getByText("PDF page 1 of 1")).toBeVisible({ timeout: 60_000 });
  await expect(viewer.locator(".highlight")).not.toHaveCount(0);

  const highlightedQuote = normalizedText((await viewer.locator(".highlight").allTextContents()).join(" "));
  expect(highlightedQuote).toContain(normalizedText(citation.quote));

  const qdrantResponse = await fetch(
    `${qdrantUrl}/collections/${qdrantCollection}/points/scroll`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filter: {
          must: [
            { key: "workspace_id", match: { value: workspace.id } },
            { key: "document_id", match: { value: uploaded.id } },
          ],
        },
        limit: 10,
        with_payload: true,
        with_vector: false,
      }),
    },
  );
  expect(qdrantResponse.ok).toBeTruthy();
  const qdrantData = (await qdrantResponse.json()) as {
    result: { points: Array<{ payload: { chunk_id?: string; text?: string } }> };
  };
  expect(qdrantData.result.points.length).toBeGreaterThan(0);
  expect(qdrantData.result.points[0].payload.text).toContain(evidenceText);

  await mkdir(resolve(".playwright"), { recursive: true });
  await writeFile(
    evidenceFile,
    JSON.stringify(
      {
        workspaceId: workspace.id,
        documentId: uploaded.id,
        queryId: ask.id,
        citationId: citation.id,
        vectorPointCount: qdrantData.result.points.length,
      },
      null,
      2,
    ),
  );
});
