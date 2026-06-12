"""
fetch_data.py

Запускать ЛОКАЛЬНО (не в GitHub Actions).
Обращается к api.hh.ru, собирает данные по вакансиям,
сохраняет data.json — который затем коммитится в репозиторий.

Запуск:
    python fetch_data.py
    git add data.json
    git commit -m "chore: update vacancy data"
    git push
"""

import json
import time
from datetime import datetime, timezone

import requests

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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://hh.uz/",
}


# ---------------------------------------------------------------------------
# Получаем area_id для каждого города
# ---------------------------------------------------------------------------

def get_area_ids():
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
            f"Не найден 'Узбекистан'. Страны: {[c['name'] for c in countries]}"
        )

    walk(uzbekistan)
    return area_map


# ---------------------------------------------------------------------------
# Считаем количество вакансий по area_id
# ---------------------------------------------------------------------------

def get_vacancy_count(area_id):
    url = "https://api.hh.ru/vacancies"
    params = {"area": area_id, "per_page": 1}
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("found", 0)


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------

def main():
    print("[*] Получаю дерево регионов...")
    area_map = get_area_ids()
    print("[+] Успешно")

    results = {}

    for city, (lat, lon) in CITIES.items():
        area_id = area_map.get(city)
        if area_id is None:
            print(f"[!] area_id не найден для: {city}")
            continue

        try:
            count = get_vacancy_count(area_id)
            results[city] = {
                "lat": lat,
                "lon": lon,
                "area_id": area_id,
                "vacancies": count,
            }
            print(f"[+] {city}: {count} вакансий")
        except requests.HTTPError as e:
            print(f"[!] Ошибка для {city}: {e}")

        time.sleep(0.7)

    if not results:
        print("[!] Нет данных — data.json не обновлён")
        return

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "cities": results,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n[+] data.json сохранён. Теперь выполни:")
    print("    git add data.json")
    print("    git commit -m \"chore: update vacancy data $(date +%Y-%m-%d)\"")
    print("    git push")


if __name__ == "__main__":
    main()
