/* =====================================================================
   RO'YXATDAN O'TISH SEHRGARI — uch qadam

     1. KORXONA   INN -> ma'lumot o'zi to'ladi (topilmasa qo'lda)
     2. YO'NALISH ro'yxatdan tanlash YOKI o'z so'zi bilan yozish
     3. SUHBAT    AI bilan gaplashib tizimni yig'ish

   NEGA SEHRGAR, BITTA UZUN FORMA EMAS: uzun formani odam ko'rib
   qo'rqadi va tashlab ketadi. Uch qisqa qadam har birida bitta savol
   beradi va har qadamda «ish bo'lyapti» hissi qoladi.

   MUHIM QOIDA — YO'L BERKILMAYDI. INN topilmasa, xizmat javob
   bermasa, yo'nalish ro'yxatda bo'lmasa — hech qaysisi to'siq emas.
   Qizil xato chiqmaydi, odam davom etadi.
   ===================================================================== */

const RX = {           // sehrgar holati
  qadam: 1,
  inn: '', korxona: '', manzil: '', rahbar: '',
  ism: '', familiya: '', telefon: '',
  kod: '', login: '', parol: '',
  soha: '', soha_matni: '',
  qqs: false,
};

function rxKodTozala(v){
  return (v||'').toLowerCase()
    .replace(/[^a-z0-9-]/g,'-').replace(/-+/g,'-').replace(/^-|-$/g,'').slice(0,40);
}

/* Kirill/lotin nomdan subdomen taklif qiladi. «Мебель Сех МЧЖ» ->
   «mebel-sex». Odam baribir o'zgartira oladi. */
const RX_TRANSLIT = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'j',
 'з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
 'с':'s','т':'t','у':'u','ф':'f','х':'x','ц':'ts','ч':'ch','ш':'sh','щ':'sh','ъ':'',
 'ы':'i','ь':'','э':'e','ю':'yu','я':'ya','ў':'o','қ':'q','ғ':'g','ҳ':'h'};
function rxKodTaklif(nom){
  const t = (nom||'').toLowerCase().split('')
    .map(ch => RX_TRANSLIT[ch] !== undefined ? RX_TRANSLIT[ch] : ch).join('');
  return rxKodTozala(t.replace(/\b(mchj|ooo|mas|xk|yatt|ip)\b/g,''));
}

function rxOch(){
  RX.qadam = 1;
  royxatSohalarniOl();
  rxChiz();
}

function rxChiz(){
  const q = RX.qadam;
  modal(`
  <div class="rx-head">
    <h2 class="sec">Ro'yxatdan o'tish</h2>
    <div class="rx-qadamlar">
      ${[1,2,3].map(i=>`<span class="rx-nuqta ${i<q?'otdi':''} ${i===q?'joriy':''}"></span>`).join('')}
      <span class="rx-qadam-matn">${q}/3</span>
    </div>
  </div>
  ${q===1 ? rxQadam1() : q===2 ? rxQadam2() : rxQadam3()}`, false);
  if(q===1) setTimeout(()=>{const e=document.getElementById('rx_inn'); if(e) e.focus();},80);
  if(q===2) setTimeout(rxSohaChiz,0);
}

