# Nexthop transceiver vendor override map

`nexthop.json` is loaded by the agents and `qsfp_service` through the
`transceiver_vendor_override_map_path` flag, set in the configs of platforms
whose platform mapping has vendor-keyed port config overrides. `package.py`
ships this directory to `/opt/fboss/share/transceiver_vendor_overrides/`.

The platform mapping keys such overrides by a placeholder vendor and part
number (`Vendor_1`, `PartNum_1`) so real optics names stay out of it. This file
resolves each placeholder to RE2 patterns, matched in full against the module
EEPROM vendor name and part number. A placeholder with no entry never matches.

Format: `cfg::TransceiverVendorOverrideMap` from
`fboss/agent/platform_config.thrift` as thrift SimpleJSON. A missing or invalid
file fails service start once the flag is set.

Generated from the Nexthop SKU tooling that also writes the placeholders into
the SI settings; do not edit by hand.
