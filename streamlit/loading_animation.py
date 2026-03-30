import streamlit as st
import time


def jumping_loader():
    # CSS for the jumping animation
    style = """
    <style>
    .loader-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        padding: 20px;
    }
    .dot {
        width: 15px;
        height: 15px;
        border-radius: 50%;
        animation: jump 0.6s infinite alternate;
    }
    .dot:nth-child(1) { background-color: #f0c1c1; animation-delay: 0s; }
    .dot:nth-child(2) { background-color: #f0edb9; animation-delay: 0.15s; }
    .dot:nth-child(3) { background-color: #b8e2f4; animation-delay: 0.3s; }
    .dot:nth-child(4) { background-color: #c1eaca; animation-delay: 0.45s; }

    @keyframes jump {
        from { transform: translateY(0); }
        to { transform: translateY(-10px); }
    }
    </style>
    <div class="loader-container">
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
    </div>
    """
    return st.markdown(style, unsafe_allow_html=True)
