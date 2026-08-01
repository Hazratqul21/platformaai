"""Eksport: Excel (openpyxl) va PDF (reportlab) — TZ 5-bo'lim."""
import io
import re
import unicodedata
from datetime import date
from decimal import Decimal
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import get_user
from .. import models as m
from .. import services as s
from .. import domain
from ..domain import soha_oqi

# Bazada lotin saqlanadi, hujjatda kirill chiqadi (ilova bilan bir xil)
_KIR = {
    "Naqd": "Нақд", "O'tkazma": "Ўтказма", "Otkazma": "Ўтказма", "Karta": "Карта",
    "Kredit": "Кредит", "Aralash": "Аралаш",
}


def kir_pay(v: str | None) -> str:
    """To'lov turini kirillga o'giradi; noma'lum qiymat o'z holicha qoladi."""
    return _KIR.get((v or "").strip(), (v or "—"))

router = APIRouter(prefix="/api/reports", tags=["Hisobotlar"])

HDR = Font(bold=True, color="FFFFFF")
FILL = PatternFill("solid", fgColor="5E63E0")
THIN = Border(*[Side(style="thin", color="CCCCCC")] * 4)

# kirillcha/lotincha to'liq chiqishi uchun tizim shrifti (macOS yoki Linux)
_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",       # Linux (server)
    "/System/Library/Fonts/Supplemental/Arial.ttf",          # macOS
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
PDF_FONT = "Helvetica"
for _fp in _FONT_PATHS:
    try:
        pdfmetrics.registerFont(TTFont("Uz", _fp))
        PDF_FONT = "Uz"
        break
    except Exception:
        continue


def xlsx_response(wb: Workbook, name: str) -> StreamingResponse:
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    # Fayl nomida kirill/o'zbek harflari bo'lishi mumkin (mijoz nomi), HTTP sarlavhasi esa
    # faqat latin-1 ni ko'taradi — shuning uchun UTF-8 nom RFC 5987 bo'yicha beriladi.
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    ascii_name = re.sub(r'[^A-Za-z0-9._-]+', "_", ascii_name).strip("_") or "hisobot.xlsx"
    if not ascii_name.endswith(".xlsx"):
        ascii_name += ".xlsx"
    disposition = (f'attachment; filename="{ascii_name}"; '
                   f"filename*=UTF-8''{quote(name)}")
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": disposition})


def style_header(ws, row=1):
    for cell in ws[row]:
        if cell.value:
            cell.font = HDR
            cell.fill = FILL
            cell.alignment = Alignment(horizontal="center")


@router.get("/warehouse.xlsx")
def warehouse_xlsx(db: Session = Depends(get_db), user=Depends(get_user)):
    wb = Workbook()
    ws = wb.active
    ws.title = "Xomashyo qoldiqlari"
    ws.append(["Lot", "Yetkazib beruvchi", "Marka", "Grammaj", "Kirim kg",
               "Qoldiq kg", "Narx so'm/kg", "Qoldiq qiymati", "Sana"])
    for lot in db.query(m.RawLot).order_by(m.RawLot.grade, m.RawLot.received_at).all():
        supp = lot.supplier.name if lot.supplier else "—"
        ws.append([lot.lot_no, supp, lot.grade, lot.grammage,
                   float(lot.qty_kg), float(lot.remaining_kg), float(lot.price_per_kg),
                   float(lot.remaining_kg) * float(lot.price_per_kg),
                   lot.received_at.isoformat()])
    style_header(ws)
    for col in "EFGH":
        for c in ws[col]:
            c.number_format = "#,##0.00"
    ws2 = wb.create_sheet("Tayyor mahsulot")
    ws2.append(["Buyurtma", "Mijoz", "O'lcham", "Marka", "Soni", "Summa"])
    for o in db.query(m.Order).filter(m.Order.status == m.ST_OMBORDA).all():
        ws2.append([f"#{o.id}", o.client.company,
                    domain.olcham_matni(o, "x"), soha_oqi(o, "grade"), o.qty, float(o.total)])
    style_header(ws2)
    return xlsx_response(wb, f"sklad_{date.today()}.xlsx")


