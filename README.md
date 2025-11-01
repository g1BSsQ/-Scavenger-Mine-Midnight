# Lace Wallet Auto Mining Bot

Bot tự động tạo ví Lace và đăng ký mining trên Scavenger Mine (sm.midnight.gd).

## Tính năng

- ✅ Tự động tạo N ví Lace độc lập
- ✅ Mỗi ví có 24 từ khôi phục riêng
- ✅ Tự động kết nối với sm.midnight.gd
- ✅ Tự động ký message và đăng ký mining
- ✅ Tự động bắt đầu mining session
- ✅ Chạy song song nhiều ví cùng lúc (batch 5 ví)
- ✅ **Quản lý ví tương tác**: Dừng/Khởi động lại bất kỳ ví nào
- ✅ **Dashboard trạng thái**: Theo dõi real-time tất cả ví
- ✅ **Lưu trạng thái**: Tự động lưu và khôi phục trạng thái ví

## Cài đặt

### 1. Cài đặt Python dependencies

```bash
python -m venv venv
venv\Scripts\activate
pip install playwright mnemonic
```

### 2. Cài đặt Playwright Chromium

```bash
playwright install chromium
```

### 3. Chuẩn bị Lace Extension

- Đặt Lace extension vào: `wallets/extensions/lace/`
- Extension ID cần là: `gafhhkghbfjjkeiendhlofajokpaflmk`

## Sử dụng

### Chạy bot:

```bash
venv\Scripts\activate
python playwright_lace_bot.py
```

### Nhập thông tin:

```
📊 Số lượng wallets cần tạo: 5
🔒 Mật khẩu cho tất cả wallets: YourStrongPassword123
```

Bot sẽ:

1. Tạo 5 browser độc lập (batch 5 ví để tránh timeout)
2. Mỗi browser tạo 1 ví Lace mới
3. Tự động đăng ký mining
4. Bắt đầu mining session
5. Hiển thị **Dashboard quản lý**

### Dashboard Quản Lý

Sau khi tất cả ví được tạo, bạn sẽ thấy dashboard:

```
============================================================
📊 WALLET MANAGEMENT DASHBOARD
============================================================

📈 THỐNG KÊ: Tổng: 5 | 🟢 Đang chạy: 4 | 🟡 Đã dừng: 0 | 🔴 Lỗi: 1
   Tỷ lệ thành công: 4/5 (80%)

ID       Tên             Trạng thái    Thời gian            Ghi chú             
--------------------------------------------------------------------------------
1        Wallet 1        🟢 running   2m 30s               OK                  
2        Wallet 2        🟢 running   2m 25s               OK                  
3        Wallet 3        🔴 failed    2m 20s               Signature error     
4        Wallet 4        🟢 running   2m 15s               OK                  
5        Wallet 5        🟢 running   2m 10s               OK                  

------------------------------------------------------------
🎮 MENU:
  1. ⏸️  Dừng ví (Stop wallets)
  2. ▶️  Khởi động lại ví (Restart wallets)
  3. 🔍 Xem chi tiết ví (View wallet details)
  4. 🔄 Làm mới trạng thái (Refresh status)
  5. 🚪 Thoát (Exit)
------------------------------------------------------------

Chọn hành động (1-5):
```

### Các chức năng Dashboard

#### 1️⃣ Dừng ví (Stop wallets)

Dừng một hoặc nhiều ví đang chạy:

```
Nhập ID ví cần dừng (cách nhau bởi dấu phấy, vd: 1,3,5 hoặc 'all'): 3,5
✅ Đã dừng Wallet 3
✅ Đã dừng Wallet 5
```

#### 2️⃣ Khởi động lại ví (Restart wallets)

Khởi động lại ví đã dừng hoặc lỗi (bắt đầu từ đầu):

```
Nhập ID ví cần khởi động lại (cách nhau bởi dấu phấy, vd: 1,3,5 hoặc 'all'): 3
🔄 Đang khởi động lại 1 ví...
✅ Đã khởi động lại Wallet 3
```

Lưu ý: Khởi động lại sẽ **tạo ví mới hoàn toàn** với mnemonic mới.

#### 3️⃣ Xem chi tiết ví (View wallet details)

Xem đầy đủ thông tin ví:

```
Nhập ID ví cần xem chi tiết: 1

============================================================
📋 CHI TIẾT VÍ #1
============================================================

🏷️  Tên ví: Wallet 1
🔒 Mật khẩu: YourPassword123

📝 Mnemonic (24 từ):
------------------------------------------------------------
   1- 4: abandon      ability      able         about       
   5- 8: above        absent       absorb       abstract    
  9-12: absurd       abuse        access       accident    
 13-16: account      accuse       achieve      acid        
 17-20: acoustic     acquire      across       act         
 21-24: action       actor        actress      actual      

------------------------------------------------------------
📊 Trạng thái: RUNNING
⏰ Thời gian bắt đầu: 2025-11-01 14:30:25
============================================================
```

#### 4️⃣ Làm mới trạng thái (Refresh status)

Cập nhật lại dashboard với dữ liệu mới nhất.

#### 5️⃣ Thoát (Exit)

Đóng tất cả ví và thoát chương trình.

## Cấu trúc thư mục

