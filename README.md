# HireOS — Intelligent Hiring Pipeline

> **Two agents. Zero bottlenecks.**

HireOS is a fully automated hiring pipeline built on [Airia Cloud](https://airia.ai) for the Airia Hackathon (Track 2: Active Agents). Type in a role title and HireOS generates a job post, creates an interview question PDF, evaluates incoming resumes, schedules Google Meet interviews, and notifies your team on Slack — all without a single manual step.

---

## Demo

**Live app:** [web-production-19d47.up.railway.app](https://web-production-19d47.up.railway.app)

**Flow:**
1. Enter a role (e.g. "Data Scientist") → Agent 1 generates a job post + interview question PDF
2. Submit a resume URL → Agent 2 scores the candidate, auto-schedules a Google Meet if shortlisted, and fires a Slack alert

---

## Architecture

HireOS runs two coordinated Airia pipelines:

### Agent 1 — Job Setup Pipeline
```
Input (role title)
  → Data_Source_Internal_Confluence   pulls role context from internal docs
  → Technical_Skills_Extractor        AI — extracts must-have skills
  → Job_Post_Generator                AI — writes full job description
  → Interview_Questions_Generator     AI — creates interview question bank
  → HTTP Request (PDFShift)           renders questions as PDF, hosted on S3
  → JSON_Output_Formatter             AI — structured JSON output
Output: job post, required skills array, interview PDF URL
```

### Agent 2 — Candidate Evaluation Pipeline
```
Input (resume PDF URL)
  → Parse_Resume_Via_Script           Python — fetches and extracts resume text
  → Resume_Keyword_Extractor          AI — pulls candidate skills
  → Resume_Scorer                     AI — scores candidate vs job requirements
  → Conditional_Branch                Python — routes SHORTLIST / REJECT
  → Google Calendar API               HTTP — creates Google Meet for shortlisted candidates
  → Slack_Message_Notifier + HTTP     AI + webhook — notifies #hiring channel
  → JSON_Output_Formatter             AI — structured scorecard output
Output: scorecard, decision, rejection email draft or meeting link
```

---

## Integration Stack

| Integration | Agent | Role |
|---|---|---|
| Confluence | Agent 1 | Pulls role requirements from internal knowledge base |
| PDFShift | Agent 1 | Renders interview question PDFs hosted on AWS S3 |
| Google Calendar | Agent 2 | Creates Google Meet invites for shortlisted candidates |
| Slack | Agent 2 | Real-time hiring alerts to #hiring channel |
| Airia Cloud | Both | Multi-agent pipeline orchestration engine |

---

## Running Locally

### Prerequisites
- Python 3.9+
- Google Cloud project with Calendar API enabled
- Airia Cloud account with both pipelines deployed

### Setup

```bash
git clone https://github.com/your-username/hireos.git
cd hireos
pip install -r requirements.txt
```

Add a `credentials.json` file from your Google Cloud Console (OAuth 2.0 Desktop App), then run:

```bash
python server.py
```

On first run, a browser window opens for Google OAuth. Sign in with your recruiter account — this generates `token.json` for subsequent runs.

Open [http://localhost:5500](http://localhost:5500).

### Environment Variables

| Variable | Description |
|---|---|
| `AIRIA_API_KEY` | Your Airia API key |
| `RECRUITER_EMAIL` | Email to invite to scheduled interviews |
| `CANDIDATE_EMAIL` | Candidate email for demo purposes |
| `GOOGLE_TOKEN_JSON` | Contents of `token.json` (for production deployments) |

---

## Deploying to Railway

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select this repo
4. Add environment variables in the Variables tab
5. Deploy

---

## Project Structure

```
hireos/
  hireos.html          # Frontend UI — single file, dark theme
  server.py            # Flask proxy + Google Calendar integration
  requirements.txt     # Python dependencies
  Procfile             # Railway/Render start command
  .gitignore           # Excludes token.json, credentials.json
```

---

## Built With

- [Airia Cloud](https://airia.ai) — multi-agent pipeline orchestration
- [Flask](https://flask.palletsprojects.com) — lightweight Python backend
- [Google Calendar API](https://developers.google.com/calendar) — automated interview scheduling
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks) — hiring notifications
- [PDFShift](https://pdfshift.io) — interview question PDF generation
- [Confluence](https://www.atlassian.com/software/confluence) — internal knowledge base via Airia connector

---

## Hackathon

Built for the **Airia Hackathon — Track 2: Active Agents**
