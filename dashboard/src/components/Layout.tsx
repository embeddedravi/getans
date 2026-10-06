import { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

interface LayoutProps {
  title: string;
  children: ReactNode;
}

export function Layout({ title, children }: LayoutProps) {
  return (
    <div className="drawer lg:drawer-open h-dvh bg-base-100">
      <input id="dashboard-drawer-toggle" type="checkbox" className="drawer-toggle" />
      <div className="drawer-content flex min-w-0 flex-col overflow-hidden">
        <TopBar title={title} />
        <main className="min-w-0 flex-1 overflow-auto p-3 sm:p-5 lg:p-6">{children}</main>
      </div>
      <div className="drawer-side z-40">
        <label htmlFor="dashboard-drawer-toggle" aria-label="Close navigation" className="drawer-overlay" />
        <Sidebar />
      </div>
    </div>
  );
}
