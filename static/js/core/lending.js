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
const ROYXAT_SOHALAR = [
  {kalit:'', nom:'— sohani keyin tanlayman —'},
  {kalit:'non', nom:"Non zavodi"},
  {kalit:'mebel', nom:"Mebel sexi"},
  {kalit:'karton', nom:"Karton / gofra qutilar"},
  {kalit:'beton', nom:"Beton / temir-beton"},
  {kalit:'tikuvchilik', nom:"Tikuvchilik sexi"},
  {kalit:'poyabzal', nom:"Poyabzal ishlab chiqarish"},
  {kalit:'sut', nom:"Sut mahsulotlari"},
  {kalit:'kolbasa', nom:"Go'sht mahsulotlari"},
  {kalit:'kimyo', nom:"Maishiy kimyo"},
  {kalit:'avto_servis', nom:"Avto servis"},
  {kalit:'chakana_dokon', nom:"Chakana do'kon"},
  {kalit:'ulgurji_savdo', nom:"Ulgurji savdo (distribyutor)"},
  {kalit:'gisht', nom:"G'isht / qurilish materiallari"},
  {kalit:'kabel', nom:"Kabel / elektrotexnika"},
  {kalit:'metall', nom:"Metall konstruksiya"},
  {kalit:'montaj', nom:"Qurilish-montaj ishlari"},
  {kalit:'plastik_deraza', nom:"Plastik deraza / eshik"},
  {kalit:'yogoch_eshik', nom:"Yog'och eshik / deraza"},
  {kalit:'poligrafiya', nom:"Poligrafiya / bosmaxona"},
  {kalit:'reklama', nom:"Reklama agentligi"},
  {kalit:'logistika', nom:"Transport / logistika"},
  {kalit:'texnika_tamiri', nom:"Maishiy texnika ta'miri"},
];

function royxatSohaOptions(){
  return ROYXAT_SOHALAR.map(s =>
    `<option value="${s.kalit}">${s.nom.replace(/</g,'&lt;')}</option>`).join('');
}

/** Subdomen kodi: kichik harf, raqam, tire. Nomdan taklif qilinadi. */
function royxatKodTozala(v){
  return (v||'').toLowerCase()
    .replace(/[^a-z0-9-]/g,'-').replace(/-+/g,'-').replace(/^-|-$/g,'').slice(0,40);
}

function lendingRoyxat(){
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

  <label class="fl">Soha</label>
  <select class="fld" id="rx_soha">${royxatSohaOptions()}</select>

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
        natija.innerHTML=`<div style="padding:12px;border-radius:12px;
          background:linear-gradient(120deg,rgba(26,158,99,.12),rgba(26,158,99,.04));
          border:1px solid rgba(26,158,99,.25);font-size:13px">
          <b style="color:var(--ok)">✓ Tayyor!</b><br>
          Manzilingiz: <b>${esc(manzil)}</b><br>
          <span class="muted">Login: admin · parol: siz kiritgan parol</span></div>`;
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
