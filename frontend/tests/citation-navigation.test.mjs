import assert from "node:assert/strict";
import test from "node:test";

import {
  findMatchingTextDivIndexes,
  getCitationTarget,
} from "../src/lib/citationNavigation.ts";

function citation(overrides = {}) {
  return {
    id: "citation-1",
    claim_id: "claim-1",
    index: 1,
    document_id: "document-1",
    filename: "research.pdf",
    page_number: 3,
    chunk_id: "chunk-1",
    quote: "Key finding in the source",
    heading: null,
    ...overrides,
  };
}

test("resolves citation document, page, and quote for viewer navigation", () => {
  assert.deepEqual(getCitationTarget(citation()), {
    documentId: "document-1",
    pageNumber: 3,
    quote: "Key finding in the source",
  });
});

test("does not resolve citations with a null document or invalid page", () => {
  assert.equal(getCitationTarget(citation({ document_id: null })), null);
  assert.equal(getCitationTarget(citation({ page_number: 0 })), null);
});

test("finds text items containing a normalized quote across spans", () => {
  assert.deepEqual(
    findMatchingTextDivIndexes(["This is the key ", "finding in", " the source text."], "key finding\nin the source"),
    [0, 1, 2],
  );
});

test("returns no match when the quote is unavailable on the cited page", () => {
  assert.deepEqual(findMatchingTextDivIndexes(["Different page text"], "missing quote"), []);
});
