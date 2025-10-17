# Copyright 2025 Nexthop Systems Inc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Required: Ensure kernel_version is provided
%{?!kernel_version:%{error:kernel_version not provided. Provide it with --define 'kernel_version X.Y.Z'}}

# Disable debug packages
%global debug_package %{nil}

# Disable shebang mangling (kernel scripts have their own shebang conventions)
%global __brp_mangle_shebangs %{nil}

Name: kernel
Version: %{kernel_version}
Release: 1.fboss%{?dist}
Epoch: 1
Summary: Linux kernel for FBOSS (v%{version})
License: GPLv2
URL: https://github.com/torvalds/linux

# Primary kernel source
Source0: https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-%{version}.tar.xz
# FBOSS configuration sources (included in SRPM)
Source1: fboss-reference.config
Source2: fboss-local-overrides.config

# Default in-container scripts dir (override via --define container_scripts_dir if needed)
%global container_scripts_dir /workspace/fboss-image/kernel/scripts

# Build requirements
BuildRequires: gcc, make
BuildRequires: openssl-devel, elfutils-libelf-devel, dwarves
BuildRequires: bc, rsync, tar, xz
BuildRequires: perl, python3

%description
The Linux kernel for FBOSS based on upstream Linux v%{version}
with production FBOSS configuration.

%package core
Summary: Core kernel package for FBOSS
Requires: kernel-modules = %{epoch}:%{version}-%{release}
Provides: kernel = %{epoch}:%{version}-%{release}
Provides: kernel-%{_target_cpu} = %{epoch}:%{version}-%{release}
Provides: kernel-uname-r = %{version}-%{release}.%{_target_cpu}

%package modules
Summary: Kernel modules for FBOSS
Requires: kernel-core = %{epoch}:%{version}-%{release}

%package headers
Summary: Header files for the Linux kernel
Requires: kernel-core = %{epoch}:%{version}-%{release}

%package devel
Summary: Development package for building kernel modules
Requires: kernel-headers = %{epoch}:%{version}-%{release}

%description core
%{summary}

%description modules
%{summary}

%description headers
%{summary}

%description devel
%{summary}

# SRPM creation phase - everything here goes into source RPM
%prep
%setup -q -n linux-%{version}

# Prepare kernel config (defconfig + FBOSS reference + local overrides)
%{__chmod} +x %{container_scripts_dir}/prepare_config.sh
%{container_scripts_dir}/prepare_config.sh . %{SOURCE1} %{SOURCE2}

# Build phase - creates binary artifacts for RPM
%build
# Build with FBOSS toolchain (using gcc-toolset-12 from container)
export CC=gcc
export LD=ld

# Build kernel and modules
make %{?_smp_mflags} bzImage modules

# Install phase - places files for binary RPM packaging
%install
mkdir -p %{buildroot}/boot
mkdir -p %{buildroot}/lib/modules

# Install kernel
cp arch/x86/boot/bzImage %{buildroot}/boot/vmlinuz-%{version}-%{release}.%{_arch}
cp System.map %{buildroot}/boot/System.map-%{version}-%{release}.%{_arch}
cp .config %{buildroot}/boot/config-%{version}-%{release}.%{_arch}

# Install modules
make %{?_smp_mflags} modules_install INSTALL_MOD_PATH=%{buildroot} INSTALL_MOD_STRIP=1

# Remove problematic symlinks that point to build directories
rm -f %{buildroot}/lib/modules/%{version}/build
rm -f %{buildroot}/lib/modules/%{version}/source

# Install headers
make %{?_smp_mflags} headers_install INSTALL_HDR_PATH=%{buildroot}/usr

# Install kernel-devel files for building external modules (Broadcom SAI on x86_64)
KERNELDEV=%{buildroot}/usr/src/kernels/%{version}
mkdir -p $KERNELDEV

# Essential build files
cp .config $KERNELDEV/
cp Module.symvers $KERNELDEV/
cp Makefile $KERNELDEV/

# Kernel headers (including generated headers like autoconf.h)
cp -a include $KERNELDEV/

# Scripts directory (required by kernel Makefile for building modules)
cp -a scripts $KERNELDEV/

# Tools directory - only copy compiled binaries needed for module builds
mkdir -p $KERNELDEV/tools/objtool
if [ -f tools/objtool/objtool ]; then
    cp tools/objtool/objtool $KERNELDEV/tools/objtool/
fi

# x86_64 architecture files
mkdir -p $KERNELDEV/arch/x86
cp -a arch/x86/include $KERNELDEV/arch/x86/
cp arch/x86/Makefile $KERNELDEV/arch/x86/

# Files sections - defines what goes into each binary RPM
%files core
%defattr(-,root,root)
/boot/vmlinuz-%{version}-%{release}.%{_arch}
/boot/System.map-%{version}-%{release}.%{_arch}
/boot/config-%{version}-%{release}.%{_arch}

%files modules
%defattr(-,root,root)
/lib/modules/%{version}/

%files headers
%defattr(-,root,root)
/usr/include/

%files devel
%defattr(-,root,root)
/usr/src/kernels/%{version}/

%changelog
* Fri Oct 03 2025 Project Mosaic Team <meta-support@nexthop.ai> - %{version}-1.fboss
- Initial FBOSS kernel package for v%{version}

