# IQA scan level - XNAT Container Service version
# Built on the SHARED minimal MATLAB Runtime image used by all XNAT tools (Ubuntu 24.04, Python 3.12).
# Build from the repository root:  docker build -f xnat/Dockerfile -t iqaxnat_scan:1.1.0-xnat .
ARG MCR_BASE=mcr-riciannoiselevel:r2024b
FROM ${MCR_BASE}

LABEL maintainer="feriel.ramdhane@eurobioimaging.eu, ferielramdhane@cnr.it"
LABEL version="1.1.0"
LABEL description="Image Quality Assessment at scan level (SNR, SI, MI, Rician noise level), 3D and 4D - XNAT version."
LABEL image.source="https://github.com/FerielRamdhane/XNAT-Quality-Metrics"
LABEL image.version="1.1.0"

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV MPLBACKEND=Agg
ENV MCR_CACHE_ROOT=/tmp/mcr_cache
ENV MPLCONFIGDIR=/tmp/matplotlib

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip libgl1 libglib2.0-0 libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Heavy packages first (cached layers), versions with Python 3.12 wheels
RUN pip3 install --break-system-packages --no-cache-dir --timeout=300 --retries=5 \
        numpy==1.26.0 scipy==1.11.3 opencv-python==4.8.1.78 SimpleITK==2.3.1
COPY src/requirements.txt /tmp/
RUN pip3 install --break-system-packages --no-cache-dir --timeout=300 --retries=5 -r /tmp/requirements.txt

COPY src/RicianNoiseLevelPkg_R2024b-24.2-py3-none-any.whl /tmp/
RUN pip3 install --break-system-packages --no-cache-dir /tmp/RicianNoiseLevelPkg_R2024b-24.2-py3-none-any.whl \
    && rm /tmp/*.whl /tmp/requirements.txt

WORKDIR /app
COPY src/*.py /app/
COPY xnat/entrypoint.sh /app/entrypoint.sh
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Runs as root, like v1.0: the Container Service mounts are owned by the XNAT user.
ENTRYPOINT ["/app/entrypoint.sh"]
