"""
E-AUKSION monitor — DB jadvallari (PHASE 4).
════════════════════════════════════════════════════════════════════
Prefiks `ea_` — ERP jadvallari bilan to'qnashmasin.
BARCHA vaqt qiymatlari UTC (`utcnow`). Pul — Numeric (float emas).
Maydonlar e-auksion `/api/front/*` javobiga moslangan
(qarang: docs/eauksion/01-DATA-SOURCE.md).

Faqat MONITORING: bu jadvallar ochiq ma'lumot + foydalanuvchining o'z
sozlamalarini saqlaydi. Bid/ariza avtomatlashtirilmaydi.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, Numeric, Boolean, ForeignKey, DateTime, Text, JSON, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base

# PostgreSQL da JSONB, SQLite da JSON — models.py dagi bilan bir xil uslub.
JSONB_ = JSON().with_variant(JSONB, "postgresql")
D = Numeric(18, 2)   # pul summalari (UZS)


def utcnow() -> datetime:
    """Har doim timezone-aware UTC. Standart qiymat sifatida ishlatiladi."""
    return datetime.now(timezone.utc)


# ── Event turlari (real-time engine) — promptdagi ro'yxat ───────────
EV_LOT_CREATED      = "LOT_CREATED"
EV_AUCTION_STARTED  = "AUCTION_STARTED"
EV_BID_RECEIVED     = "BID_RECEIVED"
EV_PRICE_CHANGED    = "PRICE_CHANGED"
EV_AUCTION_EXTENDED = "AUCTION_EXTENDED"
EV_AUCTION_FINISHED = "AUCTION_FINISHED"
EV_AUCTION_CANCELLED= "AUCTION_CANCELLED"
EV_STATUS_CHANGED   = "STATUS_CHANGED"
EVENT_TURLARI = [
    EV_LOT_CREATED, EV_AUCTION_STARTED, EV_BID_RECEIVED, EV_PRICE_CHANGED,
    EV_AUCTION_EXTENDED, EV_AUCTION_FINISHED, EV_AUCTION_CANCELLED, EV_STATUS_CHANGED,
]

# G'alaba ehtimoli natijasi
COMP_LOW, COMP_MEDIUM, COMP_HIGH = "LOW", "MEDIUM", "HIGH"


class EaLot(Base):
    """Lot katalogi — har lot uchun bitta qator. `source_lot_id` — e-auksion `id`."""
    __tablename__ = "ea_lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_lot_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    lot_number: Mapped[str | None] = mapped_column(String(32), index=True)
    name: Mapped[str | None] = mapped_column(Text)
    full_address: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String(120), index=True)

    category_id: Mapped[int | None] = mapped_column(Integer, index=True)
    group_id: Mapped[int | None] = mapped_column(Integer, index=True)
    category_name: Mapped[str | None] = mapped_column(String(120))

    start_price: Mapped[float | None] = mapped_column(D)
    appraised_price: Mapped[float | None] = mapped_column(D)   # baholangan_narx
    zaklad_summa: Mapped[float | None] = mapped_column(D)
    zaklad_percent: Mapped[float | None] = mapped_column(Numeric(6, 2))

    auction_type_id: Mapped[int | None] = mapped_column(Integer)
    is_descending: Mapped[bool] = mapped_column(Boolean, default=False)  # is_descending_auction
    is_term_payment: Mapped[bool] = mapped_column(Boolean, default=False)
    term_month: Mapped[int | None] = mapped_column(Integer)
    is_shop_lot: Mapped[bool] = mapped_column(Boolean, default=False)

    status_id: Mapped[int | None] = mapped_column(Integer, index=True)  # lot_statuses_id
    status_text: Mapped[str | None] = mapped_column(String(60))

    auction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))     # UTC
    order_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))   # UTC

    media_url: Mapped[str | None] = mapped_column(Text)
    file_hash: Mapped[str | None] = mapped_column(String(80))

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    raw: Mapped[dict | None] = mapped_column(JSONB_)  # to'liq xom javob (nomuvofiqlik tekshiruvi uchun)

    auctions: Mapped[list["EaAuction"]] = relationship(back_populates="lot")


class EaAuction(Base):
    """Auksion sikli (lot bo'yicha). Narx/status/qatnashuv jonli holati shu yerda."""
    __tablename__ = "ea_auctions"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("ea_lots.id"), index=True)
    current_price: Mapped[float | None] = mapped_column(D)
    status_id: Mapped[int | None] = mapped_column(Integer, index=True)
    status_text: Mapped[str | None] = mapped_column(String(60))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extended_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    lot: Mapped["EaLot"] = relationship(back_populates="auctions")


