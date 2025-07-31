import streamlit as st
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.deepseek import DeepSeek
from agno.models.google import Gemini
from agno.models.mistral.mistral import MistralChat
from agno.models.openai import OpenAIChat
from agno.team.team import Team
from langdetect import detect, DetectorFactory
import logging

# Set seed for consistent language detection
DetectorFactory.seed = 0

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LanguageDetector:
    """Enhanced language detection with fallback mechanisms"""
    
    @staticmethod
    def detect_language(text: str) -> str:
        """
        Detect language with multiple fallback strategies
        """
        if not text or len(text.strip()) < 2:
            return "unknown"
        
        try:
            # Primary detection
            detected = detect(text)
            logger.info(f"Detected language: {detected} for text: '{text[:50]}...'")
            return detected
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            
            # Fallback: Simple keyword detection
            text_lower = text.lower()
            german_indicators = ['ich', 'du', 'der', 'die', 'das', 'und', 'ist', 'mit', 'für', 'auf', 'von', 'zu', 'im', 'über']
            english_indicators = ['the', 'and', 'is', 'with', 'for', 'on', 'from', 'to', 'in', 'over', 'this', 'that']
            
            german_count = sum(1 for word in german_indicators if word in text_lower)
            english_count = sum(1 for word in english_indicators if word in text_lower)
            
            if german_count > english_count and german_count > 0:
                return "de"
            elif english_count > 0:
                return "en"
            
            return "unknown"

def create_agents():
    """Factory function to create language-specific agents"""
    
    # English Agent
    english_agent = Agent(
        name="English Agent",
        role="Expert English language assistant",
        model=Gemini(id="gemini-2.0-flash"),
        instructions=[
            "You must only respond in English.",
            "Provide helpful, accurate, and engaging responses.",
            "If asked to respond in another language, politely decline and respond in English.",
        ],
    )
    
    # German Agent  
    german_agent = Agent(
        name="German Agent",
        role="Experte für deutsche Sprache",
        model=Gemini(id="gemini-2.0-flash"),
        instructions=[
            "Du musst nur auf Deutsch antworten.",
            "Gib hilfreiche, genaue und ansprechende Antworten.",
            "Falls du gebeten wirst, in einer anderen Sprache zu antworten, lehne höflich ab und antworte auf Deutsch.",
        ],
    )
    
    return english_agent, german_agent

def create_team(english_agent, german_agent):
    """Create the multi-language routing team"""
    
    return Team(
        name="Multi Language Team",
        mode="route",
        model=Gemini(id="gemini-2.0-flash"),
        members=[english_agent, german_agent],
        show_tool_calls=True,
        markdown=True,
        instructions=[
            "You are a smart language router for a multi-language AI system.",
            "Analyze the user's input language and route to the appropriate agent:",
            "- English text → English Agent",
            "- German text → German Agent",
            "For unsupported languages, respond politely in English:",
            "'I can currently assist in English and German. Please rephrase your question in one of these languages.'",
            "Always maintain context and provide helpful responses.",
        ],
        show_members_responses=True,
    )

def main():
    """Main Streamlit application"""
    
    # Page configuration
    st.set_page_config(
        page_title="Multi-Language AI Agent",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Header
    st.title("🌍 Multi-Language AI Agent")
    st.markdown("### Currently supports **English** 🇺🇸 and **German** 🇩🇪")
    
    # Sidebar with information
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
        This AI agent can communicate in:
        - **English** - Full conversational support
        - **German** - Vollständige Gesprächsunterstützung
        
        The system automatically detects your language and routes your question to the appropriate specialist agent.
        """)
        
        st.header("🔧 Features")
        st.markdown("""
        - Automatic language detection
        - Specialized agents per language
        - Smart routing system
        - Fallback for unsupported languages
        """)
    
    # Initialize components
    if 'agents_initialized' not in st.session_state:
        with st.spinner("Initializing language agents..."):
            english_agent, german_agent = create_agents()
            multi_language_team = create_team(english_agent, german_agent)
            
            st.session_state.english_agent = english_agent
            st.session_state.german_agent = german_agent
            st.session_state.team = multi_language_team
            st.session_state.agents_initialized = True
        st.success("✅ Agents initialized successfully!")
    
    # Chat interface
    st.header("💬 Chat Interface")
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for i, (user_msg, bot_msg, detected_lang) in enumerate(st.session_state.chat_history):
        with st.container():
            st.markdown(f"**You** ({detected_lang}):")
            st.markdown(f"> {user_msg}")
            st.markdown("**🤖 AI Response:**")
            st.markdown(bot_msg)
            st.divider()
    
    # Input form
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Ask something:",
            placeholder="Type your question in English or German...",
            height=100
        )
        col1, col2, col3 = st.columns([1, 1, 4])
        
        with col1:
            submit_button = st.form_submit_button("Send 📤", use_container_width=True)
        
        with col2:
            clear_button = st.form_submit_button("Clear History 🗑️", use_container_width=True)
    
    # Handle form submission
    if submit_button and user_input.strip():
        # Detect language
        detected_lang = LanguageDetector.detect_language(user_input)
        
        # Show language detection
        lang_display = {
            'en': '🇺🇸 English',
            'de': '🇩🇪 German', 
            'unknown': '❓ Unknown'
        }.get(detected_lang, f'❓ {detected_lang}')
        
        st.info(f"Detected language: {lang_display}")
        
        # Process request
        if detected_lang in ['en', 'de']:
            try:
                with st.spinner("Processing your request..."):
                    team_response = st.session_state.team.run(user_input)
                    
                    # Extract content from TeamRunResponse object
                    if hasattr(team_response, 'content'):
                        response = team_response.content
                    else:
                        response = str(team_response)
                
                # Add to chat history
                st.session_state.chat_history.append((user_input, response, lang_display))
                
                # Display response
                st.success("Response generated successfully!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error processing request: {str(e)}")
                logger.error(f"Error in team processing: {e}")
        else:
            warning_msg = "I can currently assist in English and German. Please rephrase your question in one of these languages."
            st.warning(warning_msg)
            st.session_state.chat_history.append((user_input, warning_msg, lang_display))
            st.rerun()
    
    # Handle clear history
    if clear_button:
        st.session_state.chat_history = []
        st.success("Chat history cleared!")
        st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("*Powered by Agno Framework with Gemini 2.0 Flash*")

if __name__ == "__main__":
    main()