/* =====================================================================
   TIZIM YARATILISH EKRANI

   Ro'yxatdan o'tgan odam shu yerga tushadi (`?qur=1`). U hali ERP ni
   ko'rmaydi — chunki hali ERP «yo'q»: u shu yerda YIG'ILADI.

     CHAP  — qurilish tasmasi. Har bo'lim yasalgani sari kartochka
             paydo bo'ladi (ovoz bilan). Tepada aylanadigan gaykalar.
     O'NG  — AI suhbati. Odam biznesini aytadi, agent ishlaydi,
             har qadam jonli ko'rinadi.

   NEGA SHUNDAY: odam «tizimingiz tayyorlanmoqda» degan bo'sh ekranni
   30 soniya kuta olmaydi — ketib qoladi. Bu yerda esa u NIMA
   yasalayotganini ko'rib turadi, va yasalgan har narsa ekranda
   qoladi. Kod yozuvchi agentlar (Cursor, Claude Desktop) shu
   naqshni ishlatadi: chapda natija to'planadi, o'ngda jarayon.

   Bu ekran ERP ning o'zi EMAS. Tugagach odam ERP ga o'tadi.
   ===================================================================== */

const QUR = {
  rejim: 'agent',        // agent | plan
  matn: '',              // ro'yxatda yozilgan yo'nalish
  bolimlar: [],          // yasalgan narsalar (chapda ko'rinadi)
  tugadi: false,
  ovoz: true,
};

/* --------------------------------------------------------------------
   OVOZ — kichik «ding». Fayl YO'Q: WebAudio bilan yasaladi.

   Nega fayl emas: bitta mp3 ~20 KB, uni yuklab olish kerak, keshdan
   chiqib ketadi, brauzer avtoijroni bloklashi mumkin. Bu yerda esa
   ikkita sinus to'lqin — hech narsa yuklanmaydi.

   Brauzer foydalanuvchi biror narsani bosmaguncha ovozga ruxsat
   bermaydi — shuning uchun xato bo'lsa jimgina o'tkazib yuboriladi.
   -------------------------------------------------------------------- */
let QUR_AUDIO = null;
function qurDing(baland){
  if(!QUR.ovoz) return;
  try{
    QUR_AUDIO = QUR_AUDIO || new (window.AudioContext||window.webkitAudioContext)();
    const ctx=QUR_AUDIO;
    if(ctx.state==='suspended') ctx.resume();
    const t=ctx.currentTime;
    [0,1].forEach(i=>{
      const o=ctx.createOscillator(), g=ctx.createGain();
      o.type='sine';
      o.frequency.setValueAtTime(baland?(i?1320:880):(i?988:659), t+i*0.07);
      g.gain.setValueAtTime(0.0001, t+i*0.07);
      g.gain.exponentialRampToValueAtTime(0.09, t+i*0.07+0.012);
      g.gain.exponentialRampToValueAtTime(0.0001, t+i*0.07+0.26);
      o.connect(g); g.connect(ctx.destination);
      o.start(t+i*0.07); o.stop(t+i*0.07+0.3);
    });
  }catch(e){/* ovozsiz ham ishlaydi */}
}

/* -------------------------------------------------------------------- */
function qurSorovi(){
  let p;
  try{ p = new URLSearchParams(location.search); }catch(e){ return false; }
  if(p.get('qur')!=='1') return false;
  QUR.rejim = p.get('rejim')==='plan' ? 'plan' : 'agent';
  QUR.matn  = (p.get('matn')||'').slice(0,300);
  try{ history.replaceState(null,'',location.pathname); }catch(e){}
  return true;
}

