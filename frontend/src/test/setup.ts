import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => cleanup());

Object.defineProperty(window.HTMLElement.prototype, "scrollTo", { configurable: true, value: vi.fn() });
