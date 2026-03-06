"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Brain, Mic, Zap, TrendingUp, BookOpen,
  ArrowRight, Users, Award, Clock, CheckCircle
} from "lucide-react";

const NOVA_MODELS = [
  { icon: Mic,        label: "Nova 2 Sonic",     desc: "Real-time voice coaching",         color: "purple" },
  { icon: Brain,      label: "Nova 2 Lite",       desc: "Agentic skills gap reasoning",      color: "blue"   },
  { icon: TrendingUp, label: "Nova Embeddings",   desc: "Multimodal portfolio matching",     color: "teal"   },
  { icon: Zap,        label: "Nova Act",           desc: "Autonomous course enrollment",      color: "green"  },
];

const FEATURES = [
  {
    icon: Mic,
    title: "Voice-First Career Coaching",
    desc: "Speak naturally with an AI coach powered by Amazon Nova 2 Sonic. It listens, understands your career history, and asks the right follow-up questions — all in real time.",
  },
  {
    icon: Brain,
    title: "Autonomous Skills Gap Analysis",
    desc: "Nova 2 Lite agents compare your profile against live job market data using multimodal embeddings to produce a precise, ranked skills gap report with salary impact projections.",
  },
  {
    icon: BookOpen,
    title: "Personalized Learning Paths",
    desc: "A week-by-week learning plan built around your schedule, budget, and goals — curated from 50,000+ courses across Coursera, Udemy, AWS Training, and more.",
  },
  {
    icon: Zap,
    title: "Nova Act Auto-Enrollment",
    desc: "Nova Act agents browse course platforms, complete registration forms, and enroll you automatically — no copy-paste, no tab-switching, no friction.",
  },
];

const STATS = [
  { value: "85M+", label: "Workers facing reskilling need", icon: Users },
  { value: "12 wk", label: "Avg. time from gap to job-ready", icon: Clock },
  { value: "4 Nova", label: "Models working in concert", icon: Award },
  { value: "5 AWS", label: "Hackathon categories covered", icon: CheckCircle },
];

