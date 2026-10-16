import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatApiError(body: unknown, fallback = "Something went wrong"): string {
  if (!body) return fallback;
  if (typeof body === "string") return body;
  if (typeof body === "object" && body !== null) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const parts = detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return null;
        })
        .filter(Boolean);
      if (parts.length) return parts.join(" ");
    }
    if ("message" in body && typeof (body as { message: unknown }).message === "string") {
      return (body as { message: string }).message;
    }
  }
  return fallback;
}

export function formatClock(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}
