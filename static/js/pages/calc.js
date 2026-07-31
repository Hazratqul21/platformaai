/* ---- Smeta kalkulyatori ---- */
// Buyurtma turlari — mijozning o'z atamalari (backend: models.ORDER_TURLARI bilan bir xil)
const TURLAR=['1 слой','2 слой','3 слой','5 слой','Самоклейка','Офсет','Картон Меловка'];
PAGES.calc=async()=>{
  const cs=await api('/api/clients');window._clients=cs;
  const set=await api('/api/finance/settings');
  let grades = (set.paper_grades || 'K1,K2,T-22,T-23').split(',').map(s=>s.trim()).filter(Boolean);
  // ombordagi partiyalar
  try{const raw=await api('/api/warehouse/raw');
    (raw.groups||[]).forEach(g=>{if(g.grade&&!grades.includes(g.grade))grades.push(g.grade);});
  }catch(e){}
  // Haqiqatda xarid qilingan qog'ozlar — taannarxdagi narx shulardan olinadi,
  // shuning uchun ro'yxatning boshida turadi. Nomga grammaj ham qo'shiladi:
  // bitta nom ostida bir necha grammaj bo'ladi ("Silver pak" 170/210/270 гр) va
  // grammaji ko'rsatilmasa narx qaysi biridan olinishi noaniq bo'lib qoladi.
  try{const mats=await api('/api/catalog/materials');
    const nomlar=(mats||[]).filter(x=>x.last_price>0&&(x.unit||'kg')==='kg')
      .map(x=>{const g=(x.grammaj||'').trim();
               return g&&!x.name.match(/\d/)?`${x.name} ${g.replace(/\s+/g,'')}`:x.name;});
    [...new Set(nomlar)].reverse().forEach(n=>{if(!grades.includes(n))grades.unshift(n);});
  }catch(e){}
  return `<div class="split">
  <div class="glass card">
    <h2 class="sec">Янги буюртма</h2><div class="sec-sub">Ўлчам ёзилса — материал ва нарх ўзи ҳисобланади</div>
    <div style="margin-bottom:8px">
      <label class="fl">Маҳсулот номи (ихтиёрий)</label>
      <input class="fld" id="q_product_name" placeholder="Масалан: 3Л сок каробкаси" />
    </div>
    <div class="grid g3" style="gap:8px">
      <div><label class="fl">Узунлик, мм</label><input class="fld" id="q_l" type="number" value="400"/></div>
      <div><label class="fl">Кенглик, мм</label><input class="fld" id="q_w" type="number" value="300"/></div>
      <div><label class="fl">Баландлик, мм</label><input class="fld" id="q_h" type="number" value="250"/></div>
    </div>
    <div class="grid g2" style="gap:8px">
      <div><label class="fl">Тури</label><select class="fld" id="q_tur">
        ${TURLAR.map(x=>`<option ${x==='3 слой'?'selected':''}>${x}</option>`).join('')}</select></div>
      <div><label class="fl">Қоғоз маркаси (ёзинг ёки танланг)</label>
        <input class="fld" id="q_grade" list="gradeList" value="${grades[0]||''}" placeholder="масалан: Silver pak 140"/>
        <datalist id="gradeList">${grades.map(g=>`<option value="${esc(g)}">`).join('')}</datalist></div>
    </div>
    <div class="grid g2" style="gap:8px">
      <div>
        <label class="fl">Босма ранглар (флексо)</label>
        <select class="fld" id="q_colors">${[0,1,2,3,4].map(x=>`<option value="${x}">${x?x+' ранг':'Босмасиз'}</option>`).join('')}</select>
      </div>
      <div><label class="fl">Тираж, дона</label><input class="fld" id="q_qty" type="number" value="1000"/></div>
    </div>
    <label class="fl">Мижоз (номи ёки телефони бўйича қидиринг)</label>
    <input class="fld" id="q_client_search" list="clientList" placeholder="🔍 масалан: Хос ёки 90 123..."
      oninput="clientTanlandi()" autocomplete="off"/>
    <datalist id="clientList">${cs.map(c=>`<option value="${esc(c.company)}${c.phone?' · '+esc(c.phone):''}">`).join('')}</datalist>
    <input type="hidden" id="q_client"/>
    <div id="q_client_orders"></div>
    <label class="fl">Қўшимча изоҳ (ихтиёрий)</label>
    <input class="fld" id="q_note" placeholder="масалан: тагига картон қўйилсин, шошилинч"/>
    <label class="fl">Маҳсулот расмлари (ихтиёрий, бир нечта)</label>
    <div class="glass card" style="padding:10px">
      <input type="file" id="q_photo_file" accept="image/*" capture="environment" multiple
        style="display:none" onchange="calcRasmTanlandi(this)"/>
      <div id="q_photo_grid" class="row" style="flex-wrap:wrap;gap:6px;margin-bottom:6px"></div>
      <div class="row" style="gap:6px">
        <button class="btn sm pri" style="flex:1;justify-content:center"
          onclick="document.getElementById('q_photo_file').click()">📷 Расм қўшиш</button>
      </div>
      <div class="muted" style="font-size:10.5px;margin-top:5px">
        Бир нечта расм қўшса бўлади. Телефонда камера очилади.</div>
    </div>
    <button class="btn pri" style="width:100%;justify-content:center;margin-top:16px" onclick="runQuote()">${icon('calc',15)} Ҳисоблаш</button>
  </div>
  <div id="quoteRes"><div class="glass card muted" style="text-align:center;padding:40px 20px">Ўлчамларни киритинг ва «Ҳисоблаш» тугмасини босинг</div></div>
  </div>`;
};
/* ---- Mijozni qidirib tanlash + oldingi buyurtmalar (povtor) ---- */
async function clientTanlandi(){
  const val=f('q_client_search').trim();
  // "Kompaniya · telefon" ko'rinishidan mijozni topamiz
  const nom=val.split(' · ')[0].trim().toLowerCase();
  const c=(window._clients||[]).find(x=>x.company.toLowerCase()===nom)
        ||(window._clients||[]).find(x=>x.company.toLowerCase().includes(nom)&&nom.length>2);
  const box=_id('q_client_orders');
  if(!c){ _id('q_client').value=''; if(box)box.innerHTML=''; return; }
  _id('q_client').value=c.id;
  if(!box)return;
  box.innerHTML='<div class="muted" style="font-size:11px;padding:6px">Олдинги буюртмалар юкланмоқда…</div>';
  try{
    const d=await api('/api/clients/'+c.id+'/detalizatsiya');
    const orders=await api('/api/orders?firm=');  // hammasi
    const mine=orders.filter(o=>o.client_id===c.id).slice(0,6);
    if(!mine.length){ box.innerHTML=`<div class="muted" style="font-size:11px;padding:4px">${esc(c.company)} — биринчи буюртма</div>`; return; }
    box.innerHTML=`<div class="glass card" style="padding:8px;margin:6px 0;background:var(--hair)">
      <div class="muted" style="font-size:10.5px;margin-bottom:4px">🔁 ${esc(c.company)}нинг олдинги буюртмалари — босса, майдонлар тўлади</div>
      ${mine.map(o=>`<div class="between" style="font-size:11.5px;padding:4px 0;border-top:1px solid var(--hair);cursor:pointer"
        onclick='povtorTanla(${JSON.stringify(o).replace(/'/g,"&#39;")})'>
        <span><b>#${o.id}</b> ${esc(o.product_name||o.tur)} <span class="muted">${esc(o.size)} · ${esc(o.grade)}</span></span>
        <span>${new Intl.NumberFormat('ru-RU').format(o.qty)} дона · ${mshort(o.total)}</span></div>`).join('')}
    </div>`;
  }catch(e){ box.innerHTML=''; }
}
function povtorTanla(o){
  const [L,W,H]=(o.size||'').split(/[x×]/);
  if(_id('q_product_name'))_id('q_product_name').value=o.product_name||'';
  if(_id('q_l'))_id('q_l').value=+L||'';
  if(_id('q_w'))_id('q_w').value=+W||'';
  if(_id('q_h'))_id('q_h').value=+H||'';
  if(_id('q_tur'))_id('q_tur').value=o.tur||'3 слой';
  if(_id('q_grade'))_id('q_grade').value=o.grade||'';
  if(_id('q_colors'))_id('q_colors').value=o.colors||0;
  if(_id('q_qty'))_id('q_qty').value=o.qty||'';
  toast('o','check','Олдинги буюртмадан олинди','Нарх/расмни ўзгартириб «Ҳисоблаш»ни босинг');
}
let LASTQ=null;
let CALC_RASMLAR=[];   // buyurtma yaratilgunga qadar rasmlar shu yerda turadi (data URL)

