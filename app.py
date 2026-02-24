import streamlit as st
import json
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import requests
import time
import copy
import io

# Optional TTS support
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False


# ============================================================================
# Load Secrets (Priority: Streamlit Secrets > User Input)
# ============================================================================

def load_secrets():
    """Load API keys and tokens from Streamlit secrets or session state"""
    secrets = {}

    try:
        if hasattr(st, 'secrets'):
            secrets['github_token'] = st.secrets.get("GITHUB_TOKEN", "")
            secrets['openai_key'] = st.secrets.get("OPENAI_API_KEY", "")
            secrets['deepseek_key'] = st.secrets.get("DEEPSEEK_API_KEY", "")
            secrets['gist_id'] = st.secrets.get("GIST_ID", "")
    except Exception:
        pass

    if 'github_token' not in st.session_state:
        st.session_state.github_token = secrets.get('github_token', '')
    if 'gist_id' not in st.session_state:
        st.session_state.gist_id = secrets.get('gist_id', '')

    return secrets


# ============================================================================
# Configuration & Data Management
# ============================================================================

DATA_FILE = Path("learning_data.json")

DEFAULT_PHRASE_POOL = [
    {"phrase": "break the ice", "chinese": "打破僵局", "example": "Let me tell a joke to break the ice.",
     "category": "Social"},
    {"phrase": "hit the nail on the head", "chinese": "一针见血", "example": "Your analysis hit the nail on the head.",
     "category": "Business"},
    {"phrase": "piece of cake", "chinese": "小菜一碟", "example": "This test was a piece of cake!",
     "category": "Daily"},
    {"phrase": "under the weather", "chinese": "身体不适", "example": "I'm feeling under the weather today.",
     "category": "Daily"},
    {"phrase": "call it a day", "chinese": "收工", "example": "Let's call it a day and go home.",
     "category": "Business"},
    {"phrase": "bite the bullet", "chinese": "硬着头皮做", "example": "I had to bite the bullet and apologize.",
     "category": "Daily"},
    {"phrase": "on cloud nine", "chinese": "非常高兴", "example": "She was on cloud nine after getting promoted.",
     "category": "Daily"},
    {"phrase": "spill the beans", "chinese": "泄露秘密", "example": "Don't spill the beans about the surprise party!",
     "category": "Social"},
    {"phrase": "cost an arm and a leg", "chinese": "非常昂贵", "example": "That new car cost him an arm and a leg.",
     "category": "Daily"},
    {"phrase": "the ball is in your court", "chinese": "该你做决定了",
     "example": "I've made my offer, now the ball is in your court.", "category": "Business"},
    {"phrase": "beat around the bush", "chinese": "拐弯抹角",
     "example": "Stop beating around the bush and tell me the truth.", "category": "Social"},
    {"phrase": "let the cat out of the bag", "chinese": "泄露秘密",
     "example": "He let the cat out of the bag about the promotion.", "category": "Social"},
    {"phrase": "once in a blue moon", "chinese": "千载难逢", "example": "We only see each other once in a blue moon.",
     "category": "Daily"},
    {"phrase": "get cold feet", "chinese": "临阵退缩", "example": "He got cold feet before the wedding.",
     "category": "Social"},
    {"phrase": "when pigs fly", "chinese": "不可能", "example": "He'll clean his room when pigs fly.",
     "category": "TV Series"},
]


# ============================================================================
# GitHub Gist Storage Functions
# ============================================================================

