# TMS Agent - Terminal Management System Agent

Windows agent program for managing TC-200 payment terminals.

## Overview

The TMS Agent is a Python-based service that runs on Windows PCs at store locations. It communicates with TC-200 terminals via USB and sends status updates to the central TMS server every 5 minutes.

## Features

- **Heartbeat Monitoring**: Sends terminal status to server every 5 minutes
- **Automatic Reconnection**: Recovers from connection failures automatically
- **Remote Commands**: Executes commands from server (reboot, firmware update, config changes)
- **System Monitoring**: Collects CPU, memory, and disk usage metrics
- **Firmware Updates**: Downloads and installs firmware updates remotely
- **Error Reporting**: Sends alerts when terminal errors are detected

## Requirements

- Windows 7 or later
- Python 3.8 or later
- TC-200.dll (proprietary terminal control library)
- Network connection to TMS server

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Place TC-200.dll in the `dll/` directory

3. Configure the agent by editing `config.ini`:
```ini
[Server]
url = https://tms-api.techcore.com/api/v1
timeout = 30

[Agent]
version = 1.0.0
heartbeat_interval = 300
auto_update_enabled = true
log_level = INFO

[Terminal]
dll_path = dll/TC-200.dll
connection_timeout = 10
retry_attempts = 3

[Paths]
log_dir = logs
data_dir = data
temp_dir = temp
```

## Usage

### Run as foreground process:
```bash
python main.py
```

### Run as Windows service:
```bash
python service.py install
python service.py start
```

## Architecture

```
TMS Agent
├── main.py                 # Main entry point and orchestration
├── config.py               # Configuration management
├── terminal_controller.py  # TC-200 hardware interface
├── api_client.py           # Server communication
├── monitoring.py           # System metrics collection
└── dll/
    └── TC-200.dll          # Terminal control library
```

## Communication Flow

1. **Registration**: Agent registers with server on first startup
2. **Heartbeat Loop**: Every 5 minutes, agent sends:
   - Terminal status (online/offline/error)
   - System metrics (CPU, memory, disk)
   - Firmware version
   - Transaction count
3. **Command Processing**: Server responds with pending commands
4. **Command Execution**: Agent executes commands and reports results

## Mock Mode

If TC-200.dll is not available, the agent automatically runs in mock mode for testing purposes. Mock mode simulates terminal responses without requiring actual hardware.

## Logging

Logs are stored in the `logs/` directory with daily rotation:
- `agent_YYYYMMDD.log` - Daily log file
- Log level configurable in config.ini (DEBUG, INFO, WARNING, ERROR)

## Troubleshooting

### Terminal not detected
- Check USB connection
- Verify TC-200.dll is in the correct location
- Check Windows Device Manager for USB devices

### Connection to server failed
- Verify network connectivity
- Check server URL in config.ini
- Ensure firewall allows outbound HTTPS connections

### Heartbeat not sending
- Check agent logs for errors
- Verify API token is valid
- Ensure server is accessible

## Development

### Testing without hardware:
The agent automatically enters mock mode if TC-200.dll is not available. This allows testing the full agent workflow without physical terminals.

### Adding new commands:
1. Add command type to `process_commands()` in main.py
2. Implement command handler method
3. Update server API to send new command type

## License

Proprietary - TechCore Solutions