function qurBoshla(){
  document.getElementById('loginScreen').style.display='none';
  const lnd=document.getElementById('lending'); if(lnd) lnd.classList.remove('on');
  document.getElementById('app').classList.remove('on');

  let ek=document.getElementById('qurEkran');
  if(!ek){
    ek=document.createElement('div');
    ek.id='qurEkran'; ek.className='qur';
    document.body.appendChild(ek);
  }
  ek.innerHTML=`
    <div class="qur-chap glass">
      <div class="qur-bosh">
        <div class="qur-gayka">
          <svg viewBox="0 0 64 64" class="qur-g1" aria-hidden="true">
            <path fill="currentColor" d="M32 4l6 6h10l2 10 8 6-4 8 4 8-8 6-2 10H38l-6 6-6-6H16l-2-10-8-6 4-8-4-8 8-6 2-10h10z"/>
            <circle cx="32" cy="32" r="9" fill="rgba(255,255,255,.85)"/>
          </svg>
          <svg viewBox="0 0 64 64" class="qur-g2" aria-hidden="true">
            <path fill="currentColor" d="M32 4l6 6h10l2 10 8 6-4 8 4 8-8 6-2 10H38l-6 6-6-6H16l-2-10-8-6 4-8-4-8 8-6 2-10h10z"/>
            <circle cx="32" cy="32" r="9" fill="rgba(255,255,255,.85)"/>
          </svg>
        </div>
        <h2 class="qur-sarlavha" id="qurSarlavha">Tizimingiz yig'ilmoqda</h2>
        <div class="qur-sub" id="qurSub">AI yordamchi biznesingizni so'raydi
          va bo'limlarni shunga qarab yasaydi</div>
      </div>
      <div class="qur-tasma" id="qurTasma">
        <div class="qur-bosh-holat" id="qurBoshHolat">
          <div class="qur-nur"></div>
          <div class="qur-kutish">O'ngdagi suhbatda biznesingizni ayting —
            yasalgan har bo'lim shu yerda paydo bo'ladi</div>
        </div>
      </div>
      <div class="qur-past">
        <button class="btn ghost sm" onclick="qurOvozAlmash()" id="qurOvozBtn"
          title="Ovoz">🔊 Ovoz yoniq</button>
        <button class="btn pri" id="qurKirBtn" onclick="qurTizimgaKir()" disabled>
          Tizimga kirish</button>
      </div>
    </div>
    <button class="qur-chat-tugma" id="qurChatTugma" onclick="qurChatAlmash()"
      title="Suhbatni ko'rsatish/yashirish">✦</button>`;
  ek.classList.add('on');

  // AI paneli o'ngda — ERP dagi bilan BIR XIL panel. Ikkinchi chat
  // yozilmaydi: bitta joyda tuzatilsa, ikkalasida ham tuzaladi.
  if(typeof agentPanelYasa==='function') agentPanelYasa();
  setTimeout(()=>{
    if(typeof agentOchYop==='function') agentOchYop(true);
    if(typeof AGENT_KALIT!=='undefined') AGENT_KALIT='sozlash';
    if(typeof agentYangiSuhbat==='function') agentYangiSuhbat();
    qurRejimKorsat();
    if(QUR.matn) qurBirinchiXabar();
  }, 500);

  qurKuzat();
}

/* Ro'yxatda yozilgan yo'nalish suhbatning birinchi xabari bo'ladi —
   odam ikkinchi marta yozmasin. */
function qurBirinchiXabar(){
  const t=document.getElementById('agentMatn');
  if(!t) return;
  t.value = QUR.rejim==='plan'
    ? `Bizning ishimiz: ${QUR.matn}. Avval reja tuzib ber, keyin tasdiqlayman.`
    : `Bizning ishimiz: ${QUR.matn}. Tizimni shunga moslab ber.`;
  const b=document.getElementById('agentYubor');
  if(b && !b.disabled) b.click();
}

function qurRejimKorsat(){
  const s=document.getElementById('agentHolat');
  if(!s) return;
  const nishon=document.createElement('span');
  nishon.className='qur-rejim-nishon';
  nishon.textContent = QUR.rejim==='plan' ? '◎ Plan' : '⚡ Agent';
  s.appendChild(document.createTextNode(' '));
  s.appendChild(nishon);
}

function qurChatAlmash(){
  const p=document.querySelector('.agent-panel');
  if(!p) return;
  agentOchYop(!p.classList.contains('ochiq'));
}

