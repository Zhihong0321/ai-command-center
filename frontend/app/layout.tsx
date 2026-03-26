import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Command Center",
  description: "Central coordination hub for AI coding agents",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-gray-950 text-gray-100 min-h-screen`}>
        <nav className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center gap-8">
                <Link href="/" className="flex items-center gap-2">
                  <span className="text-2xl">⚡</span>
                  <span className="font-bold text-lg bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
                    AI Command Center
                  </span>
                </Link>
                <div className="hidden md:flex items-center gap-6 text-sm">
                  <Link href="/" className="text-gray-400 hover:text-white transition-colors">Dashboard</Link>
                  <Link href="/repos" className="text-gray-400 hover:text-white transition-colors">Repos</Link>
                  <Link href="/agents" className="text-gray-400 hover:text-white transition-colors">Agents</Link>
                  <Link href="/tasks" className="text-gray-400 hover:text-white transition-colors">Tasks</Link>
                  <Link href="/activity" className="text-gray-400 hover:text-white transition-colors">Activity</Link>
                  <Link href="/bugs" className="text-gray-400 hover:text-white transition-colors">Bugs 🐛</Link>
                  <Link href="/secrets" className="text-gray-400 hover:text-white transition-colors">Vault 🔐</Link>
                  <Link href="/settings" className="text-gray-400 hover:text-white transition-colors">Settings ⚙️</Link>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                Live
              </div>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