/* ---------------------------------------------------------------- 1 */
function rxQadam1(){
  return `
  <div class="rx-izoh">Korxona INN raqamini kiriting — ma'lumotlar o'zi
    to'ladi. Topilmasa o'zingiz yozasiz, muammo emas.</div>

  <label class="fl">INN (9 raqam)</label>
  <div class="rx-inn-qator">
    <input class="fld" id="rx_inn" inputmode="numeric" maxlength="9"
      placeholder="123456789" value="${esc(RX.inn)}"
      oninput="this.value=this.value.replace(/\\D/g,'');rxInnHolat()"/>
    <button class="btn" id="rx_inn_btn" onclick="rxInnQidir()">Topish</button>
  </div>
  <div id="rx_inn_natija" class="rx-natija"></div>

  <label class="fl">Korxona nomi</label>
  <input class="fld" id="rx_korxona" placeholder="Mebel Sex MCHJ"
    value="${esc(RX.korxona)}"
    oninput="if(!document.getElementById('rx_kod').dataset.qol){
      document.getElementById('rx_kod').value=rxKodTaklif(this.value)}"/>

  <div class="rx-ikki">
    <div><label class="fl">Ism</label>
      <input class="fld" id="rx_ism" placeholder="Aziz" value="${esc(RX.ism)}"/></div>
    <div><label class="fl">Familiya</label>
      <input class="fld" id="rx_familiya" placeholder="Karimov" value="${esc(RX.familiya)}"/></div>
  </div>

  <label class="fl">Telefon</label>
  <input class="fld" id="rx_telefon" placeholder="+998 90 123 45 67"
    value="${esc(RX.telefon)}" autocomplete="tel"/>

  <label class="fl">Manzil (subdomen)</label>
  <div class="rx-kod-qator">
    <input class="fld" id="rx_kod" placeholder="mebelsex" value="${esc(RX.kod)}"
      oninput="this.dataset.qol=1;this.value=rxKodTozala(this.value)"/>
    <span class="muted">.innasoft.uz</span>
  </div>

  <div class="rx-ikki">
    <div><label class="fl">Login (telefon yoki email)</label>
      <input class="fld" id="rx_login" placeholder="+998901234567"
        value="${esc(RX.login)}" autocomplete="username"/></div>
    <div><label class="fl">Parol (8+ belgi)</label>
      <input class="fld" id="rx_parol" type="password"
        value="${esc(RX.parol)}" autocomplete="new-password"/></div>
  </div>

  <label class="rx-qqs">
    <input type="checkbox" id="rx_qqs" ${RX.qqs?'checked':''}/>
    <span>QQS to'lovchimiz</span></label>

  <div class="rx-tugmalar">
    <button class="btn ghost" onclick="closeModal()">Bekor</button>
    <button class="btn pri" onclick="rxKeyingi1()">Keyingi →</button>
  </div>`;
}

function rxInnHolat(){
  const n=document.getElementById('rx_inn_natija');
  if(n) n.innerHTML='';
}

async function rxInnQidir(){
  const inn=f('rx_inn').trim();
  const n=document.getElementById('rx_inn_natija');
  const b=document.getElementById('rx_inn_btn');
  if(inn.length!==9){
    // Ogohlantirish — XATO EMAS. Rangi ham neytral.
    n.innerHTML=`<div class="rx-eslatma">INN 9 raqamdan iborat bo'ladi</div>`;
    return;
  }
  b.disabled=true; b.textContent='Qidirilmoqda…';
  n.innerHTML=`<div class="rx-eslatma">Qidirilmoqda…</div>`;
  try{
    const d=await (await fetch(API+'/api/platforma/inn/'+encodeURIComponent(inn))).json();
    if(d.topildi){
      RX.korxona=d.nom||''; RX.manzil=d.manzil||''; RX.rahbar=d.rahbar||'';
      const k=document.getElementById('rx_korxona');
      k.value=RX.korxona;
      const kod=document.getElementById('rx_kod');
      if(!kod.dataset.qol) kod.value=rxKodTaklif(RX.korxona);
      n.innerHTML=`<div class="rx-topildi">
        <b>${esc(d.nom)}</b>
        ${d.manzil?`<div class="muted">${esc(d.manzil)}</div>`:''}
        ${d.rahbar?`<div class="muted">Rahbar: ${esc(d.rahbar)}</div>`:''}</div>`;
    }else{
      // Topilmadi — QIZIL EMAS. Bu oddiy holat.
      n.innerHTML=`<div class="rx-eslatma">${esc(d.sabab||'Topilmadi')}</div>`;
      document.getElementById('rx_korxona').focus();
    }
  }catch(e){
    n.innerHTML=`<div class="rx-eslatma">Qidiruv ishlamadi — nomini o'zingiz yozing</div>`;
  }
  b.disabled=false; b.textContent='Topish';
}