export default function LandingPage() {
  const router = useRouter();
  const [isStarting, setIsStarting] = useState(false);

  const handleStart = () => {
    setIsStarting(true);
    const demoUserId = `demo_${Date.now()}`;
    localStorage.setItem("skillforge_user_id", demoUserId);
    localStorage.setItem("skillforge_user_name", "Demo Learner");
    router.push("/dashboard");
  };

  return (
    <main className="min-h-screen bg-gray-950 overflow-hidden">
      {/* Ambient background glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-60 -right-60 w-[600px] h-[600px] bg-purple-600/15 rounded-full blur-3xl animate-pulse" />
        <div className="absolute -bottom-60 -left-60 w-[600px] h-[600px] bg-blue-600/15 rounded-full blur-3xl animate-pulse delay-700" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-6">
        {/* Nav */}
        <nav className="flex items-center justify-between py-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-gradient-to-br from-purple-600 to-blue-600">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight">SkillForge AI</span>
          </div>
          <div className="hidden md:flex items-center gap-6 text-sm text-gray-400">
            <span>Agentic AI</span>
            <span>Voice AI</span>
            <span>UI Automation</span>
            <div className="h-4 w-px bg-gray-700" />
            <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 px-3 py-1.5 rounded-full text-xs font-medium">
              <span className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse" />
              Amazon Nova AI Hackathon
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <section className="text-center pt-16 pb-14">
          <div className="inline-flex items-center gap-2 bg-purple-500/10 border border-purple-500/25 text-purple-300 text-xs font-medium px-4 py-2 rounded-full mb-8">
            <Zap className="w-3.5 h-3.5" />
            Powered by Amazon Nova 2 Sonic · Nova 2 Lite · Nova Embeddings · Nova Act
          </div>

          <h1 className="text-5xl md:text-7xl font-black mb-6 leading-none tracking-tight">
            Reskill 85 Million{" "}
            <span className="bg-gradient-to-r from-purple-400 via-blue-400 to-teal-400 bg-clip-text text-transparent">
              Workers.
            </span>
            <br />
            <span className="text-4xl md:text-6xl font-black text-gray-300">
              Autonomously.
            </span>
          </h1>

          <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Talk to an AI career coach. Get your skills gaps mapped to live job market data.
            Watch Nova Act enroll you in the right courses — completely automatically.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={handleStart}
              disabled={isStarting}
              className="group flex items-center gap-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white font-bold text-lg px-10 py-4 rounded-2xl transition-all duration-200 shadow-xl shadow-purple-500/20 hover:shadow-purple-500/40 hover:-translate-y-0.5 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isStarting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Initializing Nova 2 Sonic...
                </>
              ) : (
                <>
                  <Mic className="w-5 h-5" />
                  Start Free Coaching Session
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
            <a
              href="https://github.com/SudipEnter/SkillForge-AI"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 border border-white/10 hover:border-white/25 text-gray-400 hover:text-white px-6 py-4 rounded-2xl transition-all duration-200 text-sm font-medium"
            >
              View Source on GitHub
            </a>
          </div>
          <p className="text-gray-600 text-xs mt-4">
            No account required · Free demo · Built for Amazon Nova AI Hackathon
          </p>
        </section>

        {/* Nova Models Grid */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-20">
          {NOVA_MODELS.map(({ icon: Icon, label, desc }) => (
            <div
              key={label}
              className="glass-card p-5 text-center group hover:bg-white/10 transition-all duration-200 hover:-translate-y-0.5"
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600/30 to-blue-600/30 flex items-center justify-center mx-auto mb-3 group-hover:scale-110 transition-transform">
                <Icon className="w-5 h-5 text-purple-300" />
              </div>
              <p className="text-sm font-semibold text-white">{label}</p>
              <p className="text-xs text-gray-500 mt-1">{desc}</p>
            </div>
          ))}
        </section>

        {/* Stats */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-24">
          {STATS.map(({ value, label, icon: Icon }) => (
            <div key={label} className="text-center">
              <Icon className="w-5 h-5 text-purple-400 mx-auto mb-2 opacity-70" />
              <p className="text-3xl font-black text-white">{value}</p>
              <p className="text-xs text-gray-500 mt-1">{label}</p>
            </div>
          ))}
        </section>

        {/* Features */}
        <section className="mb-24">
          <h2 className="text-3xl font-black text-center mb-12">
            Every{" "}
            <span className="bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
              Amazon Nova model
            </span>{" "}
            in your corner
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <div
                key={title}
                className="glass-card p-6 hover:bg-white/10 transition-all duration-200 group"
              >
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                    <Icon className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <h3 className="font-bold text-white mb-2">{title}</h3>
                    <p className="text-sm text-gray-400 leading-relaxed">{desc}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Architecture Callout */}
        <section className="glass-card p-8 mb-24 text-center">
          <h3 className="text-xl font-bold mb-3">Multi-Agent Architecture</h3>
          <p className="text-gray-400 text-sm max-w-2xl mx-auto mb-6">
            SkillForge orchestrates 4 specialized Nova agents via AWS Strands Agents.
            Each agent operates autonomously, shares state through DynamoDB,
            and surfaces results in real time through WebSocket streams.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 text-xs font-mono">
            {["Nova 2 Sonic", "→", "Career Coach Agent", "→", "Skills Gap Agent", "→", "Learning Path Agent", "→", "Nova Act Enrollment"].map(
              (item, i) => (
                <span
                  key={i}
                  className={
                    item === "→"
                      ? "text-gray-600"
                      : "bg-white/5 border border-white/10 px-3 py-1.5 rounded-lg text-gray-300"
                  }
                >
                  {item}
                </span>
              )
            )}
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-white/5 py-8 text-center text-gray-600 text-xs">
          <p>
            SkillForge AI · Built for the{" "}
            <a
              href="https://amazon-nova.devpost.com"
              className="text-purple-400 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Amazon Nova AI Hackathon
            </a>{" "}
            · Amazon Nova Agentic AI + Voice AI + Multimodal + UI Automation
          </p>
        </footer>
      </div>
    </main>
  );
}