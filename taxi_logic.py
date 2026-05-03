# taxi_logic.py - Hoàn chỉnh (đã bao gồm get_address_from_coords)
import requests
import polyline
import math
import random
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from geopy.distance import geodesic

BASE_FARE = 10000
RATE_PER_KM = 12000
FIRST_KM = 0.5
WEATHER_FACTOR = {"nang": 1.0, "mua": 1.3, "bao": 1.8}
PEAK_FACTOR = 1.5

geolocator = Nominatim(user_agent="taxi_app_mobile")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def get_coordinates(address):
    loc = geocode(address)
    if loc:
        return (loc.latitude, loc.longitude)
    raise ValueError(f"Không tìm thấy địa chỉ: {address}")

def get_address_from_coords(lat, lon):
    """Đảo ngược: từ tọa độ (lat, lon) -> địa chỉ gần nhất"""
    try:
        loc = geolocator.reverse((lat, lon))
        return loc.address if loc else f"{lat:.4f}, {lon:.4f}"
    except:
        return f"{lat:.4f}, {lon:.4f}"

def get_route_and_distance(coord1, coord2):
    url = f"http://router.project-osrm.org/route/v1/driving/{coord1[1]},{coord1[0]};{coord2[1]},{coord2[0]}?overview=full&geometries=polyline"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data['code'] == 'Ok':
            route = data['routes'][0]
            dist_km = route['distance'] / 1000.0
            points = polyline.decode(route['geometry'])
            return dist_km, points
    except:
        pass
    # Fallback Haversine
    R = 6371
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    dist_km = R * c
    return dist_km, None

def calculate_fare(distance_km, weather, peak):
    if distance_km <= FIRST_KM:
        fare = BASE_FARE
    else:
        fare = BASE_FARE + (distance_km - FIRST_KM) * RATE_PER_KM
    fare *= WEATHER_FACTOR.get(weather, 1.0)
    if peak:
        fare *= PEAK_FACTOR
    return int(round(fare / 100) * 100)

def generate_nearby_cars(center_coord, radius_km=2.0, num_cars=8):
    lat0, lon0 = center_coord
    cars = []
    for i in range(num_cars):
        r = radius_km * math.sqrt(random.random())
        theta = random.uniform(0, 2 * math.pi)
        dlat = (r / 111.0) * math.cos(theta)
        dlon = (r / (111.0 * math.cos(math.radians(lat0)))) * math.sin(theta)
        car_lat = lat0 + dlat
        car_lon = lon0 + dlon
        dist_to_pickup = geodesic((car_lat, car_lon), (lat0, lon0)).km
        cars.append({
            'id': f"XE{1000 + i}",
            'lat': car_lat,
            'lon': car_lon,
            'distance_km': round(dist_to_pickup, 2)
        })
    cars.sort(key=lambda x: x['distance_km'])
    return cars

def get_nearest_car(pickup_coord, cars_list):
    return cars_list[0] if cars_list else None

PAYMENT_METHODS = {"cash": "Tiền mặt", "momo": "Ví Momo", "zalopay": "Ví ZaloPay"}

def process_payment(method, amount_vnd):
    if method == "cash":
        return True, f"✅ Thanh toán {amount_vnd:,} VNĐ bằng tiền mặt khi kết thúc chuyến."
    elif method == "momo":
        return True, f"✅ Đã trừ {amount_vnd:,} VNĐ từ ví Momo (giả lập). Mã GD: MOMO{random.randint(100000,999999)}"
    elif method == "zalopay":
        return True, f"✅ Đã trừ {amount_vnd:,} VNĐ từ ví ZaloPay (giả lập). Mã GD: ZALO{random.randint(100000,999999)}"
    else:
        return False, "Phương thức thanh toán không hợp lệ."