async function calcRasmTanlandi(inp){
  const files=[...(inp.files||[])];
  if(!files.length)return;
  for(const file of files){
    if(CALC_RASMLAR.length>=10){ toast('w','alertic','Кўп','Кўпи билан 10 та расм'); break; }
    try{ CALC_RASMLAR.push(await rasmniKichiklashtir(file)); }
    catch(e){ toast('d','alertic','Расм юкланмади',e.message); }
  }
  inp.value='';
  calcRasmGrid();
}
function calcRasmGrid(){
  const g=document.getElementById('q_photo_grid'); if(!g)return;
  g.innerHTML=CALC_RASMLAR.map((src,i)=>`<div style="position:relative">
    <img src="${src}" style="width:72px;height:72px;object-fit:cover;border-radius:8px"/>
    <span onclick="calcRasmOchir(${i})" style="position:absolute;top:-6px;right:-6px;background:var(--danger);color:#fff;width:20px;height:20px;border-radius:50%;display:grid;place-items:center;cursor:pointer;font-size:12px">✕</span>
    </div>`).join('')
    +(CALC_RASMLAR.length?`<div class="muted" style="font-size:10.5px;width:100%;margin-top:2px">✅ ${CALC_RASMLAR.length} та расм тайёр</div>`:'');
}
function calcRasmOchir(i){ CALC_RASMLAR.splice(i,1); calcRasmGrid(); }

