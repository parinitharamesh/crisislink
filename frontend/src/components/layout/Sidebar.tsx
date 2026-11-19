'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import {
  AlertTriangle, Home, FileText, Shield, Package,
  Building2, LogOut, Activity, Users, ClipboardList, BarChart3, Radio, FileBarChart
} from 'lucide-react';
import { cn } from '@/lib/utils';

const citizenLinks = [
  { href: '/dashboard/citizen', label: 'Dashboard', icon: Home },
  { href: '/requests/submit', label: 'Submit Request', icon: AlertTriangle },
  { href: '/requests', label: 'My Requests', icon: FileText },
  { href: '/updates', label: 'Emergency Updates', icon: Radio },
];

const coordinatorLinks = [
  { href: '/dashboard/admin', label: 'Dashboard', icon: BarChart3 },
  { href: '/requests', label: 'All Requests', icon: ClipboardList },
  { href: '/incidents', label: 'Incidents', icon: Activity },
  { href: '/resources', label: 'Resources', icon: Package },
  { href: '/shelters', label: 'Shelters', icon: Building2 },
  { href: '/assignments', label: 'Assignments', icon: Users },
  { href: '/inventory', label: 'Inventory', icon: Shield },
  { href: '/updates', label: 'Emergency Updates', icon: Radio },
  { href: '/reports', label: 'Reports', icon: FileBarChart },
];

const adminLinks = [
  { href: '/dashboard/admin', label: 'Dashboard', icon: BarChart3 },
  { href: '/requests', label: 'All Requests', icon: ClipboardList },
  { href: '/incidents', label: 'Incidents', icon: Activity },
  { href: '/resources', label: 'Resources', icon: Package },
  { href: '/shelters', label: 'Shelters', icon: Building2 },
  { href: '/assignments', label: 'Assignments', icon: Users },
  { href: '/inventory', label: 'Inventory', icon: Shield },
  { href: '/updates', label: 'Emergency Updates', icon: Radio },
  { href: '/reports', label: 'Reports', icon: FileBarChart },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router   = useRouter();

  const links = user?.role === 'CITIZEN'
    ? citizenLinks
    : user?.role === 'COORDINATOR'
      ? coordinatorLinks
      : adminLinks;

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  return (
    <aside className="w-64 min-h-screen bg-gray-900 text-white flex flex-col fixed left-0 top-0 z-30">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-gray-700">
        <AlertTriangle className="w-7 h-7 text-orange-400" />
        <div>
          <span className="font-bold text-lg">CrisisLink</span>
          <p className="text-gray-400 text-xs">Disaster Response</p>
        </div>
      </div>

      {/* User info */}
      {user && (
        <div className="px-4 py-4 border-b border-gray-700">
          <div className="bg-gray-800 rounded-lg px-3 py-2">
            <p className="font-medium text-sm truncate">{user.full_name}</p>
            <span className={cn(
              'text-xs px-2 py-0.5 rounded-full font-medium',
              user.role === 'ADMIN'       ? 'bg-purple-900 text-purple-300' :
              user.role === 'COORDINATOR' ? 'bg-blue-900 text-blue-300' :
                                            'bg-green-900 text-green-300'
            )}>
              {user.role}
            </span>
          </div>
        </div>
      )}

      {/* Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {links.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/');
          return (
            <Link key={href} href={href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                active
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              )}>
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <div className="px-3 py-4 border-t border-gray-700">
        <button onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:bg-red-900/40 hover:text-red-300 transition-colors">
          <LogOut className="w-4 h-4" />
          Logout
        </button>
      </div>
    </aside>
  );
}
