import Link from "next/link";


export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
        <header className="border-b border-neutral-300 dark:border-neutral-800 px-6 py-3 flex gap-6 items-center">
          <h1 className="font-semibold">stock-prediction</h1>
          <nav className="flex gap-4 text-sm">
            <Link href="/dashboard" className="hover:underline">Positions</Link>
            <Link href="/signals" className="hover:underline">Signals</Link>
            <Link href="/equity" className="hover:underline">Equity</Link>
          </nav>
        </header>
      <body className="min-h-screen font-mono">
        <main className="px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
