AI Destekli Piyasa Bias ve\
Onceliklendirme Platformu

Guncellenmis Is Plani, MVP Kapsami ve Fazlandirma Notu

  -----------------------------------------------------------------------
  Bu belge, kripto icin saatlik calisan ana motor ile FX / degerli
  metaller / endeksler icin sadece onemli veri gunlerinde devreye giren
  event-driven overlay modulunu tek cati altinda tanimlar. Sistem trade
  emri vermez; yon teyidi ve onceliklendirme saglar.
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------

1\. Yonetici Ozeti

Platform iki cekirdekten olusur. Cekirdek 1, volatil kripto varliklar
icin saatlik bias ve Top 4 / Next 2 oncelik listesi uretir. Cekirdek 2
ise EURUSD, GBPUSD, USDJPY, XAUUSD, XAGUSD, US500, US100, US30, DAX40,
FTSE100 ve JP225 gibi enstrumanlarda sadece onemli veri gunlerinde aktif
olan takvim tabanli makro overlay gorevi gorur.

  -----------------------------------------------------------------------
  MVP\'nin hedefi \'olabildigince cok sey gostermek\' degil, karar
  yorgunlugunu azaltan tek bir agirlikli cikti uretmektir. Ham veri
  kalemleri arkada saklanir; kullanici tarafinda asiri kalabalik pano
  yerine tek bias, confidence ve kisa gerekce gorunur.
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------

2\. Problem ve Cozum

**•** Piyasada sorun veri eksikligi degil; hizli akan ve birbiriyle
catisan veri fazlaligidir.

**•** Kripto tarafinda flow, OI, funding ve likidasyon gibi sert veri
kaynaklari vardir; makro tarafta ise veri gunleri ve resmi aciklamalar
belirleyicidir.

**•** Cozum, ham metrikleri tek tek listelemek yerine agirliklandirilmis
birlesik skor ve tek bir yon karari ureten sistem kurmaktir.

3\. MVP Tasarim Prensipleri

  --------------------------------------------------------------------------
  **Prensip**      **Karar**               **Kazanim**
  ---------------- ----------------------- ---------------------------------
  Olculebilirlik   Deterministic scoring + 1 aylik canli kayit ile
                   shadow test             performans net olculur

  Dusuk maliyet    LLM sadece gerekli      Tum watchlist uzerinde surekli
                   yerde                   pahali islem yapilmaz

  Netlik           Tek agirlikli son cikti Kullanici panosu kalabalik olmaz

  Fazlandirma      Kripto surekli, makro   Zaman ve entegrasyon maliyeti
                   event-driven            azalir
  --------------------------------------------------------------------------

4\. Kapsam

4.1 Cekirdek 1 - Crypto Bias Engine

**•** Saatlik unified bias: bullish / bearish / neutral

**•** Confidence skoru, kisitli sayida ana driver ozeti ve Top 4 / Next
2

**•** Anomali alarmlari: flow, OI, funding, likidasyon, narrative shift

**•** X ve haber katmani sadece shortlisted coinlerde devreye girer

4.2 Cekirdek 2 - Macro Event Overlay

**•** Sadece onemli veri, merkez bankasi, enerji veya jeopolitik olay
gunlerinde aktif olur

**•** Gun basi event ozeti, veri oncesi alarm, veri sonrasi bias, gun
sonu review uretir

**•** Amaci tam zamanli sinyal degil; event gunlerinde yon teyidi ve
risk farkindaligi saglamaktir

4.3 Bilerek Disarida Birakilanlar

**•** Entry, stop-loss, take-profit, otomatik emir ve senaryo yonetimi

**•** Sesli rapor, agir dashboard ve historical replay karmasasi

**•** Tum FX / CFD evreni icin 24/7 yorum motoru

5\. Hedef Varlik Evreni

  ------------------------------------------------------------------------
  **Kategori**   **Dahil Edilenler**                 **Not**
  -------------- ----------------------------------- ---------------------
  Kripto         BTC, ETH, SOL, XRP, BNB, ADA, SUI,  ONDO ve TAO ikinci
  (surekli)      TON                                 dalga veya
                                                     experimental slot

  Makro overlay  EURUSD, GBPUSD, USDJPY, XAUUSD,     Sadece onemli takvim
                 XAGUSD, US500, US100, US30, DAX40,  gunlerinde aktif
                 FTSE100, JP225                      

  Baglam katmani ABD makro verileri, enerji, secili  Ayrica trade evreni
                 enflasyon/gida, jeopolitik/savas    degil; karar baglami
  ------------------------------------------------------------------------

6\. Soz Verilen Ciktilar

6.1 Cekirdek 1 Ciktilari

  ------------------------------------------------------------------------
  **Cikti**      **Icerik**                                **Frekans**
  -------------- ----------------------------------------- ---------------
  Unified Bias   Tek yon karari + confidence + 2-3 ana     Saatlik
                 gerekce                                   

  Top 4 / Next 2 En net ve en yuksek kaliteli coin listesi Saatlik

  Anomali Alarmi Akis, OI, funding, liquidation veya       Olay bazli
                 narrative sapmasi                         

  Debug Mode     Gerekirse alt metrikler teknik ekip icin  Istege bagli
                 gorunur                                   
  ------------------------------------------------------------------------