function rxKeyingi1(){
  RX.inn=f('rx_inn').trim(); RX.korxona=f('rx_korxona').trim();
  RX.ism=f('rx_ism').trim(); RX.familiya=f('rx_familiya').trim();
  RX.telefon=f('rx_telefon').trim(); RX.kod=f('rx_kod').trim();
  RX.login=f('rx_login').trim(); RX.parol=f('rx_parol');
  RX.qqs=document.getElementById('rx_qqs').checked;
  if(RX.korxona.length<2) return toast('w','alertic','Korxona','Korxona nomini kiriting');
  if(RX.kod.length<3)     return toast('w','alertic','Manzil','Kamida 3 belgi');
  if(RX.login.length<5)   return toast('w','alertic','Login','Telefon yoki email kiriting');
  if(RX.parol.length<8)   return toast('w','alertic','Parol','Kamida 8 belgi');
  RX.qadam=2; rxChiz();
}

/* ---------------------------------------------------------------- 2 */
function rxQadam2(){
  return `
  <div class="rx-izoh">Nima ish qilasiz? Ro'yxatdan tanlang — yoki
    ro'yxatda bo'lmasa, o'z so'zingiz bilan yozing. AI uni qabul qiladi
    va tizimni shunga yig'adi.</div>

  <input class="fld" id="rx_soha_qidir" placeholder="qidirish: ijara, elektr, non…"
    oninput="rxSohaChiz()" value=""/>
  <div class="rx-sohalar" id="rx_sohalar"></div>

  <label class="fl">Ro'yxatda yo'qmi? O'zingiz yozing</label>
  <input class="fld" id="rx_soha_matni" value="${esc(RX.soha_matni)}"
    placeholder="masalan: gilam yuvish xizmati"
    oninput="rxSohaMatn()"/>
  <div class="muted rx-kichik" id="rx_soha_holat"></div>

  <div class="rx-tugmalar">
    <button class="btn ghost" onclick="RX.qadam=1;rxChiz()">← Orqaga</button>
    <button class="btn pri" onclick="rxKeyingi2()">Keyingi →</button>
  </div>`;
}

function rxSohaChiz(){
  const q=(f('rx_soha_qidir')||'').trim().toLowerCase();
  const mos=q?ROYXAT_SOHALAR.filter(s=>(s.nom+' '+(s.izoh||'')).toLowerCase().includes(q))
             :ROYXAT_SOHALAR;
  const el=document.getElementById('rx_sohalar');
  if(!el) return;
  if(!mos.length){
    el.innerHTML=`<div class="rx-bosh">«${esc(q)}» topilmadi — pastda o'zingiz yozing</div>`;
    return;
  }
  el.innerHTML=mos.map(s=>`
    <button class="rx-soha ${RX.soha===s.kalit?'tanlangan':''}"
      onclick="rxSohaTanla('${esc(s.kalit)}')" title="${esc(s.izoh||'')}">
      ${esc(s.nom)}</button>`).join('');
}

function rxSohaTanla(kalit){
  RX.soha = (RX.soha===kalit) ? '' : kalit;
  if(RX.soha){ RX.soha_matni=''; const e=document.getElementById('rx_soha_matni'); if(e) e.value=''; }
  rxSohaChiz(); rxSohaHolat();
}

function rxSohaMatn(){
  RX.soha_matni=f('rx_soha_matni').trim();
  if(RX.soha_matni){ RX.soha=''; rxSohaChiz(); }
  rxSohaHolat();
}

function rxSohaHolat(){
  const el=document.getElementById('rx_soha_holat'); if(!el) return;
  if(RX.soha){
    const s=ROYXAT_SOHALAR.find(x=>x.kalit===RX.soha);
    el.textContent = s ? ('Tanlandi: '+s.nom+'. Tayyor shablon ishlatiladi.') : '';
  }else if(RX.soha_matni){
    el.textContent = '«'+RX.soha_matni+'» — tayyor shablon yo\'q, AI suhbatda yasab beradi.';
  }else{
    el.textContent = 'Tanlamasangiz ham bo\'ladi — AI suhbatda aniqlaymiz.';
  }
}

function rxKeyingi2(){ RX.qadam=3; rxChiz(); }

