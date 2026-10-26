import { expect, test } from "@playwright/test";

import { mockLangGraphAPI } from "./utils/mock-api";

test("campus landing links to the complete workspace on desktop and mobile", async ({
  page,
}) => {
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page).toHaveTitle(/CampusResearch/);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "调研开始",
    );
    await expect(
      page.getByRole("link", { name: "开始我的课题调研" }),
    ).toHaveAttribute("href", "/workspace/chats/new");
    await expect(
      page.getByRole("link", { name: /基于开源 DeerFlow/ }),
    ).toHaveAttribute("href", "https://github.com/bytedance/deer-flow");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `test-results/campus-home-${width}.png`,
      fullPage: true,
    });
  }
});

test("campus examples populate the composer and preview is clearly identified", async ({
  page,
}) => {
  mockLangGraphAPI(page);
  await page
    .context()
    .addCookies([
      { name: "locale", value: "zh-CN", url: "http://127.0.0.1:3000" },
    ]);
  await page.route("**/campus-status", (route) =>
    route.fulfill({ json: { modelConfigured: false } }),
  );
  await page.goto("/workspace/chats/new");
  await expect(
    page.getByText("把一个想法，变成可落地的课题。", { exact: true }).last(),
  ).toBeVisible();
  await expect(
    page.getByRole("status").filter({ hasText: "当前为界面预览" }),
  ).toBeVisible();
  const notice = await page
    .getByRole("status")
    .filter({ hasText: "当前为界面预览" })
    .boundingBox();
  expect(notice?.y).toBeGreaterThanOrEqual(0);
  await page.getByRole("button", { name: "选题调研", exact: true }).click();
  await expect(
    page.getByPlaceholder("想做什么项目？告诉我你的基础和剩余时间…"),
  ).toHaveValue(/校园失物招领系统/);
  await expect(
    page.getByPlaceholder("想做什么项目？告诉我你的基础和剩余时间…"),
  ).toHaveValue(/两个月/);
  await page.screenshot({
    path: "test-results/campus-workspace.png",
    fullPage: true,
  });
});

test("report review fills an editable draft without starting a run on desktop and mobile", async ({
  page,
}) => {
  mockLangGraphAPI(page);
  await page
    .context()
    .addCookies([
      { name: "locale", value: "zh-CN", url: "http://127.0.0.1:3000" },
    ]);
  await page.route("**/campus-status", (route) =>
    route.fulfill({ json: { modelConfigured: true } }),
  );
  const runRequests: string[] = [];
  page.on("request", (request) => {
    if (
      request.method() === "POST" &&
      /\/runs(?:\/|\?|$)/.test(new URL(request.url()).pathname)
    ) {
      runRequests.push(request.url());
    }
  });

  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/workspace/chats/new");
    await page.getByRole("button", { name: "报告复核", exact: true }).click();
    const composer = page.getByPlaceholder(
      "想做什么项目？告诉我你的基础和剩余时间…",
    );
    await expect(composer).toHaveValue(/若没有可读取的报告/);
    await expect(composer).toHaveValue(/仅搜索摘要和待验证/);
    await expect(composer).toHaveValue(/基础、周期和预算/);
    await expect(composer).toHaveValue(/实际工具、文件、下载证据/);
    await expect(composer).toHaveValue(/问题、依据、修改建议、仍待验证/);
    await composer.fill(
      `${await composer.inputValue()}\n我的补充：只复核技术路线部分。`,
    );
    await expect(composer).toHaveValue(/我的补充：只复核技术路线部分/);
    await expect(page).toHaveURL(/\/workspace\/chats\/new$/);
    expect(runRequests).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `test-results/campus-review-${width}.png`,
      fullPage: true,
    });
  }
});
