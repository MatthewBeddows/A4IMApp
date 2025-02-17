# Dockerfile
FROM ubuntu:18.04

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages and Python 3.8
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    wget \
    ca-certificates \
    gnutls-bin \
    libgnutls30 \
    libssl1.1 \
    openssl \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    python3.8 \
    python3.8-dev \
    python3.8-distutils \
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

# Update certificates
RUN update-ca-certificates

# Set Python 3.8 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1

# Install pip for Python 3.8
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3.8 get-pip.py

# Set up working directory
WORKDIR /app

# Install Python packages with specific versions
RUN python3.8 -m pip install \
    pyinstaller==4.5.1 \
    pyinstaller-hooks-contrib==2021.3 \
    gitpython \
    requests \
    beautifulsoup4 \
    PyQt5

# Configure git to use HTTPS instead of GnuTLS
RUN git config --global http.sslBackend openssl

# Copy your application files
COPY . /app

# Build command
CMD ["python3.8", "-m", "PyInstaller", "spec_file.spec"]