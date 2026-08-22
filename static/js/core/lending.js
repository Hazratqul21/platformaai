/* ================= LENDING — kirishdagi tanishtiruv sahifasi =========
   Nega kerak: ilgari birinchi ko'ringan narsa login oynasi edi. Login
   oynasi «bu nima?» degan savolga javob bermaydi — u faqat allaqachon
   biladigan odam uchun. Platforma ko'p mijozli bo'lgach, sahifaga
   birinchi kelgan odam nima taklif qilinayotganini ko'rishi kerak.

   Kirgan foydalanuvchi buni umuman ko'rmaydi (tokeni bor -> to'g'ri
   tizimga o'tadi).
   ==================================================================== */

/* Tayyor sohalar — app/profiles/*.json dagi nomlar. Ro'yxat qo'lda,
   chunki lending login BO'LMAGAN holatda ochiladi va API yopiq. */
const LND_SOHALAR = [
  "Non zavodi", "Mebel sexi", "Karton / gofra qutilar", "Beton / temir-beton",
  "Tikuvchilik sexi", "Poyabzal ishlab chiqarish", "Sut mahsulotlari",
  "Go'sht mahsulotlari", "Maishiy kimyo", "Avto servis", "Chakana do'kon",
  "Ulgurji savdo (distribyutor)", "G'isht / qurilish materiallari",
  "Kabel / elektrotexnika", "Metall konstruksiya", "Qurilish-montaj ishlari",
  "Plastik deraza / eshik", "Yog'och eshik / deraza", "Poligrafiya / bosmaxona",
  "Reklama agentligi", "Transport / logistika", "Maishiy texnika ta'miri"
];

function lendingChiplar(){
  const box = document.getElementById('lndChips');
  if(!box) return;
  box.innerHTML = '';
  LND_SOHALAR.forEach(nom => {
    const s = document.createElement('span');
    s.className = 'lnd-chip';
    s.textContent = nom;          // matn har doim textContent bilan
    box.appendChild(s);
  });
  const ai = document.createElement('span');
  ai.className = 'lnd-chip ai';
  ai.textContent = '+ sizniki — AI yasab beradi';
  box.appendChild(ai);
}

/** Lending -> login oynasi. */
function lendingKirish(){
  document.getElementById('lending').classList.remove('on');
  document.getElementById('loginScreen').style.display = 'flex';
  const lg = document.getElementById('lg');
  if(lg) lg.focus();
}

/** Login -> lending (orqaga). */
function lendingOrqaga(){
  document.getElementById('loginScreen').style.display = 'none';
  document.getElementById('lending').classList.add('on');
  window.scrollTo(0, 0);
}


function lendingBoshla(){
  lendingChiplar();
  document.getElementById('lending').classList.add('on');
  document.getElementById('loginScreen').style.display = 'none';
}

/* ================= RO'YXATDAN O'TISH FORMASI ====================
   Lending'dagi «Ro'yxatdan o'tish» tugmasi shuni ochadi. Backend
   tayyor (POST /api/platforma/royxat), lekin u FAQAT ijarachilik
   rejimida (IJARACHILIK=1 + baza shabloni) to'liq ishlaydi. Aks
   holda forma ochiladi va tekshiradi, lekin baza yaratilmaydi va
   holat «xato» bo'ladi — bu halol ko'rsatiladi.
   ==================================================================== */
/* YO'NALISHLAR RO'YXATI BACKENDDAN KELADI.
   Ilgari bu yerda qo'lda yozilgan massiv turardi. Yangi profil
   qo'shilganda uni bu yerda ham yozish esdan chiqardi va yo'nalish
   ro'yxatda umuman ko'rinmasdi — ya'ni yozilgan soha mijozga yetib
   bormasdi. Endi manba bitta: `app/profiles/*.json`. */
let ROYXAT_SOHALAR = [];

async function royxatSohalarniOl(){
  if(ROYXAT_SOHALAR.length) return ROYXAT_SOHALAR;
  try{
    const d = await (await fetch(API+'/api/platforma/sohalar')).json();
    ROYXAT_SOHALAR = d.sohalar || [];
  }catch(e){ ROYXAT_SOHALAR = []; }
  return ROYXAT_SOHALAR;
}

