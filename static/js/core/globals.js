/* ================= Telegram Mini App ================= */
const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); try{tg.setHeaderColor('#ecdfc6')}catch(e){} }
// Mini App ichida — soddaroq ko'rinish; brauzerda — to'liq
const IS_TG = !!(tg && tg.initData) || new URLSearchParams(location.search).get('mode')==='tg';
if (IS_TG) document.documentElement.classList.add('tg');

// Mini App'da oynaning HAQIQIY balandligi: klaviatura ochilsa yoki tepadagi panel
// o'zgarsa — 100vh haqiqiy joydan katta bo'lib qoladi va modal oyna ekrandan
// chiqib ketadi (tugmalar ko'rinmaydi). Telegram bergan aniq balandlikni CSS
// o'zgaruvchisiga yozamiz va modal shunga tayanadi.
function tgBalandlik(){
  const h = (tg && (tg.viewportStableHeight || tg.viewportHeight)) || window.innerHeight;
  document.documentElement.style.setProperty('--tg-h', h + 'px');
}
if (IS_TG) {
  tgBalandlik();
  try { tg && tg.onEvent && tg.onEvent('viewportChanged', tgBalandlik); } catch(e){}
  window.addEventListener('resize', tgBalandlik);
  window.addEventListener('orientationchange', () => setTimeout(tgBalandlik, 250));
}
// og'ir bloklar Mini App'da yig'ilgan holda chiqadi
const acc=(title,inner)=>IS_TG
  ?`<details class="glass card mb"><summary style="font-family:var(--serif);font-size:16px;font-weight:700;cursor:pointer">${title}</summary><div style="margin-top:12px">${inner}</div></details>`
  :`<div class="glass card mb"><h2 class="sec mb">${title}</h2>${inner}</div>`;

