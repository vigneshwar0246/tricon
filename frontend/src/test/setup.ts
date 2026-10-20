import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

beforeEach(() => {
  sessionStorage.setItem("intro_seen", "1");
});

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

Object.defineProperty(window.HTMLElement.prototype, "scrollTo", { configurable: true, value: vi.fn() });

