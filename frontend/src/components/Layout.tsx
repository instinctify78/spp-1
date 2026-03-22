import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";

export default function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b bg-card">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 font-semibold text-sm">
            <span className="text-lg">⚡</span>
            <span>SPP-1</span>
            <span className="text-muted-foreground font-normal">LLM GPU Dashboard</span>
          </Link>
          <nav className="flex items-center gap-1">
            <Link
              to="/"
              className={cn(
                "px-3 py-1.5 rounded-md text-sm transition-colors",
                pathname === "/" ? "bg-accent font-medium" : "text-muted-foreground hover:bg-accent/50",
              )}
            >
              Runs
            </Link>
            <Link
              to="/runs/new"
              className={cn(
                "px-3 py-1.5 rounded-md text-sm transition-colors",
                pathname === "/runs/new" ? "bg-accent font-medium" : "text-muted-foreground hover:bg-accent/50",
              )}
            >
              + New Run
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1">{children}</main>
    </div>
  );
}