/* ================= Ikonlar ================= */
const I={dash:'<rect x="3" y="3" width="7" height="7" rx="1.6"/><rect x="14" y="3" width="7" height="7" rx="1.6"/><rect x="14" y="14" width="7" height="7" rx="1.6"/><rect x="3" y="14" width="7" height="7" rx="1.6"/>',
users:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="3.2"/><path d="M22 21v-2a4 4 0 0 0-3-3.85"/><path d="M16 3.15A4 4 0 0 1 16 11"/>',
calc:'<rect x="4" y="2" width="16" height="20" rx="2.5"/><path d="M8 6h8M8 11h.01M12 11h.01M16 11h.01M8 15h.01M12 15h.01M16 15h.01M8 19h.01M12 19h.01M16 19h.01"/>',
box:'<path d="M21 8l-9-5-9 5v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
cart:'<circle cx="9.5" cy="20" r="1.3"/><circle cx="18" cy="20" r="1.3"/><path d="M2.5 3.5h2l2.3 12a1 1 0 0 0 1 .8h9a1 1 0 0 0 1-.8L20.5 7.5H6"/>',
wallet:'<path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H19a2 2 0 0 1 2 2v1H5.5A2.5 2.5 0 0 1 3 7.5z"/><path d="M3 7.5V18a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-3"/><path d="M21 9v6h-5a3 3 0 0 1 0-6z"/>',
hr:'<circle cx="12" cy="7" r="3.4"/><path d="M5 21a7 7 0 0 1 14 0"/><path d="M17 4l2 2 3-3"/>',
chart:'<line x1="3" y1="21" x2="21" y2="21"/><rect x="5" y="11" width="3" height="9" rx="1"/><rect x="10.5" y="6" width="3" height="14" rx="1"/><rect x="16" y="13.5" width="3" height="6.5" rx="1"/>',
up:'<path d="M3 17l6-6 4 4 8-8M15 7h6v6"/>',flag:'<path d="M5 21V3M5 4h12l-2.2 3.2L17 10.4H5"/>',
alertic:'<path d="M12 3.2l9 15.6H3z"/><path d="M12 9.5v4M12 16.6h.01"/>',
check:'<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
doc:'<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
plus:'<path d="M12 5v14M5 12h14"/>',
// AI — uchqun (sparkle). Boshqa ikonkalar chiziqli, bu ham shunday.
ai:'<path d="M12 3l1.9 4.6L18.5 9.5 13.9 11.4 12 16l-1.9-4.6L5.5 9.5l4.6-1.9z"/><path d="M18.5 15.5l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z"/>',clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5l3.2 2"/>',
gear:'<circle cx="12" cy="12" r="3.2"/><path d="M19 12a7 7 0 0 0-.15-1.4l2-1.6-2-3.4-2.4 1a7 7 0 0 0-2.4-1.4L13.7 2.7h-3.4l-.35 2.5a7 7 0 0 0-2.4 1.4l-2.4-1-2 3.4 2 1.6A7 7 0 0 0 5 12c0 .48.05.95.15 1.4l-2 1.6 2 3.4 2.4-1a7 7 0 0 0 2.4 1.4l.35 2.5h3.4l.35-2.5a7 7 0 0 0 2.4-1.4l2.4 1 2-3.4-2-1.6c.1-.45.15-.92.15-1.4z"/>',
boxIn:'<path d="M16.5 9.4 7.5 4.2M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.3 7 12 12l8.7-5M12 22V12"/>',
list:'<path d="M8 6h13M8 12h13M8 18h13"/><path d="M3 6h.01M3 12h.01M3 18h.01"/>',
globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',

/* --- Emoji o'rnini bosuvchilar ---
   Bir oila: 24x24 to'r, chiziqli, qalinligi 1.7, uchlari yumaloq.
   Emoji tizimli emas edi: har platformada boshqacha chiziladi, rangi
   interfeys palitrasiga bo'ysunmaydi va matn qatorida balandligi
   sakraydi. Bular esa `currentColor` bilan yashaydi. */
search:'<circle cx="11" cy="11" r="7"/><path d="M20.2 20.2 16 16"/>',
camera:'<path d="M3 8.8A2.3 2.3 0 0 1 5.3 6.5h1.9l1.2-2h7.2l1.2 2h1.9A2.3 2.3 0 0 1 21 8.8v8.9a2.3 2.3 0 0 1-2.3 2.3H5.3A2.3 2.3 0 0 1 3 17.7z"/><circle cx="12" cy="13" r="3.6"/>',
image:'<rect x="3" y="4.5" width="18" height="15" rx="2.5"/><circle cx="8.6" cy="10" r="1.7"/><path d="m21 15.5-4.8-4.8-9.2 8.8"/>',
upload:'<path d="M12 16.5V4M7.5 8.5 12 4l4.5 4.5"/><path d="M4 16.5v2A2.5 2.5 0 0 0 6.5 21h11a2.5 2.5 0 0 0 2.5-2.5v-2"/>',
download:'<path d="M12 4v12.5M7.5 12 12 16.5 16.5 12"/><path d="M4 16.5v2A2.5 2.5 0 0 0 6.5 21h11a2.5 2.5 0 0 0 2.5-2.5v-2"/>',
clipboard:'<rect x="5" y="4" width="14" height="17" rx="2.3"/><path d="M9 5.2A1.7 1.7 0 0 1 10.7 3.5h2.6A1.7 1.7 0 0 1 15 5.2V6.5H9z"/><path d="M9 11.5h6M9 15.5h4"/>',
receipt:'<path d="M6 3h12v18l-2.4-1.5L13.2 21 12 19.6 10.8 21l-2.4-1.5L6 21z"/><path d="M9.4 8.2h5.2M9.4 12.2h5.2"/>',
cash:'<rect x="2.5" y="6" width="19" height="12" rx="2.3"/><circle cx="12" cy="12" r="2.7"/><path d="M6 10.2v3.6M18 10.2v3.6"/>',
user:'<circle cx="12" cy="8" r="3.6"/><path d="M4.8 20a7.2 7.2 0 0 1 14.4 0"/>',
scissors:'<circle cx="6.2" cy="6.2" r="2.4"/><circle cx="6.2" cy="17.8" r="2.4"/><path d="M20 4 8.3 15.9M20 20 8.3 8.1"/>',
truck:'<rect x="2.5" y="6.5" width="11.5" height="9" rx="1.4"/><path d="M14 9.6h3.6l3 3.1v2.8H14z"/><circle cx="7" cy="18" r="1.9"/><circle cx="17.4" cy="18" r="1.9"/>',
book:'<path d="M4 5A2.5 2.5 0 0 1 6.5 2.5H20v16.2H6.5A2.5 2.5 0 0 0 4 21.2z"/><path d="M4 18.7A2.5 2.5 0 0 1 6.5 16.2H20"/>',
factory:'<path d="M2.8 20.5V11l5.4 3.1V11l5.4 3.1V6.5h4.4l1.2 14z"/><path d="M2 20.5h20"/>',
pencil:'<path d="M4 20h4.2L20.6 7.6a2.2 2.2 0 0 0-3.1-3.1L5 16.9z"/><path d="m14.6 6.5 3.1 3.1"/>',
key:'<circle cx="7.6" cy="14.6" r="3.8"/><path d="M10.4 11.9 20 4.3M17.2 7.1l2.2 2.2M14.9 9.4l2.2 2.2"/>',
repeat:'<path d="M4.5 8.5H15a4 4 0 0 1 4 4"/><path d="M7.5 5.5 4.5 8.5l3 3"/><path d="M19.5 15.5H9a4 4 0 0 1-4-4"/><path d="m16.5 18.5 3-3-3-3"/>',
printer:'<path d="M6.6 9.5V3.6h10.8v5.9"/><rect x="3" y="9.5" width="18" height="7.2" rx="2"/><path d="M6.6 13.8h10.8v6.6H6.6z"/>',
calendar:'<rect x="3" y="5" width="18" height="16" rx="2.4"/><path d="M3 10h18M8.2 3v4M15.8 3v4"/>',
sound:'<path d="M4 9.4h3.3L12 5.4v13.2L7.3 14.6H4z"/><path d="M15.8 9.2a4.4 4.4 0 0 1 0 5.6"/><path d="M18.6 6.6a8.2 8.2 0 0 1 0 10.8"/>',
mute:'<path d="M4 9.4h3.3L12 5.4v13.2L7.3 14.6H4z"/><path d="m16.2 9.8 4.4 4.4M20.6 9.8l-4.4 4.4"/>',
bolt:'<path d="M13.6 2.5 4.8 13.4h5.8l-.8 8.1 9.4-11.4h-5.9z"/>',
chat:'<path d="M21 11.6a8.2 8.2 0 0 1-11.9 7.3L3.6 20.4l1.5-5.4A8.2 8.2 0 1 1 21 11.6z"/>',
play:'<path d="M8.4 5.4v13.2L19 12z"/>',
folder:'<path d="M3 7.4A2 2 0 0 1 5 5.4h3.8l2 2.6H19a2 2 0 0 1 2 2v8.6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
x:'<path d="M6.2 6.2 17.8 17.8M17.8 6.2 6.2 17.8"/>',
tick:'<path d="m4.8 12.6 4.9 4.9L19.2 6.5"/>',
arrowDown:'<path d="M12 4.2v15.2M6.2 13.2 12 19.4l5.8-6.2"/>',
arrowUp:'<path d="M12 19.8V4.6M6.2 10.8 12 4.6l5.8 6.2"/>',
arrowLeft:'<path d="M19.4 12H4.6M10.8 5.8 4.6 12l6.2 6.2"/>',
arrowRight:'<path d="M4.6 12h14.8M13.2 5.8 19.4 12l-6.2 6.2"/>',
arrowOut:'<path d="M7 17 17 7"/><path d="M8.4 7H17v8.6"/>',
refresh:'<path d="M20.2 12a8.2 8.2 0 1 1-2.4-5.8"/><path d="M20.4 4.4v5.4H15"/>'};
const icon=(n,s=17)=>`<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${I[n]||''}</svg>`;
/* Mijoz yasagan bo'limning belgisi.
   Ilgari bu yerda emoji saqlanardi (bazada matn sifatida). Endi ikonka
   NOMI saqlanadi. Eski yozuvlar buzilmasin: nom oilada topilmasa,
   saqlangan matn o'z holicha chiqadi. */
