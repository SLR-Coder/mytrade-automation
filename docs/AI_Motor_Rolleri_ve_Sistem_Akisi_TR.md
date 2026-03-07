AI Motor Rolleri, Veri Akisi ve\
Operasyonel Uygulama Plani

Muhendislik Ekibi Icin Ayrintili Teknik Aciklama

  -----------------------------------------------------------------------
  Amac, her motorun tam gorev alanini belirlemek, overlap\'i azaltmak,
  projeyi hizlandirmak ve sonunda tek bir birlesik bias cikisi ureten net
  bir sistem insa etmektir.
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------

1\. Temel Ilke

**•** Her model tek bir ana rol ustlenir; roller ust uste binmez.

**•** Nicel skor ve nihai siralama deterministic mantikla cikar; serbest
metinle belirlenmez.

**•** Kullaniciya ham veri degil, agirliklandirilmis tek sonuc sunulur.

**•** Ayrintili metrikler sadece debug / analyst modunda acilir.

2\. Ust Duzey Sistem Akisi

  ---------------------------------------------------------------------------
  **Adim**   **Katman**         **Ne yapar?**
  ---------- ------------------ ---------------------------------------------
  1          Scheduler          Saatlik veya event-based is akisini tetikler

  2          Ingestion          API verilerini ceker ve tek formatta toplar

  3          Pre-score          Tüm evren icin temel nicel puanlari hesaplar

  4          Shortlist          Yalnizca aday varliklari secip maliyeti kisar

  5          Grok               Adaylar icin X ve headline scout yapar

  6          Gemini             Ham metni etiketli JSON formatina cevirir

  7          Commander          Tum girisleri birlestirip tek bias sonucu
                                verir

  8          Critic (ops.)      Uyumsuzluk varsa ikinci goz denetimi yapar

  9          Publisher + Logger Telegram\'a yollar ve DB\'ye kaydeder
  ---------------------------------------------------------------------------

3\. Veri Katmanlari

  -----------------------------------------------------------------------
  **Kaynak**     **Icerik**                       **Kullanan**
  -------------- -------------------------------- -----------------------
  CoinGlass      Netflow, exchange assets, OI,    Deterministic engine
                 funding, liquidations            

  CoinGecko      Price, market cap, volume        Deterministic engine

  X Search / X   Secili hesaplardan post ve       Grok
  API            thread                           

  Web search /   Canli headline ve haber ozeti    Grok
  secili siteler                                  

  Resmi takvim + CPI, NFP, FOMC, EIA, jeopolitik  Macro overlay + Gemini
  economic       eventler                         
  calendar                                        

  Config repo    Allowlist, coin map, agirliklar, Tum sistem
                 tetikleme kurallari              
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------
  Sureyi kisaltmak icin butun API baglantilari tek ingestion servisinde
  toplanir. Grok, Gemini veya Commander dogrudan farkli dis API\'lere
  daginik sekilde baglanmaz.
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------

4\. Grok Motoru - Scout ve Narrative Tarama

Grok\'un rolu hizli tarama ve ilk baglam toplamadir. Grok nihai
puanlamayi yapmaz; hangi anlatilarin ve haber basliklarinin ciddiye
alinacagini ortaya cikarir.

  -----------------------------------------------------------------------
  **Baslik**        **Detay**
  ----------------- -----------------------------------------------------
  Okudugu kaynaklar 30-50 hesaplik X allowlist, ilgili coin proje
                    hesaplari, secilmis web headline kaynaklari

  Ne zaman calisir? Yalniz shortlist olusan coinlerde veya event
                    gunlerinde

  Ne arar?          Narrative shift, yeni tema, tekrar eden hikaye, acik
                    celiski, aciliyet sinyali

  Neyi okumaz?      Tum X evreni, ilgisiz hesaplar, her coin icin sonsuz
                    tarama

  Urettigi cikti    narrative_direction, narrative_score, topic_clusters,
                    contradiction_flags, source_quality

  Teknik not        Cikti JSON olur; uzun serbest metin raporu degil
  -----------------------------------------------------------------------

Grok icin kural seti

**•** Allowlist config uzerinden yonetilir; kod icine gomulmez.

**•** Her hesap icin tier, kategori ve reliability weight tutulur.

**•** Arama asset-topic bazli olur; ornegin XRP icin XRP / Ripple / XRPL
/ SEC / ETF / listing / exploit gibi temalar.

**•** Grok sonucu ana karar degil; birlesik skor icin baglam katmani
olur.

5\. Gemini Motoru - Parser, Normalizer ve Event Classifier

