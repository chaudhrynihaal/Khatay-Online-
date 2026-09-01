"""Installability plumbing: manifest, service worker, and the pages that
reference them. No offline-write-queue coverage on purpose - see the
"no event.respondWith on non-GET" comment in service-worker.js, which is
the actual safety boundary and isn't something a Python test can assert
on a static JS file anyway."""
import app as app_module


def test_manifest_served_at_root_with_correct_type():
    c = app_module.app.test_client()
    r = c.get("/manifest.json")
    assert r.status_code == 200
    assert r.content_type == "application/manifest+json"
    assert b"Khatay" in r.data


def test_service_worker_served_at_root_scope():
    c = app_module.app.test_client()
    r = c.get("/service-worker.js")
    assert r.status_code == 200
    assert r.headers.get("Service-Worker-Allowed") == "/"
    assert b"method !== \"GET\"" in r.data, \
        "the non-GET pass-through guard is the safety boundary - must not get refactored away silently"


def test_login_page_links_manifest_and_registers_service_worker():
    c = app_module.app.test_client()
    r = c.get("/login")
    html = r.data.decode()
    assert 'rel="manifest"' in html
    assert "serviceWorker" in html
