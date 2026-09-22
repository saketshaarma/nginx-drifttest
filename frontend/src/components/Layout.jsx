import { NavLink, useNavigate } from "react-router-dom";
import { LayoutDashboard, Building2, GitCompareArrows, AlertTriangle, LogOut, ServerCog } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, testid: "nav-dashboard", end: true },
  { to: "/businesses", label: "Businesses", icon: Building2, testid: "nav-businesses" },
  { to: "/runs", label: "Comparison Runs", icon: GitCompareArrows, testid: "nav-runs" },
  { to: "/incidents", label: "Incidents", icon: AlertTriangle, testid: "nav-incidents" },
];

export function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-200 flex">
      <aside className="w-64 shrink-0 border-r border-slate-800 bg-[#0d1220]/90 backdrop-blur-md flex flex-col fixed h-full z-20">
        <div className="px-5 h-16 flex items-center gap-2.5 border-b border-slate-800">
          <div className="h-9 w-9 rounded-lg bg-sky-500/15 border border-sky-500/30 flex items-center justify-center">
            <ServerCog className="h-5 w-5 text-sky-400" />
          </div>
          <div>
            <div className="font-display font-bold text-[15px] leading-tight text-slate-100">DriftWatch</div>
            <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500">nginx config ops</div>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              data-testid={item.testid}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-sky-500/10 text-sky-300 border border-sky-500/20"
                    : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/50 border border-transparent"
                )
              }
            >
              <item.icon className="h-[18px] w-[18px]" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-slate-800">
          <div className="flex items-center gap-2.5 px-2 py-2 mb-1">
            <div className="h-8 w-8 rounded-full bg-slate-700 flex items-center justify-center text-xs font-semibold text-slate-200">
              {(user?.name || user?.email || "U").slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="text-xs font-medium text-slate-200 truncate">{user?.name}</div>
              <div className="text-[10px] text-slate-500 truncate">{user?.email}</div>
            </div>
          </div>
          <button
            data-testid="logout-btn"
            onClick={handleLogout}
            className="w-full flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
          >
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 ml-64 min-h-screen">{children}</main>
    </div>
  );
}

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="sticky top-0 z-10 bg-[#0B0F19]/85 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-xl font-bold tracking-tight text-slate-100">{title}</h1>
          {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
        <div className="flex items-center gap-3">{children}</div>
      </div>
    </div>
  );
}
