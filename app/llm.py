"""LLM QATLAMI — bitta interfeys, ko'p provayder.

Yuqoridagi agent kodi qaysi provayder ishlayotganini BILMAYDI. U faqat
`javob_ol(xabarlar, asboblar, korsatma)` chaqiradi va bir xil ko'rinishdagi
natija oladi. Provayder almashtirilsa agent kodi o'zgarmaydi.

NEGA KERAK:
Mijoz o'z kalitini qo'yadi — kimdadir Anthropic, kimdadir OpenAI, kimdadir
Gemini bor. Bittasiga bog'lanib qolish platformani cheklaydi. Bundan
tashqari bitta provayder ishlamay qolsa (limit, uzilish) tizim butunlay
to'xtab qolmasligi kerak.

QO'LLAB-QUVVATLANADI:
  anthropic — Claude (rasmiy SDK)
  openai    — GPT (rasmiy SDK). `base_url` orqali OpenAI-mos har qanday
              xizmat ham ishlaydi: DeepSeek, Groq, Together, lokal Ollama.
              Shuning uchun bitta moslashtirgich o'nlab xizmatni qoplaydi.
  gemini    — Google Gemini (rasmiy SDK)

ICHKI KO'RINISH (provayderdan mustaqil):
    xabar   = {"rol": "user"|"assistant", "matn": str,
               "asbob_chaqiruvlari": [{"id","nom","kirish"}],
               "asbob_natijalari": [{"id","natija","xato"}]}
    javob   = {"matn": str, "chaqiruvlar": [{"id","nom","kirish"}],
               "rad_etildi": bool, "provayder": str, "model": str}

Har provayder shu ko'rinishga o'giradi. Tarix bazada SHU ko'rinishda
saqlanadi — provayder almashtirilsa eski suhbat o'qilaveradi.
"""
import base64
import json
import logging
import os
import time

log = logging.getLogger("gofra.llm")

# Provayder -> (muhit o'zgaruvchisi, standart model)
PROVAYDERLAR = {
    "anthropic": ("ANTHROPIC_API_KEY", "claude-opus-5"),
    "openai": ("OPENAI_API_KEY", "gpt-5"),
    # `gemini-2.5-pro` BEPUL tarifda umuman ochiq emas (limit: 0) —
    # jonli sinovda kalit to'g'ri bo'lsa ham 429 qaytardi. Flash modeli
    # bepul tarifda ham ishlaydi va asbob chaqirishga yetarli.
    "gemini": ("GEMINI_API_KEY", "gemini-3.5-flash"),
}


def _muhit(nom: str, standart: str = "") -> str:
    return (os.getenv(nom) or standart).strip()


def joriy_provayder() -> str:
    """Qaysi provayder ishlatiladi.

    `LLM_PROVAYDER` aniq belgilangan bo'lsa — o'sha. Aks holda kaliti
    bor birinchisi tanlanadi: mijoz faqat kalitni qo'yadi, provayder
    nomini yozib o'tirmaydi.
    """
    tanlangan = _muhit("LLM_PROVAYDER").lower()
    if tanlangan in PROVAYDERLAR:
        return tanlangan
    for nom, (kalit_nomi, _) in PROVAYDERLAR.items():
        if _muhit(kalit_nomi):
            return nom
    return "anthropic"   # kalit yo'q — xabar shu nom bilan beriladi


def joriy_model() -> str:
    p = joriy_provayder()
    return _muhit("LLM_MODEL") or PROVAYDERLAR[p][1]


def ulangan_provayderlar() -> list[str]:
    """HAQIQIY kaliti bor provayderlar — afzallik tartibida.

    `LLM_PROVAYDER` berilgan bo'lsa u birinchi turadi, lekin qolganlari
    ham ro'yxatda qoladi: mijoz uchta kalit qo'ysa, uchalasi ham
    ishlatiladi. Bittasining kvotasi tugasa keyingisiga o'tiladi —
    aks holda pulli kalit turgani bilan tizim «AI ishlamayapti» derdi.
    """
    tanlangan = _muhit("LLM_PROVAYDER").lower()
    tartib = ([tanlangan] if tanlangan in PROVAYDERLAR else []) + [
        nom for nom in PROVAYDERLAR if nom != tanlangan]
    return [nom for nom in tartib
            if (k := _muhit(PROVAYDERLAR[nom][0])) and not kalit_shubhali(k)]