@router.get("/sverka/{client_id}.xlsx")
def sverka_xlsx(client_id: int, db: Session = Depends(get_db), user=Depends(get_user)):
    """Aylanma-saldo vedomosti — mijoz bilan sverka akti (TZ 4.2)."""
    c = db.get(m.Client, client_id)
    if not c:
        raise HTTPException(404, "Мижоз топилмади")
    wb = Workbook()
    ws = wb.active
    rk = s.rekvizit(db, c.firm)
    ws.title = "Сверка"
    if rk["nomi"]:
        ws.append([rk["nomi"] + (f"  ·  СТИР: {rk['stir']}" if rk["stir"] else "")])
        ws.merge_cells("A1:E1")
        ws["A1"].font = Font(bold=True, size=11)
        ws.append([])
    ws.append([f"СОЛИШТИРМА ДАЛОЛАТНОМА (СВЕРКА) — {c.company} "
               f"(СТИР: {c.inn or '—'}) · {date.today().strftime('%d.%m.%Y')}"])
    bosh = ws.max_row
    ws.merge_cells(f"A{bosh}:E{bosh}")
    ws[f"A{bosh}"].font = Font(bold=True, size=13)
    ws.append([])
    ws.append(["Сана", "Ҳужжат", "Изоҳ", "Дебет (олинди)", "Кредит (тўланди)"])
    sarlavha_qatori = ws.max_row
    rows = []
    # boshlang'ich qarz (tizimdan oldingi)
    if c.opening_balance and Decimal(c.opening_balance) != 0:
        od = c.opening_date or date(2026, 7, 1)
        rows.append((od, "Бошланғич қарз", "Тизимдан олдин",
                     float(c.opening_balance), 0))
    # faqat TOPSHIRILGAN mol (delivered_qty × narx)
    for o in c.orders:
        d = o.delivered_qty or 0
        if d > 0:
            qism = f" ({d}/{o.qty})" if d < o.qty else ""
            rows.append(((o.delivered_at or o.created_at.date()), f"Буюртма #{o.id}{qism}",
                         f"{d} дона {domain.olcham_matni(o)}",
                         float(Decimal(o.unit_price) * d), 0))
    for p in c.payments:
        rows.append((p.paid_at, f"Тўлов #{p.id}", kir_pay(p.method), 0, float(p.amount)))
    rows.sort(key=lambda r: r[0])
    deb = cred = 0.0
    for r in rows:
        ws.append([r[0].isoformat(), r[1], r[2], r[3] or "", r[4] or ""])
        deb += r[3]
        cred += r[4]
    ws.append([])
    ws.append(["", "", "ЖАМИ", deb, cred])
    ws.append(["", "", "ЯКУНИЙ ҚАРЗ", deb - cred, ""])
    if rk["rahbar"]:
        ws.append([])
        ws.append(["", "", rk["rahbar"], "", ""])
    style_header(ws, sarlavha_qatori)   # shapka bo'lsa sarlavha pastga suriladi
    yakun = ws.max_row - (2 if rk["rahbar"] else 0)
    for row in (yakun - 1, yakun):
        for cell in ws[row]:
            cell.font = Font(bold=True)
    for col in "DE":
        for cc in ws[col]:
            cc.number_format = "#,##0"
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 30
    for col in "DE":
        ws.column_dimensions[col].width = 16
    return xlsx_response(wb, f"sverka_{c.company}_{date.today()}.xlsx")


@router.get("/payroll.xlsx")
def payroll_xlsx(year: int | None = None, month: int | None = None,
                 db: Session = Depends(get_db), user=Depends(get_user)):
    today = date.today()
    data = s.payroll(db, year or today.year, month or today.month)
    wb = Workbook()
    ws = wb.active
    ws.title = "Oylik vedomost"
    ws.append(["Xodim", "Lavozim", "Brigada", "Qutilar (QC ✓)",
               "Ishbay summa", "Avans/Xarajat", "Toza qoldiq"])
    for r in data:
        ws.append([r["name"], r["position"], r["brigade"], r["boxes"],
                   r["earned"], r["advances"], r["net"]])
    style_header(ws)
    for col in "EFG":
        for c in ws[col]:
            c.number_format = "#,##0"
    ws.column_dimensions["A"].width = 24
    return xlsx_response(wb, f"oylik_{year or today.year}_{month or today.month}.xlsx")


