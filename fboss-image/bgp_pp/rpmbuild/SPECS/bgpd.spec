Name: bgpd
Version: 1.0
Release: 1
Summary: Meta bgp++ routing daemon
License: Meta
# NOTE: Source tarball still uses the old "bgp_pp" naming because the S3
# artifact has not been renamed yet.
Source0: bgp_pp-%{version}.tar.gz
BuildRequires: systemd-rpm-macros rpm cpio
AutoReqProv: no

%description
Meta bgp++ routing daemon for FBOSS-based network switches.
Bundles the fb-platform010 compat runtime libraries required by bgpd_cpp.

%prep
# NOTE: tarball extracts to bgp_pp-%{version}/ — matches the S3 artifact layout.
%setup -q -c -n bgp_pp-%{version}

%install
mkdir -p %{buildroot}/usr/sbin
install -m 755 bgpd_cpp %{buildroot}/usr/sbin/bgpd_cpp

mkdir -p %{buildroot}/etc/coop
install -m 644 bgpcpp.conf %{buildroot}/etc/coop/bgpcpp.conf

mkdir -p %{buildroot}%{_unitdir}
install -m 644 %{_sourcedir}/bgpd.service %{buildroot}%{_unitdir}/bgpd.service

# Embed the compat-runtime libs (bgpd_cpp is dynamically linked against these)
rpm2cpio fb-platform010-compat-runtime-*.x86_64.rpm | (cd %{buildroot} && cpio -idm)

# bgpd_cpp hardcodes interpreter /usr/local/fbcode/platform010/lib/ld.so but the
# compat-runtime installs to platform010-compat/. Symlink to bridge the gap.
mkdir -p %{buildroot}/usr/local/fbcode/platform010
ln -s /usr/local/fbcode/platform010-compat/lib %{buildroot}/usr/local/fbcode/platform010/lib

%files
%defattr(-,root,root,-)
/usr/sbin/bgpd_cpp
%config(noreplace) /etc/coop/bgpcpp.conf
%{_unitdir}/bgpd.service
/usr/local/fbcode/platform010-compat/
/usr/local/fbcode/platform010/

%post
systemctl enable bgpd.service

%preun
%systemd_preun bgpd.service

%postun
%systemd_postun_with_restart bgpd.service
