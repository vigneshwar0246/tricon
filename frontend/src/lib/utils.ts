import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }

export function formatDuration(value?: number | null) {
  if (value == null || Number.isNaN(value)) return "Not measured";
  return `${Math.round(value)} ms`;
}