const BOLIM_IKON=[
  ['clipboard',"Ro'yxat"],['truck','Yetkazish'],['gear','Jarayon'],
  ['receipt','Hujjat'],['box','Ombor'],['cash','Pul'],
  ['calendar','Jadval'],['folder','Papka'],['users','Odamlar'],
  ['chart','Hisobot'],
];
const bolimIkon=(v,o=18)=>I[v]?icon(v,o):esc(String(v||''));

const boxLogo=s=>`<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8l-9-5-9 5v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/></svg>`;
// Element yo'q bo'lsa YIQILMAYDI. Ilgari to'g'ridan-to'g'ri
// `.innerHTML` qo'yilardi va sahifada `loginLogo` bo'lmasa butun
// `globals.js` shu yerda uzilardi — undan keyingi hamma narsa
// (`esc`, `t`, tarjimalar) e'lon qilinmay qolardi.
const _logo=(id,o)=>{const e=document.getElementById(id); if(e)e.innerHTML=boxLogo(o);};
_logo('loginLogo',36);
_logo('brandLogo',22);

/* ================= API ================= */
const API='';

// Standart til — kirill (mijoz shunday ishlaydi)
let APP_LANG = localStorage.getItem('tizim_lang') || 'uz_cyr';

/* ===== Bazadagi qiymatlarni kirillcha ko'rsatish =====
   Status/rol/to'lov turi bazada lotincha saqlanadi (mantiq shunga bog'liq),
   ekranda esa kirillcha ko'rinadi. Baza tegilmaydi. */