@router.get("/act/{order_id}.pdf")
def act_pdf(order_id: int, db: Session = Depends(get_db), user=Depends(get_user)):
    """Akt priyom-peredachi — PDF (TZ 5.1)."""
    o = db.get(m.Order, order_id)
    if not o:
        raise HTTPException(404, "Буюртма топилмади")
    c = o.client
    rk = s.rekvizit(db, c.firm)          # mijoz firmasiga mos rekvizit (sozlamalardan)
    buf = io.BytesIO()
    p = pdfcanvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 22 * mm

    # --- Firma shapkasi (sozlamada to'ldirilgan maydonlargina chiqadi) ---
    if rk["nomi"]:
        p.setFont(PDF_FONT, 13)
        p.drawCentredString(w / 2, y, rk["nomi"])
        y -= 6 * mm
    shapka = []
    if rk["stir"]:
        shapka.append(f"СТИР: {rk['stir']}")
    if rk["tel"]:
        shapka.append(f"тел: {rk['tel']}")
    if shapka:
        p.setFont(PDF_FONT, 9)
        p.drawCentredString(w / 2, y, "  ·  ".join(shapka))
        y -= 5 * mm
    if rk["manzil"]:
        p.setFont(PDF_FONT, 9)
        p.drawCentredString(w / 2, y, rk["manzil"])
        y -= 5 * mm
    if rk["bank"] or rk["hisob"]:
        p.setFont(PDF_FONT, 9)
        bank = "  ·  ".join(x for x in (rk["bank"], rk["hisob"]) if x)
        p.drawCentredString(w / 2, y, bank)
        y -= 5 * mm
    if rk["nomi"]:
        p.setLineWidth(0.6)
        p.line(25 * mm, y, w - 25 * mm, y)
        y -= 8 * mm

    p.setFont(PDF_FONT, 16)
    p.drawCentredString(w / 2, y, "ҚАБУЛ ҚИЛИШ-ТОПШИРИШ ДАЛОЛАТНОМАСИ")
    y -= 8 * mm
    p.setFont(PDF_FONT, 10)
    p.drawCentredString(w / 2, y, f"Буюртма № {o.id} · Сана: {date.today().strftime('%d.%m.%Y')}")
    y -= 14 * mm
    p.setFont(PDF_FONT, 11)
    lines = [
        ("Топширувчи:", rk["nomi"] or "Ишлаб чиқариш цехи"),
        ("Қабул қилувчи:", f"{c.company}  (СТИР: {c.inn or '—'})"),
        ("Масъул шахс:", f"{c.contact or '—'} · {c.phone or '—'}"),
        ("Тўлов тури:", kir_pay(c.pay_type)),
        ("", ""),
        ("Маҳсулот:", f"Гофра қути {domain.olcham_matni(o)} мм, {domain.tarkib_matni(o)}"),
        ("Миқдори:", f"{o.qty:,} дона".replace(",", " ")),
        ("Нархи (1 дона):", f"{float(o.unit_price):,.0f} сўм".replace(",", " ")),
        ("Жами сумма:", f"{float(o.total):,.0f} сўм".replace(",", " ")),
    ]
    for k, v in lines:
        if k:
            p.setFont(PDF_FONT, 11)
            p.drawString(25 * mm, y, k)
            p.drawString(70 * mm, y, v)
        y -= 8 * mm
    y -= 10 * mm
    if o.accepted_stamp:
        p.setFont(PDF_FONT, 12)
        p.setFillColorRGB(0.1, 0.62, 0.39)
        p.drawString(25 * mm, y, "✔ ЭЛЕКТРОН ТАСДИҚЛАНДИ — мижоз бот орқали «Қабул қилдим» босган")
        p.setFillColorRGB(0, 0, 0)
        y -= 12 * mm
    p.setFont(PDF_FONT, 11)
    p.drawString(25 * mm, y, "Топширди: ______________________")
    p.drawString(110 * mm, y, "Қабул қилди: ______________________")
    if rk["rahbar"]:
        y -= 6 * mm
        p.setFont(PDF_FONT, 9)
        p.drawString(25 * mm, y, rk["rahbar"])
    if rk["footer"]:
        p.setFont(PDF_FONT, 8)
        p.drawCentredString(w / 2, 15 * mm, rk["footer"])
    p.showPage()
    p.save()
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'inline; filename="akt_{o.id}.pdf"'})


