import flet as ft
import httpx
import os
import inspect

# Flet 0.84 keeps ft.icons module but constants moved to ft.Icons.
ft.icons = ft.Icons
ft.colors = ft.Colors
ft.ElevatedButton = ft.Button
ft.border.all = ft.Border.all

# Compatibility: newer Flet uses leading_icon for Dropdown.
_dropdown_init_params = inspect.signature(ft.Dropdown.__init__).parameters
if "prefix_icon" not in _dropdown_init_params:
    _original_dropdown = ft.Dropdown

    def _dropdown_compat(*args, **kwargs):
        if "prefix_icon" in kwargs and "leading_icon" not in kwargs:
            kwargs["leading_icon"] = kwargs.pop("prefix_icon")
        return _original_dropdown(*args, **kwargs)

    ft.Dropdown = _dropdown_compat

# Flet 0.84 no longer exposes shortcut constants on ft.alignment.
if not hasattr(ft.alignment, "center"):
    ft.alignment.center = ft.Alignment(0, 0)
    ft.alignment.top_left = ft.Alignment(-1, -1)
    ft.alignment.bottom_right = ft.Alignment(1, 1)

API_BASE = "http://172.27.189.98:2500"
CATEGORY_FALLBACK = ["ทั้งหมด", "อิเล็กทรอนิกส์", "เสื้อผ้า", "เฟอร์นิเจอร์", "มือถือ", "อื่นๆ"]


