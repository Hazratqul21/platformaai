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
import json
import logging
import os

log = logging.getLogger("gofra.llm")

# Provayder -> (muhit o'zgaruvchisi, standart model)
PROVAYDERLAR = {
    "anthropic": ("ANTHROPIC_API_KEY", "claude-opus-5"),
    "openai": ("OPENAI_API_KEY", "gpt-5"),
    "gemini": ("GEMINI_API_KEY", "gemini-2.5-pro"),
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


def tayyormi() -> tuple[bool, str]:
    """(tayyormi, izoh). Izoh foydalanuvchiga ko'rsatiladi."""
    p = joriy_provayder()
    kalit_nomi = PROVAYDERLAR[p][0]
    if not _muhit(kalit_nomi):
        return False, f"{kalit_nomi} qo'yilmagan — .env ga yozing"
    return True, f"{p} · {joriy_model()}"


def holat() -> dict:
    """Hamma provayderlar holati — sozlamalar ekrani uchun."""
    tayyor, izoh = tayyormi()
    return {
        "tayyor": tayyor, "izoh": izoh,
        "provayder": joriy_provayder(), "model": joriy_model(),
        "provayderlar": [
            {"nom": nom, "kalit": kalit_nomi,
             "kalit_bor": bool(_muhit(kalit_nomi)), "standart_model": model}
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
    return {
        "matn": "".join(b.text for b in javob.content if b.type == "text"),
        "chaqiruvlar": [{"id": b.id, "nom": b.name, "kirish": b.input or {}}
                        for b in javob.content if b.type == "tool_use"],
        "rad_etildi": False,
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
                qismlar.append(types.Part.from_function_call(
                    name=c["nom"], args=c["kirish"]))
            tarkib.append(types.Content(role="model", parts=qismlar or [
                types.Part.from_text(text=".")]))
        else:
            tarkib.append(types.Content(role="user", parts=[
                types.Part.from_text(text=x["matn"])]))

    javob = client.models.generate_content(
        model=model, contents=tarkib,
        config=types.GenerateContentConfig(
            system_instruction=korsatma,
            tools=[types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name=a["nom"], description=a["izoh"],
                    parameters=_gemini_sxema(a["sxema"]))
                for a in asboblar])]),
    )

    matn, chaqiruvlar = "", []
    for nomzod in javob.candidates or []:
        for qism in (nomzod.content.parts or []):
            if getattr(qism, "text", None):
                matn += qism.text
            fc = getattr(qism, "function_call", None)
            if fc:
                # Gemini chaqiruv id bermaydi — o'zimiz yasaymiz, chunki
                # ichki ko'rinish natijani chaqiruvga id bilan bog'laydi.
                chaqiruvlar.append({
                    "id": f"gem_{len(chaqiruvlar)}_{fc.name}",
                    "nom": fc.name, "kirish": dict(fc.args or {})})
    return {"matn": matn, "chaqiruvlar": chaqiruvlar, "rad_etildi": False}


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


MOSLASHTIRGICHLAR = {
    "anthropic": _anthropic,
    "openai": _openai,
    "gemini": _gemini,
}


def javob_ol(xabarlar: list[dict], asboblar: list[dict],
             korsatma: str) -> dict:
    """Provayderdan javob oladi. Agent kodi faqat shuni chaqiradi."""
    provayder = joriy_provayder()
    model = joriy_model()
    tayyor, izoh = tayyormi()
    if not tayyor:
        raise RuntimeError(izoh)
    natija = MOSLASHTIRGICHLAR[provayder](xabarlar, asboblar, korsatma, model)
    natija["provayder"], natija["model"] = provayder, model
    return natija
