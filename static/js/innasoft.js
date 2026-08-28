/* INNASOFT korporativ sayt — interaktiv qatlam.
 *
 * FALSAFA: progressiv yaxshilanish. HTML/CSS o'zicha to'liq ishlaydi;
 * bu fayl ustiga MOTION qo'shadi. Foydalanuvchi `prefers-reduced-motion`
 * yoqsa yoki JS o'chsa — hech narsa yashirilmaydi, sayt darrov ko'rinadi.
 */
(function () {
  'use strict';
  var root = document.documentElement;
  var kamHarakat = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Motion faqat harakat kamaytirilmagan bo'lsa yoqiladi.
  // `.motion` sinfi CSS'dagi barcha animatsiyani ochadi.
  if (!kamHarakat) root.classList.add('motion');

  document.addEventListener('DOMContentLoaded', function () {

    /* ---- Mobil menyu (avvaldan bor edi — AYNAN o'sha mexanizm) ----
       CSS `.site-nav.open` + `body.menu-open` ga tayanadi. */
    var menuButton = document.querySelector('.menu-toggle');
    var siteNav = document.getElementById('siteNav');
    function siteMenuYop() {
      if (!menuButton || !siteNav) return;
      menuButton.setAttribute('aria-expanded', 'false');
      siteNav.classList.remove('open');
      document.body.classList.remove('menu-open');
    }
    if (menuButton && siteNav) {
      menuButton.addEventListener('click', function () {
        var ochiq = menuButton.getAttribute('aria-expanded') === 'true';
        menuButton.setAttribute('aria-expanded', String(!ochiq));
        siteNav.classList.toggle('open', !ochiq);
        document.body.classList.toggle('menu-open', !ochiq);
      });
      siteNav.querySelectorAll('a').forEach(function (a) {
        a.addEventListener('click', siteMenuYop);
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') siteMenuYop();
      });
    }

    if (kamHarakat) return;   // qolgan hammasi — motion

    /* ---- Scroll-reveal — FAIL-OPEN ----
       XAVF: `.motion [data-reveal]{opacity:0}`. Agar IntersectionObserver
       bo'lmasa yoki nimadir yiqilsa, kontent ABADIY yashirin qolardi.
       Shuning uchun: (1) IO yo'q bo'lsa umuman yashirmaymiz; (2) butun
       sozlash try/catch ichida — xato bo'lsa hamma [data-reveal] ochiladi;
       (3) 4 soniyalik xavfsizlik taymeri — hali yashirin bo'lsa ochadi. */
    function hammasiniOch() {
      document.querySelectorAll('[data-reveal]').forEach(function (el) {
        el.classList.add('in');
      });
    }
    if (!('IntersectionObserver' in window)) return;  // eski brauzer — yashirmaymiz

    try {
      var revealTanlov = [
        '.proof-bar', '.manifesto .eyebrow', '.manifesto h2', '.manifesto-note',
        '.section-head', '.services-intro', '.approach-title',
        '.cta-section .eyebrow', '.cta-section h2', '.cta-section .cta-button'
      ];
      revealTanlov.forEach(function (sel) {
        document.querySelectorAll(sel).forEach(function (el) {
          el.setAttribute('data-reveal', '');
        });
      });
      ['.product-grid', '.service-list', '.approach-steps']
        .forEach(function (sel) {
          var g = document.querySelector(sel);
          if (g) { g.setAttribute('data-reveal', ''); g.setAttribute('data-reveal-stagger', ''); }
        });

      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
        });
      }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });

      document.querySelectorAll('[data-reveal]').forEach(function (el) { io.observe(el); });

      // Xavfsizlik to'ri: 3.5s dan keyin hali ochilmagani SO'ZSIZ ochiladi.
      // `innerHeight`'ga bog'liq EMAS — ba'zi muhitlarda u 0 bo'lib IO
      // umuman ishlamaydi; unda ham kontent yashirin qolmasligi shart.
      // Odatiy holatda foydalanuvchi 3.5s ichida scroll qiladi va IO
      // progressiv ochadi; bu taymer faqat kafolat.
      setTimeout(hammasiniOch, 3500);
    } catch (err) {
      hammasiniOch();   // nimadir yiqildi — hech narsa yashirin qolmasin
    }

    /* ---- Scroll progress chizig'i (yuqorida) ---- */
    var bar = document.createElement('div');
    bar.className = 'scroll-progress';
    document.body.appendChild(bar);
    var tick = false;
    function yangila() {
      var h = document.documentElement;
      var jami = h.scrollHeight - h.clientHeight;
      var foiz = jami > 0 ? (h.scrollTop || document.body.scrollTop) / jami : 0;
      bar.style.width = (foiz * 100).toFixed(2) + '%';
      tick = false;
    }
    window.addEventListener('scroll', function () {
      if (!tick) { requestAnimationFrame(yangila); tick = true; }
    }, { passive: true });
    yangila();
  });
})();
