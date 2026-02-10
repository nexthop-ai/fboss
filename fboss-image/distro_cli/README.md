### Running Tests

```bash
# Build and run all tests
cmake --build . --target distro_cli_tests

# Run via CTest
ctest -R distro_cli -V
```
<<<<<<< HEAD
||||||| 285e7f8dbe
# Run specific test
python3 -m unittest tests.cli_test
```

### Linting

```bash
cd fboss-image/distro_cli
python3 -m ruff check .
```

### Project Structure

```
fboss-image/distro_cli/
├── fboss-image          # Main CLI entry point
├── lib/                 # Core libraries
│   ├── cli.py          # CLI framework (argparse abstraction)
│   ├── manifest.py     # Manifest parsing and validation
│   ├── builder.py      # Image builder
│   └── logger.py       # Logging setup
├── cmds/               # Command implementations
│   ├── build.py        # Build command
│   └── device.py       # Device commands
└── tests/              # Unit tests
    ├── cli_test.py     # CLI framework tests
    ├── manifest_test.py
    ├── image_builder_test.py
    ├── build_test.py
    └── device_test.py
```

### CLI Framework

The CLI uses a custom OOP wrapper around argparse (stdlib only, no external dependencies):

```python
from lib.cli import CLI

# Create CLI
cli = CLI(description='My CLI')

# Add simple command
cli.add_command('build', build_func,
                help_text='Build something',
                arguments=[('file', {'help': 'Input file'})])

# Add command group with subcommands
device = cli.add_command_group('device',
                               help_text='Device commands',
                               arguments=[('mac', {'help': 'MAC address'})])
device.add_command('ssh', ssh_func, help_text='SSH to device')

# Run
cli.run(setup_logging_func=setup_logging)
```
=======

>>>>>>> 7e29d6aa34237562b62e243cce053427fffd9f09
