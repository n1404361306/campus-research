"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

import { AuroraText } from "../ui/aurora-text";

let waved = false;

function WelcomeDescription({ children }: { children: string }) {
  return (
    <p className="max-w-full text-wrap break-words whitespace-pre-line">
      {children}
    </p>
  );
}

export function Welcome({
  className,
  mode,
}: {
  className?: string;
  mode?: "ultra" | "pro" | "thinking" | "flash";
}) {
  const { t } = useI18n();
  const [preview, setPreview] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    void fetch("/campus-status", { signal: controller.signal })
      .then((response) => response.json())
      .then((status: { modelConfigured?: boolean }) => {
        if (!controller.signal.aborted)
          setPreview(status.modelConfigured === false);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, []);
  const searchParams = useSearchParams();
  const isUltra = useMemo(() => mode === "ultra", [mode]);
  const colors = useMemo(() => {
    if (isUltra) {
      return ["#efefbb", "#e9c665", "#e3a812"];
    }
    return ["var(--color-foreground)"];
  }, [isUltra]);
  useEffect(() => {
    waved = true;
  }, []);
  return (
    <div
      className={cn(
        "mx-auto flex w-full max-w-full flex-col items-center justify-center gap-2 px-4 py-4 text-center sm:px-8",
        className,
      )}
    >
      {preview &&
        createPortal(
          <p
            role="status"
            className="fixed right-4 bottom-4 z-50 max-w-[min(24rem,calc(100vw-2rem))] rounded-xl border border-amber-300/50 bg-amber-50 px-4 py-3 text-sm text-amber-900 shadow-sm dark:bg-amber-950 dark:text-amber-100"
          >
            当前为界面预览，尚未连接模型。请在项目根目录的 .env
            填写模型配置并重启后，再发送调研任务。
          </p>,
          document.body,
        )}
      <div className="max-w-full text-2xl font-bold">
        {searchParams.get("mode") === "skill" ? (
          `✨ ${t.welcome.createYourOwnSkill} ✨`
        ) : (
          <div className="flex max-w-full flex-wrap items-center justify-center gap-2">
            <div className={cn("inline-block", !waved ? "animate-wave" : "")}>
              {isUltra ? "🚀" : "👋"}
            </div>
            <AuroraText colors={colors}>{t.welcome.greeting}</AuroraText>
          </div>
        )}
      </div>
      {searchParams.get("mode") === "skill" ? (
        <div className="text-muted-foreground max-w-full text-sm">
          <WelcomeDescription>
            {t.welcome.createYourOwnSkillDescription}
          </WelcomeDescription>
        </div>
      ) : (
        <div className="text-muted-foreground max-w-full text-sm">
          <WelcomeDescription>{t.welcome.description}</WelcomeDescription>
        </div>
      )}
    </div>
  );
}
