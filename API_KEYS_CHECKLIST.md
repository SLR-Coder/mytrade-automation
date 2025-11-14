# 🔑 MyTrade API Keys Kontrol Listesi

## ✅ **TEST AŞAMASI İÇİN GEREKLİ** (Mutlaka Olmalı)

### 1. **Google Gemini API Key** 🤖
- **Nereden:** https://aistudio.google.com/app/apikey
- **Maliyet:** ÜCRETSİZ (Aylık 60 request/dakika limiti)
- **Nasıl Alınır:**
  1. Google hesabınızla giriş yapın
  2. "Get API key" butonuna tıklayın
  3. "Create API key" → "Create API key in new project"
  4. Key'i kopyalayın
- **Secret Manager'a Kayıt:** `GEMINI_API_KEY`
- **Örnek Format:** `AIzaSyD...` (39 karakter)

---

### 2. **Google Sheets ID** 📊
- **Nereden:** Google Sheets'te oluşturacaksınız
- **Maliyet:** ÜCRETSİZ
- **Nasıl Alınır:**
  1. https://sheets.google.com → Yeni spreadsheet oluşturun
  2. İsim verin: "MyTrade Dashboard"
  3. URL'den ID'yi kopyalayın:
     ```
     https://docs.google.com/spreadsheets/d/[BU_KISIM_ID]/edit
     ```
  4. Share → Service account email'ini ekleyin (Editor yetkisi)
     ```
     mytrade-robot@mytrade-automation.iam.gserviceaccount.com
     ```
- **Secret Manager'a Kayıt:** `GOOGLE_SHEET_ID`
- **Örnek Format:** `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`

---

### 3. **Telegram Bot Token** 🤖
- **Nereden:** Telegram → @BotFather
- **Maliyet:** ÜCRETSİZ
- **Nasıl Alınır:**
  1. Telegram'da @BotFather'ı bulun
  2. `/newbot` komutunu gönderin
  3. Bot ismi girin (örn: "MyTrade AI Bot")
  4. Bot username girin (örn: "mytrade_ai_bot")
  5. Token'ı kopyalayın
- **Secret Manager'a Kayıt:** `TELEGRAM_BOT_TOKEN`
- **Örnek Format:** `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

---

### 4. **Telegram Chat ID** 💬
- **Nereden:** Telegram kanalınız veya botunuz
- **Maliyet:** ÜCRETSİZ
- **Nasıl Alınır (YÖNTEM 1 - Özel Mesaj):**
  1. Botunuza mesaj gönderin: `/start`
  2. Bu URL'yi tarayıcıda açın:
     ```
     https://api.telegram.org/bot<BOTUNUZUN_TOKEN>/getUpdates
     ```
  3. `"chat":{"id": 123456789}` kısmını bulun

**Nasıl Alınır (YÖNTEM 2 - Kanal):**
  1. Telegram'da yeni kanal oluşturun (örn: "MyTrade Signals")
  2. Kanalı public yapın (örn: @mytrade_signals)
  3. Botunuzu kanala admin olarak ekleyin
  4. Kanala bir mesaj gönderin
  5. Yukarıdaki URL'yi kontrol edin, chat ID'yi alın
  6. Kanal için ID genelde negatif olur: `-1001234567890`

- **Secret Manager'a Kayıt:** `TELEGRAM_CHAT_ID`
- **Örnek Format:** `123456789` (özel mesaj) veya `-1001234567890` (kanal)

---

## ⚠️ **TEST AŞAMASINDA KULLANILMAYACAK** (Şimdilik İsteğe Bağlı)

### 5. **OpenAI API Key (GPT-4)** 🧠
- **Durum:** ❌ TEST'TE KAPALI
- **Nereden:** https://platform.openai.com/api-keys
- **Maliyet:** ~$20-40/ay (kullanıma göre)
- **Nasıl Alınır:**
  1. OpenAI hesabı oluşturun
  2. "API keys" → "Create new secret key"
  3. Key'i kopyalayın (bir daha gösterilmez!)
- **Secret Manager'a Kayıt:** `OPENAI_API_KEY` (ileride)
- **Örnek Format:** `sk-proj-...` (56 karakter)
- **NOT:** Test başarılı olunca LIVE'da eklenecek

---

### 6. **Anthropic Claude API Key** 🤖
- **Durum:** ❌ TEST'TE KAPALI
- **Nereden:** https://console.anthropic.com/
- **Maliyet:** ~$20-40/ay (kullanıma göre)
- **Nasıl Alınır:**
  1. Anthropic hesabı oluşturun
  2. "API Keys" → "Create Key"
  3. Key'i kopyalayın
- **Secret Manager'a Kayıt:** `ANTHROPIC_API_KEY` (ileride)
- **Örnek Format:** `sk-ant-api03-...`
- **NOT:** Test başarılı olunca LIVE'da eklenecek

---

### 7. **Polygon.io API Key (Forex)** 💱
- **Durum:** ❌ TEST'TE KAPALI (Forex kapalı)
- **Nereden:** https://polygon.io/dashboard/api-keys
- **Maliyet:** $199/ay (Premium plan)
- **Nasıl Alınır:**
  1. Polygon.io hesabı oluşturun
  2. Premium plan'a yükselt
  3. Dashboard'dan API key alın
- **Secret Manager'a Kayıt:** `POLYGON_API_KEY` (ileride)
- **Örnek Format:** `your_api_key_here`
- **NOT:** Test başarılı olunca LIVE'da eklenecek

---

### 8. **Alpha Vantage API Key (Forex Yedek)** 💱
- **Durum:** ❌ TEST'TE KAPALI (Forex kapalı)
- **Nereden:** https://www.alphavantage.co/support/#api-key
- **Maliyet:** $49/ay (Premium plan)
- **Nasıl Alınır:**
  1. Form doldurun → "GET YOUR FREE API KEY TODAY"
  2. Email'inize gelen key'i kopyalayın
  3. Premium'a yükselt (daha sonra)
- **Secret Manager'a Kayıt:** `ALPHA_VANTAGE_KEY` (ileride)
- **Örnek Format:** `ABCD1234EFGH5678`
- **NOT:** Test başarılı olunca LIVE'da eklenecek

---

## 📊 **MALİYET ÖZETİ**

### TEST AŞAMASI (Şimdi)
```
✅ Google Gemini: ÜCRETSİZ
✅ Google Sheets: ÜCRETSİZ
✅ Telegram Bot: ÜCRETSİZ
✅ Google Cloud: ~$10-15/ay (db-f1-micro)
✅ Binance API: ÜCRETSİZ (public endpoints)
✅ Metals API: ÜCRETSİZ (altın/gümüş)

