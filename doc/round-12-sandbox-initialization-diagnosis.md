# Round 12 - Sandbox Initialization Diagnosis

Time: 2026-06-17 CST

## Goal

Fix the local Codex/OpenClaw command sandbox before continuing TraceShield development.

## Symptom

Normal sandboxed commands failed before the command body ran:

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

This means bubblewrap failed while creating/configuring the sandbox, specifically while setting up the loopback interface inside a network namespace.

## Confirmed Diagnostics

System:

```text
Linux 6.17.0-35-generic Ubuntu
bubblewrap 0.9.0
```

Kernel namespace settings:

```text
kernel.unprivileged_userns_clone = 1
user.max_user_namespaces = 15144
kernel.apparmor_restrict_unprivileged_userns = 1
```

Package and helper state:

```text
uidmap: not installed
/usr/bin/newuidmap: missing
/usr/bin/newgidmap: missing
/usr/bin/bwrap: present, not setuid
```

Direct reproduction:

```bash
bwrap --unshare-net --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp true
```

Observed:

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

User namespace test:

```bash
unshare -Ur true
```

Observed:

```text
unshare: write failed /proc/self/uid_map: Operation not permitted
```

## Root Cause

The sandbox host is missing `uidmap` helpers and Ubuntu AppArmor is restricting unprivileged user namespaces. Codex/OpenClaw's managed sandbox relies on bubblewrap, so every normal sandboxed command fails before the actual command can execute.

## Required Host Fix

Run these commands in a real terminal with sudo:

```bash
sudo apt update
sudo apt install -y uidmap
sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
```

Optional persistent setting across reboot:

```bash
printf 'kernel.apparmor_restrict_unprivileged_userns=0\n' | sudo tee /etc/sysctl.d/99-codex-bwrap.conf
sudo sysctl --system
```

## Verification Commands

After applying the host fix:

```bash
bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp true
bwrap --unshare-net --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp true
unshare -Ur true
```

Expected result:

```text
all commands exit with code 0 and no output
```

Then Codex normal tool execution should work again without `sandbox_permissions: require_escalated`.

