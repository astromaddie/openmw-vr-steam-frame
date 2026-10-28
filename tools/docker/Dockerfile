FROM ubuntu:24.04@sha256:24737cef17f4e22b1977df7d9a05e77c4e28b7da5b8911f8d8ccda136bf3573c
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git curl ca-certificates pkg-config python3 python3-venv lua5.4 \
    libavcodec-dev libavformat-dev libavutil-dev libswresample-dev libswscale-dev \
    libopenal-dev libluajit-5.1-dev libicu-dev libsqlite3-dev liblz4-dev libsdl2-dev \
    zlib1g-dev libfreetype6-dev libpng-dev libjpeg-dev libtiff-dev \
    libx11-dev libxrandr-dev libxcursor-dev libxinerama-dev libxi-dev \
    libxxf86vm-dev libxkbcommon-dev libxcb-glx0-dev libudev-dev libdbus-1-dev \
    libgl-dev libopengl-dev libegl-dev libgles-dev libvulkan-dev libssl-dev xz-utils libfontconfig1-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /repo
