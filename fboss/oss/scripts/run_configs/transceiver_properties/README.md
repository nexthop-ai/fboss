# Nexthop transceiver properties override

`nexthop.json5` is loaded by `qsfp_service` through the
`transceiver_properties_config` flag, which every Nexthop `qsfp.conf` and
qsfp hw test config sets to
`/opt/fboss/share/transceiver_properties/nexthop.json5`.

The file **replaces** the compiled-in default table in
`fboss/qsfp_service/module/properties/TransceiverPropertiesDefault.h`; it is
not merged on top of it. It must therefore carry every upstream entry plus the
Nexthop-specific ones. When the upstream default changes, re-sync this file.

`NexthopTransceiverPropertiesDriftTest` (in
`transceiver_properties_manager_test`, run by the CI unit-test step) fails
when this file drifts from the default table: every default entry must be
present and identical here, and any extra entry must be listed in the test's
`kNexthopOnlyCodes`. Update both that list and the list below when adding a
Nexthop-only entry.

Nexthop-only entries:

- `22` (`DR4_800G`): keyed on the first application advertised by the
  Nexthop P-800-2-4xDR 800G optic (8x100G-DR1, host code 0x4B).

`39` (`DR8_1600G`, the Nexthop P-1T6-2-4xDR 1.6T optic) is also carried here
but already lives in the compiled-in default table, so it is not Nexthop-only.
