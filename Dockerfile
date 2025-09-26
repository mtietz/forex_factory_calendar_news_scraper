 FROM python:3.9-slim

   # Install Chrome and dependencies for Selenium
   RUN apt-get update && apt-get install -y \
       wget \
       gnupg \
       unzip \
       && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
       && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
       && apt-get update \
       && apt-get install -y google-chrome-stable

   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt

   COPY . .

   EXPOSE 5000
   CMD ["python", "app.py"]