#!/usr/bin/env python3
"""
Azure DevOps Pipeline Security Analysis Tool

This tool analyzes Azure DevOps pipelines for security vulnerabilities
by examining YAML definitions, build logs, and execution traces.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.utils.azure_client import AzureDevOpsClient
from src.utils.security_analyzer import SecurityAnalyzer

# Load .env file
load_dotenv()

# Get configuration from environment variables
DEFINITION_ID = int(os.getenv('AZURE_DEFINITION_ID', '10'))
LOG_LEVEL = os.getenv('AZURE_LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description='Azure DevOps Pipeline Security Analysis Tool'
    )
    parser.add_argument(
        '--definition-id', 
        type=int, 
        default=DEFINITION_ID,
        help='Pipeline definition ID'
    )
    parser.add_argument(
        '--analyze-yaml', 
        action='store_true',
        help='Analyze pipeline YAML definition'
    )
    parser.add_argument(
        '--analyze-build', 
        action='store_true',
        help='Analyze latest build'
    )
    parser.add_argument(
        '--analyze-logs', 
        action='store_true',
        help='Analyze build logs for security issues'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize Azure client
    client = AzureDevOpsClient()
    
    print("🔍 Azure DevOps Pipeline Security Analysis")
    print("=" * 50)
    
    if args.analyze_yaml:
        analyze_pipeline_yaml(client, args.definition_id)
    
    if args.analyze_build:
        analyze_latest_build(client, args.definition_id)
    
    if args.analyze_logs:
        analyze_build_logs(client, args.definition_id)
    
    if not any([args.analyze_yaml, args.analyze_build, args.analyze_logs]):
        # Default: run all analyses
        analyze_pipeline_yaml(client, args.definition_id)
        analyze_latest_build(client, args.definition_id)
        analyze_build_logs(client, args.definition_id)

def analyze_pipeline_yaml(client: AzureDevOpsClient, definition_id: int):
    """Analyze pipeline YAML definition"""
    print(f"\n📋 Pipeline YAML Analizi (Definition ID: {definition_id})")
    print("-" * 40)
    
    pipeline_def = client.get_pipeline_definition(definition_id)
    if not pipeline_def:
        print("❌ Pipeline tanımı alınamadı")
        return
    
    print(f"✅ Pipeline: {pipeline_def.get('name', 'Bilinmiyor')}")
    print(f"🆔 ID: {pipeline_def.get('id')}")
    print(f"📝 Path: {pipeline_def.get('path', 'Bilinmiyor')}")
    
    # Analyze process for security issues
    process = pipeline_def.get('process', {})
    if 'phases' in process:
        phases = process['phases']
        print(f"\n📊 Pipeline Adımları ({len(phases)} adet):")
        
        security_issues = []
        for i, phase in enumerate(phases, 1):
            print(f"\n  {i}. Phase: {phase.get('name', 'Bilinmiyor')}")
            
            if 'steps' in phase:
                steps = phase['steps']
                for j, step in enumerate(steps, 1):
                    display_name = step.get('displayName', 'Bilinmiyor')
                    inputs = step.get('inputs', {})
                    
                    # Check for dangerous inputs
                    for key, value in inputs.items():
                        if isinstance(value, str):
                            analysis = SecurityAnalyzer.analyze_script_content(value)
                            if analysis['has_dangerous_patterns']:
                                security_issues.append({
                                    'step': display_name,
                                    'input': key,
                                    'value': value,
                                    'analysis': analysis
                                })
        
        if security_issues:
            print(f"\n⚠️  Güvenlik Sorunları ({len(security_issues)} adet):")
            for issue in security_issues:
                print(f"  • {issue['step']} - {issue['input']}")
                print(f"    Risk: {issue['analysis']['risk_level']}")
                print(f"    Pattern: {', '.join(issue['analysis']['dangerous_patterns_found'])}")
        else:
            print("\n✅ Güvenlik sorunu bulunamadı")

def analyze_latest_build(client: AzureDevOpsClient, definition_id: int):
    """Analyze latest build"""
    print(f"\n🔍 Son Build Analizi (Definition ID: {definition_id})")
    print("-" * 40)
    
    latest_build = client.get_latest_build(definition_id)
    if not latest_build:
        print("❌ Son build bulunamadı")
        return
    
    build_id = latest_build['id']
    build_number = latest_build.get('buildNumber', 'Bilinmiyor')
    result = latest_build.get('result', 'Bilinmiyor')
    
    print(f"📋 Build: {build_number}")
    print(f"🎯 Sonuç: {result}")
    print(f"🆔 Build ID: {build_id}")
    
    # Get timeline
    timeline = client.get_build_timeline(build_id)
    if timeline:
        records = timeline.get('records', [])
        task_steps = [r for r in records if r.get('type') == 'Task']
        
        print(f"\n📊 Çalışan Adımlar ({len(task_steps)} adet):")
        for i, step in enumerate(task_steps, 1):
            name = step.get('name', 'Bilinmiyor')
            result = step.get('result', 'Bilinmiyor')
            print(f"  {i}. {name} - {result}")

def analyze_build_logs(client: AzureDevOpsClient, definition_id: int):
    """Analyze build logs for security issues"""
    print(f"\n📜 Build Log Analizi (Definition ID: {definition_id})")
    print("-" * 40)
    
    latest_build = client.get_latest_build(definition_id)
    if not latest_build:
        print("❌ Son build bulunamadı")
        return
    
    build_id = latest_build['id']
    timeline = client.get_build_timeline(build_id)
    
    if not timeline:
        print("❌ Timeline alınamadı")
        return
    
    records = timeline.get('records', [])
    security_issues = []
    
    for record in records:
        if record.get('type') == 'Task':
            log_info = record.get('log')
            if log_info and isinstance(log_info, dict):
                log_id = log_info.get('id')
                if log_id:
                    log_content = client.get_log_content(build_id, log_id)
                    if log_content:
                        analysis = SecurityAnalyzer.analyze_log_content(log_content)
                        if analysis['script_blocks']:
                            security_issues.extend(analysis['script_blocks'])
    
    if security_issues:
        print(f"⚠️  Güvenlik Sorunları ({len(security_issues)} adet):")
        for issue in security_issues:
            print(f"  • Script Type: {issue['type']}")
            print(f"    Risk Level: {issue['analysis']['risk_level']}")
            print(f"    Patterns: {', '.join(issue['analysis']['dangerous_patterns_found'])}")
            print()
    else:
        print("✅ Log'larda güvenlik sorunu bulunamadı")

if __name__ == "__main__":
    main() 