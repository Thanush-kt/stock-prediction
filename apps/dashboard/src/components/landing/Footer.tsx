import React from 'react';
import Link from 'next/link';

export function Footer() {
  return (
    <footer className="border-t border-slate-800/80 bg-[#060910] text-slate-400 text-xs">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 lg:py-16 space-y-10">
        {/* Top Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 lg:gap-12">
          {/* Brand Info */}
          <div className="md:col-span-6 space-y-4">
            <Link href="/" className="flex items-center gap-2.5 text-base font-bold text-white">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <span>
                Stock<span className="text-emerald-400">Prediction</span>
              </span>
            </Link>
            <p className="text-slate-400 text-xs sm:text-sm max-w-md leading-relaxed">
              An open quantitative platform combining continuous machine-learning prediction models, disciplined strategy rules, and paper-trading execution.
            </p>
            <div className="flex items-center gap-2 font-mono text-[11px] text-emerald-400">
              <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
              <span>FastAPI · Next.js · Alpaca Sandbox · PostgreSQL</span>
            </div>
          </div>

          {/* Navigation Links */}
          <div className="md:col-span-3 space-y-3">
            <div className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">
              Platform
            </div>
            <ul className="space-y-2">
              <li>
                <Link href="/" className="hover:text-emerald-400 transition">
                  Home
                </Link>
              </li>
              <li>
                <Link href="#features" className="hover:text-emerald-400 transition">
                  Features
                </Link>
              </li>
              <li>
                <Link href="#how-it-works" className="hover:text-emerald-400 transition">
                  How It Works
                </Link>
              </li>
              <li>
                <Link href="#about" className="hover:text-emerald-400 transition">
                  About
                </Link>
              </li>
            </ul>
          </div>

          {/* Portal Links */}
          <div className="md:col-span-3 space-y-3">
            <div className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">
              Account & Portal
            </div>
            <ul className="space-y-2">
              <li>
                <Link href="/dashboard" className="hover:text-emerald-400 transition">
                  Trading Dashboard
                </Link>
              </li>
              <li>
                <Link href="/sign-in" className="hover:text-emerald-400 transition">
                  Sign In
                </Link>
              </li>
              <li>
                <Link href="/sign-up" className="hover:text-emerald-400 transition">
                  Get Started
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Risk Disclaimer Box */}
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4 sm:p-5 text-slate-400 space-y-2">
          <div className="flex items-center gap-2 text-slate-300 font-semibold text-xs">
            <svg className="h-4 w-4 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>Important Risk & Educational Disclaimer</span>
          </div>
          <p className="text-[11px] leading-relaxed text-slate-400">
            Stock-Prediction is an educational and analytical tool. Machine-learning predictions are uncertain and may be inaccurate. Paper-trading results do not guarantee future performance or real-world trading outcomes. This platform does not provide personalized financial advice.
          </p>
        </div>

        {/* Bottom Bar */}
        <div className="pt-6 border-t border-slate-800/60 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-slate-400">
          <div>
            © {new Date().getFullYear()} Stock-Prediction. All rights reserved.
          </div>
          <div className="flex items-center gap-4">
            <span>Algorithmic Research & Simulation Platform</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
