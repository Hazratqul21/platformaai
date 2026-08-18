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

/** Ro'yxatdan o'tish hali yo'q — bu A bosqichida ochiladi.
    Yolg'on tugma qo'yilmaydi: bosilganda halol javob beriladi. */
function lendingRoyxat(){
  toast('w', 'alertic', 'Hozircha yopiq',
        "Ro'yxatdan o'tish tayyorlanmoqda. Hozir tizimga mavjud login bilan kiriladi.");
}

function lendingBoshla(){
  lendingChiplar();
  document.getElementById('lending').classList.add('on');
  document.getElementById('loginScreen').style.display = 'none';
}
