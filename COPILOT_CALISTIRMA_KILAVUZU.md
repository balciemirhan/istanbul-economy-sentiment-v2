# 🚀 İstanbul Co-Pilot Çalıştırma Kılavuzu

Bu kılavuz, projenin iki farklı modda (Hızlı Yerel Geliştirme ve Docker Canlı Simülasyonu) nasıl başlatılıp kapatılacağını en net ve öz haliyle açıklar.

---

## ⚡ YÖNTEM 1: Hızlı Yerel Geliştirme (Docker YOK) - TAVSİYE EDİLEN
*Java veya Python tarafında **aktif kod yazarken** bu yöntemi kullanın. Işık hızında çalışır.*

### ☕ 1. Java Mikroservisini Başlatma (Terminal 1)
1. PowerShell veya Terminal açıp Java klasörüne girin:
   ```powershell
   cd c:\SoftWares\Python\python_project\istanbul-copilot-java
   ```
2. Sunucuyu başlatın:
   ```powershell
   .\mvnw_local.cmd spring-boot:run
   ```
   * *Java servisi yerelde `http://localhost:8080` adresinde hazır bekler.*

#### 🔄 Java'da Kod Değiştirince Güncelleme:
* Terminalde **`Ctrl + C`** tuşlarına basarak sunucuyu kapatın.
* Yeniden başlatmak için tekrar `.\mvnw_local.cmd spring-boot:run` komutunu çalıştırın (1.7 saniyede derlenip güncellenir).

---

### 🐍 2. Python Flask Panelini Başlatma (Terminal 2)
1. **Yeni bir Terminal penceresi** açıp ana Python klasörüne girin:
   ```powershell
   cd c:\SoftWares\Python\python_project\istanbulmetre_cardiffnlp_copilot
   ```
2. Flask sunucusunu başlatın:
   ```powershell
   python dashboard/api/app.py
   ```
   * *Panel yerelde `http://localhost:5000` adresinde çalışmaya başlar.*

#### 🔄 Python'da Kod Değiştirince Güncelleme:
* Hiçbir şey yapmanıza gerek yok! Flask, kod değişikliklerini otomatik algılar ve anında günceller (Hot-Reload).

---

## 🐳 YÖNTEM 2: Docker ile Çalıştırma (Canlı Simülasyonu)
*Geliştirmeniz tamamen bittiğinde ve **canlı sunucu ortamını simüle etmek** istediğinizde kullanın.*

### 🛠️ 1. Java Docker İmajını Yerelde Derlemek (Bir Kerelik / Güncellemede)
Java klasörünün içindeyken yerel kodlarınızdan güncel bir Docker imajı paketleyin:
```powershell
cd c:\SoftWares\Python\python_project\istanbul-copilot-java
docker build -t ghcr.io/emirhanbalci/istanbul-copilot-java:latest .
```

### 🚀 2. Docker Compose ile Java'yı Arka Planda Başlatma (Terminal 1)
1. Python klasörüne gidin:
   ```powershell
   cd c:\SoftWares\Python\python_project\istanbulmetre_cardiffnlp_copilot
   ```
2. Java servisini arka planda Docker üzerinde başlatın:
   ```powershell
   docker compose up -d
   ```
   * *Java mikroservisi artık Docker konteynerinde arka planda çalışmaktadır.*

### 🐍 3. Python Flask Panelini Başlatma (Terminal 2)
Python klasörünün içindeyken Flask uygulamasını yerelde çalıştırın:
```powershell
python dashboard/api/app.py
```

### 🛑 4. Docker Konteynerini Durdurma
Java servisini durdurup kapatmak için Python klasöründe şu komutu çalıştırın:
```powershell
docker compose down
```

---

## 🌐 Test Etme (Her İki Yöntem İçin)
Tarayıcınızı açın ve Co-Pilot sayfasına gidin:
👉 **[http://localhost:5000/copilot](http://localhost:5000/copilot)**


# 📌 Önemli Notlar (Lütfen Dikkatle Okuyun):

### ⚡ YÖNTEM 1 (Yerel Geliştirme - DOCKER YOK) Kullanıyorsanız:
* **Java kodlarını değiştirince:** Docker ile hiçbir işiniz yoktur! Sadece Java'nın çalıştığı ilk terminale gelip **`Ctrl + C`** ile sunucuyu durdurun ve yeniden **`.\mvnw_local.cmd spring-boot:run`** komutunu çalıştırın.
* **Python kodlarını değiştirince:** Hiçbir şey yapmanıza gerek yok, Flask (hot-reload) değişiklikleri anında otomatik olarak algılar.

### 🐳 YÖNTEM 2 (Docker ile Çalıştırma) Kullanıyorsanız:
* **Java kodlarını değiştirince:** Değişikliğin Docker konteynerine yansıması için önce **`docker build -t ghcr.io/emirhanbalci/istanbul-copilot-java:latest .`** ile imajı yeniden derlemeli, ardından **`docker compose up -d`** yapmalısınız.
* **Python kodlarını değiştirince:** Flask yerelde çalıştığı için yine hiçbir şey yapmanıza gerek yoktur.


# ⚙️ Motor Sistemi Tanımı:
* **Birinci Motor (Java):** Java Sanal Makinesi (JVM) üzerinde çalışan, yapay zekayı (Gemini/LangChain4j) ve veritabanı sorgularını yöneten motor.
* **İkinci Motor (Python):** Python yorumlayıcısı üzerinde çalışan, fine-tune ettiğiniz BERT modelinizi barındıran ve web panelini sunan ana motor.