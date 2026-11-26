# IQA scan level - single self-contained image (EUCAIM / local use)
# Stage 1: MathWorks' public runtime installer installs only the needed runtime products.
# Stage 2: Ubuntu 24.04 + runtime dependencies + that runtime + Python tools. No MATLAB needed.
# Build from the repository root:  docker build -f eucaim/Dockerfile -t iqaxnat_scan:1.1.0 .

############################ Stage 1: minimal MATLAB Runtime ############################
FROM containers.mathworks.com/matlab-runtime-utils/matlab-runtime-installer:r2024b-update-5 AS installer
WORKDIR /opt/matlabruntime/unzippedinstaller
# Only the 3 products the Rician package requires (its requiredMCRProducts.txt):
# runtime about 1.1 GB instead of 3.2 GB (image 2.38 GB instead of 4.41 GB)
RUN printf "destinationFolder=/tmp/matlabruntime/runtime\nagreeToLicense=yes\n" > installInputs.txt \
 && for p in "Numerics" "Python" "Signal Processing Toolbox Addin"; do \
      printf "product.MATLAB Runtime - %s\n" "$p" >> installInputs.txt; \
    done \
 && ./install -bat true -inputFile ./installInputs.txt

############################ Stage 2: final image ############################
FROM ubuntu:24.04

LABEL maintainer="feriel.ramdhane@eurobioimaging.eu, ferielramdhane@cnr.it"
LABEL version="1.1.0"
LABEL description="Image Quality Assessment at scan level (SNR, SI, MI, Rician noise level), 3D and 4D."
LABEL image.source="https://github.com/FerielRamdhane/XNAT-Quality-Metrics"
LABEL image.version="1.1.0"

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ENV PYTHONUNBUFFERED=1
ENV MPLBACKEND=Agg

# MATLAB Runtime dependencies (same list as Dockerfile.deps of the XNAT base) + Python
RUN apt-get update && apt-get install --no-install-recommends -y \
        ca-certificates gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-tools \
        libasound2t64 libatomic1 libc6 libcairo-gobject2 libcairo2 libcap2 libcups2t64 libdrm2 \
        libfontconfig1 libfribidi0 libgbm1 libgdk-pixbuf-2.0-0 libgl1 libglib2.0-0t64 \
        libgstreamer-plugins-base1.0-0 libgstreamer1.0-0 libgtk-3-0t64 libgtk2.0-0t64 libice6 \
        libltdl7 libnettle8t64 libnspr4 libnss3 libpam0g libpango-1.0-0 libpangocairo-1.0-0 \
        libpangoft2-1.0-0 libpixman-1-0 libsndfile1 libtirpc3t64 libuuid1 libwayland-client0 \
        libxcomposite1 libxcursor1 libxdamage1 libxfixes3 libxfont2 libxft2 libxinerama1 \
        libxrandr2 libxt6t64 libxtst6 libxxf86vm1 libsm6 libxext6 procps zlib1g \
        python3 python3-pip \
    && mkdir -p /usr/share/X11/xkb \
    && rm -rf /var/lib/apt/lists/*

COPY --from=installer /tmp/matlabruntime/runtime /opt/matlabruntime
RUN ln -sf /usr/lib/x86_64-linux-gnu/libstdc++.so.6 /opt/matlabruntime/R2024b/sys/os/glnxa64/libstdc++.so.6

ENV LD_LIBRARY_PATH=/opt/matlabruntime/R2024b/runtime/glnxa64:/opt/matlabruntime/R2024b/bin/glnxa64:/opt/matlabruntime/R2024b/sys/os/glnxa64:/opt/matlabruntime/R2024b/sys/opengl/lib/glnxa64:/opt/matlabruntime/R2024b/extern/bin/glnxa64
ENV MCR_CACHE_ROOT=/tmp/mcr_cache
ENV MPLCONFIGDIR=/tmp/matplotlib

RUN pip3 install --break-system-packages --no-cache-dir --timeout=300 --retries=5 \
        numpy==1.26.0 scipy==1.11.3 opencv-python==4.8.1.78 SimpleITK==2.3.1
COPY src/requirements.txt /tmp/
RUN pip3 install --break-system-packages --no-cache-dir --timeout=300 --retries=5 -r /tmp/requirements.txt
COPY src/RicianNoiseLevelPkg_R2024b-24.2-py3-none-any.whl /tmp/
RUN pip3 install --break-system-packages --no-cache-dir /tmp/RicianNoiseLevelPkg_R2024b-24.2-py3-none-any.whl \
    && rm /tmp/*.whl /tmp/requirements.txt

# EUCAIM requires the container to run as UID/GID 2323
ARG USER_UID=2323
ARG USER_GID=2323
RUN groupadd -g $USER_GID eucaim && \
    useradd -r -u $USER_UID -g eucaim -d /home/eucaim -m -s /usr/sbin/nologin eucaim

WORKDIR /app
COPY src/*.py /app/
COPY eucaim/entrypoint.sh /app/entrypoint.sh
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

USER eucaim
ENTRYPOINT ["/app/entrypoint.sh"]
