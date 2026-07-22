import type { Metadata } from "next";
import "@/styles/globals.css";
import { Providers } from "@/lib/providers";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: "Apex — Marketing Intelligence",
  description: "RVGT Apex · Signal Deck",
};

// No-flash theme bootstrap: set data-theme before first paint.
const themeBootstrap = `(function(){try{var t=localStorage.getItem('apex-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.dataset.theme=t;}catch(e){document.documentElement.dataset.theme='dark';}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark">
      <head>
        {/* Fonts via link (not next/font) so the build never depends on a network fetch.
            CSS vars --font-sans / --font-mono are defined in globals.css with system fallback. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap"
          rel="stylesheet"
        />
        <script dangerouslySetInnerHTML={{ __html: themeBootstrap }} />
      </head>
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
