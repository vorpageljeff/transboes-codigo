import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist", display: "swap" });

export const metadata: Metadata = { title: "Trans Boes", description: "Gestão operacional inteligente de fretes" };
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#0B1117" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="pt-BR" className={geist.variable}><body>{children}</body></html>;
}
