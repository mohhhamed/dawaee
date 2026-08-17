"""جداول قاعدة البيانات — كل شيء متعدّد العلامات حول brand_id."""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
)
from sqlalchemy.orm import relationship

from .database import Base


class Brand(Base):
    """علامة تجارية (مثل: بيج رايش، إنكيدو)."""
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True)
    slug = Column(String(50), unique=True, nullable=False)   # page_reich / enkidu
    name = Column(String(120), nullable=False)
    field = Column(String(120), default="")                  # المجال: ديكور / مدارس
    timezone = Column(String(60), default="Asia/Baghdad")
    tone = Column(Text, default="")                          # نبرة الكتابة والهوية
    hashtags = Column(Text, default="")                      # هاشتاغ ثابت
    fb_page_id = Column(String(120), default="")
    fb_page_token = Column(Text, default="")
    ig_account_id = Column(String(120), default="")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    schedule = relationship("ScheduleConfig", back_populates="brand", uselist=False,
                            cascade="all, delete-orphan")
    sources = relationship("Source", back_populates="brand", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="brand", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="brand", cascade="all, delete-orphan")


class ScheduleConfig(Base):
    """الكمّيات اليومية وأوقات النشر لكل علامة."""
    __tablename__ = "schedule_config"

    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), unique=True, nullable=False)
    daily_posts = Column(Integer, default=3)
    daily_stories = Column(Integer, default=2)
    daily_reels = Column(Integer, default=1)
    # أوقات النشر لكل صيغة، مثال: {"post": ["10:00","14:00","20:00"], ...}
    times = Column(JSON, default=dict)
    refill_threshold = Column(Integer, default=20)  # يعيد ملء البنك تحت هذا الحد

    brand = relationship("Brand", back_populates="schedule")


class Source(Base):
    """مُدخل خام: وصف و/أو صورة يرفعها صاحب العلامة، مع تحليل الرؤية."""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    description = Column(Text, default="")
    image_url = Column(Text, default="")
    ai_analysis = Column(Text, default="")   # ناتج تحليل الرؤية
    created_at = Column(DateTime, default=datetime.utcnow)

    brand = relationship("Brand", back_populates="sources")


class Asset(Base):
    """قطعة محتوى مولّدة جاهزة (بنك المحتوى)."""
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    fmt = Column(String(20), default="post")     # post / story / reel
    caption = Column(Text, default="")
    hashtags = Column(Text, default="")
    media_url = Column(Text, default="")
    prompt = Column(Text, default="")
    used = Column(Boolean, default=False)        # هل جُدول للنشر؟
    created_at = Column(DateTime, default=datetime.utcnow)

    brand = relationship("Brand", back_populates="assets")


class Post(Base):
    """منشور مجدول أو منشور فعليًا."""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    fmt = Column(String(20), default="post")
    caption = Column(Text, default="")
    media_url = Column(Text, default="")
    platform = Column(String(20), default="both")  # fb / ig / both
    status = Column(String(20), default="scheduled")  # scheduled/published/failed
    scheduled_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    external_post_id = Column(String(200), default="")
    error = Column(Text, default="")

    brand = relationship("Brand", back_populates="posts")
