# 🎓 SkillForge AI
### Autonomous Workforce Reskilling & Career Intelligence Engine

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-orange.svg)](https://aws.amazon.com/bedrock)
[![Amazon Nova](https://img.shields.io/badge/Amazon-Nova-purple.svg)](https://amazon-nova.devpost.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Amazon Nova Hackathon](https://img.shields.io/badge/Hackathon-Amazon%20Nova-yellow.svg)](https://amazon-nova.devpost.com)

> Built for the **Amazon Nova AI Hackathon** — Category: **Agentic AI + Freestyle**
> Powered by Nova 2 Sonic · Nova 2 Lite · Nova Multimodal Embeddings · Nova Act

---

## 🚀 Overview

SkillForge AI is an autonomous career intelligence platform that guides professionals
through AI-driven reskilling with personalized voice coaching, semantic skills mapping,
and fully automated enrollment and job application workflows.

The global workforce reskilling market exceeds **$370B annually** and is in crisis:
85 million jobs are being displaced by AI while 97 million new roles demand skills
that don't yet exist in the workforce. SkillForge closes this gap with a full-stack
AI platform where the learner's only job is to learn — every administrative step
is automated.

---

## 🏗️ Architecture
┌─────────────────────────────────────────────────────────────────┐
│                         LEARNER INTERFACE                        │
│                 Browser / Mobile / Desktop App                   │
└──────────────────────────┬──────────────────────────────────────┘
│ WebSocket (Voice) + REST (Data)
┌──────────────────────────▼──────────────────────────────────────┐
│                      SKILLFORGE BACKEND                          │
│                     FastAPI + WebSocket                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  AGENT ORCHESTRATOR                      │    │
│  │         (Strands Agents + Nova 2 Lite Coordination)      │    │
│  └──┬─────────────┬──────────────┬──────────────┬──────────┘    │
│     │             │              │              │               │
│  ┌──▼──┐    ┌─────▼────┐  ┌─────▼─────┐  ┌────▼──────┐        │
│  │Voice│    │ Skills   │  │ Learning  │  │  Job Mkt  │        │
│  │Coach│    │  Gap     │  │  Path     │  │ Intel     │        │
│  │Agent│    │  Agent   │  │  Agent    │  │  Agent    │        │
│  └──┬──┘    └─────┬────┘  └─────┬─────┘  └────┬──────┘        │
│     │             │              │              │               │
│  ┌──▼─────────────▼──────────────▼──────────────▼──────────┐    │
│  │              AMAZON NOVA FOUNDATION MODELS               │    │
│  │  Nova 2 Sonic │ Nova 2 Lite │ Nova Embeddings │ Nova Act │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────┐  ┌──────────────┐  ┌───────────────────┐    │
│  │   DynamoDB     │  │  OpenSearch  │  │  Job Market APIs  │    │
│  │ (User Profiles)│  │(Vector Store)│  │(LinkedIn, Indeed) │    │
│  └────────────────┘  └──────────────┘  └───────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
│
┌───────────▼──────────┐
│    NOVA ACT AGENTS   │
│  Coursera · Udemy    │
│  LinkedIn · AWS Cert │
│  Workday · Greenhouse│
└──────────────────────┘

## ✨ Features

### 🎙️ Voice Career Coaching (Nova 2 Sonic)
- 15-minute Career Discovery Conversation via real-time voice
- Emotional tone and confidence detection during skill discussions
- Weekly check-in coaching sessions with adaptive questioning
- Sub-250ms voice-to-voice latency

### 🧠 Intelligent Skills Analysis (Nova 2 Lite)
- AI-powered skills gap analysis against live job market data
- Salary impact projections per skill acquired
- Time-to-competency estimates with learning path sequencing
- Competitive intelligence: skills gaining/losing market value

### 🔍 Semantic Skills Matching (Nova Multimodal Embeddings)
- Skills knowledge graph across 50,000+ learning resources
- Portfolio analysis from GitHub profiles, PDFs, and project images
- Cross-modal matching: video course content ↔ job requirement depth
- No keyword matching — pure semantic competency alignment

### 🤖 Autonomous Enrollment & Applications (Nova Act)
- Auto-enroll in recommended courses across Coursera, Udemy, LinkedIn Learning
- Submit certifications to AWS, Credly, Pearson VUE automatically
- Tailor and submit job applications on Workday, Greenhouse, LinkedIn
- Sync learning schedule to Google Calendar with focus blocks

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Voice AI | Amazon Nova 2 Sonic |
| Reasoning | Amazon Nova 2 Lite |
| Embeddings | Amazon Nova Multimodal Embeddings |
| UI Automation | Amazon Nova Act |
| Agent Framework | AWS Strands Agents |
| Backend | Python 3.11 · FastAPI · WebSockets |
| Frontend | Next.js 14 · TypeScript · Tailwind CSS |
| Database | Amazon DynamoDB |
| Vector Store | Amazon OpenSearch Serverless |
| Cache | Amazon ElastiCache (Redis) |
| Infrastructure | AWS ECS Fargate · ALB · Terraform |

---

## ⚡ Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- AWS account with Bedrock access enabled
- Nova 2 Sonic, Nova 2 Lite, Nova Embeddings model access approved in Bedrock

### 1. Clone & Install

```bash
git clone https://github.com/your-org/skillforge-ai.git
cd skillforge-ai

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your AWS credentials and configuration
```

### 3. Run with Docker

```bash
docker-compose up --build
```

### 4. Access the Application

- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs
- **WebSocket:** ws://localhost:8000/ws/coaching

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `WS` | `/ws/coaching/{session_id}` | Real-time voice coaching stream |
| `POST` | `/api/v1/coaching/start` | Initialize coaching session |
| `GET` | `/api/v1/skills/{user_id}` | Get skills profile |
| `POST` | `/api/v1/skills/analyze` | Run skills gap analysis |
| `GET` | `/api/v1/learning/{user_id}/path` | Get personalized learning path |
| `POST` | `/api/v1/learning/enroll` | Trigger Nova Act enrollment |
| `GET` | `/api/v1/jobs/{user_id}/market` | Job market intelligence |
| `POST` | `/api/v1/portfolio/analyze` | Multimodal portfolio analysis |

---

## 🏆 Hackathon Submission

**Event:** Amazon Nova AI Hackathon
**Category:** Agentic AI + Freestyle
**Demo URL:** #AmazonNova
**Devpost:** https://amazon-nova.devpost.com

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

📁 Repository Structure
skillforge-ai/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── requirements.txt
├── pyproject.toml
├── docker-compose.yml
├── Dockerfile
│
├── src/
│   ├── config.py
│   ├── main.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── nova_sonic.py           # Nova 2 Sonic voice coaching
│   │   ├── nova_lite.py            # Nova 2 Lite reasoning agents
│   │   ├── nova_embeddings.py      # Nova multimodal embeddings
│   │   └── nova_act.py             # Nova Act UI automation
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Agent fleet coordinator
│   │   ├── career_coach.py         # Voice coaching session manager
│   │   ├── skills_gap_agent.py     # Skills gap analysis agent
│   │   ├── learning_path_agent.py  # Learning path architect agent
│   │   ├── job_market_agent.py     # Job market intelligence agent
│   │   └── enrollment_agent.py     # Nova Act enrollment automation
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── skills_graph.py         # Semantic skills knowledge graph
│   │   ├── job_market_service.py   # Real-time job market data ingestion
│   │   ├── learning_catalog.py     # 50K+ learning resource catalog
│   │   └── portfolio_analyzer.py  # Resume & portfolio multimodal analysis
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── dynamodb.py             # DynamoDB learner profiles
│   │   └── opensearch_client.py   # OpenSearch vector store
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py                  # FastAPI application
│   │   ├── websocket.py            # WebSocket voice streaming handler
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── coaching.py
│   │       ├── skills.py
│   │       ├── learning.py
│   │       └── jobs.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── audio.py
│       └── helpers.py
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── src/
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── page.tsx
│       │   └── dashboard/
│       │       └── page.tsx
│       ├── components/
│       │   ├── VoiceCoach.tsx
│       │   ├── SkillsRadar.tsx
│       │   ├── LearningPath.tsx
│       │   ├── JobMarket.tsx
│       │   └── CareerReadiness.tsx
│       └── lib/
│           ├── api.ts
│           └── websocket.ts
│
├── infrastructure/
│   └── terraform/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_models.py
    ├── test_agents.py
    └── test_api.py
