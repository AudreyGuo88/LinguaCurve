import streamlit as st
import json
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import requests
import time

# ============================================================================
# Configuration & Data Management
# ============================================================================

DATA_FILE = Path("learning_data.json")

DEFAULT_PHRASE_POOL = [
    {"phrase": "break the ice", "chinese": "打破僵局", "example": "Let me tell a joke to break the ice."},
    {"phrase": "hit the nail on the head", "chinese": "一针见血", "example": "Your analysis hit the nail on the head."},
    {"phrase": "piece of cake", "chinese": "小菜一碟", "example": "This test was a piece of cake!"},
    {"phrase": "under the weather", "chinese": "身体不适", "example": "I'm feeling under the weather today."},
    {"phrase": "call it a day", "chinese": "收工", "example": "Let's call it a day and go home."},
    {"phrase": "bite the bullet", "chinese": "硬着头皮做", "example": "I had to bite the bullet and apologize."},
    {"phrase": "on cloud nine", "chinese": "非常高兴", "example": "She was on cloud nine after getting promoted."},
    {"phrase": "spill the beans", "chinese": "泄露秘密", "example": "Don't spill the beans about the surprise party!"},
    {"phrase": "cost an arm and a leg", "chinese": "非常昂贵", "example": "That new car cost him an arm and a leg."},
    {"phrase": "the ball is in your court", "chinese": "该你做决定了", "example": "I've made my offer, now the ball is in your court."},
    {"phrase": "beat around the bush", "chinese": "拐弯抹角", "example": "Stop beating around the bush and tell me the truth."},
    {"phrase": "let the cat out of the bag", "chinese": "泄露秘密", "example": "He let the cat out of the bag about the promotion."},
    {"phrase": "once in a blue moon", "chinese": "千载难逢", "example": "We only see each other once in a blue moon."},
    {"phrase": "get cold feet", "chinese": "临阵退缩", "example": "He got cold feet before the wedding."},
    {"phrase": "when pigs fly", "chinese": "不可能", "example": "He'll clean his room when pigs fly."},
]

def load_data():
    """Load or initialize learning data"""
    if not DATA_FILE.exists():
        initial_data = {
            "phrase_pool": DEFAULT_PHRASE_POOL,
            "learning": [],
            "mastered": [],
            "daily_streak": 0,
            "last_study_date": None,
            "settings": {
                "api_key": "",
                "api_provider": "openai",  # openai or deepseek
                "deepseek_key": ""
            }
        }
        save_data(initial_data)
        return initial_data
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    """Save data to JSON file"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_today_phrases(data):
    """Get 5 phrases for today (new or due for review)"""
    today = datetime.now().date()
    
    # Check for phrases due for review
    due_phrases = []
    for phrase in data['learning']:
        next_review = datetime.strptime(phrase['next_review'], '%Y-%m-%d').date()
        if next_review <= today:
            due_phrases.append(phrase)
    
    # If we need more phrases, add new ones from pool
    needed = 5 - len(due_phrases)
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
    
    new_phrase = {
        "phrase": phrase_text,
        "chinese": next((p['chinese'] for p in data['phrase_pool'] if p['phrase'] == phrase_text), ""),
        "example": next((p['example'] for p in data['phrase_pool'] if p['phrase'] == phrase_text), ""),
        "review_count": 0,
        "last_review": datetime.now().strftime('%Y-%m-%d'),
        "next_review": calculate_next_review(0)
    }
    data['learning'].append(new_phrase)
    save_data(data)
    return True

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
            "max_tokens": 500
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
            return f"❌ API Error: {response.status_code} - {response.text}"
    
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
            "max_tokens": 500
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
            return f"❌ API Error: {response.status_code} - {response.text}"
    
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
    """Auto-generate new phrases using AI"""
    system_prompt = """You are an English teacher helping create natural, useful English phrases for Chinese learners.
Generate {count} common English idioms or expressions that are:
1. Natural and frequently used by native speakers
2. At intermediate level (B1-B2)
3. Different from phrases already in the pool
4. Include diverse topics (work, daily life, emotions, etc.)

Return ONLY valid JSON array format:
[
  {{"phrase": "example phrase", "chinese": "中文翻译", "example": "Example sentence with the phrase."}},
  ...
]

Do NOT include any markdown, explanations, or text outside the JSON array."""

    existing_phrases = [p['phrase'] for p in data['phrase_pool']]
    user_prompt = f"""Generate {count} new English phrases. 

Already existing phrases (DO NOT repeat): {', '.join(existing_phrases[:20])}

