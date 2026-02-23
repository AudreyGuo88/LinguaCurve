import streamlit as st
import json
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import requests
import time
import copy


# ============================================================================
# Load Secrets (Priority: Streamlit Secrets > User Input)
# ============================================================================

def load_secrets():
    """Load API keys and tokens from Streamlit secrets or session state"""
    secrets = {}

    # Try to load from Streamlit Cloud secrets first
    try:
        if hasattr(st, 'secrets'):
            secrets['github_token'] = st.secrets.get("GITHUB_TOKEN", "")
            secrets['openai_key'] = st.secrets.get("OPENAI_API_KEY", "")
            secrets['deepseek_key'] = st.secrets.get("DEEPSEEK_API_KEY", "")
            secrets['gist_id'] = st.secrets.get("GIST_ID", "")
    except Exception:
        pass

    # Initialize session state with secrets
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
    """Load data from Gist or local file"""
    # Get secrets
    secrets = load_secrets()

    # Try cloud storage first
    github_token = st.session_state.get('github_token', '')
    gist_id = st.session_state.get('gist_id', '')

    if github_token and gist_id:
        storage = GistStorage(github_token, gist_id)
        data, error = storage.read_gist()

        if data:
            # Migrate old data: add category if missing
            for phrase in data.get('phrase_pool', []):
                if 'category' not in phrase:
                    phrase['category'] = 'Daily'
            for phrase in data.get('learning', []):
                if 'category' not in phrase:
                    phrase['category'] = 'Daily'
            for phrase in data.get('mastered', []):
                if 'category' not in phrase:
                    phrase['category'] = 'Daily'

            # Load API keys from secrets if not in data
            if 'settings' not in data:
                data['settings'] = {}
            if not data['settings'].get('api_key') and secrets.get('openai_key'):
                data['settings']['api_key'] = secrets['openai_key']
            if not data['settings'].get('deepseek_key') and secrets.get('deepseek_key'):
                data['settings']['deepseek_key'] = secrets['deepseek_key']

            return data

    # Fallback to local file
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

            # Migrate old data
            for phrase in data.get('phrase_pool', []):
                if 'category' not in phrase:
                    phrase['category'] = 'Daily'
            for phrase in data.get('learning', []):
                if 'category' not in phrase:
                    phrase['category'] = 'Daily'
            for phrase in data.get('mastered', []):
                if 'category' not in phrase:
                    phrase['category'] = 'Daily'

            # Load API keys from secrets
            if 'settings' not in data:
                data['settings'] = {}
            if not data['settings'].get('api_key') and secrets.get('openai_key'):
                data['settings']['api_key'] = secrets['openai_key']
            if not data['settings'].get('deepseek_key') and secrets.get('deepseek_key'):
                data['settings']['deepseek_key'] = secrets['deepseek_key']

            return data

    # Create new data with secrets
    initial_data = {
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

    return initial_data


def load_data():
    """Load data from Gist or create new"""
    # 从 secrets 加载配置
    secrets = load_secrets()

    # 尝试从云端加载
    github_token = st.session_state.get('github_token', '')
    gist_id = st.session_state.get('gist_id', '')

    if github_token and gist_id:
        storage = GistStorage(github_token, gist_id)
        data, error = storage.read_gist()

        if data:
            # 🔒 强制从 Secrets 覆盖 API keys（永远不从 Gist 读取）
            if 'settings' not in data:
                data['settings'] = {}

            # 从 Secrets 加载（覆盖任何 Gist 中的值）
            data['settings']['api_key'] = secrets.get('openai_key', '')
            data['settings']['deepseek_key'] = secrets.get('deepseek_key', '')
            data['settings']['api_provider'] = data['settings'].get('api_provider', 'openai')

            # 迁移：添加 category 字段
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

    # 如果没有 Gist，创建全新数据
    initial_data = {
        "phrase_pool": DEFAULT_PHRASE_POOL,
        "learning": [],
        "mastered": [],
        "daily_streak": 0,
        "last_study_date": None,
        "settings": {
            "api_key": secrets.get('openai_key', ''),  # 只从 Secrets 加载
            "api_provider": "openai",
            "deepseek_key": secrets.get('deepseek_key', '')
        }
    }

    return initial_data


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

    # 创建深拷贝并清除所有敏感信息
    data_to_save = copy.deepcopy(data)

    # 强制清空所有 API Keys
    if 'settings' in data_to_save:
        data_to_save['settings']['api_key'] = ''
        data_to_save['settings']['deepseek_key'] = ''

    # 保存到本地文件
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"⚠️ Local save failed: {e}")

    # 保存到 Gist
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

    # Check if response is an error message
    if response.startswith("❌") or response.startswith("⚠️"):
        return False, response

    try:
        # 🔍 Show raw response for debugging
        with st.expander("🔍 Debug: AI Response"):
            st.code(response[:800], language=None)

        # Clean response
        response = response.strip()

        # Remove markdown code blocks
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
                    except:
                        continue

        # Extract JSON array
        start_idx = response.find('[')
        end_idx = response.rfind(']')

        if start_idx != -1 and end_idx != -1:
            response = response[start_idx:end_idx + 1]

        response = response.strip()

        # Parse JSON
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
        st.error("Response content:")
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
# Streamlit UI
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


