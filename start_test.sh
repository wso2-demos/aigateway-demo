#!/bin/bash
# Activate virtual environment and launch Streamlit app
dirname=$(dirname "$0")
source "$dirname/venv/bin/activate"
streamlit run demo_ui.py 