# Use Python 3.8 image from Alpine
FROM python:3.10

# Expose port 8502
EXPOSE 8502

# Create Working Directory called automation
WORKDIR /automation

# Copy the scripts and requirements.txt file
COPY ./requirements.txt requirements.txt
COPY ./app.py app.py
COPY .env .env
COPY table_streamlit.py table_streamlit.py
COPY scrape_images.py scrape_images.py

# Install the Python dependencies
RUN pip install -r requirements.txt

# Set environment variables
ENV HISTIGNORE='doppler*'
ENV DOPPLER_TOKEN="dp.st.dev_jaehyung.EHcNQQTcjZQyY5Q0gDd5f8wzoyNbWpgfcyXRXDEXhU6"

# Run Web server with Python to keep container running
CMD streamlit run --server.port 8502 --server.enableCORS true app.py