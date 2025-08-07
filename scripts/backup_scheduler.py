#!/usr/bin/env python3
"""
Backup Scheduler - Automatic backup system
"""

import time
import schedule
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.backup_manager import backup_manager
from src.utils.log_manager import log_manager

def daily_backup():
    """Creates daily backup"""
    try:
        print(f"\n🔄 Starting daily backup... ({datetime.now()})")
        
        result = backup_manager.create_backup(
            backup_type="daily",
            description=f"Daily automatic backup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        if result["success"]:
            print(f"✅ Daily backup completed: {result['backup_name']}")
            log_manager.log_audit(
                "Daily backup completed",
                backup_name=result['backup_name'],
                backup_type="daily"
            )
        else:
            print(f"❌ Daily backup error: {result['error']}")
            log_manager.log_error(
                "Daily backup error",
                error=result['error']
            )
            
    except Exception as e:
        error_msg = f"Daily backup exception: {e}"
        print(f"❌ {error_msg}")
        log_manager.log_error(error_msg)

def weekly_backup():
    """Creates weekly backup"""
    try:
        print(f"\n🔄 Starting weekly backup... ({datetime.now()})")
        
        result = backup_manager.create_backup(
            backup_type="weekly",
            description=f"Weekly automatic backup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        if result["success"]:
            print(f"✅ Weekly backup completed: {result['backup_name']}")
            log_manager.log_audit(
                "Weekly backup completed",
                backup_name=result['backup_name'],
                backup_type="weekly"
            )
        else:
            print(f"❌ Weekly backup error: {result['error']}")
            log_manager.log_error(
                "Weekly backup error",
                error=result['error']
            )
            
    except Exception as e:
        error_msg = f"Weekly backup exception: {e}"
        print(f"❌ {error_msg}")
        log_manager.log_error(error_msg)

def backup_cleanup():
    """Backup cleanup operation"""
    try:
        print(f"\n🗑️ Starting backup cleanup... ({datetime.now()})")
        
        # Log backup statistics
        stats = backup_manager.get_backup_stats()
        log_manager.log_audit(
            "Backup cleanup completed",
            total_backups=stats.get('total_backups', 0),
            total_size_mb=stats.get('total_size_mb', 0)
        )
        
        print(f"✅ Backup cleanup completed")
        
    except Exception as e:
        error_msg = f"Backup cleanup exception: {e}"
        print(f"❌ {error_msg}")
        log_manager.log_error(error_msg)

def setup_scheduler():
    """Setup scheduler"""
    print("🔄 Setting up Backup Scheduler...")
    
    # Daily backup - every day at 02:00
    schedule.every().day.at("02:00").do(daily_backup)
    print("   📅 Daily backup: Every day 02:00")
    
    # Weekly backup - every Sunday at 03:00
    schedule.every().sunday.at("03:00").do(weekly_backup)
    print("   📅 Weekly backup: Every Sunday 03:00")
    
    # Backup cleanup - every day at 04:00
    schedule.every().day.at("04:00").do(backup_cleanup)
    print("   📅 Backup cleanup: Every day 04:00")
    
    print("✅ Scheduler configured!")

def run_scheduler():
    """Run scheduler"""
    print("🚀 Backup Scheduler started!")
    print("   ⏰ Scheduled tasks:")
    print("      - Daily backup: 02:00")
    print("      - Weekly backup: Sunday 03:00")
    print("      - Backup cleanup: 04:00")
    print("   🔄 Scheduler running... (Press Ctrl+C to stop)")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print("\n⏹️ Scheduler stopped!")

def main():
    """Main function"""
    print("🔄 Starting Backup Scheduler...")
    print("=" * 50)
    
    # Setup scheduler
    setup_scheduler()
    
    # Create manual test backup
    print("\n🧪 Creating test backup...")
    test_result = backup_manager.create_backup(
        backup_type="test",
        description="Scheduler test backup"
    )
    
    if test_result["success"]:
        print(f"✅ Test backup created: {test_result['backup_name']}")
    else:
        print(f"❌ Test backup error: {test_result['error']}")
    
    # Run scheduler
    run_scheduler()

if __name__ == "__main__":
    main() 