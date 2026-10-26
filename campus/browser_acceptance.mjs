// Real browser acceptance against the completed local conversation; no mocks.
import { chromium } from "../frontend/node_modules/@playwright/test/index.mjs";
import { readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";

const output = new URL("./live-results/", import.meta.url);
const manifest = new URL("acceptance.json", output);
const evidence = JSON.parse(await readFile(manifest, "utf8"));
const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({
    locale: "zh-CN", viewport: { width: 1440, height: 1000 }, acceptDownloads: true,
  });
  const page = await context.newPage();
  await page.goto("http://127.0.0.1:3000/workspace/chats/new", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Ultra", exact: true }).waitFor({ state: "visible", timeout: 30000 });
  evidence.fresh_browser_default_mode = "ultra";
  await page.goto(evidence.chat_url, { waitUntil: "domcontentloaded" });
  const report = page.getByText("campus-research-report.md", { exact: true }).first();
  await report.waitFor({ state: "visible", timeout: 60000 });
  await report.click();
  await page.getByRole("heading", { name: /校园失物招领系统/ }).first().waitFor({ state: "visible", timeout: 30000 });
  const downloadButton = page.getByRole("button", { name: /^(下载|Download)$/ }).last();
  const downloadLink = page.getByRole("link", { name: /^(下载|Download)$/ }).last();
  await page.screenshot({ path: fileURLToPath(new URL("report-browser.png", output)), fullPage: true });
  const downloadPromise = page.waitForEvent("download", { timeout: 30000 });
  if (await downloadButton.isVisible()) await downloadButton.click();
  else await downloadLink.click();
  const download = await downloadPromise;
  const saved = new URL("browser-download.md", output);
  await download.saveAs(fileURLToPath(saved));
  const bytes = await readFile(saved);
  const digest = createHash("sha256").update(bytes).digest("hex");
  if (digest !== evidence.download_sha256) throw new Error("Browser/API download mismatch");
  evidence.browser_download = { filename: download.suggestedFilename(), bytes: bytes.length, sha256: digest, method: "clicked report artifact, then actual Download control", verified: true };
  await writeFile(manifest, JSON.stringify(evidence, null, 2), "utf8");
  console.log("BROWSER_DOWNLOAD_OK", bytes.length, "bytes", download.suggestedFilename());
} finally {
  await browser.close();
}
