# ============================================================
# TEST: endpoint de Dokan para listar productos por tienda
# ============================================================

import json

import httpx


# Probar con una tienda conocida (Farmacia Amanda = 528)
STORE_ID = 528
URL = f"https://macketi.com/wp-json/dokan/v1/stores/{STORE_ID}/products"


def main() -> None:
    print("=" * 60)
    print(f"TEST: {URL}")
    print("=" * 60)
    print()

    try:
        response = httpx.get(URL, params={"per_page": 5}, timeout=30)
    except Exception as e:
        print(f"ERROR de conexion: {e}")
        return

    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print()

    if response.status_code != 200:
        print("Respuesta:")
        print(response.text[:1000])
        return

    data = response.json()
    print(f"Tipo: {type(data).__name__}")

    if isinstance(data, list):
        print(f"Items: {len(data)}")
        print()
        if data:
            print("Primer producto:")
            print(json.dumps(data[0], indent=2, ensure_ascii=False)[:1500])
    elif isinstance(data, dict):
        print("Claves del objeto:", list(data.keys()))
        print()
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1500])
    else:
        print("Respuesta inesperada:")
        print(str(data)[:1000])


if __name__ == "__main__":
    main()