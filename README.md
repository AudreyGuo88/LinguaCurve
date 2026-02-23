# EchoRecall English 📚

A minimalist English learning desktop app with Spaced Repetition System (SRS).

## 🚀 Quick Start (Windows 10)

### First Time Setup

1. **Install Python**
   - Download Python 3.10+ from https://www.python.org/downloads/
   - ⚠️ **Important**: Check "Add Python to PATH" during installation

2. **Download this project**
   - Extract all files to a folder (e.g., `C:\EchoRecall\`)

3. **Run the app**
   - Double-click `run_app.bat`
   - Wait for installation (first time only)
   - Your browser will open automatically!

### Daily Use

- Just double-click `run_app.bat` to start
- The app runs at `http://localhost:8501`
- Close the terminal window to exit

## 📖 Features

### 1. Daily 5 Phrases
- Learn 5 new phrases or review due phrases every day
- Mark phrases as reviewed with one click

### 2. Spaced Repetition (SRS)
- Reviews at: 1 day → 3 days → 7 days → 15 days
- Automatic scheduling based on Ebbinghaus curve

### 3. Practice Chat
- Immersive roleplay with today's keywords
- (Optional) Add your OpenAI/Anthropic API key for real AI

### 4. Progress Tracking
- Daily streak counter
- Visual charts of learning progress

## ⚙️ Configuration

- Click "Settings" in the sidebar
- Add API key (optional) for AI chat
- Reset data if needed

## 📂 Data Storage

All your learning data is saved in `learning_data.json` in the same folder.

## ❓ Troubleshooting

**App won't start?**
- Make sure Python is installed
- Right-click `run_app.bat` → Run as Administrator

**Port already in use?**
- Close other Streamlit apps
- Or edit `run_app.bat` and add `--server.port 8502` to the last line

**Lost your data?**
- Your data is in `learning_data.json` - back it up regularly!

## 📝 License

Free to use for personal learning.