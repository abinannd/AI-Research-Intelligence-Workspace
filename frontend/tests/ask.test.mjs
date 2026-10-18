import assert from "node:assert/strict";
import test from "node:test";

import { createAskPayload } from "../src/lib/ask.ts";

test("does not create an ask payload for an empty question", () => {
  assert.equal(createAskPayload("  \n ", ["ready-document"]), null);
});

test("does not create an ask payload without ready documents", () => {
  assert.equal(createAskPayload("What are the findings?", []), null);
});

test("trims the question and scopes the payload to ready workspace documents", () => {
  assert.deepEqual(createAskPayload("  What are the findings?  ", ["doc-1", "doc-2"]), {
    question: "What are the findings?",
    document_ids: ["doc-1", "doc-2"],
  });
});
