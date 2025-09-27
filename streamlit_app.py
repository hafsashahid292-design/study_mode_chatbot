import streamlit as st
import google.generativeai as genai

# --- Load API Key ---
google_api_key = st.secrets.get("GOOGLE_API_KEY")
if not google_api_key:
    st.warning("API Key not found in secrets.toml! Please add it there.")
    st.stop()
else:
    try:
        genai.configure(api_key=google_api_key)
    except Exception as e:
        st.error(f"Error configuring Google Gemini API: {e}")
        st.stop()

# --- Page Config ---
st.set_page_config(
    page_title="🤖 StudyMate AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Apply Custom Colors ---
st.markdown(
    """
    <style>
    /* Background */
    .main .block-container {
        background-color: #F9F9F9;
        padding: 1rem 2rem;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ECECEC;
    }

    /* Headers / Titles */
    .stTitle, h1, h2, h3, h4, h5, h6 {
        color: #4A90E2;
    }

    /* Buttons */
    button[kind="primary"] {
        background-color: #43A047;
        color: white;
    }
    button[kind="secondary"] {
        background-color: #FFA726;
        color: white;
    }

    /* Text */
    .stText, .stMarkdown {
        color: #333333;
    }

    /* Notes / Subtext */
    .stCaption {
        color: #555555;
    }

    /* Chat Messages (Assistant) */
    .stChatMessage .assistant {
        background-color: #E3F2FD;
        border-radius: 8px;
        padding: 0.5rem;
    }

    /* Chat Messages (User) */
    .stChatMessage .user {
        background-color: #E8F5E9;
        border-radius: 8px;
        padding: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- App Title ---
st.title("📚 StudyMate AI")
st.write("Your personal AI study assistant. Choose a mode from the sidebar to get started!")

# --- Sidebar Controls ---
st.sidebar.header("⚙️ Chat Options")
new_chat_btn = st.sidebar.button("🆕 Start New Chat")
temp_chat_toggle = st.sidebar.checkbox("💭 Temporary Chat (won’t save history)")

# --- Feature Modes ---
st.sidebar.subheader("✨ Choose a Mode")
features = {
    "Normal Chat": "💬",
    "📝 Quiz Generator": "📝",
    "🎴 Flashcards": "🎴",
    "📄 Summarizer": "📄",
    "🎯 Deep Explanation": "🎯",
    "📊 Data-Driven Answer": "📊",
    "🗣 Roleplay Mode": "🗣",
    "✅ Self-Assessment": "✅",
    "🧩 Practice Problems": "🧩",
    "📅 Study Planner": "📅",
    "💡 Explain Like I’m 5 (ELI5)": "💡",
    "📈 Progress Tracker": "📈",
}

if "feature_mode" not in st.session_state:
    st.session_state.feature_mode = "Normal Chat"

# Highlight active feature in sidebar
for f in features.keys():
    if f == st.session_state.feature_mode:
        st.sidebar.markdown(f"**➡️ {features[f]} {f}**")
    elif st.sidebar.button(f"{features[f]} {f}", key=f):
        st.session_state.feature_mode = f
        st.rerun()

feature_mode = st.session_state.feature_mode

# --- Dynamic Mode Banner ---
st.markdown(f"<h4 style='color:#4A90E2'>Current Mode: {features[feature_mode]} {feature_mode}</h4>", unsafe_allow_html=True)

# --- Progress Tracker ---
if "progress" not in st.session_state:
    st.session_state.progress = {"quizzes": 0, "correct": 0, "topics": []}

# --- Study Mode Prompt ---
STUDY_MODE_PROMPT = """
You are a knowledgeable and patient AI Study Assistant.
Guidelines:
1. Keep answers clear and concise (4–5 sentences).
2. If the user asks for details, provide structured explanations with examples or analogies.
3. Encourage follow-up questions.
4. Politely redirect if the topic is not study-related.
5. Format responses clearly using markdown.
"""

# --- Initialize Gemini Model ---
@st.cache_resource
def get_gemini_model():
    with st.spinner("Loading StudyMate AI... Please wait."):
        try:
            return genai.GenerativeModel("gemini-2.5-pro", system_instruction=STUDY_MODE_PROMPT)
        except Exception as e:
            st.error(f"Could not load Gemini model: {e}")
            st.stop()

model = get_gemini_model()

# --- Session State Initialization ---
for key in ["saved_chats", "active_chat_id", "temp_session", "last_quiz", "quiz_generated"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "saved_chats" else {}

# --- Start New Chat ---
if new_chat_btn:
    chat_id = f"chat_{len(st.session_state.saved_chats)+1}"
    st.session_state.saved_chats[chat_id] = model.start_chat(history=[])
    st.session_state.active_chat_id = chat_id
    st.rerun()

# --- Sidebar Saved Chats ---
if st.session_state.saved_chats:
    st.sidebar.subheader("💾 Saved Chats")
    for chat_id in st.session_state.saved_chats.keys():
        if st.sidebar.button(chat_id, key=f"switch_{chat_id}"):
            st.session_state.active_chat_id = chat_id
            st.rerun()

# --- Active Chat Session ---
if temp_chat_toggle:
    if st.session_state.temp_session is None:
        st.session_state.temp_session = model.start_chat(history=[])
    chat_session = st.session_state.temp_session
    st.sidebar.markdown("💡 **Temporary Chat Active**")
else:
    if st.session_state.active_chat_id:
        chat_session = st.session_state.saved_chats[st.session_state.active_chat_id]
    else:
        default_id = "chat_1"
        st.session_state.saved_chats[default_id] = model.start_chat(history=[])
        st.session_state.active_chat_id = default_id
        chat_session = st.session_state.saved_chats[default_id]

# --- Display Chat History ---
if not temp_chat_toggle:
    for msg in chat_session.history:
        role = "assistant" if msg.role == "model" else "user"
        with st.chat_message(role):
            st.markdown("".join([p.text for p in msg.parts]))

# --- Helper: Stream Message (Safe) ---
def stream_message(prompt_text):
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_text = ""
        try:
            response = chat_session.send_message(prompt_text, stream=True)
            if not response:
                placeholder.markdown("⚠️ No response returned. The AI may have blocked this request.")
                return
            for chunk in response:
                if hasattr(chunk, "text") and chunk.text:
                    full_text += chunk.text
                    placeholder.markdown(full_text + "▌")
            if full_text:
                placeholder.markdown(full_text.rstrip())
            else:
                placeholder.markdown("⚠️ The AI did not return any content. Try rephrasing your prompt.")
        except genai.types.BlockedPromptException:
            st.error("⚠️ Request blocked due to sensitive content.")
        except Exception as e:
            st.error(f"Error: {e}")

# --- Feature Prompt Builder ---
def build_prompt(feature_mode, user_prompt):
    mapping = {
        "🎴 Flashcards": f"Create flashcards in Q&A format for:\n{user_prompt}",
        "📄 Summarizer": f"Summarize this text into clear notes:\n{user_prompt}",
        "🎯 Deep Explanation": f"Explain in detail, structured and professional, suitable for all ages:\n{user_prompt}",
        "📊 Data-Driven Answer": f"Answer using past, current, and latest data available:\n{user_prompt}",
        "🗣 Roleplay Mode": f"Act as a roleplay assistant. Choose a role: Teacher, Examiner, Debate Partner. Respond as that role to:\n{user_prompt}",
        "✅ Self-Assessment": f"Ask me one question step by step about this topic and evaluate my answer:\n{user_prompt}",
        "🧩 Practice Problems": f"Generate practice problems with step-by-step solutions for:\n{user_prompt}",
        "📅 Study Planner": f"Create a personalized study plan with subjects and time slots. User details:\n{user_prompt}",
        "💡 Explain Like I’m 5 (ELI5)": f"Explain this topic in very simple words, like explaining to a 5-year-old:\n{user_prompt}",
    }
    return mapping.get(feature_mode, user_prompt)

# --- Quiz Generator ---
if feature_mode == "📝 Quiz Generator":
    st.subheader("📝 Quiz Generator")
    with st.form("quiz_form"):
        subject = st.text_input("Enter the subject for the quiz:")
        topic = st.text_input("Enter the topic for the quiz:")
        difficulty = st.radio("Choose difficulty level:", ["Basic", "Intermediate", "Advanced"])
        submit_quiz = st.form_submit_button("Generate Quiz")
    if submit_quiz and subject and topic:
        quiz_prompt = f"""
        Generate a {difficulty} level quiz in {subject} about {topic}.
        Each question should have a clear answer.
        Guardrails: Avoid controversial, political, religious, sexual, violent, or sensitive topics.
        """
        st.session_state.progress["quizzes"] += 1
        st.session_state.progress["topics"].append(f"{subject} - {topic}")
        st.session_state.last_quiz = {"subject": subject, "topic": topic, "difficulty": difficulty}
        st.session_state.quiz_generated = True
        stream_message(quiz_prompt)

    if st.session_state.quiz_generated and st.session_state.last_quiz:
        followup_prompt = st.chat_input(f"Ask a question about the {feature_mode} quiz...")
        if followup_prompt:
            with st.chat_message("user"):
                st.markdown(followup_prompt)
            followup_ai_prompt = f"""
            The user is asking a question about the quiz on {st.session_state.last_quiz['subject']} - {st.session_state.last_quiz['topic']}.
            Question: {followup_prompt}
            Provide a clear explanation as if helping a student understand the quiz.
            """
            stream_message(followup_ai_prompt)

# --- Normal Chat for Other Features ---
elif feature_mode != "📈 Progress Tracker":
    user_prompt = st.chat_input(f"Ask me a question about your studies ({feature_mode} mode)...")
    if user_prompt:
        with st.chat_message("user"):
            st.markdown(user_prompt)
        full_prompt = build_prompt(feature_mode, user_prompt)
        st.session_state.progress["topics"].append(user_prompt[:100])
        stream_message(full_prompt)

# --- Progress Tracker Display ---
if feature_mode == "📈 Progress Tracker":
    stats = st.session_state.progress
    result = f"""
    ### 📊 Progress Tracker
    - Quizzes attempted: {stats['quizzes']}
    - Correct answers: {stats['correct']}
    - Topics studied: {', '.join(stats['topics']) if stats['topics'] else 'None yet'}
    """
    st.markdown(result)
    


















