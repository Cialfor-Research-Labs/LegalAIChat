import React, { useCallback, useEffect, useRef, useState } from 'react';
import { requestWithFallback } from './experimental-chat/api';

interface UsageStats {
  tokens_used: number;
  daily_limit: number;
  tokens_remaining: number;
  cooldown_until: string | null;
  cooldown_remaining_seconds: number;
  cooldown_hours: number;
  reset_at: string;
}

interface TokenUsageBadgeProps {
  authToken: string;
  /** Increment version to force an immediate re-fetch (e.g. after an LLM call). */
  refreshKey?: number;
}

function formatCountdown(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

const POLL_INTERVAL_MS = 30_000; // passive re-fetch every 30 s

export const TokenUsageBadge: React.FC<TokenUsageBadgeProps> = ({ authToken, refreshKey }) => {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [countdown, setCountdown] = useState(0);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      const data = await requestWithFallback<UsageStats>('/usage/stats', () => ({
        method: 'GET',
        headers: { Authorization: `Bearer ${authToken}` },
      }));
      setStats(data);
      setCountdown(data.cooldown_remaining_seconds ?? 0);
    } catch {
      // silently ignore — badge is non-critical
    }
  }, [authToken]);

  // Fetch on mount and whenever refreshKey changes (after an LLM call)
  useEffect(() => {
    void fetchStats();
  }, [fetchStats, refreshKey]);

  // Passive poll every 30 s
  useEffect(() => {
    pollRef.current = setInterval(() => void fetchStats(), POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchStats]);

  // Live countdown tick — 1 s interval while cooldown is active
  useEffect(() => {
    if (tickRef.current) clearInterval(tickRef.current);

    if (countdown > 0) {
      tickRef.current = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            // Cooldown just expired — re-fetch to get fresh stats
            clearInterval(tickRef.current!);
            void fetchStats();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
    };
  }, [countdown, fetchStats]);

  if (!stats) return null;

  const usedPct = Math.min(100, (stats.tokens_used / stats.daily_limit) * 100);
  const inCooldown = countdown > 0;
  const almostFull = usedPct >= 80 && !inCooldown;

  // colour scheme
  const barColor = inCooldown
    ? 'bg-red-500'
    : usedPct >= 80
    ? 'bg-amber-400'
    : 'bg-primary';

  const labelColor = inCooldown
    ? 'text-red-400'
    : usedPct >= 80
    ? 'text-amber-400'
    : 'text-on-surface-variant';

  return (
    <div className="hidden md:flex items-center gap-3 px-3">
      {/* Token bar */}
      <div className="flex flex-col items-end gap-1 min-w-[140px]">
        <div className="flex items-center justify-between w-full gap-2">
          <span className={`text-[10px] font-medium ${labelColor}`}>
            {inCooldown ? 'Cooldown active' : almostFull ? 'Limit near' : 'Daily tokens'}
          </span>
          <span className={`text-[10px] tabular-nums ${labelColor}`}>
            {stats.tokens_used.toLocaleString()} / {stats.daily_limit.toLocaleString()}
          </span>
        </div>
        <div className="w-full h-1.5 rounded-full bg-outline-variant/30 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${usedPct}%` }}
          />
        </div>
      </div>

      {/* Countdown — only visible during cooldown */}
      {inCooldown && (
        <div className="flex flex-col items-center gap-0.5">
          <span className="text-[9px] font-semibold uppercase tracking-widest text-red-400/80">
            Resets in
          </span>
          <span className="text-sm font-mono font-bold text-red-400 tabular-nums leading-none">
            {formatCountdown(countdown)}
          </span>
        </div>
      )}
    </div>
  );
};

export default TokenUsageBadge;
