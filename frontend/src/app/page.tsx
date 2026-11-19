'use client';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { AlertTriangle, Shield, Users, Activity } from 'lucide-react';

export default function HomePage() {
  const { user } = useAuth();

  const dashboardHref = user?.role === 'CITIZEN'
    ? '/dashboard/citizen'
    : user?.role === 'COORDINATOR'
      ? '/dashboard/admin'
      : '/dashboard/admin';

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-950 via-blue-900 to-blue-800 text-white">
      {/* Nav */}
      <nav className="flex justify-between items-center px-8 py-5 border-b border-blue-700/40">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-8 h-8 text-orange-400" />
          <span className="text-2xl font-bold tracking-tight">CrisisLink</span>
        </div>
        <div className="flex gap-3">
          {user ? (
            <Link
              href={dashboardHref}
              className="btn-primary bg-orange-500 hover:bg-orange-600"
            >
              Go to Dashboard
            </Link>
          ) : (
            <>
              <Link href="/login"    className="btn-ghost border-white/30 text-white hover:bg-white/10">Login</Link>
              <Link href="/register" className="btn-primary bg-orange-500 hover:bg-orange-600">Register</Link>
            </>
          )}
        </div>
      </nav>

      {/* Hero */}
      <div className="max-w-5xl mx-auto px-8 pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-2 bg-orange-500/20 border border-orange-400/30 rounded-full px-4 py-1.5 text-orange-300 text-sm font-medium mb-6">
          <Activity className="w-4 h-4" /> Real-time Disaster Coordination
        </div>
        <h1 className="text-5xl md:text-6xl font-extrabold leading-tight mb-6">
          Coordinating Relief<br />
          <span className="text-orange-400">When It Matters Most</span>
        </h1>
        <p className="text-xl text-blue-200 max-w-2xl mx-auto mb-10">
          CrisisLink connects citizens in distress with rescue organizations, resources,
          and shelters — providing a centralized, database-backed coordination platform
          for effective disaster response.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/register?role=CITIZEN"
            className="px-8 py-4 bg-orange-500 hover:bg-orange-600 rounded-xl font-bold text-lg transition-colors">
            🆘 Request Emergency Help
          </Link>
          <Link href="/login"
            className="px-8 py-4 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl font-bold text-lg transition-colors">
            🛡️ Coordinator Login
          </Link>
        </div>
      </div>

      {/* Feature cards */}
      <div className="max-w-6xl mx-auto px-8 pb-20">
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: <AlertTriangle className="w-8 h-8 text-red-400" />,
              title: 'Emergency Requests',
              desc: 'Citizens submit rescue, medical, shelter, food, and evacuation requests instantly. Track status in real-time.',
              color: 'border-red-500/30 bg-red-900/20'
            },
            {
              icon: <Shield className="w-8 h-8 text-green-400" />,
              title: 'Resource Management',
              desc: 'Organizations manage boats, medical kits, food, ambulances and shelters. Inventory tracked with full audit trail.',
              color: 'border-green-500/30 bg-green-900/20'
            },
            {
              icon: <Users className="w-8 h-8 text-blue-400" />,
              title: 'Smart Coordination',
              desc: 'Coordinators assign resources to requests, manage shelter occupancy, and track incident response progress.',
              color: 'border-blue-500/30 bg-blue-900/20'
            },
          ].map((f, i) => (
            <div key={i} className={`rounded-xl border p-6 ${f.color}`}>
              <div className="mb-3">{f.icon}</div>
              <h3 className="text-lg font-bold mb-2">{f.title}</h3>
              <p className="text-blue-200/80 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Tech stack footer */}
      <div className="border-t border-blue-700/40 py-8 text-center">
        <p className="text-blue-400 text-sm mb-3 font-medium">Powered by</p>
        <div className="flex flex-wrap justify-center gap-4 text-sm text-blue-300">
          {['MySQL 8.0', 'MongoDB', 'Neo4j', 'ChromaDB', 'Python Flask', 'Next.js 14', 'Docker'].map(t => (
            <span key={t} className="bg-blue-800/50 px-3 py-1 rounded-full border border-blue-600/30">{t}</span>
          ))}
        </div>
        <p className="text-blue-500 text-xs mt-4">CrisisLink – DBMS University Project</p>
      </div>
    </div>
  );
}
