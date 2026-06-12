"""
build_map.py

    python build_map.py
"""

import json
import time
from datetime import datetime, timezone

import requests
import folium

# ---------------------------------------------------------------------------
# Настройки
# ---------------------------------------------------------------------------

# Города на карте: название (как в API hh.ru) -> координаты (lat, lon)
CITIES = {
    "Ташкент":   (41.2995, 69.2401),
    "Самарканд": (39.6270, 66.9750),
    "Бухара":    (39.7747, 64.4286),
    "Андижан":   (40.7821, 72.3442),
    "Наманган":  (41.0011, 71.6726),
    "Фергана":   (40.3864, 71.7843),
    "Нукус":     (42.4531, 59.6103),
    "Карши":     (38.8606, 65.7891),
}

# hh.ru просит указывать User-Agent с контактом для публичного API
HEADERS = {
    "User-Agent": "uzbekistan-labor-map/1.0 (contact: your-email@example.com)"
}


# ---------------------------------------------------------------------------
# Шаг 1. Получаем area_id для каждого города из дерева регионов hh.ru
# ---------------------------------------------------------------------------

def get_area_ids():
    """Возвращает словарь {название города: area_id} для Узбекистана.

    hh.ru отдаёт полное дерево регионов через /areas (без параметров) —
    это список "стран" верхнего уровня, каждая со своим поддеревом регионов
    и городов. Здесь мы находим узел "Узбекистан" и обходим его поддерево.
    """
    url = "https://api.hh.ru/areas"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    countries = resp.json()

    area_map = {}

    def walk(node):
        area_map[node["name"]] = node["id"]
        for child in node.get("areas", []):
            walk(child)

    uzbekistan = None
    for country in countries:
        if country["name"] in ("Узбекистан", "Uzbekistan"):
            uzbekistan = country
            break

    if uzbekistan is None:
        raise RuntimeError(
            "Не удалось найти 'Узбекистан' в дереве регионов hh.ru. "
            f"Доступные страны: {[c['name'] for c in countries]}"
        )

    walk(uzbekistan)
    return area_map


# ---------------------------------------------------------------------------
# Шаг 2. Считаем количество открытых вакансий по area_id
# ---------------------------------------------------------------------------

def get_vacancy_count(area_id):
    url = "https://api.hh.ru/vacancies"
    params = {"area": area_id, "per_page": 1}
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("found", 0)


# ---------------------------------------------------------------------------
# Шаг 3. Собираем данные по всем городам
# ---------------------------------------------------------------------------

def collect_data():
    area_map = get_area_ids()
    results = {}

    for city, (lat, lon) in CITIES.items():
        area_id = area_map.get(city)
        if area_id is None:
            print(f"[!] Не найден area_id для города: {city} — пропускаю")
            continue

        count = get_vacancy_count(area_id)
        results[city] = {
            "lat": lat,
            "lon": lon,
            "area_id": area_id,
            "vacancies": count,
        }
        print(f"{city}: {count} вакансий (area_id={area_id})")

        # небольшая пауза, чтобы не долбить API слишком часто
        time.sleep(0.5)

    return results


# ---------------------------------------------------------------------------
# Шаг 4. Строим интерактивную карту folium
# ---------------------------------------------------------------------------

def build_map(data):
    m = folium.Map(location=[41.3, 64.5], zoom_start=6, tiles="cartodbpositron")

    counts = [d["vacancies"] for d in data.values()] or [1]
    max_count = max(counts)
    total = sum(counts)

    for city, d in data.items():
        count = d["vacancies"]
        share = (count / total * 100) if total else 0

        # радиус круга масштабируем относительно максимума
        radius = 8 + 30 * (count / max_count) if max_count else 8

        popup_html = (
            f"<b>{city}</b><br>"
            f"Открытых вакансий: <b>{count}</b><br>"
            f"Доля от всех вакансий по стране: {share:.1f}%"
        )

        folium.CircleMarker(
            location=[d["lat"], d["lon"]],
            radius=radius,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{city}: {count}",
            color="#1f4e8c",
            weight=1,
            fill=True,
            fill_color="#3186cc",
            fill_opacity=0.6,
        ).add_to(m)

        folium.map.Marker(
            [d["lat"], d["lon"]],
            icon=folium.DivIcon(
                html=(
                    '<div style="font-size:11px; font-weight:bold; '
                    f'color:#1f4e8c;">{city}</div>'
                )
            ),
        ).add_to(m)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title_html = f"""
    <div style="position: fixed; top: 10px; left: 50px; z-index: 9999;
                background: white; padding: 10px 15px; border-radius: 8px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3); font-family: sans-serif;
                max-width: 320px;">
        <div style="font-size:15px; font-weight:bold;">
            Спрос на рынке труда: открытые вакансии по городам Узбекистана
        </div>
        <div style="font-size:12px; color:#555; margin-top:4px;">
            Источник: hh.uz (api.hh.ru) · Обновлено: {timestamp}
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    return m


# ---------------------------------------------------------------------------
# Главная точка входа
# ---------------------------------------------------------------------------

def main():
    data = collect_data()

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "cities": data,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    m = build_map(data)
    m.save("index.html")
    print("Карта сохранена в index.html")


if __name__ == "__main__":
    main()
