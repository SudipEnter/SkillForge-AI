"use client";

import { Target, ArrowUpRight } from "lucide-react";

interface CareerReadinessProps {
  score: number;
  targetRole: string;
  stage: string;
  className?: string;
}

const STAGE_LABELS: Record<string, string> = {
  onboarding: "Getting Started",
  coaching_complete: "Coaching Done",
  gap_analysis_complete: "Analysis Done",
  learning_path_active: "Learning Active",
  enrolled: "Enrolled",
  certifying: "Certifying",
  job_hunting: "Job Hunting",
  placed: "🎉 Placed!",
};

export function CareerReadiness({ score, targetRole, stage, className = "" }: CareerReadinessProps) {
  const clampedScore = Math.min(100, Math.max(0, score));
  const scoreColor =
    clampedScore >= 75 ? "#22c55e" :
    clampedScore >= 50 ? "#eab308" :
    "#ef4444";

  // SVG circle progress
  const r = 28;
  const circumference = 2 * Math.PI * r;
  const dashOffset = circumference * (1 - clampedScore / 100);

  return (
    <div className={`glass-card p-5 ${className}`}>
      <div className="flex items-center gap-5">
        {/* Circular Progress */}
        <div className="relative flex-shrink-0">
          <svg width="72" height="72" className="-rotate-90">
            <circle cx="36" cy="36" r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="6" />
            <circle
              cx="36" cy="36" r={r}
              fill="none"
              stroke={scoreColor}
              strokeWidth="6"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              strokeLinecap="round"
              style={{ transition: "stroke-dashoffset 1s ease-in-out" }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-base font-black text-white">{clampedScore.toFixed(0)}%</span>
          </div>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Target className="w-4 h-4 text-purple-400 flex-shrink-0" />
            <span className="text-sm font-bold text-white truncate">{targetRole}</span>
          </div>
          <p className="text-xs text-gray-500 mb-2">Career Readiness Score</p>
          <div className="flex items-center gap-2">
            <span className="text-xs bg-white/5 border border-white/10 px-2.5 py-1 rounded-full text-gray-400">
              {STAGE_LABELS[stage] ?? stage}
            </span>
            {clampedScore > 0 && (
              <span
                className="text-xs font-medium flex items-center gap-1"
                style={{ color: scoreColor }}
              >
                <ArrowUpRight className="w-3 h-3" />
                {clampedScore >= 75 ? "Job Ready" :
                 clampedScore >= 50 ? "On Track" : "Needs Work"}
              </span>
            )}
          </div>
        </div>

        {/* Gradient bar */}
        <div className="hidden sm:block w-24">
          <div className="w-full bg-gray-800 rounded-full h-1.5 mb-1">
            <div
              className="h-1.5 rounded-full transition-all duration-700"
              style={{ width: `${clampedScore}%`, backgroundColor: scoreColor }}
            />
          </div>
          <p className="text-xs text-gray-600 text-right">{clampedScore.toFixed(0)} / 100</p>
        </div>
      </div>
    </div>
  );
}