function royxatSohaOptions(filtr){
  const q = (filtr||'').trim().toLowerCase();
  const mos = q
    ? ROYXAT_SOHALAR.filter(s =>
        (s.nom+' '+(s.izoh||'')).toLowerCase().includes(q))
    : ROYXAT_SOHALAR;
  const bosh = `<option value="">— sohani keyin tanlayman —</option>`;
  if(!mos.length) return bosh +
    `<option value="" disabled>«${esc(q)}» bo'yicha topilmadi</option>`;
  return bosh + mos.map(s =>
    `<option value="${esc(s.kalit)}">${esc(s.nom)}</option>`).join('');
}

/* 29 ta yo'nalish oddiy ro'yxatda ko'p — qidiruv maydonchasi bor.
   Tanlangani filtr o'zgarganda ham saqlanadi. */
function royxatSohaFiltr(){
  const sel = document.getElementById('rx_soha');
  const tanlangan = sel.value;
  sel.innerHTML = royxatSohaOptions(f('rx_soha_qidir'));
  if([...sel.options].some(o=>o.value===tanlangan)) sel.value = tanlangan;
  royxatSohaIzoh();
}

function royxatSohaIzoh(){
  const k = f('rx_soha');
  const s = ROYXAT_SOHALAR.find(x=>x.kalit===k);
  const el = document.getElementById('rx_soha_izoh');
  if(!el) return;
  el.textContent = s && s.izoh ? s.izoh
    : 'Tanlamasangiz ham bo\'ladi — keyin AI yordamchi sozlab beradi.';
}

/** Subdomen kodi: kichik harf, raqam, tire. Nomdan taklif qilinadi. */
function royxatKodTozala(v){
  return (v||'').toLowerCase()
    .replace(/[^a-z0-9-]/g,'-').replace(/-+/g,'-').replace(/^-|-$/g,'').slice(0,40);
}

async function lendingRoyxat(){
  await royxatSohalarniOl();
  modal(`<h2 class="sec">Ro'yxatdan o'tish</h2>
  <div class="muted" style="font-size:12px;margin:2px 0 14px;line-height:1.5">
    Akkaunt yaratasiz va o'z manzilingizga (masalan
    <b>mebelsex.innasoft.uz</b>) ega bo'lasiz. Tizim bir necha soniyada
    tayyorlanadi.</div>

  <label class="fl">Korxona nomi</label>
  <input class="fld" id="rx_nom" placeholder="Mebel Sex MCHJ"
    oninput="if(!document.getElementById('rx_kod').dataset.qol){document.getElementById('rx_kod').value=royxatKodTozala(this.value)}"/>

  <label class="fl">Manzil (subdomen)</label>
  <div class="row" style="align-items:center;gap:6px">
    <input class="fld" id="rx_kod" placeholder="mebelsex" style="flex:1"
      oninput="this.dataset.qol=1;this.value=royxatKodTozala(this.value)"/>
    <span class="muted" style="font-size:12px">.innasoft.uz</span>
  </div>

  <label class="fl">Faoliyat yo'nalishi</label>
  <input class="fld" id="rx_soha_qidir" placeholder="qidirish: ijara, elektr, non…"
    style="margin-bottom:6px" oninput="royxatSohaFiltr()"/>
  <select class="fld" id="rx_soha" onchange="royxatSohaIzoh()">${royxatSohaOptions()}</select>
  <div class="muted" id="rx_soha_izoh" style="font-size:11.5px;margin-top:4px">
    Tanlamasangiz ham bo'ladi — keyin AI yordamchi sozlab beradi.</div>

  <label class="fl">Login (telefon yoki email)</label>
  <input class="fld" id="rx_login" placeholder="+998 90 123 45 67" autocomplete="username"/>

  <label class="fl">Parol (kamida 8 belgi)</label>
  <input class="fld" id="rx_parol" type="password" autocomplete="new-password"/>

  <div id="rx_natija" style="margin-top:10px"></div>

  <div class="row" style="margin-top:16px;justify-content:space-between">
    <button class="btn ghost" onclick="closeModal()">Bekor</button>
    <button class="btn pri" id="rx_btn" onclick="royxatYubor()">Yaratish</button>
  </div>`, false);
}

