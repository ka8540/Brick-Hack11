# Use an official Python image
FROM python:3.11

# Set the working directory
WORKDIR /app

# Copy the project files to the container
COPY . /app

# Install system dependencies required for PyAudio
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt 



# Expose the port Chainlit runs on
EXPOSE 8000

# Run the Chainlit application
CMD ["chainlit", "run", "lumeo.py", "--port", "8000", "--host", "0.0.0.0"]
