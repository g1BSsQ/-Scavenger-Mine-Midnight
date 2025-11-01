import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright
from mnemonic import Mnemonic
import json
from datetime import datetime

class PlaywrightLaceBot:
    def __init__(self, num_wallets=1, password=""):
        self.num_wallets = num_wallets
        self.password = password
        self.base_dir = Path(__file__).parent
        self.wallets_dir = self.base_dir / "wallets"
        self.extension_path = self.wallets_dir / "extensions" / "lace"
        self.chrome_data_dir = self.wallets_dir / "bot_chrome_data"
        self.mnemo = Mnemonic("english")
        
        # Quản lý trạng thái ví
        self.wallet_states = {}  # {wallet_num: {"status": "running/stopped/failed", "context": context, "start_time": datetime}}
        self.playwright_instance = None
        self.state_file = self.wallets_dir / "wallet_states.json"
        
    def save_wallet_states(self):
        """Lưu trạng thái ví vào file"""
        try:
            states_to_save = {}
            for wallet_num, state in self.wallet_states.items():
                states_to_save[wallet_num] = {
                    "status": state["status"],
                    "start_time": state["start_time"].isoformat() if state["start_time"] else None,
                    "error": state.get("error")
                }
            
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(states_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Không thể lưu trạng thái: {e}")
    
    def load_wallet_states(self):
        """Tải trạng thái ví từ file"""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r", encoding="utf-8") as f:
                    states = json.load(f)
                
                for wallet_num_str, state_data in states.items():
                    wallet_num = int(wallet_num_str)
                    self.wallet_states[wallet_num] = {
                        "status": state_data["status"],
                        "context": None,  # Context sẽ được tạo lại khi restart
                        "start_time": datetime.fromisoformat(state_data["start_time"]) if state_data["start_time"] else datetime.now(),
                        "error": state_data.get("error")
                    }
                print(f"✅ Đã tải trạng thái {len(self.wallet_states)} ví từ file")
        except Exception as e:
            print(f"⚠️ Không thể tải trạng thái: {e}")
        
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
            # Navigate to Lace extension - tăng timeout cho nhiều tab
            extension_url = "chrome-extension://gafhhkghbfjjkeiendhlofajokpaflmk/app.html"
            await page.goto(extension_url, wait_until="domcontentloaded", timeout=90000)
            
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
            
            # Wait và click nút Create wallet - click ngay khi thấy
            await page.wait_for_selector('[data-testid="create-wallet-button"]', state='visible', timeout=60000)
            await asyncio.sleep(1)  # Đợi render và enable
            await page.click('[data-testid="create-wallet-button"]', timeout=30000, force=True)
            print(f"✅ Wallet {wallet_num}: Clicked Create Wallet")
            
            await asyncio.sleep(2)
            
            # Bước 0: Chọn Recovery method (Recovery phrase) - có thể không xuất hiện
            # Thử đợi radio button, nếu không có thì bỏ qua
            try:
                await page.wait_for_selector('[data-testid="radio-btn-test-id-mnemonic"]', state='visible', timeout=5000)
                await asyncio.sleep(0.5)
                await page.click('[data-testid="radio-btn-test-id-mnemonic"]', timeout=30000)
                print(f"✅ Wallet {wallet_num}: Selected Recovery phrase method")
                
                await asyncio.sleep(1)
                
                # Click Next
                await page.click('[data-testid="wallet-setup-step-btn-next"]', timeout=30000)
                print(f"✅ Wallet {wallet_num}: Clicked Next (recovery method)")
                
                await asyncio.sleep(2)
            except Exception as e:
                print(f"⚠️  Wallet {wallet_num}: Recovery method step skipped (may not be needed)")
            
            # Trang 1: Copy 24 từ mnemonic
            # Đợi nút Next xuất hiện (có 24 từ hiển thị)
            await page.wait_for_selector('[data-testid="wallet-setup-step-btn-next"]', state='visible', timeout=60000)
            
            # Đợi 24 từ load đầy đủ
            await asyncio.sleep(2)
            
            # Lấy 24 từ từ Lace (để lưu vào file - backup)
            mnemonic_words = []
            word_elements = await page.query_selector_all('[data-testid="mnemonic-word-writedown"]')
            
            # Retry nếu chưa load đủ 24 từ
            retry_count = 0
            while len(word_elements) < 24 and retry_count < 5:
                await asyncio.sleep(1)
                word_elements = await page.query_selector_all('[data-testid="mnemonic-word-writedown"]')
                retry_count += 1
            
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
            await asyncio.sleep(1)
            await page.click('[data-testid="wallet-setup-step-btn-next"]', timeout=30000)
            print(f"✅ Wallet {wallet_num}: Clicked Next (copied mnemonic)")
            
            await asyncio.sleep(2)
            
            # Trang 2: Điền mnemonic thủ công để xác nhận (không dùng paste)
            await page.wait_for_selector('input[data-testid="mnemonic-word-input"]', state='visible', timeout=60000)
            
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
            await page.click('[data-testid="wallet-setup-step-btn-next"]', timeout=30000)
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
            await asyncio.sleep(0.5)
            password_inputs = await page.query_selector_all('input[type="password"]')
            if len(password_inputs) >= 2:
                await password_inputs[0].fill(password)  # Password
                await password_inputs[1].fill(password)  # Confirm password
                print(f"✅ Wallet {wallet_num}: Set password")
            
            await asyncio.sleep(1)
            
            # Click Next/Create để hoàn tất - đợi lâu hơn vì có nhiều tab
            await page.wait_for_selector('[data-testid="wallet-setup-step-btn-next"]', state='visible', timeout=60000)
            await asyncio.sleep(1)
            next_button = await page.query_selector('[data-testid="wallet-setup-step-btn-next"]')
            if not next_button:
                next_button = await page.query_selector('button:has-text("Create")')
            
            if next_button:
                await next_button.click(timeout=30000)
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
            
            # Kiểm tra response để bắt lỗi 429
            response = await mining_page.goto("https://sm.midnight.gd", wait_until="domcontentloaded", timeout=90000)
            
            # Kiểm tra status code
            if response and response.status == 429:
                error_msg = "429 Too many requests - Server đang giới hạn request"
                print(f"❌ Wallet {wallet_num}: {error_msg}")
                # Lưu lỗi vào state
                if wallet_num in self.wallet_states:
                    self.wallet_states[wallet_num]["error"] = error_msg
                    self.wallet_states[wallet_num]["status"] = "failed"
                    self.save_wallet_states()
                return False
            
            print(f"✅ Wallet {wallet_num}: Opened mining site (Status: {response.status if response else 'Unknown'})")
            
            # Kiểm tra nội dung trang có chứa thông báo lỗi 429
            page_content = await mining_page.content()
            if "429" in page_content or "too many requests" in page_content.lower():
                error_msg = "429 Too many requests detected in page content"
                print(f"❌ Wallet {wallet_num}: {error_msg}")
                if wallet_num in self.wallet_states:
                    self.wallet_states[wallet_num]["error"] = error_msg
                    self.wallet_states[wallet_num]["status"] = "failed"
                    self.save_wallet_states()
                return False
            
            await asyncio.sleep(3)
            
            # Click "Get started"
            get_started_btn = await mining_page.query_selector('button:has-text("Get started")')
            if get_started_btn:
                await get_started_btn.click()
                print(f"✅ Wallet {wallet_num}: Clicked Get started")
                await asyncio.sleep(3)
            
            # Click vào Lace wallet (radio button với INSTALLED badge)
            # Đợi nút enable (có thể mất thời gian)
            await asyncio.sleep(2)
            lace_btn = await mining_page.query_selector('button:has-text("Lace")')
            if lace_btn:
                # Đợi nút enabled
                for i in range(30):  # Thử 30 lần, mỗi lần 1s
                    is_enabled = await lace_btn.is_enabled()
                    if is_enabled:
                        break
                    await asyncio.sleep(1)
                
                await lace_btn.click(timeout=30000)
                print(f"✅ Wallet {wallet_num}: Selected Lace wallet")
                await asyncio.sleep(2)
            
            # Click Continue
            continue_btn = await mining_page.query_selector('button:has-text("Continue")')
            if continue_btn:
                await continue_btn.click()
                print(f"✅ Wallet {wallet_num}: Clicked Continue")
                await asyncio.sleep(3)
            
            # Popup Lace: Authorize DApp - mở trong window riêng
            # Đợi popup window xuất hiện - đợi lâu hơn với nhiều tab
            await asyncio.sleep(3)
            
            # Tìm popup window - thử nhiều lần
            popup_page = None
            for attempt in range(10):  # Thử 10 lần, mỗi lần 1s
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
                    break
                await asyncio.sleep(1)
            
            if popup_page:
                print(f"✅ Wallet {wallet_num}: Found Lace popup window")
                # Click Authorize - đợi visible
                await popup_page.wait_for_selector('[data-testid="connect-authorize-button"]', state='visible', timeout=10000)
                await asyncio.sleep(0.5)
                authorize_btn = await popup_page.query_selector('[data-testid="connect-authorize-button"]')
                if authorize_btn:
                    await authorize_btn.click(timeout=30000)
                    print(f"✅ Wallet {wallet_num}: Clicked Authorize")
                    await asyncio.sleep(2)
                
                # Click Always (nếu có)
                always_btn = await popup_page.query_selector('button:has-text("Always")')
                if always_btn:
                    await always_btn.click(timeout=30000)
                    await asyncio.sleep(1)
                
                # Đóng popup sau khi authorize thành công
                try:
                    await popup_page.close()
                    print(f"✅ Wallet {wallet_num}: Closed Authorize popup")
                except Exception as e:
                    print(f"⚠️  Wallet {wallet_num}: Could not close Authorize popup - {e}")
            
            # Quay lại main page, click Next - đợi visible
            await mining_page.wait_for_selector('button:has-text("Next")', state='visible', timeout=60000)
            await asyncio.sleep(1)
            next_btn = await mining_page.query_selector('button:has-text("Next")')
            if next_btn:
                await next_btn.click(timeout=30000)
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
            await asyncio.sleep(3)
            
            # Tìm popup window cho Confirm Data - thử nhiều lần
            popup_page = None
            for attempt in range(10):
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
                    break
                await asyncio.sleep(1)
            
            if popup_page:
                print(f"✅ Wallet {wallet_num}: Found Lace Confirm Data popup")
                
                # Bước 1: Click Confirm (dapp-transaction-confirm) - đợi visible
                await popup_page.wait_for_selector('[data-testid="dapp-transaction-confirm"]', state='visible', timeout=10000)
                await asyncio.sleep(0.5)
                confirm_btn = await popup_page.query_selector('[data-testid="dapp-transaction-confirm"]')
                if confirm_btn:
                    await confirm_btn.click(timeout=30000)
                    print(f"✅ Wallet {wallet_num}: Clicked Confirm (step 1)")
                    await asyncio.sleep(2)
                
                # Bước 2: Nhập password
                await popup_page.wait_for_selector('[data-testid="password-input"]', state='visible', timeout=10000)
                password_input = await popup_page.query_selector('[data-testid="password-input"]')
                if password_input:
                    await password_input.fill(self.password)
                    print(f"✅ Wallet {wallet_num}: Entered password")
                    await asyncio.sleep(1)
                
                # Bước 3: Click Confirm để sign (sign-transaction-confirm)
                await popup_page.wait_for_selector('[data-testid="sign-transaction-confirm"]', state='visible', timeout=10000)
                await asyncio.sleep(0.5)
                sign_confirm_btn = await popup_page.query_selector('[data-testid="sign-transaction-confirm"]')
                if sign_confirm_btn:
                    await sign_confirm_btn.click(timeout=30000)
                    print(f"✅ Wallet {wallet_num}: Clicked Sign button")
                    
                    # Đợi signature được gửi - QUAN TRỌNG!
                    await asyncio.sleep(5)
                    
                    print(f"✅ Wallet {wallet_num}: Signed message - Registration completed!")
                
                # Đợi popup tự đóng hoặc đóng thủ công
                try:
                    # Đợi button biến mất (popup đóng)
                    await popup_page.wait_for_selector('[data-testid="sign-transaction-confirm"]', state='hidden', timeout=10000)
                    print(f"✅ Wallet {wallet_num}: Sign button hidden, closing popup...")
                except:
                    print(f"✅ Wallet {wallet_num}: Timeout waiting for auto-close, closing manually...")
                
                # Đóng popup
                try:
                    if not popup_page.is_closed():
                        await popup_page.close()
                        print(f"✅ Wallet {wallet_num}: Closed Sign popup successfully")
                except Exception as e:
                    print(f"⚠️  Wallet {wallet_num}: Could not close Sign popup - {e}")
            
            # Quay lại trang chính, click "Start session" - đợi lâu hơn
            await asyncio.sleep(5)  # Đợi signature xử lý
            
            # Kiểm tra error message trước
            try:
                error_msg = await mining_page.query_selector('text=We could not find the signed message')
                if error_msg:
                    print(f"❌ Wallet {wallet_num}: Signature not found - retrying...")
                    
                    # Đợi trang reset
                    await asyncio.sleep(3)
                    
                    # Retry: Tìm button "Accept and sign" hoặc "Sign"
                    accept_sign_btn = await mining_page.query_selector('button:has-text("Accept and sign")')
                    if not accept_sign_btn:
                        accept_sign_btn = await mining_page.query_selector('button:has-text("Sign")')
                    
                    if accept_sign_btn:
                        # Check checkbox lại nếu cần
                        checkbox = await mining_page.query_selector('#accept-terms')
                        if checkbox:
                            is_checked = await checkbox.is_checked()
                            if not is_checked:
                                await checkbox.click()
                                await asyncio.sleep(1)
                        
                        await accept_sign_btn.click(timeout=30000)
                        print(f"✅ Wallet {wallet_num}: Retry - Clicked Accept and sign")
                        await asyncio.sleep(3)
                        
                        # Tìm popup lại
                        popup_page = None
                        for attempt in range(10):
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
                                break
                            await asyncio.sleep(1)
                        
                        if popup_page:
                            # Retry signing
                            print(f"✅ Wallet {wallet_num}: Retry - Found popup")
                            await popup_page.wait_for_selector('[data-testid="dapp-transaction-confirm"]', state='visible', timeout=10000)
                            await asyncio.sleep(0.5)
                            confirm_btn = await popup_page.query_selector('[data-testid="dapp-transaction-confirm"]')
                            if confirm_btn:
                                await confirm_btn.click(timeout=30000)
                                print(f"✅ Wallet {wallet_num}: Retry - Clicked Confirm")
                                await asyncio.sleep(2)
                            
                            password_input = await popup_page.query_selector('[data-testid="password-input"]')
                            if password_input:
                                await password_input.fill(self.password)
                                print(f"✅ Wallet {wallet_num}: Retry - Entered password")
                                await asyncio.sleep(1)
                            
                            sign_confirm_btn = await popup_page.query_selector('[data-testid="sign-transaction-confirm"]')
                            if sign_confirm_btn:
                                await sign_confirm_btn.click(timeout=30000)
                                print(f"✅ Wallet {wallet_num}: Retry - Clicked Sign")
                                await asyncio.sleep(7)  # Đợi lâu hơn
                                print(f"✅ Wallet {wallet_num}: Retry - Signed successfully")
                            
                            # Đóng popup sau khi retry thành công
                            try:
                                await popup_page.wait_for_selector('[data-testid="sign-transaction-confirm"]', state='hidden', timeout=10000)
                                print(f"✅ Wallet {wallet_num}: Retry - Sign button hidden, closing popup...")
                            except:
                                print(f"✅ Wallet {wallet_num}: Retry - Timeout waiting for auto-close, closing manually...")
                            
                            # Đóng popup
                            try:
                                if not popup_page.is_closed():
                                    await popup_page.close()
                                    print(f"✅ Wallet {wallet_num}: Retry - Closed Sign popup successfully")
                            except Exception as e:
                                print(f"⚠️  Wallet {wallet_num}: Retry - Could not close Sign popup - {e}")
                            
                            await asyncio.sleep(5)
                    else:
                        print(f"⚠️ Wallet {wallet_num}: Retry failed - No popup found after 10 attempts")
                else:
                    print(f"⚠️  Wallet {wallet_num}: Retry failed - Accept and sign button not found")
            except Exception as retry_error:
                print(f"⚠️  Wallet {wallet_num}: Retry error - {retry_error}")
            
            # Click "Start session" - nếu có
            try:
                await mining_page.wait_for_selector('button:has-text("Start session")', state='visible', timeout=60000)
                await asyncio.sleep(1)
                start_session_btn = await mining_page.query_selector('button:has-text("Start session")')
                if start_session_btn:
                    await start_session_btn.click(timeout=30000)
                    print(f"✅ Wallet {wallet_num}: Started mining session!")
                    await asyncio.sleep(3)
            except Exception as e:
                print(f"⚠️  Wallet {wallet_num}: Could not start session - {e}")
                print(f"⚠️  Wallet {wallet_num}: Signature may have failed, skipping this wallet")
                return False
            
            # Dọn dẹp: Đóng các tab không cần thiết
            for p in page.context.pages:
                url = p.url
                # Giữ lại tab mining, đóng các tab khác (bao gồm popup windows)
                if "about:blank" in url or "chrome-extension://gafhhkghbfjjkeiendhlofajokpaflmk/app.html" in url or "lace-popup" in url:
                    try:
                        await p.close()
                        print(f"✅ Wallet {wallet_num}: Closed unnecessary tab: {url[:50]}...")
                    except:
                        pass
            
            # Đóng tất cả popup windows còn lại
            try:
                all_pages = page.context.pages
                for p in all_pages:
                    if p != mining_page and "sm.midnight.gd" not in p.url:
                        try:
                            if not p.is_closed():
                                await p.close()
                                print(f"✅ Wallet {wallet_num}: Closed remaining popup/tab")
                        except:
                            pass
            except Exception as e:
                print(f"⚠️  Wallet {wallet_num}: Error during cleanup - {e}")
            
            print(f"✅ Wallet {wallet_num}: Connected and registered successfully")
            return True
            
        except Exception as e:
            error_message = str(e)
            
            # Kiểm tra lỗi 429
            if "429" in error_message or "too many requests" in error_message.lower():
                error_msg = "429 Too many requests - Server đang giới hạn request"
                print(f"❌ Wallet {wallet_num}: {error_msg}")
                # Lưu lỗi vào state
                if wallet_num in self.wallet_states:
                    self.wallet_states[wallet_num]["error"] = error_msg
                    self.wallet_states[wallet_num]["status"] = "failed"
                    self.save_wallet_states()
            else:
                print(f"❌ Wallet {wallet_num}: Error connecting to mining site - {error_message}")
                # Lưu lỗi vào state
                if wallet_num in self.wallet_states:
                    self.wallet_states[wallet_num]["error"] = error_message[:100]  # Giới hạn độ dài
                    self.wallet_states[wallet_num]["status"] = "failed"
                    self.save_wallet_states()
            
            import traceback
            traceback.print_exc()
            return False
    
    async def run(self):
        """Chạy bot với N wallets - giới hạn 5 concurrent để tránh timeout"""
        async with async_playwright() as playwright:
            self.playwright_instance = playwright
            
            # Chạy từng batch 5 wallets để tránh quá tải
            batch_size = 5
            
            for batch_start in range(0, self.num_wallets, batch_size):
                batch_end = min(batch_start + batch_size, self.num_wallets)
                batch_wallets = range(batch_start + 1, batch_end + 1)
                
                print(f"\n🚀 Starting batch: Wallets {batch_start + 1} to {batch_end}")
                
                # Delay giữa các batch để tránh 429
                if batch_start > 0:
                    delay = 10
                    print(f"⏳ Waiting {delay}s before next batch to avoid rate limiting...")
                    await asyncio.sleep(delay)
                
                tasks = []
                for wallet_num in batch_wallets:
                    task = self.process_wallet(wallet_num, playwright)
                    tasks.append(task)
                
                # Chạy batch này
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Cập nhật trạng thái
                for i, wallet_num in enumerate(batch_wallets):
                    result = results[i]
                    if isinstance(result, Exception):
                        self.wallet_states[wallet_num] = {
                            "status": "failed",
                            "context": None,
                            "start_time": datetime.now(),
                            "error": str(result)
                        }
                    elif result is not None:
                        self.wallet_states[wallet_num] = {
                            "status": "running",
                            "context": result,
                            "start_time": datetime.now(),
                            "error": None
                        }
                    else:
                        self.wallet_states[wallet_num] = {
                            "status": "failed",
                            "context": None,
                            "start_time": datetime.now(),
                            "error": "Unknown error"
                        }
                
                # Lưu trạng thái sau mỗi batch
                self.save_wallet_states()
                
                print(f"✅ Batch {batch_start + 1}-{batch_end} completed\n")
            
            # Hiển thị menu quản lý
            await self.show_management_menu()
    
    async def show_management_menu(self):
        """Hiển thị menu quản lý ví"""
        while True:
            print("\n" + "="*60)
            print("📊 WALLET MANAGEMENT DASHBOARD")
            print("="*60)
            
            # Hiển thị trạng thái tất cả ví
            self.display_wallet_status()
            
            print("\n" + "-"*60)
            print("🎮 MENU:")
            print("  1. ⏸️  Dừng ví (Stop wallets)")
            print("  2. ▶️  Khởi động lại ví (Restart wallets)")
            print("  3. 🔍 Xem chi tiết ví (View wallet details)")
            print("  4. 🔄 Làm mới trạng thái (Refresh status)")
            print("  5. 🚪 Thoát (Exit)")
            print("-"*60)
            
            choice = input("\nChọn hành động (1-5): ").strip()
            
            if choice == "1":
                await self.stop_wallets_interactive()
            elif choice == "2":
                await self.restart_wallets_interactive()
            elif choice == "3":
                self.view_wallet_details()
            elif choice == "4":
                continue  # Refresh bằng cách loop lại
            elif choice == "5":
                print("\n👋 Đang đóng tất cả ví...")
                await self.stop_all_wallets()
                break
            else:
                print("❌ Lựa chọn không hợp lệ!")
    
    def view_wallet_details(self):
        """Xem chi tiết thông tin ví"""
        wallet_id = input("\nNhập ID ví cần xem chi tiết: ").strip()
        
        try:
            wallet_num = int(wallet_id)
        except ValueError:
            print("❌ ID không hợp lệ!")
            return
        
        if wallet_num not in self.wallet_states:
            print(f"❌ Wallet {wallet_num} không tồn tại!")
            return
        
        # Đọc thông tin từ file
        wallet_dir = self.wallets_dir / f"wallet_{wallet_num}"
        info_file = wallet_dir / "wallet_info.json"
        
        print("\n" + "="*60)
        print(f"📋 CHI TIẾT VÍ #{wallet_num}")
        print("="*60)
        
        if info_file.exists():
            try:
                with open(info_file, "r", encoding="utf-8") as f:
                    info = json.load(f)
                
                print(f"\n🏷️  Tên ví: {info.get('wallet_name', 'N/A')}")
                print(f"🔒 Mật khẩu: {info.get('password', 'N/A')}")
                print(f"\n📝 Mnemonic (24 từ):")
                print("-"*60)
                
                mnemonic = info.get('mnemonic', '')
                if mnemonic:
                    words = mnemonic.split()
                    for i in range(0, len(words), 4):
                        row = words[i:i+4]
                        print(f"  {i+1:2d}-{i+4:2d}: " + "  ".join(f"{w:<12}" for w in row))
                
            except Exception as e:
                print(f"❌ Không thể đọc thông tin ví: {e}")
        else:
            print("\n⚠️ Chưa có file thông tin ví")
        
        # Hiển thị trạng thái
        state = self.wallet_states[wallet_num]
        print("\n" + "-"*60)
        print(f"📊 Trạng thái: {state['status'].upper()}")
        print(f"⏰ Thời gian bắt đầu: {state['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        if state.get('error'):
            print(f"❌ Lỗi: {state['error']}")
        
        print("="*60)
        input("\nNhấn Enter để quay lại menu...")
    
    def display_wallet_status(self):
        """Hiển thị trạng thái tất cả ví"""
        if not self.wallet_states:
            print("  Chưa có ví nào được tạo")
            return
        
        # Thống kê
        total = len(self.wallet_states)
        running = sum(1 for s in self.wallet_states.values() if s["status"] == "running")
        stopped = sum(1 for s in self.wallet_states.values() if s["status"] == "stopped")
        failed = sum(1 for s in self.wallet_states.values() if s["status"] == "failed")
        
        # Đếm số lỗi 429
        error_429 = sum(1 for s in self.wallet_states.values() 
                       if s.get("error") and "429" in s.get("error", ""))
        
        print(f"\n📈 THỐNG KÊ: Tổng: {total} | 🟢 Đang chạy: {running} | 🟡 Đã dừng: {stopped} | 🔴 Lỗi: {failed}")
        print(f"   Tỷ lệ thành công: {running}/{total} ({running*100//total if total > 0 else 0}%)")
        
        if error_429 > 0:
            print(f"   ⚠️ Cảnh báo: {error_429} ví bị lỗi 429 (Too many requests)")
        
        print(f"\n{'ID':<8} {'Tên':<15} {'Trạng thái':<12} {'Thời gian':<20} {'Ghi chú':<30}")
        print("-"*90)
        
        for wallet_num in sorted(self.wallet_states.keys()):
            state = self.wallet_states[wallet_num]
            status = state["status"]
            
            # Icon theo trạng thái
            if status == "running":
                icon = "🟢"
            elif status == "stopped":
                icon = "🟡"
            else:
                icon = "🔴"
            
            # Tính thời gian chạy
            start_time = state["start_time"]
            elapsed = datetime.now() - start_time
            time_str = f"{int(elapsed.total_seconds() / 60)}m {int(elapsed.total_seconds() % 60)}s"
            
            # Ghi chú - highlight lỗi 429
            error = state.get("error", "")
            if error:
                if "429" in error:
                    note = "⚠️ 429 Too many requests"[:30]
                else:
                    note = error[:30]
            else:
                note = "OK"
            
            print(f"{wallet_num:<8} {f'Wallet {wallet_num}':<15} {icon} {status:<9} {time_str:<20} {note:<30}")
    
    async def stop_wallets_interactive(self):
        """Cho phép chọn và dừng các ví"""
        wallet_ids = input("\nNhập ID ví cần dừng (cách nhau bởi dấu phấy, vd: 1,3,5 hoặc 'all'): ").strip()
        
        if wallet_ids.lower() == "all":
            selected = list(self.wallet_states.keys())
        else:
            try:
                selected = [int(x.strip()) for x in wallet_ids.split(",")]
            except ValueError:
                print("❌ Định dạng không hợp lệ!")
                return
        
        for wallet_num in selected:
            if wallet_num not in self.wallet_states:
                print(f"❌ Wallet {wallet_num} không tồn tại")
                continue
            
            state = self.wallet_states[wallet_num]
            if state["status"] == "stopped":
                print(f"⚠️ Wallet {wallet_num} đã dừng rồi")
                continue
            
            # Đóng browser context
            if state["context"]:
                try:
                    await state["context"].close()
                    print(f"✅ Đã dừng Wallet {wallet_num}")
                except Exception as e:
                    print(f"❌ Lỗi khi dừng Wallet {wallet_num}: {e}")
            
            # Cập nhật trạng thái
            state["status"] = "stopped"
            state["context"] = None
        
        # Lưu trạng thái
        self.save_wallet_states()
    
    async def restart_wallets_interactive(self):
        """Cho phép chọn và khởi động lại các ví"""
        wallet_ids = input("\nNhập ID ví cần khởi động lại (cách nhau bởi dấu phấy, vd: 1,3,5 hoặc 'all'): ").strip()
        
        if wallet_ids.lower() == "all":
            selected = list(self.wallet_states.keys())
        else:
            try:
                selected = [int(x.strip()) for x in wallet_ids.split(",")]
            except ValueError:
                print("❌ Định dạng không hợp lệ!")
                return
        
        print(f"\n🔄 Đang khởi động lại {len(selected)} ví...")
        
        tasks = []
        for wallet_num in selected:
            if wallet_num not in self.wallet_states:
                print(f"❌ Wallet {wallet_num} không tồn tại")
                continue
            
            # Dừng ví cũ nếu đang chạy
            state = self.wallet_states[wallet_num]
            if state["context"]:
                try:
                    await state["context"].close()
                except:
                    pass
            
            # Khởi động lại
            task = self.process_wallet(wallet_num, self.playwright_instance)
            tasks.append((wallet_num, task))
        
        # Chạy song song
        for wallet_num, task in tasks:
            try:
                context = await task
                if context:
                    self.wallet_states[wallet_num] = {
                        "status": "running",
                        "context": context,
                        "start_time": datetime.now(),
                        "error": None
                    }
                    print(f"✅ Đã khởi động lại Wallet {wallet_num}")
                else:
                    self.wallet_states[wallet_num]["status"] = "failed"
                    print(f"❌ Khởi động lại Wallet {wallet_num} thất bại")
            except Exception as e:
                self.wallet_states[wallet_num]["status"] = "failed"
                self.wallet_states[wallet_num]["error"] = str(e)
                print(f"❌ Lỗi khi khởi động lại Wallet {wallet_num}: {e}")
        
        # Lưu trạng thái
        self.save_wallet_states()
    
    async def stop_all_wallets(self):
        """Dừng tất cả ví"""
        for wallet_num, state in self.wallet_states.items():
            if state["context"]:
                try:
                    await state["context"].close()
                    print(f"✅ Đã đóng Wallet {wallet_num}")
                except Exception as e:
                    print(f"⚠️ Lỗi khi đóng Wallet {wallet_num}: {e}")
    
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
            
            # Return context để giữ browser mở
            return context
            
        except Exception as e:
            print(f"❌ Wallet {wallet_num}: Fatal error - {e}")
            import traceback
            traceback.print_exc()
            return None


async def main():
    print("="*60)
    print("🤖 LACE WALLET AUTO MINING BOT")
    print("="*60)
    
    # Nhập số lượng wallets và password
    try:
        num_wallets = int(input("\n📊 Số lượng wallets cần tạo: "))
        if num_wallets <= 0:
            print("❌ Số lượng wallet phải lớn hơn 0!")
            return
    except ValueError:
        print("❌ Vui lòng nhập số hợp lệ!")
        return
    
    password = input("🔒 Mật khẩu cho tất cả wallets: ")
    if not password:
        print("❌ Mật khẩu không được để trống!")
        return
    
    print(f"\n🚀 Bắt đầu tạo {num_wallets} ví...")
    print(f"🔒 Mật khẩu: {'*' * len(password)}")
    print("-"*60)
    
    bot = PlaywrightLaceBot(num_wallets=num_wallets, password=password)
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Bot đã dừng bởi người dùng")
    except Exception as e:
        print(f"\n❌ Lỗi nghiêm trọng: {e}")
        import traceback
        traceback.print_exc()
