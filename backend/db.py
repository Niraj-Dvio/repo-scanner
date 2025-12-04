"""Database models and operations for scan persistence"""
import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, JSON as SAJSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Dict, Optional

logger = logging.getLogger(__name__)

Base = declarative_base()


class ScanModel(Base):
    """Database model for scan results"""
    __tablename__ = 'scans'
    scan_id = Column(String, primary_key=True, index=True)
    repo_url = Column(String, nullable=True)
    status = Column(String, nullable=True)
    result = Column(SAJSON, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)


# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/scanner")
engine = None
SessionLocal = None


def init_db():
    """Initialize database"""
    global engine, SessionLocal
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database init failed: {e}")


def save_scan_to_db(scan_id: str, repo_url: str = None, status: str = None, result: Dict = None):
    """Save or update scan result in database"""
    if SessionLocal is None:
        return
    session = None
    try:
        session = SessionLocal()
        now = datetime.utcnow()
        obj = session.query(ScanModel).filter(ScanModel.scan_id == scan_id).one_or_none()
        if obj is None:
            obj = ScanModel(scan_id=scan_id, repo_url=repo_url, status=status, result=result, created_at=now, updated_at=now)
            session.add(obj)
        else:
            if repo_url is not None:
                obj.repo_url = repo_url
            if status is not None:
                obj.status = status
            if result is not None:
                obj.result = result
            obj.updated_at = now
        session.commit()
    except Exception as e:
        logger.error(f"Failed to save scan to DB: {e}")
    finally:
        if session:
            session.close()


def get_scan_from_db(scan_id: str) -> Optional[Dict]:
    """Retrieve scan result from database"""
    if SessionLocal is None:
        return None
    session = None
    try:
        session = SessionLocal()
        obj = session.query(ScanModel).filter(ScanModel.scan_id == scan_id).one_or_none()
        if obj:
            return {
                "scan_id": obj.scan_id,
                "repo_url": obj.repo_url,
                "status": obj.status,
                "result": obj.result,
                "created_at": obj.created_at.isoformat() if obj.created_at else None,
                "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
            }
    except Exception as e:
        logger.error(f"Failed to read scan from DB: {e}")
    finally:
        if session:
            session.close()
    return None


def delete_scan_from_db(scan_id: str):
    """Delete scan from database"""
    if SessionLocal is None:
        return
    session = None
    try:
        session = SessionLocal()
        obj = session.query(ScanModel).filter(ScanModel.scan_id == scan_id).one_or_none()
        if obj:
            session.delete(obj)
            session.commit()
            logger.info(f"Deleted scan {scan_id} from DB")
    except Exception as e:
        logger.error(f"Failed to delete scan from DB: {e}")
    finally:
        if session:
            session.close()
