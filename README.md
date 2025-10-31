# Lace Wallet Auto Mining Bot

Bot tự động tạo ví Lace và đăng ký mining trên Scavenger Mine (sm.midnight.gd).

## Tính năng

- ✅ Tự động tạo N ví Lace độc lập
- ✅ Mỗi ví có 24 từ khôi phục riêng
- ✅ Tự động kết nối với sm.midnight.gd
- ✅ Tự động ký message và đăng ký mining
- ✅ Tự động bắt đầu mining session
- ✅ Chạy song song nhiều ví cùng lúc

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
Số lượng wallets: 5
Mật khẩu cho tất cả wallets: YourStrongPassword123
```

Bot sẽ:

1. Tạo 5 browser độc lập
2. Mỗi browser tạo 1 ví Lace mới
3. Tự động đăng ký mining
4. Bắt đầu mining session

## Cấu trúc thư mục

```
bot-mine/
├── wallets/
│   ├── extensions/
│   │   └── lace/              # Lace extension
│   ├── wallet_1/
│   │   └── mnemonic.txt       # 24 từ khôi phục
│   ├── wallet_2/
│   │   └── mnemonic.txt
│   └── bot_chrome_data/
│       ├── Wallet_1/          # Chrome data cho wallet 1
│       └── Wallet_2/          # Chrome data cho wallet 2
├── playwright_lace_bot.py     # Bot chính
└── README.md
```

## Lưu ý quan trọng

### Bảo mật

- ⚠️ **BACKUP** file `mnemonic.txt` của mỗi ví
- ⚠️ **KHÔNG chia sẻ** 24 từ khôi phục với ai
- ⚠️ Mật khẩu được dùng chung cho tất cả ví

### Quản lý ví

- Mỗi lần chạy bot sẽ **xóa data cũ** và tạo ví mới
- 24 từ khôi phục được lưu trong `wallets/wallet_X/mnemonic.txt`
- Mỗi ví có browser profile riêng

### Mining

- Bot tự động bắt đầu mining session
- Giữ browser mở để mining tiếp tục
- Nhấn `Ctrl+C` để dừng bot

## Xử lý lỗi

### Lỗi timeout khi tạo ví

- Tăng timeout trong code nếu mạng chậm
- Kiểm tra extension Lace đã được load đúng

### Popup clipboard permission

- Bot tự động cho phép clipboard access
- Nếu vẫn xuất hiện, click "Allow" thủ công

### Mining không bắt đầu

- Kiểm tra wallet đã được tạo thành công
- Xem log để biết bước nào bị lỗi
- Đảm bảo có kết nối internet ổn định

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
