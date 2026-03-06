"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Brain, Mic, TrendingUp, BookOpen, Zap,
  RefreshCw, Bell, Settings, LogOut, ChevronRight,
  Loader2, AlertCircle
} from "lucide-react";
import { VoiceCoach } from "@/components/VoiceCoach";
import { CareerReadiness } from "@/components/CareerReadiness";
import { SkillsRadar } from "@/components/SkillsRadar";
import { LearningPath } from "@/components/LearningPath";
import { JobMarket } from "@/components/JobMarket";
import { api } from "@/lib/api";

type DashboardTab = "coach" | "skills" | "learning" | "jobs";

interface DashboardState {
  userId: string;
  stage: string;
  careerReadiness: number;
  targetRole: string;
  gapReport: Record<string, unknown> | null;
  learningPath: Record<string, unknown> | null;
  isLoading: boolean;
  error: string | null;
}

const TABS: { id: DashboardTab; label: string; icon: typeof Brain; description: string }[] = [
  { id: "coach",    label: "Voice Coach",     icon: Mic,        description: "Talk to your AI career coach" },
  { id: "skills",   label: "Skills Gap",      icon: Brain,      description: "Your personalized gap analysis" },
  { id: "learning", label: "Learning Path",   icon: BookOpen,   description: "Week-by-week learning plan" },
  { id: "jobs",     label: "Job Market",      icon: TrendingUp, description: "Real-time market intelligence" },
];

