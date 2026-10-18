export const MAX_PDF_BYTES = 20 * 1024 * 1024;

export function validatePdfUpload(filename: string, size: number): string | null {
  if (!filename.toLowerCase().endsWith(".pdf")) {
    return "Only PDF files are accepted.";
  }
  if (size === 0) {
    return "Choose a non-empty PDF file.";
  }
  if (size > MAX_PDF_BYTES) {
    return "PDF exceeds the 20 MiB size limit.";
  }
  return null;
}
