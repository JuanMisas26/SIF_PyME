import pytest


def test_paginacion_facturas_flat_and_envelope(client):
    # Verify flat list mode (backwards compatible)
    res_flat = client.get("/api/facturas")
    assert res_flat.status_code == 200
    data_flat = res_flat.json()
    assert isinstance(data_flat, list)
    assert "X-Total-Count" in res_flat.headers
    assert "X-Page" in res_flat.headers
    assert "X-Page-Size" in res_flat.headers
    assert "X-Total-Pages" in res_flat.headers

    # Verify structured paginated envelope
    res_pag = client.get("/api/facturas?paginated=true&page=1&page_size=5")
    assert res_pag.status_code == 200
    data_pag = res_pag.json()
    assert isinstance(data_pag, dict)
    assert "items" in data_pag
    assert "total" in data_pag
    assert "page" in data_pag
    assert "page_size" in data_pag
    assert "total_pages" in data_pag
    assert data_pag["page"] == 1
    assert data_pag["page_size"] == 5
    assert len(data_pag["items"]) <= 5


def test_paginacion_presupuestos_flat_and_envelope(client):
    # Flat list mode
    res_flat = client.get("/api/presupuestos")
    assert res_flat.status_code == 200
    data_flat = res_flat.json()
    assert isinstance(data_flat, list)
    assert "X-Total-Count" in res_flat.headers
    assert "X-Page" in res_flat.headers
    assert "X-Page-Size" in res_flat.headers
    assert "X-Total-Pages" in res_flat.headers

    # Envelope mode
    res_pag = client.get("/api/presupuestos?paginated=true&page=1&page_size=2")
    assert res_pag.status_code == 200
    data_pag = res_pag.json()
    assert isinstance(data_pag, dict)
    assert "items" in data_pag
    assert "total" in data_pag
    assert "page" in data_pag
    assert "page_size" in data_pag
    assert "total_pages" in data_pag
    assert data_pag["page"] == 1
    assert data_pag["page_size"] == 2
    assert len(data_pag["items"]) <= 2


def test_paginacion_clientes_flat_and_envelope(client):
    # Create test client if needed
    client.post("/api/clientes", json={
        "razon_social": "Cliente Paginacion Test",
        "nif_cif": "B99999999",
        "email": "test@paginacion.com",
        "telefono": "600000000"
    })

    # Flat list mode
    res_flat = client.get("/api/clientes")
    assert res_flat.status_code == 200
    data_flat = res_flat.json()
    assert isinstance(data_flat, list)
    assert "X-Total-Count" in res_flat.headers
    assert "X-Page" in res_flat.headers
    assert "X-Page-Size" in res_flat.headers
    assert "X-Total-Pages" in res_flat.headers

    # Envelope mode
    res_pag = client.get("/api/clientes?paginated=true&page=1&page_size=1")
    assert res_pag.status_code == 200
    data_pag = res_pag.json()
    assert isinstance(data_pag, dict)
    assert "items" in data_pag
    assert "total" in data_pag
    assert "page" in data_pag
    assert "page_size" in data_pag
    assert "total_pages" in data_pag
    assert data_pag["page"] == 1
    assert data_pag["page_size"] == 1
    assert len(data_pag["items"]) <= 1


def test_paginacion_productos_flat_and_envelope(client):
    # Create test product if needed
    client.post("/api/productos", json={
        "nombre": "Producto Paginacion Test",
        "descripcion": "Descripción test",
        "precio_base": 25.0
    })

    # Flat list mode
    res_flat = client.get("/api/productos")
    assert res_flat.status_code == 200
    data_flat = res_flat.json()
    assert isinstance(data_flat, list)
    assert "X-Total-Count" in res_flat.headers
    assert "X-Page" in res_flat.headers
    assert "X-Page-Size" in res_flat.headers
    assert "X-Total-Pages" in res_flat.headers

    # Envelope mode
    res_pag = client.get("/api/productos?paginated=true&page=1&page_size=1")
    assert res_pag.status_code == 200
    data_pag = res_pag.json()
    assert isinstance(data_pag, dict)
    assert "items" in data_pag
    assert "total" in data_pag
    assert "page" in data_pag
    assert "page_size" in data_pag
    assert "total_pages" in data_pag
    assert data_pag["page"] == 1
    assert data_pag["page_size"] == 1
    assert len(data_pag["items"]) <= 1

