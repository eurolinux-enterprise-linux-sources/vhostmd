%global have_xen 0

Summary:       Virtualization host metrics daemon
Name:          vhostmd
Version:       0.4
Release:       2.8%{?dist}
License:       GPLv2+
Group:         System Environment/Daemons
BuildRoot:     %{_tmppath}/%{name}-%{version}-%{release}-root

URL:           http://gitorious.org/vhostmd

# Upstream tarball hosting is screwed at the moment.  This release is
# of the 0.4 branch, with 'make dist' done by the packager.
Source0:       vhostmd-%{version}.tar.bz2
Source1:       vhostmd.init
Source2:       vhostmd.sysconfig
Source3:       vhostmd.conf

# vhostmd doesn't set supplemental groups correctly
# https://bugzilla.redhat.com/show_bug.cgi?id=741289
Patch0:        0001-Security-Set-supplemental-groups-correctly-when-drop.patch

# Fix segfault in libmetrics
# https://bugzilla.redhat.com/show_bug.cgi?id=820500
Patch1:        0001-libmetrics-Return-error-indication-up-through-get_me.patch

BuildRequires: chrpath
BuildRequires: pkgconfig
BuildRequires: libxml2-devel
BuildRequires: libvirt-devel

%if %{have_xen}
BuildRequires: xen-devel
%endif

Requires(post): chkconfig
Requires(preun): chkconfig
Requires(preun): initscripts
Requires(postun): initscripts
Requires(pre): shadow-utils


%description 
vhostmd provides a "metrics communication channel" between a host and
its hosted virtual machines, allowing limited introspection of host
resource usage from within virtual machines.


%package -n    vm-dump-metrics
Summary:       Virtualization host metrics dump 
Group:         Applications/System


%description -n vm-dump-metrics
Executable to dump all available virtualization host metrics to stdout
or a file.


%package -n    vm-dump-metrics-devel
Summary:       Virtualization host metrics dump development 
Group:         Development/Libraries
Requires:      vm-dump-metrics = %{version}-%{release}
Requires:      pkgconfig


%description -n vm-dump-metrics-devel
Header and libraries necessary for metrics gathering development


%prep
%setup -q

%patch0 -p1
%patch1 -p1


%build
%configure \
%if %{have_xen} == 0
  --without-xenstore \
%endif
  --enable-shared --disable-static
make %{_smp_mflags}


%install
rm -rf $RPM_BUILD_ROOT

make DESTDIR=$RPM_BUILD_ROOT install

mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/init.d
install -m 0755 %{SOURCE1} $RPM_BUILD_ROOT%{_sysconfdir}/init.d/%{name}

mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig
install -m 0644 %{SOURCE2} $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/%{name}

#rm $RPM_BUILD_ROOT%{_libdir}/libmetrics.a
rm $RPM_BUILD_ROOT%{_libdir}/libmetrics.la

chrpath --delete $RPM_BUILD_ROOT%{_sbindir}/vm-dump-metrics

# Remove docdir - we'll make a proper one ourselves.
rm -r $RPM_BUILD_ROOT%{_docdir}/vhostmd

# Remove metric.dtd from /etc.
rm $RPM_BUILD_ROOT%{_sysconfdir}/vhostmd/metric.dtd

# The default configuration file is great for Xen, not so great
# for anyone else.  Replace it with one which is better for libvirt
# users.
mv $RPM_BUILD_ROOT%{_sysconfdir}/vhostmd/vhostmd.conf \
   $RPM_BUILD_ROOT%{_sysconfdir}/vhostmd/vhostmd.conf.for.xen
cp %{SOURCE3} $RPM_BUILD_ROOT%{_sysconfdir}/vhostmd/vhostmd.conf

# Remove Perl script (https://bugzilla.redhat.com/show_bug.cgi?id=749875)
rm $RPM_BUILD_ROOT%{_datadir}/vhostmd/scripts/pagerate.pl


%clean
rm -rf $RPM_BUILD_ROOT


%post
/sbin/chkconfig --add vhostmd


%preun
if [ $1 = 0 ] ; then
  /sbin/service vhostmd stop >/dev/null 2>&1
  /sbin/chkconfig --del vhostmd
fi


%postun
if [ "$1" -ge "1" ] ; then
  /sbin/service vhostmd condrestart >/dev/null 2>&1 || :
fi


%post -n vm-dump-metrics -p /sbin/ldconfig


%postun -n vm-dump-metrics -p /sbin/ldconfig


%pre
# UID:GID 112:112 reserved, see RHBZ#534109.
getent group vhostmd >/dev/null || groupadd -g 112 -r vhostmd
getent passwd vhostmd >/dev/null || \
useradd -u 112 -r -g vhostmd -d %{_datadir}/vhostmd -s /sbin/nologin \
-c "Virtual Host Metrics Daemon" vhostmd
exit 0


%files
%defattr(-,root,root,-)
%doc AUTHORS ChangeLog COPYING README
%doc mdisk.xml metric.dtd vhostmd.dtd vhostmd.xml

%{_sbindir}/vhostmd

%dir %{_sysconfdir}/vhostmd
%config(noreplace) %{_sysconfdir}/vhostmd/vhostmd.conf
%config(noreplace) %{_sysconfdir}/vhostmd/vhostmd.conf.for.xen
%config %{_sysconfdir}/vhostmd/vhostmd.dtd
%{_sysconfdir}/init.d/%{name}
%config(noreplace) %{_sysconfdir}/sysconfig/%{name}

