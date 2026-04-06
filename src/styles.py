import streamlit as st

def inject_custom_css():
    """Injecte un style CSS Premium pour Vision-Boot."""
    st.markdown(
        """
        <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

        /* Global Styling */
        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Outfit', sans-serif;
            background-color: #0e1117;
            color: #ffffff;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #1a1c24 !important;
            border-right: 1px solid rgba(0, 255, 204, 0.1);
        }

        /* Metric Cards Styling (Glassmorphism) */
        [data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 15px 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s ease-in-out;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-5px);
            border-color: #00ffcc;
        }

        /* Buttons Styling */
        .stButton > button {
            border-radius: 8px !important;
            border: none !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #00ffcc 0%, #0099ff 100%) !important;
            color: #0e1117 !important;
        }
        .stButton > button[kind="primary"]:hover {
            box-shadow: 0 0 15px rgba(0, 255, 204, 0.4) !important;
            transform: scale(1.02);
        }

        /* Titles and Headers */
        h1, h2, h3 {
            color: #ffffff !important;
            font-weight: 700 !important;
        }
        
        .stTitle {
            background: -webkit-linear-gradient(#ffffff, #00ffcc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3rem !important;
        }

        /* Warnings and Alerts */
        [data-testid="stNotification"] {
            border-radius: 10px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }
        
        /* Sidebar Badge Demo Mode */
        .demo-badge {
            background-color: rgba(255, 165, 0, 0.2);
            color: orange;
            padding: 5px 10px;
            border-radius: 20px;
            border: 1px solid orange;
            font-size: 12px;
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
