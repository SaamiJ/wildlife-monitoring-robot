FROM python:3.11-slim

ENV DISPLAY=:0

RUN apt-get update && apt-get install -y \
    python3-tk \
    libopencv-dev \
    python3-opencv \
    ffmpeg \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install pillow opencv-python

WORKDIR /app

COPY . /app

CMD ["python3", "main_interface.py"]