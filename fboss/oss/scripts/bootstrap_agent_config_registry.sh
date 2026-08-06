#!/bin/bash
# Reports bootstrap agent.conf registry problems found at BUILD time.
# Each argument is <kind>:<platform>.

status=0

for item in "$@"; do
  kind=${item%%:*}
  platform=${item#*:}
  status=1
  case "$kind" in
  uncovered)
    echo "$platform: agent.conf has no entry in fboss/bootstrap_agent_configs.bzl." >&2
    echo "  Add it to _GENERATED_PLATFORMS, _IDENTITY_PLATFORMS or _EXCLUDED_PLATFORMS." >&2
    ;;
  own-mapping)
    echo "$platform: now has its own port profile mapping CSV." >&2
    echo "  Stop borrowing one: set mapping_codename = None in _GENERATED_PLATFORMS." >&2
    ;;
  own-asic)
    echo "$platform: now has its own ASIC config." >&2
    echo "  Point asic_codename at it in _GENERATED_PLATFORMS, adding an entry if" >&2
    echo "  absent and keeping any _IDENTITY_PLATFORMS entry." >&2
    ;;
  *)
    echo "unrecognised registry problem: $item" >&2
    ;;
  esac
done

exit $status
