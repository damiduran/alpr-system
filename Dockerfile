# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Ensure the assets and data directories exist
RUN mkdir -p assets/downloads alpr_data

# The bot doesn't expose a port, but Railway/Render might expect one.
# For a background worker, we don't necessarily need to EXPOSE.

# Run main.py when the container launches
CMD ["python", "main.py"]
