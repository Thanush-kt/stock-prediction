import { auth } from '@clerk/nextjs/server';
import { DashboardNav } from '@/components/DashboardNav';

export default async function Layout({ children }: { children: React.ReactNode }) {
  await auth.protect();

  return (
    <div className="min-h-screen bg-[#080c14] text-slate-100 flex flex-col selection:bg-emerald-500/30 selection:text-emerald-200">
      <DashboardNav />
      {/* Background radial glow */}
      <div className="pointer-events-none fixed top-20 right-1/4 w-[500px] h-[300px] bg-emerald-500/5 blur-[150px] rounded-full" />
      <main className="relative flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
