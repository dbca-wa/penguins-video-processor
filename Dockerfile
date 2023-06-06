FROM python:3.11.3-bullseye
MAINTAINER asi@dbca.wa.gov.au
LABEL org.opencontainers.image.source https://github.com/dbca-wa/penguins-video-processor

RUN apt-get update -y \
  && apt install -y handbrake-cli \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY processor.py ./
CMD ["python", "processor.py"]