class EaBid(Base):
    """Bid eventi. Jonli savdo kanalidan olinadi (kelajakda). Faqat OCHIQ ma'lumot."""
    __tablename__ = "ea_bids"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("ea_lots.id"), index=True)
    amount: Mapped[float | None] = mapped_column(D)
    bidder_ref: Mapped[str | None] = mapped_column(String(120))  # ochiq ko'rsatkich (ism/№) — PII saqlanmaydi
    bid_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str | None] = mapped_column(String(40))
    raw_hash: Mapped[str | None] = mapped_column(String(80))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EaEvent(Base):
    """Real-time event log — promptdagi event sxemasi.
    {lot_id, event_type, timestamp, price, source, raw_data_hash}."""
    __tablename__ = "ea_auction_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int | None] = mapped_column(Integer, index=True)  # source_lot_id (yumshoq bog'lanish)
    event_type: Mapped[str] = mapped_column(String(30), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    price: Mapped[float | None] = mapped_column(D)
    source: Mapped[str | None] = mapped_column(String(40))
    raw_data_hash: Mapped[str | None] = mapped_column(String(80))
    payload: Mapped[dict | None] = mapped_column(JSONB_)


class EaPriceHistory(Base):
    """Narx o'zgarishlari tarixi (price_velocity hisobi uchun)."""
    __tablename__ = "ea_price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(Integer, index=True)  # source_lot_id
    price: Mapped[float | None] = mapped_column(D)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    source: Mapped[str | None] = mapped_column(String(40))


class EaParticipantsPublic(Base):
    """Ochiq qatnashuv snapshoti (bid'lar aniq soni yashirin — faqat agregat)."""
    __tablename__ = "ea_participants_public"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(Integer, index=True)  # source_lot_id
    order_cnt_text: Mapped[str | None] = mapped_column(String(16))  # "0" / "1+"
    apply_cnt: Mapped[int | None] = mapped_column(Integer)
    view_count: Mapped[int | None] = mapped_column(Integer)
    favourite_count: Mapped[int | None] = mapped_column(Integer)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class EaWatcher(Base):
    """Bidding assistant sozlamalari (foydalanuvchi ustuvorliklari).
    E-auksion PAROLI BU YERDA SAQLANMAYDI — auth alohida, shifrlangan (ea_session)."""
    __tablename__ = "ea_watchers"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_user_id: Mapped[int | None] = mapped_column(Integer, index=True)  # ERP users.id (ixtiyoriy)
    label: Mapped[str | None] = mapped_column(String(120))
    max_budget: Mapped[float | None] = mapped_column(D)
    minimum_increment: Mapped[float | None] = mapped_column(D)
    notification_threshold: Mapped[float | None] = mapped_column(D)
    notification_channels: Mapped[dict | None] = mapped_column(JSONB_)  # {"telegram":..., "web":true}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EaWatchLot(Base):
    """Kuzatilayotgan lotlar (watcher ↔ lot)."""
    __tablename__ = "ea_watch_lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    watcher_id: Mapped[int] = mapped_column(ForeignKey("ea_watchers.id"), index=True)
    source_lot_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EaNotification(Base):
    """Yuborilgan/navbatdagi bildirishnomalar."""
    __tablename__ = "ea_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    watcher_id: Mapped[int | None] = mapped_column(Integer, index=True)
    source_lot_id: Mapped[int | None] = mapped_column(Integer, index=True)
    channel: Mapped[str | None] = mapped_column(String(30))     # telegram | web
    kind: Mapped[str | None] = mapped_column(String(40))        # NEW_BID | PRICE_NEAR_BUDGET | ENDING_SOON ...
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | sent | failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EaAnalysis(Base):
    """G'alaba ehtimoli / raqobat tahlili natijasi (PROGNOZ — UI'da shunday belgilanadi)."""
    __tablename__ = "ea_analysis_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_lot_id: Mapped[int] = mapped_column(Integer, index=True)
    competition_level: Mapped[str | None] = mapped_column(String(10))  # LOW | MEDIUM | HIGH
    competition_intensity: Mapped[float | None] = mapped_column(Numeric(10, 4))
    bid_frequency: Mapped[float | None] = mapped_column(Numeric(10, 4))
    price_velocity: Mapped[float | None] = mapped_column(Numeric(18, 4))
    time_remaining_sec: Mapped[int | None] = mapped_column(Integer)
    metrics: Mapped[dict | None] = mapped_column(JSONB_)  # to'liq ko'rsatkichlar
    is_forecast: Mapped[bool] = mapped_column(Boolean, default=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class EaSystemLog(Base):
    """Tizim loglari — collector/xatolar/rate-limit (log analyzer uchun)."""
    __tablename__ = "ea_system_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    component: Mapped[str | None] = mapped_column(String(40), index=True)  # collector | events | session ...
    level: Mapped[str | None] = mapped_column(String(12), index=True)      # INFO | WARN | ERROR
    message: Mapped[str | None] = mapped_column(Text)
    context: Mapped[dict | None] = mapped_column(JSONB_)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


# Tez-tez birga so'raladigan ustunlar uchun kompozit indekslar
Index("ix_ea_events_lot_type_ts", EaEvent.lot_id, EaEvent.event_type, EaEvent.ts)
Index("ix_ea_price_lot_time", EaPriceHistory.lot_id, EaPriceHistory.observed_at)
