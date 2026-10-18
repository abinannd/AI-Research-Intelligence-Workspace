"use client";

import { useEffect, useRef, useState } from "react";
import type { PDFDocumentLoadingTask, PDFDocumentProxy, PDFPageProxy, RenderTask, TextLayer } from "pdfjs-dist";

import { findMatchingTextDivIndexes } from "@/lib/citationNavigation";
import styles from "@/components/WorkspacePdfViewer.module.css";

interface WorkspacePdfViewerProps {
  documentId: string | null;
  pdfBlob: Blob | null;
  targetPage: number | null;
  highlightQuote: string | null;
  onPageChange?: (page: number) => void;
  onError?: (error: Error) => void;
}

function asError(error: unknown): Error {
  return error instanceof Error ? error : new Error("Could not display this PDF.");
}

export default function WorkspacePdfViewer({
  documentId,
  pdfBlob,
  targetPage,
  highlightQuote,
  onPageChange,
  onError,
}: WorkspacePdfViewerProps) {
  const pageContainerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [pdfDocument, setPdfDocument] = useState<PDFDocumentProxy | null>(null);
  const [pageCount, setPageCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageOverride, setPageOverride] = useState<{ targetPage: number | null; page: number } | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [renderResult, setRenderResult] = useState<{
    page: number;
    error?: string;
    quoteFound?: boolean | null;
  } | null>(null);
  const displayPage =
    pageOverride?.targetPage === targetPage ? pageOverride.page : targetPage ?? 1;
  const pageResult = renderResult?.page === displayPage ? renderResult : null;
  const loading = Boolean(pdfBlob) && !pdfError && (!pdfDocument || !pageResult);
  const error = pdfError ?? pageResult?.error ?? (!pdfBlob ? "PDF data is not available." : null);

  useEffect(() => {
    const blob = pdfBlob;
    if (!blob) return;

    let active = true;
    let loadingTask: PDFDocumentLoadingTask | null = null;

    async function loadPdf(source: Blob) {
      try {
        const pdfjs = await import("pdfjs-dist");
        pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
        loadingTask = pdfjs.getDocument({
          data: new Uint8Array(await source.arrayBuffer()),
        });
        const loadedDocument = await loadingTask.promise;
        if (active) {
          setPdfDocument(loadedDocument);
          setPageCount(loadedDocument.numPages);
        }
      } catch (loadError) {
        if (active) {
          const parsedError = asError(loadError);
          setPdfError(parsedError.message);
          onError?.(parsedError);
        }
      }
    }

    void loadPdf(blob);
    return () => {
      active = false;
      if (loadingTask) void loadingTask.destroy();
    };
  }, [documentId, onError, pdfBlob]);

  useEffect(() => {
    const currentDocument = pdfDocument;
    const canvasElement = canvasRef.current;
    const containerElement = pageContainerRef.current;
    if (!currentDocument || !canvasElement || !containerElement || !displayPage) return;

    let active = true;
    let renderTask: RenderTask | null = null;
    let textLayer: TextLayer | null = null;
    const canvas = canvasElement;
    const container = containerElement;
    const textLayerContainer = container.querySelector<HTMLDivElement>("[data-pdf-text-layer]");
    if (!textLayerContainer) return;
    textLayerContainer.replaceChildren();
    async function renderPage(
      document: PDFDocumentProxy,
      textLayerElement: HTMLDivElement,
    ) {
      try {
        if (displayPage < 1 || displayPage > document.numPages) {
          throw new Error(`Page ${displayPage} is not available in this PDF.`);
        }
        const page: PDFPageProxy = await document.getPage(displayPage);
        if (!active) return;

        const baseViewport = page.getViewport({ scale: 1 });
        const availableWidth = Math.max(1, container.clientWidth || 720);
        const scale = Math.min(1.25, availableWidth / baseViewport.width);
        const viewport = page.getViewport({ scale });
        const outputScale = window.devicePixelRatio || 1;
        canvas.width = Math.floor(viewport.width * outputScale);
        canvas.height = Math.floor(viewport.height * outputScale);
        canvas.style.width = `${viewport.width}px`;
        canvas.style.height = `${viewport.height}px`;
        renderTask = page.render({
          canvas,
          viewport,
          transform: outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : undefined,
        });
        const textContent = await page.getTextContent();
        await renderTask.promise;
        if (!active) return;

        const pdfjs = await import("pdfjs-dist");
        textLayerElement.style.setProperty("--total-scale-factor", String(scale));
        textLayer = new pdfjs.TextLayer({
          textContentSource: textContent,
          container: textLayerElement,
          viewport,
        });
        textLayerElement.style.width = `${viewport.width}px`;
        textLayerElement.style.height = `${viewport.height}px`;
        await textLayer.render();
        if (!active) return;

        const matchingIndexes = findMatchingTextDivIndexes(
          textLayer.textContentItemsStr,
          highlightQuote ?? "",
        );
        for (const index of matchingIndexes) {
          textLayer.textDivs[index]?.classList.add("highlight");
        }
        const quoteFound = highlightQuote ? matchingIndexes.length > 0 : null;
        setRenderResult({ page: displayPage, quoteFound });
        setCurrentPage(displayPage);
        onPageChange?.(displayPage);
      } catch (renderError) {
        if (active) {
          const parsedError = asError(renderError);
          setRenderResult({ page: displayPage, error: parsedError.message });
          onError?.(parsedError);
        }
      }
    }

    void renderPage(currentDocument, textLayerContainer);
    return () => {
      active = false;
      renderTask?.cancel();
      textLayer?.cancel();
    };
  }, [displayPage, highlightQuote, onError, onPageChange, pdfDocument]);

  function changePage(page: number) {
    if (page >= 1 && page <= pageCount) {
      setPageOverride({ targetPage, page });
    }
  }

  return (
    <section className="mt-4 rounded-lg border border-slate-200 bg-white p-3 sm:p-4" aria-label={`PDF viewer for ${documentId ?? "document"}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-800">
          PDF page {currentPage}{pageCount > 0 ? ` of ${pageCount}` : ""}
        </p>
        <div className="flex items-center gap-2">
          <button
            className="rounded border border-slate-300 px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
            disabled={loading || currentPage <= 1}
            onClick={() => changePage(currentPage - 1)}
            type="button"
          >
            Previous
          </button>
          <button
            className="rounded border border-slate-300 px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
            disabled={loading || currentPage >= pageCount}
            onClick={() => changePage(currentPage + 1)}
            type="button"
          >
            Next
          </button>
        </div>
      </div>
      {loading && <p className="py-4 text-sm text-slate-600" role="status">Loading PDF page…</p>}
      {error && <p className="mt-3 text-sm text-red-800" role="alert">{error}</p>}
      {pageResult?.quoteFound === false && !error && (
        <p className="mt-3 text-sm text-amber-800" role="status">
          The cited quote could not be matched in the page text; the cited page is shown.
        </p>
      )}
      {pdfDocument && (
        <div className="mt-3 max-h-[75vh] overflow-auto rounded bg-slate-100 p-2">
          <div className={styles.page} ref={pageContainerRef}>
            <canvas ref={canvasRef} aria-label={`PDF page ${currentPage}`} />
            <div className={styles.textLayer} data-pdf-text-layer aria-hidden="true" />
          </div>
        </div>
      )}
    </section>
  );
}
