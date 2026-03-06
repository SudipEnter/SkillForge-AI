/**
 * SkillForge AI — API Client
 * Typed client for all backend REST endpoints.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? "Request failed");
  }

  return res.json() as Promise<T>;
}

export const api = {
  // ── Coaching ────────────────────────────────────────────────────
  startCoaching: (userId: string, targetRole?: string) =>
    request<{ session_id: string; ws_url: string }>("/coaching/start", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, target_role: targetRole }),
    }),

  completeCoaching: (data: {
    userId: string;
    sessionId: string;
    coachingProfile: Record<string, unknown>;
    targetRole?: string;
  }) =>
    request("/coaching/complete", {
      method: "POST",
      body: JSON.stringify({
        session_id: data.sessionId,
        user_id: data.userId,
        coaching_profile: data.coachingProfile,
        target_role: data.targetRole,
      }),
    }),

  getCoachingHistory: (userId: string) =>
    request<{ sessions: unknown[] }>(`/coaching/history/${userId}`),

  // ── Skills ──────────────────────────────────────────────────────
  getSkillsProfile: (userId: string) =>
    request<Record<string, unknown>>(`/skills/${userId}`),

  analyzeSkills: (data: {
    userId: string;
    skillsProfile: Record<string, unknown>;
    targetRole: string;
    targetLocation?: string;
  }) =>
    request("/skills/analyze", {
      method: "POST",
      body: JSON.stringify({
        user_id: data.userId,
        skills_profile: data.skillsProfile,
        target_role: data.targetRole,
        target_location: data.targetLocation ?? "United States",
      }),
    }),

  analyzePortfolio: (data: {
    userId: string;
    githubUrl?: string;
    resumeBase64?: string;
  }) =>
    request("/skills/portfolio/analyze", {
      method: "POST",
      body: JSON.stringify({
        user_id: data.userId,
        github_url: data.githubUrl,
        resume_base64: data.resumeBase64,
      }),
    }),

  getRoleSkills: (role: string) =>
    request<{ role: string; skills: unknown[] }>(`/skills/graph/roles/${encodeURIComponent(role)}`),

  // ── Learning ────────────────────────────────────────────────────
  getLearningPath: (userId: string) =>
    request<Record<string, unknown>>(`/learning/${userId}/path`),

  buildLearningPath: (data: {
    userId: string;
    targetRole: string;
    weeklyHours?: number;
    weeklyBudgetUsd?: number;
  }) =>
    request("/learning/build", {
      method: "POST",
      body: JSON.stringify({
        user_id: data.userId,
        target_role: data.targetRole,
        weekly_hours: data.weeklyHours ?? 12,
        weekly_budget_usd: data.weeklyBudgetUsd ?? 50,
      }),
    }),

  triggerEnrollment: (data: { userId: string; autoApproveUnder?: number }) =>
    request("/learning/enroll", {
      method: "POST",
      body: JSON.stringify({
        user_id: data.userId,
        auto_approve_under_usd: data.autoApproveUnder ?? 25,
      }),
    }),

  syncCalendar: (userId: string) =>
    request("/learning/calendar/sync", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),

  // ── Jobs ────────────────────────────────────────────────────────
  getJobMarket: (userId: string, role: string, location?: string, company?: string) => {
    const params = new URLSearchParams({ role });
    if (location) params.set("location", location);
    if (company) params.set("company", company);
    return request<Record<string, unknown>>(`/jobs/${userId}/market?${params}`);
  },

  searchJobs: (data: {
    userId: string;
    targetRole: string;
    location?: string;
    remoteOnly?: boolean;
    minSalary?: number;
  }) =>
    request("/jobs/search", {
      method: "POST",
      body: JSON.stringify({
        user_id: data.userId,
        target_role: data.targetRole,
        location: data.location ?? "United States",
        remote_only: data.remoteOnly ?? false,
        min_salary: data.minSalary ?? 0,
      }),
    }),

  getSkillsVelocity: (skills: string[], role: string) => {
    const params = new URLSearchParams({ skills: skills.join(","), role });
    return request<{ skills_velocity: unknown[] }>(`/jobs/skills/velocity?${params}`);
  },
};