---
sidebar_position: 21
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
# /etc/easyhaproxy/static/config.yaml
plugins:
  enabled: [cleanup]
  config:
    cleanup:
      max_idle_time: 600
      cleanup_temp_files: true
```

### Environment Variables

Configure the Cleanup plugin globally:

| Environment Variable                            | Config Key           | Type     | Default | Description                                  |
|-------------------------------------------------|----------------------|----------|---------|----------------------------------------------|
| `EASYHAPROXY_PLUGINS_ENABLED`                   | -                    | string   | -       | Enable cleanup plugin (value: `cleanup`)     |
| `EASYHAPROXY_PLUGIN_CLEANUP_ENABLED`            | `enabled`            | boolean  | `true`  | Enable/disable plugin                        |
| `EASYHAPROXY_PLUGIN_CLEANUP_MAX_IDLE_TIME`      | `max_idle_time`      | integer  | `300`   | Maximum age in seconds before deleting files |
| `EASYHAPROXY_PLUGIN_CLEANUP_CLEANUP_TEMP_FILES` | `cleanup_temp_files` | boolean  | `true`  | Enable temp file cleanup                     |

**Note:** This is a global plugin - configuration applies to the entire system.

### Custom Idle Time (1 hour)

```yaml
# /etc/easyhaproxy/static/config.yaml
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