const KIR = {
  // buyurtma statuslari
  'Kutishda':'Кутишда', 'Muzokara':'Музокара', 'Sexda kesilmoqda':'Цехда кесилмоқда',
  'Omborga tushdi':'Омборга тушди', 'Yetkazib berildi':'Мижозга берилди',
  'Bekor qilindi':'Бекор қилинди',
  // rollar
  'Rahbar':'Раҳбар', 'Menejer':'Менежер', 'Sklad mudiri':'Склад мудири',
  "Sex boshlig'i":'Цех бошлиғи', 'Buxgalter':'Бухгалтер',
  // to'lov turlari va usullari
  'Naqd':'Нақд', 'Qarz':'Қарз', "Keyinroq to'lash":'Кейинроқ тўлаш',
  "O'tkazma":'Ўтказма', 'Karta':'Карта',
  // mijoz toifalari
  'VIP':'VIP', 'Standart':'Стандарт', 'Yangi':'Янги',
  // kassa / xarajat turlari
  'Kirim':'Кирим', 'Chiqim':'Чиқим', 'Avans':'Аванс', 'Xarajat':'Харажат',
  // material bo'limlari
  "Qog'oz":'Қоғоз', 'Karton':'Картон', 'Gofrokarton':'Гофрокартон', 'Kley':'Клей',
  "Bo'yoq":'Бўёқ', 'Lak':'Лак', 'Plyonka':'Плёнка', 'Boshqa':'Бошқа',
  // lavozimlar
  'Ishchi':'Ишчи', 'Stanokchi':'Станокчи', 'Haydovchi':'Ҳайдовчи', 'Texnolog':'Технолог',
  // yetkazib beruvchi turi
  'Pechat':'Печат (кўчада принт)',
};
// kir('Kutishda') -> 'Кутишда'; noma'lum qiymat o'zgarmay qaytadi
const kir = v => KIR[v] || v || '';
function setLang(l) { APP_LANG = l; localStorage.setItem('tizim_lang', l); if (ME) { location.reload(); } }

