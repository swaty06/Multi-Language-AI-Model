import streamlit as st
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini
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
        model=Gemini(id="gemini-2.0-flash-exp"),
        instructions=[
            "You must only respond in English.",
            "Provide helpful, accurate, and engaging responses.",
            "If asked to respond in another language, politely decline and respond in English.",
        ],
        markdown=True,
    )
    
    # German Agent  
    german_agent = Agent(
        name="German Agent",
        role="Experte für deutsche Sprache",
        model=Gemini(id="gemini-2.0-flash-exp"),
        instructions=[
            "Du musst nur auf Deutsch antworten.",
            "Gib hilfreiche, genaue und ansprechende Antworten.",
            "Falls du gebeten wirst, in einer anderen Sprache zu antworten, lehne höflich ab und antworte auf Deutsch.",
        ],
        markdown=True,
    )
    
    return english_agent, german_agent


def create_team(english_agent, german_agent):
    """Create the multi-language routing team"""
    
    return Team(
        name="Multi Language Team",
        model=Gemini(id="gemini-2.0-flash-exp"),
        members=[english_agent, german_agent],
        instructions=[
            "You are a smart language router for a multi-language AI system.",
            "Analyze the user's input language and route to the appropriate agent:",
            "- English text → English Agent",
            "- German text → German Agent",
            "For unsupported languages, respond politely in English:",
            "'I can currently assist in English and German. Please rephrase your question in one of these languages.'",
            "Always maintain context and provide helpful responses.",
        ],
    )


def get_response_from_agent(user_input: str, detected_lang: str, 
                            english_agent: Agent, german_agent: Agent) -> str:
    """
    Direct routing to appropriate agent based on detected language
    """
    try:
        if detected_lang == 'de':
            response = german_agent.run(user_input)
        else:  # Default to English
            response = english_agent.run(user_input)
        
        # Extract content from response
        if hasattr(response, 'content'):
            return response.content
        elif hasattr(response, 'messages') and response.messages:
            # Get the last message content
            last_message = response.messages[-1]
            if hasattr(last_message, 'content'):
                return last_message.content
        
        return str(response)
    
    except Exception as e:
        logger.error(f"Error getting response: {e}")
        return f"❌ Error processing your request: {str(e)}"


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
        
        st.divider()
        
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
        
        # Statistics
        if 'chat_history' in st.session_state:
            st.divider()
            st.caption(f"💬 Messages: {len(st.session_state.chat_history)}")
    
    # Initialize components
    if 'agents_initialized' not in st.session_state:
        with st.spinner("Initializing language agents..."):
            try:
                english_agent, german_agent = create_agents()
                
                st.session_state.english_agent = english_agent
                st.session_state.german_agent = german_agent
                st.session_state.agents_initialized = True
                
                st.success("✅ Agents initialized successfully!")
            except Exception as e:
                st.error(f"❌ Failed to initialize agents: {str(e)}")
                logger.error(f"Initialization error: {e}")
                st.stop()
    
    # Chat interface
    st.header("💬 Chat Interface")
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for user_msg, bot_msg, detected_lang in st.session_state.chat_history:
        with st.chat_message("user"):
            st.markdown(f"**{detected_lang}**")
            st.markdown(user_msg)
        
        with st.chat_message("assistant"):
            st.markdown(bot_msg)
    
    # Chat input
    if user_input := st.chat_input("Type your message in English or German..."):
        # Detect language
        detected_lang = LanguageDetector.detect_language(user_input)
        
        # Show language detection
        lang_display = {
            'en': '🇺🇸 English',
            'de': '🇩🇪 German', 
            'unknown': '❓ Unknown'
        }.get(detected_lang, f'❓ {detected_lang}')
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(f"**{lang_display}**")
            st.markdown(user_input)
        
        # Process request and display response
        with st.chat_message("assistant"):
            if detected_lang in ['en', 'de']:
                with st.spinner("Thinking..."):
                    response = get_response_from_agent(
                        user_input,
                        detected_lang,
                        st.session_state.english_agent,
                        st.session_state.german_agent
                    )
                
                st.markdown(response)
                
                # Add to chat history
                st.session_state.chat_history.append((user_input, response, lang_display))
                
            else:
                warning_msg = "I can currently assist in English and German. Please rephrase your question in one of these languages.\n\nIch kann derzeit auf Englisch und Deutsch helfen. Bitte formulieren Sie Ihre Frage in einer dieser Sprachen."
                st.warning(warning_msg)
                st.session_state.chat_history.append((user_input, warning_msg, lang_display))
    
    # Footer
    st.markdown("---")
    st.markdown("*Powered by Agno Framework with Gemini 2.0 Flash*")


if __name__ == "__main__":
    main()
