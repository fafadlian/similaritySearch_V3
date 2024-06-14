# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Copy the model files into the container
COPY model /app/model

# Copy the environment file
COPY environment.env /app/environment.env

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose the port defined in the environment variable or default to 8000
EXPOSE ${PORT:-443}

# Run the command to start the FastAPI server using run.py
CMD ["python", "run.py"]



