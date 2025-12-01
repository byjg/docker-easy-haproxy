---
sidebar_position: 6
---

# Cleanup Plugin

**Type:** Global Plugin
**Runs:** Once per discovery cycle

## Overview

The Cleanup plugin performs cleanup tasks during each discovery cycle, such as removing old temporary files.

## Why Use It

Prevents disk space issues by automatically cleaning up temporary files created by EasyHAProxy.

## Configuration Options

| Option               | Description                                  | Default |
|----------------------|----------------------------------------------|---------|
| `enabled`            | Enable/disable plugin                        | `true`  |
| `max_idle_time`      | Maximum age in seconds before deleting files | `300`   |
| `cleanup_temp_files` | Enable temp file cleanup                     | `true`  |

## Configuration Examples

### Static YAML Configuration

```yaml
# /etc/haproxy/static/config.yaml
plugins:
  enabled: [cleanup]
  config:
    cleanup:
      max_idle_time: 600
      cleanup_temp_files: true
```

### Environment Variables

```bash
EASYHAPROXY_PLUGINS_ENABLED=cleanup
EASYHAPROXY_PLUGIN_CLEANUP_MAX_IDLE_TIME=600
```

### Custom Idle Time (1 hour)

```yaml
# /etc/haproxy/static/config.yaml
plugins:
  enabled: [cleanup]
  config:
    cleanup:
      enabled: true
      max_idle_time: 3600  # 1 hour
```

## How It Works

The cleanup plugin:
- Runs once during each discovery cycle
- Scans temporary directories for old files
- Removes files older than `max_idle_time` seconds
- Helps maintain disk space efficiency

## Important Notes

- This is a **global plugin** - it runs once per discovery cycle, not per domain
- Does not generate HAProxy configuration
- Performs maintenance operations in the background
- Safe to enable in production environments

## Related Documentation

- [Plugin System Overview](../plugins.md)
- [Environment Variables Reference](../environment-variable.md)
- [Static Configuration Reference](../static.md)