TOPLAM: ~$10-15/ay (sadece Google Cloud)
```

### LIVE AŞAMASI (Sonra)
```
✅ Google Gemini: ÜCRETSİZ
✅ OpenAI GPT-4: ~$30-50/ay
✅ Anthropic Claude: ~$30-50/ay
✅ Polygon.io (Forex): $199/ay VEYA
✅ Alpha Vantage (Forex): $49/ay
✅ Google Sheets: ÜCRETSİZ
✅ Telegram Bot: ÜCRETSİZ
✅ Google Cloud: ~$15-20/ay (db-g1-small)

TOPLAM: $150-250/ay (Alpha Vantage ile)
VEYA: $300-350/ay (Polygon.io ile)
```

---

## ✅ **HAZIRLIK KONTROL LİSTESİ**

Test aşaması için şunları hazırlayın:

- [ ] **1. Google Gemini API Key aldım**
  - [ ] Key'i bir yere not ettim (güvenli yer!)

- [ ] **2. Google Sheets oluşturdum**
  - [ ] Yeni spreadsheet açtım
  - [ ] Sheet ID'yi kopyaladım
  - [ ] Service account'u Editor olarak ekleyeceğim (setup sırasında)

- [ ] **3. Telegram Bot oluşturdum**
  - [ ] @BotFather'dan bot token aldım
  - [ ] Telegram Chat ID'mi aldım (kanal veya özel mesaj)

- [ ] **4. Google Cloud Console hazır**
  - [ ] Project açtım: `mytrade-automation`
  - [ ] Billing aktif
  - [ ] Cloud Shell kullanmaya hazırım

---

## 🔐 **GÜVENLİK UYARILARI**

⚠️ **ÖNEMLİ:**
1. API key'leri asla GitHub'a commit etmeyin!
2. `.env` dosyası `.gitignore`'da var (güvenli)
3. Secret Manager kullanın (Google Cloud)
4. Key'leri düzenli olarak rotate edin (3-6 ayda bir)
5. Test bitince kullanılmayan key'leri silin

---

## 📝 **NOTLAR**

### Google Gemini Limitleri (Ücretsiz)
- **Request Limiti:** 60 request/dakika
- **Günlük Limit:** 1,500 request/gün
- **Aylık Limit:** Yok (günlük limit dahilinde)

**BİZİM KULLANIM:**
- Saatlik job: 1 request (haber analizi yok)
- Piyasa açılış: ~6 request (kripto + altın/gümüş için)
- Günlük: ~30-40 request
- **SONUÇ:** Ücretsiz limit YETER! ✅

### Test Aşamasında Zamanlama
Setup sırasında önce **MANUEL** test yapacağız:
```bash
gcloud run jobs execute mytrade-automation-job --region=europe-west1 --wait
```

Başarılı olursa Cloud Scheduler ekleyeceğiz (otomatik).

---

## 🚀 **SIRADA NE VAR?**

1. ✅ Siz API key'leri alın (yukarıdaki listeden)
2. ⏳ Ben kodu güncelleyeceğim (sadece Gemini aktif)
3. ⏳ GitHub'a push edeceğim
4. ⏳ Siz Google Cloud Shell'i açacaksınız
5. ⏳ Beraber setup yapacağız (14 adım)
6. ⏳ İlk testi yapacağız
7. 🎉 Telegram'a mesaj gelecek!

---

**Hazır olunca bana haber verin!** 😊
