"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Brain, Mic, Zap, TrendingUp, BookOpen,
  ArrowRight, Star, Shield, Clock
} from "lucide-react";

export default function LandingPage() {
  const router = useRouter();
  const [isStarting, setIsStarting] = useState(false);

  const handleStart = async () => {
    setIsStarting(true);
    // In production: auth flow here
    const demoUserId = `demo_${Date.now()}`;
    localStorage.setItem("skillforge_user_id", demoUserId);
    router.push("/dashboard");
  };

  return (
    <main className="min-h-screen bg-gray-950 overflow-hidden">
      {/* Animated background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-purple-600/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-blue-600/20 rounded-full blur-3xl animate-pulse delay-1000" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-teal-600/10 rounded-full blur-3xl animate-pulse delay-500" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-6">
        {/* Header */}
        <nav className="flex items-center justify-between py-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 nova-gradient rounded-xl flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold">SkillForge AI</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500 bg-white/5 px-3 py-1.5 rounded-full border border-white/10">
            <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
            Powered by Amazon Nova
          </div>
        </nav>

        {/* Hero */}
        <div className="text-center pt-20 pb-16">
          <div className="inline-flex items-center gap-2 bg-purple-500/10 border border-purple-500/30 text-purple-300 text-sm px-4 py-2 rounded-full mb-8">
            <Zap className="w-4 h-4" />
            Amazon Nova AI Hackathon Submission
          </div>

          <h1 className="text-6xl md:text-7xl font-black mb-6 leading-none">
            Your Career,{" "}
            <span className="bg-gradient-to-r from-purple-400 via-blue-400 to-teal-400 bg-clip-text text-transparent">
              Autonomously
            </span>
            <br />
            Reskilled.
          </h1>

          <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-12 leading-relaxed">
            Speak to an AI coach powered by{" "}
            <strong className="text-white">Amazon Nova 2 Sonic</strong>. 
            Get your skills gap analyzed by{" "}
            <strong className="text-white">Nova 2 Lite agents</strong>. 
            Watch{" "}
            <strong className="text-white">Nova Act</strong> enroll you in the 
            right courses — automatically.
          </p>

          <button
            onClick={handleStart}
            disabled={isStarting}
            className="group inline-flex items-center gap-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white font-bold text-lg px-10 py-5 rounded-2xl transition-all duration-300 shadow-2xl shadow-purple-500/25 hover:shadow-purple-500/40 hover:-translate-y-1 disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {isStarting ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Initializing...
              </>
            ) : (
              <>
                <Mic className="w-5 h-5" />
                Start Career Coaching Session
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </button>

          <p className="text-gray-600 text-sm mt-4">
            Free 15-minute AI coaching session · No account required
          </p>
        </div>

        {/* Nova Model Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-20">
          {[
            {
              icon: Mic,
              label: "Nova 2 Sonic",
              desc: "Real-time voice coaching",
              color: "purple",
            },
            {
              icon: Brain,
              label: "Nova 2 Lite",
              desc: "Skills gap reasoning agents",
              color: "blue",
            },
            {
              icon: TrendingUp,
              label: "Nova Embeddings",
              desc: "Multimodal skills matching",
              color: "teal",
            },
            {
              icon: Zap,
              label: "Nova Act",
              desc: "Autonomous enrollment",
              color: "green",
            },
          ].map(({ icon: Icon, label, desc, color }) => (
            <div key={label} className="glass-card p-4 text-center hover:bg-white/10 transition-colors">
              <div
                className={`w-10 h-10 bg-${color}-500/20 rounded-xl flex items-center justify-center mx-auto mb-3`}
              >
                <Icon className={`w-5 h-5 text-${color}-400`} />
              </div>
              <div className="text-sm font-semibold text-white">{label}</div>
              <div className="text-xs text-gray-500 mt-1">{desc}</div>
            </div>
          ))}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-8 pb-20 text-center">
          {[
            { value: "85M+",