async function runQuote(){
  const body={product_name:f('q_product_name'), length_mm:+f('q_l'),width_mm:+f('q_w'),height_mm:+f('q_h'),
    tur:f('q_tur'), grade:f('q_grade'),colors:+f('q_colors'),qty:+f('q_qty'),
    client_id:+f('q_client')||null, note:f('q_note')};
  try{
    const q=await post('/api/orders/quote',body);LASTQ={...body,quote:q};
    const cr=q.credit;
    document.getElementById('quoteRes').innerHTML=`<div class="glass card">
      <h2 class="sec mb">Смета натижаси</h2>
      <div class="between" style="padding:5px 0;font-size:13px"><span class="muted">1 қути учун м²</span><b>${q.m2_per_box.toFixed(4)} м²</b></div>
      <div class="between" style="padding:5px 0;font-size:13px"><span class="muted">Жами керак (5% брак билан)</span><b>${q.need_m2_total.toFixed(1)} м²</b></div>
      <div class="between" style="padding:5px 0;font-size:13px"><span class="muted">Омборда бор</span>
        <b style="color:${q.enough_material?'var(--ok)':'var(--danger)'}">${q.stock_m2.toFixed(1)} m² ${q.enough_material?'✓':'— ЕТМАЙДИ!'}</b></div>
      <hr style="border:0;border-top:1px dashed var(--hair);margin:10px 0"/>
      ${q.formula_ogoh?alertBox('d','alertic','ДИҚҚАТ: сизнинг формулангиз ишламаяпти!',esc(q.formula_ogoh)):''}
      ${q.narx_ogoh?alertBox('d','alertic','ДИҚҚАТ: қоғоз нархи 0 — таннарх нотўғри!',esc(q.narx_ogoh)):''}
      <div style="background:rgba(124,127,240,.07);border-radius:12px;padding:12px;margin-bottom:10px">
        <div class="muted" style="font-size:10px;letter-spacing:1px;margin-bottom:6px">ФАҚАТ СИЗГА КЎРИНАДИ — мижозга чиқмайди</div>
        <div class="between" style="font-size:12.5px;padding:3px 0"><span>Хомашё (${money(q.material_price_m2)}/м² + 5% брак)</span><b style="${!q.material_price_m2?'color:var(--danger)':''}">${money(q.material)}</b></div>
        ${q.narx_manba?`<div class="muted" style="font-size:10.5px;padding:0 0 3px 0">нарх манбаси: ${esc(q.narx_manba)}</div>`:''}
        <div class="between" style="font-size:12.5px;padding:3px 0"><span>Иш ҳақи / дона</span><b>${money(q.labor)}</b></div>
        <div class="between" style="font-size:12.5px;padding:3px 0"><span>Босма</span><b>${money(q.printing)}</b></div>
        <div class="between" style="font-size:13px;padding:5px 0;border-top:1px solid var(--hair)"><span><b>Таннарх / дона</b></span><b>${money(q.unit_cost)}</b></div>
        <div class="between" style="font-size:12.5px;padding:3px 0"><span>Устама (${esc(q.category)})</span><b style="color:var(--ok)">${q.margin_percent}% → фойда ${mshort(q.profit)} сўм</b></div>
      </div>
      <div class="between" style="font-size:15px;padding:6px 0"><span>Таклиф нархи / дона</span><b>${money(q.unit_price)}</b></div>
      <div class="between" style="font-size:19px;font-weight:700;padding:8px 0;border-top:1px solid var(--hair)"><span>ЖАМИ (${body.qty} дона)</span><span style="color:var(--primary-deep)">${money(q.total)}</span></div>
      ${cr&&cr.over_limit?alertBox('d','alertic','Кредит лимити!',`Жорий қарз ${mshort(cr.current_debt)} + бу буюртма = ${mshort(cr.would_be)} (лимит ${mshort(cr.limit)})${cr.blocked?' — БЛОКЛАНАДИ':''}`):''}
      ${cr&&cr.blacklisted?alertBox('d','flag','Қора рўйхат','Бу мижоз қора рўйхатда — буюртма блокланади'):''}
      ${body.client_id&&['Rahbar','Menejer'].includes(ME.role)?`
        <label class="fl">Якуний нарх (келишилган бўлса ўзгартиринг)</label>
        <input class="fld" id="q_final" type="number" value="${q.unit_price}"/>
        <div class="grid g3" style="gap:8px; margin-top:8px;">
          <div><label class="fl">Олдиндан тўлов %</label><input class="fld" id="q_prepaid" type="number" value="30"/></div>
          <div><label class="fl">Тайёрлаш муддати</label><input class="fld" id="q_due" type="number" value="15" title="Кун ҳисобида"/></div>
          <div><label class="fl">Тўлов муддати</label><input class="fld" id="q_pay_due" type="number" value="15" title="Кун ҳисобида"/></div>
        </div>
        <button class="btn pri" style="width:100%;justify-content:center;margin-top:12px" onclick="createOrder()">${icon('cart',15)} Буюртмани яратиш</button>`
      :'<div class="muted" style="font-size:11.5px;margin-top:8px">Буюртма яратиш учун мижозни танланг</div>'}
    </div>`;
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
async function createOrder(){
  try{
    const o=await post('/api/orders',{...LASTQ,unit_price:+f('q_final')||null,
      prepaid_percent:+f('q_prepaid')||0,due_days:+f('q_due')||15, payment_due_days:+f('q_pay_due')||15,
      note:f('q_note')});
    // rasmlar bo'lsa — buyurtma yaratilgach ketma-ket yuklanadi
    let rasmXato='';
    for(const src of CALC_RASMLAR){
      try{ await post('/api/orders/'+o.id+'/photo',{data:src}); }
      catch(e){ rasmXato=' · баъзи расм сақланмади'; }
    }
    CALC_RASMLAR=[];
    toast(rasmXato?'w':'o','check',`Буюртма №${o.id} яратилди`,
      `${money(o.total)}${o.credit_warning?' · ДИҚҚАТ: лимит ошди!':''}${rasmXato}`);
    go('orders');
  }catch(e){toast('d','alertic','Блокланди',e.message);}
}