const DICT = {
  'uz_lat': {
    'smeta': "Yangi buyurtma (smeta)", 'smeta_sub': "Tavsif → tannarx → taklif narxi",
    'clients': "Mijozlar", 'clients_sub': "Toifa, qarz chegarasi va hisob-kitob kartalari",
    'mats': "Materiallar", 'mats_sub': "Xomashyo va material kataloglari",
    'mode': "Rejim",

    'lang_name': "O'zbek (Lotin)",
    'dash': "Boshqaruv paneli", 'dash_sub': "Bugungi savdo, qarzlar va ogohlantirishlar",
    'orders': "Buyurtmalar", 'orders_sub': "Bosqichlar soha profilidan olinadi",
    'wh': "Ombor", 'wh_sub': "Xomashyo partiyalari va tayyor mahsulot",
    'calc': "Yangi buyurtma (smeta)", 'calc_sub': "Tavsif → tannarx → taklif narxi",
    'crm': "Mijozlar", 'crm_sub': "Toifa, qarz chegarasi va hisob-kitob kartalari",
    'mat': "Materiallar katalogi", 'mat_sub': "Materiallar — bo'limlar bo'yicha",
    'hr': "Xodimlar", 'hr_sub': "Ishbay va oylik hisob-kitobi",
    'zakup': "Xarid (Zakup)", 'zakup_sub': "Material olish — naqd yoki qarzga, yetkazib beruvchi qarzi",
    'fin': "Moliya", 'fin_sub': "Mijozlar qarzi, pul oqimi, amallar tarixi",
    'kassa': "Kassa jurnali", 'kassa_sub': "Kirim-chiqim daftari — kimdan keldi, kimga ketdi",
    'exp': "Sex xarajatlari", 'exp_sub': "Material, ta'mir, ehtiyot qism — umumiy rasxodlar",
    'set': "Sozlamalar", 'set_sub': "Foydalanuvchilar, brak %, ustama, qarz chegarasi",
    'all_firms': "Barcha firmalar",
    'save': "Saqlash", 'cancel': "Bekor qilish", 'add': "Qo'shish", 'delete': "O'chirish", 'back': "Orqaga",
    'good_morning': "Xayrli tong", 'good_day': "Xayrli kun", 'good_evening': "Xayrli kech",
    'paper_enough_for': "material {days} kunga yetadi", 'restock_warehouse': "Omborga kirim qiling", 'left_in_stock': "{amount} qoldi",
    'today_sales': "Bugungi savdo", 'month_sales': "Oylik savdo", 'client_debt': "Mijozlar qarzi", 'they_will_pay': "bizga to'lashadi",
    'our_debt': "Bizning qarzimiz", 'to_suppliers': "yetkazib beruvchilarga", 'sales_dynamics': "Savdo dinamikasi — 6 oy",
    'month_suffix': "-oy", 'profit_share': "Foyda ulushi (oyma-oy):",
  },
  'uz_cyr': {
    'smeta': "Янги буюртма (смета)", 'smeta_sub': "Тавсиф → таннарх → таклиф нархи",
    'clients': "Мижозлар", 'clients_sub': "Тоифа, қарз чегараси ва ҳисоб-китоб карталари",
    'mats': "Материаллар", 'mats_sub': "Хомашё ва материал каталоглари",
    'mode': "Режим",

    'lang_name': "Ўзбек (Кирилл)",
    'dash': "Бошқарув панели", 'dash_sub': "Бугунги савдо, қарзлар ва огоҳлантиришлар",
    'orders': "Буюртмалар", 'orders_sub': "Босқичлар соҳа профилидан олинади",
    'wh': "Омбор", 'wh_sub': "Хомашё партиялари ва тайёр маҳсулот",
    'calc': "Янги буюртма (смета)", 'calc_sub': "Тавсиф → таннарх → таклиф нархи",
    'crm': "Мижозлар", 'crm_sub': "Тоифа, қарз чегараси ва ҳисоб-китоб карталари",
    'mat': "Материаллар каталоги", 'mat_sub': "Материаллар — бўлимлар бўйича",
    'hr': "Ходимлар", 'hr_sub': "Сдельщина ва ойлик ҳисоб-китоби",
    'zakup': "Харид (Закуп)", 'zakup_sub': "Материал олиш — нақд ёки қарзга, етказиб берувчи қарзи",
    'fin': "Молия", 'fin_sub': "Мижозлар қарзи, пул оқими, амаллар тарихи",
    'kassa': "Касса журнали", 'kassa_sub': "Кирим-чиқим дафтари — кимдан келди, кимга кетди",
    'exp': "Цех харажатлари", 'exp_sub': "Материал, таъмир, эҳтиёт қисм — умумий расходлар",
    'set': "Созламалар", 'set_sub': "Фойдаланувчилар, Брак %, устама, қарз чегараси",
    'all_firms': "Барча фирмалар",
    'save': "Сақлаш", 'cancel': "Бекор қилиш", 'add': "Қўшиш", 'delete': "Ўчириш", 'back': "Орқага",
    'good_morning': "Хайрли тонг", 'good_day': "Хайрли кун", 'good_evening': "Хайрли кеч",
    'paper_enough_for': "материал {days} кунга етади", 'restock_warehouse': "Омборга кирим қилинг", 'left_in_stock': "{amount} қолди",
    'today_sales': "Бугунги савдо", 'month_sales': "Ойлик савдо", 'client_debt': "Мижозлар қарзи", 'they_will_pay': "бизга тўлашади",
    'our_debt': "Бизнинг қарзимиз", 'to_suppliers': "етказиб берувчиларга", 'sales_dynamics': "Савдо динамикаси — 6 ой",
    'month_suffix': "-ой", 'profit_share': "Фойда улуши (ойма-ой):",
  },
  'ru': {
    'smeta': "Новый заказ (смета)", 'smeta_sub': "Описание → себестоимость → цена",
    'clients': "Клиенты", 'clients_sub': "Категория, лимит долга и расчёты",
    'mats': "Материалы", 'mats_sub': "Каталоги сырья и материалов",
    'mode': "Режим",

    'lang_name': "Русский",
    'dash': "Панель управления", 'dash_sub': "Сегодняшние продажи, долги и уведомления",
    'orders': "Заказы", 'orders_sub': "Этапы берутся из профиля отрасли",
    'wh': "Склад", 'wh_sub': "Партии сырья и готовая продукция",
    'calc': "Новый заказ (смета)", 'calc_sub': "Описание → себестоимость → цена",
    'crm': "Клиенты", 'crm_sub': "Категории, лимиты долга и карточки",
    'mat': "Каталог материалов", 'mat_sub': "Материалы — по разделам",
    'hr': "Сотрудники", 'hr_sub': "Сдельщина и расчет зарплаты",
    'zakup': "Закупки", 'zakup_sub': "Прием материала — нал/долг, долг поставщикам",
    'fin': "Финансы", 'fin_sub': "Долги клиентов, денежный поток, история",
    'kassa': "Касса", 'kassa_sub': "Приход-расход — от кого, кому",
    'exp': "Расходы цеха", 'exp_sub': "Материалы, ремонт, запчасти — общие расходы",
    'set': "Настройки", 'set_sub': "Пользователи, % брака, наценки, лимит долга",
    'all_firms': "Все фирмы",
    'save': "Сохранить", 'cancel': "Отмена", 'add': "Добавить", 'delete': "Удалить", 'back': "Назад",
    'good_morning': "Доброе утро", 'good_day': "Добрый день", 'good_evening': "Добрый вечер",
    'paper_enough_for': "материала хватит на {days} дн.", 'restock_warehouse': "Пополните склад", 'left_in_stock': "осталось {amount}",
    'today_sales': "Продажи сегодня", 'month_sales': "Продажи за месяц", 'client_debt': "Долги клиентов", 'they_will_pay': "нам заплатят",
    'our_debt': "Наш долг", 'to_suppliers': "поставщикам", 'sales_dynamics': "Динамика продаж — 6 мес.",
    'month_suffix': "-мес", 'profit_share': "Доля прибыли (по месяцам):",
  }
};
function t(key) { return DICT[APP_LANG][key] || key; }

