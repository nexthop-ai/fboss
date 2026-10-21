Name:           flashrom
Version:        1.7.0
Release:        2
Summary:        Utility for reading, writing, verifying and erasing flash chips
License:        GPL-2.0-only
URL:            https://www.flashrom.org/
Source0:        flashrom-v%{version}.tar.xz
# The 64 MiB BIOS flash on the Black Turtle CPU card (m4061nhp, m4062nhp).
# Without it the chip probes as "unknown Macronix SPI chip" and fw_util cannot
# program the BIOS. Backport of https://review.coreboot.org/c/flashrom/+/96393;
# drop it once a flashrom release includes that change.
Patch0:         0001-flashchips-Add-Macronix-MX77U51255G.patch

# Disable automatic debuginfo/debugsource subpackages. This is a small
# helper RPM built inside the fboss-image container; we don't need
# separate -debuginfo/-debugsource packages, and the default macros can
# fail with an empty debugsourcefiles.list.
%global debug_package %{nil}
%global _enable_debug_packages 0
%global _no_debugsource 1

BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  pkgconfig(libusb-1.0)
BuildRequires:  pkgconfig(libftdi1)
BuildRequires:  pkgconfig(libpci)
BuildRequires:  pkgconfig(openssl)
BuildRequires:  pkgconfig(zlib)

%description
flashrom is a utility for detecting, reading, writing, verifying and erasing
flash chips. It is often used to flash BIOS/EFI/coreboot/firmware images
in-system using a supported mainboard, but it also supports flashing of
network cards, SATA controller cards, and other external devices which can
program flash chips.

%prep
%autosetup -p1 -n flashrom-v%{version}

%build
# -Dtests=disabled: flashrom 1.7 bundles cmocka 1.1.5 which fails to compile
# under GCC 11 with -Werror=clobbered. Tests are not needed for packaging.
meson setup builddir --prefix=/usr -Dtests=disabled
meson compile -C builddir

%install
rm -rf "%{buildroot}"
meson install -C builddir --destdir="%{buildroot}"

# Upstream installs the binary into /usr/sbin. We also want a
# /usr/bin/flashrom for tools (like fw_util) that expect it there.
mkdir -p "%{buildroot}/usr/bin"
ln -sf ../sbin/flashrom "%{buildroot}/usr/bin/flashrom"

# Drop unused static archive: rpm's strip re-timestamps it, breaking reproducibility.
rm -f "%{buildroot}/usr/lib64/libflashrom.a"

%files
/usr/sbin/flashrom
/usr/bin/flashrom
/usr/include/libflashrom.h
/usr/lib64/libflashrom.so
/usr/lib64/libflashrom.so.1
/usr/lib64/libflashrom.so.1.0.0
/usr/lib64/pkgconfig/flashrom.pc
/usr/share/bash-completion/completions/flashrom.bash
