import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  FileText,
  Settings,
  Shield,
  BarChart3,
  Bell,
  LogOut,
  AlertCircle,
  UserCheck,
  Trash2,
} from "lucide-react";
import { clsx } from "clsx";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/fiduciaries", label: "Fiduciaries", icon: Shield },
  { href: "/consents", label: "Consents", icon: FileText },
  { href: "/principals", label: "Data Principals", icon: Users },
  { href: "/grievances", label: "Grievances", icon: AlertCircle },
  { href: "/guardians", label: "Guardians", icon: UserCheck },
  { href: "/deletions", label: "Deletion Requests", icon: Trash2 },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/webhooks", label: "Webhooks", icon: Bell },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 min-h-screen bg-gray-900 text-white">
      <div className="p-4 border-b border-gray-800">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <Shield className="w-6 h-6" />
          ConsentChain
        </h1>
        <p className="text-xs text-gray-400 mt-1">Admin Portal</p>
      </div>

      <nav className="p-4">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={clsx(
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                    isActive
                      ? "bg-primary-600 text-white"
                      : "text-gray-300 hover:bg-gray-800",
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="absolute bottom-0 left-0 w-64 p-4 border-t border-gray-800">
        <button className="flex items-center gap-2 text-gray-400 hover:text-white text-sm">
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
