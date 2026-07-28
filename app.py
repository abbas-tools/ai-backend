import streamlit as st

st.title("My Free AI Hub")

prompt = st.text_input("Enter your prompt:")
if st.button("Generate"):
    st.success(f"AI Response for: {prompt}")
  
