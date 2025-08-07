# Backup System Usage Guide

## 📋 Overview

The backup system automatically backs up database and log files. It has both manual and automatic backup features.

## 🚀 Quick Start

### Manual Backup
```bash
# Test backup commands
python scripts/backup_commands.py

# Create manual backup
python -c "
from src.utils.backup_manager import backup_manager
result = backup_manager.create_backup('manual', 'Manual backup')
print(f'Backup created: {result[\"backup_name\"]}')
"
```

### Automatic Backup Scheduler
```bash
# Start scheduler (stop with Ctrl+C)
python scripts/backup_scheduler.py
```

## 📊 Backup Content

Each backup file contains:
- **Database**: `pipeline_security.db` (all webhook events, security findings, pipeline analysis)
- **Logs**: All log files (`webhook_events.log`, `security_alerts.log`, etc.)
- **Metadata**: Backup information (`backup_metadata.json`)

## ⏰ Scheduled Tasks

The scheduler automatically runs these tasks:

| Task | Time | Description |
|------|------|-------------|
| Daily Backup | Every day 02:00 | Daily data backup |
| Weekly Backup | Every Sunday 03:00 | Weekly full backup |
| Backup Cleanup | Every day 04:00 | Clean old backups |

## 📁 Backup File Structure

```
backups/
├── backup_20250807_174947_manual.zip
├── backup_20250807_180000_daily.zip
└── backup_20250807_190000_weekly.zip
```

### Backup Content:
```
backup_YYYYMMDD_HHMMSS_TYPE.zip
├── database/
│   └── pipeline_security_YYYYMMDD_HHMMSS.db
├── logs/
│   ├── webhook_events.log
│   ├── security_alerts.log
│   ├── database_operations.log
│   ├── errors.log
│   └── audit.log
└── backup_metadata.json
```

## 🔧 Management Commands

### Backup List
```python
from src.utils.backup_manager import backup_manager

# List all backups
backups = backup_manager.list_backups()
for backup in backups:
    print(f"{backup['filename']} - {backup['size_mb']} MB")
```

### Backup Statistics
```python
from src.utils.backup_manager import backup_manager

# Get statistics
stats = backup_manager.get_backup_stats()
print(f"Total backups: {stats['total_backups']}")
print(f"Total size: {stats['total_size_mb']} MB")
```

### Backup Restore
```python
from src.utils.backup_manager import backup_manager

# Restore backup
result = backup_manager.restore_backup("backup_20250807_174947_manual.zip")
if result["success"]:
    print(f"Restored: {result['restore_path']}")
```

## ⚙️ Configuration

### Backup Retention
By default, the last 5 backups are kept. To change:

```python
# src/utils/backup_manager.py
class BackupManager:
    def __init__(self):
        self.max_backups = 10  # Keep 10 backups
```

### Backup Directory
Backups are stored in the `backups/` directory. To change:

```python
# src/utils/backup_manager.py
class BackupManager:
    def __init__(self):
        self.backup_dir = Path("custom_backup_path")
```

## 🔍 Monitoring

### Log Files
Backup operations are tracked in these log files:
- `logs/audit.log` - Backup creation/restore
- `logs/errors.log` - Backup errors

### Disk Usage
```bash
# Check backup directory size
du -sh backups/

# List backup files
ls -lah backups/
```

## 🛠️ Troubleshooting

### Backup Creation Error
```bash
# Check database file existence
ls -la data/database/pipeline_security.db

# Check log directory existence
ls -la logs/
```

### Scheduler Not Working
```bash
# Test scheduler manually
python scripts/backup_scheduler.py

# Add as cron job (Linux/Mac)
crontab -e
# 0 2 * * * cd /path/to/project && python scripts/backup_scheduler.py
```

### Low Disk Space
```bash
# Manually delete old backups
rm backups/backup_OLD_*.zip

# Reduce backup retention
# src/utils/backup_manager.py -> max_backups = 3
```

## 📈 Performance

### Backup Sizes (Estimated)
- **Database**: ~300KB (current data)
- **Logs**: ~5KB (current logs)
- **Total**: ~0.3MB per backup

### Annual Estimate
- **Daily backup**: 365 × 0.3MB = 109.5MB/year
- **Weekly backup**: 52 × 0.3MB = 15.6MB/year
- **Total**: ~125MB/year

## 🔐 Security

### Backup Security
- Backup files are compressed (ZIP)
- Full traceability with metadata
- Automatic cleanup for disk control

### Restore Security
- Backups are restored to separate directory
- Does not affect existing data
- Validation with metadata

## 📞 Support

For backup system issues:
1. Check log files
2. Check disk space
3. Check database connection
4. Examine backup metadata 