Gemini\'nin rolu, ham metinleri ve olay girdilerini standart alanlara
cevirmektir. Bu sayede commander ve scoring motoru her kaynagi ayni sema
icinde gorur.

  -----------------------------------------------------------------------
  **Baslik**        **Detay**
  ----------------- -----------------------------------------------------
  Okudugu veri      Grok ham ciktilari, resmi event basliklari, secili
                    duyurular, kisa haber metinleri

  Temel gorev       Dilimleme, temizleme, tekilleştirme, varlikla esleme,
                    kategori ve etki etiketi verme

  Ornek alanlar     event_type, asset_relevance, importance, urgency,
                    policy_tone, risk_theme, surprise_direction

  Kripto icin       listing, unlock, exploit, ETF, treasury, partnership,
                    regulation gibi olaylari normalize eder

  Makro icin        CPI, NFP, FOMC, EIA, geopolitical shock gibi olaylari
                    standart event nesnesine donusturur

  Urettigi cikti    Event JSON paketi ve standart etiketler
  -----------------------------------------------------------------------

Gemini neden gerekli?

**•** Farkli kaynaklardan gelen metni tek veri modeline indirger.

**•** Commander\'in metin daginikligiyla bogusmasini engeller.

**•** Deterministic motorun hangi narrative veya event\'i nasil
agirliklayacagini netlestirir.

6\. Deterministic Scoring Engine - Sistemim Omurgasi

Bu katman proje sure ve maliyet optimizasyonunun merkezidir. Nihai
siralama serbest yorumla degil, burada hesaplanan agirlikli toplam skor
ile belirlenir.

  -----------------------------------------------------------------------
  **Skor blogu**   **Ornek girdiler**                     **Rol**
  ---------------- -------------------------------------- ---------------
  Market score     price trend, volume, market cap        Temel yon
                   normalization                          altligi

  Flow score       net inflow/outflow, exchange balance   Kriptoda guclu
                   shift                                  ana katki

  Derivatives      OI, funding, liquidation pressure      Momentum ve
  score                                                   risk teyidi

  Narrative score  Grok + Gemini ciktilarindan gelen      Ikincil teyit /
                   etiketsel sonuc                        ceza

  Macro overlay    event importance, actual/forecast      Event
  score            farki, risk-on/off                     gunlerinde
                                                          kuvvetli katki

  Conflict penalty katmanlar arasi belirgin uyumsuzluk    Confidence
                                                          dusurur veya
                                                          ceza yazar
  -----------------------------------------------------------------------

Birlesik son cikti mantigi

Kullaniciya ham alt skorlar acikca gosterilmez. Sistem, bu katmanlari
agirliklandirip tek bir final mesajina indirger: Unified Bias +
Confidence + Kisa Gerekce + Oncelik. Alt skorlar debug modunda saklanir.

  -----------------------------------------------------------------------
  Ana hedef: tabloyu kalabaliklastirmamak. Kullanici \'flow 7.2, funding
  3.9, liquidation 2.1\' gormek zorunda degil. Kullanici tek cümlede
  piyasa yonunu ve guven duzeyini gormelidir.
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------

7\. GPT Commander - Final Sentez ve Yayin Karari

GPT Commander nicel skorlarin yerine gecmez. Gorevi; deterministic
motor, Grok ve Gemini ciktilarini okuyup son yayina hazir kisa mesaji
olusturmak, catisan noktalarin etkisini confidence duzeyine yansitmak ve
kullaniciya tek bir okunabilir sonuc sunmaktir.

  -----------------------------------------------------------------------
  **Baslik**        **Detay**
  ----------------- -----------------------------------------------------
  Okudugu veri      Scoring engine ciktilari, Grok narrative JSON\'u,
                    Gemini event JSON\'u, varsa critic notu

  Temel gorev       Tek bias karari, confidence ayari, 2-3 maddelik kisa
                    gerekce, risk warning uretimi

  Neyi yapmaz?      Ham veriden baslayarak serbest skor uretmez;
                    deterministic motorun yerine gecmez

  Urettigi cikti    Telegram mesajina uygun kisa ozet + makinece
                    okunabilir final JSON

  Kullanim yeri     Saatlik crypto raporu, Top 4 ozeti, event-day bias
                    ozeti
  -----------------------------------------------------------------------

8\. Claude Critic - Opsiyonel Kidemli Danisman

