# FormPilot — Frontend Application

**Paperwork, handled.**  
AI-powered, human-controlled browser automation for online forms.

> “Traditional autofill knows where to type. FormPilot understands what to type, where the information came from, and whether the result is correct.”

---

## Implemented Routes

- `/profiles` — Manual profile selection and profile creation (default entry workflow)
- `/welcome` — Overview & workflow introduction
- `/profiles/:profileId` — Profile settings, profile-scoped vault, API mode toggle, cascade delete
- `/dashboard` — Editorial burgundy dashboard with summary stats, Live Workspace preview, Agent Timeline, Review & Approve preview, Document Vault, and Recent Applications
- `/tasks/new` — Task creation with profile scope indicator, target URL validation, vault selector, and PDF/TXT multi-file upload
- `/tasks/:taskId/workspace` — Two-column Live Workspace (Browser Preview + WebSocket Agent Timeline, progress, counters, cancel/reconnect)
- `/tasks/:taskId/review` — Full Review & Approval table with inline editing, conflict resolution, missing-value alerts, approval invalidation on subsequent edits, and confirmation modal
- `/tasks/:taskId/complete` — Verification summary (`"Form filled and verified — ready for your review."`), counts, final screenshot, and per-field Expected vs Observed table

---

## Running Locally

1. Install dependencies:
   ```bash
   npm install
   ```

2. Configure frontend environment (optional — defaults to Demo Mock Mode):
   ```bash
   cp .env.example .env
   ```

3. Start the Vite dev server:
   ```bash
   npm run dev
   ```

4. Build & type-check:
   ```bash
   npm run lint
   npm run build
   ```

---

## Switching Between Demo Mock Mode and FastAPI Backend

The frontend ships with a centralized **Mock API & Simulated WebSocket** mode (`VITE_USE_MOCK_API="true"` by default) so all workflows work independently before Developer 2's FastAPI backend is connected.

You can switch to live backend mode in either of two ways:
1. Set `VITE_USE_MOCK_API="false"`, `VITE_API_BASE_URL="http://localhost:8000"`, and `VITE_WS_BASE_URL="ws://localhost:8000"` in `.env`.
2. Open any Profile's **Profile Settings** (`/profiles/:profileId`) and toggle **Use Mock API & Simulated WebSocket** at runtime.

See [`docs/INTEGRATION_NOTES.md`](docs/INTEGRATION_NOTES.md) for the exact REST, WebSocket, and payload contracts expected from Developer 2.
