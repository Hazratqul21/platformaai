/* ================= LENDING — kirishdagi tanishtiruv sahifasi =========
   Nega kerak: ilgari birinchi ko'ringan narsa login oynasi edi. Login
   oynasi «bu nima?» degan savolga javob bermaydi — u faqat allaqachon
   biladigan odam uchun. Platforma ko'p mijozli bo'lgach, sahifaga
   birinchi kelgan odam nima taklif qilinayotganini ko'rishi kerak.

   Kirgan foydalanuvchi buni umuman ko'rmaydi (tokeni bor -> to'g'ri
   tizimga o'tadi).
   ==================================================================== */

/* Tayyor sohalar — ZAXIRA ro'yxat.
   Asosiy manba backend: `GET /api/platforma/sohalar` (ochiq endpoint).
   Ilgari bu yerdagi ro'yxat YAGONA manba edi va izohda «API yopiq»
   deb yozilgan edi — endi u ochiq. Natijada yangi yo'nalish
   qo'shilganda intro sahifasida ko'rinmasdi: 29 ta bor, 22 tasi
   yozilgan edi.
   Bu ro'yxat faqat so'rov yiqilganda ishlatiladi — sahifa bo'sh
   ko'rinmasin. */
const LND_SOHALAR = [
  "Non zavodi", "Mebel sexi", "Karton / gofra qutilar", "Beton / temir-beton",
  "Tikuvchilik sexi", "Poyabzal ishlab chiqarish", "Sut mahsulotlari",
  "Go'sht mahsulotlari", "Maishiy kimyo", "Avto servis", "Chakana do'kon",
  "Ulgurji savdo (distribyutor)", "G'isht / qurilish materiallari",
  "Kabel / elektrotexnika", "Metall konstruksiya", "Qurilish-montaj ishlari",
  "Plastik deraza / eshik", "Yog'och eshik / deraza", "Poligrafiya / bosmaxona",
  "Reklama agentligi", "Transport / logistika", "Maishiy texnika ta'miri"
];

async function lendingChiplar(){
  const box = document.getElementById('lndChips');
  if(!box) return;
  let nomlar = LND_SOHALAR;
  try{
    const d = await (await fetch(API+'/api/platforma/sohalar')).json();
    if(d.sohalar && d.sohalar.length) nomlar = d.sohalar.map(x=>x.nom);
  }catch(e){ /* zaxira ro'yxat ishlatiladi */ }

  // Sarlavhadagi raqam ham shu yerdan — qo'lda yozilgan «22 soha»
  // eskirib qolgandi.
  const kick = document.querySelector('.lnd-hero .kicker');
  if(kick) kick.textContent =
    `Konstruktor · ${nomlar.length} yo'nalish · O'zbekiston uchun`;

  box.innerHTML = '';
  nomlar.forEach(nom => {
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
  lendingKorinish();
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

/* RO'YXATDAN O'TISH FORMASI BU YERDAN KO'CHDI.
   Endi u uch qadamli sehrgar: `static/js/core/royxat.js` (rxOch).
   Bu yerda faqat yo'nalishlar ro'yxati funksiyalari qoldi — ular
   sehrgar tomonidan ham ishlatiladi. */

/* --------------------------------------------------------------------
   SCROLL BILAN OCHILISH

   `data-korin` belgisi qo'yilgan bo'lim ko'rinishga kirganda ochiladi.
   Nega IntersectionObserver, `scroll` hodisasi emas: scroll hodisasi
   sekundiga o'nlab marta ishlaydi va har safar `getBoundingClientRect`
   chaqirsak sahifa qotadi. Observer esa brauzerning o'zi hisoblab
   beradi.

   Bir marta ochilgach kuzatuvdan chiqariladi — yuqoriga qaytganda
   qayta animatsiya bo'lmasin, bu bezovta qiladi.
   -------------------------------------------------------------------- */
function lendingKorinish(){
  const nishonlar=document.querySelectorAll('[data-korin]');
  if(!nishonlar.length) return;
  if(!('IntersectionObserver' in window)) return;   // kontent baribir ko'rinadi

  const idish=document.getElementById('lending');
  const hammasini_och=()=>nishonlar.forEach(e=>e.classList.add('kordi'));

  // Yashirishni FAQAT shu yerda yoqamiz. Agar quyidagi kod umuman
  // ishlamasa, `.korin-yoniq` qo'yilmaydi va kontent ko'rinib turadi.
  idish.classList.add('korin-yoniq');

  let ku;
  try{
    ku=new IntersectionObserver((yozuvlar)=>{
      yozuvlar.forEach(y=>{
        if(!y.isIntersecting) return;
        y.target.classList.add('kordi');
        ku.unobserve(y.target);
      });
    },{threshold:.12, rootMargin:'0px 0px -40px 0px'});
    nishonlar.forEach(e=>ku.observe(e));
  }catch(e){ hammasini_och(); return; }

  // XAVFSIZLIK TAYMERI.
  // Kuzatuvchi ba'zi muhitlarda umuman ishga tushmaydi (brauzerda
  // sinovda aynan shunday bo'ldi: birorta ham chaqiruv kelmadi).
  // Bunda kontent abadiy ko'rinmay qolardi. 1.5 soniyadan keyin
  // ochilmagani qolsa — majburan ochiladi. Odam scroll qilib
  // ulgurmagan bo'lsa ham, bo'sh ekrandan ko'ra ko'ringani yaxshi.
  setTimeout(()=>{
    const qolgan=[...nishonlar].filter(e=>!e.classList.contains('kordi'));
    if(qolgan.length===nishonlar.length) hammasini_och();
  }, 1500);
}
