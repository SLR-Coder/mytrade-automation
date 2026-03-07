# MyTrade (İşlemlerim) Sayfası - Kapsamlı Geliştirme Planı

> **Amaç**: Admin panelindeki `transactions` sayfasını modüler hale getirmek, temiz bir dosya yapısına kavuşturmak ve sürdürülebilir şekilde geliştirmeye devam edebilmek.

---

## 1. Mevcut Durum Analizi

### Sorunlar
- `page.tsx` **5.291 satır** → tek bir dev dosya, bakımı çok zor
- Tüm iş mantığı, form state'leri, API çağrıları, UI bileşenleri aynı yerde
- Modal'lar component olarak ayrılmış ama ana mantık hâlâ `page.tsx` içinde
- Save logic (`save-logic.ts`) ve utils (`utils.ts`) ayrı ama yetersiz

### Mevcut Dosya Yapısı
```
src/app/admin/transactions/
├── page.tsx                    # 5291 satır (!!!)
├── save-logic.ts              # Kaydetme/balance mantığı
├── utils.ts                   # Yardımcı fonksiyonlar
├── buysell2-rate-handlers.ts  # BuySell2 kur hesaplama
├── components/
│   ├── BalanceWarningModal.tsx
│   ├── BuySell2Modal.tsx
│   ├── DekontUploadModal.tsx
│   ├── GeneralTransactionModal.tsx
│   ├── QuickAddAccountPopup.tsx
│   ├── TransactionActionCards.tsx
│   ├── TransactionFilters.tsx
│   ├── TransactionStatsBar.tsx
│   ├── TransactionTable.tsx
│   └── index.ts
├── constants/
│   └── index.ts               # Sabitler, varsayılan formlar, döviz bilgileri
└── types/
    └── index.ts               # Transaction, form, UI tipleri
```

### Mevcut Transaction Tipleri
| Tip | Açıklama |
|-----|----------|
| `alim_satim` | Döviz alım/satım (BuySell2 ile) |
| `general` | Genel işlem (kasalar/bankalar/müşteriler arası) |
| `internal_transfer` | Dahili transfer (kasa↔banka) |
| `para_giris` | Para giriş |
| `para_cikis` | Para çıkış |
| `tahsilat` | Tahsilat |
| `odeme` | Ödeme |

### Mevcut Muhasebe Sistemi
- Çift taraflı muhasebe (double-entry) → `lib/accounting/engine.ts`
- Hesap planı (Chart of Accounts) → `lib/accounting/types.ts`
- Journal entries → `admin/accounting/journal/`
- Trial balance → `admin/accounting/trial-balance/`
- Müşteri ekstresi → `admin/accounting/customer-statement/`
- Kasa/Banka hesapları → Supabase `cash_accounts` & `bank_accounts` tabloları

---

## 2. Hedef Mimari

### 2.1 Yeni Dosya Yapısı (Refactoring)

```
src/app/admin/transactions/
├── page.tsx                        # ~200 satır, sadece layout + routing
├── save-logic.ts                   # (mevcut) kaydetme mantığı
├── utils.ts                       # (mevcut) yardımcılar
├── buysell2-rate-handlers.ts      # (mevcut) kur hesaplama
│
├── types/
│   └── index.ts                   # (mevcut) tüm tipler
│
├── constants/
│   └── index.ts                   # (mevcut) sabitler
│
├── hooks/                         # ★ YENİ - Custom hooks
│   ├── useTransactionData.ts      # Data fetching (kasa, banka, müşteri, işlemler)
│   ├── useTransactionFilters.ts   # Filtreleme state & logic
│   ├── useTransactionForm.ts      # Genel form state management
│   ├── useBuySell2Form.ts         # BuySell2 form state management
│   ├── useTransactionSave.ts      # Kaydetme işlemleri
│   ├── useTransactionDelete.ts    # Silme işlemleri
│   ├── useCustomerBankAccounts.ts # Müşteri banka hesapları cache
│   └── index.ts
│
├── components/                    # ★ GENİŞLETİLMİŞ
│   ├── BalanceWarningModal.tsx     # (mevcut)
│   ├── BuySell2Modal.tsx          # (mevcut)
│   ├── DekontUploadModal.tsx      # (mevcut)
│   ├── GeneralTransactionModal.tsx # (mevcut)
│   ├── QuickAddAccountPopup.tsx   # (mevcut)
│   ├── TransactionActionCards.tsx  # (mevcut)
│   ├── TransactionFilters.tsx     # (mevcut)
│   ├── TransactionStatsBar.tsx    # (mevcut)
│   ├── TransactionTable.tsx       # (mevcut)
│   ├── TransactionDetailModal.tsx # ★ YENİ - İşlem detay görüntüleme
│   ├── TransactionEditWrapper.tsx # ★ YENİ - Edit akışını yönetir
│   └── index.ts
│
└── actions/                       # ★ YENİ - Server actions veya API helpers
    ├── fetchTransactions.ts       # İşlem listesi çekme
    ├── saveTransaction.ts         # İşlem kaydetme
    ├── deleteTransaction.ts       # İşlem silme
    └── index.ts
```

