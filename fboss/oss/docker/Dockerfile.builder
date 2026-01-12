FROM quay.io/centos/centos:stream9

RUN mkdir -p /var/src
WORKDIR /var/src

RUN dnf install -y 'dnf-command(config-manager)'
RUN dnf config-manager --set-enabled crb
RUN dnf install -y epel-release epel-next-release
RUN dnf install -y --allowerasing \
    git sudo lsof autoconf automake binutils binutils-devel bzip2 \
    bzip2-devel cmake double-conversion double-conversion-devel libcurl-devel \
    libcurl-minimal libdwarf libdwarf-devel libevent-devel libffi libffi-devel \
    libnghttp2 libnghttp2-devel libnl3 libnl3-devel libsodium-devel \
    libsodium-static libtool libunwind libunwind-devel libusb libusb-devel \
    libzstd libzstd-devel lz4-devel ncurses-devel ninja-build openssl \
    openssl-devel openssl-libs python3 python3-devel re2 re2-devel \
    snappy-devel xxhash-devel xz-devel zlib-devel zlib-static bison flex \
    gperf libcap-devel libmount-devel gcc-toolset-12 glog libusbx xxhash-libs \
    libunwind libdwarf libsodium libgpiod

RUN dnf group install "Development Tools" -y
RUN echo "source /opt/rh/gcc-toolset-12/enable" >> /root/.bashrc
RUN python3 -m pip install boto3 botocore gitpython meson jinja2

# The following are needed for building Broadcom SDK
RUN dnf install -y doxygen aspell libyaml-devel vim-common libnsl libnsl2-devel \
    perl-diagnostics perl-sort perl-English perl-Clone perl-Data-Compare \
    perl-List-MoreUtils perl-Moose perl-YAML perl-namespace-autoclean perl-JSON-XS perl-FindBin \
    perl-Math-BigInt perl-YAML-LibYAML perl-Sys-Hostname perl-Time
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN pip install pyyaml filelock
# ============================================================

# Download and install sccache
RUN curl -L https://github.com/timn-nexthop/sccache/releases/download/v3-better-remote-only/sccache-latest-x86_64-unknown-linux-musl.zst | \
    zstdmt -d > /usr/local/bin/sccache && \
    chmod +x /usr/local/bin/sccache

RUN --mount=type=bind,dst=/var/src ./build/fbcode_builder/getdeps.py install-system-deps --recursive fboss
