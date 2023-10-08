FROM apache/airflow:2.6.1

# RUN apt-get update && apt-get install -y git

RUN pip install --no-cache-dir numpy==1.21.6 \
    selenium==3.141.0 rq==1.10.1 redis==4.3.4 \
    beautifulsoup4==4.12.2 nltk==3.7 pandas==1.3.5 requests==2.30.0 \
    slack_sdk==3.19.5 slackclient==2.9.4 pyspellchecker==0.7.0 gitpython==3.1.24 \
    googletrans==3.1.0a0 langdetect==1.0.9 flask_limiter==3.3.1 openai==0.27.8 python_Levenshtein==0.21.1 \
    pytz==2023.3