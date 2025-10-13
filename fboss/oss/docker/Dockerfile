FROM quay.io/centos/centos:stream9

# Build arguments for user creation
ARG USERNAME=root
ARG USER_UID=0
ARG USER_GID=0
ARG USER_SHELL=/bin/bash

# Download and install sccache
RUN curl -L https://github.com/mozilla/sccache/releases/download/v0.10.0/sccache-v0.10.0-x86_64-unknown-linux-musl.tar.gz -o sccache.tar.gz && \
    tar xzf sccache.tar.gz && \
    mv sccache-v0.10.0-x86_64-unknown-linux-musl/sccache /usr/local/bin/ && \
    rm -rf sccache-v0.10.0-x86_64-unknown-linux-musl sccache.tar.gz

# Mount point for extra files.
RUN mkdir -p /var/extras

RUN dnf install -y 'dnf-command(config-manager)' && \
    dnf config-manager --set-enabled crb && \
    dnf install -y epel-release epel-next-release
RUN dnf install -y --allowerasing autoconf automake binutils binutils-devel bzip2 \
    bzip2-devel cmake double-conversion double-conversion-devel libcurl-devel \
    libcurl-minimal libdwarf libdwarf-devel libevent-devel libffi libffi-devel \
    libnghttp2 libnghttp2-devel libnl3 libnl3-devel libsodium-devel \
    libsodium-static libtool libunwind libunwind-devel libusb libusb-devel \
    libzstd libzstd-devel lz4-devel ncurses-devel ninja-build openssl \
    openssl-devel openssl-libs python3 python3-devel re2 re2-devel \
    snappy-devel xxhash-devel xz-devel zlib-devel zlib-static \
    libxml2-devel expat-devel wget \
    git sudo lsof `basename "$USER_SHELL"`
RUN python3 -m pip install boto3 botocore

# Use /var/FBOSS as the set location to clone the git repository and store the outputs of the build.
WORKDIR /var/FBOSS/fboss
COPY build/fbcode_builder /var/FBOSS/fboss/build/fbcode_builder
RUN ./build/fbcode_builder/getdeps.py install-system-deps --recursive fboss && \
    rm -rf build

RUN dnf install bison flex -y && \
    dnf group install "Development Tools" -y && \
    python3 -m pip install gitpython meson jinja2 && \
    dnf install gperf libcap-devel libmount-devel -y && \
    dnf install gcc-toolset-12 gcc-toolset-12-libasan-devel gcc-toolset-12-libubsan-devel -y && \
    echo "source /opt/rh/gcc-toolset-12/enable" >> /etc/profile.d/gcc-toolset-12.sh

# The following libraries are needed for building SDK
RUN dnf install -y doxygen aspell libyaml-devel vim-common libnsl libnsl2-devel
# Install Perl modules
RUN dnf install -y perl-diagnostics perl-sort perl-English perl-Clone perl-Data-Compare \
    perl-List-MoreUtils perl-Moose perl-YAML perl-namespace-autoclean perl-JSON-XS perl-FindBin \
    perl-Math-BigInt perl-YAML-LibYAML perl-Sys-Hostname perl-Time
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN pip install pyyaml filelock
# ============================================================

# Configure sudoers to allow wheel group passwordless sudo
RUN echo "%wheel ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Create user if USERNAME is not root
RUN if [ "$USERNAME" != "root" ] && [ "$USER_UID" != "0" ]; then \
    groupadd -g $USER_GID $USERNAME && \
    useradd -m -u $USER_UID -g $USER_GID -G root,adm,wheel,users -s $USER_SHELL $USERNAME && \
    chown -R $USERNAME /var/FBOSS; \
    fi

USER ${USERNAME}