def main(page: ft.Page):
    page.title = "SecondHand Market"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F3F8FF"
    if not page.web:
        page.window_width = 420
        page.window_height = 760

    user_info = {"name": "", "username": "", "role": ""}

    def back_to_login(show_message: bool = False):
        clear_user_info()
        build_login()
        if show_message:
            show_snack("ออกจากระบบแล้ว", is_error=False)

    def clear_user_info():
        user_info["name"] = ""
        user_info["username"] = ""
        user_info["role"] = ""

    def show_snack(text: str, is_error: bool = True):
        snack = ft.SnackBar(
            content=ft.Text(text),
            bgcolor=ft.colors.RED if is_error else ft.colors.GREEN,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def can_sell() -> bool:
        role = (user_info.get("role") or "").strip().lower()
        return role in ["seller", "both", "admin"]

    def close_dialog(dialog: ft.AlertDialog):
        dialog.open = False
        page.update()

    def open_dialog(dialog: ft.AlertDialog):
        if dialog not in page.overlay:
            page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def safe_json(resp: httpx.Response, default):
        try:
            return resp.json()
        except Exception:
            return default

    def error_detail(resp: httpx.Response, fallback: str) -> str:
        data = safe_json(resp, {})
        if isinstance(data, dict):
            detail = data.get("detail")
            if detail:
                return str(detail)
        text = (resp.text or "").strip()
        return text if text else fallback

    def get_product_image_url(product: dict) -> str:
        # Try common image keys from API payload; fallback to deterministic placeholder.
        image_url = (
            product.get("image_url")
            or product.get("image")
            or product.get("cover_image")
            or ""
        )
        if image_url:
            return str(image_url)
        product_id = product.get("id", "default")
        return f"https://picsum.photos/seed/secondhand-{product_id}/800/500"

    def format_rating(value) -> str:
        try:
            return f"{float(value):.1f}/5"
        except Exception:
            return "0.0/5"

    def top_right_logout_button() -> ft.IconButton:
        return ft.IconButton(
            ft.icons.LOGOUT,
            tooltip="ออกจากระบบ",
            on_click=lambda _: page.run_task(do_logout),
        )

    def seller_quick_nav(current: str) -> ft.Container:
        return ft.Container(
            padding=10,
            bgcolor=ft.colors.GREY_100,
            content=ft.Row(
                [
                    ft.OutlinedButton(
                        "Home",
                        icon=ft.icons.HOME,
                        disabled=current == "home",
                        on_click=lambda _: page.run_task(show_home),
                    ),
                    ft.OutlinedButton(
                        "ลงขาย",
                        icon=ft.icons.STORE,
                        disabled=current == "seller",
                        on_click=lambda _: page.run_task(show_seller_inventory),
                    ),
                    ft.OutlinedButton(
                        "ข้อความ",
                        icon=ft.icons.CHAT,
                        disabled=current == "inbox",
                        on_click=lambda _: page.run_task(show_seller_inquiries),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                wrap=True,
            ),
            visible=can_sell(),
        )

    def buyer_quick_nav(current: str) -> ft.Container:
        return ft.Container(
            padding=12,
            bgcolor="white",
            border=ft.border.only(top=ft.BorderSide(1, "#E8F0F8")),
            shadow=ft.BoxShadow(
                blur_radius=8,
                spread_radius=0,
                offset=ft.Offset(0, -2),
                color="#00000008",
            ),
            content=ft.Row(
                [
                    ft.ElevatedButton(
                        "Home",
                        icon=ft.icons.HOME,
                        disabled=current == "home",
                        style=ft.ButtonStyle(
                            bgcolor="#E3F2FD" if current == "home" else "white",
                            color="#1976D2" if current == "home" else "#424242",
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        on_click=lambda _: page.run_task(show_home),
                    ),
                    ft.ElevatedButton(
                        "Logout",
                        icon=ft.icons.LOGOUT,
                        style=ft.ButtonStyle(
                            bgcolor="#FFF3E0",
                            color="#E65100",
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        on_click=lambda _: page.run_task(do_logout),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                wrap=True,
            ),
        )

    async def do_logout():
        username = (user_info.get("username") or "").strip()
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{API_BASE}/logout",
                    json={"username": username},
                    timeout=5.0,
                )
        except Exception:
            pass

        back_to_login(show_message=True)

    async def open_inquiry_dialog(product: dict):
        msg_tf = ft.TextField(
            label="ข้อความถึงผู้ขาย",
            hint_text="เช่น สนใจสินค้าชิ้นนี้ ต่อราคาได้ไหมครับ",
            multiline=True,
            min_lines=3,
            max_lines=5,
        )

        async def submit_inquiry(_=None):
            if not msg_tf.value or not msg_tf.value.strip():
                show_snack("กรุณากรอกข้อความสอบถาม")
                return

            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{API_BASE}/inquiries",
                        json={
                            "product_id": product["id"],
                            "buyer_username": user_info["username"] or user_info["name"],
                            "message": msg_tf.value.strip(),
                        },
                        timeout=8.0,
                    )
                if resp.status_code == 200:
                    close_dialog(dialog)
                    show_snack("ส่งข้อความสอบถามเรียบร้อย", is_error=False)
                else:
                    show_snack(error_detail(resp, "ส่งข้อความไม่สำเร็จ"))
            except Exception as ex:
                show_snack(f"ส่งข้อความไม่สำเร็จ: {ex}")

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("สอบถามผู้ขาย"),
            content=ft.Column([ft.Text(product["product_name"]), msg_tf], tight=True),
            actions=[
                ft.TextButton("ยกเลิก", on_click=lambda _: close_dialog(dialog)),
                ft.ElevatedButton("ส่งข้อความ", on_click=lambda _: page.run_task(submit_inquiry)),
            ],
        )
        open_dialog(dialog)

    async def open_product_detail(product_id: int):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{API_BASE}/products/{product_id}", timeout=8.0)
            if resp.status_code != 200:
                show_snack(error_detail(resp, "ไม่พบรายละเอียดสินค้า"))
                return

            p = safe_json(resp, {})
            if not isinstance(p, dict):
                show_snack("รูปแบบข้อมูลรายละเอียดสินค้าไม่ถูกต้อง")
                return

            name = p.get("product_name") or "ไม่ระบุชื่อสินค้า"
            price = p.get("price") if p.get("price") is not None else 0
            category = p.get("category") or "อื่นๆ"
            condition = p.get("condition_label") or "มือสอง"
            seller = (p.get("seller_username") or "unknown").strip()
            description = p.get("description") or "-"

            seller_profile = {
                "username": seller,
                "full_name": seller,
                "user_role": "Seller",
                "product_count": 0,
                "review_count": 0,
                "average_rating": float(p.get("seller_rating") or 0),
            }
            seller_reviews = []
            seller_products = []

            if seller and seller.lower() != "unknown":
                async with httpx.AsyncClient() as client:
                    profile_resp = await client.get(f"{API_BASE}/sellers/{seller}", timeout=8.0)
                    if profile_resp.status_code == 200:
                        profile_data = safe_json(profile_resp, {})
                        if isinstance(profile_data, dict):
                            seller_profile.update(profile_data)

                    reviews_resp = await client.get(f"{API_BASE}/sellers/{seller}/reviews", timeout=8.0)
                    if reviews_resp.status_code == 200:
                        reviews_data = safe_json(reviews_resp, [])
                        if isinstance(reviews_data, list):
                            seller_reviews = reviews_data

                    products_resp = await client.get(f"{API_BASE}/seller/products/{seller}", timeout=8.0)
                    if products_resp.status_code == 200:
                        products_data = safe_json(products_resp, [])
                        if isinstance(products_data, list):
                            seller_products = [item for item in products_data if item.get("id") != product_id]

            page.controls.clear()
            page.app_bar = ft.AppBar(
                leading=ft.IconButton(
                    ft.icons.ARROW_BACK,
                    tooltip="ย้อนกลับ",
                    on_click=lambda _: page.run_task(show_home),
                ),
                title=ft.Text("โปรไฟล์ผู้ขาย"),
                bgcolor=ft.colors.BLUE_700,
                color="white",
                actions=[top_right_logout_button()],
            )

            detail_view = ft.ListView(expand=True, spacing=14, padding=12)
            current_username = (user_info.get("username") or "").strip()
            can_review_seller = bool(
                seller
                and seller.lower() != "unknown"
                and current_username
                and current_username.lower() != seller.lower()
            )

            review_score_tf = ft.TextField(
                label="คะแนนรีวิว (1-5)",
                value="5",
                disabled=not can_review_seller,
            )
            review_comment_tf = ft.TextField(
                label="รีวิวผู้ขาย",
                hint_text="พิมพ์ความเห็นเกี่ยวกับการซื้อขายกับผู้ขายรายนี้",
                multiline=True,
                min_lines=3,
                max_lines=5,
                disabled=not can_review_seller,
            )

            async def submit_review(_=None):
                if not can_review_seller:
                    show_snack("ไม่สามารถรีวิวผู้ขายรายนี้ได้")
                    return

                try:
                    rating_value = float((review_score_tf.value or "").strip())
                except ValueError:
                    show_snack("กรุณากรอกคะแนนรีวิวให้ถูกต้อง")
                    return

                if rating_value < 1 or rating_value > 5:
                    show_snack("คะแนนรีวิวต้องอยู่ระหว่าง 1 ถึง 5")
                    return

                review_comment = (review_comment_tf.value or "").strip()
                if not review_comment:
                    show_snack("กรุณากรอกรายละเอียดรีวิว")
                    return

                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(
                            f"{API_BASE}/sellers/{seller}/reviews",
                            json={
                                "reviewer_username": current_username,
                                "rating": rating_value,
                                "comment": review_comment,
                            },
                            timeout=8.0,
                        )
                    if resp.status_code in [200, 201]:
                        show_snack("บันทึกรีวิวผู้ขายเรียบร้อย", is_error=False)
                        await open_product_detail(product_id)
                    else:
                        show_snack(error_detail(resp, "บันทึกรายการรีวิวไม่สำเร็จ"))
                except Exception as ex:
                    show_snack(f"บันทึกรายการรีวิวไม่สำเร็จ: {ex}")

            detail_view.controls.append(
                ft.Container(
                    padding=14,
                    border_radius=18,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.top_left,
                        end=ft.alignment.bottom_right,
                        colors=["#EAF4FF", "#E7FBF3"],
                    ),
                    border=ft.border.all(1, "#D8E6F7"),
                    content=ft.Column(
                        [
                            ft.Container(
                                width=float("inf"),
                                height=190,
                                border_radius=16,
                                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                                content=ft.Image(
                                    src=get_product_image_url(p),
                                    fit=ft.BoxFit.COVER,
                                ),
                            ),
                            ft.Text(name, size=22, weight=ft.FontWeight.BOLD, color="#123B66"),
                            ft.Text(f"฿{float(price):,.2f}", size=20, weight=ft.FontWeight.BOLD, color="#0B5ED7"),
                            ft.Text(f"หมวดหมู่: {category}"),
                            ft.Text(f"สภาพสินค้า: {condition}"),
                            ft.Text("รายละเอียด:"),
                            ft.Text(description, selectable=True),
                            ft.Row(
                                [
                                    ft.ElevatedButton(
                                        "สอบถามผู้ขาย",
                                        icon=ft.icons.CHAT,
                                        on_click=lambda _: page.run_task(open_inquiry_dialog, p),
                                    ),
                                    ft.Text("เลื่อนลงเพื่อเขียนรีวิว", color="#5D6C7F"),
                                ],
                                wrap=True,
                            ),
                        ],
                        spacing=8,
                    ),
                )
            )

            detail_view.controls.append(
                ft.Container(
                    padding=14,
                    border_radius=16,
                    bgcolor="white",
                    border=ft.border.all(1, "#E6ECF5"),
                    content=ft.Column(
                        [
                            ft.Text("โปรไฟล์ผู้ขาย", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(f"ชื่อผู้ใช้: {seller_profile.get('username', seller)}"),
                            ft.Text(f"ชื่อแสดงผล: {seller_profile.get('full_name', seller)}"),
                            ft.Text(f"บทบาท: {seller_profile.get('user_role', 'Seller')}"),
                            ft.Text(f"สินค้าที่ลงขาย: {int(seller_profile.get('product_count', 0))} ชิ้น"),
                            ft.Text(f"รีวิวทั้งหมด: {int(seller_profile.get('review_count', 0))} รายการ"),
                            ft.Text(f"คะแนนเฉลี่ย: {format_rating(seller_profile.get('average_rating', 0))}"),
                        ],
                        spacing=6,
                    ),
                )
            )

            detail_view.controls.append(
                ft.Container(
                    padding=14,
                    border_radius=16,
                    bgcolor="white",
                    border=ft.border.all(1, "#E6ECF5"),
                    content=ft.Column(
                        [
                            ft.Text("เขียนรีวิวผู้ขาย", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "รีวิวนี้จะช่วยให้ผู้ซื้อคนอื่นตัดสินใจได้ง่ายขึ้น",
                                size=12,
                                color="#5D6C7F",
                            ),
                            review_score_tf,
                            review_comment_tf,
                            ft.ElevatedButton(
                                "ส่งรีวิว",
                                icon=ft.icons.SEND,
                                on_click=lambda _: page.run_task(submit_review),
                                visible=can_review_seller,
                            ),
                            ft.Text(
                                "บัญชีนี้เป็นผู้ขายรายเดียวกับโปรไฟล์ที่กำลังเปิดอยู่ จึงไม่สามารถรีวิวได้",
                                size=12,
                                color=ft.colors.RED_700,
                                visible=not can_review_seller,
                            ),
                        ],
                        spacing=8,
                    ),
                )
            )

            latest_review_controls = []
            if seller_reviews:
                for review in seller_reviews[:3]:
                    latest_review_controls.append(
                        ft.Card(
                            content=ft.Container(
                                padding=10,
                                content=ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Text(
                                                    f"จาก: {review.get('reviewer_username', 'unknown')}",
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                ft.Text(f"⭐ {format_rating(review.get('rating', 0))}"),
                                            ],
                                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        ),
                                        ft.Text(review.get("comment") or "-"),
                                    ],
                                    spacing=4,
                                ),
                            )
                        )
                    )
            else:
                latest_review_controls.append(ft.Text("ยังไม่มีรีวิวจากผู้ซื้อ"))

            detail_view.controls.append(
                ft.Container(
                    padding=14,
                    border_radius=16,
                    bgcolor="white",
                    border=ft.border.all(1, "#E6ECF5"),
                    content=ft.Column(
                        [
                            ft.Text("รีวิวล่าสุด", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text("แสดงรีวิวล่าสุด 3 รายการ", size=12, color="#6B7280"),
                            ft.Column(latest_review_controls, spacing=8),
                        ],
                        spacing=8,
                    ),
                )
            )

            if seller_products:
                related_controls = []
                for item in seller_products[:5]:
                    related_controls.append(
                        ft.Card(
                            content=ft.Container(
                                padding=10,
                                content=ft.Column(
                                    [
                                        ft.Text(item.get("product_name") or "ไม่ระบุชื่อสินค้า", weight=ft.FontWeight.BOLD),
                                        ft.Text(f"฿{float(item.get('price') or 0):,.2f}"),
                                        ft.Text(f"หมวด: {item.get('category') or 'อื่นๆ'} | สภาพ: {item.get('condition_label') or 'มือสอง'}", size=12),
                                        ft.TextButton(
                                            "ดูรายละเอียด",
                                            on_click=lambda _, pid=item["id"]: page.run_task(open_product_detail, pid),
                                        ),
                                    ],
                                    spacing=4,
                                ),
                            ),
                        )
                    )

                detail_view.controls.append(
                    ft.Container(
                        padding=14,
                        border_radius=16,
                        bgcolor="white",
                        border=ft.border.all(1, "#E6ECF5"),
                        content=ft.Column(
                            [
                                ft.Text("สินค้าอื่นของผู้ขาย", size=18, weight=ft.FontWeight.BOLD),
                                ft.Column(related_controls, spacing=8),
                            ],
                            spacing=8,
                        ),
                    )
                )

            if can_sell():
                page.add(detail_view, seller_quick_nav("home"))
            else:
                page.add(detail_view, buyer_quick_nav("detail"))
            page.update()
        except Exception as ex:
            show_snack(f"โหลดรายละเอียดไม่สำเร็จ: {ex}")

    async def show_seller_inquiries():
        page.controls.clear()
        page.app_bar = ft.AppBar(
            leading=ft.IconButton(
                ft.icons.ARROW_BACK,
                tooltip="ย้อนกลับ",
                on_click=lambda _: page.run_task(show_seller_inventory),
            ),
            title=ft.Text(f"กล่องข้อความผู้ขาย | {user_info['name']}"),
            bgcolor=ft.colors.TEAL_700,
            color="white",
            actions=[
                ft.IconButton(ft.icons.STORE, tooltip="หน้าประกาศ", on_click=lambda _: page.run_task(show_seller_inventory)),
                ft.IconButton(ft.icons.HOME, tooltip="หน้า Home", on_click=lambda _: page.run_task(show_home)),
                top_right_logout_button(),
            ],
        )

        inquiry_list = ft.ListView(expand=True, spacing=10, padding=12)

        async def load_inquiries(_=None):
            inquiry_list.controls.clear()
            seller_key = user_info["username"] or user_info["name"]
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{API_BASE}/seller/inquiries/{seller_key}", timeout=8.0)
                if resp.status_code != 200:
                    show_snack(error_detail(resp, "โหลดข้อความไม่สำเร็จ"))
                    return

                items = safe_json(resp, [])
                if not items:
                    inquiry_list.controls.append(ft.Text("ยังไม่มีข้อความสอบถาม"))
                else:
                    for msg in items:
                        inquiry_list.controls.append(
                            ft.Card(
                                content=ft.Container(
                                    padding=12,
                                    content=ft.Column(
                                        [
                                            ft.Text(f"สินค้า: {msg['product_name']}", weight=ft.FontWeight.BOLD),
                                            ft.Text(f"ผู้ซื้อ: {msg['buyer_username']}", size=12),
                                            ft.Text(msg["message"]),
                                        ],
                                        spacing=6,
                                    ),
                                )
                            )
                        )
                page.update()
            except Exception as ex:
                show_snack(f"โหลดข้อความไม่สำเร็จ: {ex}")

        page.add(
            ft.Container(
                padding=10,
                content=ft.Row(
                    [
                        ft.Text("ข้อความจากผู้ซื้อ", weight=ft.FontWeight.BOLD),
                        ft.IconButton(ft.icons.REFRESH, on_click=lambda _: page.run_task(load_inquiries)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ),
            inquiry_list,
            seller_quick_nav("inbox"),
        )
        await load_inquiries()

    async def show_home():
        page.controls.clear()
        page.app_bar = ft.AppBar(
            leading=ft.IconButton(
                ft.icons.ARROW_BACK,
                tooltip="กลับหน้า Login",
                on_click=lambda _: back_to_login(),
            ),
            title=ft.Text(f"SecondHand | {user_info['name']}"),
            bgcolor=ft.colors.BLUE_800,
            color="white",
            actions=[
                ft.IconButton(
                    ft.icons.STORE,
                    tooltip="จัดการประกาศ",
                    visible=can_sell(),
                    on_click=lambda _: page.run_task(show_seller_inventory),
                ),
                top_right_logout_button(),
            ],
        )

        search_tf = ft.TextField(
            label="ค้นหาสินค้า",
            hint_text="ค้นหาชื่อสินค้า รายละเอียด หรือผู้ขาย",
            prefix_icon=ft.icons.SEARCH,
            expand=True,
        )
        category_dd = ft.Dropdown(
            label="หมวดหมู่",
            value="ทั้งหมด",
            width=150,
            options=[ft.dropdown.Option(c) for c in CATEGORY_FALLBACK],
        )
        product_grid = ft.GridView(
            expand=True,
            runs_count=1,
            spacing=12,
            run_spacing=12,
            child_aspect_ratio=0.88,
            padding=10,
        )

        def apply_grid_layout():
            width = page.width or page.window_width or 390
            if width < 520:
                product_grid.runs_count = 1
                product_grid.child_aspect_ratio = 0.96
            elif width < 960:
                product_grid.runs_count = 2
                product_grid.child_aspect_ratio = 0.9
            else:
                product_grid.runs_count = 3
                product_grid.child_aspect_ratio = 0.86

        def handle_resize(_):
            apply_grid_layout()
            page.update()

        page.on_resize = handle_resize

        async def load_categories():
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{API_BASE}/categories", timeout=8.0)
                if resp.status_code == 200:
                    api_categories = resp.json() if isinstance(resp.json(), list) else []
                    # Filter and add "ทั้งหมด" first
                    merged = ["ทั้งหมด"] + sorted([c.strip() for c in api_categories if c and c.strip()])
                    category_dd.options = [ft.dropdown.Option(c) for c in merged]
                    category_dd.value = "ทั้งหมด"
                    page.update()
                else:
                    # Fallback if API fails
                    category_dd.options = [ft.dropdown.Option(c) for c in CATEGORY_FALLBACK]
                    category_dd.value = "ทั้งหมด"
                    page.update()
            except Exception as ex:
                # On error, use fallback
                category_dd.options = [ft.dropdown.Option(c) for c in CATEGORY_FALLBACK]
                category_dd.value = "ทั้งหมด"
                page.update()

        async def load_products(_=None):
            product_grid.controls.clear()
            params = {}
            if search_tf.value and search_tf.value.strip():
                params["search"] = search_tf.value.strip()
            if category_dd.value and category_dd.value != "ทั้งหมด":
                params["category"] = category_dd.value

            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{API_BASE}/products", params=params, timeout=8.0)
                if resp.status_code != 200:
                    show_snack(error_detail(resp, "โหลดสินค้าไม่สำเร็จ"))
                    return

                items = safe_json(resp, [])
                if not items:
                    product_grid.controls.append(
                        ft.Container(content=ft.Text("ไม่พบสินค้า", size=16), alignment=ft.alignment.center, padding=20)
                    )
                else:
                    for p in items:
                        image_url = get_product_image_url(p)
                        product_grid.controls.append(
                            ft.Card(
                                elevation=3,
                                content=ft.Container(
                                    border_radius=16,
                                    bgcolor="white",
                                    border=ft.border.all(1, "#E4ECF7"),
                                    content=ft.Column(
                                        [
                                            ft.Container(
                                                width=float("inf"),
                                                content=ft.Image(
                                                    src=image_url,
                                                    fit=ft.BoxFit.COVER,
                                                    width=float("inf"),
                                                ),
                                                height=150,
                                                border_radius=ft.border_radius.only(
                                                    top_left=16,
                                                    top_right=16,
                                                ),
                                                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                                            ),
                                            ft.Container(
                                                padding=12,
                                                content=ft.Column(
                                                    [
                                                        ft.Text(p["product_name"], weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                                        ft.Text(f"฿{float(p['price']):,.2f}", color="#0B5ED7", weight=ft.FontWeight.BOLD, size=16),
                                                        ft.Text(f"หมวด: {p['category']}", size=12),
                                                        ft.Text(f"สภาพ: {p['condition_label']}", size=12),
                                                        ft.Text(f"ผู้ขาย: {p['seller_username']}", size=12),
                                                        ft.Text(f"⭐ {float(p['seller_rating']):.1f}/5", size=12),
                                                        ft.ElevatedButton(
                                                            "ดูรายละเอียด",
                                                            icon=ft.icons.VISIBILITY,
                                                            style=ft.ButtonStyle(
                                                                shape=ft.RoundedRectangleBorder(radius=10),
                                                                bgcolor="#1F7AE0",
                                                                color="white",
                                                            ),
                                                            on_click=lambda _, pid=p["id"]: page.run_task(open_product_detail, pid),
                                                        ),
                                                    ],
                                                    spacing=6,
                                                ),
                                            ),
                                        ],
                                        spacing=0,
                                    ),
                                )
                            )
                        )
                page.update()
            except Exception as ex:
                show_snack(f"เชื่อมต่อ Server ไม่ได้: {ex}")

        search_tf.on_change = lambda _: page.run_task(load_products)
        search_tf.on_submit = lambda _: page.run_task(load_products)
        category_dd.on_change = lambda _: page.run_task(load_products)

        page.add(
            ft.Container(
                margin=ft.margin.only(left=10, right=10, top=10),
                padding=12,
                border_radius=14,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                    colors=["#E6F2FF", "#DDF7F1"],
                ),
                border=ft.border.all(1, "#CFE2F7"),
                content=ft.Column(
                    [
                        ft.Text(f"สวัสดี {user_info['name']}", size=20, weight=ft.FontWeight.BOLD, color="#123B66"),
                        ft.Text(f"บทบาท: {user_info['role'] or 'Buyer'}", color="#315B86"),
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    "ไปหน้าประกาศขาย",
                                    icon=ft.icons.STORE,
                                    visible=can_sell(),
                                    on_click=lambda _: page.run_task(show_seller_inventory),
                                ),
                                ft.OutlinedButton(
                                    "ข้อความผู้ขาย",
                                    icon=ft.icons.CHAT,
                                    visible=can_sell(),
                                    on_click=lambda _: page.run_task(show_seller_inquiries),
                                ),
                                ft.ElevatedButton(
                                    "ออกจากระบบ",
                                    icon=ft.icons.LOGOUT,
                                    style=ft.ButtonStyle(
                                        bgcolor="white",
                                        color="#1976D2",
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                    ),
                                    on_click=lambda _: page.run_task(do_logout),
                                ),
                            ],
                            wrap=True,
                            spacing=10,
                        ),
                    ],
                    spacing=8,
                ),
            ),
            ft.Container(
                padding=10,
                content=ft.Column(
                    [
                        search_tf,
                        ft.Row(
                            [
                                category_dd,
                                ft.IconButton(ft.icons.SEARCH, tooltip="ค้นหา", on_click=lambda _: page.run_task(load_products)),
                                ft.IconButton(ft.icons.REFRESH, tooltip="รีเฟรชรายการ", on_click=lambda _: page.run_task(load_products)),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            wrap=True,
                        ),
                    ],
                    spacing=8,
                ),
            ),
            product_grid,
            seller_quick_nav("home"),
        )

        apply_grid_layout()
        await load_categories()
        await load_products()

    async def show_seller_inventory():
        page.controls.clear()
        page.app_bar = ft.AppBar(
            leading=ft.IconButton(
                ft.icons.ARROW_BACK,
                tooltip="ย้อนกลับ",
                on_click=lambda _: page.run_task(show_home),
            ),
            title=ft.Text(f"Seller Center | {user_info['name']}"),
            bgcolor=ft.colors.GREEN_700,
            color="white",
            actions=[
                ft.IconButton(ft.icons.CHAT, tooltip="กล่องข้อความ", on_click=lambda _: page.run_task(show_seller_inquiries)),
                ft.IconButton(ft.icons.HOME, tooltip="กลับหน้า Home", on_click=lambda _: page.run_task(show_home)),
                top_right_logout_button(),
            ],
        )

        inventory_list = ft.ListView(expand=True, spacing=8, padding=10)
        review_count_text = ft.Text("รีวิวทั้งหมด: 0", size=12, color="#4E5D6C")
        average_rating_text = ft.Text("คะแนนเฉลี่ย: 0.0/5", size=12, color="#4E5D6C")
        latest_reviews_col = ft.Column(spacing=8)

        async def load_seller_reviews(_=None):
            seller_key = user_info["username"] or user_info["name"]
            latest_reviews_col.controls.clear()
            try:
                async with httpx.AsyncClient() as client:
                    profile_resp = await client.get(f"{API_BASE}/sellers/{seller_key}", timeout=8.0)
                    reviews_resp = await client.get(f"{API_BASE}/sellers/{seller_key}/reviews", timeout=8.0)

                if profile_resp.status_code == 200:
                    profile_data = safe_json(profile_resp, {})
                    if isinstance(profile_data, dict):
                        review_count_text.value = f"รีวิวทั้งหมด: {int(profile_data.get('review_count', 0))}"
                        average_rating_text.value = f"คะแนนเฉลี่ย: {format_rating(profile_data.get('average_rating', 0))}"

                if reviews_resp.status_code == 200:
                    reviews = safe_json(reviews_resp, [])
                    if reviews:
                        for review in reviews[:3]:
                            latest_reviews_col.controls.append(
                                ft.Card(
                                    content=ft.Container(
                                        padding=10,
                                        content=ft.Column(
                                            [
                                                ft.Row(
                                                    [
                                                        ft.Text(
                                                            f"จาก: {review.get('reviewer_username', 'unknown')}",
                                                            weight=ft.FontWeight.BOLD,
                                                        ),
                                                        ft.Text(f"⭐ {format_rating(review.get('rating', 0))}"),
                                                    ],
                                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                                ),
                                                ft.Text(review.get("comment") or "-"),
                                            ],
                                            spacing=4,
                                        ),
                                    )
                                )
                            )
                    else:
                        latest_reviews_col.controls.append(ft.Text("ยังไม่มีรีวิวจากผู้ซื้อ"))
                else:
                    latest_reviews_col.controls.append(ft.Text("โหลดรีวิวไม่สำเร็จ"))

                page.update()
            except Exception as ex:
                latest_reviews_col.controls.append(ft.Text("โหลดรีวิวไม่สำเร็จ"))
                page.update()

        def open_product_form(existing=None):
            is_edit = existing is not None
            name_tf = ft.TextField(label="ชื่อสินค้า", value=existing["product_name"] if is_edit else "")
            price_tf = ft.TextField(label="ราคา", value=str(existing["price"]) if is_edit else "0")
            category_tf = ft.TextField(label="หมวดหมู่", value=existing["category"] if is_edit else "อื่นๆ")
            condition_tf = ft.TextField(label="สภาพสินค้า", value=existing["condition_label"] if is_edit else "มือสอง")
            rating_tf = ft.TextField(label="คะแนนผู้ขาย (0-5)", value=str(existing["seller_rating"]) if is_edit else "4.5")
            detail_tf = ft.TextField(
                label="รายละเอียด",
                value=existing["description"] if is_edit else "",
                multiline=True,
                min_lines=3,
                max_lines=5,
            )
            image_url_tf = ft.TextField(
                label="URL รูปสินค้า",
                hint_text="https://example.com/image.jpg",
                value=existing.get("image_url", "") if is_edit else "",
            )

            async def save_product(_=None):
                try:
                    payload = {
                        "product_name": (name_tf.value or "").strip(),
                        "price": float(price_tf.value),
                        "description": (detail_tf.value or "").strip(),
                        "condition_label": (condition_tf.value or "").strip() or "มือสอง",
                        "category": (category_tf.value or "").strip() or "อื่นๆ",
                        "seller_username": user_info["username"] or user_info["name"],
                        "seller_rating": float(rating_tf.value),
                        "image_url": (image_url_tf.value or "").strip(),
                    }
                except ValueError:
                    show_snack("รูปแบบราคา/คะแนนไม่ถูกต้อง")
                    return

                if not payload["product_name"]:
                    show_snack("กรุณากรอกชื่อสินค้า")
                    return
                if payload["price"] < 0:
                    show_snack("ราคาต้องมากกว่าหรือเท่ากับ 0")
                    return
                if payload["seller_rating"] < 0 or payload["seller_rating"] > 5:
                    show_snack("คะแนนผู้ขายต้องอยู่ระหว่าง 0 ถึง 5")
                    return

                try:
                    async with httpx.AsyncClient() as client:
                        if is_edit:
                            resp = await client.put(
                                f"{API_BASE}/seller/products/{existing['id']}",
                                json=payload,
                                timeout=8.0,
                            )
                        else:
                            resp = await client.post(
                                f"{API_BASE}/seller/products",
                                json=payload,
                                timeout=8.0,
                            )
                    if resp.status_code in [200, 201]:
                        show_snack("บันทึกประกาศเรียบร้อย", is_error=False)
                        close_dialog(form_dialog)
                        await load_inventory()
                    else:
                        show_snack(error_detail(resp, "บันทึกข้อมูลไม่สำเร็จ"))
                except Exception as ex:
                    show_snack(f"บันทึกข้อมูลไม่สำเร็จ: {ex}")

            form_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("แก้ไขประกาศ" if is_edit else "เพิ่มประกาศใหม่"),
                content=ft.Column(
                    [name_tf, price_tf, category_tf, condition_tf, rating_tf, detail_tf, image_url_tf],
                    tight=True,
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                ),
                actions=[
                    ft.TextButton("ยกเลิก", on_click=lambda _: close_dialog(form_dialog)),
                    ft.ElevatedButton("บันทึก", on_click=lambda _: page.run_task(save_product)),
                ],
            )
            open_dialog(form_dialog)

        async def set_sold_status(product_id: int, sold: bool):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.patch(
                        f"{API_BASE}/seller/products/{product_id}/sold",
                        json={"is_sold": sold},
                        timeout=8.0,
                    )
                if resp.status_code == 200:
                    show_snack("อัปเดตสถานะขายแล้วเรียบร้อย", is_error=False)
                    await load_inventory()
                else:
                    show_snack(error_detail(resp, "อัปเดตสถานะไม่สำเร็จ"))
            except Exception as ex:
                show_snack(f"อัปเดตสถานะไม่สำเร็จ: {ex}")

        async def delete_product(product_id: int):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.delete(f"{API_BASE}/seller/products/{product_id}", timeout=8.0)
                if resp.status_code == 200:
                    show_snack("ลบประกาศเรียบร้อย", is_error=False)
                    await load_inventory()
                else:
                    show_snack(error_detail(resp, "ลบประกาศไม่สำเร็จ"))
            except Exception as ex:
                show_snack(f"ลบประกาศไม่สำเร็จ: {ex}")

        def confirm_delete(product_id: int):
            confirm_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("ยืนยันการลบ"),
                content=ft.Text("ต้องการลบประกาศนี้ใช่หรือไม่"),
                actions=[
                    ft.TextButton("ยกเลิก", on_click=lambda _: close_dialog(confirm_dialog)),
                    ft.ElevatedButton(
                        "ลบ",
                        on_click=lambda _: (
                            close_dialog(confirm_dialog),
                            page.run_task(delete_product, product_id),
                        ),
                    ),
                ],
            )
            open_dialog(confirm_dialog)

        async def load_inventory(_=None):
            inventory_list.controls.clear()
            seller_key = user_info["username"] or user_info["name"]
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{API_BASE}/seller/products/{seller_key}", timeout=8.0)
                if resp.status_code != 200:
                    show_snack(error_detail(resp, "โหลดรายการประกาศไม่สำเร็จ"))
                    return

                products = safe_json(resp, [])
                if not products:
                    inventory_list.controls.append(ft.Text("ยังไม่มีประกาศขาย"))
                else:
                    for p in products:
                        sold = bool(p.get("is_sold", 0))
                        inventory_list.controls.append(
                            ft.Card(
                                content=ft.Container(
                                    padding=12,
                                    content=ft.Column(
                                        [
                                            ft.Row(
                                                [
                                                    ft.Text(p["product_name"], weight=ft.FontWeight.BOLD, expand=True),
                                                    ft.Text(
                                                        "ขายแล้ว" if sold else "พร้อมขาย",
                                                        color=ft.colors.RED_400 if sold else ft.colors.GREEN_700,
                                                    ),
                                                ]
                                            ),
                                            ft.Text(f"ราคา: ฿{float(p['price']):,.2f}"),
                                            ft.Text(f"หมวด: {p['category']} | สภาพ: {p['condition_label']}", size=12),
                                            ft.Row(
                                                [
                                                    ft.OutlinedButton("แก้ไข", on_click=lambda _, item=p: open_product_form(item)),
                                                    ft.OutlinedButton(
                                                        "ขายแล้ว" if not sold else "เปิดขายใหม่",
                                                        on_click=lambda _, pid=p["id"], next_state=not sold: page.run_task(set_sold_status, pid, next_state),
                                                    ),
                                                    ft.OutlinedButton("ลบ", on_click=lambda _, pid=p["id"]: confirm_delete(pid)),
                                                ],
                                                wrap=True,
                                            ),
                                        ],
                                        spacing=6,
                                    ),
                                )
                            )
                        )
                page.update()
            except Exception as ex:
                show_snack(f"โหลดรายการประกาศไม่สำเร็จ: {ex}")

        async def refresh_seller_dashboard(_=None):
            await load_inventory()
            await load_seller_reviews()

        page.add(
            ft.Container(
                padding=10,
                content=ft.Row(
                    [
                        ft.ElevatedButton("+ เพิ่มประกาศใหม่", on_click=lambda _: open_product_form()),
                        ft.IconButton(ft.icons.REFRESH, on_click=lambda _: page.run_task(refresh_seller_dashboard)),
                    ]
                ),
            ),
            ft.Container(
                margin=ft.margin.only(left=10, right=10, top=4, bottom=6),
                padding=12,
                border_radius=14,
                bgcolor="white",
                border=ft.border.all(1, "#E6ECF5"),
                content=ft.Column(
                    [
                        ft.Text("รีวิวล่าสุด", size=16, weight=ft.FontWeight.BOLD),
                        ft.Text("แสดงรีวิวล่าสุด 3 รายการจากผู้ซื้อ", size=12, color="#6B7280"),
                        ft.Row([review_count_text, average_rating_text], wrap=True, spacing=12),
                        latest_reviews_col,
                    ],
                    spacing=8,
                ),
            ),
            inventory_list,
            seller_quick_nav("seller"),
        )
        await refresh_seller_dashboard()

    def build_login():
        page.controls.clear()
        page.app_bar = None

        user_tf = ft.TextField(label="Username", value="root", prefix_icon=ft.icons.PERSON)
        pass_tf = ft.TextField(label="Password", value="P@ssw0rd", password=True, prefix_icon=ft.icons.LOCK)

        async def open_register_dialog(_=None):
            reg_username_tf = ft.TextField(label="Username", prefix_icon=ft.icons.PERSON)
            reg_fullname_tf = ft.TextField(label="ชื่อ-นามสกุล", prefix_icon=ft.icons.BADGE)
            reg_phone_tf = ft.TextField(label="เบอร์โทร", prefix_icon=ft.icons.PHONE)
            reg_password_tf = ft.TextField(label="Password", password=True, prefix_icon=ft.icons.LOCK)
            reg_role_dd = ft.Dropdown(
                label="สมัครเป็น",
                value="buyer",
                options=[
                    ft.dropdown.Option("buyer", "Buyer"),
                    ft.dropdown.Option("seller", "Seller"),
                ],
            )

            async def submit_register(_=None):
                username = (reg_username_tf.value or "").strip()
                full_name = (reg_fullname_tf.value or "").strip()
                phone = (reg_phone_tf.value or "").strip()
                password = (reg_password_tf.value or "").strip()
                role = (reg_role_dd.value or "buyer").strip().lower()

                if not username or not full_name or not password:
                    show_snack("กรุณากรอก Username, ชื่อ และ Password")
                    return

                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(
                            f"{API_BASE}/register",
                            json={
                                "username": username,
                                "password": password,
                                "full_name": full_name,
                                "phone": phone,
                                "user_role": role,
                            },
                            timeout=8.0,
                        )

                    if resp.status_code in [200, 201]:
                        close_dialog(register_dialog)
                        user_tf.value = username
                        pass_tf.value = password
                        page.update()
                        show_snack("สมัครสมาชิกเรียบร้อย กรุณาเข้าสู่ระบบ", is_error=False)
                    else:
                        show_snack(error_detail(resp, "สมัครสมาชิกไม่สำเร็จ"))
                except Exception as ex:
                    show_snack(f"เชื่อมต่อ Server ไม่ได้: {ex}")

            register_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("สมัครสมาชิก", weight=ft.FontWeight.BOLD),
                content=ft.Column(
                    [
                        reg_username_tf,
                        reg_fullname_tf,
                        reg_phone_tf,
                        reg_password_tf,
                        ft.Row(
                            [
                                ft.Icon(ft.icons.ACCOUNT_CIRCLE, color="#1976D2"),
                                reg_role_dd,
                            ],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                    ],
                    tight=True,
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
                actions=[
                    ft.TextButton("ยกเลิก", on_click=lambda _: close_dialog(register_dialog)),
                    ft.ElevatedButton("สมัครสมาชิก", on_click=lambda _: page.run_task(submit_register)),
                ],
            )
            open_dialog(register_dialog)

        async def login_click(_=None):
            if not user_tf.value or not pass_tf.value:
                show_snack("กรุณากรอก Username และ Password")
                return

            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{API_BASE}/login",
                        json={"username": user_tf.value, "password": pass_tf.value},
                        timeout=5.0,
                    )

                if resp.status_code == 200:
                    data = safe_json(resp, {})
                    user_info["username"] = (data.get("username") or user_tf.value or "").strip()
                    user_info["name"] = (data.get("full_name") or user_info["username"]).strip()
                    user_info["role"] = (data.get("role") or "Buyer").strip()
                    show_snack(f"เข้าสู่ระบบสำเร็จ ({user_info['role']})", is_error=False)
                    await show_home()
                else:
                    show_snack(error_detail(resp, "Login Failed"))
            except Exception as ex:
                show_snack(f"เชื่อมต่อ Server ไม่ได้: {ex}")

        page.add(
            ft.Container(
                width=360,
                padding=24,
                border_radius=24,
                bgcolor="white",
                shadow=ft.BoxShadow(
                    blur_radius=24,
                    spread_radius=0,
                    offset=ft.Offset(0, 8),
                    color="#00000018",
                ),
                content=ft.Column(
                    [
                        ft.Container(
                            padding=14,
                            border_radius=20,
                            bgcolor="#E3F2FD",
                            content=ft.Icon(ft.icons.STOREFRONT_ROUNDED, size=64, color="#1976D2"),
                        ),
                        ft.Text("SecondHand Shop", size=28, weight=ft.FontWeight.BOLD, color="#1F2937"),
                        ft.Text("เข้าสู่ระบบหรือสมัครสมาชิกเพื่อเริ่มใช้งาน", size=12, color="#6B7280", text_align=ft.TextAlign.CENTER),
                        user_tf,
                        pass_tf,
                        ft.ElevatedButton(
                            "เข้าสู่ระบบ",
                            on_click=lambda _: page.run_task(login_click),
                            width=float("inf"),
                            style=ft.ButtonStyle(
                                bgcolor="#1976D2",
                                color="white",
                                shape=ft.RoundedRectangleBorder(radius=12),
                            ),
                        ),
                        ft.OutlinedButton(
                            "สมัครสมาชิก",
                            on_click=lambda _: page.run_task(open_register_dialog),
                            width=float("inf"),
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12),
                            ),
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                ),
                alignment=ft.alignment.center,
                expand=True,
                margin=20,
            )
        )
        page.update()

    build_login()


ft.run(main,
    view=ft.AppView.WEB_BROWSER,
    host=os.getenv("FLET_HOST", "192.168.1.21"),
    port=int(os.getenv("FLET_PORT", "8550")),
)