@router.get("/cash.xlsx")
def cash_xlsx(db: Session = Depends(get_db), user=Depends(get_user)):
    wb = Workbook()
    ws = wb.active
    ws.title = "Kassa aylanmasi"
    ws.append(["Sana", "Turi", "Xodim", "Summa", "Izoh"])
    for r in db.query(m.CashEntry).order_by(m.CashEntry.entry_at.desc()).all():
        e = db.get(m.Employee, r.employee_id) if r.employee_id else None
        ws.append([r.entry_at.isoformat(), r.kind, e.name if e else "—",
                   float(r.amount), r.note])
    style_header(ws)
    for c in ws["D"]:
        c.number_format = "#,##0"
    return xlsx_response(wb, f"kassa_{date.today()}.xlsx")


# ================= YUK XATI (nakladnoy) — PDF / Excel / Word =================

def _nakladnoy_data(db: Session, order_id: int):
    o = db.get(m.Order, order_id)
    if not o:
        raise HTTPException(404, "Буюртма топилмади")
    c = o.client
    # DIQQAT: bu yerda "Картон қути", boshqa hujjatda "Гофра қути" — eskidan
    # shunday. Ataylab birlashtirilmadi: foydalanuvchi ko'radigan matn
    # refaktorda o'zgarib ketmasin. Sohaga ko'chirilganda hal qilinadi.
    product = f"Картон қути {domain.olcham_matni(o)} мм, {domain.tarkib_matni(o)}"
    return o, c, product


@router.get("/nakladnoy/{order_id}.pdf")
def nakladnoy_pdf(order_id: int, db: Session = Depends(get_db), user=Depends(get_user)):
    o, c, product = _nakladnoy_data(db, order_id)
    buf = io.BytesIO()
    p = pdfcanvas.Canvas(buf, pagesize=A4)
    w, h = A4
    rk = s.rekvizit(db, c.firm)
    y = h - 20 * mm
    # --- Firma shapkasi (sozlamadan; bo'sh maydonlar chiqmaydi) ---
    if rk["nomi"]:
        p.setFont(PDF_FONT, 12)
        p.drawCentredString(w / 2, y, rk["nomi"])
        y -= 5 * mm
        qat = [x for x in (f"СТИР: {rk['stir']}" if rk["stir"] else "",
                           f"тел: {rk['tel']}" if rk["tel"] else "",
                           rk["manzil"]) if x]
        if qat:
            p.setFont(PDF_FONT, 8.5)
            p.drawCentredString(w / 2, y, "  ·  ".join(qat))
            y -= 5 * mm
        p.setLineWidth(0.6)
        p.line(20 * mm, y, w - 20 * mm, y)
        y -= 7 * mm

    p.setFont(PDF_FONT, 16)
    p.drawCentredString(w / 2, y, f"ЮК ХАТИ (НАКЛАДНАЯ) № {o.id}")
    y -= 7 * mm
    p.setFont(PDF_FONT, 10)
    p.drawCentredString(w / 2, y, f"Сана: {date.today().strftime('%d.%m.%Y')}")
    y -= 13 * mm
    p.setFont(PDF_FONT, 11)
    for k, v in [("Юк берувчи:", rk["nomi"] or "Ишлаб чиқариш цехи"),
                 ("Юк олувчи:", f"{c.company} (СТИР: {c.inn or '—'})"),
                 ("Масъул шахс:", f"{c.contact or '—'} · {c.phone or '—'}"),
                 ("Тўлов тури:", kir_pay(c.pay_type))]:
        p.drawString(20 * mm, y, k)
        p.drawString(60 * mm, y, v)
        y -= 7 * mm
    y -= 5 * mm
    # jadval
    headers = ["№", "Маҳсулот номи", "Ўлчов", "Сони", "Нархи (сўм)", "Сумма (сўм)"]
    xs = [20, 32, 118, 136, 152, 175]
    p.setFont(PDF_FONT, 10)
    p.setFillColorRGB(0.37, 0.39, 0.88)
    p.rect(18 * mm, y - 2 * mm, 174 * mm, 8 * mm, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    for x, htxt in zip(xs, headers):
        p.drawString(x * mm, y, htxt)
    p.setFillColorRGB(0, 0, 0)
    y -= 9 * mm
    row = ["1", product, "дона", f"{o.qty:,}".replace(",", " "),
           f"{float(o.unit_price):,.0f}".replace(",", " "),
           f"{float(o.total):,.0f}".replace(",", " ")]
    for x, v in zip(xs, row):
        p.setFont(PDF_FONT, 9 if x == 32 else 10)
        p.drawString(x * mm, y, v[:52])
    y -= 6 * mm
    p.line(18 * mm, y, 192 * mm, y)
    y -= 8 * mm
    p.setFont(PDF_FONT, 11)
    p.drawString(118 * mm, y, "ЖАМИ:")
    p.drawString(152 * mm, y, f"{float(o.total):,.0f} сўм".replace(",", " "))
    y -= 16 * mm
    p.setFont(PDF_FONT, 11)
    p.drawString(20 * mm, y, "Топширди: ______________________")
    p.drawString(110 * mm, y, "Қабул қилди: ______________________")
    if rk["rahbar"]:
        y -= 6 * mm
        p.setFont(PDF_FONT, 9)
        p.drawString(20 * mm, y, rk["rahbar"])
    y -= 10 * mm
    p.setFont(PDF_FONT, 9)
    p.drawString(20 * mm, y, "М.Ў.")
    if rk["footer"]:
        p.setFont(PDF_FONT, 8)
        p.drawCentredString(w / 2, 12 * mm, rk["footer"])
    p.showPage()
    p.save()
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'inline; filename="yuk_xati_{o.id}.pdf"'})


