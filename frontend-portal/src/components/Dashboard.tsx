import { useEffect, useState } from "react";
import apiClient from "../api/apiClient";
import type { DashboardSummaryResponse } from "../api/types";

export function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const fetchDashboardSummary = async () => {
      setLoading(true);
      setError(null);

      try {
        const { data } = await apiClient.get<DashboardSummaryResponse>(
          "/api/v1/neufin/dashboard-summary",
        );

        if (!isMounted) return;
        setSummary(data);
      } catch (err) {
        if (!isMounted) return;
        setError("Unable to load dashboard summary. Please try again.");
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchDashboardSummary();

    return () => {
      isMounted = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex items-center gap-3 text-sm font-mono text-gray-400">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-500 border-t-transparent" />
          <span>Loading dashboard…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-500/40 bg-red-500/5 px-4 py-3 text-sm font-mono text-red-300">
        {error}
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm font-mono text-gray-300">
        No dashboard data available yet.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Total Trade Volume */}
      <div className="rounded-lg border border-white/10 bg-[#0D1117] px-6 py-4">
        <div className="text-xs font-mono text-gray-500 mb-1">
          Total Trade Volume
        </div>
        <div className="text-3xl font-mono text-white">
          {summary.total_trade_volume.toLocaleString()}
        </div>
      </div>

      {/* Top Biases */}
      <div className="rounded-lg border border-white/10 bg-[#0D1117] px-6 py-4">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <div className="text-xs font-mono text-gray-500">
              Top Biases
            </div>
            <div className="text-[10px] font-mono text-gray-500">
              Ranked by frequency for this venture
            </div>
          </div>
        </div>

        {summary.top_biases.length === 0 ? (
          <div className="text-xs font-mono text-gray-500">
            No behavioral biases detected yet.
          </div>
        ) : (
          <ul className="space-y-2">
            {summary.top_biases.map((bias) => (
              <li
                key={bias.bias_name}
                className="flex items-center justify-between text-xs font-mono"
              >
                <span className="text-gray-200">{bias.bias_name}</span>
                <span className="text-gray-400">
                  {bias.frequency} trade{bias.frequency === 1 ? "" : "s"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

