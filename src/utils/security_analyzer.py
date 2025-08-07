import re
import json
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class SecurityAnalyzer:
    """Security analysis utilities for pipeline content"""
    
    @staticmethod
    def analyze_script_content(content: str, script_type: str = None) -> Dict[str, Any]:
        """Analyze script content for security risks"""
        results = {
            'has_dangerous_patterns': False,
            'dangerous_patterns_found': [],
            'risk_level': 'LOW',
            'recommendations': []
        }
        
        if not content:
            return results
        
        # Use the same pattern analysis as analyze_yaml_content
        findings = SecurityAnalyzer.analyze_yaml_content(content)
        
        if findings:
            results['has_dangerous_patterns'] = True
            results['dangerous_patterns_found'] = [f['pattern'] for f in findings]
            
            # Determine risk level based on findings
            if len(findings) > 3:
                results['risk_level'] = 'HIGH'
            elif len(findings) > 1:
                results['risk_level'] = 'MEDIUM'
            else:
                results['risk_level'] = 'LOW'
            
            # Add recommendations
            results['recommendations'].append(
                f"Found {len(findings)} dangerous pattern(s): {', '.join(results['dangerous_patterns_found'])}"
            )
        
        return results
    
    @staticmethod
    def analyze_powershell_script(content: str) -> Dict[str, Any]:
        """Analyze PowerShell script specifically"""
        results = SecurityAnalyzer.analyze_script_content(content, 'powershell')
        
        # Additional PowerShell specific checks
        additional_patterns = [
            r'powershell\s+-Command\s+["\']',
            r'powershell\s+-EncodedCommand\s+',
            r'IEX\s+[`"\'][^`"\']*[`"\']',
            r'Invoke-Expression\s+[`"\'][^`"\']*[`"\']'
        ]
        
        for pattern in additional_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                results['has_dangerous_patterns'] = True
                results['dangerous_patterns_found'].append(f"Dynamic execution: {pattern}")
        
        return results
    
    @staticmethod
    def analyze_bash_script(content: str) -> Dict[str, Any]:
        """Analyze Bash script specifically"""
        results = SecurityAnalyzer.analyze_script_content(content, 'bash')
        
        # Additional Bash specific checks
        additional_patterns = [
            r'curl\s+.*\s*\|\s*bash',
            r'wget\s+.*\s*\|\s*bash',
            r'source\s+<\([^)]+\)',
            r'eval\s+[`"\'][^`"\']*[`"\']'
        ]
        
        for pattern in additional_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                results['has_dangerous_patterns'] = True
                results['dangerous_patterns_found'].append(f"Dynamic execution: {pattern}")
        
        return results
    
    @staticmethod
    def analyze_python_script(content: str) -> Dict[str, Any]:
        """Analyze Python script specifically"""
        results = SecurityAnalyzer.analyze_script_content(content, 'python')
        
        # Additional Python specific checks
        additional_patterns = [
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__\s*\(',
            r'compile\s*\(',
            r'os\.system\s*\(',
            r'subprocess\.call\s*\('
        ]
        
        for pattern in additional_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                results['has_dangerous_patterns'] = True
                results['dangerous_patterns_found'].append(f"Dynamic execution: {pattern}")
        
        return results
    
    @staticmethod
    def get_script_type(content: str) -> str:
        """Detect script type based on content"""
        content_lower = content.lower()
        
        if 'powershell' in content_lower or 'invoke-expression' in content_lower:
            return 'powershell'
        elif 'bash' in content_lower or '#!/bin/bash' in content_lower:
            return 'bash'
        elif 'python' in content_lower or '#!/usr/bin/env python' in content_lower:
            return 'python'
        else:
            return 'unknown'
    
    @staticmethod
    def analyze_yaml_content(yaml_content: str) -> List[Dict[str, Any]]:
        """YAML içeriğini güvenlik açısından analiz eder"""
        findings = []
        
        if not yaml_content:
            return findings
        
        try:
            # Absolute path kullan - proje root'unu bul
            project_root = Path(__file__).parent.parent.parent
            blacklist_path = project_root / "config" / "patterns" / "blacklist.json"
            
            if blacklist_path.exists():
                with open(blacklist_path, 'r', encoding='utf-8') as f:
                    blacklist = json.load(f)
            else:
                logger.error(f"Blacklist file not found: {blacklist_path}")
                return findings
            
            # Read whitelist patterns
            whitelist_path = project_root / "config" / "patterns" / "whitelist.json"
            if whitelist_path.exists():
                with open(whitelist_path, 'r', encoding='utf-8') as f:
                    whitelist = json.load(f)
            else:
                logger.warning(f"Whitelist file not found: {whitelist_path}")
                whitelist = {"patterns": {}}
            
            # Check each blacklist pattern
            for pattern_name, pattern_data in blacklist['patterns'].items():
                try:
                    regex = pattern_data['regex']
                    matches = re.findall(regex, yaml_content, re.IGNORECASE)
                    
                    if matches:
                        # Whitelist check
                        is_whitelisted = False
                        for whitelist_name, whitelist_data in whitelist['patterns'].items():
                            whitelist_regex = whitelist_data['regex']
                            whitelist_matches = re.findall(whitelist_regex, yaml_content, re.IGNORECASE)
                            if whitelist_matches:
                                # If whitelist pattern matches, skip this pattern
                                is_whitelisted = True
                                logger.info(f"Pattern '{pattern_name}' blocked by whitelist '{whitelist_name}'")
                                break
                        
                        if not is_whitelisted:
                            # Determine risk score
                            risk_level = pattern_data.get('risk_level', 'medium')
                            if risk_level == 'high':
                                risk_score = 8.0
                            elif risk_level == 'medium':
                                risk_score = 5.0
                            else:
                                risk_score = 3.0
                            
                            findings.append({
                                'pattern': pattern_name,
                                'count': len(matches),
                                'matches': matches[:3],  # First 3 matches
                                'risk_score': risk_score,
                                'description': pattern_data.get('description', 'Security pattern')
                            })
                    
                except re.error as e:
                    logger.warning(f"Regex error - {pattern_name}: {e}")
                    continue
            
            # Sort by risk score
            findings.sort(key=lambda x: x['risk_score'], reverse=True)
            
            return findings
            
        except Exception as e:
            logger.error(f"Pattern analysis error: {e}")
            return findings
    
    @staticmethod
    def analyze_log_content(log_content: str) -> Dict[str, Any]:
        """Analyze log content for security issues"""
        results = {
            'script_blocks': [],
            'security_issues': [],
            'recommendations': []
        }
        
        if not log_content:
            return results
        
        # Find script blocks in logs
        script_patterns = [
            r'##\[command\].*?powershell.*?##\[section\]Finishing',
            r'##\[command\].*?bash.*?##\[section\]Finishing',
            r'##\[command\].*?python.*?##\[section\]Finishing'
        ]
        
        for pattern in script_patterns:
            matches = re.findall(pattern, log_content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                script_type = SecurityAnalyzer.get_script_type(match)
                analysis = SecurityAnalyzer.analyze_script_content(match, script_type)
                
                if analysis['has_dangerous_patterns']:
                    results['script_blocks'].append({
                        'content': match,
                        'type': script_type,
                        'analysis': analysis
                    })
        
        return results 