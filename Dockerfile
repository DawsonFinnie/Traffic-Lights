# Start from an official Python image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements first - Docker caches this layer
# so it won't reinstall packages every time you change your code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Tell Docker the app listens on port 5000
EXPOSE 8500

# Command to run the app
CMD ["python", "-m", "app.main"]