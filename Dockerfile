# Use an official Python runtime as a parent image
FROM arm32v7/python:3.6-slim

# Set the working directory to /app
WORKDIR /SpamMon

# Copy the current directory contents into the container at /app
ADD . /SpamMon

# install  cron
RUN apt-get update && apt-get install -y --no-install-recommends cron
COPY spammon-cron /etc/cron.d/spammon-cron
RUN crontab /etc/cron.d/spammon-cron

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV NAME SpamMon

# Run app.py when the container launches
# ENTRYPOINT ["python", "SpamMon.py"]
CMD ["cron", "-f"]

