/* ---- Buyurtmalar ----
 *
 * Oqim (qaysi statusdan qayoqqa) va bosqichlar profildan olinadi:
 * `soha.js` -> sohaKeyingi()/sohaQadamlar(). Ilgari bu yerda karton
 * statuslari qotirilgan edi va boshqa sohada tugmalar umuman chiqmasdi.
 */
PAGES.orders=async()=>{
  if(window._ordArchive===undefined)window._ordArchive=false;
  const [os]=await Promise.all([
    api('/api/orders'+(window._ordArchive?'?archive=1':'')), sohaYukla()]);
  window._orders=os;window._ordFilter='Hammasi';window._postRender=renderOrders;
  const counts={};os.forEach(o=>counts[o.status]=(counts[o.status]||0)+1);
  // arxivda faqat Ҳаммаси, faol'da esa holat bo'yicha
  const tabs=window._ordArchive?['Hammasi']:['Hammasi',...sohaFiltrStatuslari()];
  return `
  <div class="between mb" style="align-items:center">
    <b style="font-size:13px">${window._ordArchive?'📦 Архив — тугалланган ва бекор қилинган':'Фаол буюртмалар'}</b>
    <button class="btn sm ${window._ordArchive?'pri':''}" onclick="ordToggleArchive()">
      ${window._ordArchive?'← Фаол буюртмалар':'📦 Архив'}</button>
  </div>
  <div class="chips">${tabs.map(s=>{
    const label=s==='Hammasi'?'Ҳаммаси':kir(s);
    const n=s==='Hammasi'?os.length:(counts[s]||0);
    return `<button class="fchip ${s==='Hammasi'?'on':''}" data-st="${s}" onclick="window._ordFilter='${s}';document.querySelectorAll('.chips .fchip').forEach(b=>b.classList.toggle('on',b.dataset.st==='${s}'));renderOrders()">${label} ${n?`· ${n}`:''}</button>`;}).join('')}</div>
  <div class="grid g2" id="orderCards"></div>`;
};
async function ordToggleArchive(){
  window._ordArchive=!window._ordArchive;
  // hash o'zgarmaydi (bir xil sahifa) — shuning uchun kontentni to'g'ridan-to'g'ri qayta chizamiz
  const html=await PAGES.orders();
  document.getElementById('content').innerHTML=`<div class="page show">${html}</div>`;
  if(window._postRender){const fn=window._postRender;window._postRender=null;fn();}
}
function renderOrders(){
  const box=document.getElementById('orderCards');if(!box)return;
  const list=window._orders.filter(o=>window._ordFilter==='Hammasi'||o.status===window._ordFilter);
  const QADAM=sohaQadamlar();
  box.innerHTML=list.map(o=>{
    const si=QADAM.findIndex(q=>q.nom===o.status);
    const tracker=si>=0?`
      <div class="trk">${QADAM.map((_,i)=>`${i?`<div class="tl ${i<=si?'on':''}"></div>`:''}<div class="td ${i<=si?'on':''}"></div>`).join('')}</div>
      <div class="trk-labs">${QADAM.map(q=>`<span>${esc(kir(q.nom))}</span>`).join('')}</div>`:'';
    return `<div class="glass ccard" style="cursor:default">
      <div class="between"><span><b style="font-size:14px">№ ${o.id}</b> <span class="muted" style="font-size:11px">· ${o.created_at.slice(0,10)}</span></span>
        <span class="tag ${sohaTag(o.status)}">${kir(o.status)}</span></div>
      ${o.photo_url?`<img src="${esc(o.photo_url)}" alt="маҳсулот расми" loading="lazy"
        style="width:100%;height:130px;object-fit:cover;border-radius:10px;margin-top:8px;cursor:zoom-in"
        onerror="this.style.display='none'"
        onclick="rasmniKatta('${esc(o.photo_url)}')"/>`:''}
      <div style="font-size:12.5px;margin-top:4px"><b>${esc(o.company)}</b></div>
      ${o.product_name ? `<div style="font-size:12px;margin-top:2px;color:var(--text-main)">📦 ${esc(o.product_name)}</div>` : ''}
      <div class="muted" style="font-size:11.5px;margin-top:2px">${esc(o.size||'')}${o.tur?` · <b>${esc(o.tur)}</b>`:''}${o.tarkib?` · ${esc(o.tarkib)}`:''}</div>
      ${o.note?`<div class="muted" style="font-size:11px;margin-top:3px;font-style:italic">📝 ${esc(o.note)}</div>`:''}
      <div class="between" style="margin-top:8px;font-size:13px">
        <span>${new Intl.NumberFormat('ru-RU').format(o.qty)} ${esc(o.qty_birlik||'')}</span><b>${money(o.total)}</b></div>
      ${o.delivered_qty>0&&o.qolgan_qty>0?`<div class="between" style="font-size:11px;margin-top:2px"><span class="muted">Топширилди: ${new Intl.NumberFormat('ru-RU').format(o.delivered_qty)}</span><span class="tag warn" style="font-size:9.5px">қолди ${new Intl.NumberFormat('ru-RU').format(o.qolgan_qty)}</span></div>`:''}
      ${o.tolanmadi?`<div class="between" style="font-size:11px;margin-top:2px"><span class="muted">Топширилган мол пули</span><span class="tag dn" style="font-size:9.5px">💸 Тўланмади</span></div>`:''}
      <div class="between muted" style="font-size:10.5px;margin-top:3px">
        <span>Тўлов: ${o.payment_due_date ? o.payment_due_date : 'номаълум'}</span>
        <span>Тайёр бўлиши: ${o.due_date ? o.due_date : 'номаълум'}</span>
      </div>
      ${['Rahbar','Menejer'].includes(ME.role)?`<div class="between" style="font-size:10.5px;margin-top:3px"><span class="muted">Фойда улуши</span><span class="tag ${o.margin>=15?'ok':'warn'}" style="font-size:9.5px">${o.margin}%</span></div>`:''}
      ${tracker}
      <div class="row" style="flex-wrap:wrap;gap:5px;margin-top:8px">
        <button class="btn sm" onclick="orderCard(${o.id})">${o.photo_url?'🖼':'📷'} Ичини кўриш</button>
        ${sohaKeyingi(o.status).filter(s=>!['bekor','boshlanish'].includes(sohaMano(s))).map(s=>sohaMano(s)==='topshirildi'
          ?`<button class="btn sm pri" onclick='deliverForm(${JSON.stringify(o).replace(/'/g,"&#39;")})'>📤 ${o.delivered_qty>0?'Яна топшириш':'Мижозга топшириш'}</button>`
          :`<button class="btn sm ${sohaMano(s)==='muzokara'?'':'pri'}" onclick="setStatus(${o.id},'${esc(s)}',this)">${esc(sohaTugmaMatni(s))}</button>`).join('')}
        ${o.delivered_qty>0&&!['topshirildi','bekor'].includes(sohaMano(o.status))&&['Rahbar','Menejer','Sklad mudiri'].includes(ME.role)
          ?`<button class="btn sm${o.qolgan_qty<=0?' pri':''}" onclick="yakunla(${o.id},${o.delivered_qty},${o.qty},this)" title="${o.qolgan_qty<=0?'Ҳаммаси берилган — архивга ўтказиш':'Тираж кам чиққан бўлса — шу берилган миқдор билан ёпиш'}">🏁 Якунлаш</button>`:''}
        ${sohaKeyingi(o.status).some(s=>sohaMano(s)==='bekor')&&['Rahbar','Menejer'].includes(ME.role)?`<button class="btn sm dngr" onclick="if(confirm('№${o.id} буюртма бекор қилинсинми? Материал омборга қайтади.'))setStatus(${o.id},'${esc(sohaKeyingi(o.status).find(s=>sohaMano(s)==='bekor')||'')}',this)">✕ Бекор</button>`:''}
        ${!['boshlanish','bekor'].includes(sohaMano(o.status))?dl('/api/reports/act/'+o.id+'.pdf','Акт'):''}
        ${['tayyor','topshirildi'].includes(sohaMano(o.status))?`<span class="muted" style="font-size:10.5px;width:100%;margin-top:2px">Юк хати:</span>${dl('/api/reports/nakladnoy/'+o.id+'.pdf','PDF')}${dl('/api/reports/nakladnoy/'+o.id+'.xlsx','Excel')}${dl('/api/reports/nakladnoy/'+o.id+'.docx','Word')}`:''}
        ${o.accepted_stamp?'<span class="tag ok" style="font-size:9.5px">✔ мижоз қабул қилган</span>':''}
      </div>
    </div>`;}).join('')||'<div class="glass card muted" style="grid-column:1/-1;text-align:center">Бу ҳолатда буюртма йўқ</div>';
}
/* ---- Buyurtma ichi: to'liq ma'lumot + mahsulot rasmi ---- */
function orderCard(id){
  const o=(window._orders||[]).find(x=>x.id===id);
  if(!o)return;
  modal(`<h2 class="sec">Буюртма № ${o.id}</h2>
  <div class="muted" style="font-size:12px;margin:4px 0 10px">${esc(o.company)} · ${o.created_at.slice(0,10)}
    <span class="tag ${sohaTag(o.status)}" style="margin-left:6px">${kir(o.status)}</span></div>
  <div id="ord_photo_box">${ordPhotoGallery(o)}</div>
  <input type="file" id="ord_photo_file" accept="image/*" capture="environment" multiple style="display:none"
    onchange="ordRasmYukla(${o.id},this)"/>
  <div class="glass card" style="padding:10px;background:var(--hair);margin-top:10px">
    ${o.product_name?`<div class="between" style="font-size:12.5px"><span>Маҳсулот</span><b>${esc(o.product_name)}</b></div>`:''}
    ${sohaTavsifHtml(o)}
    <div class="between" style="font-size:12.5px"><span>Миқдори</span><b>${new Intl.NumberFormat('ru-RU').format(o.qty)} ${esc(o.qty_birlik||'')}</b></div>
    <div class="between" style="font-size:12.5px"><span>1 ${esc(o.qty_birlik||'дона')} нархи</span><b>${money(o.unit_price)}</b></div>
    ${o.qqs_summa?`<div class="between muted" style="font-size:12px"><span>ҚҚС ${o.qqs_stavka}%</span><span>${money(o.qqs_summa)}</span></div>`:''}
    <div class="between" style="font-size:14px;border-top:1px solid var(--ink-2);margin-top:6px;padding-top:6px">
      <b>Жами</b><b style="color:var(--primary-deep)">${money(o.total)}</b></div>
  </div>
  <div id="ord_retsept" class="glass card" style="padding:10px;margin-top:8px;font-size:12px">
    <div class="muted">Хомашё ҳисоби юкланмоқда…</div></div>
  <div class="between muted" style="font-size:11.5px;margin-top:8px">
    <span>Тайёр бўлиши: <b>${o.due_date||'—'}</b></span>
    <span>Тўлов: <b>${o.payment_due_date||'—'}</b></span></div>
  ${o.note?`<div class="glass card" style="padding:8px;margin-top:8px;font-size:12px;font-style:italic">📝 ${esc(o.note)}</div>`:''}
  ${o.delivered_qty>0?`<div id="ord_topshir" class="glass card" style="padding:10px;margin-top:8px;font-size:12px">
    <div class="muted">Топшириш тарихи юкланмоқда…</div></div>`:''}
  <div class="row" style="margin-top:14px;justify-content:space-between">
    ${['Rahbar','Menejer','Buxgalter'].includes(ME.role)&&!['Yetkazib berildi','Bekor qilindi'].includes(o.status)
      ?`<button class="btn" onclick='orderEdit(${JSON.stringify(o).replace(/'/g,"&#39;")})'>✎ Таҳрирлаш</button>`:'<span></span>'}
    <button class="btn pri" onclick="closeModal()">Ёпиш</button></div>`);
  ordRetsept(o.id);
  if(o.delivered_qty>0) ordTopshirishlar(o.id);
}

/* ---- Соҳа майдонлари: профилдаги НОМ билан кўрсатилади ----
 * Ilgari bu yerda «Ўлчам / Тури / Қоғоз маркаси» qotirilgan edi.
 * Endi qaysi maydon bo'lsa — o'sha, o'z nomi bilan chiqadi. */
function sohaTavsifHtml(o){
  const at=o.attributes||{};
  const qatorlar=sohaMaydonlar().map(md=>{
    let v=at[md.kalit];
    if(v===undefined||v===null||v==='')return '';
    if(md.tur==='mantiq')v=v?'Ҳа':'Йўқ';
    return `<div class="between" style="font-size:12.5px"><span>${esc(md.nom)}</span>
      <b>${esc(v)}${md.birlik?' '+esc(md.birlik):''}</b></div>`;
  }).filter(Boolean).join('');
  // Profil almashgan bo'lsa eski buyurtma maydonlari ro'yxatda yo'q —
  // shunda hech bo'lmasa tayyor matnni ko'rsatamiz, bo'sh qolmasin.
  return qatorlar||`<div class="between" style="font-size:12.5px"><span>Тавсиф</span>
    <b>${esc([o.size,o.tur,o.tarkib].filter(Boolean).join(' · ')||'—')}</b></div>`;
}

/* ---- Хомашё: нима кетади, қанчага ва зарарига сотилмаяптими ---- */
async function ordRetsept(id){
  const box=()=>document.getElementById('ord_retsept');
  try{
    const d=await api(`/api/orders/${id}/retsept`);
    const el=box(); if(!el)return;
    if(!d.retsept_bor){ el.remove(); return; }   // ретцептсиз соҳа — блок керак эмас
    const n=v=>new Intl.NumberFormat('ru-RU').format(v);
    el.innerHTML=`
      <div style="font-weight:700;margin-bottom:6px">🧾 Хомашё (шу буюртмага)</div>
      ${d.qatorlar.map(q=>`
        <div class="between" style="padding:5px 0;border-top:1px solid var(--hair)">
          <span>${esc(q.material)} <span class="muted">${n(q.kerak_material_birligida??q.kerak)} ${esc(q.material_birligi||q.birlik)}</span></span>
          <span>${q.summa!=null?`<b>${money(q.summa)}</b> `:''}
            <span class="tag ${q.yetadi?'ok':'dn'}" style="font-size:9.5px">${q.yetadi?'етади':'ЕТМАЙДИ'}</span></span>
        </div>`).join('')}
      <div class="between" style="border-top:1px solid var(--ink-2);margin-top:6px;padding-top:6px;font-weight:700">
        <span>Хомашё жами</span><span>${money(d.xomashyo_summasi||0)}</span></div>
      <div class="between muted" style="font-size:11.5px">
        <span>Буюртма (ҚҚСсиз)</span><span>${money(d.qqssiz_summa||0)}</span></div>
      ${d.zarar_ogoh?alertBox('d','alertic','Зарарига сотилмоқда',esc(d.zarar_ogoh)):''}`;
  }catch(e){
    const el=box(); if(el)el.innerHTML='<div class="muted">Хомашё ҳисобини олиб бўлмади</div>';
  }
}

/* ---- Мол қачон, соат нечида берилган ---- */
async function ordTopshirishlar(id){
  const box=()=>document.getElementById('ord_topshir');
  try{
    const d=await api(`/api/orders/${id}/topshirishlar`);
    const el=box(); if(!el)return;                 // ойна ёпилган бўлса — тегмаймиз
    const n=v=>new Intl.NumberFormat('ru-RU').format(v);
    if(!d.topshirishlar.length){
      el.innerHTML=`<div class="muted">Топшириш тарихи топилмади (эски ёзув бўлиши мумкин)</div>`;
      return;
    }
    // Тарихдаги йиғинди ҳақиқий миқдордан фарқ қилиши мумкин — агар кейинчалик
    // топширилган миқдор тузатилган бўлса. Шунда чалкашмаслик учун изоҳ берамиз.
    const yigindi=d.topshirishlar.reduce((a,t)=>a+(t.dona||0),0);
    const farq = yigindi!==d.delivered_qty;
    el.innerHTML=`
      <div style="font-weight:700;margin-bottom:6px">📦 Мол қачон берилган</div>
      ${d.topshirishlar.map(t=>`
        <div class="between" style="padding:5px 0;border-top:1px solid var(--hair)">
          <span><b>${t.sana}</b> <span class="muted">соат ${t.vaqt}</span></span>
          <span><b>${t.dona!=null?n(t.dona)+' дона':'—'}</b>${t.pul?` <span class="muted">· ${n(t.pul)} сўм</span>`:''}</span>
        </div>`).join('')}
      <div class="between" style="border-top:1px solid var(--ink-2);margin-top:6px;padding-top:6px;font-weight:700">
        <span>Ҳозирги ҳисоб</span><span>${n(d.delivered_qty)} / ${n(d.qty)} дона</span></div>
      ${farq?`<div class="muted" style="font-size:11px;margin-top:5px;line-height:1.45">
        ⚠️ Тарихдаги йиғинди (${n(yigindi)} дона) ҳозирги ҳисобдан фарқ қилади —
        топширилган миқдор кейинчалик тузатилган. Тўғри рақам: <b>${n(d.delivered_qty)} дона</b>.</div>`:''}`;
  }catch(e){
    const el=box(); if(el)el.innerHTML=`<div class="muted">Топшириш тарихини олиб бўлмади</div>`;
  }
}
/* ---- Buyurtmani tuzatish (yaratilgandan keyin) ---- */
function orderEdit(o){
  const birlik=esc(o.qty_birlik||'дона');
  const qadam=(SOHA&&SOHA.kasrli)?' step="any"':'';
  modal(`<h2 class="sec">Буюртма № ${o.id} ни таҳрирлаш</h2>
  <label class="fl">Маҳсулот номи</label><input class="fld" id="oe_name" value="${esc(o.product_name||'')}"/>
  ${sohaFormaHtml('oe_',o.attributes||{})}
  <div class="grid g2" style="gap:8px;margin-top:8px">
    <div><label class="fl">Миқдор, ${birlik}</label>
      <input class="fld" id="oe_qty" type="number"${qadam} value="${o.qty}" oninput="oeRecalc()"/></div>
    <div><label class="fl">1 ${birlik} нархи</label>
      <input class="fld" id="oe_price" type="number" step="any" value="${o.unit_price}" oninput="oeRecalc()"/></div>
  </div>
  <div class="between" style="font-size:14px;padding:6px 0"><span>Жами (ҚҚСсиз)</span>
    <b id="oe_total" style="color:var(--primary-deep)">${money(o.qqssiz_summa??o.total)}</b></div>
  <label class="fl">Изоҳ</label><input class="fld" id="oe_note" value="${esc(o.note||'')}"/>
  ${o.delivered_qty>0?`<div class="muted" style="font-size:11px;margin-top:4px;color:var(--warn)">⚠️ ${new Intl.NumberFormat('ru-RU').format(o.delivered_qty)} ${birlik} аллақачон топширилган — миқдор ундан кам бўлмасин</div>`:''}
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="orderEditSave(${o.id})">Сақлаш</button></div>`);
}
function oeRecalc(){
  const t=(+f('oe_qty')||0)*(+f('oe_price')||0);
  const el=_id('oe_total'); if(el)el.textContent=money(t);
}
async function orderEditSave(id){
  const bosh=sohaTekshir('oe_');
  if(bosh)return toast('w','alertic','Майдон тўлдирилмаган',bosh);
  const body={product_name:f('oe_name'), attributes:sohaFormaOl('oe_'),
    qty:+f('oe_qty'), unit_price:+f('oe_price'), note:f('oe_note')};
  try{
    const r=await api('/api/orders/'+id,{method:'PUT',body:JSON.stringify(body)});
    closeModal();
    toast('o','check','Буюртма тузатилди',r.ogoh||money(r.total));
    if(r.ogoh)setTimeout(()=>toast('w','alertic','Диққат',r.ogoh),300);
    go('orders');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
/* ---- Buyurtma rasmlari galereyasi (swipe) ---- */
function ordPhotoGallery(o){
  const ph=(o.photos&&o.photos.length)?o.photos:(o.photo_url?[{url:o.photo_url,filename:o.photo}]:[]);
  window._ordPh={id:o.id,list:ph,idx:0};
  if(!ph.length){
    return `<button class="btn pri" style="width:100%;justify-content:center" onclick="document.getElementById('ord_photo_file').click()">📷 Расмга олиш</button>
      <div class="muted" style="font-size:10.5px;margin-top:5px;text-align:center">Цехда маҳсулотни расмга олинг — бир нечта бўлса ҳам бўлади</div>`;
  }
  return `<div style="position:relative">
    <img id="ord_ph_img" src="${esc(ph[0].url)}" style="width:100%;max-height:300px;object-fit:contain;border-radius:12px;background:var(--hair);cursor:zoom-in"
      onerror="this.onerror=null;this.replaceWith(Object.assign(document.createElement('div'),{className:'muted',style:'padding:40px;text-align:center;background:var(--hair);border-radius:12px;font-size:13px',textContent:'Расм мавжуд эмас'}))"
      onclick="rasmniKatta(_ordPh.list[_ordPh.idx].url)"/>
    ${ph.length>1?`<span onclick="ordPhNav(-1)" style="position:absolute;left:6px;top:50%;transform:translateY(-50%);background:rgba(0,0,0,.5);color:#fff;width:32px;height:32px;border-radius:50%;display:grid;place-items:center;cursor:pointer">‹</span>
      <span onclick="ordPhNav(1)" style="position:absolute;right:6px;top:50%;transform:translateY(-50%);background:rgba(0,0,0,.5);color:#fff;width:32px;height:32px;border-radius:50%;display:grid;place-items:center;cursor:pointer">›</span>
      <span id="ord_ph_num" style="position:absolute;bottom:8px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.6);color:#fff;font-size:11px;padding:2px 8px;border-radius:10px">1 / ${ph.length}</span>`:''}
  </div>
  <div class="row" style="gap:6px;margin-top:6px">
    <button class="btn sm" style="flex:1;justify-content:center" onclick="document.getElementById('ord_photo_file').click()">➕ Яна расм</button>
    <button class="btn sm dngr" onclick="ordRasmOchir(${o.id})">✕ Шу расмни ўчириш</button></div>`;
}
function ordPhNav(dir){
  const p=window._ordPh; if(!p||!p.list.length)return;
  p.idx=(p.idx+dir+p.list.length)%p.list.length;
  const img=_id('ord_ph_img'); if(img)img.src=p.list[p.idx].url;
  const num=_id('ord_ph_num'); if(num)num.textContent=(p.idx+1)+' / '+p.list.length;
}
async function ordRasmYukla(id,inp){
  const files=[...(inp.files||[])]; if(!files.length)return;
  const box=document.getElementById('ord_photo_box');
  if(box)box.innerHTML='<div class="muted" style="text-align:center;padding:16px">Расм(лар) юкланмоқда…</div>';
  try{
    let last=null;
    for(const file of files){
      const data=await rasmniKichiklashtir(file);
      last=await post('/api/orders/'+id+'/photo',{data});
    }
    const o=(window._orders||[]).find(x=>x.id===id);
    if(o&&last){o.photos=(last.photos||[]).map(u=>({url:u,filename:u.split('/').pop()}));o.photo_url=o.photos[0]?.url;o.photo=o.photos[0]?.filename;}
    toast('o','check','Расм сақланди',files.length>1?files.length+' та':'');
    orderCard(id); renderOrders();
  }catch(e){ toast('d','alertic','Расм сақланмади',e.message); orderCard(id); }
}
async function ordRasmOchir(id){
  const p=window._ordPh;
  const fn=(p&&p.list[p.idx])?p.list[p.idx].filename:null;
  if(!confirm('Шу расм ўчирилсинми?'))return;
  try{
    const r=await api('/api/orders/'+id+'/photo'+(fn?'?filename='+encodeURIComponent(fn):''),{method:'DELETE'});
    const o=(window._orders||[]).find(x=>x.id===id);
    if(o){o.photos=(r.photos||[]).map(u=>({url:u,filename:u.split('/').pop()}));o.photo_url=o.photos[0]?.url||null;o.photo=o.photos[0]?.filename||'';}
    toast('o','check','Расм ўчирилди','');
    orderCard(id); renderOrders();
  }catch(e){ toast('d','alertic','Хатолик',e.message); }
}

/* ---- Mijozga topshirish: qisman ham bo'lishi mumkin ---- */
function deliverForm(o){
  const qolgan = o.qolgan_qty!=null ? o.qolgan_qty : o.qty;
  const berilgan = o.delivered_qty||0;
  modal(`<h2 class="sec">Мижозга топшириш — буюртма № ${o.id}</h2>
  <div class="muted" style="font-size:12px;margin:4px 0 10px">${esc(o.company)}</div>
  <div class="glass card mb" style="padding:10px;background:var(--hair)">
    <div class="muted" style="font-size:10.5px;margin-bottom:6px">ТОПШИРИЛАЁТГАН МОЛ</div>
    <div class="between" style="font-size:12.5px"><span>Маҳсулот</span><b>${esc(o.product_name||'—')}</b></div>
    ${sohaTavsifHtml(o)}
    ${o.note?`<div class="between" style="font-size:12px"><span>Изоҳ</span><b style="font-style:italic">${esc(o.note)}</b></div>`:''}
    <div class="between" style="font-size:12.5px"><span>Жами буюртма</span><b>${new Intl.NumberFormat('ru-RU').format(o.qty)} ${esc(o.qty_birlik||'')}</b></div>
    ${berilgan>0?`<div class="between" style="font-size:12.5px"><span>Аввал топширилган</span><b style="color:var(--ok)">${new Intl.NumberFormat('ru-RU').format(berilgan)} ${esc(o.qty_birlik||'')}</b></div>`:''}
    <div class="between" style="font-size:12.5px"><span>1 ${esc(o.qty_birlik||'дона')} нархи</span><b>${money(o.unit_price)}</b></div>
  </div>
  <label class="fl">Ҳозир қанча топширилади (${esc(o.qty_birlik||'дона')})? <span style="color:var(--danger)">(жами ${new Intl.NumberFormat('ru-RU').format(qolgan)} қолган)</span></label>
  <input class="fld" id="dl_qty" type="number" max="${qolgan}" placeholder="масалан: 500 (ҳаммасини эмас!)" oninput="dlQtyChange(${o.unit_price},${qolgan})"/>
  <div class="row" style="gap:6px;margin:6px 0">
    <button class="btn sm" onclick="_id('dl_qty').value=${qolgan};dlQtyChange(${o.unit_price},${qolgan})">Ҳаммаси (${new Intl.NumberFormat('ru-RU').format(qolgan)})</button>
    <button class="btn sm" onclick="_id('dl_qty').value=Math.ceil(${qolgan}/2);dlQtyChange(${o.unit_price},${qolgan})">Ярми</button>
  </div>
  <div class="muted" style="font-size:10.5px;margin-bottom:4px">Фақат бир қисми берилса — рақамни ёзинг. Бутун заказни ёпмоқчи бўлсангизгина «Ҳаммаси».</div>
  <div class="between" style="font-size:13.5px;padding:6px 0"><span>Топширилаётган сумма</span>
    <b id="dl_sum" style="color:var(--primary-deep)">0 сўм</b></div>
  <hr style="border:0;border-top:1px dashed var(--hair);margin:6px 0"/>
  <label class="fl">Мижоз ҳозир берган пул (сўм)</label>
  <input class="fld" id="dl_amount" inputmode="numeric" value="0" placeholder="0 — мол қарзга берилди" oninput="pulFmt(this)"/>
  <div class="row" style="gap:6px;margin:6px 0">
    <button class="btn sm" onclick="_id('dl_amount').value=Math.round((+f('dl_qty')||0)*${o.unit_price})">Тўлиқ тўлади</button>
    <button class="btn sm" onclick="_id('dl_amount').value=0">Қарзга берилди</button>
  </div>
  <label class="fl">Тўлов тури</label>
  <select class="fld" id="dl_method"><option value="Naqd">Нақд</option><option value="Karta">Карта</option><option value="O'tkazma">Ўтказма</option></select>
  <label class="fl">Изоҳ (ихтиёрий)</label><input class="fld" id="dl_note"/>
  <label class="fl">Қачон берилган? <span class="muted" style="font-weight:400">(бугун бўлса — тегманг)</span></label>
  <input class="fld" id="dl_sana" type="date" max="${new Date().toISOString().slice(0,10)}"
         min="${(o.created_at||'').slice(0,10)}" value="${new Date().toISOString().slice(0,10)}"/>
  <div class="muted" style="font-size:10.5px;margin-top:3px">Мол олдинроқ берилиб, кейин киритилаётган бўлса — ҳақиқий санани танланг.</div>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="deliverSave(${o.id},${o.unit_price},${qolgan})">📤 Топшириш</button></div>`);
}
function dlQtyChange(price,qolgan){
  let q=+f('dl_qty')||0;
  if(q>qolgan){q=qolgan;_id('dl_qty').value=qolgan;}
  const el=_id('dl_sum'); if(el)el.textContent=money(q*price);
}
async function deliverSave(id,price,qolgan){
  const qty=+f('dl_qty')||0;
  const amount=fnum('dl_amount')||0;
  if(!(qty>0))return toast('w','alertic','Дона киритилмади','Нечта топширилаётганини ёзинг');
  if(qty>qolgan)return toast('w','alertic','Кўп','Фақат '+qolgan+' дона қолган');
  // butun buyurtma yopilishidan oldin tasdiq — noto'g'ri to'liq yopib qo'ymaslik uchun
  if(qty===qolgan&&!confirm('⚠️ '+new Intl.NumberFormat('ru-RU').format(qty)+' дона — БУТУН қолган мол топширилади, заказ ёпилади.\n\nАгар фақат бир қисмини бермоқчи бўлсангиз — «Бекор» босиб, камроқ рақам ёзинг.\n\nҲаммасини топширасизми?'))return;
  const jami=qty*price;
  if(amount>jami&&!confirm('Киритилган пул топширилаётган мол суммасидан катта. Давом этасизми?'))return;
  try{
    const sana=f('dl_sana')||'';
    const bugun=new Date().toISOString().slice(0,10);
    const r=await post('/api/orders/'+id+'/deliver',
      {qty,paid_amount:amount,method:f('dl_method'),note:f('dl_note'),
       ...(sana&&sana!==bugun?{sana}:{})});   // бугунги бўлса — юбормаймиз
    closeModal();
    const holat = r.qolgan>0 ? `Қисман: ${new Intl.NumberFormat('ru-RU').format(r.berildi)} дона берилди, ${new Intl.NumberFormat('ru-RU').format(r.qolgan)} қолди` : 'Тўлиқ топширилди';
    const sanaIzoh = (sana&&sana!==bugun) ? ` · ${sana.split('-').reverse().join('.')} санаси билан` : '';
    toast('o','check',holat, (amount>0?money(amount)+" олинди · ":"")+"қарз: "+money(r.client_debt)+sanaIzoh);
    go('orders');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
// Тираж буюртмадан кам чиққанда — берилган миқдор билан ёпиб, архивга юбориш
async function yakunla(id,berildi,qty,btn){
  const n=v=>v.toLocaleString('ru');
  const b=sohaBirlik();
  const qoldi=qty-berildi;
  // Ikki xil holat: (a) tiraj kam chiqqan — qolgani yopiladi,
  //                 (b) hammasi berilgan — faqat arxivga o'tkaziladi.
  const matn = qoldi>0
    ? `№${id} буюртма якунлансинми?\n\n`+
      `Буюртма: ${n(qty)} ${b}\n`+
      `Берилди:  ${n(berildi)} ${b}\n`+
      `Ёпилади:  ${n(qoldi)} ${b} (миқдор кам чиққан)\n\n`+
      `Берилган ${n(berildi)} дона якуний ҳисобланади ва буюртма архивга ўтади.\n`+
      `Қарз ўзгармайди — у аллақачон фақат берилган мол бўйича ҳисобланган.\n\n`+
      `ДИҚҚАТ: якунлангач буюртмани таҳрирлаб бўлмайди.`
    : `№${id} буюртма архивга ўтказилсинми?\n\n`+
      `Ҳамма мол берилган: ${n(berildi)} дона.\n`+
      `Миқдор ва қарз ўзгармайди — фақат фаол рўйхатдан архивга ўтади.\n\n`+
      `ДИҚҚАТ: якунлангач буюртмани таҳрирлаб бўлмайди.`;
  if(!confirm(matn))return;
  if(_stBusy.has(id))return;
  _stBusy.add(id);
  if(btn){btn.disabled=true;btn.style.opacity='.55';}
  try{
    await api(`/api/orders/${id}/yakunla`,{method:'POST'});
    toast('o','check',`№${id} якунланди`,`${berildi.toLocaleString('ru')} дона · архивга ўтди`);
    go('orders');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
  finally{_stBusy.delete(id);if(btn){btn.disabled=false;btn.style.opacity='';}}
}

// Бир буюртма учун бир вақтда битта сўров — тугма икки марта босилса, иккинчиси
// эски статусни юбориб «...дан ...га ўтиб бўлмайди» (400) хатосини берарди.
const _stBusy = new Set();
async function setStatus(id,st,btn){
  if(_stBusy.has(id))return;                 // аллақачон юборилган — такрор босилмасин
  _stBusy.add(id);
  if(btn){btn.disabled=true;btn.style.opacity='.55';}
  try{
    // Ишлаб чиқаришга беришдан олдин хомашё етадими — ҳар соҳада
    // ишлайдиган умумий ретцепт орқали (олдин фақат картон учун
    // ёзилган `check-stock` чақириларди ва бошқа соҳада фойдасиз эди).
    if(sohaMano(st)==='ishlab_chiqarish'){
      try{
        const r=await api('/api/orders/'+id+'/retsept');
        if(r.retsept_bor&&!r.yetadi){
          const kam=r.qatorlar.filter(q=>!q.yetadi)
            .map(q=>`${q.material}: керак ${q.kerak_material_birligida??q.kerak}, бор ${q.omborda}`).join('\n');
          if(!confirm('⚠️ Омборда хомашё етмайди:\n\n'+kam+'\n\nБарибир давом эттирасизми? (Қолдиқ минусга ўтади)'))return;
        }
      }catch(e){ console.error(e); }
    }
    await api(`/api/orders/${id}/status?status=${encodeURIComponent(st)}`,{method:'POST'});
    toast('o','check',`№${id} → ${kir(st)}`,sohaMano(st)==='ishlab_chiqarish'?'Хомашё FIFO бўйича ечилди':'');
    go('orders');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
  finally{_stBusy.delete(id);if(btn){btn.disabled=false;btn.style.opacity='';}}
}
