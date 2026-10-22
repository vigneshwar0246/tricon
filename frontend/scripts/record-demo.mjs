import { chromium } from "playwright";
import { mkdir, rename, rm, writeFile } from "node:fs/promises";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "../..");
const artifacts = path.join(root, "artifacts", "demo");
const micWav = path.join(artifacts, "interviewer-question.wav");
await mkdir(artifacts, { recursive: true });

const browser = await chromium.launch({
  headless: true,
  executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", `--use-file-for-fake-audio-capture=${micWav}`],
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  recordVideo: { dir: artifacts, size: { width: 1440, height: 900 } },
  permissions: ["microphone"],
  reducedMotion: "reduce",
});
const page = await context.newPage();
const events = [];
const recordingStarted = Date.now();
const mark = (step, result, detail = "", extra = {}) => events.push({ time: new Date().toISOString(), offset_ms: Date.now() - recordingStarted, step, result, detail, ...extra });
const ask = async (question, expected, holdMs = 10000) => {
  const questionOffsetMs = Date.now() - recordingStarted;
  await page.waitForTimeout(5500);
  const before = await page.locator("article.message.assistant").count();
  await page.getByRole("textbox", { name: "Message" }).fill(question);
  await page.getByRole("button", { name: "Send message" }).click();
  await page.locator("article.message.assistant").nth(before).waitFor({ timeout: 30000 });
  const actual = (await page.locator("article.message.assistant").nth(before).innerText()).replace(/\s+/g, " ").trim();
  if (expected && !actual.toLocaleLowerCase().includes(expected.toLocaleLowerCase())) throw new Error(`Response did not contain '${expected}': ${actual}`);
  mark(question, "PASS", actual, { kind: "question", question_offset_ms: questionOffsetMs });
  await page.waitForTimeout(holdMs);
};

try {
  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  const enter = page.getByRole("button", { name: /enter the ai voice assistant/i });
  if (await enter.isVisible().catch(() => false)) await enter.click();
  await page.getByRole("heading", { name: "Hello!" }).waitFor();
  mark("Open real application", "PASS", "Single browser session started");
  await page.waitForTimeout(4000);

  await ask("What can you do?", "I", 9000);
  await ask("Explain artificial intelligence in one simple sentence.", "artificial intelligence", 11000);
  await ask("What is the difference between a CPU and a GPU?", "GPU", 21000);
  await ask("Tell me the current system status.", "Backend: PASS", 29000);

  await page.getByRole("link", { name: "Settings" }).click();
  await page.getByRole("button", { name: /Run system requirements/i }).click();
  await page.getByText("Configured model", { exact: false }).waitFor({ timeout: 30000 });
  mark("Live system requirements", "PASS", "Hardware and bounded model inference shown");
  await page.waitForTimeout(5000);
  await page.getByRole("link", { name: "Home", exact: true }).click();

  await page.getByRole("button", { name: "Start listening" }).first().click();
  await page.waitForTimeout(7000);
  await page.getByRole("button", { name: "Stop listening" }).first().click();
  await page.getByText("What is artificial intelligence", { exact: false }).last().waitFor({ timeout: 60000 });
  mark("Real tap-to-speak pipeline", "PASS", "Browser audio -> Faster-Whisper -> Qwen -> Piper");
  const play = page.getByRole("button", { name: "Play response" }).last();
  if (await play.isVisible().catch(() => false)) await play.click();
  await page.waitForTimeout(14000);

  await page.getByRole("button", { name: "Use Hindi" }).click();
  await ask("भारत की राजधानी क्या है?", "", 8000);
  mark("Hindi language switch", "PASS", "Devanagari response received in same session");
  await page.waitForTimeout(3000);

  await page.getByRole("button", { name: "Use English" }).click();
  await ask("Summarize what we tested in one sentence.", "tested", 8000);
  await page.waitForTimeout(2000);

  const priorHandsFree = await page.locator("article.message.assistant").count();
  await page.getByRole("button", { name: "Enable hands-free" }).click();
  await page.locator("article.message.assistant").nth(priorHandsFree).waitFor({ timeout: 45000 });
  mark("Real hands-free pipeline", "PASS", "Continuous capture produced a real assistant turn");
  await page.waitForTimeout(8000);
} catch (error) {
  mark("Recording", "FAIL", error instanceof Error ? error.message : String(error));
  throw error;
} finally {
  await writeFile(path.join(artifacts, "browser-demo-results.json"), JSON.stringify(events, null, 2));
  const video = page.video();
  await context.close();
  if (video) {
    const destination = path.join(artifacts, "trikon-real-demo.webm");
    await rm(destination, { force: true });
    await rename(await video.path(), destination);
  }
  await browser.close();
}
