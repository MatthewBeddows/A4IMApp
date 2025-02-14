# Dockerfile
FROM ubuntu:20.04

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-pyqt5 \
    python3-pyqt5.qtwebengine \
    git \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-render-util0 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libxcb-randr0 \
    libxkbcommon-x11-0 \
    libfontconfig1 \
    libdbus-1-3

# Set up working directory
WORKDIR /app

# Install Python packages
RUN pip3 install pyinstaller \
    gitpython \
    requests \
    beautifulsoup4 \
    PyQt5

# Copy your application files
COPY . /app

# Build command
CMD ["pyinstaller", "spec_file.spec"]