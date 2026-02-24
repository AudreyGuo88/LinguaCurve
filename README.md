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
- **Active Recall** — translation and example are hidden by default; click **"🧠 Reveal"** to check yourself
- **Bulk controls** — "👁 Reveal All" opens every card at once for quick review; "🙈 Hide All" resets them
- **Done-card feedback** — clicking "✅ Mark Done" immediately dims the card, strikes through the title, and shows a green "Completed" badge

### 2. Spaced Repetition (SRS)
- Review schedule based on the Ebbinghaus forgetting curve:
  - 1 day → 3 days → 7 days → 15 days → Mastered
- Phrases due today surface automatically; new phrases fill any remaining slots

### 3. TTS Pronunciation
- Click **"🔊 Listen"** on any card to hear the phrase spoken aloud
- Powered by Google Text-to-Speech (`gTTS`) — requires an internet connection
- Shows an install hint if `gTTS` is not found

### 4. Daily Challenge 🎯
- AI generates a short, humorous story using today's 5 phrases as fill-in-the-blank gaps
- Pass the challenge to auto-mark all 5 phrases as reviewed at once
- Requires an AI API key (OpenAI or DeepSeek)

### 5. Practice Chat 💬
- Conversational AI tutor focused on today's phrases
- **Word Bank** — a pinned chip row above the chat shows all 5 phrases; chips turn green with a ✓ as you use each one in conversation
- Encourages natural usage and gently corrects mistakes

### 6. Progress Tracking 📊
- **Animated progress bar** in Tab 1 with a changing emoji as you advance (📋 → 🌱 → 💪 → 🔥 → 🎉)
- **Streak counter** with dynamic sidebar icons: 💤 / 🕯️ / 🔥 / 🚀 / ⚡
- Live sidebar progress bar (today's completed vs. total)
- Progress tab shows full learning and mastered phrase tables

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
- Run `pip install gTTS` and restart the app
- Requires an active internet connection

**Daily Challenge not available?**
- Add an API key (OpenAI or DeepSeek) in the sidebar
- Need at least 5 phrases in today's list

**Accidentally clicked "Delete Local Data"?**
- The button now requires a second confirmation — click **"❌ Cancel"** to abort safely

---

## 📝 License

Free to use for personal learning.
