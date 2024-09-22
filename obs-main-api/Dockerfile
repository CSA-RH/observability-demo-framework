# Use the official RHEL base image
FROM registry.redhat.io/rhel9/python-312@sha256:d8e5c0e8324c696fec3f0341250b2f7a060a5e1d478b4970a457ebb55657999c

# Set the working directory
WORKDIR /app

# Copy the application files into the container
COPY main.py .
COPY requirements.txt .

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0"]