# Haqiqiy kalitlar uzun bo'ladi (Anthropic/OpenAI ~100+, Gemini ~39).
# `.env.example` dan ko'chirilgan «sk-...» kabi o'rin egallovchi qiymat
# esa qisqa. Buni tekshirmasak — chat oynasi «tayyor» deb turadi,
# foydalanuvchi yozadi va faqat shunda 502 xatosini ko'radi.
ENG_QISQA_KALIT = 20


def kalit_shubhali(qiymat: str) -> bool:
    if len(qiymat) < ENG_QISQA_KALIT:
        return True
    past = qiymat.lower()
    return any(x in past for x in ("...", "xxx", "your", "sizning", "here",
                                   "kalit", "placeholder", "example"))


def tayyormi() -> tuple[bool, str]:
    """(tayyormi, izoh). Izoh foydalanuvchiga ko'rsatiladi."""
    p = joriy_provayder()
    kalit_nomi = PROVAYDERLAR[p][0]
    kalit = _muhit(kalit_nomi)
    if not kalit:
        return False, f"{kalit_nomi} qo'yilmagan — .env ga yozing"
    if kalit_shubhali(kalit):
        return False, (f"{kalit_nomi} haqiqiy kalitga o'xshamaydi "
                       f"(o'rin egallovchi qiymat qolib ketganmi?)")
    return True, f"{p} · {joriy_model()}"


def holat() -> dict:
    """Hamma provayderlar holati — sozlamalar va AI ekrani uchun."""
    tayyor, izoh = tayyormi()
    ulangan = ulangan_provayderlar()
    return {
        "tayyor": tayyor, "izoh": izoh,
        "provayder": joriy_provayder(), "model": joriy_model(),
        # Ulangan provayderlar TARTIB bilan: birinchisi ishlatiladi,
        # kvotasi tugasa keyingisiga o'tiladi.
        "ulangan": ulangan,
        "zanjir": [{"provayder": p, "model": md} for p, md in _zanjir()],
        "provayderlar": [
            {"nom": nom, "kalit": kalit_nomi,
             "kalit_bor": bool(_muhit(kalit_nomi)),
             "ishlaydi": nom in ulangan,
             "izoh": ("ulangan" if nom in ulangan
                      else ("kalit haqiqiyga o'xshamaydi"
                            if _muhit(kalit_nomi) else "kalit qo'yilmagan")),
             "standart_model": model}
            for nom, (kalit_nomi, model) in PROVAYDERLAR.items()],
    }


# =====================================================================
#  ANTHROPIC
# =====================================================================

def _anthropic(xabarlar, asboblar, korsatma, model):
    import anthropic

    client = anthropic.Anthropic()
    xom = []
    for x in xabarlar:
        if x["rol"] == "user" and x.get("asbob_natijalari"):
            xom.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": n["id"],
                 "content": n["natija"], "is_error": bool(n.get("xato"))}
                for n in x["asbob_natijalari"]]})
        elif x["rol"] == "assistant":
            bloklar = []
            if x.get("matn"):
                bloklar.append({"type": "text", "text": x["matn"]})
            for c in x.get("asbob_chaqiruvlari") or []:
                bloklar.append({"type": "tool_use", "id": c["id"],
                                "name": c["nom"], "input": c["kirish"]})
            xom.append({"role": "assistant", "content": bloklar or [
                {"type": "text", "text": "."}]})
        else:
            xom.append({"role": "user", "content": x["matn"]})

    javob = client.messages.create(
        model=model, max_tokens=16000,
        # Ko'rsatma har so'rovda bir xil — keshlansa qayta hisoblanmaydi
        system=[{"type": "text", "text": korsatma,
                 "cache_control": {"type": "ephemeral"}}],
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        tools=[{"name": a["nom"], "description": a["izoh"],
                "input_schema": a["sxema"]} for a in asboblar],
        messages=xom,
    )
    # Xavfsizlik klassifikatori rad etsa `content` bo'sh bo'lishi mumkin —
    # shuning uchun `stop_reason` content dan OLDIN tekshiriladi.
    if javob.stop_reason == "refusal":
        return {"matn": "", "chaqiruvlar": [], "rad_etildi": True}
    u = getattr(javob, "usage", None)
    return {
        "matn": "".join(b.text for b in javob.content if b.type == "text"),
        "chaqiruvlar": [{"id": b.id, "nom": b.name, "kirish": b.input or {}}
                        for b in javob.content if b.type == "tool_use"],
        "rad_etildi": False,
        "kirish_token": int(getattr(u, "input_tokens", 0) or 0),
        "chiqish_token": int(getattr(u, "output_tokens", 0) or 0),
    }