@router.get("/nakladnoy/{order_id}.xlsx")
def nakladnoy_xlsx(order_id: int, db: Session = Depends(get_db), user=Depends(get_user)):
    o, c, product = _nakladnoy_data(db, order_id)
    wb = Workbook()
    ws = wb.active
    ws.title = "Накладная"
    ws.append([f"НАКЛАДНАЯ № {o.id} · {date.today().strftime('%d.%m.%Y')}"])
    ws.merge_cells("A1:F1")
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([])
    ws.append(["Yuk beruvchi:", "Ishlab chiqarish sexi"])
    ws.append(["Yuk oluvchi:", f"{c.company} (STIR: {c.inn or '—'})"])
    ws.append(["Mas'ul shaxs:", f"{c.contact or '—'} · {c.phone or '—'}"])
    ws.append(["To'lov turi:", c.pay_type])
    ws.append([])
    ws.append(["№", "Mahsulot nomi", "O'lchov", "Soni", "Narxi", "Summa"])
    ws.append([1, product, "dona", o.qty, float(o.unit_price), float(o.total)])
    ws.append([])
    ws.append(["", "", "", "", "JAMI:", float(o.total)])
    style_header(ws, 8)
    for col in "EF":
        for cc in ws[col]:
            cc.number_format = "#,##0"
    ws.column_dimensions["B"].width = 46
    for col in "CDEF":
        ws.column_dimensions[col].width = 13
    ws.append([])
    ws.append(["Topshirdi: ______________", "", "Qabul qildi: ______________"])
    return xlsx_response(wb, f"yuk_xati_{o.id}.xlsx")


