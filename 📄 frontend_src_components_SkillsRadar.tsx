"use client";

import { useState } from "react";
import { Brain, AlertTriangle, TrendingUp, Loader2, Search } from "lucide-react";

interface SkillsRadarProps {
  userId: string;
  gapReport: Record<string, unknown> | null;
  targetRole: string;
  onAnalyze: () => void;
}

interface SkillGapItem {
  skill: string;
  current_level: number;
  required_level: number;
  gap_severity: "critical" | "moderate" | "minor";
  salary_impact_usd: number;
}

export function SkillsRadar({ userId, gapReport, targetRole, onAnalyze }: SkillsRadarProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    await onAnalyze();
    setIsAnalyzing(false);
  };

  const urgentGaps: SkillGapItem[] = (gapReport?.urgent_gaps as SkillGapItem[]) ?? [];
  const score = (gapReport?.career_readiness_score as number) ?? 0;
  const summary = (gapReport?.gap_summary as string) ?? "";

  const severityColor = {
    critical: "text-red-400 bg-red-500/10 border-red-500/20",
    moderate: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
    minor:    "text-blue-400 bg-blue-500/10 border-blue-500/20",
  };

  if (!gapReport) {
    return (
      <div className="glass-card p-8 text-center">
        <Brain className="w-12 h-12 text-purple-400 mx-auto mb-4 opacity-60" />
        <h3 className="font-bold text-lg mb-2">No Skills Analysis Yet</h3>
        <p className="text-gray-500 text-sm mb-6 max-w-sm mx-auto">
          Complete a voice coaching session first, or manually trigger a skills gap analysis.
        </p>
        <button
          onClick={handleAnalyze}
          disabled={isAnalyzing}
          className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white font-semibold px-6 py-3 rounded-xl transition-colors disabled:opacity-50"
        >
          {isAnalyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          {isAnalyzing ? "Analyzing..." : "Run Skills Analysis"}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary Header */}
      <div className="glass-card p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="font-bold text-lg">Skills Gap Analysis</h3>
            <p className="text-gray-500 text-sm">Target: {targetRole}</p>
          </div>
          <div className="text-right">
            <div
              className={`text-3xl font-black ${
                score >= 75 ? "text-green-400" : score >= 50 ? "text-yellow-400" : "text-red-400"
              }`}
            >
              {score.toFixed(0)}%
            </div>
            <div className="text-xs text-gray-500">Career Readiness</div>
          </div>
        </div>

        {/* Readiness Bar */}
        <div className="w-full bg-gray-800 rounded-full h-2.5 mb-4">
          <div
            className={`h-2.5 rounded-full transition-all duration-700 ${
              score >= 75 ? "bg-green-500" : score >= 50 ? "bg-yellow-500" : "bg-red-500"
            }`}
            style={{ width: `${score}%` }}
          />
        </div>

        {summary && (
          <p className="text-sm text-gray-400 leading-relaxed">{summary}</p>
        )}
      </div>

      {/* Skills Gap Grid */}
      {urgentGaps.length > 0 && (
        <div className="glass-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-yellow-400" />
            <h4 className="font-semibold text-sm">Priority Skill Gaps</h4>
            <span className="ml-auto text-xs text-gray-500">{urgentGaps.length} gaps identified</span>
          </div>

          <div className="space-y-3">
            {urgentGaps.map((gap, i) => (
              <div key={i} className="group">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-200">{gap.skill}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${severityColor[gap.gap_severity]}`}>
                      {gap.gap_severity}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500">
                    +${gap.salary_impact_usd?.toLocaleString() ?? 0}/yr
                  </span>
                </div>

                {/* Gap progress bar */}
                <div className="relative w-full bg-gray-800 rounded-full h-2">
                  {/* Required level (background) */}
                  <div
                    className="absolute h-2 rounded-full bg-gray-700"
                    style={{ width: `${(gap.required_level / 5) * 100}%` }}
                  />
                  {/* Current level */}
                  <div
                    className="absolute h-2 rounded-full bg-purple-500 transition-all duration-500"
                    style={{ width: `${(gap.current_level / 5) * 100}%` }}
                  />
                </div>

                <div className="flex justify-between text-xs text-gray-600 mt-1">
                  <span>Current: {gap.current_level}/5</span>
                  <span>Required: {gap.required_level}/5</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Salary Impact Summary */}
      {urgentGaps.length > 0 && (
        <div className="glass-card p-5 flex items-center gap-4">
          <div className="w-10 h-10 bg-teal-500/20 rounded-xl flex items-center justify-center flex-shrink-0">
            <TrendingUp className="w-5 h-5 text-teal-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">
              Total Salary Uplift Potential
            </p>
            <p className="text-2xl font-black text-teal-400">
              +${urgentGaps.reduce((sum, g) => sum + (g.salary_impact_usd ?? 0), 0).toLocaleString()}
              <span className="text-sm font-normal text-gray-500">/year</span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}