# =====================================================================
#  OPENAI (va OpenAI-mos xizmatlar: DeepSeek, Groq, Ollama, ...)
# =====================================================================

def _openai(xabarlar, asboblar, korsatma, model):
    from openai import OpenAI

    # `OPENAI_BASE_URL` berilsa boshqa xizmatga ulanadi. Aynan shu tufayli
    # bitta moslashtirgich o'nlab OpenAI-mos xizmatni qoplaydi.
    client = OpenAI(base_url=_muhit("OPENAI_BASE_URL") or None)

    xom = [{"role": "system", "content": korsatma}]
    for x in xabarlar:
        if x["rol"] == "user" and x.get("asbob_natijalari"):
            # OpenAI da har natija ALOHIDA xabar (Anthropic da bitta
            # xabarda ro'yxat) — formatlar shu joyda ajraladi.
            for n in x["asbob_natijalari"]:
                xom.append({"role": "tool", "tool_call_id": n["id"],
                            "content": n["natija"]})
        elif x["rol"] == "assistant":
            xabar = {"role": "assistant", "content": x.get("matn") or None}
            if x.get("asbob_chaqiruvlari"):
                xabar["tool_calls"] = [
                    {"id": c["id"], "type": "function",
                     "function": {"name": c["nom"],
                                  "arguments": json.dumps(c["kirish"],
                                                          ensure_ascii=False)}}
                    for c in x["asbob_chaqiruvlari"]]
            xom.append(xabar)
        else:
            xom.append({"role": "user", "content": x["matn"]})

    javob = client.chat.completions.create(
        model=model, messages=xom,
        tools=[{"type": "function",
                "function": {"name": a["nom"], "description": a["izoh"],
                             "parameters": a["sxema"]}} for a in asboblar],
    )
    xabar = javob.choices[0].message
    return {
        "matn": xabar.content or "",
        "chaqiruvlar": [
            {"id": c.id, "nom": c.function.name,
             # Argumentlar SATR bo'lib keladi — JSON qilib ochamiz.
             # Buzuq bo'lsa bo'sh lug'at: asbob o'zi xato qaytaradi va
             # model tuzatadi, butun suhbat yiqilmaydi.
             "kirish": _json_yoki_bosh(c.function.arguments)}
            for c in (xabar.tool_calls or [])],
        "rad_etildi": False,
        "kirish_token": int(getattr(getattr(javob, "usage", None), "prompt_tokens", 0) or 0),
        "chiqish_token": int(getattr(getattr(javob, "usage", None), "completion_tokens", 0) or 0),
    }


def _json_yoki_bosh(matn: str) -> dict:
    try:
        return json.loads(matn or "{}")
    except (ValueError, TypeError):
        log.warning("Asbob argumentlari buzuq JSON: %s", (matn or "")[:200])
        return {}


# =====================================================================
#  GOOGLE GEMINI
# =====================================================================

