/* ================= UI helpers ================= */
function toast(c,ic,t,p){
  // yangi uslub: toast("Xabar") yoki toast("Xabar","err")
  if(arguments.length<=2&&!['d','w','o'].includes(c)){
    const msg=c; const kind=ic==='err'?'d':'o';
    return toast(kind, kind==='d'?'alertic':'check', msg, '');
  }
  const el=document.createElement('div');el.className='toast glass alert '+c;
  el.innerHTML=`<div class="ai">${icon(ic,16)}</div><div><b>${esc(t)}</b><p>${esc(p)}</p></div>`;
  document.getElementById('toasts').appendChild(el);setTimeout(()=>el.remove(),4200);}
function modal(html,wide){
  const box=document.getElementById('modalBox');
  box.innerHTML=html;
  box.classList.toggle('wide',!!wide);   // keng jadvalli oynalar uchun
  document.getElementById('overlay').classList.add('show');
}
function closeModal(){document.getElementById('overlay').classList.remove('show');}
const f=id=>document.getElementById(id)?.value||'';
// Pul maydoni qiymatini toza son qilib olish (probel/vergul olib tashlanadi): fnum('id')
const fnum=id=>+String(f(id)).replace(/[\s,]/g,'')||0;
// Pul kiritish maydonini minglik ajratgich bilan formatlash (yozayotganda):
// input'ga oninput="pulFmt(this)" qo'yiladi. Manfiy (−) qo'llab-quvvatlanadi.
function pulFmt(el){
  if(!el)return;
  const manfiy=String(el.value).trim().startsWith('-');
  const raqam=String(el.value).replace(/[^\d]/g,'');
  el.value=(manfiy&&raqam?'-':'')+(raqam?Number(raqam).toLocaleString('ru-RU'):'');
}
const _id=id=>document.getElementById(id);
const kpi=(ic,lab,val,chip,dir)=>`<div class="glass card kpi"><div class="between"><div class="ic-box">${icon(ic,19)}</div>${chip?`<span class="chip ${dir}">${chip}</span>`:''}</div><div class="val">${val}</div><div class="lab">${lab}</div></div>`;
const alertBox=(c,ic,t,p)=>`<div class="alert ${c}"><div class="ai">${icon(ic,16)}</div><div><b>${t}</b><p>${p}</p></div></div>`;
const stTag=st=>({'Kutishda':'mut','Muzokara':'warn','Sexda kesilmoqda':'pri','Omborga tushdi':'warn','Yetkazib berildi':'ok','Bekor qilindi':'dn'})[st]||'mut';
const agColor=(k,v)=>v<=0?'':k==='0-15'?'ok':k==='15-30'?'warn':'dn';
// DIQQAT: bu <button> bo'lishi shart. Ilgari <a href="#"> edi va bosilganda
// hash "#" ga o'zgarib, router uni tanimay standart sahifaga (Янги заказ)
// tashlab yuborardi — hisobot o'rniga sahifa almashib ketardi.
const dl=(path,label)=>`<button type="button" class="btn sm" onclick="download('${path}')">${icon('doc',14)} ${label}</button>`;
async function download(path){
  if(FIRM&&!path.includes('firm=')){path+=(path.includes('?')?'&':'?')+'firm='+encodeURIComponent(FIRM);}
  try{
    const r=await fetch(API+path,{headers:{'Authorization':'Bearer '+TOKEN}});
    if(!r.ok){
      let msg='Файл юклаб бўлмади ('+r.status+')';
      if(r.status===401)msg='Сеанс тугаган — қайта киринг';
      if(r.status===403)msg='Бу ҳисоботга рухсатингиз йўқ';
      if(r.status===404)msg='Маълумот топилмади';
      return toast('d','alertic','Хатолик',msg);
    }
    const blob=await r.blob();
    if(!blob.size)return toast('d','alertic','Хатолик','Файл бўш келди');
    // fayl nomi: RFC5987 (filename*=UTF-8'') yoki oddiy filename=
    const cd=r.headers.get('Content-Disposition')||'';
    let name=decodeURIComponent((cd.match(/filename\*=UTF-8''([^;]+)/i)||[])[1]||'')
          || (cd.match(/filename="?([^";]+)"?/i)||[])[1] || 'hisobot';
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=url; a.download=name.trim(); a.style.display='none';
    document.body.appendChild(a);   // DOM'da bo'lmasa mobil brauzer bosmaydi
    a.click();
    // darhol revoke qilinsa yuklanish uzilib qoladi — kechiktiramiz
    setTimeout(()=>{try{URL.revokeObjectURL(url);a.remove();}catch(e){}},4000);
    toast('o','check','Юкланди',name.trim());
  }catch(e){toast('d','alertic','Хатолик',e.message||'Юклашда хатолик');}
}

const UZ_OY=['январ','феврал','март','апрел','май','июн','июл','август','сентябр','октябр','ноябр','декабр'];
const UZ_KUN=['якшанба','душанба','сешанба','чоршанба','пайшанба','жума','шанба'];
const uzDate=d=>`${d.getDate()}-${UZ_OY[d.getMonth()]}, ${UZ_KUN[d.getDay()]}`;


// sahifa sarlavhasini o'rnatish (modullashgan sahifalar ishlatadi)
function setTitle(title, sub){
  const pt=document.getElementById('ptitle');
  const ps=document.getElementById('psub');
  if(pt)pt.textContent=title||'';
  if(ps)ps.textContent=sub||'';
}

// modal ochilganda birinchi maydonga fokus (qulaylik)
const _origModal = modal;
modal = function(html,wide){
  _origModal(html,wide);
  setTimeout(()=>{const el=document.querySelector('#modalBox input.fld, #modalBox select.fld');if(el)el.focus();},60);
};

// yangi sahifalar uslubi uchun taxallus
const openModal = (html)=>modal(html);

/* ============ Rasm bilan ishlash (mahsulot rasmi) ============ */
// Telefonda olingan rasm katta bo'ladi — yuborishdan oldin kichiklashtiramiz,
// aks holda internet sekin joyda yuklanmaydi.
function rasmniKichiklashtir(file, maxTomon=1280, sifat=0.72){
  return new Promise((resolve,reject)=>{
    const fr=new FileReader();
    fr.onerror=()=>reject(new Error('Расм ўқилмади'));
    fr.onload=()=>{
      const img=new Image();
      img.onerror=()=>reject(new Error('Расм очилмади'));
      img.onload=()=>{
        let {width:w,height:h}=img;
        if(w>maxTomon||h>maxTomon){
          if(w>h){h=Math.round(h*maxTomon/w);w=maxTomon;}
          else {w=Math.round(w*maxTomon/h);h=maxTomon;}
        }
        const cv=document.createElement('canvas');cv.width=w;cv.height=h;
        cv.getContext('2d').drawImage(img,0,0,w,h);
        resolve(cv.toDataURL('image/jpeg',sifat));
      };
      img.src=fr.result;
    };
    fr.readAsDataURL(file);
  });
}
// Rasmni katta qilib ko'rish
function rasmniKatta(url){
  modal(`<div style="text-align:center">
    <img src="${esc(url)}" style="max-width:100%;max-height:74vh;border-radius:12px"/>
    <div class="row" style="justify-content:center;margin-top:12px;gap:6px">
      <a class="btn sm" href="${esc(url)}" target="_blank" rel="noopener">Янги ойнада очиш</a>
      <button class="btn sm pri" onclick="closeModal()">Ёпиш</button>
    </div></div>`, true);
}