// Firma filtri HAR OChILGANDA "Barcha firmalar" dan boshlanadi — eski tanlangan
// firma boshqa firma ma'lumotini doimiy YASHIRIB qo'ymasin ("ma'lumot yo'qoldi" shikoyati).
// Filtr faqat joriy sessiyada ishlaydi, saqlanmaydi.
var FIRM='';
try{ localStorage.removeItem('tizim_firm'); }catch(e){}
function setFirm(v){FIRM=v;firmBanner();if(ME)go(PAGE);}
// Firma filtri yoqilganda ogohlantirish bandi — ma'lumot "yo'qolgandek"
// ko'rinmasligi uchun: aslida boshqa firmada, filtrni olib qo'yish kerak
function firmBanner(){
  let b=document.getElementById('firmBanner');
  if(!b){
    b=document.createElement('div'); b.id='firmBanner';
    b.style.cssText='position:sticky;top:0;z-index:50;background:#f9d97a;color:#5a4400;'
      +'padding:7px 14px;font-size:12.5px;text-align:center;cursor:pointer;font-weight:600';
    b.onclick=()=>{const s=document.getElementById('firmSel');if(s)s.value='';setFirm('');};
    const c=document.getElementById('content'); if(c&&c.parentNode)c.parentNode.insertBefore(b,c);
  }
  if(FIRM){ b.style.display='';
    b.innerHTML=`${icon('factory',13)} Фақат «${esc(FIRM)}» фирмаси кўрсатиляпти — бошқа фирма маълумотлари ЯШИРИН. `
      +`<u>Ҳаммасини кўриш учун босинг</u>`;
  }else b.style.display='none';
}
async function loadFirms(){
  try{const fs=await api('/api/kassa/firms');
    window._firms=fs;   // formalarda firma tanlash uchun
    const sel=document.getElementById('firmSel');
    if(fs.length){sel.style.display='';
      sel.innerHTML=`<option value="">${t('all_firms')}</option>`+fs.map(x=>`<option value="${esc(x)}" ${FIRM===x?'selected':''}>${esc(x)}</option>`).join('');
    }else sel.style.display='none';
    firmBanner();
  }catch(e){}
}
let TOKEN=localStorage.getItem('tizim_token')||'';
let ME=JSON.parse(localStorage.getItem('tizim_me')||'null');
// Yuborilib, hali javobi kelmagan o'zgartiruvchi so'rovlar: "METOD yo'l tana" -> Promise.
// Tugma ikki marta bosilsa, ikkinchisi shu turgan so'rovning javobini oladi —
// serverga ikkinchi so'rov ketmaydi, demak dublikat yozuv paydo bo'lmaydi.
// (Birinchi so'rov tugagach kalit bo'shaydi — keyin ataylab qayta yuborsa ishlaydi.)
const _yuborilgan = new Map();

