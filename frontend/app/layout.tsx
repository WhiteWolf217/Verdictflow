import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VerdictFlow — AI Contract Intelligence",
  description:
    "Multi-agent contract review platform with tamper-evident audit trails. Analyze, red-team, and redline enterprise contracts with AI.",
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
      <body className="min-h-screen antialiased">
        {/* Single subtle ambient glow */}
        <div className="fixed top-[-200px] right-[-100px] w-[600px] h-[600px] rounded-full pointer-events-none opacity-[0.03]"
          style={{ background: "radial-gradient(circle, #3b82f6, transparent 70%)" }}
        />
        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}
