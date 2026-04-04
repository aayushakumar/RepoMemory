import { NavLink } from "react-router-dom";
import {
  Search,
  Database,
  Brain,
  Activity,
  ExternalLink,
} from "lucide-react";

const links = [
  { to: "/", icon: Search, label: "Search" },
  { to: "/repos", icon: Database, label: "Repositories" },
  { to: "/memory", icon: Brain, label: "Memory" },
];

export default function Sidebar() {
  return (
    <aside className="w-56 shrink-0 h-screen sticky top-0 flex flex-col bg-bg-secondary border-r border-border">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-border">
        <div className="flex items-center gap-2">
          <Activity className="w-6 h-6 text-cyan" />
          <span className="font-mono font-bold text-lg text-text-primary tracking-tight">
            RepoMemory
          </span>
        </div>
        <p className="text-[11px] text-text-dim mt-1 font-mono">
          local code retrieval engine
        </p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-1">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 ${
                isActive
                  ? "bg-cyan/10 text-cyan border border-cyan/20"
                  : "text-text-secondary hover:bg-bg-hover hover:text-text-primary border border-transparent"
              }`
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-border">
        <a
          href="https://github.com"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 text-text-dim hover:text-text-secondary text-xs transition-colors"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          <span>v0.1.0</span>
        </a>
      </div>
    </aside>
  );
}