Return JSON array only."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    with st.spinner("🤖 AI is generating new phrases..."):
        response = call_ai_api(data, messages)
    
    try:
        # Clean response (remove markdown code blocks if present)
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        response = response.strip()
        
        new_phrases = json.loads(response)
        
        if isinstance(new_phrases, list) and len(new_phrases) > 0:
            # Add to phrase pool
            data['phrase_pool'].extend(new_phrases)
            save_data(data)
            return True, len(new_phrases)
        else:
            return False, "Invalid response format"
    
    except json.JSONDecodeError as e:
        return False, f"JSON parsing error: {str(e)}\nResponse: {response[:200]}"
    except Exception as e:
        return False, str(e)

def check_and_refill_pool(data, threshold=10):
    """Check if phrase pool needs refilling and auto-generate if needed"""
    available = [p for p in data['phrase_pool'] 
                 if not any(p['phrase'] == lp['phrase'] for lp in data['learning'])
                 and not any(p['phrase'] == mp['phrase'] for mp in data['mastered'])]
    
    if len(available) < threshold:
        return generate_new_phrases(data, count=5)
    
    return None, None

# ============================================================================
# Streamlit UI
# ============================================================================

def main():
    st.set_page_config(
        page_title="EchoRecall English",
        page_icon="📚",
        layout="wide"
    )
    
    data = load_data()
    
    # Sidebar
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # API Provider selection
        provider = st.selectbox(
            "AI Provider",
            options=["openai", "deepseek"],
            index=0 if data['settings'].get('api_provider', 'openai') == 'openai' else 1,
            help="Choose your AI API provider"
        )
        
        if provider != data['settings'].get('api_provider'):
            data['settings']['api_provider'] = provider
            save_data(data)
        
        # API Key inputs
        if provider == 'openai':
            api_key = st.text_input(
                "OpenAI API Key",
                value=data['settings'].get('api_key', ''),
                type="password",
                help="Get your key from https://platform.openai.com/api-keys"
            )
            if api_key != data['settings'].get('api_key', ''):
                data['settings']['api_key'] = api_key
                save_data(data)
                st.success("✅ API Key saved!")
        
        elif provider == 'deepseek':
            deepseek_key = st.text_input(
                "DeepSeek API Key",
                value=data['settings'].get('deepseek_key', ''),
                type="password",
                help="Get your key from https://platform.deepseek.com"
            )
            if deepseek_key != data['settings'].get('deepseek_key', ''):
                data['settings']['deepseek_key'] = deepseek_key
                save_data(data)
                st.success("✅ API Key saved!")
        
        st.divider()
        
        # Phrase pool management
        st.subheader("📦 Phrase Pool")
        available_count = len([p for p in data['phrase_pool'] 
                               if not any(p['phrase'] == lp['phrase'] for lp in data['learning'])
                               and not any(p['phrase'] == mp['phrase'] for mp in data['mastered'])])
        st.metric("Available Phrases", available_count)
        
        if st.button("🔄 Generate 5 New Phrases", help="Use AI to create new phrases"):
            success, result = generate_new_phrases(data, count=5)
            if success:
                st.success(f"✅ Added {result} new phrases!")
                st.rerun()
            else:
                st.error(f"❌ Failed: {result}")
        
        st.divider()
        
        # Quick stats
        st.metric("🔥 Daily Streak", f"{data['daily_streak']} days")
        st.metric("📖 Learning", len(data['learning']))
        st.metric("✅ Mastered", len(data['mastered']))
        
        st.divider()
        
        if st.button("🔄 Reset All Data", type="secondary"):
            if st.checkbox("Are you sure?"):
                DATA_FILE.unlink(missing_ok=True)
                st.rerun()
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📚 Today's Learning", "💬 Practice Chat", "📊 Progress"])
    
    # ========================================================================
    # TAB 1: Daily Learning
    # ========================================================================
    with tab1:
        st.title("📚 Today's 5 Phrases")
        
        # Auto-refill check
        refill_result = check_and_refill_pool(data, threshold=10)
        if refill_result[0] is True:
            st.info(f"🤖 Auto-generated {refill_result[1]} new phrases to keep your pool fresh!")
        elif refill_result[0] is False:
            st.warning(f"⚠️ Auto-refill failed: {refill_result[1]}")
        
        today_phrases = get_today_phrases(data)
        
        if not today_phrases:
            st.success("🎉 All phrases reviewed for today! Come back tomorrow.")
        else:
            st.info(f"📌 You have {len(today_phrases)} phrases to study today.")
            
            for i, phrase_data in enumerate(today_phrases, 1):
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.subheader(f"{i}. {phrase_data['phrase']}")
                        st.write(f"**中文：** {phrase_data['chinese']}")
                        st.write(f"**例句：** {phrase_data['example']}")
                        
                        if any(p['phrase'] == phrase_data['phrase'] for p in data['learning']):
                            phrase_info = next(p for p in data['learning'] if p['phrase'] == phrase_data['phrase'])
                            review_count = phrase_info.get('review_count', 0)
                            next_review = phrase_info.get('next_review', 'N/A')
                            st.caption(f"📅 Review #{review_count + 1} | Next: {next_review}")
                    
                    with col2:
                        if st.button(f"✅ Mark Reviewed", key=f"review_{i}"):
                            mark_reviewed(data, phrase_data['phrase'])
                            update_streak(data)
                            st.success("Reviewed!")
                            st.rerun()
                    
                    st.divider()
    
    # ========================================================================
    # TAB 2: Practice Chat (Real AI)
    # ========================================================================
    with tab2:
        st.title("💬 Immersive Practice")
        
        # Check API key
        provider = data['settings'].get('api_provider', 'openai')
        has_key = False
        
        if provider == 'openai':
            has_key = bool(data['settings'].get('api_key'))
        elif provider == 'deepseek':
            has_key = bool(data['settings'].get('deepseek_key'))
        
        if not has_key:
            st.warning("⚠️ Please add your API Key in Settings to use the chat feature.")
            st.stop()
        
        # Get today's keywords
        today_phrases = get_today_phrases(data)
        keywords = [p['phrase'] for p in today_phrases[:5]]
        
        if keywords:
            st.info(f"**Today's Keywords:** {', '.join(keywords)}")
        
        # Initialize chat history
        if 'messages' not in st.session_state:
            st.session_state.messages = []
            # Send initial system message
            system_msg = f"""You are a friendly English teacher helping a Chinese student practice English.

Today's target phrases: {', '.join(keywords)}

Your role:
1. Engage in natural conversation
2. Encourage the student to use today's phrases
3. If you notice grammar mistakes, point them out gently using this format:
   "Great! Just a small note: [incorrect part] → [correct form] (explanation)"
4. Keep responses concise and encouraging
5. Ask follow-up questions to keep the conversation flowing

Start by greeting the student and mentioning today's phrases."""
            
            # Get initial greeting
            with st.spinner("🤖 AI is preparing..."):
                initial_response = call_ai_api(data, [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": "Hi! I'm ready to practice."}
                ])
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": initial_response
            })
            st.session_state.system_context = system_msg
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Type your message..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            # Generate AI response
            with st.chat_message("assistant"):
                with st.spinner("🤔 Thinking..."):
                    # Build conversation history
                    api_messages = [
                        {"role": "system", "content": st.session_state.system_context}
                    ]
                    api_messages.extend([
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages[-10:]  # Last 10 messages for context
                    ])
                    
                    response = call_ai_api(data, api_messages)
                
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Clear chat button
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("🔄 New Chat"):
                st.session_state.messages = []
                if 'system_context' in st.session_state:
                    del st.session_state.system_context
                st.rerun()
    
    # ========================================================================
    # TAB 3: Progress Dashboard
    # ========================================================================
    with tab3:
        st.title("📊 Your Progress")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🔥 Current Streak", f"{data['daily_streak']} days")
        
        with col2:
            st.metric("📖 In Progress", len(data['learning']))
        
        with col3:
            st.metric("✅ Mastered", len(data['mastered']))
        
        st.divider()
        
        # Pie chart
        if data['learning'] or data['mastered']:
            chart_data = pd.DataFrame({
                'Status': ['Learning', 'Mastered'],
                'Count': [len(data['learning']), len(data['mastered'])]
            })
            st.subheader("📈 Learning Distribution")
            st.bar_chart(chart_data.set_index('Status'))
        
        # Learning list
        if data['learning']:
            st.subheader("📚 Phrases in Progress")
            learning_df = pd.DataFrame([
                {
                    'Phrase': p['phrase'],
                    'Chinese': p['chinese'],
                    'Reviews': p.get('review_count', 0),
                    'Next Review': p.get('next_review', 'N/A')
                }
                for p in data['learning']
            ])
            st.dataframe(learning_df, use_container_width=True)
        
        # Mastered list
        if data['mastered']:
            st.subheader("✅ Mastered Phrases")
            mastered_df = pd.DataFrame([
                {'Phrase': p['phrase'], 'Chinese': p['chinese']}
                for p in data['mastered']
            ])
            st.dataframe(mastered_df, use_container_width=True)

if __name__ == "__main__":
    main()
