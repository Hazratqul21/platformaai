/* =====================================================================
   KIRISH UI — onboarding oqimining faqat ko'rinishi.

   Bu fayl autentifikatsiya yoki ro'yxatdan o'tish mantiqiga tegmaydi.
   `?kir=` va `?qur=1` ni o'qib, yangi akkaunt egasiga qayerga
   kirayotgani hamda keyin nima bo'lishini tushuntiradi.
   ===================================================================== */

function kirishUIManzil(){
  const host=(location.hostname||'').replace(/^www\./,'');
  // localhost/IP manzilida sun'iy korxona nomi ko'rsatmaymiz.
  if(!host || host==='localhost' || /^\d{1,3}(\.\d{1,3}){3}$/.test(host)) return '';
  return host;
}

function kirishUITenantNomi(host){
  const first=(host||'').split('.')[0]||'';
  if(!first || first==='innasoft') return 'INNASOFT';
  return first.split(/[-_]+/).filter(Boolean)
    .map(x=>x.charAt(0).toUpperCase()+x.slice(1)).join(' ');
}

function kirishUIBoshla(){
  const card=document.querySelector('.login-card');
  const toggle=document.getElementById('loginPasswordToggle');
  const pw=document.getElementById('pw');
  if(!card || !toggle || !pw) return;

  toggle.addEventListener('click',()=>{
    const ochiq=pw.type==='text';
    pw.type=ochiq?'password':'text';
    toggle.textContent=ochiq?"Ko'rsatish":"Yashirish";
    toggle.setAttribute('aria-pressed',String(!ochiq));
    toggle.setAttribute('aria-label',ochiq?"Parolni ko'rsatish":"Parolni yashirish");
    pw.focus();
  });

  let p;
  try{p=new URLSearchParams(location.search);}catch(e){p=new URLSearchParams();}
  const yangi=!!p.get('kir');
  const qurilish=p.get('qur')==='1';
  const host=kirishUIManzil();
  if(!yangi) return;

  const nom=kirishUITenantNomi(host);
  const name=document.getElementById('loginWorkspaceName');
  const domain=document.getElementById('loginWorkspaceDomain');
  const mark=document.getElementById('loginWorkspaceMark');
  const title=document.getElementById('loginTitle');
  const kicker=document.getElementById('loginKicker');
  const intro=document.getElementById('loginIntro');
  const back=document.getElementById('loginBack');
  if(name) name.textContent=nom;
  if(domain) domain.textContent=host || "Sizning shaxsiy ish maydoningiz";
  if(mark) mark.textContent=(nom.charAt(0)||'◈').toUpperCase();
  if(title) title.textContent='Ish joyingiz tayyor';
  if(kicker) kicker.textContent='Bir qadam qoldi';
  if(intro) intro.textContent=qurilish
    ? "Parolni kiriting — keyin AI tizimingizni siz bilan birga yig'ishni boshlaydi."
    : "Parolni kiriting va shaxsiy boshqaruv maydoningizga o‘ting.";
  if(back) back.hidden=true;
  card.classList.add('login-card-yangi');
}

kirishUIBoshla();
