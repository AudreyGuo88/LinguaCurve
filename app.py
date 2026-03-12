import streamlit as st
import streamlit.components.v1 as components
import json
import base64
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
            secrets['owner_password'] = st.secrets.get("OWNER_PASSWORD", "")
            secrets['auto_login_key'] = st.secrets.get("AUTO_LOGIN_KEY", "")
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
CLOUD_SYNC_IDLE_SECONDS = 600

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


def _migrate_data(data):
    """Normalise and migrate loaded data (shared by Gist + local file paths)."""
    if 'settings' not in data:
        data['settings'] = {}
    # Keys are never loaded from storage; injected at runtime based on auth
    data['settings']['api_key'] = ''
    data['settings']['deepseek_key'] = ''
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
    # Migrate: add dismissed list
    if 'dismissed' not in data:
        data['dismissed'] = []
    return data


def load_data():
    """Load data from Gist or local file, falling back to fresh data."""
    secrets = load_secrets()
    github_token = st.session_state.get('github_token', '')
    gist_id = st.session_state.get('gist_id', '')

    if github_token and gist_id:
        storage = GistStorage(github_token, gist_id)
        data, error = storage.read_gist()

        if data:
            return _migrate_data(data)

    # Fallback: read from local file
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return _migrate_data(data)
        except Exception:
            pass

    # Create fresh data if nothing exists
    return {
        "phrase_pool": DEFAULT_PHRASE_POOL,
        "learning": [],
        "mastered": [],
        "dismissed": [],
        "daily_streak": 0,
        "last_study_date": None,
        "settings": {
            "api_key": "",
            "api_provider": "openai",
            "deepseek_key": ""
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

    dismissed_set = {p['phrase'] for p in data.get('dismissed', [])}

    needed = count - len(due_phrases)
    new_phrases = []
    if needed > 0:
        available = [p for p in data['phrase_pool']
                     if not any(p['phrase'] == lp['phrase'] for lp in data['learning'])
                     and not any(p['phrase'] == mp['phrase'] for mp in data['mastered'])
                     and p['phrase'] not in dismissed_set]
        new_phrases = available[:needed]

    return due_phrases + new_phrases


def calculate_next_review(review_count):
    """Calculate next review date based on Ebbinghaus curve"""
    intervals = [1, 3, 7, 15]
    if review_count >= len(intervals):
        return None
    return (datetime.now() + timedelta(days=intervals[review_count])).strftime('%Y-%m-%d')


def mark_reviewed(data, phrase_text, save_now=True):
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

            if save_now:
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
        if save_now:
            save_data(data)
        return True

    return False


def dismiss_phrase(data, phrase_text, save_now=True):
    """Remove a phrase from the SRS cycle."""
    # Already in learning — move it out
    for phrase in data['learning']:
        if phrase['phrase'] == phrase_text:
            phrase['dismissed_on'] = datetime.now().strftime('%Y-%m-%d')
            data.setdefault('dismissed', []).append(phrase)
            data['learning'].remove(phrase)
            if save_now:
                save_data(data)
            return True

    # New phrase (only in pool) — add directly to dismissed
    phrase_data = next((p for p in data['phrase_pool'] if p['phrase'] == phrase_text), None)
    if phrase_data:
        data.setdefault('dismissed', []).append({
            "phrase": phrase_text,
            "chinese": phrase_data.get('chinese', ''),
            "example": phrase_data.get('example', ''),
            "category": phrase_data.get('category', 'Daily'),
            "review_count": 0,
            "dismissed_on": datetime.now().strftime('%Y-%m-%d'),
        })
        if save_now:
            save_data(data)
        return True

    return False


def restore_phrase(data, phrase_text):
    """Move a phrase from dismissed or mastered back into the learning queue."""
    for source in ('dismissed', 'mastered'):
        for phrase in data.get(source, []):
            if phrase['phrase'] == phrase_text:
                data[source].remove(phrase)
                data['learning'].append({
                    "phrase": phrase['phrase'],
                    "chinese": phrase.get('chinese', ''),
                    "example": phrase.get('example', ''),
                    "category": phrase.get('category', 'Daily'),
                    "review_count": 0,
                    "last_review": datetime.now().strftime('%Y-%m-%d'),
                    "next_review": calculate_next_review(0),
                })
                save_data(data)
                return True
    return False


def update_streak(data, save_now=True):
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
        if save_now:
            save_data(data)


def save_data(data, force_cloud=False):
    """Save data locally/session immediately; cloud sync is deferred until idle or forced."""
    data_to_save = copy.deepcopy(data)
    if 'settings' in data_to_save:
        data_to_save['settings']['api_key'] = ''
        data_to_save['settings']['deepseek_key'] = ''

    # -- Guest mode: keep data in session only, never write to disk / Gist --
    if not st.session_state.get('owner_authenticated', False):
        st.session_state.guest_data = data_to_save
        return

    # -- Owner mode: persist locally first (fast and reliable) --
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"⚠️ Local save failed: {e}")

    github_token = st.session_state.get('github_token', '')
    gist_id = st.session_state.get('gist_id', '')
    if not github_token:
        return

    now_ts = time.time()

    if force_cloud:
        payload = st.session_state.get('cloud_sync_pending_data', data_to_save)
    else:
        # Debounce cloud sync: only push after user has been idle for the configured window.
        st.session_state.cloud_sync_pending_data = data_to_save
        st.session_state.cloud_last_change_ts = now_ts
        st.session_state.cloud_sync_pending = True
        st.session_state.cloud_sync_status = 'pending'
        return

    storage = GistStorage(github_token, gist_id)
    success, error = storage.update_gist(payload)

    if success:
        if not gist_id and storage.gist_id:
            st.session_state.gist_id = storage.gist_id
            st.success(f"✅ Gist created! ID: {storage.gist_id}")
        st.session_state.cloud_sync_pending = False
        st.session_state.cloud_sync_status = 'synced'
        st.session_state.cloud_last_sync_ts = now_ts
        st.session_state.cloud_sync_pending_data = payload
    elif error:
        st.session_state.cloud_sync_pending = True
        st.session_state.cloud_sync_status = f"error: {error}"
        if force_cloud:
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


def get_phrase_data(data, phrase_text):
    """Look up full phrase data from any list."""
    for source in ('learning', 'mastered', 'dismissed', 'phrase_pool'):
        for p in data.get(source, []):
            if p['phrase'] == phrase_text:
                return p
    return None


def remove_dismissed_from_session_today(data):
    """Keep today's locked list in sync after phrases are marked as known."""
    dismissed_texts = {p['phrase'] for p in data.get('dismissed', [])}
    if not dismissed_texts:
        return

    locked = st.session_state.get('session_today_phrases', [])
    filtered_locked = [p for p in locked if p['phrase'] not in dismissed_texts]
    if len(filtered_locked) == len(locked):
        return

    removed = {p['phrase'] for p in locked if p['phrase'] in dismissed_texts}
    st.session_state.session_today_phrases = filtered_locked
    st.session_state.reviewed_today = {
        p for p in st.session_state.get('reviewed_today', set()) if p not in removed
    }
    st.session_state.session_new_phrases = {
        p for p in st.session_state.get('session_new_phrases', set()) if p not in removed
    }
    st.session_state.session_review_phrases = {
        p for p in st.session_state.get('session_review_phrases', set()) if p not in removed
    }

def remove_phrase_from_session_today(phrase_text):
    """Immediately remove a resolved phrase from today's session state."""
    locked = st.session_state.get('session_today_phrases', [])
    filtered_locked = [p for p in locked if p['phrase'] != phrase_text]
    if len(filtered_locked) == len(locked):
        return

    st.session_state.session_today_phrases = filtered_locked
    st.session_state.reviewed_today.discard(phrase_text)
    st.session_state.session_new_phrases.discard(phrase_text)
    st.session_state.session_review_phrases.discard(phrase_text)


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


@st.cache_data(show_spinner=False)
def _tts_b64(text):
    """Return base64-encoded MP3 for text (cached per unique text)."""
    if not TTS_AVAILABLE:
        return None
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return base64.b64encode(fp.getvalue()).decode()
    except Exception:
        return None


def tts_button(text, key, label="🔊"):
    """Render a Listen button that plays audio invisibly (no player widget)."""
    if not TTS_AVAILABLE:
        return
    if st.button(label, key=key, help="Listen"):
        b64 = _tts_b64(text)
        if b64:
            # JS Audio object is DOM-independent: survives re-renders
            components.html(
                f"<script>(new Audio('data:audio/mp3;base64,{b64}')).play()</script>",
                height=0
            )
        else:
            st.caption("⚠️ TTS unavailable")


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
/* ── Base phrase card ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
    border: 1px solid #e0e7ff !important;
    box-shadow: 0 2px 12px rgba(99, 102, 241, 0.07) !important;
    background: linear-gradient(135deg, #fafbff 0%, #f5f0ff 100%) !important;
    transition: background 0.3s ease, box-shadow 0.2s ease, opacity 0.3s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.16) !important;
}
/* ── Done card: muted green state via :has() ── */
[data-testid="stVerticalBlockBorderWrapper"]:has(.done-card-marker) {
    background: linear-gradient(135deg, #f0fdf4 0%, #d1fae5 100%) !important;
    border-color: #6ee7b7 !important;
    box-shadow: 0 1px 6px rgba(16, 185, 129, 0.08) !important;
    opacity: 0.78;
}
/* ── Done badge ── */
.done-badge {
    display: inline-block;
    background: #d1fae5;
    color: #065f46;
    border: 1px solid #6ee7b7;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.78em;
    font-weight: 700;
    margin-right: 6px;
}
/* ── Category badge ── */
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
/* ── Word Bank chips (Practice tab) ── */
.word-chip {
    display: inline-block;
    background: #f1f5f9;
    border: 1.5px solid #cbd5e1;
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 0.88em;
    font-weight: 600;
    color: #475569;
}
.word-chip-used {
    background: #dcfce7;
    border-color: #6ee7b7;
    color: #065f46;
}
/* ── Challenge story box ── */
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
/* ── Sidebar streak ── */
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
    if 'learn_mode' not in st.session_state:
        st.session_state.learn_mode = 5
    if 'challenge_data' not in st.session_state:
        st.session_state.challenge_data = None
    if 'challenge_passed' not in st.session_state:
        st.session_state.challenge_passed = False
    if 'reveal_all' not in st.session_state:
        st.session_state.reveal_all = False
    if 'celebration_fired' not in st.session_state:
        st.session_state.celebration_fired = False
    if 'owner_authenticated' not in st.session_state:
        st.session_state.owner_authenticated = False
        # Auto-login via URL token, e.g. ?key=YOUR_SECRET
        auto_key = secrets.get('auto_login_key', '')
        if auto_key and st.query_params.get('key') == auto_key:
            st.session_state.owner_authenticated = True
    if 'guest_openai_key' not in st.session_state:
        st.session_state.guest_openai_key = ''
    if 'guest_deepseek_key' not in st.session_state:
        st.session_state.guest_deepseek_key = ''
    if 'nav_to_tab' not in st.session_state:
        st.session_state.nav_to_tab = None
    # Locked phrase set for today — fixed at session start, never changes mid-session
    if 'session_today_phrases' not in st.session_state:
        st.session_state.session_today_phrases = []
    if 'session_locked_mode' not in st.session_state:
        st.session_state.session_locked_mode = None
    # Categorisation: which locked phrases are brand-new vs SRS-due reviews
    if 'session_new_phrases' not in st.session_state:
        st.session_state.session_new_phrases = set()
    if 'session_review_phrases' not in st.session_state:
        st.session_state.session_review_phrases = set()
    if 'cloud_sync_pending' not in st.session_state:
        st.session_state.cloud_sync_pending = False
    if 'cloud_sync_status' not in st.session_state:
        st.session_state.cloud_sync_status = 'idle'
    if 'cloud_last_sync_ts' not in st.session_state:
        st.session_state.cloud_last_sync_ts = 0.0
    if 'cloud_sync_idle_seconds' not in st.session_state:
        st.session_state.cloud_sync_idle_seconds = CLOUD_SYNC_IDLE_SECONDS
    if 'cloud_last_change_ts' not in st.session_state:
        st.session_state.cloud_last_change_ts = 0.0
    if 'cloud_sync_pending_data' not in st.session_state:
        st.session_state.cloud_sync_pending_data = None
    if 'progress_mode' not in st.session_state:
        st.session_state.progress_mode = 'in_progress'

    # ── Load data ─────────────────────────────────────────────────────────────
    if st.session_state.owner_authenticated:
        # Owner: real persistent data from file / Gist
        data = load_data()
    else:
        # Guest: isolated in-memory data, never touches owner's storage
        if 'guest_data' not in st.session_state:
            st.session_state.guest_data = {
                "phrase_pool": copy.deepcopy(DEFAULT_PHRASE_POOL),
                "learning": [],
                "mastered": [],
                "dismissed": [],
                "daily_streak": 0,
                "last_study_date": None,
                "settings": {"api_key": "", "api_provider": "openai", "deepseek_key": ""}
            }
        data = st.session_state.guest_data

    # ── Inject API keys based on auth state (never from saved data) ──────────
    if st.session_state.owner_authenticated:
        data['settings']['api_key'] = secrets.get('openai_key', '')
        data['settings']['deepseek_key'] = secrets.get('deepseek_key', '')
    else:
        # Use guest-supplied keys (stored in session state, not persisted)
        data['settings']['api_key'] = st.session_state.guest_openai_key
        data['settings']['deepseek_key'] = st.session_state.guest_deepseek_key

    # Opportunistic cloud sync: when there is pending data and idle window is reached.
    if (
        st.session_state.owner_authenticated
        and st.session_state.get('github_token')
        and st.session_state.get('cloud_sync_pending', False)
    ):
        idle_seconds = st.session_state.get('cloud_sync_idle_seconds', CLOUD_SYNC_IDLE_SECONDS)
        last_change_ts = st.session_state.get('cloud_last_change_ts', 0.0)
        if (time.time() - last_change_ts) >= idle_seconds:
            save_data(data, force_cloud=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SIDEBAR
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with st.sidebar:
        st.title("📚 EchoRecall")

        # ── Owner Login ────────────────────────────────────────────────────────
        owner_pwd_configured = bool(secrets.get('owner_password'))
        if st.session_state.owner_authenticated:
            st.success("👑 Owner mode")
            if st.button("🔓 Logout", key="owner_logout"):
                st.session_state.owner_authenticated = False
                st.session_state.guest_openai_key = ''
                st.session_state.guest_deepseek_key = ''
                st.session_state.session_today_phrases = []
                st.session_state.reviewed_today = set()
                st.rerun()
        else:
            with st.expander("🔐 Owner Login"):
                if owner_pwd_configured:
                    pwd_input = st.text_input("Password", type="password", key="owner_pwd_input")
                    if st.button("Login", key="owner_login_btn"):
                        if pwd_input == secrets.get('owner_password', ''):
                            st.session_state.owner_authenticated = True
                            st.session_state.session_today_phrases = []
                            st.session_state.reviewed_today = set()
                            st.rerun()
                        else:
                            st.error("Incorrect password")
                else:
                    st.caption("Set `OWNER_PASSWORD` in `.streamlit/secrets.toml` to enable owner login.")

        st.divider()

        # Cloud connection status
        if st.session_state.get('github_token'):
            cloud_pending = st.session_state.get('cloud_sync_pending', False)
            cloud_status = st.session_state.get('cloud_sync_status', 'idle')

            if cloud_pending:
                st.warning("☁️ Cloud: Pending (sync after 10m idle)")
            elif isinstance(cloud_status, str) and cloud_status.startswith('error:'):
                st.warning("☁️ Cloud: Retry pending")
            elif cloud_status == 'synced':
                st.success("☁️ Cloud: Synced")
            else:
                st.success("☁️ Cloud: Connected")

            if st.session_state.get('gist_id'):
                st.caption(f"Gist: `{st.session_state.gist_id[:8]}...`")

            if st.button("☁️ Sync Now", key="cloud_sync_now", use_container_width=True):
                save_data(data, force_cloud=True)
                st.rerun()

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

        # ── AI Provider ──
        provider = st.selectbox(
            "AI Provider",
            options=["openai", "deepseek"],
            index=0 if data['settings'].get('api_provider', 'openai') == 'openai' else 1
        )
        if provider != data['settings'].get('api_provider'):
            data['settings']['api_provider'] = provider
            save_data(data)

        api_key_configured = False
        if st.session_state.owner_authenticated:
            # Owner: use key from secrets silently
            if provider == 'openai':
                if secrets.get('openai_key'):
                    st.success("✅ OpenAI: Active")
                    api_key_configured = True
                else:
                    st.warning("⚠️ No OPENAI_API_KEY in secrets.toml")
            else:
                if secrets.get('deepseek_key'):
                    st.success("✅ DeepSeek: Active")
                    api_key_configured = True
                else:
                    st.warning("⚠️ No DEEPSEEK_API_KEY in secrets.toml")
        else:
            # Guest: must supply their own key
            st.info("👋 Enter your own API key to use AI features")
            if provider == 'openai':
                guest_key = st.text_input(
                    "Your OpenAI API Key",
                    value=st.session_state.guest_openai_key,
                    type="password",
                    key="guest_openai_input"
                )
                if guest_key != st.session_state.guest_openai_key:
                    st.session_state.guest_openai_key = guest_key
                    data['settings']['api_key'] = guest_key
                api_key_configured = bool(st.session_state.guest_openai_key)
            else:
                guest_key = st.text_input(
                    "Your DeepSeek API Key",
                    value=st.session_state.guest_deepseek_key,
                    type="password",
                    key="guest_deepseek_input"
                )
                if guest_key != st.session_state.guest_deepseek_key:
                    st.session_state.guest_deepseek_key = guest_key
                    data['settings']['deepseek_key'] = guest_key
                api_key_configured = bool(st.session_state.guest_deepseek_key)

        st.divider()

        # ── Dynamic streak display ──
        streak = data['daily_streak']
        streak_icon = get_streak_icon(streak)
        st.markdown(
            f'<div class="streak-display">{streak_icon} {streak}-day streak</div>',
            unsafe_allow_html=True
        )

        # ── Lock today's phrase set once per session / learn_mode ────────────
        if (not st.session_state.session_today_phrases or
                st.session_state.session_locked_mode != st.session_state.learn_mode):
            fresh = get_today_phrases(data, count=st.session_state.learn_mode)
            st.session_state.session_today_phrases = fresh
            st.session_state.session_locked_mode = st.session_state.learn_mode
            # Re-categorise new vs review
            learning_set_now = {p['phrase'] for p in data['learning']}
            st.session_state.session_new_phrases = {
                p['phrase'] for p in fresh if p['phrase'] not in learning_set_now
            }
            st.session_state.session_review_phrases = {
                p['phrase'] for p in fresh if p['phrase'] in learning_set_now
            }

        # If user marks "I Know This", make sure it disappears from today's locked list.
        remove_dismissed_from_session_today(data)
        locked_phrases = st.session_state.session_today_phrases

        # ── Today's progress bar ──
        completed_count = sum(
            1 for p in locked_phrases if p['phrase'] in st.session_state.reviewed_today
        )
        total_count = len(locked_phrases)

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

        # ── 4-item navigation library ──────────────────────────────────────────

        # 1 & 2: In Progress / Mastered — nav buttons → Progress tab (with mode pre-set)
        if st.button(f"📖 In Progress  ({len(data['learning'])})", use_container_width=True):
            st.session_state.nav_to_tab = 2
            st.session_state.progress_mode = 'in_progress'
            st.rerun()
        if st.button(f"✅ Mastered  ({len(data['mastered'])})", use_container_width=True):
            st.session_state.nav_to_tab = 2
            st.session_state.progress_mode = 'mastered'
            st.rerun()

        # 3. New Today — brand-new phrases (from phrase_pool, no review_count field)
        new_today_list = [p for p in locked_phrases
                          if 'review_count' not in p]
        new_done_count = sum(1 for p in new_today_list if p['phrase'] in st.session_state.reviewed_today)
        with st.expander(f"🌱 New Today ({new_done_count}/{len(new_today_list)})"):
            for p in new_today_list:
                done_mark = " ✅" if p['phrase'] in st.session_state.reviewed_today else ""
                st.markdown(f"**{p['phrase']}**{done_mark}")
                st.caption(f"> {p['example']}")

        # 4. Reviewed Today — SRS-due phrases (from data['learning'], have review_count field)
        rev_today_list = [p for p in locked_phrases
                          if 'review_count' in p]
        if rev_today_list:
            rev_done_count = sum(1 for p in rev_today_list if p['phrase'] in st.session_state.reviewed_today)
            with st.expander(f"🔁 Reviewed Today ({rev_done_count}/{len(rev_today_list)})"):
                for p in rev_today_list:
                    done_mark = " ✅" if p['phrase'] in st.session_state.reviewed_today else ""
                    st.markdown(f"**{p['phrase']}**{done_mark}")
                    st.caption(f"> {p['example']}")

        if not st.session_state.owner_authenticated:
            st.divider()
            st.caption("🔒 Guest session — data resets on refresh")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MAIN TABS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    tab1, tab2, tab3 = st.tabs(["📚 Today's Learning", "💬 Practice Chat", "📊 Progress"])

    def handle_mark_done(phrase_text):
        if mark_reviewed(data, phrase_text, save_now=False):
            st.session_state.reviewed_today.add(phrase_text)
            update_streak(data, save_now=False)
            save_data(data)

    def handle_mark_known(phrase_text):
        if dismiss_phrase(data, phrase_text, save_now=False):
            remove_phrase_from_session_today(phrase_text)
            save_data(data)

    # ── JS tab navigation (fires once when nav_to_tab is set by sidebar) ──────
    if st.session_state.nav_to_tab is not None:
        tab_idx = st.session_state.nav_to_tab
        st.session_state.nav_to_tab = None
        components.html(f"""
        <script>
        setTimeout(function() {{
            var tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
            if (tabs.length > {tab_idx}) tabs[{tab_idx}].click();
        }}, 100);
        </script>
        """, height=0)

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

        # Use the locked session set — never changes mid-session
        today_phrases = st.session_state.session_today_phrases

        if not today_phrases:
            st.success("🎉 All done for today! Come back tomorrow.")
        else:
            # Split using the locked set so completed phrases stay visible
            pending_phrases = [p for p in today_phrases if p['phrase'] not in st.session_state.reviewed_today]
            learned_phrases = [p['phrase'] for p in today_phrases if p['phrase'] in st.session_state.reviewed_today]

            done_count = len(learned_phrases)
            total_count_t1 = len(today_phrases)
            pct = min(done_count / total_count_t1, 1.0) if total_count_t1 > 0 else 0.0
            progress_emoji = (
                "🎉" if pct >= 1.0 else
                "🔥" if pct >= 0.75 else
                "💪" if pct >= 0.5 else
                "🌱" if pct > 0 else
                "📋"
            )
            st.progress(pct, text=f"{progress_emoji}  {done_count} / {total_count_t1} phrases completed")

            # ── 🎉 Fire celebration when all phrases done (once per session) ─
            if pct >= 1.0 and total_count_t1 > 0 and not st.session_state.celebration_fired:
                st.balloons()
                st.session_state.celebration_fired = True

            # ── Bulk reveal/hide controls ──────────────────────────────────
            reveal_col, hide_col, _ = st.columns([1, 1, 5])
            with reveal_col:
                if st.button("👁 Reveal All"):
                    st.session_state.reveal_all = True
                    st.rerun()
            with hide_col:
                if st.button("🙈 Hide All"):
                    st.session_state.reveal_all = False
                    st.rerun()

            # ── Section 1: Up Next ─────────────────────────────────────────
            if pending_phrases:
                review_ct = sum(1 for p in pending_phrases if 'review_count' in p)
                new_ct = len(pending_phrases) - review_ct
                if review_ct > 0 and new_ct > 0:
                    up_next_sub = f"{new_ct} new · {review_ct} SRS reviews"
                elif review_ct > 0:
                    up_next_sub = f"{review_ct} SRS reviews (phrases you learned before)"
                else:
                    up_next_sub = f"{new_ct} new"
                st.markdown(f"#### 📋 Up Next — {up_next_sub}")
                for idx, phrase_data in enumerate(pending_phrases):
                    phrase_text = phrase_data['phrase']
                    category = phrase_data.get('category', 'Daily')
                    cat_emoji = get_category_color(category)

                    is_mastered = any(p['phrase'] == phrase_text for p in data['mastered'])
                    learning_info = next(
                        (p for p in data['learning'] if p['phrase'] == phrase_text), None
                    )
                    review_count = learning_info.get('review_count', 0) if learning_info else 0
                    proficiency_icon = get_proficiency_icon(review_count, is_mastered)

                    with st.container(border=True):
                        header_col, action_col = st.columns([4, 1])

                        with header_col:
                            st.markdown(f"### {proficiency_icon} {phrase_text}")
                            is_srs_review = 'review_count' in phrase_data
                            type_badge = (
                                '<span style="background:#fef3c7;color:#92400e;border:1px solid #fcd34d;'
                                'border-radius:12px;padding:2px 9px;font-size:0.75em;font-weight:600;'
                                'margin-right:6px;">🔁 Review</span>'
                                if is_srs_review else
                                '<span style="background:#e0e7ff;color:#4338ca;border:1px solid #a5b4fc;'
                                'border-radius:12px;padding:2px 9px;font-size:0.75em;font-weight:600;'
                                'margin-right:6px;">✨ New</span>'
                            )
                            st.markdown(
                                f'{type_badge}<span class="cat-badge">{cat_emoji} {category}</span>',
                                unsafe_allow_html=True
                            )
                            if learning_info:
                                next_rev = phrase_data.get('next_review', '?')
                                st.caption(f"Review #{review_count + 1} · next: {next_rev}")

                        with action_col:
                            st.write("")
                            st.button(
                                "✅ Mark Done",
                                key=f"review_up_{idx}",
                                type="primary",
                                on_click=handle_mark_done,
                                args=(phrase_text,)
                            )
                            st.button(
                                "⭐ I Know This",
                                key=f"dismiss_up_{idx}",
                                help="I've fully mastered this — remove it from the review schedule",
                                type="secondary",
                                on_click=handle_mark_known,
                                args=(phrase_text,)
                            )

                        with st.expander(
                            "🧠 Reveal: Translation & Example",
                            expanded=st.session_state.reveal_all
                        ):
                            st.markdown(f"**🇨🇳 Chinese:** {phrase_data['chinese']}")
                            ex_col, ex_btn_col = st.columns([6, 1])
                            with ex_col:
                                st.markdown(f"**✍️ Example：**  \n> *{phrase_data['example']}*")
                            with ex_btn_col:
                                tts_button(phrase_data['example'], key=f"tts_ex_up_{idx}")

                        tts_col, _ = st.columns([1, 3])
                        with tts_col:
                            tts_button(phrase_text, key=f"tts_up_{idx}", label="🔊 Listen")

            # ── Section 2: Learned Today ───────────────────────────────────
            if learned_phrases:
                st.markdown(f"#### ✅ Learned Today — {len(learned_phrases)}")
                for idx, phrase_text in enumerate(learned_phrases):
                    pd_full = get_phrase_data(data, phrase_text)
                    if pd_full is None:
                        continue
                    category = pd_full.get('category', 'Daily')
                    cat_emoji = get_category_color(category)
                    is_mastered = any(p['phrase'] == phrase_text for p in data['mastered'])
                    review_count = pd_full.get('review_count', 0)
                    proficiency_icon = get_proficiency_icon(review_count, is_mastered)

                    with st.expander(
                        f"{proficiency_icon} {phrase_text}  ✅",
                        expanded=False
                    ):
                        st.markdown(
                            f'<span class="cat-badge">{cat_emoji} {category}</span>',
                            unsafe_allow_html=True
                        )
                        st.markdown(f"**🇨🇳 Chinese:** {pd_full['chinese']}")
                        ex_col2, ex_btn_col2 = st.columns([6, 1])
                        with ex_col2:
                            st.markdown(f"**✍️ Example：**  \n> *{pd_full['example']}*")
                        with ex_btn_col2:
                            tts_button(pd_full['example'], key=f"tts_ex_done_{idx}")
                        tts_button(phrase_text, key=f"tts_done_{idx}", label="🔊 Listen")

            # ── Load More: when all locked phrases are done ────────────────
            if not pending_phrases and today_phrases:
                locked_texts = {p['phrase'] for p in st.session_state.session_today_phrases}
                dismissed_texts = {p['phrase'] for p in data.get('dismissed', [])}
                mastered_texts = {p['phrase'] for p in data.get('mastered', [])}
                learning_texts = {p['phrase'] for p in data.get('learning', [])}
                extra_pool = [
                    p for p in data['phrase_pool']
                    if p['phrase'] not in learning_texts
                    and p['phrase'] not in mastered_texts
                    and p['phrase'] not in dismissed_texts
                    and p['phrase'] not in locked_texts
                ]
                st.markdown("---")
                if extra_pool:
                    n_more = min(st.session_state.learn_mode, len(extra_pool))
                    load_col, _ = st.columns([2, 3])
                    with load_col:
                        if st.button(f"➕ Load {n_more} More Phrases", type="primary", key="load_more_btn"):
                            st.session_state.session_today_phrases = (
                                st.session_state.session_today_phrases + extra_pool[:n_more]
                            )
                            st.session_state.session_new_phrases.update(
                                {p['phrase'] for p in extra_pool[:n_more]}
                            )
                            st.session_state.celebration_fired = False
                            st.rerun()
                else:
                    st.info("📭 No more phrases available in the pool. Use **🔄 Generate 5 New** in the sidebar to add more.")

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
                                        mark_reviewed(data, p['phrase'], save_now=False)
                                        st.session_state.reviewed_today.add(p['phrase'])
                                update_streak(data, save_now=False)
                                save_data(data)
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
                # ── Word Bank: chip row with live usage tracking ──────────────
                all_user_text = ' '.join(
                    m['content'].lower()
                    for m in st.session_state.get('messages', [])
                    if m['role'] == 'user'
                )
                chips_html = (
                    '<div style="margin:0 0 12px 0;">'
                    '<p style="font-size:0.85em;color:#6b7280;margin-bottom:6px;">'
                    '📋 <strong>Word Bank</strong> — try to use all 5 phrases:</p>'
                    '<div style="display:flex;flex-wrap:wrap;gap:8px;">'
                )
                used_count = 0
                for kw in keywords:
                    used = kw.lower() in all_user_text
                    if used:
                        used_count += 1
                        chips_html += f'<span class="word-chip word-chip-used">{kw} ✓</span>'
                    else:
                        chips_html += f'<span class="word-chip">{kw}</span>'
                chips_html += '</div>'
                if used_count == len(keywords):
                    chips_html += (
                        '<p style="font-size:0.82em;color:#065f46;margin-top:6px;">'
                        '🎉 All phrases used!</p>'
                    )
                else:
                    chips_html += (
                        f'<p style="font-size:0.82em;color:#6b7280;margin-top:6px;">'
                        f'{used_count} / {len(keywords)} used so far</p>'
                    )
                chips_html += '</div>'
                st.markdown(chips_html, unsafe_allow_html=True)

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

            for msg_idx, msg in enumerate(st.session_state.messages):
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    if msg["role"] == "assistant" and TTS_AVAILABLE:
                        if st.button("🔊", key=f"chat_tts_{msg_idx}", help="Listen"):
                            ab = get_tts_audio(msg["content"])
                            if ab:
                                ab.seek(0)
                                st.session_state[f'chat_tts_play_{msg_idx}'] = ab
                        chat_play_key = f'chat_tts_play_{msg_idx}'
                        if chat_play_key in st.session_state:
                            ab = st.session_state[chat_play_key]
                            del st.session_state[chat_play_key]
                            ab.seek(0)
                            st.audio(ab, format='audio/mp3', autoplay=True)

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
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(f"{get_streak_icon(streak)} Streak", f"{streak} days")
        col2.metric("📖 In Progress", len(data['learning']))
        col3.metric("🌳 Mastered", len(data['mastered']))
        col4.metric("⭐ Known", len(data.get('dismissed', [])))

        CATEGORIES = [
            ('Daily', '🏠'),
            ('Business', '💼'),
            ('Social', '👥'),
            ('TV Series', '📺'),
        ]

        st.markdown("### 📚 Progress Browser")
        m1, m2, m3 = st.columns(3)
        with m1:
            if st.button("📖 In Progress", use_container_width=True, type="primary" if st.session_state.progress_mode == 'in_progress' else "secondary"):
                st.session_state.progress_mode = 'in_progress'
                st.rerun()
        with m2:
            if st.button("🌳 Mastered", use_container_width=True, type="primary" if st.session_state.progress_mode == 'mastered' else "secondary"):
                st.session_state.progress_mode = 'mastered'
                st.rerun()
        with m3:
            if st.button("⭐ Known", use_container_width=True, type="primary" if st.session_state.progress_mode == 'known' else "secondary"):
                st.session_state.progress_mode = 'known'
                st.rerun()

        dismissed_set = {p['phrase'] for p in data.get('dismissed', [])}
        mastered_set = {p['phrase'] for p in data.get('mastered', [])}

        if st.session_state.progress_mode == 'in_progress':
            # Safety filter: never show phrases that already exist in Known/Mastered.
            source_list = [
                p for p in data.get('learning', [])
                if p['phrase'] not in dismissed_set and p['phrase'] not in mastered_set
            ]
            mode_title = "📖 In Progress"
            empty_msg = "No phrases in progress."
        elif st.session_state.progress_mode == 'mastered':
            source_list = data.get('mastered', [])
            mode_title = "🌳 Mastered"
            empty_msg = "No mastered phrases yet."
        else:
            source_list = data.get('dismissed', [])
            mode_title = "⭐ Known"
            empty_msg = "No known phrases yet."

        st.markdown(f"#### {mode_title}  `{len(source_list)}`")

        if not source_list:
            st.info(empty_msg)
        else:
            # Compact category cards: click card(expander) to reveal phrase-only list.
            cat_map = {cat: [] for cat, _ in CATEGORIES}
            for p in source_list:
                cat = p.get('category', 'Daily')
                if cat not in cat_map:
                    cat = 'Daily'
                cat_map[cat].append(p['phrase'])

            left_col, right_col = st.columns(2)
            category_columns = [left_col, right_col]
            visible_idx = 0

            for cat, cat_emoji in CATEGORIES:
                phrases = cat_map.get(cat, [])
                if not phrases:
                    continue

                with category_columns[visible_idx % 2]:
                    with st.container(border=True):
                        with st.expander(f"{cat_emoji} {cat}  ({len(phrases)})", expanded=False):
                            for phrase_text in phrases:
                                st.markdown(f"- {phrase_text}")
                visible_idx += 1


if __name__ == "__main__":
    main()
