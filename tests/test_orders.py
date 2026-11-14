def test_order_number_format():
    """
    Comprueba que el formato de un número
    de pedido sea el esperado.
    """
    year = 2026
    sequence_number = 15

    order_number = f"MK-{year}-{sequence_number:05d}"

    assert order_number == "MK-2026-00015"