### 2.2 page.tsx Hedef Yapısı (~200 satır)

```tsx
// page.tsx - Sadece bileşenleri birleştirme ve layout
'use client'

export default function TransactionsPage() {
  // Custom hooks ile tüm state'ler
  const { data, isLoading, refresh } = useTransactionData()
  const { filters, setFilter, filteredTransactions } = useTransactionFilters(data.transactions)
  const { save, isSaving } = useTransactionSave(data, refresh)
  const { deleteTransaction, isDeleting } = useTransactionDelete(refresh)

  // Modal state'leri
  const [activeModal, setActiveModal] = useState<ModalType>(null)

  return (
    <div>
      <TransactionStatsBar transactions={filteredTransactions} />
      <TransactionActionCards onAction={setActiveModal} />
      <TransactionFilters filters={filters} onChange={setFilter} />
      <TransactionTable
        transactions={filteredTransactions}
        onEdit={...}
        onDelete={...}
      />
      {/* Modals */}
      <BuySell2Modal ... />
      <GeneralTransactionModal ... />
    </div>
  )
}
```

---

## 3. Adım Adım Uygulama Planı

### FAZ 1: Hook'ları Çıkarma (Öncelik: YÜKSEK)
> Tahmini dosya sayısı: 7 yeni dosya

| Adım | İş | Dosya | Açıklama |
|------|----|-------|----------|
| 1.1 | `useTransactionData` hook | `hooks/useTransactionData.ts` | `page.tsx`'den tüm `fetchData`, `useEffect` ve state'leri çıkar. `cashAccounts`, `bankAccounts`, `customers`, `extraCategories`, `transactions`, `exchangeRates`, `bankDefinitions` state'lerini bu hook'a taşı |
| 1.2 | `useTransactionFilters` hook | `hooks/useTransactionFilters.ts` | Filtre state'lerini (`searchTerm`, `typeFilter`, `dateFilter`, vs.) ve filtreleme mantığını çıkar |
| 1.3 | `useCustomerBankAccounts` hook | `hooks/useCustomerBankAccounts.ts` | `customerBankAccountsCache` ve `fetchCustomerBankAccounts` çıkar |
| 1.4 | `useTransactionForm` hook | `hooks/useTransactionForm.ts` | `generalForm` state, form handlers, validation |
| 1.5 | `useBuySell2Form` hook | `hooks/useBuySell2Form.ts` | `buySell2Form` state ve kur hesaplama handlers |
| 1.6 | `useTransactionSave` hook | `hooks/useTransactionSave.ts` | Kaydetme işlemleri, `isSaving` state |
| 1.7 | `useTransactionDelete` hook | `hooks/useTransactionDelete.ts` | Silme mantığı ve `deleteConfirmTx` state |

**Test Stratejisi**: Her hook çıkarıldıktan sonra sayfa aynı şekilde çalışmalı. Regresyon kontrolü.

---

### FAZ 2: page.tsx Temizleme (Öncelik: YÜKSEK)
> `page.tsx`'i 5000+ satırdan ~200-300 satıra düşürme

| Adım | İş | Açıklama |
|------|----|----------|
| 2.1 | Hook'ları import et | Tüm yeni hook'ları `page.tsx`'e bağla |
| 2.2 | Inline fonksiyonları kaldır | Handler'ları hook'ların döndürdüğü fonksiyonlarla değiştir |
| 2.3 | JSX temizle | Gereksiz inline style/logic'leri component'lere taşı |
| 2.4 | Test et | Tüm işlem tipleri doğru çalışıyor mu kontrol et |

---

### FAZ 3: Yeni Özellikler (Öncelik: ORTA)

#### 3.1 İşlem Detay Modalı
- Seçilen işlemin tüm bilgilerini göster
- İlgili muhasebe kaydını (journal entry) göster
- Dekont/makbuz görüntüleme
- Yazdırma desteği

#### 3.2 Gelişmiş Filtreleme
- Tarih aralığı picker (takvim)
- Tutar aralığı
- Çoklu döviz filtresi
- Kaynak filtresi (Panel, Bot, API, vs.)
- Filtre preset'leri (bugün, bu hafta, bu ay)

#### 3.3 Toplu İşlemler (Bulk Operations)
- Çoklu seçim (checkbox)
- Toplu onay/iptal
- Toplu silme
- Seçili işlemleri dışa aktarma

