'use client';

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Phone, BarChart3, Settings, Home, FileText } from "lucide-react";

const navigation = [
  { name: 'Overview', href: '/dashboard', icon: Home },
  { name: 'Calls', href: '/dashboard/calls', icon: Phone },
  { name: 'Analytics', href: '/dashboard/analytics', icon: BarChart3 },
  { name: 'Transcripts', href: '/dashboard/calls', icon: FileText },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex flex-col w-64 bg-gray-900 h-screen">
      <div className="flex items-center h-16 px-4 bg-gray-800">
        <Phone className="h-8 w-8 text-blue-400" />
        <span className="ml-2 text-xl font-bold text-white">Zenith AI</span>
      </div>

      <nav className="flex-1 px-2 py-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors",
                isActive
                  ? "bg-gray-800 text-white"
                  : "text-gray-300 hover:bg-gray-800 hover:text-white"
              )}
            >
              <Icon className="h-5 w-5 mr-3" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-800">
        <div className="text-xs text-gray-400">
          <p>Zenith AI Agent v1.0</p>
          <p className="mt-1">Status: 🟢 Active</p>
        </div>
      </div>
    </div>
  );
}
