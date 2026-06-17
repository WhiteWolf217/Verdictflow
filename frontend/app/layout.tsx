import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VerdictFlow — Contract Intelligence",
  description:
    "Multi-agent contract review system with tamper-evident audit trails. Upload, analyze, red-team, and redline enterprise contracts.",
  keywords: [
    "contract review",
    "AI agents",
    "legal tech",
    "compliance",
    "redline",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-zinc-950 text-zinc-100 antialiased">
        {/* Background grid pattern */}
        <div className="fixed inset-0 bg-grid pointer-events-none opacity-50" />

        {/* Ambient gradient orbs */}
        <div className="fixed top-0 left-1/4 w-[500px] h-[500px] bg-emerald-500/5 rounded-full blur-[120px] pointer-events-none" />
        <div className="fixed bottom-0 right-1/4 w-[500px] h-[500px] bg-cyan-500/5 rounded-full blur-[120px] pointer-events-none" />

        {/* Main content */}
        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}