export default function DashboardPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<DashboardTab>("coach");
  const [state, setState] = useState<DashboardState>({
    userId: "",
    stage: "onboarding",
    careerReadiness: 0,
    targetRole: "Senior Data Engineer",
    gapReport: null,
    learningPath: null,
    isLoading: true,
    error: null,
  });

  const loadDashboard = useCallback(async (userId: string) => {
    try {
      setState(s => ({ ...s, isLoading: true, error: null }));

      const [profile, pathData] = await Promise.allSettled([
        api.getSkillsProfile(userId),
        api.getLearningPath(userId),
      ]);

      const profileData = profile.status === "fulfilled" ? profile.value : null;
      const pathResult  = pathData.status === "fulfilled" ? pathData.value : null;

      setState(s => ({
        ...s,
        stage: profileData?.stage ?? "onboarding",
        careerReadiness: profileData?.gap_report?.career_readiness_score ?? 0,
        targetRole: profileData?.gap_report?.target_role ?? "Senior Data Engineer",
        gapReport: profileData?.gap_report ?? null,
        learningPath: pathResult ?? null,
        isLoading: false,
      }));
    } catch {
      setState(s => ({ ...s, isLoading: false, error: "Failed to load dashboard data." }));
    }
  }, []);

  useEffect(() => {
    const userId = localStorage.getItem("skillforge_user_id");
    if (!userId) { router.push("/"); return; }
    setState(s => ({ ...s, userId }));
    loadDashboard(userId);
  }, [loadDashboard, router]);

  const handleCoachingComplete = async (profile: Record<string, unknown>) => {
    try {
      await api.completeCoaching({
        userId: state.userId,
        sessionId: `sf_${state.userId}_${Date.now()}`,
        coachingProfile: profile,
      });
      setTimeout(() => loadDashboard(state.userId), 2000);
      setActiveTab("skills");
    } catch (e) {
      console.error("Coaching completion failed", e);
    }
  };

  if (state.isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 text-purple-400 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading your career intelligence...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Top Nav */}
      <header className="border-b border-white/5 bg-gray-950/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gradient-to-br from-purple-600 to-blue-600">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-sm">SkillForge AI</span>
            <ChevronRight className="w-4 h-4 text-gray-600" />
            <span className="text-sm text-gray-400">Dashboard</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => loadDashboard(state.userId)}
              className="p-2 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-white/5 transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button className="p-2 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-white/5 transition-colors">
              <Bell className="w-4 h-4" />
            </button>
            <div className="w-px h-5 bg-gray-800 mx-1" />
            <button
              onClick={() => { localStorage.clear(); router.push("/"); }}
              className="p-2 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6 flex-1 w-full">
        {/* Career Readiness Banner */}
        {state.careerReadiness > 0 && (
          <CareerReadiness
            score={state.careerReadiness}
            targetRole={state.targetRole}
            stage={state.stage}
            className="mb-6"
          />
        )}

        {/* Error Banner */}
        {state.error && (
          <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-6 text-red-400 text-sm">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            {state.error}
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
          {TABS.map(({ id, label, icon: Icon, description }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
                activeTab === id
                  ? "bg-purple-600 text-white shadow-lg shadow-purple-500/25"
                  : "bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white border border-white/5"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2">
            {activeTab === "coach" && (
              <VoiceCoach
                userId={state.userId}
                onCoachingComplete={handleCoachingComplete}
              />
            )}
            {activeTab === "skills" && (
              <SkillsRadar
                userId={state.userId}
                gapReport={state.gapReport}
                targetRole={state.targetRole}
                onAnalyze={() => loadDashboard(state.userId)}
              />
            )}
            {activeTab === "learning" && (
              <LearningPath
                userId={state.userId}
                learningPath={state.learningPath}
                onEnroll={() => api.triggerEnrollment({ userId: state.userId })}
              />
            )}
            {activeTab === "jobs" && (
              <JobMarket
                userId={state.userId}
                targetRole={state.targetRole}
              />
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Journey Stage Card */}
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
                <Zap className="w-4 h-4 text-purple-400" />
                Your Journey
              </h3>
              <div className="space-y-3">
                {[
                  { label: "Voice Coaching",   done: state.stage !== "onboarding" },
                  { label: "Skills Analysis",  done: !!state.gapReport },
                  { label: "Learning Path",    done: !!state.learningPath },
                  { label: "Enrolled",         done: state.stage === "enrolled" || state.stage === "certifying" },
                  { label: "Job Applications", done: state.stage === "job_hunting" || state.stage === "placed" },
                ].map(({ label, done }) => (
                  <div key={label} className="flex items-center gap-3 text-sm">
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
                      done ? "bg-green-500/20 text-green-400" : "bg-white/5 text-gray-600"
                    }`}>
                      {done ? "✓" : "·"}
                    </div>
                    <span className={done ? "text-gray-300" : "text-gray-600"}>{label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Nova Models Active */}
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-4">Nova Models Active</h3>
              <div className="space-y-3">
                {[
                  { model: "Nova 2 Sonic",   status: "active",  use: "Voice coaching" },
                  { model: "Nova 2 Lite",    status: "active",  use: "Gap analysis agents" },
                  { model: "Nova Embeddings",status: "active",  use: "Skills matching" },
                  { model: "Nova Act",       status: activeTab === "learning" ? "active" : "standby", use: "Enrollment" },
                ].map(({ model, status, use }) => (
                  <div key={model} className="flex items-center justify-between text-xs">
                    <div>
                      <p className="text-gray-300 font-medium">{model}</p>
                      <p className="text-gray-600">{use}</p>
                    </div>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      status === "active"
                        ? "bg-green-500/15 text-green-400"
                        : "bg-gray-500/15 text-gray-500"
                    }`}>
                      {status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Quick Actions</h3>
              <div className="space-y-2">
                <button
                  onClick={() => setActiveTab("coach")}
                  className="w-full flex items-center gap-2 text-sm text-gray-400 hover:text-white hover:bg-white/5 px-3 py-2 rounded-lg transition-colors text-left"
                >
                  <Mic className="w-4 h-4 text-purple-400" />
                  New coaching session
                </button>
                <button
                  onClick={() => { setActiveTab("learning"); api.triggerEnrollment({ userId: state.userId }); }}
                  className="w-full flex items-center gap-2 text-sm text-gray-400 hover:text-white hover:bg-white/5 px-3 py-2 rounded-lg transition-colors text-left"
                >
                  <Zap className="w-4 h-4 text-blue-400" />
                  Auto-enroll courses
                </button>
                <button
                  onClick={() => setActiveTab("jobs")}
                  className="w-full flex items-center gap-2 text-sm text-gray-400 hover:text-white hover:bg-white/5 px-3 py-2 rounded-lg transition-colors text-left"
                >
                  <TrendingUp className="w-4 h-4 text-teal-400" />
                  Explore job market
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}