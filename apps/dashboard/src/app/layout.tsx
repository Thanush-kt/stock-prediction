import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'Stock-Prediction Dashboard',
  description: 'Read-only paper-trading dashboard.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-mono">
        <main className="px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
