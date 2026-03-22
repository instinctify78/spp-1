import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  unit?: string;
  className?: string;
}

export function StatCard({ label, value, unit, className }: StatCardProps) {
  return (
    <div className={cn(
      "rounded-lg border bg-card p-4 flex flex-col gap-1",
      className,
    )}>
      <span className="text-xs text-muted-foreground uppercase tracking-wide">{label}</span>
      <div className="flex items-baseline gap-1">
        <span className="text-2xl font-semibold tabular-nums">{value}</span>
        {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
      </div>
    </div>
  );
}
