import React from 'react';
import { Navbar } from '@/components/landing/Navbar';
import { HeroSection } from '@/components/landing/HeroSection';
import { MarketOverview } from '@/components/landing/MarketOverview';
import { FeaturesSection } from '@/components/landing/FeaturesSection';
import { HowItWorksSection } from '@/components/landing/HowItWorksSection';
import { DashboardPreviewSection } from '@/components/landing/DashboardPreviewSection';
import { AboutSection } from '@/components/landing/AboutSection';
import { FinalCtaSection } from '@/components/landing/FinalCtaSection';
import { Footer } from '@/components/landing/Footer';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#080c14] text-slate-100 flex flex-col selection:bg-emerald-500/30 selection:text-emerald-200">
      <Navbar />
      <main className="flex-1">
        <HeroSection />
        <MarketOverview />
        <FeaturesSection />
        <HowItWorksSection />
        <DashboardPreviewSection />
        <AboutSection />
        <FinalCtaSection />
      </main>
      <Footer />
    </div>
  );
}
