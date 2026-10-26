import "@/styles/globals.css";

import { type Metadata } from "next";

import { ThemeProvider } from "@/components/theme-provider";
import { ArtifactDraftsProvider } from "@/core/artifacts/draft-context";
import { DEFAULT_LOCALE } from "@/core/i18n/locale";

export const metadata: Metadata = {
  title: "CampusResearch · 校园选题调研助手",
  description:
    "从毕业设计想法到有来源、可落地的技术方案。基于 DeerFlow 的校园调研助手。",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang={DEFAULT_LOCALE}
      suppressContentEditableWarning
      suppressHydrationWarning
    >
      <body>
        <ThemeProvider attribute="class" enableSystem disableTransitionOnChange>
          <ArtifactDraftsProvider>{children}</ArtifactDraftsProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