class GistStorage:
    """Handle data persistence using GitHub Gist"""

    def __init__(self, token, gist_id=None):
        self.token = token
        self.gist_id = gist_id
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.filename = "learning_data.json"

    def create_gist(self, data):
        """Create a new private Gist"""
        try:
            payload = {
                "description": "EchoRecall English Learning Data",
                "public": False,
                "files": {
                    self.filename: {
                        "content": json.dumps(data, ensure_ascii=False, indent=2)
                    }
                }
            }
            response = requests.post(
                "https://api.github.com/gists",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            if response.status_code == 201:
                self.gist_id = response.json()['id']
                return True, self.gist_id
            else:
                return False, f"Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, str(e)

    def read_gist(self):
        """Read data from existing Gist"""
        if not self.gist_id:
            return None, "No Gist ID provided"
        try:
            response = requests.get(
                f"https://api.github.com/gists/{self.gist_id}",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                content = response.json()['files'][self.filename]['content']
                return json.loads(content), None
            else:
                return None, f"Error {response.status_code}"
        except Exception as e:
            return None, str(e)

    def update_gist(self, data):
        """Update existing Gist"""
        if not self.gist_id:
            return self.create_gist(data)
        try:
            payload = {
                "files": {
                    self.filename: {
                        "content": json.dumps(data, ensure_ascii=False, indent=2)
                    }
                }
            }
            response = requests.patch(
                f"https://api.github.com/gists/{self.gist_id}",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            if response.status_code == 200:
                return True, None
            else:
                return False, f"Error {response.status_code}"
        except Exception as e:
            return False, str(e)


def load_data():
    """Load data from Gist or create new"""
    secrets = load_secrets()
    github_token = st.session_state.get('github_token', '')
    gist_id = st.session_state.get('gist_id', '')

    if github_token and gist_id:
        storage = GistStorage(github_token, gist_id)
        data, error = storage.read_gist()

        if data:
            if 'settings' not in data:
                data['settings'] = {}

            # 🔒 Force load API keys from Secrets (never from Gist)
            data['settings']['api_key'] = secrets.get('openai_key', '')
            data['settings']['deepseek_key'] = secrets.get('deepseek_key', '')
            data['settings']['api_provider'] = data['settings'].get('api_provider', 'openai')

            # Migrate: add category field
            for phrase in data.get('phrase_pool', []):
                if 'category' not in phrase:
                    phrase['category'] = 'Daily'
            for phrase in data.get('learning', []):
                if 'category' not in phrase:
                    phrase['category'] = 'Daily'
            for phrase in data.get('mastered', []):
                if 'category' not in phrase:
                    phrase['category'] = 'Daily'

            return data

    # Create fresh data if no Gist
    return {
        "phrase_pool": DEFAULT_PHRASE_POOL,
        "learning": [],
        "mastered": [],
        "daily_streak": 0,
        "last_study_date": None,
        "settings": {
            "api_key": secrets.get('openai_key', ''),
            "api_provider": "openai",
            "deepseek_key": secrets.get('deepseek_key', '')
        }
    }


def get_today_phrases(data, count=5):
    """Get phrases for today (new or due for review)"""
    today = datetime.now().date()

    due_phrases = []
    for phrase in data['learning']:
        next_review = datetime.strptime(phrase['next_review'], '%Y-%m-%d').date()
        if next_review <= today:
            due_phrases.append(phrase)

    needed = count - len(due_phrases)
    new_phrases = []
    if needed > 0:
        available = [p for p in data['phrase_pool']
                     if not any(p['phrase'] == lp['phrase'] for lp in data['learning'])
                     and not any(p['phrase'] == mp['phrase'] for mp in data['mastered'])]
        new_phrases = available[:needed]

    return due_phrases + new_phrases


def calculate_next_review(review_count):
    """Calculate next review date based on Ebbinghaus curve"""
    intervals = [1, 3, 7, 15]
    if review_count >= len(intervals):
        return None
    return (datetime.now() + timedelta(days=intervals[review_count])).strftime('%Y-%m-%d')


def mark_reviewed(data, phrase_text):
    """Mark a phrase as reviewed and update next review date"""
    for phrase in data['learning']:
        if phrase['phrase'] == phrase_text:
            phrase['review_count'] += 1
            phrase['last_review'] = datetime.now().strftime('%Y-%m-%d')
            next_date = calculate_next_review(phrase['review_count'])

            if next_date is None:
                data['mastered'].append(phrase)
                data['learning'].remove(phrase)
            else:
                phrase['next_review'] = next_date

            save_data(data)
            return True

    phrase_data = next((p for p in data['phrase_pool'] if p['phrase'] == phrase_text), None)
    if phrase_data:
        new_phrase = {
            "phrase": phrase_text,
            "chinese": phrase_data.get('chinese', ''),
            "example": phrase_data.get('example', ''),
            "category": phrase_data.get('category', 'Daily'),
            "review_count": 0,
            "last_review": datetime.now().strftime('%Y-%m-%d'),
            "next_review": calculate_next_review(0)
        }
        data['learning'].append(new_phrase)
        save_data(data)
        return True

    return False


def update_streak(data):
    """Update daily streak counter"""
    today = datetime.now().strftime('%Y-%m-%d')
    last_study = data.get('last_study_date')

    if last_study != today:
        if last_study is None:
            data['daily_streak'] = 1
        else:
            last_date = datetime.strptime(last_study, '%Y-%m-%d').date()
            if (datetime.now().date() - last_date).days == 1:
                data['daily_streak'] += 1
            else:
                data['daily_streak'] = 1

        data['last_study_date'] = today
        save_data(data)


def save_data(data):
    """Save data to Gist (NEVER save API keys)"""
    data_to_save = copy.deepcopy(data)

    if 'settings' in data_to_save:
        data_to_save['settings']['api_key'] = ''
        data_to_save['settings']['deepseek_key'] = ''

    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"⚠️ Local save failed: {e}")

    github_token = st.session_state.get('github_token', '')
    gist_id = st.session_state.get('gist_id', '')

    if not github_token:
        return

    storage = GistStorage(github_token, gist_id)
    success, error = storage.update_gist(data_to_save)

    if success:
        if not gist_id and storage.gist_id:
            st.session_state.gist_id = storage.gist_id
            st.success(f"✅ Gist created! ID: {storage.gist_id}")
    elif error:
        st.warning(f"⚠️ Cloud sync failed: {error}")


# ============================================================================
# AI API Integration
# ============================================================================

def call_openai_api(api_key, messages, model="gpt-4o-mini"):
    """Call OpenAI API"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 800
        }
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"❌ API Error: {response.status_code}"
    except Exception as e:
        return f"❌ Connection Error: {str(e)}"


def call_deepseek_api(api_key, messages, model="deepseek-chat"):
    """Call DeepSeek API"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 800
        }
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"❌ API Error: {response.status_code}"
    except Exception as e:
        return f"❌ Connection Error: {str(e)}"


def call_ai_api(data, messages):
    """Unified API caller based on settings"""
    provider = data['settings'].get('api_provider', 'openai')

    if provider == 'openai':
        api_key = data['settings'].get('api_key', '')
        if not api_key:
            return "⚠️ Please add your OpenAI API Key in Settings."
        return call_openai_api(api_key, messages)

    elif provider == 'deepseek':
        api_key = data['settings'].get('deepseek_key', '')
        if not api_key:
            return "⚠️ Please add your DeepSeek API Key in Settings."
        return call_deepseek_api(api_key, messages)

    return "⚠️ Unknown API provider."


def generate_new_phrases(data, count=5):
    """Auto-generate high-frequency practical phrases using AI"""

    system_prompt = """You are an expert English teacher specializing in teaching practical, high-frequency English to Chinese learners.

# CRITICAL REQUIREMENTS:

## 1. SOURCE PRIORITY:
- **Tier 1**: Popular TV series (Friends, Modern Family, The Office)
- **Tier 2**: Workplace/office expressions
- **Tier 3**: Social gathering phrases
- **Tier 4**: Daily life essentials

## 2. VOCABULARY CONSTRAINTS:
- MUST use ONLY COCA top 5000 high-frequency words
- STRICTLY FORBIDDEN: Literary/archaic/academic vocabulary
- Think: "Would a character in Friends say this?"

## 3. DIFFICULTY LEVEL:
- CEFR B1-B2 level (intermediate)

## 4. CATEGORY CLASSIFICATION:
- **Daily**: Everyday life
- **Business**: Workplace
- **TV Series**: Pop culture
- **Social**: Social gatherings

## 5. QUALITY STANDARDS:
- Phrase: 2-6 words
- Natural example sentence
- Colloquial Chinese translation

# CRITICAL OUTPUT RULES:
Return ONLY a valid JSON array. NO markdown, NO explanations, NO code blocks.

Start directly with [ and end with ]

Format:
[
  {
    "phrase": "grab a bite",
    "chinese": "随便吃点",
    "example": "Want to grab a bite after work?",
    "category": "Daily"
  }
]

DO NOT include ```json or any other text."""

    existing_phrases = [p['phrase'] for p in data['phrase_pool']]
    user_prompt = f"""Generate exactly {count} NEW high-frequency English phrases.

AVOID these: {', '.join(existing_phrases[:30])}

Return ONLY the JSON array. No markdown, no explanations."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    with st.spinner("🤖 Generating..."):
        response = call_ai_api(data, messages)

    if response.startswith("❌") or response.startswith("⚠️"):
        return False, response

    try:
        with st.expander("🔍 Debug: AI Response"):
            st.code(response[:800], language=None)

        response = response.strip()

        if "```" in response:
            parts = response.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    response = part[4:].strip()
                    break
                elif part and "[" in part:
                    try:
                        json.loads(part)
                        response = part
                        break
                    except Exception:
                        continue

        start_idx = response.find('[')
        end_idx = response.rfind(']')

        if start_idx != -1 and end_idx != -1:
            response = response[start_idx:end_idx + 1]

        response = response.strip()
        new_phrases = json.loads(response)

        if isinstance(new_phrases, list) and len(new_phrases) > 0:
            valid_phrases = []
            for phrase in new_phrases:
                if all(key in phrase for key in ['phrase', 'chinese', 'example', 'category']):
                    if phrase['category'] not in ['Daily', 'Business', 'TV Series', 'Social']:
                        phrase['category'] = 'Daily'
                    valid_phrases.append(phrase)

            if valid_phrases:
                data['phrase_pool'].extend(valid_phrases)
                save_data(data)
                return True, len(valid_phrases)
            else:
                return False, "No valid phrases in response"
        else:
            return False, "Response is not a JSON array"

    except json.JSONDecodeError as e:
        st.error(f"❌ JSON Parse Error at position {e.pos}")
        st.code(response[:1000], language=None)
        return False, f"Parse error: {str(e)}"
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        return False, str(e)


def check_and_refill_pool(data, threshold=10):
    """Check if phrase pool needs refilling"""
    available = [p for p in data['phrase_pool']
                 if not any(p['phrase'] == lp['phrase'] for lp in data['learning'])
                 and not any(p['phrase'] == mp['phrase'] for mp in data['mastered'])]

    if len(available) < threshold:
        return generate_new_phrases(data, count=5)

    return None, None


# ============================================================================
# UI Helper Functions
# ============================================================================

def get_category_color(category):
    """Return emoji for category"""
    colors = {
        'Daily': '🏠',
        'Business': '💼',
        'TV Series': '📺',
        'Social': '👥'
    }
    return colors.get(category, '📌')


def get_proficiency_icon(review_count, is_mastered=False):
    """Return growth stage icon based on review progress"""
    if is_mastered:
        return "🌳"
    elif review_count <= 1:
        return "🌱"
    else:
        return "🌿"


def get_streak_icon(streak):
    """Return dynamic icon based on streak count"""
    if streak == 0:
        return "💤"
    elif streak <= 2:
        return "🕯️"
    elif streak <= 7:
        return "🔥"
    elif streak <= 20:
        return "🚀"
    else:
        return "⚡"


def get_tts_audio(text):
    """Generate TTS audio bytes for given text"""
    if not TTS_AVAILABLE:
        return None
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        return audio_fp
    except Exception:
        return None


def generate_daily_challenge(data, phrases):
    """Generate a fill-in-the-blank story using today's phrases"""
    phrase_texts = [p['phrase'] for p in phrases[:5]]

    system_prompt = """You are a creative and humorous English teacher.
Create a short, funny story (4-6 sentences) that naturally uses exactly the 5 given phrases.
In the story, replace each phrase with a blank marker. Use [BLANK_1] through [BLANK_5] in the ORDER they appear in the story.

Return ONLY valid JSON (no markdown, no explanation):
{
  "story": "The full story text with [BLANK_1], [BLANK_2], [BLANK_3], [BLANK_4], [BLANK_5] placed where each phrase belongs",
  "answers": ["phrase for blank 1", "phrase for blank 2", "phrase for blank 3", "phrase for blank 4", "phrase for blank 5"]
}

The answers array must list all 5 phrases in the EXACT order they appear as [BLANK_1] to [BLANK_5]."""

    user_prompt = f"Write a funny story using ALL 5 of these phrases in any order: {', '.join(phrase_texts)}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    with st.spinner("🎭 Crafting your Daily Challenge..."):
        response = call_ai_api(data, messages)

    if response.startswith("❌") or response.startswith("⚠️"):
        return None, response

    try:
        response = response.strip()
        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end != -1:
            response = response[start:end + 1]
        result = json.loads(response)
        if 'story' in result and 'answers' in result:
            return result, None
        return None, "Invalid response format"
    except Exception as e:
        return None, f"Parse error: {e}"


# ============================================================================
# Main UI
# ============================================================================

def main():
    st.set_page_config(
        page_title="EchoRecall English",
        page_icon="📚",
        layout="wide"
    )

    # ── Global CSS ────────────────────────────────────────────────────────────
    st.markdown("""
<style>
/* Phrase card containers */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
    border: 1px solid #e0e7ff !important;
    box-shadow: 0 2px 12px rgba(99, 102, 241, 0.07) !important;
    background: linear-gradient(135deg, #fafbff 0%, #f5f0ff 100%) !important;
    transition: box-shadow 0.2s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.16) !important;
}
/* Category badge */
.cat-badge {
    display: inline-block;
    background: #e0e7ff;
    color: #4338ca;
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.8em;
    font-weight: 600;
    margin-right: 4px;
}
/* Challenge story box */
.story-box {
    background: #fffbeb;
    border: 1px solid #fcd34d;
    border-radius: 10px;
    padding: 16px 20px;
    font-size: 1.05em;
    line-height: 2.0;
    margin: 12px 0;
}
.blank-tag {
    display: inline-block;
    background: #fef3c7;
    border: 2px dashed #f59e0b;
    border-radius: 6px;
    padding: 0 10px;
    color: #92400e;
    font-weight: 700;
    font-size: 0.95em;
}
/* Sidebar streak */
.streak-display {
    font-size: 1.35em;
    font-weight: 700;
    margin: 4px 0 10px 0;
}
</style>
""", unsafe_allow_html=True)

    # ── Load secrets ──────────────────────────────────────────────────────────
    secrets = load_secrets()

    # ── Session state initialisation ─────────────────────────────────────────
    if 'reviewed_today' not in st.session_state:
        st.session_state.reviewed_today = set()
    if 'just_reviewed' not in st.session_state:
        st.session_state.just_reviewed = False
    if 'learn_mode' not in st.session_state:
        st.session_state.learn_mode = 5
    if 'challenge_data' not in st.session_state:
        st.session_state.challenge_data = None
    if 'challenge_passed' not in st.session_state:
        st.session_state.challenge_passed = False

    # ── Load data (once, shared by all tabs) ─────────────────────────────────
    data = load_data()

    # ── Balloons celebration (fires after any ✅ review) ─────────────────────
    if st.session_state.just_reviewed:
        st.balloons()
        st.session_state.just_reviewed = False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SIDEBAR
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with st.sidebar:
        st.title("📚 EchoRecall")

        # Cloud connection status
        if st.session_state.get('github_token'):
            st.success("☁️ Cloud: Connected")
            if st.session_state.get('gist_id'):
                st.caption(f"Gist: `{st.session_state.gist_id[:8]}...`")

        if not secrets.get('github_token'):
            with st.expander("☁️ Manual Cloud Setup"):
                github_token = st.text_input(
                    "GitHub Token",
                    value=st.session_state.get('github_token', ''),
                    type="password"
                )
                gist_id_input = st.text_input(
                    "Gist ID (Optional)",
                    value=st.session_state.get('gist_id', '')
                )
                if st.button("💾 Connect"):
                    if github_token:
                        st.session_state.github_token = github_token
                        if gist_id_input:
                            st.session_state.gist_id = gist_id_input
                        st.success("✅ Connected!")
                        st.rerun()

        st.divider()

        # ── API Provider ──
        provider = st.selectbox(
            "AI Provider",
            options=["openai", "deepseek"],
            index=0 if data['settings'].get('api_provider', 'openai') == 'openai' else 1
        )
        if provider != data['settings'].get('api_provider'):
            data['settings']['api_provider'] = provider
            save_data(data)

        api_key_configured = False
        if provider == 'openai':
            if secrets.get('openai_key'):
                st.success("✅ OpenAI: Configured")
                api_key_configured = True
            else:
                api_key = st.text_input(
                    "OpenAI API Key",
                    value=data['settings'].get('api_key', ''),
                    type="password"
                )
                if api_key != data['settings'].get('api_key', ''):
                    data['settings']['api_key'] = api_key
                    save_data(data)
                    st.success("✅ Saved!")
                api_key_configured = bool(api_key)

        elif provider == 'deepseek':
            if secrets.get('deepseek_key'):
                st.success("✅ DeepSeek: Configured")
                api_key_configured = True
            else:
                deepseek_key = st.text_input(
                    "DeepSeek API Key",
                    value=data['settings'].get('deepseek_key', ''),
                    type="password"
                )
                if deepseek_key != data['settings'].get('deepseek_key', ''):
                    data['settings']['deepseek_key'] = deepseek_key
                    save_data(data)
                    st.success("✅ Saved!")
                api_key_configured = bool(deepseek_key)

        st.divider()

        # ── Dynamic streak display ──
        streak = data['daily_streak']
        streak_icon = get_streak_icon(streak)
        st.markdown(
            f'<div class="streak-display">{streak_icon} {streak}-day streak</div>',
            unsafe_allow_html=True
        )

        # ── Today's progress bar ──
        today_phrases_sidebar = get_today_phrases(data, count=st.session_state.learn_mode)
        completed_count = len(st.session_state.reviewed_today)
        total_count = len(today_phrases_sidebar)

        st.markdown("**Today's Progress**")
        if total_count > 0:
            progress_val = min(completed_count / total_count, 1.0)
            st.progress(progress_val, text=f"✅ {completed_count} / {total_count} completed")
        else:
            st.progress(1.0, text="🎉 All done!")

        st.divider()

        # ── Phrase pool ──
        st.subheader("📦 Phrase Pool")
        available = len([p for p in data['phrase_pool']
                         if not any(p['phrase'] == lp['phrase'] for lp in data['learning'])
                         and not any(p['phrase'] == mp['phrase'] for mp in data['mastered'])])
        st.metric("Available", available)

        if api_key_configured:
            if st.button("🔄 Generate 5 New"):
                success, result = generate_new_phrases(data, count=5)
                if success:
                    st.success(f"✅ Added {result}!")
                    st.rerun()
                else:
                    st.error(f"❌ {result}")

        st.divider()
        st.metric("📖 Learning", len(data['learning']))
        st.metric("✅ Mastered", len(data['mastered']))

        st.divider()
        st.subheader("🔄 Reset")
        if st.button("🗑️ Delete Local Data", type="secondary"):
            if DATA_FILE.exists():
                DATA_FILE.unlink()
                st.success("✅ Local file deleted")
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.warning("⚠️ Please refresh the page")
            st.info("Next save will create a fresh Gist")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MAIN TABS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    tab1, tab2, tab3 = st.tabs(["📚 Today's Learning", "💬 Practice Chat", "📊 Progress"])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB 1 — Today's Learning
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab1:
        st.title("📚 Today's Learning")

        # Auto-refill phrase pool if running low
        refill_result = check_and_refill_pool(data, threshold=10)
        if refill_result[0] is True:
            st.info(f"🤖 Auto-generated {refill_result[1]} new phrases!")

        col_title, col_mode = st.columns([3, 1])
        with col_mode:
            st.selectbox("Phrases/day", [5, 10, 15, 20], key='learn_mode')

        today_phrases = get_today_phrases(data, count=st.session_state.learn_mode)

        if not today_phrases:
            st.success("🎉 All done for today! Come back tomorrow.")
        else:
            done_count = len(st.session_state.reviewed_today)
            st.info(f"📌 {len(today_phrases)} phrases today — {done_count} completed")

            for i, phrase_data in enumerate(today_phrases, 1):
                phrase_text = phrase_data['phrase']
                category = phrase_data.get('category', 'Daily')
                cat_emoji = get_category_color(category)

                # Determine proficiency level
                is_mastered = any(p['phrase'] == phrase_text for p in data['mastered'])
                learning_info = next(
                    (p for p in data['learning'] if p['phrase'] == phrase_text), None
                )
                review_count = learning_info.get('review_count', 0) if learning_info else 0
                proficiency_icon = get_proficiency_icon(review_count, is_mastered)
                already_done = phrase_text in st.session_state.reviewed_today

                # ── Phrase Card (Material-style) ──────────────────────────────
                with st.container(border=True):
                    header_col, action_col = st.columns([4, 1])

                    with header_col:
                        st.markdown(f"### {proficiency_icon} {phrase_text}")
                        st.markdown(
                            f'<span class="cat-badge">{cat_emoji} {category}</span>',
                            unsafe_allow_html=True
                        )
                        if learning_info:
                            next_rev = phrase_data.get('next_review', '?')
                            st.caption(
                                f"Review #{review_count + 1} · next review: {next_rev}"
                            )

                    with action_col:
                        st.write("")  # vertical breathing room
                        if already_done:
                            st.success("✅ Done!")
                        else:
                            if st.button(
                                "✅ Mark Done",
                                key=f"review_{i}",
                                type="primary"
                            ):
                                mark_reviewed(data, phrase_text)
                                update_streak(data)
                                st.session_state.reviewed_today.add(phrase_text)
                                st.session_state.just_reviewed = True
                                st.rerun()

                    # ── Active Recall: details hidden by default ──────────────
                    with st.expander("🧠 Reveal: Translation & Example"):
                        st.markdown(f"**🇨🇳 中文：** {phrase_data['chinese']}")
                        st.markdown(
                            f"**✍️ Example：**  \n> *{phrase_data['example']}*"
                        )

                    # ── TTS pronunciation ─────────────────────────────────────
                    tts_col, _ = st.columns([1, 3])
                    with tts_col:
                        if TTS_AVAILABLE:
                            tts_key = f'show_audio_{i}'
                            if st.button("🔊 Listen", key=f"tts_btn_{i}"):
                                st.session_state[tts_key] = not st.session_state.get(tts_key, False)
                            if st.session_state.get(tts_key, False):
                                audio_bytes = get_tts_audio(phrase_text)
                                if audio_bytes:
                                    st.audio(audio_bytes, format='audio/mp3')
                                else:
                                    st.caption("TTS failed — check internet")
                        else:
                            st.caption("Install `gTTS` for 🔊")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # DAILY CHALLENGE MODULE
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        st.divider()

        provider_name = data['settings'].get('api_provider', 'openai')
        has_api_key = bool(
            data['settings'].get(
                'api_key' if provider_name == 'openai' else 'deepseek_key', ''
            )
        )

        with st.container(border=True):
            st.subheader("🎯 Daily Challenge")
            st.caption("Fill in the blanks — reinforce all 5 phrases at once")

            if len(today_phrases) < 5:
                st.info("Need at least 5 phrases to generate a Daily Challenge.")
            elif not has_api_key:
                st.warning("⚠️ Configure an API Key in the sidebar to unlock Daily Challenge.")
            else:
                challenge = st.session_state.challenge_data

                # Generate / reset controls
                gen_col, reset_col = st.columns([2, 1])
                with gen_col:
                    if challenge is None:
                        if st.button("🎲 Generate Today's Challenge", type="primary"):
                            result, error = generate_daily_challenge(data, today_phrases[:5])
                            if result:
                                st.session_state.challenge_data = result
                                st.session_state.challenge_passed = False
                                st.rerun()
                            else:
                                st.error(f"❌ {error}")
                with reset_col:
                    if challenge is not None and not st.session_state.challenge_passed:
                        if st.button("🔄 New Story"):
                            st.session_state.challenge_data = None
                            st.session_state.challenge_passed = False
                            st.rerun()

                if challenge:
                    if st.session_state.challenge_passed:
                        st.success("🌟 Challenge completed! All 5 phrases marked as reviewed.")
                    else:
                        # Render story with highlighted blank placeholders
                        story_html = challenge['story']
                        for j in range(1, 6):
                            story_html = story_html.replace(
                                f'[BLANK_{j}]',
                                f'<span class="blank-tag">__ {j} __</span>'
                            )
                        st.markdown(
                            f'<div class="story-box">{story_html}</div>',
                            unsafe_allow_html=True
                        )

                        # Input fields (3-column grid)
                        answers = challenge.get('answers', [])
                        user_inputs = []
                        input_cols = st.columns(min(len(answers), 3))
                        for j, _ in enumerate(answers):
                            col_idx = j % 3
                            with input_cols[col_idx]:
                                val = st.text_input(
                                    f"Blank {j + 1}:",
                                    key=f"blank_input_{j}",
                                    placeholder="type the phrase…"
                                )
                                user_inputs.append(val)

                        # Submit & check
                        if st.button("📝 Submit Answers", type="primary"):
                            results = [
                                u.strip().lower() == c.strip().lower()
                                for u, c in zip(user_inputs, answers)
                            ]
                            all_correct = all(results)

                            if all_correct:
                                st.session_state.challenge_passed = True
                                st.balloons()
                                # Auto-mark all 5 challenge phrases as reviewed
                                for p in today_phrases[:5]:
                                    if p['phrase'] not in st.session_state.reviewed_today:
                                        mark_reviewed(data, p['phrase'])
                                        st.session_state.reviewed_today.add(p['phrase'])
                                update_streak(data)
                                st.rerun()
                            else:
                                st.error("Some blanks are wrong — try again!")
                                for j, (res, correct) in enumerate(zip(results, answers)):
                                    if res:
                                        st.markdown(f"✅ Blank {j + 1}: correct!")
                                    else:
                                        hint = correct[:3] + "…"
                                        given = user_inputs[j] or "(empty)"
                                        st.markdown(
                                            f"❌ Blank {j + 1}: `{given}` — hint: *{hint}*"
                                        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB 2 — Practice Chat
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab2:
        st.title("💬 Practice")

        provider_name = data['settings'].get('api_provider', 'openai')
        has_key = bool(
            data['settings'].get('api_key' if provider_name == 'openai' else 'deepseek_key', '')
        )

        if not has_key:
            st.warning("⚠️ Add an API Key in the sidebar to enable Practice Chat.")
        else:
            today_phrases_chat = get_today_phrases(data, count=5)
            keywords = [p['phrase'] for p in today_phrases_chat[:5]]

            if keywords:
                st.info(f"**Keywords:** {', '.join(keywords)}")

            if 'messages' not in st.session_state:
                st.session_state.messages = []
                system_msg = (
                    f"You are a friendly English teacher. Today's phrases: {', '.join(keywords)}. "
                    "Encourage their usage, point out mistakes gently."
                )
                with st.spinner("Starting conversation…"):
                    initial = call_ai_api(data, [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": "Hi!"}
                    ])
                st.session_state.messages.append({"role": "assistant", "content": initial})
                st.session_state.system_context = system_msg

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

            if prompt := st.chat_input("Type here…"):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("🤔"):
                        api_msgs = [{"role": "system", "content": st.session_state.system_context}]
                        api_msgs.extend(
                            [{"role": m["role"], "content": m["content"]}
                             for m in st.session_state.messages[-10:]]
                        )
                        response = call_ai_api(data, api_msgs)
                    st.write(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

            if st.button("🔄 New Conversation"):
                st.session_state.messages = []
                if 'system_context' in st.session_state:
                    del st.session_state.system_context
                st.rerun()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB 3 — Progress
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab3:
        st.title("📊 Progress")

        streak = data['daily_streak']
        col1, col2, col3 = st.columns(3)
        col1.metric(f"{get_streak_icon(streak)} Streak", f"{streak} days")
        col2.metric("📖 Learning", len(data['learning']))
        col3.metric("✅ Mastered", len(data['mastered']))

        if data['learning']:
            st.subheader("📚 In Progress")
            df = pd.DataFrame([{
                'Phrase': p['phrase'],
                'Proficiency': get_proficiency_icon(p.get('review_count', 0)),
                'Category': p.get('category', 'Daily'),
                'Next Review': p.get('next_review', 'N/A'),
                'Reviews Done': p.get('review_count', 0)
            } for p in data['learning']])
            st.dataframe(df, use_container_width=True)

        if data['mastered']:
            st.subheader("🌳 Mastered")
            df_mastered = pd.DataFrame([{
                'Phrase': p['phrase'],
                'Chinese': p.get('chinese', ''),
                'Category': p.get('category', 'Daily')
            } for p in data['mastered']])
            st.dataframe(df_mastered, use_container_width=True)


if __name__ == "__main__":
    main()
