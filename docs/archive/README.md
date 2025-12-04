# 📦 Arşiv Klasörü

Bu klasör, production deployment sırasında silinen ama gelecekte faydalı olabilecek dosyaları içerir.

## 📚 Dokümantasyon

### ANALIZ_VE_ONERILER.md
- **Ne**: Proje için detaylı analiz ve öneriler
- **İçerik**:
  - Mevcut özellikler ve eksikler
  - Yasal sorumluluk uyarısı (disclaimer) önemi
  - Performans şeffaflığı önerileri
  - Haber güncellemeleri stratejisi
  - Forex aktif hale getirme notları
- **Neden Saklandı**: Gelecek iyileştirmeler için değerli bilgiler içeriyor

### COMPLETE_SOURCE_CODE_ANALYSIS.md
- **Ne**: Tüm kaynak kod analizi
- **İçerik**: Kod yapısı, fonksiyonlar, bağımlılıklar
- **Neden Saklandı**: Yeni geliştiriciler için kod mimarisi referansı

### ROBOT_4_5_UPDATES.md
- **Ne**: Robot 4 ve 5 güncellemeleri
- **İçerik**: Chart generator ve Telegram publisher güncellemeleri
- **Neden Saklandı**: Güncelleme geçmişi ve değişiklik notları

### scheduler_config_v1.yaml
- **Ne**: Eski scheduler konfigürasyonu
- **İçerik**: İlk versiyon cron job tanımları
- **Neden Saklandı**: Referans için (v2 kullanılıyor)

---

## 🗄️ Database Layer

**Dizin**: `docs/archive/database/`

### database.py, models.py
- **Ne**: CloudSQL/SQLite database layer
- **Neden Saklandı**:
  - Şu anda Google Sheets kullanılıyor
  - Gelecekte CloudSQL'e geçersek lazım olabilir
  - Database schema referansı

### Data Models
- `market_data_model.py` - Market data schema
- `signals_model.py` - Trading signals schema
- `performance_model.py` - Performance tracking schema
- `news_model.py` - News data schema

**Not**: Bu dosyalar production'da kullanılmıyor ama gelecekteki database migration için saklandı.

---

## 🔧 Setup Scripts

**Dizin**: `scripts/archive/`

### Setup Scripts
- `setup_sheets.py` - Google Sheets ilk kurulum
- `setup_twelve_data_secret.py` - TwelveData API setup
- `add_twelve_data_secret.py` - Secret Manager ekleme

**Kullanım**: Yeni ortam kurulumunda bu scriptler gerekebilir.

### Test Scripts
- `test_secret_manager.py` - Secret Manager testi
- `test_twelve_data.py` - TwelveData API testi
- `test_robot6_pipeline.sh` - Robot 6 pipeline testi
- `verify_robot6_results.py` - Robot 6 sonuç doğrulama

**Kullanım**: Production'da manuel test yapmak için kullanılabilir.

---

## 🤖 Old Robot Files

**Dizin**: `robots/archive/`

### performance_tracker.py
- **Ne**: Eski performans takip robotu
- **Neden Kaldırıldı**: Robot 6 (weekly_telegram_report.py) bu işi yapıyor
- **Neden Saklandı**: Alternatif implementasyon referansı

### sheets_to_db_sync.py
- **Ne**: Google Sheets → Database senkronizasyonu
- **Neden Kaldırıldı**: Database layer kullanılmıyor
- **Neden Saklandı**: Gelecekte database'e geçersek referans olabilir

---

## ⚠️ KULLANIM UYARILARI

1. **Bu dosyalar production'da kullanılmıyor!**
   - Sadece referans ve arşiv amaçlı
   - Çalıştırmadan önce güncellenmeleri gerekebilir

2. **Bağımlılıklar eksik olabilir**
   - Bu dosyalar silinirken bazı import'lar kaldırılmış olabilir
   - Kullanmadan önce requirements.txt kontrol edilmeli

3. **Test etmeden production'a eklemeyin**
   - Bu dosyalar development/test amaçlı
   - Production'a eklemeden önce mutlaka test edin

---

## 📅 Arşivleme Tarihi

**Tarih**: 2025-11-29
**Commit**: 33b4374
**Branch**: claude/resume-debug-session-01Hw8PG54X3gQYmxgz3wCB8x
**Sebep**: GCP Cloud Run deployment için production cleanup

---

## 🔄 Restore Etme

Bir dosyayı geri yüklemek için:

```bash
# Archive'den production'a kopyala
cp docs/archive/DOSYA_ADI.md ./

# Veya git'ten geri yükle
git show 33b4374^:PATH/TO/FILE > PATH/TO/FILE
```

---

## 📞 Sorular

Bu arşivdeki dosyalarla ilgili sorularınız varsa:
1. Bu README.md dosyasını okuyun
2. Git history'yi kontrol edin: `git log --all -- PATH/TO/FILE`
3. Commit mesajlarına bakın

**Not**: Yeni bir Claude Code session başlattığınızda, bu README sayesinde arşivdeki dosyaların ne olduğunu ve neden saklandığını anlayabilirsiniz.