#### 3.4 Excel/CSV Dışa Aktarma
- Mevcut filtreye göre dışa aktar
- Döviz bazında rapor
- Müşteri bazında rapor
- Tarih bazında rapor

---

### FAZ 4: İleri Seviye Özellikler (Öncelik: DÜŞÜK)

#### 4.1 Gerçek Zamanlı Güncellemeler
- Supabase Realtime ile işlem listesi otomatik güncelleme
- Başka bir kullanıcı işlem girdiğinde bildirim
- Kur değişikliği bildirimi

#### 4.2 İşlem Şablonları
- Sık yapılan işlemleri şablon olarak kaydet
- Tek tıkla şablondan işlem oluştur
- Şablon yönetimi sayfası

#### 4.3 Performans İyileştirmeleri
- Sanal kaydırma (virtualized list) büyük listeler için
- İşlem arama debounce optimizasyonu
- Lazy loading modal'lar

---

## 4. Teknik Detaylar

### 4.1 Data Flow Diyagramı

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Supabase   │────→│ useTransactionData│────→│    page.tsx      │
│  (DB)       │     │  (hook)          │     │  (orchestrator)  │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                       │
                    ┌──────────────────┐               │
                    │ useTransaction   │◄──────────────┤
                    │ Filters (hook)   │               │
                    └──────────────────┘               │
                                                       │
                    ┌──────────────────┐               │
                    │ useTransaction   │◄──────────────┤
                    │ Save (hook)      │               │
                    └──────────────────┘               │
                                                       │
               ┌────────────┐  ┌──────────────┐       │
               │ BuySell2   │  │ General      │◄──────┘
               │ Modal      │  │ Transaction  │
               └────────────┘  │ Modal        │
                               └──────────────┘
```

### 4.2 State Management Prensibi

```
Her hook kendi state'ini yönetir:

useTransactionData → cashAccounts, bankAccounts, customers, transactions, ...
useTransactionFilters → searchTerm, typeFilter, dateFilter, filteredList
useTransactionForm → generalForm, validation, handlers
useBuySell2Form → buySell2Form, rate handlers
useTransactionSave → isSaving, saveResult, saveHandlers
useTransactionDelete → isDeleting, deleteConfirmTx, deleteHandlers
```

### 4.3 Supabase Tabloları (Mevcut)

| Tablo | Açıklama |
|-------|----------|
| `transactions` | Ana işlem tablosu |
| `cash_accounts` | Kasa hesapları (TRY, USD, EUR, vs.) |
| `bank_accounts` | Banka hesapları |
| `customers` | Müşteri listesi |
| `customer_bank_accounts` | Müşteri banka hesapları |
| `customer_balances` | Müşteri bakiyeleri (döviz bazında) |
| `exchange_rates` | Döviz kurları |
| `extra_categories` | Gelir/gider kategorileri |
| `journal_entries` | Muhasebe yevmiye kayıtları |
| `journal_lines` | Yevmiye satırları (borç/alacak) |
| `accounts` | Hesap planı |

### 4.4 Hesap Planı (Chart of Accounts)

```
VARLIKLAR (1000-1999)
├── 1000 Kasa ve Nakit
│   ├── 1010 Kasa - TRY
│   ├── 1011 Kasa - USD
│   ├── 1012 Kasa - EUR
│   ├── 1013 Kasa - USDT
│   ├── 1014 Kasa - IRT
│   └── 1015 Kasa - GBP
├── 1100 Banka Hesapları
│   ├── 1110 Banka - TRY
│   ├── 1120 Banka - USD
│   └── 1130 Banka - EUR
├── 1200 Alacaklar
│   └── 1210 Müşteri Alacakları
└── 1300 Kripto Cüzdanları

BORÇLAR (2000-2999)
├── 2000 Borçlar
│   └── 2010 Tedarikçi Borçları
├── 2100 Müşteri Teminatları
└── 2200 Tahakkuk Giderler

ÖZKAYNAKLAR (3000-3999)
├── 3000 Öz Sermaye
├── 3100 Geçmiş Yıl Kârları
├── 3200 Dönem Kâr/Zararı
└── 3300 Sermaye Çekişi

GELİRLER (4000-4999)
├── 4000 Döviz Geliri
│   ├── 4010 Kur Farkı Geliri
│   ├── 4020 Komisyon Geliri
│   └── 4030 Havale Ücret Geliri
└── 4900 Diğer Gelirler

