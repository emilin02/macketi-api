"""Vista previa de migración de clientes WooCommerce -> Macketi.

Solo lectura: consulta la API REST y PostgreSQL, no crea ni modifica usuarios.
Uso desde la raíz del proyecto: python scripts/preview_woocommerce_customers.py
"""
import asyncio
import sys
from base64 import b64encode
from pathlib import Path

import httpx
from sqlalchemy import select, func

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.db.session import async_session_factory  # noqa: E402
from app.models.user import User  # noqa: E402

PER_PAGE = 100
TIMEOUT = 30.0


def auth_header() -> str:
    if not settings.WOOCOMMERCE_URL or not settings.WOOCOMMERCE_CONSUMER_KEY or not settings.WOOCOMMERCE_CONSUMER_SECRET:
        raise RuntimeError("Faltan WOOCOMMERCE_URL/CONSUMER_KEY/CONSUMER_SECRET en .env")
    raw = f"{settings.WOOCOMMERCE_CONSUMER_KEY}:{settings.WOOCOMMERCE_CONSUMER_SECRET}"
    return "Basic " + b64encode(raw.encode()).decode()


async def fetch_customers(client: httpx.AsyncClient) -> list[dict]:
    customers: list[dict] = []
    page = 1
    while True:
        response = await client.get(
            "/wc/v3/customers",
            params={"page": page, "per_page": PER_PAGE, "_fields": "id,email,first_name,last_name,username,billing"},
        )
        response.raise_for_status()
        batch = response.json()
        if not isinstance(batch, list):
            raise RuntimeError("WooCommerce devolvió una respuesta inesperada; no se ha importado nada.")
        customers.extend(batch)
        print(f"Página {page}: {len(batch)} clientes recibidos")
        if len(batch) < PER_PAGE:
            break
        page += 1
    return customers


async def main() -> None:
    base_url = settings.WOOCOMMERCE_URL.rstrip("/") + "/wp-json"
    headers = {"Authorization": auth_header(), "Accept": "application/json"}
    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=TIMEOUT) as client:
        customers = await fetch_customers(client)

    # Solo preparar identificadores normalizados en memoria; no mostrar datos personales.
    woo_emails: dict[str, list[int]] = {}
    missing_email = 0
    for customer in customers:
        email = (customer.get("email") or "").strip().casefold()
        if not email:
            missing_email += 1
            continue
        woo_emails.setdefault(email, []).append(int(customer["id"]))

    duplicate_email_groups = sum(1 for ids in woo_emails.values() if len(ids) > 1)
    async with async_session_factory() as session:
        result = await session.execute(select(func.lower(User.email), User.id))
        existing = {email.strip().casefold(): user_id for email, user_id in result.all() if email}

    overlap = set(woo_emails) & set(existing)
    new_emails = set(woo_emails) - set(existing)
    duplicate_db_groups = len(woo_emails) - len(set(woo_emails))

    print("\n=== VISTA PREVIA (SOLO LECTURA) ===")
    print(f"Clientes recibidos desde WooCommerce: {len(customers)}")
    print(f"Clientes con email: {len(woo_emails)}")
    print(f"Clientes sin email: {missing_email}")
    print(f"Emails distintos repetidos dentro de WooCommerce: {duplicate_email_groups}")
    print(f"Emails que ya existen en Macketi (no se modificarían): {len(overlap)}")
    print(f"Emails candidatos a cuenta nueva: {len(new_emails)}")
    print("\nNo se ha escrito ni modificado ningún dato en PostgreSQL ni en WooCommerce.")
    print("Nota: esta vista previa no verifica contraseñas ni importa usuarios.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except httpx.HTTPStatusError as exc:
        print(f"Error HTTP de WooCommerce: estado {exc.response.status_code}. Revisa URL, permisos y claves.", file=sys.stderr)
        raise SystemExit(1)
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        print(f"No se pudo completar la vista previa: {exc}", file=sys.stderr)
        raise SystemExit(1)
