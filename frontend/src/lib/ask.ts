export interface AskPayload {
  question: string;
  document_ids: string[];
}

export function createAskPayload(
  question: string,
  readyDocumentIds: string[],
): AskPayload | null {
  const normalizedQuestion = question.trim();
  if (!normalizedQuestion || readyDocumentIds.length === 0) return null;

  return {
    question: normalizedQuestion,
    document_ids: readyDocumentIds,
  };
}