%dir %{_datadir}/vhostmd
%dir %{_datadir}/vhostmd/scripts

%{_mandir}/man8/vhostmd.8.gz


%files -n vm-dump-metrics
%defattr(-,root,root,-)
%doc COPYING
%{_sbindir}/vm-dump-metrics
%{_libdir}/libmetrics.so.0
%{_libdir}/libmetrics.so.0.0.0
%{_mandir}/man1/vm-dump-metrics.1.gz


%files -n vm-dump-metrics-devel
%defattr(-,root,root,-)
%doc README
%{_libdir}/libmetrics.so
%dir %{_includedir}/vhostmd
%{_includedir}/vhostmd/libmetrics.h


%changelog
* Fri Jul  5 2013 Richard W.M. Jones <rjones@redhat.com> - 0.4-2.8
- Fix segfault in libmetrics
  resolves: rhbz#820500

* Fri Mar 23 2012 Richard W.M. Jones <rjones@redhat.com> - 0.4-2.7
- Delete PID file in stop action (updated)
  resolves: rhbz#766674

* Mon Mar  5 2012 Richard W.M. Jones <rjones@redhat.com> - 0.4-2.6
- Security: Set supplemental groups correctly when dropping privileges
  resolves: rhbz#741289
- Remove pagerate.pl Perl script (749875).
- Delete PID file in stop action
  resolves: rhbz#766674

* Fri Jul 23 2010 Richard W.M. Jones <rjones@redhat.com> - 0.4-2.4
- /etc/sysconfig/vhostmd: Default to KVM (RHBZ#616783).

* Tue Jul  6 2010 Richard W.M. Jones <rjones@redhat.com> - 0.4-2.3
- Updated vhostmd.conf from Dr. Joachim Schneider at SAP.

* Thu Jan 14 2010 Richard W.M. Jones <rjones@redhat.com> - 0.4-2.2
- Import package from Fedora Rawhide and check.
- Disable Xen support.

* Thu Dec 10 2009 Richard W.M. Jones <rjones@redhat.com> - 0.4-2
- Fix the PagedOutMemory and PagedInMemory stats to report MB instead
  of pages (fixes supplied by Joachim Schneider).

* Wed Dec  9 2009 Richard W.M. Jones <rjones@redhat.com> - 0.4-1
- vhostmd didn't chdir ("/") when daemonizing.  Fixed in this 0.4 release.

* Tue Nov 17 2009 Richard W.M. Jones <rjones@redhat.com> - 0.4-0.9.gite9db007b
- Add a timestamp to the metrics.
- Fix a typo in MemoryAllocatedToVirtualServers metric
  (https://bugzilla.redhat.com/show_bug.cgi?id=532070#c7)
- %{_sysconfdir}/sysconfig/vhostmd: Use libvirt default URI
  (https://bugzilla.redhat.com/show_bug.cgi?id=537828)
- %{_sysconfdir}/init.d/vhostmd: If using libvirt's default URI, then pass
  the root URI to vhostmd (the default URI changes in some circumstances
  when vhostmd switches to the non-root user).

* Wed Nov 11 2009 Richard W.M. Jones <rjones@redhat.com> - 0.4-0.8.gite9db007b
- Use fixed UID:GID 112:112 (RHBZ#534109).

* Tue Nov 10 2009 Richard W.M. Jones <rjones@redhat.com> - 0.4-0.7.gite9db007b
- vm-dump-metrics-devel package should require version and release of
  base package.

* Mon Nov  2 2009 Richard W.M. Jones <rjones@redhat.com> - 0.4-0.6.gite9db007b
- Some changes to the default configuration file suggested by SAP to
  make it more CIM standards compliant.

* Fri Oct 16 2009 Richard W.M. Jones <rjones@redhat.com> - 0.4-0.5.gite9db007b
- New upstream based on git e9db007b.
- Fix segfault in vm-dump-metrics (RHBZ#529348).
- On error, vm-dump-metrics now exits with status code 1.

* Thu Oct 15 2009 Richard W.M. Jones <rjones@redhat.com> - 0.4-0.2.gitea2f772d
- New upstream based on git ea2f772d.
- Update the configuration file based on upstream changes to how virsh
  has to be run.
- vhostmd should run non-root as user 'vhostmd'.
- Allow libvirt URI to be configured.

* Tue Oct 13 2009 Richard W.M. Jones <rjones@redhat.com> - 0.4-0.1.git326f0012172
- Move to pre-release of 0.4, self-built tarball.
- Disable xenstore on non-x86 platforms.
- Add patch to fix --without-xenstore option.
- Use have_xen RPM macro.

* Mon Oct 12 2009 Richard W.M. Jones <rjones@redhat.com> - 0.3-3
- Remove metric.dtd file from /etc (fixes rpmlint warning), but
  vhostmd.dtd has to remain because it is needed to validate the
  XML configuration file.
- Remove ExclusiveArch, instead conditionally depend on xen-devel.
- Use a better, less noisy, more minimal configuration file which
  doesn't depend on Xen.

* Thu Oct  8 2009 Richard W.M. Jones <rjones@redhat.com> - 0.3-1
- New upstream version 0.3.

* Fri Aug 14 2009 Richard W.M. Jones <rjones@redhat.com> - 0.2-1
- Initial packaging for Fedora, based on SuSE package.
