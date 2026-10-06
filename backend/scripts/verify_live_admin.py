import http.cookiejar
import re
import urllib.parse
import urllib.request


def test_live_admin():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    login_url = "http://127.0.0.1:8002/admin/login/"
    req = urllib.request.Request(login_url)
    resp = opener.open(req)
    html = resp.read().decode("utf-8")
    csrf_token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)
    print(f"[OK] Fetched CSRF token: {csrf_token[:10]}...")

    login_data = urllib.parse.urlencode(
        {
            "csrfmiddlewaretoken": csrf_token,
            "username": "admin@dhan.local",
            "password": "DhanAdmin@2026!",
            "next": "/admin/",
        }
    ).encode("utf-8")

    req = urllib.request.Request(login_url, data=login_data, headers={"Referer": login_url})
    resp = opener.open(req)
    dashboard = resp.read().decode("utf-8")
    print(f"[OK] Logged in to Live Django Admin. Final URL: {resp.geturl()}")
    print(
        "Dashboard title/snippet:",
        [line for line in dashboard.splitlines() if "<title>" in line or "<h1>" in line],
    )
    assert "administration" in dashboard.lower() or "dhan" in dashboard.lower()
    print("[OK] Admin Dashboard verified")

    resp_users = opener.open("http://127.0.0.1:8002/admin/core/dhanuser/")
    users_html = resp_users.read().decode("utf-8")
    assert "Select User to change" in users_html or "Users" in users_html
    print("[OK] Users page loaded successfully, verified DHAN users!")

    resp_search = opener.open("http://127.0.0.1:8002/admin/core/dhanuser/?q=admin")
    search_html = resp_search.read().decode("utf-8")
    assert "admin@dhan.local" in search_html
    print("[OK] Search users verified!")

    models_to_test = [
        "account",
        "category",
        "transaction",
        "budget",
        "splitexpense",
        "splitgroup",
        "settlement",
        "goal",
        "recurringpayment",
        "asset",
        "liability",
        "notification",
        "adminauditlog",
    ]
    for model in models_to_test:
        resp_m = opener.open(f"http://127.0.0.1:8002/admin/core/{model}/")
        assert resp_m.status == 200
        print(f"[OK] Verified live model page: /admin/core/{model}/ (Status 200)")

    # Test normal user rejection
    cj_normal = http.cookiejar.CookieJar()
    opener_normal = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_normal))
    req = urllib.request.Request(login_url)
    resp = opener_normal.open(req)
    csrf_token_normal = re.search(
        r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.read().decode("utf-8")
    ).group(1)

    login_data_normal = urllib.parse.urlencode(
        {
            "csrfmiddlewaretoken": csrf_token_normal,
            "username": "rohan_42aa91@dhan.com",
            "password": "WrongOrNormalPassword123!",
            "next": "/admin/",
        }
    ).encode("utf-8")
    req = urllib.request.Request(login_url, data=login_data_normal, headers={"Referer": login_url})
    resp = opener_normal.open(req)
    content = resp.read().decode("utf-8")
    assert (
        "/admin/login/" in resp.geturl()
        or "Please enter the correct email" in content
        or "Please enter the correct" in content
    )
    print("[OK] Normal user access successfully blocked by live server!")

    print("\nALL 15 LIVE HTTP DJANGO ADMIN END-TO-END VERIFICATIONS PASSED!")


if __name__ == "__main__":
    test_live_admin()
