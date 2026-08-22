import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Arc Terminal · Solana intelligence",
  description: "Local-first Solana market analysis and paper trading terminal.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className="bg-background"><body>{children}</body></html>;
}