```
bot-mine/
├── wallets/
│   ├── extensions/
│   │   └── lace/              # Lace extension
│   ├── wallet_1/
│   │   ├── mnemonic.txt       # 24 từ khôi phục
│   │   └── wallet_info.json   # Thông tin ví (tên, mật khẩu)
│   ├── wallet_2/
│   │   ├── mnemonic.txt
│   │   └── wallet_info.json
│   ├── wallet_states.json     # Trạng thái tất cả ví
│   └── bot_chrome_data/
│       ├── Wallet_1/          # Chrome data cho wallet 1
│       └── Wallet_2/          # Chrome data cho wallet 2
├── playwright_lace_bot.py     # Bot chính
└── README.md
```

## Lưu ý quan trọng

### Bảo mật

- ⚠️ **BACKUP** file `mnemonic.txt` và `wallet_info.json` của mỗi ví
- ⚠️ **KHÔNG chia sẻ** 24 từ khôi phục với ai
- ⚠️ Mật khẩu được dùng chung cho tất cả ví
- ✅ File `.gitignore` tự động bảo vệ dữ liệu ví khỏi Git

### Quản lý ví

- Trạng thái ví được **tự động lưu** vào `wallets/wallet_states.json`
- **Khởi động lại ví** sẽ xóa data cũ và tạo ví mới hoàn toàn
- **Dừng ví** chỉ đóng browser, không xóa dữ liệu
- Mỗi ví có browser profile riêng trong `bot_chrome_data/Wallet_X/`

### Mining

- Bot tự động bắt đầu mining session cho mỗi ví
- Giữ browser mở để mining tiếp tục
- Dashboard cho phép theo dõi trạng thái real-time
- Có thể dừng/khởi động lại từng ví riêng lẻ hoặc hàng loạt

## Xử lý lỗi

### Lỗi 429 - Too many requests ⚠️

**Nguyên nhân**: Server sm.midnight.gd giới hạn số lượng request từ cùng một IP trong khoảng thời gian ngắn.

**Dấu hiệu**:
- Dashboard hiển thị: `⚠️ 429 Too many requests`
- Thống kê cảnh báo: "X ví bị lỗi 429"

**Giải pháp**:
1. **Chờ 5-10 phút** trước khi khởi động lại ví bị lỗi
2. **Giảm batch size**: Sửa `batch_size = 5` thành `batch_size = 3` trong code
3. **Tăng delay**: Bot tự động delay 10s giữa các batch
4. **Khởi động lại từng ví một** thay vì nhiều ví cùng lúc

**Ví dụ xử lý**:
```
📈 THỐNG KÊ: Tổng: 10 | 🟢 Đang chạy: 7 | 🔴 Lỗi: 3
   ⚠️ Cảnh báo: 3 ví bị lỗi 429 (Too many requests)

ID       Tên             Trạng thái    Thời gian            Ghi chú                        
------------------------------------------------------------------------------------------
3        Wallet 3        🔴 failed    2m 20s               ⚠️ 429 Too many requests
7        Wallet 7        🔴 failed    1m 15s               ⚠️ 429 Too many requests
10       Wallet 10       🔴 failed    0m 45s               ⚠️ 429 Too many requests
```

Sau đó:
1. Chờ 10 phút
2. Chọn menu "Khởi động lại ví"
3. Nhập: `3,7,10` (khởi động lại từng ví một, cách nhau vài phút)

### Lỗi timeout khi tạo ví

- Bot đã tối ưu với timeout 90s cho page loads
- Batch size giới hạn 5 ví để tránh quá tải
- Kiểm tra extension Lace đã được load đúng

### Ví bị lỗi (🔴 failed)

- Xem chi tiết lỗi qua menu "Xem chi tiết ví"
- Sử dụng "Khởi động lại ví" để thử lại
- Bot tự động retry signature errors

### Mining không bắt đầu

- Kiểm tra wallet đã được tạo thành công
- Xem log để biết bước nào bị lỗi
- Đảm bảo có kết nối internet ổn định
- Dashboard hiển thị tỷ lệ thành công để dễ theo dõi

### Quản lý nhiều ví

- Khuyến nghị: Dừng ví lỗi trước khi khởi động lại
- Có thể chọn nhiều ví cùng lúc: `1,3,5` hoặc `all`
- Trạng thái được lưu tự động sau mỗi thao tác

## Flow hoàn chỉnh

1. **Tạo Lace Wallet**

   - Click "Create Wallet"
   - Chọn "Recovery phrase" (nếu có)
   - Copy 24 từ → Save to file
   - Paste để xác nhận
   - Đặt tên: `Wallet_1`, `Wallet_2`, ...
   - Nhập password

2. **Đăng ký Mining**

   - Mở https://sm.midnight.gd
   - Click "Get started"
   - Chọn Lace wallet
   - Click "Continue"
   - **Popup**: Authorize → Always
   - Click "Next"
   - Tick checkbox điều khoản
   - Click "Accept and sign"
   - **Popup**: Confirm → Nhập password → Confirm
   - Click "Start session"

3. **Dọn dẹp**
   - Đóng tab Lace extension
   - Đóng tab about:blank
   - Giữ tab mining đang chạy

## License

MIT