/* ---------------------------------------------------------------- 3 */
function rxQadam3(){
  const nima = RX.soha
    ? (ROYXAT_SOHALAR.find(x=>x.kalit===RX.soha)||{}).nom
    : (RX.soha_matni || 'yo\'nalish keyin aniqlanadi');
  return `
  <div class="rx-xulosa">
    <div class="rx-xulosa-qator"><span>Korxona</span><b>${esc(RX.korxona)}</b></div>
    ${RX.inn?`<div class="rx-xulosa-qator"><span>INN</span><b>${esc(RX.inn)}</b></div>`:''}
    <div class="rx-xulosa-qator"><span>Manzil</span><b>${esc(RX.kod)}.innasoft.uz</b></div>
    <div class="rx-xulosa-qator"><span>Yo'nalish</span><b>${esc(nima)}</b></div>
  </div>

  <div class="rx-izoh" style="margin-top:12px">Keyingi qadamda AI bilan
    suhbat ochiladi. Ikki rejim bor:</div>

  <div class="rx-rejimlar">
    <button class="rx-rejim ${RX.rejim!=='plan'?'tanlangan':''}" onclick="rxRejim('agent')">
      <span class="rx-rejim-nom">⚡ Agent</span>
      <span class="rx-rejim-izoh">Darrov qilishga kirishadi</span></button>
    <button class="rx-rejim ${RX.rejim==='plan'?'tanlangan':''}" onclick="rxRejim('plan')">
      <span class="rx-rejim-nom">◎ Plan</span>
      <span class="rx-rejim-izoh">Avval reja tuzadi, siz tasdiqlaysiz</span></button>
  </div>

  <div id="rx_natija" class="rx-natija"></div>

  <div class="rx-tugmalar">
    <button class="btn ghost" onclick="RX.qadam=2;rxChiz()">← Orqaga</button>
    <button class="btn pri" id="rx_btn" onclick="rxYubor()">Tizimni yaratish</button>
  </div>`;
}

function rxRejim(r){ RX.rejim=r; rxChiz(); }

async function rxYubor(){
  const btn=document.getElementById('rx_btn');
  const natija=document.getElementById('rx_natija');
  btn.disabled=true; btn.textContent='Yaratilmoqda…';
  natija.innerHTML=`<div class="rx-eslatma">Akkaunt va baza tayyorlanmoqda…</div>`;
  try{
    const r=await fetch(API+'/api/platforma/royxat',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({login:RX.login, parol:RX.parol,
        akkaunt_kod:RX.kod, akkaunt_nom:RX.korxona, inn:RX.inn,
        qqs_tolovchi:RX.qqs, soha:RX.soha||null, soha_matni:RX.soha_matni,
        ism:RX.ism, familiya:RX.familiya, telefon:RX.telefon})});
    if(!r.ok){const e=await r.json(); throw new Error(e.detail||'Xatolik');}
    const d=await r.json();
    await rxHolatKuzat(d.manzil, natija, btn);
  }catch(e){
    natija.innerHTML=`<div class="rx-xato">${esc(e.message)}</div>`;
    btn.disabled=false; btn.textContent='Tizimni yaratish';
  }
}

async function rxHolatKuzat(manzil, natija, btn){
  for(let i=0;i<25;i++){
    await new Promise(r=>setTimeout(r,700));
    try{
      const h=await (await fetch(API+`/api/platforma/holat/${RX.kod}`)).json();
      if(h.tayyorlik==='tayyor'){
        // Yaratilish ekraniga o'tamiz — sehrgar shu yerda tugaydi.
        const p=new URLSearchParams({qur:'1', rejim:RX.rejim||'agent'});
        if(RX.soha_matni) p.set('matn', RX.soha_matni);
        location.href = manzil + '/?' + p.toString();
        return;
      }
      if(h.tayyorlik==='xato'){
        natija.innerHTML=`<div class="rx-xato">Tayyorlanmadi: ${esc(h.izoh||'nomaʼlum')}</div>`;
        btn.disabled=false; btn.textContent='Qayta urinish'; return;
      }
    }catch(e){/* keyingi urinish */}
  }
  natija.innerHTML=`<div class="rx-eslatma">Kutilmoqda — birozdan keyin
    <b>${esc(RX.kod)}.innasoft.uz</b> manziliga kiring</div>`;
  btn.disabled=false; btn.textContent='Tizimni yaratish';
}
