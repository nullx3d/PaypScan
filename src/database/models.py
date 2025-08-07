"""
Database models for pipeline security analysis
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

Base = declarative_base()

class WebhookEvent(Base):
    """Stores webhook events"""
    __tablename__ = 'webhook_events'
    
    id = Column(Integer, primary_key=True)
    event_type = Column(String(50), nullable=False)
    build_id = Column(Integer, nullable=False)
    build_number = Column(String(50), nullable=False)
    definition_id = Column(Integer, nullable=False)
    definition_name = Column(String(200), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(Text)  # JSON string
    processed = Column(Boolean, default=False)
    
    # Relationships
    security_findings = relationship("SecurityFinding", back_populates="webhook_event")
    pipeline_analysis = relationship("PipelineAnalysis", back_populates="webhook_event", uselist=False)
    
    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, build_number='{self.build_number}', event_type='{self.event_type}')>"

class SecurityFinding(Base):
    """Stores security findings"""
    __tablename__ = 'security_findings'
    
    id = Column(Integer, primary_key=True)
    webhook_event_id = Column(Integer, ForeignKey('webhook_events.id'), nullable=False)
    pattern_name = Column(String(100), nullable=False)
    pattern_count = Column(Integer, default=0)
    risk_score = Column(Float, default=0.0)
    examples = Column(Text)  # JSON string - first 3 examples
    timestamp = Column(DateTime, default=datetime.utcnow)
    severity = Column(String(20), default='MEDIUM')  # LOW, MEDIUM, HIGH, CRITICAL
    
    # Relationships
    webhook_event = relationship("WebhookEvent", back_populates="security_findings")
    
    def __repr__(self):
        return f"<SecurityFinding(id={self.id}, pattern='{self.pattern_name}', count={self.pattern_count}, severity='{self.severity}')>"

class PipelineAnalysis(Base):
    """Stores pipeline analysis results"""
    __tablename__ = 'pipeline_analysis'
    
    id = Column(Integer, primary_key=True)
    webhook_event_id = Column(Integer, ForeignKey('webhook_events.id'), nullable=False)
    yaml_content = Column(Text)
    yaml_filename = Column(String(200))
    total_patterns_found = Column(Integer, default=0)
    total_risk_score = Column(Float, default=0.0)
    analysis_status = Column(String(20), default='PENDING')  # PENDING, SUCCESS, FAILED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    webhook_event = relationship("WebhookEvent", back_populates="pipeline_analysis")
    
    def __repr__(self):
        return f"<PipelineAnalysis(id={self.id}, status='{self.analysis_status}', patterns={self.total_patterns_found})>"

class PatternStatistic(Base):
    """Stores pattern statistics"""
    __tablename__ = 'pattern_statistics'
    
    id = Column(Integer, primary_key=True)
    pattern_name = Column(String(100), unique=True, nullable=False)
    total_occurrences = Column(Integer, default=0)
    last_seen = Column(DateTime)
    risk_level = Column(String(20), default='MEDIUM')
    description = Column(Text)
    
    def __repr__(self):
        return f"<PatternStatistic(pattern='{self.pattern_name}', occurrences={self.total_occurrences}, risk='{self.risk_level}')>" 