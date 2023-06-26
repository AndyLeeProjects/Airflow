import pandas as pd
from slack import WebClient
from sqlalchemy import create_engine, text
from sqlalchemy import text
from datetime import datetime, timezone
import streamlit as st
import requests


class VocabApp():
    def __init__(self):
        self.con = create_engine(st.secrets["db_uri_token"])
        self.user_df = pd.read_sql_query("SELECT * FROM users;", self.con)
        self.vocab_df = pd.read_sql_query("SELECT * FROM my_vocabs;", self.con)
        self.client = WebClient(st.secrets["slack_token"])

        st.title("Vocab App")

    def user_page(self):
        user_name = st.selectbox("Please choose a user name: ", self.user_df['user'].tolist())
        user_id = self.user_df[self.user_df['user'] == user_name]['user_id'].values[0]
        
        user_data = self.user_df[self.user_df['user_id'] == user_id]
        
        st.table(user_data)
        
        with st.expander("Modify User Info"):
            user_name_mod = st.text_input("Please type in the new user name: ", placeholder=user_name)
            country_mod = st.text_input("Please type in the new country: ", placeholder=user_data['country'].values[0])
            language_mod = st.selectbox("Please choose your default language: ", self.user_df['language'].unique().tolist() + ["Other"])
            timezone_mod = st.selectbox("Please choose your timezone: ", self.user_df['timezone'].unique().tolist() + ["Other"])

            user_data['user'] = user_name_mod
            user_data['language'] = language_mod
            user_data['timezone'] = timezone_mod
            
            if timezone_mod == "Other":
                new_timezone = st.text_input("Please type in your timezone: (e.g. EST, PST, etc)")
                user_data['timezone'] = new_timezone
            if language_mod == "Other":
                new_language = st.text_input("Please type in your language: (e.g. English, Spanish, etc)")
                user_data['language'] = new_language
            
            st.table(user_data)

            col1, col2, col3 = st.columns(3)
            with col2:
                submit_change = st.button("Submit User Changes ✅")

            if submit_change:
                # Replace the row with the new row
                updated_at_utc = datetime.now(timezone.utc)
                user_data['updated_at_utc'] = updated_at_utc
                self.user_df.loc[self.user_df['user_id'] == user_id] = user_data
                self.user_df.to_sql('users', self.con, if_exists='replace', index=False)
                
    def vocab_analysis(self):
        user_name = st.selectbox("Please choose a user name: ", self.user_df['user'].tolist(), key="vocab_analysis")
        user_id = self.user_df[self.user_df['user'] == user_name]['user_id'].values[0]
        
        vocab_data = self.vocab_df[self.vocab_df['user_id'] == user_id]
        # Compute the Average exposure 
        memorized_vocabs = vocab_data[vocab_data['status'] == "Memorized"]
        avg_exposure = round(memorized_vocabs['exposure'].mean(),2)
        st.write(f"### Average Exposure for Memorization: {avg_exposure}")
        
        status_df = pd.DataFrame()
        status_df["Total Vocabs Added"] = [vocab_data.shape[0]]
        status_df["Total Memorized"] = [memorized_vocabs.shape[0]]
        status_df["Average Exposure"] = [avg_exposure]
        st.table()
        

    def execute_all(self):
        user_page, vocab_analysis = st.tabs(["User Page", "Vocab Analysis"])
        with user_page:
            self.user_page()
        with vocab_analysis:
            self.vocab_analysis()


VA = VocabApp()
VA.execute_all()