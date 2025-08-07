#!/usr/bin/env python3
"""
Webhook Build YAML Analyzer
Performs YAML analysis using build information from webhook
"""

import requests
from requests.auth import HTTPBasicAuth
import json
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load .env file with explicit path and override
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path, override=True)

# Load configuration from environment variables
organization = os.getenv('AZURE_ORGANIZATION', 'your-organization')
project = os.getenv('AZURE_PROJECT', 'your-project')
definition_id = int(os.getenv('AZURE_DEFINITION_ID', '10'))
build_id = int(os.getenv('AZURE_BUILD_ID', '132'))
pat = os.getenv('AZURE_PAT', '')
devops_server_url = os.getenv('AZURE_DEVOPS_SERVER_URL', 'https://dev.azure.com')

def get_pipeline_yaml(definition_id):
    """Gets pipeline YAML definition"""
    url = f'{devops_server_url}/{organization}/{project}/_apis/build/definitions/{definition_id}?api-version=6.0'
    response = requests.get(url, auth=HTTPBasicAuth('', pat))
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get pipeline definition: {response.status_code}")
        print(f"URL: {url}")
        return None

def get_build_timeline(build_id):
    """Gets build timeline"""
    url = f'{devops_server_url}/{organization}/{project}/_apis/build/builds/{build_id}/timeline?api-version=6.0'
    response = requests.get(url, auth=HTTPBasicAuth('', pat))
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get build timeline: {response.status_code}")
        return None

def analyze_webhook_build():
    """Analyzes build from webhook"""
    
    print("🔍 Webhook Build YAML Analysis")
    print("=" * 50)
    print(f"Organization: {organization}")
    print(f"Project: {project}")
    print(f"Definition ID: {definition_id}")
    print(f"Build ID: {build_id}")
    
    # Check if PAT is configured
    if not pat:
        print("❌ Error: AZURE_PAT not configured in .env file")
        print("Please add your Personal Access Token to .env file")
        return
    
    # Get pipeline definition
    print(f"\n📋 Getting Pipeline YAML Definition...")
    pipeline_def = get_pipeline_yaml(definition_id)
    
    if pipeline_def:
        print(f"✅ Pipeline definition received")
        print(f"  🏷️  Name: {pipeline_def.get('name', 'Unknown')}")
        print(f"  🆔 ID: {pipeline_def.get('id')}")
        print(f"  📝 Path: {pipeline_def.get('path', 'Unknown')}")
        
        # Get process information
        process = pipeline_def.get('process', {})
        if 'phases' in process:
            phases = process['phases']
            print(f"\n📊 Pipeline Steps ({len(phases)} items):")
            
            for i, phase in enumerate(phases, 1):
                print(f"\n  {i}. Phase: {phase.get('name', 'Unknown')}")
                
                if 'steps' in phase:
                    steps = phase['steps']
                    print(f"     📝 Steps ({len(steps)} items):")
                    
                    for j, step in enumerate(steps, 1):
                        display_name = step.get('displayName', 'Unknown')
                        task = step.get('task', {})
                        task_name = task.get('name', 'Unknown')
                        task_id = task.get('id', 'Unknown')
                        
                        print(f"       {j}. {display_name}")
                        print(f"          Task: {task_name} (ID: {task_id})")
                        
                        # Show inputs
                        inputs = step.get('inputs', {})
                        if inputs:
                            print(f"          Inputs:")
                            for key, value in inputs.items():
                                # Hide sensitive information
                                if 'token' in key.lower() or 'password' in key.lower():
                                    print(f"            {key}: [HIDDEN]")
                                else:
                                    print(f"            {key}: {value}")
        
        # Save to JSON file
        filename = f'webhook_pipeline_{definition_id}_definition.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(pipeline_def, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Pipeline definition saved to {filename}")
        
    else:
        print("❌ Failed to get pipeline definition")
    
    # Get build timeline
    print(f"\n📋 Getting Build Timeline...")
    timeline = get_build_timeline(build_id)
    
    if timeline:
        print(f"✅ Build timeline received")
        records = timeline.get('records', [])
        print(f"  📊 Total Records: {len(records)}")
        
        # Show tasks
        task_records = [r for r in records if r.get('type') == 'Task']
        print(f"  🔧 Task Count: {len(task_records)}")
        
        for i, task in enumerate(task_records, 1):
            name = task.get('name', 'Unknown')
            result = task.get('result', 'Unknown')
            print(f"    {i}. {name} - {result}")
        
        # Save to JSON file
        filename = f'webhook_build_{build_id}_timeline.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(timeline, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Build timeline saved to {filename}")
        
    else:
        print("❌ Failed to get build timeline")

if __name__ == "__main__":
    analyze_webhook_build() 