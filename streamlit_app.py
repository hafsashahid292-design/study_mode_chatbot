import streamlit as st
import google.generativeai as genai

# --- Load API Key from Streamlit secrets ---
google_api_key = st.secrets.get("GOOGLE_API_KEY")

if not google_api_key:
    st.warning("API Key not found in secrets.toml! Please add it there.")
    st.stop()  # Stop the app until API key is set
else:
    # Configure Gemini API
    try:
        genai.configure(api_key=google_api_key)
    except Exception as e:
        st.error(f"Error configuring Google Gemini API: {e}")
        st.stop()

st.set_page_config(page_title="🤖 Study Mode Chatbot", page_icon="📚")

# --- Streamlit UI Setup ---
st.title("📚 Study Mode Chatbot")
st.write("Your personal AI study assistant. Ask me anything related to your studies!")

# --- Sidebar Chat Controls ---
st.sidebar.header("⚙️ Chat Options")
new_chat_btn = st.sidebar.button("🆕 Start New Chat")
temp_chat_toggle = st.sidebar.checkbox("💭 Temporary Chat (won’t save history)")

# Saved chats dictionary in session state
if "saved_chats" not in st.session_state:
    st.session_state.saved_chats = {}  # {chat_id: chat_session}
if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = None

# --- Study Mode Prompt (hidden system instruction) ---
STUDY_MODE_PROMPT = """
You are a knowledgeable and patient AI Study Assistant.

Guidelines:
1. By default, keep answers short and clear (around 4–5 sentences).
2. If the user explicitly asks for details (e.g., "explain more", "go in detail", "step by step"),
   then provide a long, structured explanation with examples, lists, or analogies.
3. Encourage follow-up questions so the user can request more depth if they want.
4. Politely redirect if the topic is not study-related.
5. Format responses clearly using markdown for readability.
"""

# --- Initialize Gemini Model with system instruction ---
@st.cache_resource
def get_gemini_model():
    try:
        model = genai.GenerativeModel(
            "gemini-2.5-pro",
            system_instruction=STUDY_MODE_PROMPT,
        )
        return model
    except Exception as e:
        st.error(f"Could not load Gemini model: {e}")
        st.stop()

model = get_gemini_model()

# --- New Chat Button ---
if new_chat_btn:
    chat_id = f"chat_{len(st.session_state.saved_chats) + 1}"
    st.session_state.saved_chats[chat_id] = model.start_chat(history=[])
    st.session_state.active_chat_id = chat_id
    st.rerun()

# --- Sidebar Chat List ---
if st.session_state.saved_chats:
    st.sidebar.subheader("💾 Saved Chats")
    for chat_id in st.session_state.saved_chats.keys():
        if st.sidebar.button(chat_id, key=f"switch_{chat_id}"):
            st.session_state.active_chat_id = chat_id
            st.rerun()

# --- Select active chat session ---
if st.session_state.active_chat_id:
    chat_session = st.session_state.saved_chats[st.session_state.active_chat_id]
else:
    # First-time load → create a default chat
    default_id = "chat_1"
    st.session_state.saved_chats[default_id] = model.start_chat(history=[])
    st.session_state.active_chat_id = default_id
    chat_session = st.session_state.saved_chats[default_id]

# --- Display Chat History (only if NOT temporary chat) ---
if not temp_chat_toggle:
    for msg in chat_session.history:
        role = "assistant" if msg.role == "model" else "user"
        with st.chat_message(role):
            st.markdown("".join([p.text for p in msg.parts]))

# --- Chat Input and Response ---
if prompt := st.chat_input("Ask me a question about your studies..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    # Placeholder for streaming response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        try:
            if temp_chat_toggle:
                # Temporary chat → no saving
                temp_session = model.start_chat(history=[])
                response = temp_session.send_message(prompt, stream=True)
            else:
                response = chat_session.send_message(prompt, stream=True)

            for chunk in response:
                full_response += chunk.text
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)

        except genai.types.BlockedPromptException:
            st.error("Your prompt was blocked due to safety concerns.")
            with st.chat_message("assistant"):
                st.markdown("⚠️ I cannot process that request. Please ask a different study-related question.")
        except Exception as e:
            st.error(f"An error occurred: {e}")
            with st.chat_message("assistant"):
                st.markdown(f"⚠️ Error encountered. Please try again. ({e})")












