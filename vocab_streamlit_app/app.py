import pandas as pd
import os
from slack import WebClient
from sqlalchemy import create_engine, text
from sqlalchemy import text
from datetime import datetime, timezone
import streamlit as st
import requests
from dotenv import load_dotenv
import plotly.graph_objects as go
from table_streamlit import interactive_table
from scrape_images import scrape_web_images


class VocabApp():
    def __init__(self):
        load_dotenv()  # Load variables from .env file
        db_uri = os.environ.get('VOCAB_DB_URI')
        slack_token = os.environ.get('SLACK_TOKEN')

        self.con = create_engine(db_uri)
        self.user_df = pd.read_sql_query("SELECT * FROM users;", self.con)
        self.vocab_df = pd.read_sql_query("SELECT * FROM my_vocabs;", self.con)
        
        user_name_df = self.user_df[['user_id', 'user']]
        self.merged_df = self.vocab_df.merge(user_name_df, on='user_id', how='left')
        self.client = WebClient(slack_token)

        st.title("Vocab App")
        
        # Define the username and password for the admin user
        ADMIN_USERNAME = "admin"
        ADMIN_PASSWORD = "password"

        def authenticate(username, password):
            return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

        # Display login form
        login = st.sidebar.expander("Admin Login")
        with login:
            st.header("Admin Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                if authenticate(username, password):
                    st.success("Logged in as Admin!")
                    st.experimental_set_query_params(admin=True)
                else:
                    st.error("Invalid credentials")

        # Check if admin is logged in
        self.is_admin = st.experimental_get_query_params().get("admin", False)


    def user_page(self):
        user_name = st.selectbox("Please choose a user name: ", self.user_df['user'].tolist())
        user_id = self.user_df[self.user_df['user'] == user_name]['user_id'].values[0]
        
        user_data = self.user_df[self.user_df['user_id'] == user_id]
        
        st.table(user_data)
        
        with st.expander("Modify User Info"):
            user_name_mod = st.text_input("Name: ", placeholder=user_name, key="name_mod")
            country_mod = st.text_input("Country: ", placeholder=user_data['country'].values[0], key="country_mod")
            language_mod = st.selectbox("Default Language: ", self.user_df['language'].unique().tolist() + ["Other"])
            timezone_mod = st.selectbox("Timezone: ", self.user_df['timezone'].unique().tolist() + ["Other"])
            status_mod = st.selectbox("Status: ", ["Active", "Inactive"])

            user_data['user'] = user_name_mod
            user_data['language'] = language_mod
            user_data['timezone'] = timezone_mod
            
            if timezone_mod == "Other":
                new_timezone = st.text_input("Please type in your timezone: (e.g. EST, PST, etc)", key="timezone_mod")
                user_data['timezone'] = new_timezone
            if language_mod == "Other":
                new_language = st.text_input("Please type in your language: (e.g. English, Spanish, etc)", key="language_mod")
                user_data['language'] = new_language
            
            st.table(user_data)

            col1, col2, col3 = st.columns(3)
            with col2:
                submit_change = st.button("Submit User Changes ✅")

            if submit_change:
                # Replace the row with the new row
                user_data['updated_at_utc'] = datetime.now(timezone.utc)
                self.user_df.loc[self.user_df['user_id'] == user_id] = user_data
                self.user_df.to_sql('users', self.con, if_exists='replace', index=False)
                c1, c2, c3 = st.columns(3)
                with c2:
                    st.write("User info updated! 🎉")

        with st.expander("Add New User"):
            new_user_name = st.text_input("Name: ", key="name_new")
            new_country = st.text_input("Country: ", key="country_new")
            new_language = st.selectbox("Default Language: ", self.user_df['language'].unique().tolist() + ["Other"], key="new_user_lang")
            new_timezone = st.selectbox("Timezone: ", self.user_df['timezone'].unique().tolist() + ["Other"], key="new_user_timezone")
            slack_channel = st.text_input("Slack Channel (User ID): ", key="new_slack_channel")

            new_user = {}
            new_user['user'] = new_user_name
            new_user['country'] = new_country
            new_user['user_id'] = slack_channel
            new_user['language'] = new_language
            new_user['timezone'] = new_timezone

            if timezone_mod == "Other":
                new_timezone = st.text_input("Please type in your timezone: (e.g. EST, PST, etc)", key="timezone_new")
                new_user['timezone'] = new_timezone
            if language_mod == "Other":
                new_language = st.text_input("Please type in your language: (e.g. English, Spanish, etc)", key="language_new")
                new_user['language'] = new_language
            
            st.table(new_user)

            col1, col2, col3 = st.columns(3)
            with col2:
                submit_change = st.button("Submit New User ✅")

            if submit_change and self.is_admin:
                # Replace the row with the new row
                updated_at_utc = datetime.now(timezone.utc)
                new_user['created_at_utc'] = updated_at_utc
                new_user['updated_at_utc'] = updated_at_utc
                new_user['status'] = "Active"
                new_user = pd.DataFrame(new_user, index=[0])
                new_user.to_sql('users', self.con, if_exists='append', index=False)
                c1, c2, c3 = st.columns(3)
                with c2:
                    st.write("User Added! 🎉")
            elif submit_change:
                st.error("You are not logged in as admin. Please log in as admin to add a new user.")

        with st.expander("Delete User"):
            # select user
            user_name = st.selectbox("Please choose a user name: ", self.user_df['user'].tolist(), key="delete_user")

            col1, col2, col3 = st.columns(3)
            with col2:
                submit_change = st.button("Delete User ❌")

            if submit_change and self.is_admin:
                # Replace the row with the new row
                self.user_df = self.user_df[self.user_df['user'] != user_name]
                self.user_df.to_sql('users', self.con, if_exists='replace', index=False)
                c1, c2, c3 = st.columns(3)
                with c2:
                    st.write("Vocabulary Deleted! 👍")
                
            elif submit_change:
                st.error("You are not logged in as admin. Please log in as admin to delete a user.")

    def vocab_update(self):
        user_name = st.selectbox("Please choose a user name: ", self.user_df['user'].tolist(), key="vocab_update")
        user_id = self.user_df[self.user_df['user'] == user_name]['user_id'].values[0]
        user_vocabs = self.merged_df[self.merged_df['user'] == user_name]

        # drop user column 
        user_vocabs = user_vocabs.drop(columns=['user'])

        refresh_button = st.button("Generate Table")
        if refresh_button:
            updated_table = interactive_table(user_vocabs, key="vocab_table")

        try:
            vocab_id_update = user_vocabs[user_vocabs['vocab'] == vocab_update]['vocab_id'].iloc[0]
        except:
            vocab_id_update = None
        

        st.write("# ")
        st.write("### Add New Vocabulary")
        with st.expander("Add New Vocabulary"):
            new_vocab_dic = {}
            new_vocab = st.text_input("Please type in the new vocabulary: ", key="vocab_spelling_new")
            new_vocab_dic["vocab_origin"] = st.text_input("Please add context to your vocabulary: ", key="vocab_origin_new")
            new_vocab_dic["vocab"] = new_vocab
            new_vocab_dic["status"] = "Wait List"
            new_vocab_id = max(self.vocab_df['vocab_id'].tolist())
            # Add 1 to "V0012" format
            new_vocab_id = int(new_vocab_id.split("V")[1]) + 1
            new_vocab_id = "V" + str(new_vocab_id).zfill(5)
            new_vocab_dic["vocab_id"] = new_vocab_id
            new_vocab_dic["exposure"] = 0
            for ind, link in enumerate(scrape_web_images(new_vocab)):
                new_vocab_dic[f"img_url{ind + 1}"] = link
            new_vocab_dic["created_at_utc"] = datetime.now(timezone.utc)
            new_vocab_dic["memorized_at_utc"] = None
            new_vocab_dic["confidence"] = None
            new_vocab_dic["quizzed_count"] = 0
            new_vocab_dic["correct_count"] = 0
            new_vocab_dic["incorrect_count"] = 0
            new_vocab_dic["user_id"] = user_id
            
            new_vocab_df = pd.DataFrame(new_vocab_dic, index=[0])
            col1, col2, col3 = st.columns(3)
            with col2:
                adding_new_vocab = st.button("Submit New Vocabulary ✅")
            
            if adding_new_vocab:
                new_vocab_df.to_sql('my_vocabs', self.con, if_exists='append', index=False)
                c1, c2, c3 = st.columns(3)
                with c2:
                    st.write("Vocabulary Added! 🎉")

        st.write("# ")
        st.write("# ")
        st.write("# ")
        st.write("### Update Vocabulary")
        vocab_update = st.selectbox("Please search or choose a vocabulary to update: ", user_vocabs['vocab'].tolist(), key="vocab_select_update")
        try:
            vocab_origin_update = user_vocabs[user_vocabs['vocab'] == vocab_update]['vocab_origin'].iloc[0]
        except:
            vocab_origin_update = f"{vocab_update} is ..."
        try:
            vocab_id_update = user_vocabs[user_vocabs['vocab'] == vocab_update]['vocab_id'].iloc[0]
        except:
            vocab_id_update = None
        try:
            vocab_exposure_update = user_vocabs[user_vocabs['vocab'] == vocab_update]['exposure'].iloc[0]
        except:
            vocab_exposure_update = 2
        with st.expander(f"Update Vocabulary: {vocab_update}"):

            new_vocab = st.text_input("Please type in the new vocabulary: ", key="vocab_spelling_update", value=vocab_update)
            new_vocab_origin = st.text_input("Please type in the new vocabulary origin: ", key="vocab_origin_update", value=vocab_origin_update)
            new_exposure = st.number_input("Please type in the new exposure: ", key="vocab_exposure_update", value=vocab_exposure_update)
            new_status = st.selectbox("Please select the new status: ", ["Memorized", "Wait List", "Next"])

            user_vocabs.loc[user_vocabs['vocab_id'] == vocab_id_update, 'vocab'] = new_vocab
            user_vocabs.loc[user_vocabs['vocab_id'] == vocab_id_update, 'vocab_origin'] = new_vocab_origin
            user_vocabs.loc[user_vocabs['vocab_id'] == vocab_id_update, 'exposure'] = new_exposure
            user_vocabs.loc[user_vocabs['vocab_id'] == vocab_id_update, 'status'] = new_status
            st.table(user_vocabs[user_vocabs['vocab_id'] == vocab_id_update])

            col1, col2, col3 = st.columns(3)
            with col2:
                submit_change = st.button("Submit Change ✅")

            if submit_change:
                # Replace the row with the new row
                vocab_rest_df = self.vocab_df[self.vocab_df['user_id'] != user_id]
                updated_df = pd.concat([vocab_rest_df, user_vocabs])
                updated_df.to_sql('my_vocabs', self.con, if_exists='replace', index=False)
                c1, c2, c3 = st.columns(3)
                with c2:
                    st.write("Vocabulary Updated! 🎉")

        st.write("# ")
        st.write("# ")
        st.write("# ")
        st.write("### Delete Vocabulary")
        with st.expander("Delete a Vocabulary"):
            user_vocab_and_id = [f"{vocab} ({vocab_id})" for vocab, vocab_id in zip(user_vocabs['vocab'].tolist(), user_vocabs['vocab_id'].tolist())]
            vocab_to_delete = st.selectbox("Please search or choose a vocabulary to delete: ", user_vocab_and_id, key="vocab_select_delete")
            try:
                vocab_id_delete = vocab_to_delete.split("(")[1].split(")")[0]
                st.table(user_vocabs[user_vocabs['vocab_id'] == vocab_id_delete])
            except:
                vocab_id_delete = None
            self.vocab_df = self.vocab_df[self.vocab_df['vocab_id'] != vocab_id_delete]
            
            c1, c2, c3 = st.columns(3)
            with c2:
                delete_vocab = st.button("Delete Vocabulary ❌")
                if delete_vocab:
                    self.vocab_df.to_sql('my_vocabs', self.con, if_exists='replace', index=False)
                    st.write("Vocabulary Deleted! 👍")


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
        st.table(status_df)
        
        # Get the total vocab count for each user
        vocab_count = self.merged_df.groupby('user').count()['vocab'].reset_index()
        vocab_count.columns = ['user', 'vocab_count']
        
        # using plotly go, visualize the bar and show values for each bar
        st.write("# ")
        st.write("# ")
        st.write("### Total Vocab Count for Each User")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=vocab_count['user'], y=vocab_count['vocab_count'], text=vocab_count['vocab_count'], textposition='auto'))
        st.plotly_chart(fig, use_container_width=True)

    def execute_all(self):
        vocab_update, user_page, vocab_analysis = st.tabs(["Vocab Update", "User Update", "Vocab Analysis"])
        with vocab_update:
            self.vocab_update()
        with user_page:
            self.user_page()
        with vocab_analysis:
            self.vocab_analysis()

VA = VocabApp()
VA.execute_all()