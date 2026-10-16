import { ClerkProvider } from '@clerk/nextjs';
import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Stock-Prediction | Machine Learning & Paper Trading Platform',
  description: 'Explore machine-learning-driven stock predictions, trading signals, and portfolio insights through one integrated platform.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en" className="dark">
        <body className="min-h-screen font-sans bg-[#080c14] text-slate-100 antialiased selection:bg-emerald-500/30 selection:text-emerald-200">
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}