@router.get("/nakladnoy/{order_id}.docx")
def nakladnoy_docx(order_id: int, db: Session = Depends(get_db), user=Depends(get_user)):
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    o, c, product = _nakladnoy_data(db, order_id)
    doc = Document()
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.add_run(f"НАКЛАДНАЯ № {o.id}")
    run.bold = True
    run.font.size = Pt(16)
    d = doc.add_paragraph(f"Sana: {date.today().strftime('%d.%m.%Y')}")
    d.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for k, v in [("Yuk beruvchi", "Ishlab chiqarish sexi"),
                 ("Yuk oluvchi", f"{c.company} (STIR: {c.inn or '—'})"),
                 ("Mas'ul shaxs", f"{c.contact or '—'} · {c.phone or '—'}"),
                 ("To'lov turi", c.pay_type)]:
        pr = doc.add_paragraph()
        pr.add_run(f"{k}: ").bold = True
        pr.add_run(v)
    table = doc.add_table(rows=2, cols=6)
    table.style = "Table Grid"
    for i, htxt in enumerate(["№", "Mahsulot nomi", "O'lchov", "Soni", "Narxi", "Summa"]):
        cell = table.rows[0].cells[i]
        cell.text = htxt
        cell.paragraphs[0].runs[0].bold = True
    vals = ["1", product, "dona", f"{o.qty:,}".replace(",", " "),
            f"{float(o.unit_price):,.0f}".replace(",", " "),
            f"{float(o.total):,.0f}".replace(",", " ")]
    for i, v in enumerate(vals):
        table.rows[1].cells[i].text = v
    tot = doc.add_paragraph()
    tot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    tr = tot.add_run(f"JAMI: {float(o.total):,.0f} so'm".replace(",", " "))
    tr.bold = True
    doc.add_paragraph()
    doc.add_paragraph("Topshirdi: ______________________        Qabul qildi: ______________________")
    doc.add_paragraph("M.O'.")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="yuk_xati_{o.id}.docx"'})


@router.get("/purchases.xlsx")
def purchases_xlsx(db: Session = Depends(get_db), user=Depends(get_user)):
    """Xaridlar hisoboti — Master Excel'ning o'rnini bosadi (2 sahifa: xarid + qarz)."""
    from sqlalchemy import func as _f
    wb = Workbook()
    ws = wb.active
    ws.title = "Xaridlar"
    ws.append(["Sana", "Material", "Grammaj", "Bo'lim", "Format", "Miqdor",
               "Birlik", "Narx", "Summa", "To'lov turi", "To'landi", "Qarz"])
    tot = Decimal("0")
    tot_debt = Decimal("0")
    for p in db.query(m.Purchase).order_by(m.Purchase.purchased_at).all():
        paid = Decimal(p.paid_amount) + Decimal(
            db.query(_f.coalesce(_f.sum(m.PurchasePayment.amount), 0))
            .filter(m.PurchasePayment.purchase_id == p.id).scalar())
        debt = Decimal(p.total) - paid
        mat = p.material
        ws.append([p.purchased_at.isoformat(), mat.name if mat else "?",
                   mat.grammaj if mat else "", mat.category if mat else "",
                   p.fmt, float(p.qty), p.unit, float(p.unit_price),
                   float(p.total), p.payment_type, float(paid), float(debt)])
        tot += Decimal(p.total)
        tot_debt += debt
    ws.append([])
    ws.append(["", "", "", "", "", "", "", "JAMI:", float(tot), "", "", float(tot_debt)])
    style_header(ws)
    for cell in ws[ws.max_row]:
        cell.font = Font(bold=True)
    for col in "HIKL":
        for c in ws[col]:
            c.number_format = "#,##0"
    ws.column_dimensions["B"].width = 22
    return xlsx_response(wb, f"xaridlar_{date.today()}.xlsx")


@router.get("/expenses.xlsx")
def expenses_xlsx(firm: str | None = None, db: Session = Depends(get_db), user=Depends(get_user)):
    """Sex xarajatlari hisoboti — sana, nimaga, firma, summa."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Xarajatlar"
    ws.append(["Sana", "Nimaga", "Firma", "Summa"])
    q = db.query(m.CashEntry).filter(m.CashEntry.kind == "Xarajat")
    if firm:
        q = q.filter(m.CashEntry.firm.in_([firm, ""]))
    tot = Decimal("0")
    for r in q.order_by(m.CashEntry.entry_at).all():
        ws.append([r.entry_at.isoformat(), r.note or "Izohsiz", r.firm, float(r.amount)])
        tot += Decimal(r.amount)
    ws.append([])
    ws.append(["", "", "JAMI:", float(tot)])
    style_header(ws)
    for cell in ws[ws.max_row]:
        cell.font = Font(bold=True)
    for c in ws["D"]:
        c.number_format = "#,##0"
    ws.column_dimensions["B"].width = 34
    ws.column_dimensions["C"].width = 14
    return xlsx_response(wb, f"xarajatlar_{date.today()}.xlsx")
