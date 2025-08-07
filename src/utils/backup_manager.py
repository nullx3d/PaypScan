#!/usr/bin/env python3
"""
Backup Manager - Database and log file backup system
"""

import shutil
import sqlite3
import zipfile
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging
from src.utils.log_manager import log_manager

class BackupManager:
    """Database and log files backup manager"""
    
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Database path
        self.db_path = Path("data/database/pipeline_security.db")
        
        # Logs path
        self.logs_path = Path("logs")
        
        # Backup retention (last 5 backups)
        self.max_backups = 5
        
        # Backup format
        self.backup_format = "backup_{timestamp}_{type}.zip"
        
        print("✅ Backup Manager started")
    
    def create_backup(self, backup_type: str = "manual", description: str = "") -> Dict:
        """Create new backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = self.backup_format.format(
                timestamp=timestamp,
                type=backup_type
            )
            backup_path = self.backup_dir / backup_name
            
            # Backup metadata
            metadata = {
                "backup_type": backup_type,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "database_size": 0,
                "logs_size": 0,
                "total_size": 0
            }
            
            # Create zip file
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                
                # Database backup
                if self.db_path.exists():
                    db_backup_name = f"database/pipeline_security_{timestamp}.db"
                    zipf.write(self.db_path, db_backup_name)
                    metadata["database_size"] = self.db_path.stat().st_size
                
                # Logs backup
                if self.logs_path.exists():
                    for log_file in self.logs_path.glob("*.log"):
                        log_backup_name = f"logs/{log_file.name}"
                        zipf.write(log_file, log_backup_name)
                        metadata["logs_size"] += log_file.stat().st_size
                
                # Add metadata file
                metadata["total_size"] = metadata["database_size"] + metadata["logs_size"]
                zipf.writestr("backup_metadata.json", json.dumps(metadata, indent=2))
            
            # Cleanup old backups
            self._cleanup_old_backups()
            
            # Log
            log_manager.log_audit(
                "Backup created",
                backup_name=backup_name,
                backup_type=backup_type,
                description=description,
                total_size_mb=round(metadata["total_size"] / (1024*1024), 2)
            )
            
                    print(f"✅ Backup created: {backup_name}")
        print(f"   📊 Size: {round(metadata['total_size'] / (1024*1024), 2)} MB")
        print(f"   📁 Database: {round(metadata['database_size'] / (1024*1024), 2)} MB")
        print(f"   📄 Logs: {round(metadata['logs_size'] / (1024*1024), 2)} MB")
            
            return {
                "success": True,
                "backup_name": backup_name,
                "backup_path": str(backup_path),
                "metadata": metadata
            }
            
        except Exception as e:
            error_msg = f"Backup creation error: {e}"
            log_manager.log_error(error_msg, backup_type=backup_type)
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _cleanup_old_backups(self):
        """Clean old backups"""
        try:
            # List backup files
            backup_files = list(self.backup_dir.glob("backup_*.zip"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep only last max_backups
            if len(backup_files) > self.max_backups:
                files_to_delete = backup_files[self.max_backups:]
                
                for backup_file in files_to_delete:
                    backup_file.unlink()
                    log_manager.log_audit(
                        "Old backup deleted",
                        backup_name=backup_file.name
                    )
                
                print(f"🗑️ {len(files_to_delete)} old backups deleted")
                
        except Exception as e:
            log_manager.log_error("Backup cleanup error", error=str(e))
    
    def list_backups(self) -> List[Dict]:
        """List existing backups"""
        backups = []
        
        try:
            for backup_file in self.backup_dir.glob("backup_*.zip"):
                try:
                    # Read metadata
                    with zipfile.ZipFile(backup_file, 'r') as zipf:
                        if "backup_metadata.json" in zipf.namelist():
                            metadata_content = zipf.read("backup_metadata.json")
                            metadata = json.loads(metadata_content)
                        else:
                            # Simple metadata for old backups
                            metadata = {
                                "backup_type": "unknown",
                                "created_at": datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat(),
                                "total_size": backup_file.stat().st_size
                            }
                    
                    backups.append({
                        "filename": backup_file.name,
                        "size_mb": round(backup_file.stat().st_size / (1024*1024), 2),
                        "created_at": metadata.get("created_at", ""),
                        "backup_type": metadata.get("backup_type", "unknown"),
                        "description": metadata.get("description", ""),
                        "database_size_mb": round(metadata.get("database_size", 0) / (1024*1024), 2),
                        "logs_size_mb": round(metadata.get("logs_size", 0) / (1024*1024), 2)
                    })
                    
                except Exception as e:
                    print(f"⚠️ Backup metadata read error: {backup_file.name} - {e}")
            
            # Sort by date
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            
        except Exception as e:
            log_manager.log_error("Backup list read error", error=str(e))
        
        return backups
    
    def restore_backup(self, backup_name: str, restore_path: Optional[Path] = None) -> Dict:
        """Restore backup"""
        try:
            backup_file = self.backup_dir / backup_name
            
            if not backup_file.exists():
                return {
                    "success": False,
                    "error": f"Backup file not found: {backup_name}"
                }
            
            # Restore directory
            if restore_path is None:
                restore_path = Path("restore") / datetime.now().strftime("%Y%m%d_%H%M%S")
            
            restore_path.mkdir(parents=True, exist_ok=True)
            
            # Extract backup
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                zipf.extractall(restore_path)
            
            # Read metadata
            metadata_file = restore_path / "backup_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {"backup_type": "unknown"}
            
            log_manager.log_audit(
                "Backup restored",
                backup_name=backup_name,
                restore_path=str(restore_path),
                backup_type=metadata.get("backup_type", "unknown")
            )
            
                    print(f"✅ Backup restored: {backup_name}")
        print(f"   📁 Restore directory: {restore_path}")
            
            return {
                "success": True,
                "restore_path": str(restore_path),
                "metadata": metadata
            }
            
        except Exception as e:
            error_msg = f"Backup restore error: {e}"
            log_manager.log_error(error_msg, backup_name=backup_name)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_backup_stats(self) -> Dict:
        """Return backup statistics"""
        try:
            backups = self.list_backups()
            
            total_backups = len(backups)
            total_size_mb = sum(backup["size_mb"] for backup in backups)
            
            # Count by backup type
            backup_types = {}
            for backup in backups:
                backup_type = backup["backup_type"]
                backup_types[backup_type] = backup_types.get(backup_type, 0) + 1
            
            return {
                "total_backups": total_backups,
                "total_size_mb": round(total_size_mb, 2),
                "backup_types": backup_types,
                "max_backups": self.max_backups,
                "backup_dir": str(self.backup_dir)
            }
            
        except Exception as e:
            log_manager.log_error("Backup statistics error", error=str(e))
            return {"error": str(e)}

# Global backup manager instance
backup_manager = BackupManager() 