6.2 Cekirdek 2 Ciktilari

  -----------------------------------------------------------------------
  **Cikti**       **Icerik**                              **Zaman**
  --------------- --------------------------------------- ---------------
  Daily Event     Gunun yuksek etkili verileri ve         Gun basi
  Summary         etkilenecek varliklar                   

  Pre-Event Alert 15-30 dk once uyarı ve risk tonu        Veri oncesi

  Post-Event Bias Actual/forecast yorumu ve ilk yon       Veri sonrasi
                  karari                                  

  Event-Day       Piyasa veriyle ayni yone gitti mi,      Gun sonu
  Review          false start var mi                      
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------
  Kullanicinin gorecegi ana ekran sade olmalidir: tek bias, confidence,
  kisa gerekce ve oncelik listesi. Flow, funding, OI gibi ham kalemler
  sadece teknik inceleme veya debug modunda acilmalidir.
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------

7\. Mimari Ozet

**•** Scheduler ve ingestion katmani veri cekimini tek merkezde toplar.

**•** Grok, secilmis X hesaplari ve web basliklari uzerinden scout
gorevi yapar.

**•** Gemini, ham metni standart JSON alanlarina normalizer eder ve
event/class etiketleri uretir.

**•** Deterministic scoring engine, tum nicel ve nitel girdilere agirlik
vererek tek bir birlesik skor uretir.

**•** GPT Commander, son sentez ve yayinlanacak kisitli metin
ciktilarini olusturur.

**•** Opsiyonel Claude Critic, yalnizca conflict / mismatch /
high-impact durumda devreye girer.

8\. Claude Critic Gerekli mi?

Sürekli calisan bir Claude benzeri critic katmani MVP icin zorunlu
degildir. Ancak modeller arasi uyumsuzluk, deterministic skor ile
commander sonucu arasinda ciddi fark veya yuksek etkili haberlerde yorum
riski varsa, critic on demand mantigi ciddi deger uretir. Bu sayede
kalite artar, ama maliyet kontrolu korunur.

**•** MVP onerisi: Critic sadece disagreement score yuksekse veya olay
yuksek etkiliyse calissin.

**•** Faydasi: asiri anlatı etkisini, yanlis etiketlemeyi ve yorum
sapmasini yakalamak.

**•** Maliyeti dusuk tutar: tum watchlist degil, yalnizca final adaylar
veya catisma anlari uzerinde calisir.

9\. Birlesik Agirlikli Sonuc Mantigi

Sistem sonunda tabloyu kalabaliklastiran onlarca satir gostermek yerine,
tum parametreleri agirliklandirilmis tek bir karara indirger. Her varlik
icin son mesajin cekirdegi su olur: Unified Bias + Confidence + Kisa
Gerekce + Oncelik Sirasi.

  -----------------------------------------------------------------------
  **Katman**     **Ornek Girdiler**             **Son skora rolu**
  -------------- ------------------------------ -------------------------
  Nicel piyasa   Flow, OI, funding,             Ana agirlik
                 liquidation, market cap,       
                 volume                         

  Narrative /    X anlatisi, secili headline,   Ikincil agirlik / teyit
  haber          resmi duyuru                   

  Makro baglam   CPI, FOMC, enerji, savas,      Event gunlerinde kuvvetli
                 risk-on/off                    agirlik

  Critic /       Uyumsuzluk ve celiski tespiti  Ceza veya confidence
  mismatch                                      ayari
  -----------------------------------------------------------------------

10\. Takvim ve Basari Olcutleri

  ------------------------------------------------------------------------
  **Faz**             **Sure**      **Teslimat**
  ------------------- ------------- --------------------------------------
  Tasarim ve schema   2-3 gun       JSON semalari, agirliklar, Telegram
                                    formatlari

  Cekirdek 1 MVP      5-7 gun       Saatlik crypto bias, Top 4 / Next 2,
                                    loglama

  Cekirdek 2 overlay  3-4 gun       Takvim tetikleme, event-day raporlari

  Dry run             2-3 gun       Stabilizasyon ve hata temizligi

  Shadow forward test 4 hafta       Isabet, false alarm ve kalite raporu
  ------------------------------------------------------------------------

**•** Directional accuracy ve high-confidence hit rate

**•** False alarm rate ve gereksiz mesaj sayisi

**•** Top 4 listesinin pratik kullanisligi

**•** Unified bias ile alt katman verileri arasindaki tutarlilik

11\. Son Not

**•** X katmani 30-50 secilmis ve agirliklandirilmis hesapla sinirli
olmalidir; acik uclu tarama MVP\'yi sisirir.

**•** Makro, enerji, gida ve jeopolitik basliklar trade listesi degil;
context filter olarak kullanilmalidir.

**•** Ilk ayin basarisi, sistemin ne kadar etkileyici rapor yazdigindan
degil, tek bir net sonucun ne kadar dogru ve tutarli oldugundan
okunacaktir.
