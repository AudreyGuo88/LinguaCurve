# EchoRecall English 📚

A minimalist English learning app with Spaced Repetition, Active Recall, and AI-powered Daily Challenges.

---

## 🚀 Quick Start

Double-click `run_app.bat` — the app opens at `http://localhost:8501`.
Close the terminal window to exit.

---

## 📖 Features

### 1. Smart Phrase Cards
- Learn 5–20 phrases per day (configurable)
- Each card shows a **proficiency icon** based on review history:
  - 🌱 First review &nbsp;·&nbsp; 🌿 In progress &nbsp;·&nbsp; 🌳 Mastered
- Translation and example sentence are **hidden by default** — click **"🧠 Reveal"** to test yourself (Active Recall)

### 2. Spaced Repetition (SRS)
- Review schedule based on the Ebbinghaus forgetting curve:
  - 1 day → 3 days → 7 days → 15 days → Mastered
- Phrases due today surface automatically; new phrases fill any remaining slots

### 3. TTS Pronunciation
- Click **"🔊 Listen"** on any card to hear the phrase spoken aloud
- Powered by Google Text-to-Speech (`gTTS`) — requires an internet connection
- Gracefully disabled if `gTTS` is not installed

### 4. Daily Challenge 🎯
- Generates a short, humorous story that uses today's 5 phrases as blanks
- Fill in all blanks correctly to auto-mark all 5 phrases as reviewed at once
- Requires an AI API key (OpenAI or DeepSeek)

### 5. Practice Chat 💬
- Conversational AI tutor focused on today's phrases
- Encourages natural usage and gently corrects mistakes

### 6. Progress Tracking 📊
- **Streak counter** with dynamic icons: 💤 / 🕯️ / 🔥 / 🚀 / ⚡
- Live progress bar in the sidebar (today's completed vs. total)
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

**"🔊 Listen" button missing / not working?**
- Run `pip install gTTS` and restart the app
- Requires an active internet connection

**Daily Challenge not available?**
- Add an API key (OpenAI or DeepSeek) in the sidebar
- Need at least 5 phrases in today's list

---

## 📝 License

Free to use for personal learning.