async function api(path,opts={},body){
  // ikkala uslub: api(path,{method,body}) yoki api(path,'POST',data)
  if(typeof opts==='string'){opts={method:opts,body:body!==undefined?JSON.stringify(body):undefined};}
  if(FIRM&&(!opts.method||opts.method==='GET')&&!path.includes('firm=')){
    path+=(path.includes('?')?'&':'?')+'firm='+encodeURIComponent(FIRM);
  }
  const metod=(opts.method||'GET').toUpperCase();
  const kalit = metod==='GET' ? null : metod+' '+path+' '+(opts.body||'');
  if(kalit&&_yuborilgan.has(kalit))return _yuborilgan.get(kalit);

  const soruv=(async()=>{
    const r=await fetch(API+path,{...opts,headers:{'Content-Type':'application/json','Authorization':'Bearer '+TOKEN,...(opts.headers||{})}});
    if(r.status===401){logout();throw new Error('Avtorizatsiya');}
    if(!r.ok){const e=await r.json().catch(()=>({detail:'Хатолик'}));throw new Error(e.detail||'Хатолик');}
    return r.json();
  })();

  if(kalit){
    _yuborilgan.set(kalit,soruv);
    // javob kelgach (yoki xato bo'lsa) kalitni bo'shatamiz
    soruv.finally(()=>_yuborilgan.delete(kalit)).catch(()=>{});
  }
  return soruv;
}
const post=(p,body)=>api(p,{method:'POST',body:JSON.stringify(body)});
const money=n=>new Intl.NumberFormat('ru-RU').format(Math.round(n))+" сўм";
const mshort=n=>Math.abs(n)>=1e9?(n/1e9).toFixed(1)+' mlrd':Math.abs(n)>=1e6?(n/1e6).toFixed(1)+' mln':new Intl.NumberFormat('ru-RU').format(Math.round(n));
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

