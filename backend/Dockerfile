# Python 3.10
FROM python:3.10-slim

# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user

# Set working directory
WORKDIR /app

# Upgrade pip and install requirements
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Change ownership of the app directory to the user
RUN chown -R user:user /app

# Switch to the "user" user
USER user

# Set home to execute writes
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Expose port (Hugging Face expects 7860)
EXPOSE 7860

# Command to run the app
# Hugging Face Spaces expects the app to run on port 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