Claude veya benzeri bir critic motoru sürekli acik tutulmak zorunda
degildir. En dogru kullanim sekli, final kararda uyumsuzluk olustugu
anlarda ikinci bir denetleyici goz olarak devreye sokmaktir.

  -------------------------------------------------------------------------
  **Ne zaman           **Ne kontrol eder?**            **Cikti**
  cagrilir?**                                          
  -------------------- ------------------------------- --------------------
  Disagreement score   Model yorumlari ile nicel skor  critic_verdict +
  yuksekse             catisiyor mu?                   confidence_penalty

  Yuksek etkili haber  Commander asiri hikaye          risk note + override
  varsa                etkisinde kaldi mi?             tavsiyesi

  Cok yuksek           Bu confidence gercekten         quality check sonucu
  confidence           destekleniyor mu?               
  verildiyse                                           
  -------------------------------------------------------------------------

**•** MVP tavsiyesi: Claude Critic sadece belirlenmis esikler
asildiginda devreye girsin.

**•** Bu yapi kaliteyi artirir, ama surekli ek maliyet yaratmaz.

**•** Critic sonucu son komuta degil; commander ve confidence katmanina
rehber olur.

9\. Cekirdek 1 Is Akisi - Crypto Bias

  -----------------------------------------------------------------------
  **Asama**        **Detay**
  ---------------- ------------------------------------------------------
  1\. Veri cekimi  CoinGlass ve CoinGecko saatlik verileri alinir

  2\. Pre-score    Tüm coin evreni icin nicel temel skor hesaplanir

  3\. Shortlist    En anlamli 4-8 aday ayrilir

  4\. Grok         Sadece shortlist coinleri icin X ve headline taranir
  taramasi         

  5\. Gemini       Narrative ve event etiketleri standart JSON\'a doner
  normalizasyonu   

  6\. Unified      Tum katmanlar agirliklandirilir ve tek bias cikisi
  scoring          olusur

  7\. Commander    Top 4 / Next 2 ve kisa ozet mesaji uretir

  8\. Kayit        Tum kararlar DB\'ye yazilir, 1 saat sonra outcome ile
                   karsilastirilir
  -----------------------------------------------------------------------

10\. Cekirdek 2 Is Akisi - Macro Event Overlay

  -----------------------------------------------------------------------
  **Asama**        **Detay**
  ---------------- ------------------------------------------------------
  1\. Takvim       Gunluk event listesi ve onem derecesi okunur
  kontrolu         

  2\. Trigger      Sadece yuksek etkili olaylar icin workflow tetiklenir

  3\. Veri oncesi  Ilgili varliklar ve risk tonu gonderilir
  mesaj            

  4\. Veri sonrasi Actual/forecast farki ve ilk bias sinyali olusur
  analiz           

  5\. Commander    FX, metal veya endeks icin sade event-day bias mesaji
  ozeti            uretilir

  6\. Gun sonu     Piyasa tepki kalitesi ve false start olup olmadigi
  review           kayda girer
  -----------------------------------------------------------------------

11\. Kullaniciya Giden Son Mesaj Formati

Uygulama tarafinda esas prensip sade cikti sunmaktir. Sistem, her
raporda tek bir son karari one cikarir; alt metrikleri yalniz teknik
ekip icin saklar.

  -----------------------------------------------------------------------
  **Alan**            **Gorunen format**
  ------------------- ---------------------------------------------------
  Unified Bias        Bullish / Bearish / Neutral

  Confidence          0-100 veya dusuk / orta / yuksek

  Kisa gerekce        En fazla 2-3 madde

  Oncelik             Top 4 Now / Next 2 Candidates

  Risk uyarisi        Varsa tek satir warning
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------
  Alt metrikler (flow, OI, funding, liquidation, narrative_score vb.)
  panoda varsayilan olarak acik olmamalidir. Bu veriler yalniz analyst
  mode veya internal debug ekraninda tutulmalidir.
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------

12\. Shadow Forward Test ve Geri Olcum

**•** Her saat son karar ve confidence veri tabanina yazilir.

**•** 1 saat sonra gerceklesen yon ile sonuc karsilastirilir.

**•** Ayrica event gunlerinde veri sonrasi pencere bazli dogruluk
tutulur.

**•** Yuksek confidence isabet orani, false alarm rate ve disagreement
etkisi raporlanir.

13\. Hizi Artiran Uygulama Kararlari

**•** API baglantilari tek servis altinda toplanir.

**•** Grok sadece shortlist ve event gunlerinde cagrilir.

**•** Gemini sadece normalizasyon yapar; yorum liderligine cikmaz.

**•** Commander yazim ve son sentez gorevinde kalir; nicel hesap yapmaz.

**•** Critic opsiyonel ve event-based tutulur.

**•** Kullaniciya tek bir birlesik sonuc gosterildigi icin frontend ve
mesajlasma mantigi basitlesir.
