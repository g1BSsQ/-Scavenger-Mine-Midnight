import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright
from mnemonic import Mnemonic
import json

class PlaywrightLaceBot:
    def __init__(self, num_wallets=1, password=""):
        self.num_wallets = num_wallets
        self.password = password
        self.base_dir = Path(__file__).parent
        self.wallets_dir = self.base_dir / "wallets"
        self.extension_path = self.wallets_dir / "extensions" / "lace"
        self.chrome_data_dir = self.wallets_dir / "bot_chrome_data"
        self.mnemo = Mnemonic("english")
        
    async def create_wallet_mnemonic(self, wallet_num):
        """Tạo mnemonic 24 từ cho wallet"""
        mnemonic = self.mnemo.generate(strength=256)  # 24 từ
        wallet_dir = self.wallets_dir / f"wallet_{wallet_num}"
        wallet_dir.mkdir(parents=True, exist_ok=True)
        
        with open(wallet_dir / "mnemonic.txt", "w") as f:
            f.write(mnemonic)
        
        print(f"✅ Wallet {wallet_num}: Created mnemonic")
        return mnemonic
    
    async def launch_browser_with_wallet(self, wallet_num, playwright):
        """Khởi động browser riêng cho mỗi wallet với Lace extension"""
        mnemonic = await self.create_wallet_mnemonic(wallet_num)
        
        # User data riêng cho mỗi wallet
        user_data = self.chrome_data_dir / f"Wallet_{wallet_num}"
        
        # Xóa data cũ để tạo wallet mới hoàn toàn
        if user_data.exists():
            import shutil
            shutil.rmtree(user_data)
            print(f"✅ Wallet {wallet_num}: Cleaned old browser data")
        
        user_data.mkdir(parents=True, exist_ok=True)
        
        # Tạo context với extension
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data),
            headless=False,
            args=[
                f"--disable-extensions-except={self.extension_path}",
                f"--load-extension={self.extension_path}",
            ],
            viewport={"width": 1280, "height": 800},
            # Tự động cho phép clipboard permission
            permissions=["clipboard-read", "clipboard-write"],
        )
        
        print(f"✅ Wallet {wallet_num}: Browser launched with Lace extension")
        
        # Tạo page mới
        page = await context.new_page()
        
        return context, page, mnemonic
    
    async def setup_lace_wallet(self, page, mnemonic, wallet_num, password):
        """Tự động tạo wallet trong Lace UI"""
        try:
            # Navigate to Lace extension
            extension_url = "chrome-extension://gafhhkghbfjjkeiendhlofajokpaflmk/app.html"
            await page.goto(extension_url, wait_until="domcontentloaded", timeout=30000)
            
            print(f"✅ Wallet {wallet_num}: Lace extension opened")
            
            # Xử lý clipboard permission popup nếu xuất hiện
            try:
                allow_btn = await page.query_selector('button:has-text("Allow")')
                if allow_btn:
                    await allow_btn.click()
                    print(f"✅ Wallet {wallet_num}: Allowed clipboard access")
                    await asyncio.sleep(1)
            except:
                pass
            
            # Wait và click nút Create wallet
            await page.wait_for_selector('[data-testid="create-wallet-button"]', timeout=20000)
            await page.click('[data-testid="create-wallet-button"]')
            print(f"✅ Wallet {wallet_num}: Clicked Create Wallet")
            
            await asyncio.sleep(2)
            
            # Bước 0: Chọn Recovery method (Recovery phrase) - có thể không xuất hiện
            # Thử đợi radio button, nếu không có thì bỏ qua
            try:
                await page.wait_for_selector('[data-testid="radio-btn-test-id-mnemonic"]', timeout=5000)
                await page.click('[data-testid="radio-btn-test-id-mnemonic"]')
                print(f"✅ Wallet {wallet_num}: Selected Recovery phrase method")
                
                await asyncio.sleep(1)
                
                # Click Next
                await page.click('[data-testid="wallet-setup-step-btn-next"]')
                print(f"✅ Wallet {wallet_num}: Clicked Next (recovery method)")
                
                await asyncio.sleep(2)
            except Exception as e:
                print(f"⚠️  Wallet {wallet_num}: Recovery method step skipped (may not be needed)")
            
            # Trang 1: Copy 24 từ mnemonic
            # Đợi nút Next xuất hiện (có 24 từ hiển thị)
            await page.wait_for_selector('[data-testid="wallet-setup-step-btn-next"]', timeout=15000)
            
            # Lấy 24 từ từ Lace (để lưu vào file - backup)
            mnemonic_words = []
            word_elements = await page.query_selector_all('[data-testid="mnemonic-word-writedown"]')
            
            for word_element in word_elements:
                word = await word_element.text_content()
                mnemonic_words.append(word.strip())
            
            lace_mnemonic = " ".join(mnemonic_words)
            print(f"✅ Wallet {wallet_num}: Captured {len(mnemonic_words)} mnemonic words")
            
            # Lưu mnemonic của Lace vào file (thay vì dùng mnemonic tự tạo)
            wallet_dir = self.wallets_dir / f"wallet_{wallet_num}"
            with open(wallet_dir / "mnemonic.txt", "w") as f:
                f.write(lace_mnemonic)
            
            # Lưu đầy đủ thông tin wallet vào file JSON
            wallet_info = {
                "wallet_name": f"Wallet {wallet_num}",
                "mnemonic": lace_mnemonic,
                "password": password
            }
            with open(wallet_dir / "wallet_info.json", "w", encoding="utf-8") as f:
                json.dump(wallet_info, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Wallet {wallet_num}: Saved Lace-generated mnemonic (24 words)")
            print(f"✅ Wallet {wallet_num}: Saved wallet info to wallet_info.json")
            
            # KHÔNG dùng clipboard nữa vì nhiều tab sẽ conflict
            # Thay vào đó sẽ điền thủ công từng ô
            
            # Click Next
            await page.click('[data-testid="wallet-setup-step-btn-next"]')
            print(f"✅ Wallet {wallet_num}: Clicked Next (copied mnemonic)")
            
            await asyncio.sleep(2)
            
            # Trang 2: Điền mnemonic thủ công để xác nhận (không dùng paste)
            await page.wait_for_selector('input[data-testid="mnemonic-word-input"]', timeout=15000)
            
            # Điền từng từ vào từng ô input
            for idx, word in enumerate(mnemonic_words):
                # Input fields có thể có data-testid hoặc name attribute
                input_selector = f'input[data-testid="mnemonic-word-input"]:nth-of-type({idx + 1})'
                input_field = await page.query_selector(input_selector)
                
                if not input_field:
                    # Thử selector khác
                    all_inputs = await page.query_selector_all('input[data-testid="mnemonic-word-input"]')
                    if idx < len(all_inputs):
                        input_field = all_inputs[idx]
                
                if input_field:
                    await input_field.fill(word)
            
            print(f"✅ Wallet {wallet_num}: Filled all {len(mnemonic_words)} words manually")
            
            await asyncio.sleep(1)
            
            # Click Next
            await page.click('[data-testid="wallet-setup-step-btn-next"]')
            print(f"✅ Wallet {wallet_num}: Confirmed mnemonic")
            
            await asyncio.sleep(2)
            
            # Trang 3: Đặt tên wallet và password
            # Đặt tên wallet
            wallet_name_input = await page.query_selector('input[data-testid="wallet-name-input"]')
            if not wallet_name_input:
                wallet_name_input = await page.query_selector('input[type="text"]')
            
            if wallet_name_input:
                await wallet_name_input.fill(f"Wallet {wallet_num}")
                print(f"✅ Wallet {wallet_num}: Set wallet name to Wallet {wallet_num}")
            
            # Điền password
            password_inputs = await page.query_selector_all('input[type="password"]')
            if len(password_inputs) >= 2:
                await password_inputs[0].fill(password)  # Password
                await password_inputs[1].fill(password)  # Confirm password
                print(f"✅ Wallet {wallet_num}: Set password")
            
            await asyncio.sleep(1)
            
            # Click Next/Create để hoàn tất
            next_button = await page.query_selector('[data-testid="wallet-setup-step-btn-next"]')
            if not next_button:
                next_button = await page.query_selector('button:has-text("Create")')
            
            if next_button:
                await next_button.click()
                print(f"✅ Wallet {wallet_num}: Wallet creation completed!")
            
            return True
            
        except Exception as e:
            print(f"❌ Wallet {wallet_num}: Error setting up Lace - {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def connect_to_mining_site(self, page, wallet_num):
        """Kết nối wallet với sm.midnight.gd và đăng ký mining"""
        try:
            # Mở tab mới cho mining site
            mining_page = await page.context.new_page()
            await mining_page.goto("https://sm.midnight.gd", wait_until="domcontentloaded", timeout=30000)
            
            print(f"✅ Wallet {wallet_num}: Opened mining site")
            
            await asyncio.sleep(3)
            
            # Click "Get started"
            get_started_btn = await mining_page.query_selector('button:has-text("Get started")')
            if get_started_btn:
                await get_started_btn.click()
                print(f"✅ Wallet {wallet_num}: Clicked Get started")
                await asyncio.sleep(3)
            
            # Click vào Lace wallet (radio button với INSTALLED badge)
            lace_btn = await mining_page.query_selector('button:has-text("Lace")')
            if lace_btn:
                await lace_btn.click()
                print(f"✅ Wallet {wallet_num}: Selected Lace wallet")
                await asyncio.sleep(2)
            
            # Click Continue
            continue_btn = await mining_page.query_selector('button:has-text("Continue")')
            if continue_btn:
                await continue_btn.click()
                print(f"✅ Wallet {wallet_num}: Clicked Continue")
                await asyncio.sleep(3)
            
            # Popup Lace: Authorize DApp - mở trong window riêng
            # Đợi popup window xuất hiện
            await asyncio.sleep(2)
            
            # Tìm popup window
            popup_page = None
            for p in page.context.pages:
                url = p.url
                if "lace-popup" in url or "chrome-extension://gafhhkghbfjjkeiendhlofajokpaflmk" in url:
                    # Kiểm tra nếu page có nút Authorize
                    try:
                        authorize_check = await p.query_selector('[data-testid="connect-authorize-button"]')
                        if authorize_check:
                            popup_page = p
                            break
                    except:
                        pass
            
            if popup_page:
                print(f"✅ Wallet {wallet_num}: Found Lace popup window")
                # Click Authorize
                authorize_btn = await popup_page.query_selector('[data-testid="connect-authorize-button"]')
                if authorize_btn:
                    await authorize_btn.click()
                    print(f"✅ Wallet {wallet_num}: Clicked Authorize")
                    await asyncio.sleep(2)
                
                # Click Always (nếu có)
                always_btn = await popup_page.query_selector('button:has-text("Always")')
                if always_btn:
                    await always_btn.click()
                    await asyncio.sleep(1)
            
            # Quay lại main page, click Next
            await mining_page.wait_for_selector('button:has-text("Next")', timeout=15000)
            next_btn = await mining_page.query_selector('button:has-text("Next")')
            if next_btn:
                await next_btn.click()
                print(f"✅ Wallet {wallet_num}: Clicked Next (after wallet connect)")
                await asyncio.sleep(3)
            
            # Accept terms: Tick checkbox
            checkbox = await mining_page.query_selector('#accept-terms')
            if checkbox:
                await checkbox.click()
                print(f"✅ Wallet {wallet_num}: Checked terms checkbox")
                await asyncio.sleep(1)
            
            # Click "Accept and sign"
            accept_sign_btn = await mining_page.query_selector('button:has-text("Accept and sign")')
            if accept_sign_btn:
                await accept_sign_btn.click()
                print(f"✅ Wallet {wallet_num}: Clicked Accept and sign")
                await asyncio.sleep(3)
            
            # Popup Lace: Confirm Data
            await asyncio.sleep(2)
            
            # Tìm popup window cho Confirm Data
            popup_page = None
            for p in page.context.pages:
                url = p.url
                if "lace-popup" in url or "chrome-extension://gafhhkghbfjjkeiendhlofajokpaflmk" in url:
                    try:
                        confirm_check = await p.query_selector('[data-testid="dapp-transaction-confirm"]')
                        if confirm_check:
                            popup_page = p
                            break
                    except:
                        pass
            
            if popup_page:
                print(f"✅ Wallet {wallet_num}: Found Lace Confirm Data popup")
                
                # Bước 1: Click Confirm (dapp-transaction-confirm)
                confirm_btn = await popup_page.query_selector('[data-testid="dapp-transaction-confirm"]')
                if confirm_btn:
                    await confirm_btn.click()
                    print(f"✅ Wallet {wallet_num}: Clicked Confirm (step 1)")
                    await asyncio.sleep(2)
                
                # Bước 2: Nhập password
                password_input = await popup_page.query_selector('[data-testid="password-input"]')
                if password_input:
                    await password_input.fill(self.password)
                    print(f"✅ Wallet {wallet_num}: Entered password")
                    await asyncio.sleep(1)
                
                # Bước 3: Click Confirm để sign (sign-transaction-confirm)
                sign_confirm_btn = await popup_page.query_selector('[data-testid="sign-transaction-confirm"]')
                if sign_confirm_btn:
                    await sign_confirm_btn.click()
                    print(f"✅ Wallet {wallet_num}: Signed message - Registration completed!")
                    await asyncio.sleep(2)
                
                # Đóng popup
                await popup_page.close()
                print(f"✅ Wallet {wallet_num}: Closed popup")
            
            # Quay lại trang chính, click "Start session"
            await asyncio.sleep(2)
            start_session_btn = await mining_page.query_selector('button:has-text("Start session")')
            if start_session_btn:
                await start_session_btn.click()
                print(f"✅ Wallet {wallet_num}: Started mining session!")
                await asyncio.sleep(3)
            
            # Dọn dẹp: Đóng các tab không cần thiết
            for p in page.context.pages:
                url = p.url
                # Giữ lại tab mining, đóng các tab khác
                if "about:blank" in url or "chrome-extension://gafhhkghbfjjkeiendhlofajokpaflmk/app.html" in url:
                    try:
                        await p.close()
                        print(f"✅ Wallet {wallet_num}: Closed unnecessary tab: {url[:50]}...")
                    except:
                        pass
            
            print(f"✅ Wallet {wallet_num}: Connected and registered successfully")
            return True
            
        except Exception as e:
            print(f"❌ Wallet {wallet_num}: Error connecting to mining site - {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run(self):
        """Chạy bot với N wallets"""
        async with async_playwright() as playwright:
            tasks = []
            
            for i in range(1, self.num_wallets + 1):
                task = self.process_wallet(i, playwright)
                tasks.append(task)
            
            # Chạy tất cả wallets song song
            await asyncio.gather(*tasks)
            
            # Giữ browsers mở
            print(f"\n✅ All {self.num_wallets} wallets are running")
            print("Press Ctrl+C to stop...")
            
            try:
                await asyncio.Event().wait()  # Chờ vô hạn
            except KeyboardInterrupt:
                print("\n👋 Stopping bot...")
    
    async def process_wallet(self, wallet_num, playwright):
        """Xử lý 1 wallet hoàn chỉnh"""
        try:
            # Launch browser
            context, page, mnemonic = await self.launch_browser_with_wallet(wallet_num, playwright)
            
            # Setup Lace wallet
            success = await self.setup_lace_wallet(page, mnemonic, wallet_num, self.password)
            
            if success:
                # Connect to mining site and register
                await self.connect_to_mining_site(page, wallet_num)
            
            # Giữ browser mở
            await asyncio.Event().wait()
            
        except Exception as e:
            print(f"❌ Wallet {wallet_num}: Fatal error - {e}")
            import traceback
            traceback.print_exc()


async def main():
    # Nhập số lượng wallets và password
    num_wallets = int(input("Số lượng wallets: "))
    password = input("Mật khẩu cho tất cả wallets: ")
    
    bot = PlaywrightLaceBot(num_wallets=num_wallets, password=password)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
