# DisPinMap Bot User Guide

Welcome to the DisPinMap Bot! This guide explains how to use the bot to monitor
pinball machine locations from [Pinball Map](https://pinballmap.com) and receive
updates directly in your Discord channel.

## Getting Started

To begin, add a monitoring target to your channel. The simplest way is to add a
location by its name.

**Example:**

```
!add location "Ground Kontrol Classic Arcade"
```

The bot will find the location and start monitoring it for changes. After adding
the target, the bot will immediately display the 5 most recent submissions for
that location to confirm it's working. By default, it will check for new
submissions every 60 minutes and notify you about new machine additions or
removals.

---

## Command Reference

All commands are prefixed with `!`.

#### `!help [command_name]`

Shows a list of all available commands or provides detailed help for a specific
command.

- **To see all commands**: `!help`
- **To see help for a specific command**: `!help add`

#### `!add`

Adds a new target to monitor. This command has three variations:

1.  **`!add location <name_or_id>`**: Monitor a specific location by its name or
    its Pinball Map ID.
    - **By Name**: `!add location "My Favorite Arcade"`
    - **By ID**: `!add location 123`

2.  **`!add city <name> [radius]`**: A convenient alias for `!add coordinates`. It geocodes the city name to get coordinates and then monitors that geographic area.
    - **Without Radius**: `!add city "Portland, OR"` (uses a default radius of
      25 miles)
    - **With Radius**: `!add city "Seattle, WA" 15`

3.  **`!add coordinates <latitude> <longitude> [radius]`**: Monitor a specific
    geographic point with a radius in miles.
    - **Without Radius**: `!add coordinates 45.5231 -122.6765` (uses a default
      radius of 25 miles)
    - **With Radius**: `!add coordinates 47.6062 -122.3321 5`

**Special Behavior for Geographic Targets:**

When adding coordinates or city targets, if you specify the same coordinates
that are already being monitored but with a different radius, the bot will
update the existing target's radius instead of creating a duplicate. You'll see
a message like:

```text
✅ Updated radius to 30 miles for existing coordinates: Downtown Austin
```

This prevents duplicate monitoring of the same geographic area and allows you to
easily adjust your monitoring radius.

#### `!list` (or `!ls`, `!status`)

Displays a detailed table of all active monitoring targets in the current
channel. The table includes each target's index, poll rate, notification type,
and the last time it was checked. The index numbers are used for commands like
`!rm`.

**Example:**

```
!list
```

_Output:_

```
Index | Target                               | Poll (min) | Notifications | Last Checked
-|-
1     | Location: Funland                    | 60         | machines      | 5m ago
2     | Coords: 40.71, -74.00                | 30         | all           | 2h ago
3     | City: Austin, TX                     | 60         | all           | Never
```

#### `!check`

Manually triggers an immediate check for new submissions across all active
targets in the channel. If no new submissions are found, it will show the most
recent previously seen submissions.

**Example:**

```
!check
```

#### `!monitor_health`

Displays health status of the monitoring service, including current status,
performance metrics, and any issues with the background monitoring system. This
is useful for troubleshooting or checking if the bot is working correctly.

**Example:**

```
!monitor_health
```

This command shows system status information to help diagnose any monitoring
issues.

#### `!notifications <type> [target_index]`

Sets the type of notifications you want to receive. The available types are:

- `machines`: Only notifies about machine additions or removals.
- `comments`: Only notifies about new comments or condition reports on existing
  machines.
- `all`: Notifies for all submission types.

- **Set for the whole channel**: `!notifications all`
- **Set for a specific target**: `!notifications comments 2` (Target #2 will
  only send comment notifications.)

#### `!poll_rate <minutes> [target_index]`

Sets how frequently (in minutes) the bot checks for updates.

- **Set for the whole channel**: `!poll_rate 30` (All targets will be checked
  every 30 minutes, unless they have a custom poll rate.)
- **Set for a specific target**: `!poll_rate 10 1` (Target #1 will be checked
  every 10 minutes, ignoring the channel default.)

#### `!rm <index>` (or `!remove`)

Removes a monitoring target. The `index` corresponds to the number shown in the
`!list` command.

**Example:**

```
!rm 2
```

#### `!export`

Generates a copy-pasteable list of commands that can be used to replicate the
channel's entire monitoring configuration in another channel or server.

**Example:**

```
!export
```

_Output:_

```
Here is the configuration for this channel:

!poll_rate 30
!notifications all

!add location "Ground Kontrol Classic Arcade"
!poll_rate 15 1
!notifications machines 1

!add city "Portland, OR" 10
```

---

## How Configuration Works

### Channel Defaults vs. Per-Target Settings

- When you use `!poll_rate` or `!notifications` without specifying a
  `target_index`, you are setting the **default** for the entire channel. All
  existing and future targets will use this setting.
- When you specify a `target_index`, you are creating a **custom override** for
  that specific target only. It will ignore the channel's default setting.

### Example Scenario

1.  You set a channel's poll rate: `!poll_rate 60`.
2.  You add two targets: `!add location "Arcade A"` and
    `!add location "Arcade B"`. Both will be polled every 60 minutes.
3.  You decide you want faster updates for "Arcade A": `!poll_rate 10 1`.
4.  Now, "Arcade A" is polled every 10 minutes, while "Arcade B" continues to be
    polled every 60 minutes.
5.  If you change the channel default again (`!poll_rate 45`), "Arcade B" will
    be updated to 45 minutes, but "Arcade A" will remain at 10 minutes because
    it has a custom setting.
