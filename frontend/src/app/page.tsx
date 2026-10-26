import {
  ArrowRight,
  BookOpen,
  Check,
  Compass,
  FileText,
  Search,
} from "lucide-react";
import Link from "next/link";

const steps = [
  {
    number: "01",
    title: "说清你的想法",
    text: "从熟悉的校园场景出发，带上技术基础、开发时间和项目目标。",
    icon: Compass,
  },
  {
    number: "02",
    title: "让资料支撑选择",
    text: "检索相关产品、开源项目与官方文档，对比不同技术路线。",
    icon: Search,
  },
  {
    number: "03",
    title: "拿到可以执行的计划",
    text: "整理功能边界、每周里程碑、风险和参考来源，继续追问与调整。",
    icon: FileText,
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#f5f5ef] text-[#193c34]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Link
          href="/"
          className="flex items-center gap-2 font-semibold tracking-tight"
        >
          <BookOpen className="size-6" /> CampusResearch
        </Link>
        <Link
          href="/workspace/chats/new"
          className="rounded-full border border-[#193c34]/20 px-5 py-2 text-sm transition hover:bg-[#193c34]/5"
        >
          进入工作台 <span aria-hidden="true">↗</span>
        </Link>
      </header>
      <main className="mx-auto max-w-6xl px-6">
        <section className="grid items-center gap-12 py-16 md:grid-cols-[1.1fr_1fr] md:py-24">
          <div>
            <p className="mb-6 text-xs tracking-[0.2em] uppercase">
              A clearer start for your next project
            </p>
            <h1 className="text-5xl leading-[1.2] font-medium tracking-tight md:text-6xl">
              好课题，
              <br />
              从一次认真
              <br />
              <span className="text-[#69876a]">调研开始。</span>
            </h1>
            <p className="mt-7 max-w-md text-base leading-8 text-[#53665c]">
              想法太多，不知道选哪个；方向有了，不知道怎么做。把你的困惑交给校园调研助手，一起找到有资料依据、适合自己完成的方案。
            </p>
            <Link
              href="/workspace/chats/new"
              className="mt-9 inline-flex items-center gap-6 rounded-full bg-[#193c34] px-7 py-4 text-sm text-white transition hover:bg-[#2c5347]"
            >
              开始我的课题调研 <ArrowRight className="size-4" />
            </Link>
            <p className="mt-5 text-xs text-[#66766a]">
              中文交流 · 来源可追溯 · 支持继续调整方案
            </p>
          </div>
          <div className="rotate-1 rounded-2xl border border-[#193c34]/10 bg-white p-7 shadow-[0_20px_70px_-35px_#193c3460] md:p-9">
            <div className="flex items-center justify-between border-b border-[#193c34]/10 pb-5 text-xs text-[#758074]">
              <span>调研报告 · 结构示意</span>
              <FileText className="size-4" />
            </div>
            <p className="mt-6 text-xs tracking-widest text-[#83917f]">
              校园失物招领系统
            </p>
            <h2 className="mt-3 text-2xl font-medium">从需求到技术方案</h2>
            <p className="mt-4 text-sm leading-7 text-[#66766a]">
              面向个人开发，优先解决发布、检索和认领三个核心问题。
            </p>
            <div className="mt-6 space-y-4 text-sm">
              {[
                "真实场景与类似项目",
                "三种技术路线对比",
                "两个月开发计划",
                "风险清单与参考来源",
              ].map((item) => (
                <div key={item} className="flex items-center gap-3">
                  <span className="rounded-full bg-[#eaf0e5] p-1">
                    <Check className="size-3" />
                  </span>
                  {item}
                </div>
              ))}
            </div>
            <div className="mt-8 rounded-lg bg-[#f5f5ef] px-4 py-3 text-xs leading-6 text-[#66766a]">
              “如果只剩一个月，哪些功能应该先放下？”
              <br />
              <span className="text-[#193c34]">
                可以继续追问，让计划适应你的实际情况。
              </span>
            </div>
          </div>
        </section>
        <section className="border-t border-[#193c34]/15 py-14">
          <p className="text-xs tracking-widest text-[#758074]">从想法到行动</p>
          <div className="mt-8 grid gap-8 md:grid-cols-3">
            {steps.map(({ number, title, text, icon: Icon }) => (
              <article key={number}>
                <div className="mb-5 flex items-center gap-3 text-[#69876a]">
                  <Icon className="size-5" />
                  <span className="text-xs">{number}</span>
                </div>
                <h2 className="text-lg font-medium">{title}</h2>
                <p className="mt-3 text-sm leading-7 text-[#66766a]">{text}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
      <footer className="mx-auto flex max-w-6xl flex-wrap justify-between gap-3 border-t border-[#193c34]/15 px-6 py-7 text-xs text-[#66766a]">
        <span>CampusResearch · 为下一步，找到依据。</span>
        <a
          href="https://github.com/bytedance/deer-flow"
          target="_blank"
          rel="noreferrer"
          className="underline underline-offset-4"
        >
          基于开源 DeerFlow · MIT License
        </a>
      </footer>
    </div>
  );
}