def _gemini(xabarlar, asboblar, korsatma, model):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=_muhit("GEMINI_API_KEY"))

    tarkib = []
    for x in xabarlar:
        if x["rol"] == "user" and x.get("asbob_natijalari"):
            tarkib.append(types.Content(role="user", parts=[
                types.Part.from_function_response(
                    name=n.get("nom") or "asbob",
                    response={"natija": n["natija"]})
                for n in x["asbob_natijalari"]]))
        elif x["rol"] == "assistant":
            qismlar = []
            if x.get("matn"):
                qismlar.append(types.Part.from_text(text=x["matn"]))
            for c in x.get("asbob_chaqiruvlari") or []:
                qism = types.Part.from_function_call(
                    name=c["nom"], args=c["kirish"])
                if c.get("imzo"):
                    # Muhrlangan fikr izi — o'zgartirmasdan qaytariladi
                    qism.thought_signature = base64.b64decode(c["imzo"])
                qismlar.append(qism)
            tarkib.append(types.Content(role="model", parts=qismlar or [
                types.Part.from_text(text=".")]))
        else:
            tarkib.append(types.Content(role="user", parts=[
                types.Part.from_text(text=x["matn"])]))

    javob = client.models.generate_content(
        model=model, contents=tarkib,
        config=types.GenerateContentConfig(
            system_instruction=korsatma,
            # 2.5+ modellarida «fikrlash» standart yoqilgan va u chiqish
            # byudjetini yeydi. Ustiga `korsat` asbobi butun jadvalni
            # JSON MATN qilib yuboradi — 50 qatorli qarzdorlar ro'yxati
            # osongina bir necha ming token bo'ladi. Byudjet kam bo'lsa
            # model matn o'rtasida uzilib qoladi va API buni
            # MALFORMED_FUNCTION_CALL deb qaytaradi (javob umuman
            # yo'qoladi). Shuning uchun chegara keng olinadi.
            max_output_tokens=32768,
            tools=[types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name=a["nom"], description=a["izoh"],
                    parameters=_gemini_sxema(a["sxema"]))
                for a in asboblar])]),
    )

    matn, chaqiruvlar, sabablar = "", [], []
    for nomzod in javob.candidates or []:
        sabab = str(getattr(nomzod, "finish_reason", "") or "")
        if sabab:
            sabablar.append(sabab)
        # `content` NONE bo'lishi mumkin: model fikrlash byudjetini
        # tugatsa (MAX_TOKENS), xavfsizlik filtri to'xtatsa yoki javob
        # bo'sh bo'lsa. Bu yerda tekshirilmasa `.parts` da
        # «NoneType has no attribute 'parts'» chiqadi va butun suhbat
        # 502 bilan yiqiladi — sababi esa foydalanuvchiga ko'rinmaydi.
        tarkib = getattr(nomzod, "content", None)
        for qism in (getattr(tarkib, "parts", None) or []):
            if getattr(qism, "text", None):
                matn += qism.text
            fc = getattr(qism, "function_call", None)
            if fc:
                # Gemini chaqiruv id bermaydi — o'zimiz yasaymiz, chunki
                # ichki ko'rinish natijani chaqiruvga id bilan bog'laydi.
                #
                # `thought_signature` — Gemini 3.x fikrlaydigan modellari
                # beradigan MUHRLANGAN fikr izi. Suhbat davom etganda u
                # AYNAN qaytarib yuborilishi shart, aks holda API
                # «Function call is missing a thought_signature» deb 400
                # qaytaradi va agent ikkinchi qadamda yiqiladi. Tarix
                # JSON bo'lib bazada saqlanadi, shuning uchun baytlar
                # base64 ga o'giriladi.
                imzo = getattr(qism, "thought_signature", None)
                chaqiruvlar.append({
                    "id": f"gem_{len(chaqiruvlar)}_{fc.name}",
                    "nom": fc.name, "kirish": dict(fc.args or {}),
                    "imzo": base64.b64encode(imzo).decode() if imzo else None})

    if not matn and not chaqiruvlar:
        # Nima uchun bo'sh qolgani AYTILADI. Jim qolinsa foydalanuvchi
        # «agent javob bermadi» deb o'ylab, sababini bilmaydi.
        sabab = ", ".join(sorted(set(sabablar))) or "noma'lum"
        if "SAFETY" in sabab or "PROHIBITED" in sabab:
            return {"matn": "", "chaqiruvlar": [], "rad_etildi": True}
        if "MALFORMED" in sabab or "MAX_TOKENS" in sabab:
            # Tiklanadigan hol — agent qisqaroq javob bilan qayta uradi
            raise JavobBuzildi(sabab)
        matn = (f"Model bo'sh javob qaytardi (sabab: {sabab}). "
                f"Savolni qisqaroq yoki aniqroq yozib ko'ring.")
    um = getattr(javob, "usage_metadata", None)
    return {"matn": matn, "chaqiruvlar": chaqiruvlar, "rad_etildi": False,
            "kirish_token": int(getattr(um, "prompt_token_count", 0) or 0),
            "chiqish_token": int(getattr(um, "candidates_token_count", 0) or 0)}


