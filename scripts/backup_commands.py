#!/usr/bin/env python3
"""
Backup Commands - Backup system test script
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.backup_manager import backup_manager

def main():
    """Test backup commands"""
    
    print("🔄 Testing Backup System...")
    print("=" * 50)
    
    # 1. Backup statistics
    print("\n📊 Backup Statistics:")
    stats = backup_manager.get_backup_stats()
    print(f"   Total backups: {stats.get('total_backups', 0)}")
    print(f"   Total size: {stats.get('total_size_mb', 0)} MB")
    print(f"   Backup directory: {stats.get('backup_dir', 'N/A')}")
    
    # 2. List existing backups
    print("\n📋 Existing Backups:")
    backups = backup_manager.list_backups()
    
    if not backups:
        print("   No backups yet")
    else:
        for backup in backups:
            print(f"   📦 {backup['filename']}")
            print(f"      Size: {backup['size_mb']} MB")
            print(f"      Type: {backup['backup_type']}")
            print(f"      Date: {backup['created_at']}")
            print(f"      Database: {backup['database_size_mb']} MB")
            print(f"      Logs: {backup['logs_size_mb']} MB")
            print()
    
    # 3. Create manual backup
    print("\n🔄 Creating Manual Backup...")
    result = backup_manager.create_backup(
        backup_type="manual",
        description="Test backup - Manually created"
    )
    
    if result["success"]:
        print(f"   ✅ Backup created: {result['backup_name']}")
        print(f"   📁 Path: {result['backup_path']}")
    else:
        print(f"   ❌ Backup error: {result['error']}")
    
    # 4. Updated statistics
    print("\n📊 Updated Statistics:")
    updated_stats = backup_manager.get_backup_stats()
    print(f"   Total backups: {updated_stats.get('total_backups', 0)}")
    print(f"   Total size: {updated_stats.get('total_size_mb', 0)} MB")
    
    print("\n✅ Backup system test completed!")

if __name__ == "__main__":
    main() 