async function royxatYubor(){
  const nom=f('rx_nom').trim(), kod=f('rx_kod').trim(),
        login=f('rx_login').trim(), parol=f('rx_parol'), soha=f('rx_soha');
  if(nom.length<2) return toast('w','alertic','Nom','Firma nomini kiriting');
  if(kod.length<3) return toast('w','alertic','Manzil','Kamida 3 belgi, harf bilan boshlansin');
  if(login.length<5) return toast('w','alertic','Login','Telefon yoki email kiriting');
  if(parol.length<8) return toast('w','alertic','Parol','Kamida 8 belgi');

  const btn=document.getElementById('rx_btn');
  btn.disabled=true; btn.textContent='Yaratilmoqda…';
  const natija=document.getElementById('rx_natija');
  natija.innerHTML='<div class="muted" style="font-size:12px">Baza tayyorlanmoqda…</div>';

  try{
    const r=await fetch(API+'/api/platforma/royxat',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({login,parol,akkaunt_kod:kod,akkaunt_nom:nom,soha:soha||null})});
    if(!r.ok){const e=await r.json();throw new Error(e.detail||'Xatolik');}
    const d=await r.json();
    // Baza fon vazifasida tayyorlanadi — holatni kuzatamiz.
    await royxatHolatKuzat(kod, d.manzil, natija, btn);
  }catch(e){
    natija.innerHTML=`<div class="lnd-chip" style="color:var(--danger)">${esc(e.message)}</div>`;
    btn.disabled=false; btn.textContent='Yaratish';
  }
}

async function royxatHolatKuzat(kod, manzil, natija, btn){
  for(let i=0;i<15;i++){
    await new Promise(r=>setTimeout(r,700));
    try{
      const h=await (await fetch(API+`/api/platforma/holat/${kod}`)).json();
      if(h.tayyorlik==='tayyor'){
        // AI BILAN SOZLASH — shu yerdan boshlanadi.
        // Yo'nalish tanlangan bo'lsa ham tizim uni aynan mijozning
        // ishiga moslashi kerak (qaysi maydonlar, qanday narx, qaysi
        // bo'limlar). «Sozlash yordamchisi» aynan shu ish uchun bor,
        // lekin unga yo'l yo'q edi — odam kirib, uni o'zi topishi
        // kerak edi. Endi ro'yxatdan o'tishning oxiri to'g'ridan
        // to'g'ri o'sha suhbatga olib boradi.
        const sozlaUrl = manzil + '/?sozlash=1';
        natija.innerHTML=`<div style="padding:12px;border-radius:12px;
          background:linear-gradient(120deg,rgba(26,158,99,.12),rgba(26,158,99,.04));
          border:1px solid rgba(26,158,99,.25);font-size:13px">
          <b style="color:var(--ok)">✓ Tayyor!</b><br>
          Manzilingiz: <b>${esc(manzil)}</b><br>
          <span class="muted">Login: admin · parol: siz kiritgan parol</span>
          <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">
            <a class="btn pri" href="${esc(sozlaUrl)}">AI bilan sozlashni boshlash</a>
            <a class="btn ghost" href="${esc(manzil)}">Shunchaki kirish</a>
          </div>
          <div class="muted" style="margin-top:8px;font-size:11.5px">
            AI yordamchi biznesingizni so'raydi va tizimni shunga
            moslaydi — maydonlar, narx hisobi, kerakli bo'limlar.</div>
        </div>`;
        btn.textContent='Tayyor'; return;
      }
      if(h.tayyorlik==='xato'){
        natija.innerHTML=`<div class="lnd-chip" style="color:var(--danger)">
          Tayyorlanmadi: ${esc(h.izoh||'nomaʼlum xato')}</div>`;
        btn.disabled=false; btn.textContent='Qayta urinish'; return;
      }
    }catch(e){/* keyingi urinish */}
  }
  natija.innerHTML='<div class="muted" style="font-size:12px">Tayyorlash kutilyapti — birozdan keyin manzilga kiring</div>';
  btn.disabled=false; btn.textContent='Yaratish';
}