GİDERLER (5000-5999)
├── 5100 Operasyonel Giderler
├── 5200 Banka Masrafları
├── 5300 Maaşlar
├── 5400 Kira
├── 5500 Kur Farkı Zararı
└── 5900 Diğer Giderler
```

---

## 5. Her İşlem Tipinin Muhasebe Kaydı

### 5.1 Alım/Satım (BuySell2)
**Senaryo**: Müşteri 220.000 TL veriyor, 5.000 USD alıyor (kur: 44)

```
Borç  1101 Kasa-TRY  220.000 TL    (kasaya para girdi)
      Alacak 1102 Kasa-USD     5.000 USD  (kasadan dolar çıktı)
      Alacak 4010 Kur Farkı Geliri  (spread kârı)
```

### 5.2 Para Giriş
**Senaryo**: Müşteriden 1.000 USD nakit geldi

```
Borç  1102 Kasa-USD  1.000 USD     (kasaya para girdi)
      Alacak 1210 Müşteri Alacakları 1.000 USD (müşteri borcu azaldı)
```

### 5.3 Para Çıkış
**Senaryo**: Müşteriye 500 EUR havale yapıldı

```
Borç  1210 Müşteri Alacakları  500 EUR   (müşteriye borcumuz azaldı)
      Alacak 1130 Banka-EUR          500 EUR   (bankadan para çıktı)
```

### 5.4 Dahili Transfer
**Senaryo**: Kasadan bankaya 10.000 TL aktarma

```
Borç  1110 Banka-TRY  10.000 TL    (bankaya para girdi)
      Alacak 1101 Kasa-TRY    10.000 TL    (kasadan para çıktı)
```

---

## 6. Önerilen Geliştirme Sırası

```
Hafta 1-2: FAZ 1 (Hook çıkarma)
  ├── useTransactionData
  ├── useTransactionFilters
  ├── useCustomerBankAccounts
  ├── useTransactionForm
  ├── useBuySell2Form
  ├── useTransactionSave
  └── useTransactionDelete

Hafta 3: FAZ 2 (page.tsx temizleme)
  ├── Hook'ları bağla
  ├── page.tsx'i küçült
  └── Regresyon testi

Hafta 4-5: FAZ 3 (Yeni özellikler)
  ├── İşlem detay modalı
  ├── Gelişmiş filtreleme
  ├── Toplu işlemler
  └── Excel/CSV export

Hafta 6+: FAZ 4 (İleri özellikler)
  ├── Realtime updates
  ├── İşlem şablonları
  └── Performans optimizasyonu
```

---

## 7. Dikkat Edilmesi Gerekenler

### Kritik Kurallar
1. **Çift taraflı muhasebe**: Her işlemde BORÇ = ALACAK olmalı
2. **Balance tutarlılığı**: İşlem kaydedildiğinde kasa/banka/müşteri bakiyeleri güncellenmeli
3. **Transaction group**: İlişkili işlemler aynı `transaction_group_id` ile bağlanmalı
4. **Master group**: Alım/satım fazları aynı `master_group_id` ile bağlanmalı
5. **Atomik işlemler**: Ya tüm kayıtlar başarılı olmalı ya da hiçbiri (Supabase RPC kullanılıyor)

### Mevcut Bug'lar / Teknik Borç
- `page.tsx` çok büyük → **FAZ 1-2 ile çözülecek**
- Bazı inline handler'lar karmaşık → hook'lara taşınacak
- Bazı modal'lar çok fazla prop alıyor → context veya composition pattern kullanılabilir

### Test Yaklaşımı
- Her hook için unit test yazılabilir (jest)
- Her işlem tipi için integration test
- Manuel test: Tüm senaryo matrix'i (`docs/transaction-matrix.json`)

---

## 8. Kullanılan Teknolojiler

| Teknoloji | Kullanım |
|-----------|----------|
| **Next.js 14** | App Router, Server/Client Components |
| **React 18** | UI framework |
| **TypeScript** | Tip güvenliği |
| **Supabase** | Backend (PostgreSQL + Auth + Realtime + Storage) |
| **Tailwind CSS** | Stil |
| **Lucide React** | İkon kütüphanesi |
| **Custom UI** | Card, Badge, Button, Input, Modal, StatCard |

---

## 9. Hızlı Başlangıç

**FAZ 1, Adım 1.1'e başlamak için:**

```bash
# hooks klasörünü oluştur
mkdir -p src/app/admin/transactions/hooks

# İlk hook'u oluştur
touch src/app/admin/transactions/hooks/useTransactionData.ts
touch src/app/admin/transactions/hooks/index.ts
```

Sonra `page.tsx`'den şu state'leri ve fetch logic'i `useTransactionData.ts`'e taşı:
- `cashAccounts`, `bankAccounts`, `customers`, `extraCategories`
- `transactions`, `exchangeRates`, `bankDefinitions`
- `customerBalances`
- `isLoading`
- `fetchData()` fonksiyonu ve `useEffect`

---

*Bu doküman canlı bir plandır. Geliştirme ilerledikçe güncellenecektir.*