def main():
    st.set_page_config(
        page_title="EchoRecall English",
        page_icon="📚",
        layout="wide"
    )

    # Load secrets
    secrets = load_secrets()

    # Sidebar
    with st.sidebar:
        st.title("⚙️ Settings")

        # Show connection status
        if st.session_state.get('github_token'):
            st.success("☁️ Cloud: Connected")
            if st.session_state.get('gist_id'):
                st.caption(f"Gist: `{st.session_state.gist_id[:8]}...`")

        # Only show manual input if secrets not configured
        if not secrets.get('github_token'):
            with st.expander("☁️ Manual Cloud Setup"):
                github_token = st.text_input(
                    "GitHub Token",
                    value=st.session_state.get('github_token', ''),
                    type="password"
                )

                gist_id = st.text_input(
                    "Gist ID (Optional)",
                    value=st.session_state.get('gist_id', '')
                )

                if st.button("💾 Connect"):
                    if github_token:
                        st.session_state.github_token = github_token
                        if gist_id:
                            st.session_state.gist_id = gist_id
                        st.success("✅ Connected!")
                        st.rerun()

        st.divider()

        # Load data
        data = load_data()

        # API Provider
        provider = st.selectbox(
            "AI Provider",
            options=["openai", "deepseek"],
            index=0 if data['settings'].get('api_provider', 'openai') == 'openai' else 1
        )

        if provider != data['settings'].get('api_provider'):
            data['settings']['api_provider'] = provider
            save_data(data)

        # Only show API key input if not in secrets
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

        # Phrase pool
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

        # Stats
        st.metric("🔥 Streak", f"{data['daily_streak']} days")
        st.metric("📖 Learning", len(data['learning']))
        st.metric("✅ Mastered", len(data['mastered']))

        st.divider()
        st.subheader("🔄 Reset")

        if st.button("🗑️ Delete Local Data", type="secondary"):
            # 删除本地文件
            if DATA_FILE.exists():
                DATA_FILE.unlink()
                st.success("✅ Local file deleted")

            # 清空 session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]

            st.warning("⚠️ Please refresh the page")
            st.info("Next save will create a fresh Gist")

    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📚 Today's Learning", "💬 Practice Chat", "📊 Progress"])

    # TAB 1
    with tab1:
        st.title("📚 Today's Learning")

        refill_result = check_and_refill_pool(data, threshold=10)
        if refill_result[0] is True:
            st.info(f"🤖 Auto-generated {refill_result[1]} phrases!")

        col1, col2 = st.columns([3, 1])
        with col2:
            learn_mode = st.selectbox("Phrases/day", [5, 10, 15, 20], index=0)

        today_phrases = get_today_phrases(data, count=learn_mode)

        if not today_phrases:
            st.success("🎉 All done!")
        else:
            st.info(f"📌 {len(today_phrases)} phrases")

            for i, phrase_data in enumerate(today_phrases, 1):
                category = phrase_data.get('category', 'Daily')
                emoji = get_category_color(category)

                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"### {i}. {phrase_data['phrase']} {emoji}")
                    st.markdown(f"**`{category}`** | {phrase_data['chinese']}")
                    st.write(f"**例句：** {phrase_data['example']}")

                    if any(p['phrase'] == phrase_data['phrase'] for p in data['learning']):
                        info = next(p for p in data['learning'] if p['phrase'] == phrase_data['phrase'])
                        st.caption(f"📅 Review #{info.get('review_count', 0) + 1}")

                with col2:
                    if st.button(f"✅", key=f"r_{i}"):
                        mark_reviewed(data, phrase_data['phrase'])
                        update_streak(data)
                        st.rerun()

                st.divider()

    # TAB 2
    with tab2:
        st.title("💬 Practice")

        provider = data['settings'].get('api_provider', 'openai')
        has_key = bool(data['settings'].get('api_key' if provider == 'openai' else 'deepseek_key'))

        if not has_key:
            st.warning("⚠️ Add API Key in Settings")
            st.stop()

        today_phrases = get_today_phrases(data, count=5)
        keywords = [p['phrase'] for p in today_phrases[:5]]

        if keywords:
            st.info(f"**Keywords:** {', '.join(keywords)}")

        if 'messages' not in st.session_state:
            st.session_state.messages = []
            system_msg = f"You are a friendly teacher. Today's phrases: {', '.join(keywords)}. Encourage usage, point out mistakes gently."

            with st.spinner("Starting..."):
                initial = call_ai_api(data, [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": "Hi!"}
                ])

            st.session_state.messages.append({"role": "assistant", "content": initial})
            st.session_state.system_context = system_msg

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if prompt := st.chat_input("Type..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🤔"):
                    api_msgs = [{"role": "system", "content": st.session_state.system_context}]
                    api_msgs.extend(
                        [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-10:]])
                    response = call_ai_api(data, api_msgs)

                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

        if st.button("🔄 New"):
            st.session_state.messages = []
            if 'system_context' in st.session_state:
                del st.session_state.system_context
            st.rerun()

    # TAB 3
    with tab3:
        st.title("📊 Progress")

        col1, col2, col3 = st.columns(3)
        col1.metric("🔥 Streak", f"{data['daily_streak']}")
        col2.metric("📖 Learning", len(data['learning']))
        col3.metric("✅ Mastered", len(data['mastered']))

        if data['learning']:
            st.subheader("📚 In Progress")
            df = pd.DataFrame([{
                'Phrase': p['phrase'],
                'Category': p.get('category', 'Daily'),
                'Next': p.get('next_review', 'N/A')
            } for p in data['learning']])
            st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()