function qurOvozAlmash(){
  QUR.ovoz=!QUR.ovoz;
  document.getElementById('qurOvozBtn').textContent =
    QUR.ovoz ? '🔊 Ovoz yoniq' : '🔇 Ovoz o\'chiq';
  if(QUR.ovoz) qurDing(false);
}

/* --------------------------------------------------------------------
   KUZATUV — chapdagi tasma nimadan to'ladi.

   Agent asbob chaqirganda (profil saqladi, modul yoqdi) shu asbob
   nomi chapda kartochka bo'lib chiqadi. Ya'ni tasma o'ylab topilgan
   animatsiya emas — HAQIQIY ishning aksi. Agent hech narsa qilmasa,
   chapda ham hech narsa paydo bo'lmaydi.
   -------------------------------------------------------------------- */
const QUR_ASBOB_NOM = {
  profil_saqla:        ['Yo\'nalish profili', 'Maydonlar va narx hisobi yozildi'],
  profilni_faollashtir:['Yo\'nalish yoqildi', 'Tizim shu yo\'nalishda ishlaydi'],
  profilni_oqi:        ['Profil o\'qildi', 'Hozirgi sozlama ko\'rildi'],
  profillarni_kor:     ['Tayyor shablonlar', 'Mos keladigani qidirildi'],
  modullarni_kor:      ['Ish tartiblari', 'Buyurtma bosqichlari ko\'rildi'],
  sinov_buyurtma:      ['Sinov buyurtmasi', 'Hisob-kitob tekshirildi'],
};

function qurKuzat(){
  const oqim=document.getElementById('agentOqim');
  if(!oqim){ setTimeout(qurKuzat, 400); return; }
  new MutationObserver(()=>qurTekshir(oqim))
    .observe(oqim, {childList:true, subtree:true});
}

const QUR_KORILGAN = new Set();
function qurTekshir(oqim){
  oqim.querySelectorAll('.agent-iz').forEach((iz,i)=>{
    const kalit = i+'|'+iz.textContent;
    if(QUR_KORILGAN.has(kalit)) return;
    QUR_KORILGAN.add(kalit);
    iz.textContent.replace(/^⚙\s*/,'').split('·').forEach(nom=>{
      qurBolimQosh(nom.trim());
    });
  });
}

function qurBolimQosh(asbob){
  if(!asbob) return;
  const [nom, izoh] = QUR_ASBOB_NOM[asbob] || [asbob, 'Bajarildi'];
  if(QUR.bolimlar.includes(nom)) return;
  QUR.bolimlar.push(nom);

  const bosh=document.getElementById('qurBoshHolat');
  if(bosh) bosh.remove();

  const k=document.createElement('div');
  k.className='qur-karta';
  k.innerHTML=`<div class="qur-karta-belgi">✓</div>
    <div><div class="qur-karta-nom">${esc(nom)}</div>
    <div class="qur-karta-izoh">${esc(izoh)}</div></div>`;
  document.getElementById('qurTasma').appendChild(k);
  requestAnimationFrame(()=>k.classList.add('kirdi'));
  k.scrollIntoView({behavior:'smooth', block:'nearest'});
  qurDing(false);

  // Profil yoqilgan bo'lsa — tizim ishlashga tayyor.
  if(asbob==='profilni_faollashtir') qurTayyor();
}

function qurTayyor(){
  if(QUR.tugadi) return;
  QUR.tugadi=true;
  document.getElementById('qurSarlavha').textContent='Tizimingiz tayyor';
  document.getElementById('qurSub').textContent=
    'Bo\'limlar yasaldi. Suhbatni davom ettirib qo\'shimcha o\'zgartirish kiritishingiz mumkin.';
  const b=document.getElementById('qurKirBtn');
  b.disabled=false; b.classList.add('chaqnaydi');
  document.getElementById('qurEkran').classList.add('tayyor');
  qurDing(true);
}

function qurTizimgaKir(){
  const ek=document.getElementById('qurEkran');
  if(ek) ek.classList.remove('on');
  if(typeof agentOchYop==='function') agentOchYop(false);
  if(typeof enterApp==='function') enterApp();
}
