import { cn } from "@/lib/utils";
import type { RunStatus } from "@/api/types";

const statusStyles: Record<RunStatus, string> = {
  PENDING:   "bg-yellow-100 text-yellow-800 border-yellow-200",
  RUNNING:   "bg-blue-100 text-blue-800 border-blue-200 animate-pulse",
  COMPLETED: "bg-green-100 text-green-800 border-green-200",
  FAILED:    "bg-red-100 text-red-800 border-red-200",
};

export function StatusBadge({ status }: { status: RunStatus }) {
  return (
    <span className={cn(
      "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border",
      statusStyles[status],
    )}>
      {status}
    </span>
  );
}
