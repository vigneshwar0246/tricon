import { Menu } from "lucide-react";
import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Brand } from "../Brand";
import { Sidebar } from "./Sidebar";

export function AppLayout() {
  const [open, setOpen] = useState(false);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="mobile-header">
        <Brand />
        <button className="mobile-menu" onClick={() => setOpen(true)} aria-label="Open navigation" aria-expanded={open}><Menu /></button>
      </header>
      <Sidebar open={open} onClose={() => setOpen(false)} />
      {open && <button className="sidebar-scrim" onClick={() => setOpen(false)} aria-label="Close navigation" />}
      <main id="main-content"><Outlet /></main>
    </div>
  );
}
