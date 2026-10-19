import { Home, Info, LockKeyhole, MessageSquareText, Settings, X } from "lucide-react";
import { NavLink } from "react-router-dom";
import { Brand } from "../Brand";
import { cn } from "../../lib/utils";

const links = [
  { to: "/", label: "Home", icon: Home, end: true },
  { to: "/conversations", label: "Conversations", icon: MessageSquareText },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/about", label: "About", icon: Info },
];

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <aside className={cn("sidebar", open && "is-open")} aria-label="Primary navigation">
      <div>
        <div className="sidebar-brand"><Brand /><button className="sidebar-close" onClick={onClose} aria-label="Close navigation"><X /></button></div>
        <nav className="nav-list">
          {links.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} onClick={onClose} className={({ isActive }) => cn("nav-link", isActive && "active")}>
              <Icon aria-hidden="true" /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
      <div className="privacy-card"><LockKeyhole aria-hidden="true" /><div><strong>Private by design</strong><span>Your conversations stay on your system.</span></div></div>
    </aside>
  );
}
