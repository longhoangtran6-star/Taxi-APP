import flet as ft
from taxi_logic import (
    get_coordinates, get_address_from_coords, get_route_and_distance, calculate_fare,
    generate_nearby_cars, get_nearest_car, process_payment, PAYMENT_METHODS
)
import folium
import tempfile
import webbrowser

def main(page: ft.Page):
    page.title = "Taxi App - Đặt Xe Công Nghệ"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    # Dùng user_data để lưu trạng thái (thay thế session)
    page.user_data = {}

    # Biến trạng thái
    current_location_coord = None
    selected_car = None
    route_points = None
    distance_km = 0.0
    fare_amount = 0

    # ------- Widgets -------
    get_location_btn = ft.ElevatedButton("📍 Lấy vị trí hiện tại", icon=ft.Icons.MY_LOCATION)
    current_location_text = ft.Text("Chưa xác định", italic=True)

    pickup_input = ft.TextField(label="Điểm đón", hint_text="Hoặc nhập địa chỉ khác", width=350)
    dropoff_input = ft.TextField(label="Điểm đến", hint_text="Nhập địa chỉ", width=350)

    weather_dropdown = ft.Dropdown(
        label="Thời tiết",
        options=[ft.dropdown.Option("nắng"), ft.dropdown.Option("mưa"), ft.dropdown.Option("bão")],
        value="nắng",
        width=150
    )
    peak_switch = ft.Switch(label="Giờ cao điểm", value=False)

    car_info_text = ft.Text("", size=14, italic=True)

    payment_dropdown = ft.Dropdown(
        label="Phương thức thanh toán",
        options=[
            ft.dropdown.Option("cash", "Tiền mặt"),
            ft.dropdown.Option("momo", "Ví Momo"),
            ft.dropdown.Option("zalopay", "Ví ZaloPay"),
        ],
        value="cash",
        width=200
    )

    book_btn = ft.ElevatedButton("🚖 ĐẶT XE", icon=ft.Icons.TAXI_ALERT, bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE)
    map_btn = ft.ElevatedButton("🗺 Xem lộ trình", icon=ft.Icons.MAP, disabled=True)
    payment_btn = ft.ElevatedButton("💳 Thanh toán", icon=ft.Icons.PAYMENT)

    result_text = ft.Text("", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN)
    detail_text = ft.Text("", size=14, selectable=True)

    # ------- Hàm xử lý -------
    def get_current_location(e):
        try:
            loc = page.get_geolocation()
            if loc:
                lat, lon = loc['latitude'], loc['longitude']
                nonlocal current_location_coord
                current_location_coord = (lat, lon)
                addr = get_address_from_coords(lat, lon)
                pickup_input.value = addr
                current_location_text.value = f"✅ Đã lấy: {addr[:50]}..."
                page.update()
                return
        except:
            pass
        page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("Không thể lấy vị trí tự động"),
                content=ft.Text("Vui lòng nhập địa chỉ đón thủ công."),
                actions=[ft.TextButton("OK", on_click=lambda d: page.close_dialog())]
            )
        )

    def find_nearest_car(pickup_coord):
        cars = generate_nearby_cars(pickup_coord, radius_km=2.0, num_cars=8)
        nearest = get_nearest_car(pickup_coord, cars)
        if nearest:
            car_info_text.value = f"🚗 Xe gần nhất: {nearest['id']} cách {nearest['distance_km']} km"
        else:
            car_info_text.value = "⚠️ Không tìm thấy xe nào gần bạn."
        page.update()
        return nearest

    def book_ride(e):
        nonlocal distance_km, route_points, fare_amount, selected_car
        result_text.value = ""
        detail_text.value = ""
        map_btn.disabled = True
        page.update()

        pickup_addr = pickup_input.value.strip()
        dropoff_addr = dropoff_input.value.strip()
        if not pickup_addr or not dropoff_addr:
            result_text.value = "❌ Vui lòng nhập đầy đủ điểm đón và điểm đến."
            page.update()
            return

        try:
            pickup_coord = get_coordinates(pickup_addr)
            dropoff_coord = get_coordinates(dropoff_addr)
            selected_car = find_nearest_car(pickup_coord)

            distance_km, route_points = get_route_and_distance(pickup_coord, dropoff_coord)
            weather = weather_dropdown.value
            peak = peak_switch.value
            fare_amount = calculate_fare(distance_km, weather, peak)

            result_text.value = f"💰 {fare_amount:,} VNĐ"
            detail_text.value = f"📏 {distance_km:.2f} km · {weather.upper()} · {'Cao điểm' if peak else 'Bình thường'}\n🚕 Xe: {selected_car['id'] if selected_car else 'Sẽ tìm xe sau'}"
            map_btn.disabled = False

            # Lưu vào user_data để dùng cho hiển thị bản đồ
            page.user_data['pickup_coord'] = pickup_coord
            page.user_data['dropoff_coord'] = dropoff_coord
            page.user_data['route_points'] = route_points
            page.update()
        except Exception as ex:
            result_text.value = f"❌ Lỗi: {ex}"
            page.update()

    def show_map(e):
        pickup_coord = page.user_data.get('pickup_coord')
        dropoff_coord = page.user_data.get('dropoff_coord')
        route_pts = page.user_data.get('route_points')
        if not pickup_coord:
            page.show_dialog(ft.AlertDialog(title=ft.Text("Lỗi"), content=ft.Text("Chưa có thông tin chuyến đi. Hãy đặt xe trước.")))
            return
        m = folium.Map(location=pickup_coord, zoom_start=14)
        folium.Marker(pickup_coord, popup="Đón", icon=folium.Icon(color='green')).add_to(m)
        folium.Marker(dropoff_coord, popup="Đến", icon=folium.Icon(color='red')).add_to(m)
        if route_pts and len(route_pts) > 1:
            folium.PolyLine(route_pts, color="#1E90FF", weight=5, opacity=0.8).add_to(m)
        else:
            folium.PolyLine([pickup_coord, dropoff_coord], color="gray", weight=3, dash_array='5').add_to(m)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp:
            m.save(tmp.name)
            webbrowser.open(tmp.name)

    def process_payment_click(e):
        if fare_amount == 0:
            page.show_dialog(ft.AlertDialog(title=ft.Text("Chưa có chuyến"), content=ft.Text("Hãy đặt xe trước.")))
            return
        method = payment_dropdown.value
        success, msg = process_payment(method, fare_amount)
        if success:
            page.show_dialog(ft.AlertDialog(title=ft.Text("Thanh toán"), content=ft.Text(msg), actions=[ft.TextButton("OK", on_click=lambda d: page.close_dialog())]))
        else:
            page.show_dialog(ft.AlertDialog(title=ft.Text("Lỗi"), content=ft.Text(msg), actions=[ft.TextButton("OK", on_click=lambda d: page.close_dialog())]))

    # Gán sự kiện
    get_location_btn.on_click = get_current_location
    book_btn.on_click = book_ride
    map_btn.on_click = show_map
    payment_btn.on_click = process_payment_click

    # Layout
    page.add(
        ft.Column(
            [
                ft.Text("🚖 ỨNG DỤNG ĐẶT XE CÔNG NGHỆ", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                get_location_btn,
                current_location_text,
                pickup_input,
                dropoff_input,
                ft.Row([weather_dropdown, peak_switch], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                car_info_text,
                ft.Row([book_btn, map_btn, payment_btn], alignment=ft.MainAxisAlignment.CENTER),
                payment_dropdown,
                ft.Divider(),
                result_text,
                detail_text,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15
        )
    )
    page.update()

ft.app(target=main)