def _gemini_sxema(sxema: dict) -> dict:
    """Gemini `additionalProperties` ni qabul qilmaydi — tozalaymiz.

    Qolgan JSON Schema maydonlari (type/properties/required) bir xil.
    """
    tozalangan = {k: v for k, v in sxema.items() if k != "additionalProperties"}
    if "properties" in tozalangan:
        tozalangan["properties"] = {
            k: {kk: vv for kk, vv in v.items() if kk != "additionalProperties"}
            for k, v in tozalangan["properties"].items()}
    # Bo'sh `properties` ni Gemini rad etadi — maydonsiz asbob uchun
    # butun `parameters` ni tashlab yuboramiz.
    if not tozalangan.get("properties"):
        return {"type": "object", "properties": {}}
    return tozalangan


# Asosiy model ishlamasa ketma-ket sinaladigan zaxiralar. Tartib:
# sifatliroqdan arzonroqqa. Ro'yxatdagi model mavjud bo'lmasa ham
# xato emas — shunchaki o'tkazib yuboriladi.
ZAXIRA_MODELLAR = {
    "gemini": ["gemini-2.5-flash", "gemini-3.5-flash-lite",
               "gemini-flash-latest"],
    "openai": ["gpt-5-mini", "gpt-4.1-mini"],
    "anthropic": ["claude-sonnet-5", "claude-haiku-4-5-20251001"],
}


def _yoq_model(e: Exception) -> bool:
    """Model yo'q yoki shu kalitda kvotasi nol — kutish yordam bermaydi."""
    matn = str(e)
    return ("404" in matn and "model" in matn.lower()) or "limit: 0" in matn


MOSLASHTIRGICHLAR = {
    "anthropic": _anthropic,
    "openai": _openai,
    "gemini": _gemini,
}


# Vaqtinchalik xatolar: model band (503), so'rov chegarasi (429),
# tarmoq uzilishi (5xx). Bular O'TKINCHI — biroz kutib qayta urinilsa
# odatda o'tadi. Qayta urinmasak, foydalanuvchi 502 oladi va qaytadan
# yozishga majbur bo'ladi (jonli sinovda bepul tarifda aynan shunday
# bo'ldi: 4 ta so'rovdan 3 tasi shu sababdan yiqildi).
QAYTA_URINISH = 3
KUTISH_SEK = (2, 6, 14)     # har urinishdan keyin — o'sib boradigan pauza
OTKINCHI = ("429", "503", "500", "502", "504", "RESOURCE_EXHAUSTED",
            "UNAVAILABLE", "overloaded", "rate limit", "timeout")


def _otkinchimi(xato: Exception) -> bool:
    matn = str(xato)
    return any(belgi.lower() in matn.lower() for belgi in OTKINCHI)


class JavobBuzildi(RuntimeError):
    """Model javobi yarim yo'lda uzilib qoldi (buzuq asbob chaqiruvi).

    Gemini da bu `MALFORMED_FUNCTION_CALL` deb keladi va deyarli har
    doim BITTA sabab bilan: model juda uzun asbob argumentini yozmoqchi
    bo'ladi (masalan 50 qatorli jadvalning JSON matni) va chiqish
    chegarasiga urilib, JSON yarmida to'xtaydi.

    Bu XATO EMAS, TIKLANADIGAN hol: agentga qisqaroq javob berishni
    aytib, qadamni qayta yurgizsa bo'ladi.
    """


class LLMBand(RuntimeError):
    """Provayder vaqtincha javob bermayapti — foydalanuvchiga tushunarli xabar."""


def _zanjir() -> list[tuple[str, str]]:
    """Sinaladigan (provayder, model) juftliklari — to'liq ro'yxat.

    Avval birinchi provayderning hamma modellari, keyin ikkinchisiniki
    va hokazo. Shu bilan «hamma kalitlar ulangan» degani amalda ham
    to'g'ri bo'ladi: birinchisi tugasa ikkinchisi javob beradi.
    """
    natija = []
    for p in ulangan_provayderlar():
        for md in _modellar_zanjiri(p):
            natija.append((p, md))
    return natija


