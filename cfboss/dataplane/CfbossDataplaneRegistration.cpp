// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.
//
// Static-init translation unit that wires the cfboss dataplane into the
// generic FBOSS hook + registry points (InitHookRegistry,
// FakeSaiPacketBackendRegistry). The file is linked into both agent binaries
// only when BUILD_CFBOSS=ON; nothing in FBOSS itself references it. Behavior
// switches over automatically at process startup because the kRegister
// global's constructor runs before main().
//
// This .cpp MUST be linked with --whole-archive (or live in a .so) so its
// translation unit is not discarded by the linker for lack of external
// references.

#include "cfboss/dataplane/KernelRouteSyncer.h"
#include "cfboss/dataplane/PortMap.h"
#include "cfboss/dataplane/VethIpInstaller.h"
#include "cfboss/dataplane/VethPacketBackend.h"
#include "fboss/agent/InitHookRegistry.h"
#include "fboss/agent/SwSwitch.h"
#include "fboss/agent/hw/sai/fake/FakeSaiPacketBackend.h"
#include "fboss/agent/state/Port.h"
#include "fboss/agent/state/PortMap.h"
#include "fboss/agent/state/StateDelta.h"
#include "fboss/agent/state/SwitchState.h"

#include <folly/logging/xlog.h>

#include <memory>

namespace facebook::fboss::cfboss {

namespace {

// Single shared PortMap instance, loaded once per process on first access.
// Each agent process takes exactly one hook path: hw_agent loads it from the
// PreSaiInit hook, sw_agent from the PostConfigApplied hook.
std::shared_ptr<const PortMap> loadPortMapOnce() {
  static std::shared_ptr<const PortMap> pm = std::make_shared<const PortMap>(
      PortMap::loadFromFile(PortMap::kDefaultPath));
  return pm;
}

void registerKernelDataplaneObservers(SwSwitch* sw) {
  if (!sw) {
    XLOG(ERR) << "cfboss: PostConfigApplied hook got null SwSwitch";
    return;
  }
  auto pm = loadPortMapOnce();

  // Both observers are intentionally leaked. SwSwitch keeps observers for
  // the process lifetime and does not own their storage; the simplest
  // correct ownership model here is to never delete them. Each pair holds an
  // open libnl socket, so a process that cycles multiple SwSwitch instances
  // (one run of this hook per cycle) leaks two observers and their fds per
  // cycle — acceptable for the single-switch cfboss container.
  auto installer = new VethIpInstaller(pm);
  sw->registerStateObserver(installer, "VethIpInstaller");
  auto routeSyncer = new KernelRouteSyncer(pm);
  sw->registerStateObserver(routeSyncer, "KernelRouteSyncer");

  // registerStateObserver only delivers future deltas, so seed each observer
  // with a synthetic empty->current delta covering the state applied before
  // registration. The seed must run on the update EventBase: StateObserver
  // callbacks are serialized on that thread and real deltas can already be
  // in flight once the switch is CONFIGURED, so invoking stateUpdated from
  // this (init) thread would race them. The delta is built inside the
  // marshaled lambda so it reflects the state current when the seed actually
  // runs, keeping it ordered with any delta delivered before it.
  sw->getUpdateEvb()->runInFbossEventBaseThread([sw, installer, routeSyncer]() {
    auto emptyState = std::make_shared<SwitchState>();
    emptyState->publish();
    StateDelta initialDelta(emptyState, sw->getState());
    XLOG(INFO) << "cfboss: seeding observers with initial-state delta";
    installer->stateUpdated(initialDelta);
    routeSyncer->stateUpdated(initialDelta);
  });

  // Defensive: in split-agent mode the SAI port-state-change notification
  // path can land before sw_agent is ready to consume it, leaving FBOSS's
  // port LinkState stuck at Down despite veths being kernel-UP. Fire
  // linkStateChanged(UP) directly for every enabled port so the LinkState
  // machine ends in the correct state regardless of timing.
  XLOG(INFO) << "cfboss: firing linkStateChanged(UP) for every enabled port";
  auto state = sw->getState();
  size_t fired = 0;
  for (const auto& portMapPair : std::as_const(*state->getPorts())) {
    for (const auto& portPair : std::as_const(*portMapPair.second)) {
      const auto& port = portPair.second;
      if (port->isEnabled()) {
        sw->linkStateChanged(port->getID(), /*up=*/true, port->getPortType());
        ++fired;
      }
    }
  }
  XLOG(INFO) << "cfboss: linkStateChanged(UP) fired for " << fired << " ports";
}

struct Register {
  Register() {
    XLOG(INFO) << "cfboss_dataplane: registering InitHooks "
               << "(PreSaiInit, PostConfigApplied)";

    // PreSaiInit (hw_agent): install the AF_PACKET-backed packet backend
    // into the Fake-SAI registry. Must happen before SAI init creates ports
    // so backend.onPortCreated() callbacks have somewhere to land.
    InitHookRegistry::registerHook([]() {
      XLOG(INFO) << "cfboss: PreSaiInit hook — installing VethPacketBackend";
      auto pm = loadPortMapOnce();
      FakeSaiPacketBackendRegistry::install(
          std::make_unique<VethPacketBackend>(pm));
    });

    // PostConfigApplied (sw_agent): register the kernel-dataplane observers.
    InitHookRegistry::registerHook(
        [](SwSwitch* sw) { registerKernelDataplaneObservers(sw); });
  }
};

// Static initializer — constructor runs before main() and performs all
// registrations. Linker must include this translation unit (use
// --whole-archive on the cfboss_dataplane static library).
Register kRegister;

} // namespace

} // namespace facebook::fboss::cfboss
