import type { Citation } from "@/lib/types";

export interface CitationTarget {
  documentId: string;
  pageNumber: number;
  quote: string;
}

export function getCitationTarget(citation: Citation): CitationTarget | null {
  if (!citation.document_id || !Number.isInteger(citation.page_number) || citation.page_number < 1) {
    return null;
  }

  return {
    documentId: citation.document_id,
    pageNumber: citation.page_number,
    quote: citation.quote,
  };
}

export function findMatchingTextDivIndexes(texts: string[], quote: string): number[] {
  const normalizedQuote = quote.toLocaleLowerCase().replace(/\s+/g, " ").trim();
  if (!normalizedQuote) return [];

  let normalizedText = "";
  const owners: number[] = [];
  let pendingSpace = false;

  texts.forEach((text, index) => {
    for (const character of text.toLocaleLowerCase()) {
      if (/\s/.test(character)) {
        pendingSpace = normalizedText.length > 0;
        continue;
      }
      if (pendingSpace) {
        normalizedText += " ";
        owners.push(index);
        pendingSpace = false;
      }
      normalizedText += character;
      owners.push(index);
    }
    if (index < texts.length - 1) pendingSpace = true;
  });

  const matchStart = normalizedText.indexOf(normalizedQuote);
  if (matchStart === -1) return [];
  const matchEnd = matchStart + normalizedQuote.length;
  return [...new Set(owners.slice(matchStart, matchEnd))];
}
