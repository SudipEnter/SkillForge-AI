"use client";

import { useState, useEffect } from "react";
import {
  TrendingUp, TrendingDown, Minus, Building2,
  MapPin, DollarSign, Loader2, Wifi, Users
} from "lucide-react";
import { api } from "@/lib/api";

interface JobMarketProps {
  userId: string;
  targetRole: string;
}

interface MarketIntel {
  market_summary: string;
  demand_level: "low" | "moderate" | "high" | "critical";
  total_open_positions: number;
  avg_salary_usd: number;
  salary_range: { min: number; p50: number; p75: number; max: number };
  top_hiring_companies: { company: string; openings: number; is_remote: boolean }[];
  trending_skills: { skill: string; demand_change_pct: number; trend: string }[];
  remote_percentage: number;
  competition_level: string;
  insider_tip: string;
}

const DEMAND_CONFIG = {
  low:      { color: "text-gray-400",   bg: "bg-gray-500/10 border-gray-500/20",   label: "Low Demand" },
  moderate: { color: "text-yellow-400", bg: "bg-yellow-500/10 border-yellow-500/20", label: "Moderate Demand" },
  high:     { color: "text-green-400",  bg: "bg-green-500/10 border-green-500/20",  label: "High Demand" },
  critical: { color: "text-teal-400",   bg: "bg-teal-500/10 border-teal-500/20",    label: "Critical Demand" },
};

export function JobMarket({ userId, targetRole }: JobMarketProps) {
  const [intel, setIntel] = useState<MarketIntel | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchIntel = async () => {
    setIsLoading(true);
    try {
      const data = await api.getJobMarket(userId, targetRole);
      setIntel(data);
    } catch (e) {
      console.error("Job market fetch failed", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchIntel(); }, [userId, targetRole]);

  if (isLoading) {
    return (
      <div className="glass-card p-8 flex flex-col items-center justify-center gap-3 min-h-48">
        <Loader2 className="w-8 h-8 text-teal-400 animate-spin" />
        <p className="text-gray-500 text-sm">Nova 2 Lite analyzing job market...</p>
      </div>
    );
  }

  if (!intel) {
    return (
      <div className="glass-card p-8 text-center">
        <TrendingUp className="w-10 h-10 text-teal-400 mx-auto mb-3 opacity-50" />
        <p className="text-gray-500 text-sm">Market intelligence unavailable</p>
        <button onClick={fetchIntel} className="mt-3 text-sm text-teal-400 hover:underline">
          Retry
        </button>
      </div>
    );
  }

  const demand = DEMAND_CONFIG[intel.demand_level] ?? DEMAND_CONFIG.moderate;

  return (
    <div className="space-y-4">
      {/* Overview Card */}
      <div className="glass-card p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="font-bold text-lg">Job Market Intelligence</h3>
            <p className="text-gray-500 text-sm">{targetRole}</p>
          </div>
          <span className={`text-xs px-3 py-1.5 rounded-full border font-medium ${demand.bg} ${demand.color}`}>
            {demand.label}
          </span>
        </div>

        <p className="text-sm text-gray-400 leading-relaxed mb-5">{intel.market_summary}</p>

        <div className="grid grid-cols-3 gap-3">
          <div className="bg-white/5 rounded-xl p-3 text-center">
            <Users className="w-4 h-4 text-purple-400 mx-auto mb-1" />
            <div className="text-lg font-black text-white">
              {intel.total_open_positions.toLocaleString()}
            </div>
            <div className="text-xs text-gray-600">Open Positions</div>
          </div>
          <div className="bg-white/5 rounded-xl p-3 text-center">
            <DollarSign className="w-4 h-4 text-teal-400 mx-auto mb-1" />
            <div className="text-lg font-black text-white">
              ${Math.round(intel.avg_salary_usd / 1000)}k
            </div>
            <div className="text-xs text-gray-600">Avg Salary</div>
          </div>
          <div className="bg-white/5 rounded-xl p-3 text-center">
            <Wifi className="w-4 h-4 text-blue-400 mx-auto mb-1" />
            <div className="text-lg font-black text-white">{intel.remote_percentage.toFixed(0)}%</div>
            <div className="text-xs text-gray-600">Remote</div>
          </div>
        </div>
      </div>

      {/* Salary Range */}
      <div className="glass-card p-5">
        <h4 className="text-sm font-semibold mb-4">Salary Distribution</h4>
        <div className="flex items-end gap-1 h-16">
          {[
            { label: "Min",  value: intel.salary_range.min,  pct: 40 },
            { label: "P50",  value: intel.salary_range.p50,  pct: 70 },
            { label: "P75",  value: intel.salary_range.p75,  pct: 90 },
            { label: "Max",  value: intel.salary_range.max,  pct: 100 },
          ].map(({ label, value, pct }) => (
            <div key={label} className="flex-1 flex flex-col items-center gap-1">
              <span className="text-xs text-gray-500">${Math.round(value / 1000)}k</span>
              <div
                className="w-full bg-gradient-to-t from-purple-600 to-blue-500 rounded-t-md opacity-70 hover:opacity-100 transition-opacity"
                style={{ height: `${pct}%` }}
              />
              <span className="text-xs text-gray-600">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Top Hiring Companies */}
      {intel.top_hiring_companies?.length > 0 && (
        <div className="glass-card p-5">
          <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-blue-400" />
            Top Hiring Companies
          </h4>
          <div className="space-y-2">
            {intel.top_hiring_companies.slice(0, 5).map((co, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="text-gray-300">{co.company}</span>
                <div className="flex items-center gap-2">
                  {co.is_remote && (
                    <span className="text-xs bg-teal-500/10 text-teal-400 border border-teal-500/20 px-2 py-0.5 rounded-full">
                      Remote
                    </span>
                  )}
                  <span className="text-gray-500 text-xs">{co.openings} openings</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trending Skills */}
      {intel.trending_skills?.length > 0 && (
        <div className="glass-card p-5">
          <h4 className="text-sm font-semibold mb-3">Skills Velocity</h4>
          <div className="space-y-2">
            {intel.trending_skills.slice(0, 6).map((sk, i) => {
              const TrendIcon = sk.trend === "rising" ? TrendingUp : sk.trend === "declining" ? TrendingDown : Minus;
              const trendColor = sk.trend === "rising" ? "text-green-400" : sk.trend === "declining" ? "text-red-400" : "text-gray-400";
              return (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="text-gray-300">{sk.skill}</span>
                  <div className={`flex items-center gap-1.5 ${trendColor}`}>
                    <TrendIcon className="w-3.5 h-3.5" />
                    <span className="text-xs font-medium">
                      {sk.demand_change_pct > 0 ? "+" : ""}{sk.demand_change_pct?.toFixed(1)}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Insider Tip */}
      {intel.insider_tip && (
        <div className="bg-amber-500/5 border border-amber-500/15 rounded-xl p-4">
          <p className="text-xs font-semibold text-amber-400 mb-1">💡 Nova Insight</p>
          <p className="text-sm text-gray-400">{intel.insider_tip}</p>
        </div>
      )}
    </div>
  );
}