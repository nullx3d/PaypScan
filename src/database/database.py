"""
Database manager for pipeline security analysis
"""

import logging
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from .config import DATABASE_URL, DATABASE_CONFIG
from .models import Base, WebhookEvent, SecurityFinding, PipelineAnalysis, PatternStatistic

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database işlemlerini yöneten sınıf"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Database'i başlatır ve tabloları oluşturur"""
        try:
            # Engine oluştur
            self.engine = create_engine(DATABASE_URL, **DATABASE_CONFIG)
            
            # Session factory oluştur
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Tabloları oluştur
            Base.metadata.create_all(bind=self.engine)
            
            logger.info("✅ Database başarıyla başlatıldı")
            
        except Exception as e:
            logger.error(f"❌ Database başlatma hatası: {e}")
            raise
    
    def get_session(self):
        """Database session'ı döndürür"""
        return self.SessionLocal()
    
    def save_webhook_event(self, event_data):
        """Webhook event'ini kaydeder"""
        try:
            session = self.get_session()
            
            # Event'i oluştur
            webhook_event = WebhookEvent(
                event_type=event_data['event_type'],
                build_id=event_data['build_id'],
                build_number=event_data['build_number'],
                definition_id=event_data['definition_id'],
                definition_name=event_data['definition_name'],
                raw_data=json.dumps(event_data.get('raw_data', {})),
                processed=False
            )
            
            session.add(webhook_event)
            session.commit()
            
            logger.info(f"✅ Webhook event kaydedildi: {webhook_event.build_number}")
            return webhook_event.id
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Webhook event kaydetme hatası: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def save_security_findings(self, webhook_event_id, findings):
        """Güvenlik bulgularını kaydeder"""
        try:
            session = self.get_session()
            
            for finding in findings:
                security_finding = SecurityFinding(
                    webhook_event_id=webhook_event_id,
                    pattern_name=finding['pattern'],
                    pattern_count=finding['count'],
                    risk_score=self._calculate_risk_score(finding['pattern']),
                    examples=json.dumps(finding['matches'][:3]),  # İlk 3 örnek
                    severity=self._determine_severity(finding['pattern'])
                )
                
                session.add(security_finding)
            
            session.commit()
            logger.info(f"✅ {len(findings)} güvenlik bulgusu kaydedildi")
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Güvenlik bulguları kaydetme hatası: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def save_pipeline_analysis(self, webhook_event_id, yaml_content, yaml_filename, total_patterns, total_risk_score):
        """Pipeline analiz sonuçlarını kaydeder"""
        try:
            session = self.get_session()
            
            pipeline_analysis = PipelineAnalysis(
                webhook_event_id=webhook_event_id,
                yaml_content=yaml_content,
                yaml_filename=yaml_filename,
                total_patterns_found=total_patterns,
                total_risk_score=total_risk_score,
                analysis_status='SUCCESS'
            )
            
            session.add(pipeline_analysis)
            session.commit()
            
            logger.info(f"✅ Pipeline analizi kaydedildi")
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Pipeline analizi kaydetme hatası: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def update_webhook_event_processed(self, webhook_event_id):
        """Webhook event'i işlenmiş olarak işaretler"""
        try:
            session = self.get_session()
            
            event = session.query(WebhookEvent).filter(WebhookEvent.id == webhook_event_id).first()
            if event:
                event.processed = True
                session.commit()
                logger.info(f"✅ Webhook event işlenmiş olarak işaretlendi: {event.build_number}")
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Webhook event güncelleme hatası: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_recent_events(self, limit=10):
        """Son event'leri getirir"""
        try:
            session = self.get_session()
            
            events = session.query(WebhookEvent).order_by(WebhookEvent.timestamp.desc()).limit(limit).all()
            return events
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Event'ler getirme hatası: {e}")
            return []
        finally:
            session.close()
    
    def get_security_findings_by_event(self, webhook_event_id):
        """Event'e ait güvenlik bulgularını getirir"""
        try:
            session = self.get_session()
            
            findings = session.query(SecurityFinding).filter(
                SecurityFinding.webhook_event_id == webhook_event_id
            ).all()
            
            return findings
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Güvenlik bulguları getirme hatası: {e}")
            return []
        finally:
            session.close()
    
    def get_pattern_statistics(self):
        """Pattern istatistiklerini getirir"""
        try:
            session = self.get_session()
            
            # Pattern'leri grupla ve say
            result = session.execute(text("""
                SELECT 
                    pattern_name,
                    COUNT(*) as total_occurrences,
                    MAX(timestamp) as last_seen,
                    AVG(risk_score) as avg_risk_score
                FROM security_findings 
                GROUP BY pattern_name 
                ORDER BY total_occurrences DESC
            """))
            
            return [dict(row) for row in result]
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Pattern istatistikleri getirme hatası: {e}")
            return []
        finally:
            session.close()
    
    def _calculate_risk_score(self, pattern_name):
        """Pattern için risk skoru hesaplar"""
        risk_scores = {
            'eval': 10.0,
            'exec': 10.0,
            'base64_execute': 9.0,
            'powershell_invoke': 8.0,
            'subprocess_call': 7.0,
            'curl_dangerous': 6.0,
            'file_write': 5.0,
            'base64_encoded': 3.0
        }
        
        return risk_scores.get(pattern_name, 5.0)
    
    def _determine_severity(self, pattern_name):
        """Pattern için severity belirler"""
        high_risk_patterns = ['eval', 'exec', 'base64_execute', 'powershell_invoke']
        medium_risk_patterns = ['subprocess_call', 'curl_dangerous', 'file_write']
        
        if pattern_name in high_risk_patterns:
            return 'CRITICAL'
        elif pattern_name in medium_risk_patterns:
            return 'HIGH'
        else:
            return 'MEDIUM'
    
    def event_exists(self, build_id, build_number):
        """Event'in daha önce kaydedilip kaydedilmediğini kontrol eder"""
        try:
            session = self.get_session()
            
            # Build ID ve build number ile kontrol et
            existing_event = session.query(WebhookEvent).filter(
                WebhookEvent.build_id == build_id,
                WebhookEvent.build_number == build_number
            ).first()
            
            return existing_event is not None
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Event kontrol hatası: {e}")
            return False
        finally:
            session.close() 