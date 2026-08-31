import type { Metadata } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";

import { AppHeader } from "@/components/layout/AppHeader";
import { SkipLink } from "@/components/layout/SkipLink";
import { copy } from "@/lib/copy";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: copy.appName,
  description: copy.statusDescription,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" className={inter.variable}>
      <body className="font-sans antialiased">
        <SkipLink />
        <AppHeader />
        <main id="contenido" className="px-4 py-6 md:px-8 md:py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