def _modellar_zanjiri(provayder: str) -> list[str]:
    """Qaysi modellarni ketma-ket sinash: asosiy, keyin yengilroqlari.

    NEGA KERAK: mijoz o'z kalitini qo'yadi va uning tarifi noma'lum.
    Bepul Gemini kalitida `gemini-3.5-flash` uchun kvota NOL bo'lishi
    mumkin, `gemini-2.5-flash` esa ishlaydi — buni oldindan bilib
    bo'lmaydi. Kvota tugagan yoki model yo'q bo'lsa keyingisiga
    o'tamiz, aks holda foydalanuvchi «AI ishlamayapti» degan xulosaga
    keladi, holbuki kalit joyida.

    `LLM_MODEL` aniq berilgan bo'lsa u BIRINCHI turadi — foydalanuvchi
    tanlovi hurmat qilinadi, lekin u ishlamasa ham yo'l berkilmaydi.
    """
    # `LLM_MODEL` FAQAT o'z provayderiga tegishli: «gemini-2.5-flash» ni
    # Anthropic ga yuborib bo'lmaydi. Shuning uchun u tanlangan
    # provayderdagina birinchi o'ringa qo'yiladi.
    tanlangan = (_muhit("LLM_MODEL")
                 if _muhit("LLM_PROVAYDER").lower() in ("", provayder) else "")
    zanjir = [tanlangan] if tanlangan else []
    zanjir.append(PROVAYDERLAR[provayder][1])
    zanjir.extend(ZAXIRA_MODELLAR.get(provayder, []))
    korilgan, natija = set(), []
    for x in zanjir:
        if x and x not in korilgan:
            korilgan.add(x)
            natija.append(x)
    return natija


def javob_ol(xabarlar: list[dict], asboblar: list[dict],
             korsatma: str, qotirilgan_model: str | None = None) -> dict:
    """Provayderdan javob oladi. Agent kodi faqat shuni chaqiradi.

    `qotirilgan_model` — suhbat BOSHLANGAN model. Halqaning ikkinchi
    qadamida boshqa modelga o'tib bo'lmaydi: Gemini 3.x asbob
    chaqiruviga «thought_signature» muhrini qo'yadi va uni FAQAT o'sha
    model qabul qiladi. Model almashsa API «Function call is missing a
    thought_signature» deb 400 qaytaradi va agent o'rtada yiqiladi.
    Shuning uchun zaxira modelga o'tish faqat BIRINCHI qadamda mumkin.
    """
    tayyor, izoh = tayyormi()
    if not tayyor:
        raise RuntimeError(izoh)

    oxirgi = None
    if qotirilgan_model:
        # Suhbat o'rtasi — model ham, provayder ham o'zgarmaydi
        zanjir = [(joriy_provayder(), qotirilgan_model)]
    else:
        zanjir = _zanjir()
    for provayder, model in zanjir:
        for urinish in range(QAYTA_URINISH):
            try:
                natija = MOSLASHTIRGICHLAR[provayder](
                    xabarlar, asboblar, korsatma, model)
                natija["provayder"], natija["model"] = provayder, model
                return natija
            except Exception as e:                            # noqa: BLE001
                oxirgi = e
                if _yoq_model(e):
                    # Bu model umuman yo'q yoki kvotasi nol — kutish
                    # foyda bermaydi, darhol keyingisiga o'tamiz.
                    log.warning("«%s» ishlamadi (%s), keyingi modelga o'tamiz",
                                model, str(e)[:90])
                    break
                if not _otkinchimi(e) or urinish == QAYTA_URINISH - 1:
                    break
                kut = KUTISH_SEK[min(urinish, len(KUTISH_SEK) - 1)]
                log.warning("LLM o'tkinchi xato (%s), %s sek kutib qayta urinamiz: %s",
                            urinish + 1, kut, str(e)[:120])
                time.sleep(kut)
        else:
            continue
        if oxirgi is not None and not (_yoq_model(oxirgi) or _otkinchimi(oxirgi)):
            break

    if oxirgi is not None and _otkinchimi(oxirgi):
        # Xom API matnini foydalanuvchiga ko'rsatmaymiz — u inglizcha va
        # texnik. Sababi logda qoladi.
        log.error("LLM band: %s", str(oxirgi)[:300])
        raise LLMBand(
            "Sun'iy intellekt xizmati hozir band yoki so'rov chegarasi "
            "tugagan. Bir necha daqiqadan so'ng qayta urinib ko'ring.")
    raise oxirgi if oxirgi else RuntimeError("noma'lum xato")
