#!/bin/bash
# Initialize the database if it doesn't exist
python initialize_database.py

# Run the Streamlit app
#cd streamlit
streamlit run streamlit/app.py
