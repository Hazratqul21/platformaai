/* Dizayn stendi — faqat ko'rish uchun. Backend yo'q, ma'lumot namunaviy.
   Maqsad: haqiqiy CSS haqiqiy markup ustida qanday ko'rinishini o'lchash. */
const NAVX=[
  {p:'calc',t:'Янги буюртма (смета)',i:'calc'},
  {p:'orders',t:'Буюртмалар',i:'cart'},
  {p:'crm',t:'Мижозлар',i:'users'},
  {p:'dash',t:'Бошқарув панели',i:'dash'},
  {p:'ai',t:'AI ёрдамчи',i:'ai'},
  {p:'hr',t:'Ходимлар',i:'hr'},
  {p:'fin',t:'Молия',i:'wallet'},
  {p:'kassa',t:'Касса журнали',i:'wallet'},
  {p:'hisob',t:'Бухгалтерия',i:'doc'},
  {p:'exp',t:'Сех харажатлари',i:'doc'},
  {p:'set',t:'Созламалар',i:'gear'},
  {p:'help',t:'Йўриқнома',i:'doc'},
];
const PAGEX='kassa';
document.getElementById('nav').innerHTML=NAVX.map(n=>
 `<a class="${n.p===PAGEX?'active':''}" data-label="${n.t}"><span class="ic">${icon(n.i)}</span><span>${n.t}</span></a>`).join('');
document.getElementById('brandLogo').innerHTML=icon('box',20);
document.getElementById('ptitle').textContent='Касса журнали';
document.getElementById('psub').textContent='Кирим-чиқим дафтари — кимдан келди, кимга кетди';
document.getElementById('uav').textContent='B';
document.getElementById('uname').textContent='Boshqaruvchi';
document.getElementById('urole').textContent='Рахбар';
const fs=document.getElementById('firmSel');
fs.style.display=''; fs.innerHTML='<option>Барча фирмалар</option>';
document.getElementById('app').classList.add('on');

const kpiX=(ic,lab,val,chip,dir)=>`<div class="glass card kpi"><div class="between"><div class="ic-box">${icon(ic,19)}</div>${chip?`<span class="chip ${dir}">${chip}</span>`:''}</div><div class="val">${val}</div><div class="lab">${lab}</div></div>`;
const rows=[
 ['2026-08-21','−800 000',[['асвежител','Зарплата','−800 000 сўм']]],
 ['2026-08-20','−1.9 mln',[['Програма','Зарплата','−1 900 000 сўм']]],
 ['2026-08-19','−16.9 mln',[
   ['Бар кофе','товар','−1 200 000 сўм'],
   ['електро энергия','Зарплата','−510 000 сўм'],
   ['електро энергия','Зарплата','−7 650 000 сўм'],
   ['електро энергия','Зарплата','−5 100 000 сўм'],
   ['Аббос ишчи','зарплата','−2 100 000 сўм'],
   ['Ишчила','обед','−100 000 сўм'],
   ['Рахим','','−100 000 сўм']]],
];
document.getElementById('content').innerHTML=`<div class="page show">
<div class="grid g3 mb">
  ${kpiX('up','Жами кирим','3.2 mln сўм','','up')}
  ${kpiX('flag','Жами чиқим','240.8 mln сўм','','dn')}
  ${kpiX('wallet','Баланс','-237.6 mln сўм','минус','dn')}
</div>
<div class="between mb" style="flex-wrap:wrap;gap:8px">
  <div class="chips" style="margin:0">
    <button class="fchip on">Ҳаммаси</button>
    <button class="fchip">THE BILLIARD</button>
  </div>
  <div class="row">
    <button class="btn pri sm">${icon('arrowDown',14)} Кирим</button>
    <button class="btn sm dngr">${icon('arrowUp',14)} Чиқим</button>
    <button class="btn sm">${icon('doc',15)} Excel</button>
  </div>
</div>
<div class="row mb" style="gap:8px">
  <input class="fld qidir" style="margin:0;flex:1" placeholder="Мижозни қидириш — номи, телефон ёки СТИР бўйича…"/>
  <button class="btn">${icon('dash',14)} Жадвал</button>
  <button class="btn sm ghost">${icon('pencil',13)}</button>
  <button class="btn sm dngr">${icon('x',13)}</button>
  <button class="btn sm">${icon('camera',15)} Расм</button>
  <button class="btn sm">${icon('truck',14)} Етказиш</button>
  <button class="btn sm">${icon('cash',14)} Пул бериш</button>
</div>
<div class="glass card">
${rows.map(([day,sum,list])=>`<div style="padding:6px 0">
  <div class="between" style="font-size:11px;color:var(--ink-3);padding:6px 2px;border-bottom:1px solid var(--hair)">
    <b>${day}</b><span>${sum}</span></div>
  ${list.map(([who,note,amt])=>`<div class="between" style="padding:8px 2px;border-bottom:1px solid var(--hair);gap:8px">
    <span style="flex:1"><b style="font-size:13px">${who}</b>
      <span class="tag mut" style="font-size:9px;padding:1px 6px">THE BILLIARD</span>
      ${note?`<div class="muted" style="font-size:10.5px">${note}</div>`:''}</span>
    <b style="color:var(--danger);font-variant-numeric:tabular-nums;white-space:nowrap">${amt}</b>
    <button class="btn sm ghost">✕</button>
  </div>`).join('')}</div>`).join('')}
</div></div>`;
