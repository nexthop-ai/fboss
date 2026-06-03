// cFBOSS service stub. The same compiled binary is installed at six service
// paths (platform_manager, sensor_service, fan_service, data_corral_service,
// led_service, qsfp_service) when CMake is configured with BUILD_CFBOSS=ON, so
// the existing systemd unit files run unmodified and the dependency graph
// resolves naturally.
//
// Lifecycle selection: systemd sets $NOTIFY_SOCKET in the env iff the unit
// declares Type=notify (or notify-reload/dbus). Type=simple services (sensor,
// fan, data_corral, led, qsfp) won't have it set; platform_manager
// (Type=notify) will. We call sd_notify(READY=1) unconditionally -- libsystemd
// reads $NOTIFY_SOCKET internally and the call is a no-op when it's unset, so
// Type=simple services get no-op'd and Type=notify services transition to
// active. No explicit type selection is needed in this binary.
//
// Any extra flags the unit files pass (e.g. --run_once=false,
// --thrift_ssl_policy=disabled) are accepted via
// gflags::AllowCommandLineReparsing and ignored.

#include <gflags/gflags.h>
#include <systemd/sd-daemon.h>

#include <unistd.h>
#include <atomic>
#include <csignal>

namespace {
std::atomic<bool> shouldExit{false};
void onSigterm(int /*signum*/) {
  shouldExit.store(true);
}
} // namespace

int main(int argc, char** argv) {
  gflags::AllowCommandLineReparsing();
  gflags::ParseCommandLineFlags(&argc, &argv, /*remove_flags=*/false);

  std::signal(SIGTERM, onSigterm);
  std::signal(SIGINT, onSigterm);

  sd_notify(0, "READY=1");

  while (!shouldExit.load()) {
    pause();
  }
  return 0;
}
