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


● EchoRecall English 📚                                                                                                                                                                                                                                                 
                                                                                                                                                                                                                                                                      
  一款用科学方法帮你记住英语短语的学习工具。                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                      
  ---                                                                                                                                                                                                                                                                   
  核心理念                                                                                                                                                                                                                                                            

  大多数人背单词的问题不是"没背过"，而是"背了就忘"。EchoRecall 基于艾宾浩斯遗忘曲线，在你即将遗忘的那一刻推送复习，让记忆真正留下来。

  ---
  主要功能

  📚 每日学习

  每天推送 5～20 个短语（数量可调）。每张卡片默认隐藏中文释义和例句——先凭记忆回想，再点开验证，这叫主动回忆，比反复看效果强得多。

  学完一个短语点 ✅ Mark Done，卡片立刻变灰划线，进度条也跟着走。

  如果某个短语你早就会了，点 ⭐ I Know This，它直接进入"已掌握"库，不再打扰你。

  🔁 间隔复习

  复习不是今天背、明天忘。系统按照科学间隔自动安排：
  - 第一次复习后 → 1 天后再见
  - 第二次 → 3 天后
  - 第三次 → 7 天后
  - 第四次 → 15 天后 → 正式毕业 🌳

  🔊 真人发音

  每个短语都有朗读按钮，一键听标准美式发音，解决"认识但不会说"的问题。

  🎯 每日挑战

  AI 把今天的 5 个短语编成一个幽默小故事，然后把它们挖空——你来填空。全对才算通关，通关后自动帮你完成今日复习。

  💬 对话练习

  跟 AI 老师自由对话，Word Bank 实时追踪你有没有在对话里用上今天的短语，用过的词条会变绿打勾 ✓。

  📊 学习档案

  Progress 页面按用途分类（日常 / 职场 / 社交 / 影视）展示所有短语：
  - In Progress — 还在复习计划里的
  - Mastered — 已毕业或手动标记的，随时可以点开复习，也可以用 ↩️ Re-learn 重新加回复习队列

  ---
  技术特点

  - 数据存在本地 JSON，可选同步到 GitHub Gist（多设备共享）
  - API 密钥永远不写入磁盘或云端
  - 支持 OpenAI 和 DeepSeek 两种 AI 接口
