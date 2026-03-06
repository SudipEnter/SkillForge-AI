"use client";

import { useState } from "react";
import {
  BookOpen, Zap, Clock, DollarSign,
  CheckCircle, Circle, ExternalLink, Loader2, Calendar
} from "lucide-react";

interface Resource {
  title: string;
  provider: string;
  url: string;
  duration_hours: number;
  cost_usd: number;
  type: "course" | "project" | "reading";
}

interface Week {
  week_number: number;
  theme: string;
  resources: Resource[];
  milestone: string;
}

interface LearningPathProps {
  userId: string;
  learningPath: Record<string, unknown> | null;
  onEnroll: () => Promise<void>;
}

export function LearningPath({ userId, learningPath, onEnroll }: LearningPathProps) {
  const [isEnrolling, setIsEnrolling] = useState(false);
  const [enrollComplete, setEnrollComplete] = useState(false);

  const handleEnroll = async () => {
    setIsEnrolling(true);
    await onEnroll();
    setIsEnrolling(false);
    setEnrollComplete(true);
  };

  if (!learningPath) {
    return (
      <div className="glass-card p-8 text-center">
        <BookOpen className="w-12 h-12 text-blue-400 mx-auto mb-4 opacity-60" />
        <h3 className="font-bold text-lg mb-2">No Learning Path Yet</h3>
        <p className="text-gray-500 text-sm max-w-sm mx-auto">
          Complete a voice coaching session to get your personalized week-by-week learning plan.
        </p>
      </div>
    );
  }

  const weeks = (learningPath.weeks as Week[]) ?? [];
  const totalWeeks = (learningPath.total_weeks as number) ?? weeks.length;
  const totalCost = (learningPath.total_cost_usd as number) ?? 0;
  const salaryIncrease = (learningPath.estimated_salary_increase as number) ?? 0;
  const weeklyHours = (learningPath.weekly_time_commitment_hours as number) ?? 0;
  const summary = (learningPath.path_summary as string) ?? "";

  return (
    <div className="space-y-4">
      {/* Path Summary Card */}
      <div className="glass-card p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="font-bold text-lg">Your Learning Path</h3>
            <p className="text-gray-500 text-sm mt-1">{summary}</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-5">
          {[
            { label: "Duration",       value: `${totalWeeks} weeks`,        icon: Clock,       color: "text-purple-400" },
            { label: "Weekly Commitment", value: `${weeklyHours}h/week`,    icon: BookOpen,    color: "text-blue-400" },
            { label: "Total Cost",     value: `$${totalCost.toFixed(0)}`,   icon: DollarSign,  color: "text-teal-400" },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="bg-white/5 rounded-xl p-3 text-center">
              <Icon className={`w-4 h-4 ${color} mx-auto mb-1`} />
              <div className="text-sm font-bold text-white">{value}</div>
              <div className="text-xs text-gray-600">{label}</div>
            </div>
          ))}
        </div>

        {salaryIncrease > 0 && (
          <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-3 mb-5 flex items-center gap-3">
            <span className="text-green-400 text-2xl font-black">
              +${salaryIncrease.toLocaleString()}
            </span>
            <span className="text-green-300/70 text-sm">estimated annual salary increase</span>
          </div>
        )}

        <button
          onClick={handleEnroll}
          disabled={isEnrolling || enrollComplete}
          className={`w-full flex items-center justify-center gap-2 font-bold py-3 rounded-xl transition-all ${
            enrollComplete
              ? "bg-green-600/20 border border-green-600/30 text-green-400 cursor-default"
              : "bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white hover:-translate-y-0.5 shadow-lg shadow-purple-500/20"
          } disabled:opacity-60`}
        >
          {isEnrolling ? (
            <><Loader2 className="w-4 h-4 animate-spin" />Nova Act enrolling you...</>
          ) : enrollComplete ? (
            <><CheckCircle className="w-4 h-4" />Enrollment Triggered!</>
          ) : (
            <><Zap className="w-4 h-4" />Auto-Enroll All Courses via Nova Act</>
          )}
        </button>
      </div>

      {/* Weekly Timeline */}
      {weeks.length > 0 && (
        <div className="glass-card p-6">
          <h4 className="font-semibold text-sm mb-5 flex items-center gap-2">
            <Calendar className="w-4 h-4 text-purple-400" />
            Week-by-Week Plan
          </h4>
          <div className="space-y-4">
            {weeks.map((week, i) => (
              <div key={i} className="relative pl-8">
                {/* Timeline connector */}
                {i < weeks.length - 1 && (
                  <div className="absolute left-3.5 top-7 bottom-0 w-px bg-white/5" />
                )}
                {/* Week dot */}
                <div className="absolute left-0 top-1 w-7 h-7 rounded-full bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-xs font-bold text-purple-400">
                  {week.week_number}
                </div>

                <div className="bg-white/3 hover:bg-white/6 rounded-xl p-4 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <h5 className="font-semibold text-sm text-white">{week.theme}</h5>
                    <span className="text-xs text-gray-600">{week.resources?.length ?? 0} resources</span>
                  </div>

                  {week.milestone && (
                    <p className="text-xs text-purple-300/70 mb-3 flex items-center gap-1.5">
                      <CheckCircle className="w-3 h-3" />
                      {week.milestone}
                    </p>
                  )}

                  <div className="space-y-2">
                    {(week.resources ?? []).slice(0, 3).map((r, j) => (
                      <a
                        key={j}
                        href={r.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-between text-xs text-gray-500 hover:text-gray-300 group transition-colors"
                      >
                        <span className="flex items-center gap-1.5 truncate">
                          <Circle className="w-2.5 h-2.5 flex-shrink-0 text-gray-700" />
                          <span className="truncate">{r.title}</span>
                        </span>
                        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                          <span className="text-gray-600">{r.duration_hours}h</span>
                          <span>{r.cost_usd === 0 ? "Free" : `$${r.cost_usd}`}</span>
                          <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100" />
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}