# Use an official Python runtime as a parent image
# FROM arm32v7/python:3.6-slim
# https://hub.docker.com/r/resin/raspberrypi3-python/tags/
#
# run the following command to build a rpi image
# docker run --rm --privileged multiarch/qemu-user-static:register --reset
 
FROM resin/raspberrypi3-python:3.6-slim

# Set the working directory to /app
WORKDIR /SpamMon

# Copy the current directory contents into the container at /app
ADD . /SpamMon

# install  cron
RUN apt-get update
RUN apt-get install -y --no-install-recommends cron
COPY spammon-cron /etc/cron.d/spammon-cron
RUN crontab /etc/cron.d/spammon-cron
RUN chmod 0644 /etc/cron.d/spammon-cron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV NAME SpamMon

# Run app.py when the container launches
ENTRYPOINT ["python", "SpamMon.py"]
CMD ["cron"]

