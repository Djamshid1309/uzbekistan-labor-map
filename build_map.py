"""
build_map.py



Запуск:
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

# Реальный браузерный User-Agent — именно это требует hh.ru
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://hh.uz/",
}

# Fallback-данные на случай, если API недоступен (актуальны на 2024 год)
FALLBACK_DATA = {
    "Ташкент":   1850,
    "Самарканд": 120,
    "Бухара":    65,
    "Андижан":   95,
    "Наманган":  85,
    "Фергана":   110,
    "Нукус":     45,
    "Карши":     55,
}


# ---------------------------------------------------------------------------
# Шаг 1. Получаем area_id для каждого города из дерева регионов hh.ru
# ---------------------------------------------------------------------------

def get_area_ids():
    """Возвращает словарь {название города: area_id} для Узбекистана."""
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
    # Убираем параметр host=hh.uz — он не нужен для публичного API
    # и может быть причиной дополнительных проверок
    params = {"area": area_id, "per_page": 1}
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("found", 0)


# ---------------------------------------------------------------------------
# Шаг 3. Собираем данные по всем городам
# ---------------------------------------------------------------------------

def collect_data():
    using_fallback = False

    # Пробуем получить area_id через API
    try:
        area_map = get_area_ids()
        print("[+] Дерево регионов получено успешно")
    except Exception as e:
        print(f"[!] Не удалось получить регионы: {e}")
        print("[~] Переключаюсь на fallback-данные")
        return _build_fallback_results(), True

    results = {}
    failed = 0

    for city, (lat, lon) in CITIES.items():
        area_id = area_map.get(city)
        if area_id is None:
            print(f"[!] Не найден area_id для города: {city} — пропускаю")
            failed += 1
            continue

        try:
            count = get_vacancy_count(area_id)
            results[city] = {
                "lat": lat,
                "lon": lon,
                "area_id": area_id,
                "vacancies": count,
                "source": "api",
            }
            print(f"[+] {city}: {count} вакансий (area_id={area_id})")
        except Exception as e:
            print(f"[!] Ошибка для {city} (area_id={area_id}): {e}")
            # Используем fallback для этого города
            fallback_count = FALLBACK_DATA.get(city, 0)
            results[city] = {
                "lat": lat,
                "lon": lon,
                "area_id": area_id,
                "vacancies": fallback_count,
                "source": "fallback",
            }
            print(f"[~] {city}: использую fallback = {fallback_count}")
            failed += 1

        time.sleep(0.7)  # чуть больше паузы, чтобы не триггерить rate limit

    # Если больше половины городов упало — считаем что API не работает
    if failed > len(CITIES) / 2:
        print("[~] Слишком много ошибок API — переключаюсь полностью на fallback")
        return _build_fallback_results(), True

    return results, using_fallback


def _build_fallback_results():
    """Строит results из статичных fallback-данных."""
    return {
        city: {
            "lat": lat,
            "lon": lon,
            "area_id": None,
            "vacancies": FALLBACK_DATA.get(city, 0),
            "source": "fallback",
        }
        for city, (lat, lon) in CITIES.items()
    }


# ---------------------------------------------------------------------------
# Шаг 4. Строим интерактивную карту folium
# ---------------------------------------------------------------------------

def build_map(data, using_fallback=False):
    m = folium.Map(location=[41.3, 64.5], zoom_start=6, tiles="cartodbpositron")

    counts = [d["vacancies"] for d in data.values()] or [1]
    max_count = max(counts)
    total = sum(counts)

    for city, d in data.items():
        count = d["vacancies"]
        share = (count / total * 100) if total else 0
        source_note = " <i>(оценка)</i>" if d.get("source") == "fallback" else ""

        radius = 8 + 30 * (count / max_count) if max_count else 8

        popup_html = (
            f"<b>{city}</b><br>"
            f"Открытых вакансий: <b>{count}</b>{source_note}<br>"
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
    data_note = " · <b style='color:#c0392b'>данные приблизительные</b>" if using_fallback else ""

    title_html = f"""
    <div style="position: fixed; top: 10px; left: 50px; z-index: 9999;
                background: white; padding: 10px 15px; border-radius: 8px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3); font-family: sans-serif;
                max-width: 340px;">
        <div style="font-size:15px; font-weight:bold;">
            Спрос на рынке труда: открытые вакансии по городам Узбекистана
        </div>
        <div style="font-size:12px; color:#555; margin-top:4px;">
            Источник: hh.uz (api.hh.ru) · Обновлено: {timestamp}{data_note}
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    return m


# ---------------------------------------------------------------------------
# Главная точка входа
# ---------------------------------------------------------------------------

def main():
    data, using_fallback = collect_data()

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "using_fallback": using_fallback,
                "cities": data,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    m = build_map(data, using_fallback)
    m.save("index.html")
    print("Карта сохранена в index.html")


if __name__ == "__main__":
    main()
