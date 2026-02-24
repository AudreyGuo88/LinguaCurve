# EchoRecall English 📚

An English learning app with Spaced Repetition, Active Recall, AI-powered Daily Challenges, and live pronunciation.

---

## 🚀 Quick Start

Double-click `run_app.bat` — the app opens at `http://localhost:8501`.
Close the terminal window to exit.

---

## 📖 Features

### 1. Smart Phrase Cards
- Learn 5–20 phrases per day (configurable via the dropdown)
- Each card shows a **proficiency icon** based on review history:
  - 🌱 First review · 🌿 In progress · 🌳 Mastered
- **Active Recall** — Chinese translation and example are hidden by default; click **"🧠 Reveal"** to check yourself
- **Bulk controls** — "👁 Reveal All" opens every card at once; "🙈 Hide All" resets them
- **Done-card feedback** — clicking "✅ Mark Done" dims the card, strikes through the title, and shows a green "Completed" badge
- **⭐ I Know This** — skip the SRS schedule entirely for phrases you already know; they move to the Mastered library instantly

### 2. Spaced Repetition (SRS)
- Review schedule based on the Ebbinghaus forgetting curve:
  - 1 day → 3 days → 7 days → 15 days → Mastered
- Phrases due today surface automatically; new phrases fill any remaining slots
- Dismissed (⭐) and mastered (🌳) phrases are permanently excluded from daily reviews

### 3. TTS Pronunciation
- Click **"🔊 Listen"** on any card to hear the phrase spoken aloud
- Powered by Google Text-to-Speech (`gTTS`) — requires an internet connection
- Available on phrase cards in Today's Learning **and** in the Progress library

### 4. Daily Challenge 🎯
- AI generates a short, humorous story using today's 5 phrases as fill-in-the-blank gaps
- Pass the challenge to auto-mark all 5 phrases as reviewed at once
- Requires an AI API key (OpenAI or DeepSeek)

### 5. Practice Chat 💬
- Conversational AI tutor focused on today's phrases
- **Word Bank** — a pinned chip row above the chat shows all 5 phrases; chips turn green with a ✓ as you use each one
- Encourages natural usage and gently corrects mistakes

### 6. Progress Library 📊
- **In Progress** — phrases still on the SRS schedule, grouped by category (🏠 Daily · 💼 Business · 👥 Social · 📺 TV Series); click any phrase to review its translation, example, and pronunciation
- **Mastered** — all completed (🌳) and manually dismissed (⭐) phrases, also grouped by category; click to review at any time
- **↩️ Re-learn** button on every mastered phrase — moves it back into the SRS queue if you want to practise it again
- Four summary metrics: Streak · In Progress · Mastered · Known
- **Animated progress bar** in Today's Learning with a changing emoji as you advance (📋 → 🌱 → 💪 → 🔥 → 🎉)
- **Streak counter** with dynamic sidebar icons: 💤 / 🕯️ / 🔥 / 🚀 / ⚡

---

## ⚙️ Setup

### Install dependencies

```bash
pip install streamlit pandas requests gTTS
```

### AI API Key (optional — required for Daily Challenge & Practice Chat)

Add your key in the sidebar under **AI Provider**:

| Provider | Where to get |
|----------|-------------|
| OpenAI   | platform.openai.com |
| DeepSeek | platform.deepseek.com |

Keys are **never** written to disk or synced to cloud.

### Cloud Sync (optional)

Store your learning data in a private GitHub Gist so it persists across devices:

1. Create a GitHub personal access token (scope: `gist`)
2. Enter it under **"☁️ Manual Cloud Setup"** in the sidebar
3. Your data syncs automatically on every review

For Streamlit Cloud deployments, add secrets in the dashboard:

```toml
# .streamlit/secrets.toml
GITHUB_TOKEN = "ghp_..."
GIST_ID = "abc123..."          # leave blank on first run
OPENAI_API_KEY = "sk-..."      # or use DEEPSEEK_API_KEY
```

---

## 📂 Data Storage

| Location | When used |
|----------|-----------|
| `learning_data.json` | Always (local fallback) |
| GitHub Gist | When GitHub token is configured |

Back up `learning_data.json` if you are not using Gist sync.

---

## ❓ Troubleshooting

**App won't start?**
- Ensure Python 3.9+ is installed
- Try: right-click `run_app.bat` → Run as Administrator

**Port already in use?**
- Edit `run_app.bat` and append `--server.port 8502` to the last line

**"🔊 Listen" not working?**
- Run `venv\Scripts\pip install gTTS` and restart the app
- Requires an active internet connection

**Daily Challenge not available?**
- Add an API key (OpenAI or DeepSeek) in the sidebar
- Need at least 5 phrases in today's list

**Accidentally clicked "Delete Local Data"?**
- The button requires a second confirmation — click **"❌ Cancel"** to abort safely

**Accidentally clicked "⭐ I Know This"?**
- Go to **📊 Progress → Mastered**, find the phrase, and click **"↩️ Re-learn"** to restore it to the review schedule

---

## 📝 License

Free to use for personal learning.
