"""PHASE 13 — Complete DHAN End-to-End QA Test Suite.

Tests the entire system at runtime as a real user against the live FastAPI (port 8010)
and Django Admin (port 8002) services.
"""

import asyncio
import datetime as dt
import http.cookiejar
import re
import sys
import urllib.parse
import urllib.request
import uuid
import httpx
import jwt

if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

API_BASE = "http://127.0.0.1:8010"
ADMIN_BASE = "http://127.0.0.1:8002"
JWT_SECRET = "dhan-insecure-development-secret-key-change-in-production-1234567890"

class QALogger:
    def __init__(self):
        self.results: list[dict] = []

    def log(self, category: str, name: str, passed: bool, detail: str = ""):
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] {category} :: {name} - {detail}")
        self.results.append({
            "category": category,
            "name": name,
            "passed": passed,
            "detail": detail,
        })

async def run_e2e_qa():
    logger = QALogger()
    print("=" * 80)
    print("STARTING DHAN COMPLETE END-TO-END QA RUNTIME VERIFICATION")
    print("=" * 80)

    # Health check
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        resp = await client.get("/health")
        assert resp.status_code == 200 and resp.json().get("status") == "ok"
        logger.log("Infrastructure", "FastAPI Live Health", True, "Status 200 OK")

    user_a_email = f"user_a_{uuid.uuid4().hex[:8]}@dhan.com"
    user_a_pass = "UserA_Password@2026!"
    user_b_email = f"user_b_{uuid.uuid4().hex[:8]}@dhan.com"
    user_b_pass = "UserB_Password@2026!"

    user_a_tokens = {}
    user_b_tokens = {}

    user_a_data = {}

    # =========================================================================
    # USER A JOURNEY
    # =========================================================================
    print("\n--- USER A: REGISTRATION & ONBOARDING ---")
    async with httpx.AsyncClient(base_url=API_BASE, timeout=15.0) as client:
        # Register User A
        reg_resp = await client.post("/auth/register", json={
            "name": "User Alpha",
            "email": user_a_email,
            "password": user_a_pass,
        })
        passed = reg_resp.status_code == 201 and "access_token" in reg_resp.json()
        logger.log("User A", "Register", passed, f"Status: {reg_resp.status_code}")
        user_a_tokens = reg_resp.json()
        user_a_id = user_a_tokens["user"]["id"]

        # Login User A
        login_resp = await client.post("/auth/login", json={
            "email": user_a_email,
            "password": user_a_pass,
        })
        passed = login_resp.status_code == 200 and "access_token" in login_resp.json()
        logger.log("User A", "Login", passed, f"Status: {login_resp.status_code}")
        user_a_tokens = login_resp.json()
        a_headers = {"Authorization": f"Bearer {user_a_tokens['access_token']}"}

        # Add account 1: Bank (HDFC)
        acc1_resp = await client.post("/accounts", headers=a_headers, json={
            "name": "HDFC Salary Account",
            "type": "bank",
            "balance": "50000.00",
            "currency": "INR",
        })
        passed = acc1_resp.status_code == 201 and float(acc1_resp.json()["balance"]) == 50000.0
        logger.log("User A", "Add Account 1 (Bank)", passed, f"Created {acc1_resp.json().get('name')} with Rs. 50,000")
        user_a_data["acc1"] = acc1_resp.json()

        # Add account 2: Cash
        acc2_resp = await client.post("/accounts", headers=a_headers, json={
            "name": "Cash Wallet",
            "type": "cash",
            "balance": "5000.00",
            "currency": "INR",
        })
        passed = acc2_resp.status_code == 201 and float(acc2_resp.json()["balance"]) == 5000.0
        logger.log("User A", "Add Account 2 (Cash)", passed, f"Created {acc2_resp.json().get('name')} with Rs. 5,000")
        user_a_data["acc2"] = acc2_resp.json()

        # Fetch Categories
        cats_resp = await client.get("/categories", headers=a_headers)
        cats = cats_resp.json()
        food_cat = next((c for c in cats if "food" in c["name"].lower()), cats[0] if cats else None)
        food_cat_id = food_cat["id"] if food_cat else None

        # Add expense: 1,500.00 from Account 1
        exp_resp = await client.post("/transactions", headers=a_headers, json={
            "account_id": user_a_data["acc1"]["id"],
            "category_id": food_cat_id,
            "amount": "1500.00",
            "type": "expense",
            "description": "Dinner at Restaurant",
            "notes": "Team dinner",
        })
        passed = exp_resp.status_code == 201 and float(exp_resp.json()["amount"]) == 1500.0
        logger.log("User A", "Add Expense", passed, f"Expense Rs. 1,500 recorded (ID: {exp_resp.json().get('id')})")
        user_a_data["exp1"] = exp_resp.json()

        # Add income: 25,000.00 into Account 1
        inc_resp = await client.post("/transactions", headers=a_headers, json={
            "account_id": user_a_data["acc1"]["id"],
            "amount": "25000.00",
            "type": "income",
            "description": "Bonus Payout",
            "notes": "Q3 performance bonus",
        })
        passed = inc_resp.status_code == 201 and float(inc_resp.json()["amount"]) == 25000.0
        logger.log("User A", "Add Income", passed, f"Income Rs. 25,000 recorded (ID: {inc_resp.json().get('id')})")
        user_a_data["inc1"] = inc_resp.json()

        # Transfer: 3,000.00 from Account 1 to Account 2
        transfer_resp = await client.post("/transactions", headers=a_headers, json={
            "account_id": user_a_data["acc1"]["id"],
            "destination_account_id": user_a_data["acc2"]["id"],
            "amount": "3000.00",
            "type": "transfer",
            "description": "ATM Cash Withdrawal",
        })
        passed = transfer_resp.status_code == 201 and transfer_resp.json().get("type") == "transfer"
        logger.log("User A", "Transfer", passed, f"Transferred Rs. 3,000 between accounts")
        user_a_data["transfer1"] = transfer_resp.json()

        # Budget: Create monthly budget
        current_month = dt.datetime.now().strftime("%Y-%m")
        budget_resp = await client.post("/budgets", headers=a_headers, json={
            "name": "Food & Dining Monthly Budget",
            "amount": "10000.00",
            "month": current_month,
            "category_id": food_cat_id,
            "period": "monthly",
        })
        passed = budget_resp.status_code == 201 and float(budget_resp.json()["amount"]) == 10000.0
        logger.log("User A", "Budget", passed, f"Budget Rs. 10,000 created for {current_month}")
        user_a_data["budget1"] = budget_resp.json()

        # Split: Create group, split expense, and settlement
        group_resp = await client.post("/groups", headers=a_headers, json={
            "name": "Goa Trip QA Group",
            "description": "Weekend getaway expenses",
            "currency": "INR",
        })
        passed = group_resp.status_code == 201
        logger.log("User A", "Split - Create Group", passed, f"Group '{group_resp.json().get('name')}' created")
        user_a_data["group1"] = group_resp.json()

        split_exp_resp = await client.post("/splits", headers=a_headers, json={
            "group_id": user_a_data["group1"]["id"],
            "title": "Beach Villa Booking",
            "amount": "6000.00",
            "split_type": "equal",
        })
        passed = split_exp_resp.status_code == 201 and float(split_exp_resp.json()["amount"]) == 6000.0
        logger.log("User A", "Split - Add Expense", passed, f"Split expense Rs. 6,000 created")
        user_a_data["split1"] = split_exp_resp.json()

        # Goal: Create goal and add contribution
        goal_resp = await client.post("/goals", headers=a_headers, json={
            "name": "Emergency Fund 2027",
            "target_amount": "100000.00",
            "target_date": (dt.date.today() + dt.timedelta(days=365)).isoformat(),
            "initial_amount": "5000.00",
            "icon": "shield",
        })
        passed = goal_resp.status_code == 201 and float(goal_resp.json()["target_amount"]) == 100000.0
        logger.log("User A", "Goal - Create Target", passed, f"Goal '{goal_resp.json().get('name')}' created")
        user_a_data["goal1"] = goal_resp.json()

        contrib_resp = await client.post(f"/goals/{user_a_data['goal1']['id']}/contributions", headers=a_headers, json={
            "amount": "10000.00",
            "notes": "Added from monthly savings",
        })
        passed = contrib_resp.status_code in (200, 201) and "saved" in contrib_resp.json().get("progress", {})
        saved_amt = contrib_resp.json().get("progress", {}).get("saved")
        logger.log("User A", "Goal - Contribution", passed, f"Contributed Rs. 10,000 to goal, new saved: Rs. {saved_amt}")

        # Recurring: Register recurring subscription
        next_week = (dt.date.today() + dt.timedelta(days=7)).isoformat()
        rec_resp = await client.post("/recurring", headers=a_headers, json={
            "title": "Netflix Premium",
            "kind": "subscription",
            "amount": "649.00",
            "account_id": user_a_data["acc1"]["id"],
            "frequency": "monthly",
            "next_due_date": next_week,
            "status": "active",
        })
        passed = rec_resp.status_code == 201 and rec_resp.json().get("title") == "Netflix Premium"
        logger.log("User A", "Recurring", passed, f"Subscription Rs. 649/mo created")
        user_a_data["rec1"] = rec_resp.json()

        # Reports: Monthly & Categories
        rep_month_resp = await client.get("/reports/monthly", headers=a_headers)
        passed = rep_month_resp.status_code == 200 and "income" in rep_month_resp.json()
        logger.log("User A", "Reports - Monthly", passed, f"Monthly income: {rep_month_resp.json().get('income')}, spending: {rep_month_resp.json().get('spending')}")

        rep_cat_resp = await client.get("/reports/categories", headers=a_headers)
        passed = rep_cat_resp.status_code == 200 and "categories" in rep_cat_resp.json()
        logger.log("User A", "Reports - Categories", passed, f"Categories breakdown returned {len(rep_cat_resp.json().get('categories', []))} entries")

        # Net Worth: Assets & Overall
        asset_resp = await client.post("/net-worth/assets", headers=a_headers, json={
            "name": "Nifty Index Fund",
            "asset_type": "mutual_fund",
            "current_value": "50000.00",
        })
        passed = asset_resp.status_code == 201 and float(asset_resp.json()["current_value"]) == 50000.0
        logger.log("User A", "Net Worth - Add External Asset", passed, f"Added Rs. 50,000 mutual fund asset")
        user_a_data["asset1"] = asset_resp.json()

        nw_resp = await client.get("/net-worth", headers=a_headers)
        passed = nw_resp.status_code == 200 and "net_worth" in nw_resp.json()
        nw_val = nw_resp.json().get("net_worth")
        logger.log("User A", "Net Worth - Calculation", passed, f"Total Net Worth: Rs. {nw_val}")

        # AI: Conversation & Messaging
        ai_conv_resp = await client.post("/ai/conversations", headers=a_headers, json={
            "title": "Spending Analysis QA",
        })
        passed = ai_conv_resp.status_code == 201
        ai_conv = ai_conv_resp.json()
        logger.log("User A", "AI - Create Conversation", passed, f"Conversation ID: {ai_conv.get('id')}")
        user_a_data["ai_conv"] = ai_conv

        ai_msg_resp = await client.post(f"/ai/conversations/{ai_conv['id']}/messages", headers=a_headers, json={
            "content": "How much did I spend this month?",
        })
        passed = ai_msg_resp.status_code == 201 and "assistant_message" in ai_msg_resp.json()
        ai_ans = ai_msg_resp.json().get("assistant_message", {}).get("content", "")
        logger.log("User A", "AI - Send Message & Receive Answer", passed, f"AI Answer: {ai_ans[:60]}...")

        # Logout User A
        logout_resp = await client.post("/auth/logout", headers=a_headers, json={
            "refresh_token": user_a_tokens.get("refresh_token"),
        })
        passed = logout_resp.status_code == 200
        logger.log("User A", "Logout", passed, f"Logout message: {logout_resp.json().get('message')}")

    # =========================================================================
    # USER B JOURNEY & ISOLATION VERIFICATION
    # =========================================================================
    print("\n--- USER B: ISOLATION VERIFICATION ---")
    async with httpx.AsyncClient(base_url=API_BASE, timeout=15.0) as client:
        # Register User B
        reg_b_resp = await client.post("/auth/register", json={
            "name": "User Beta",
            "email": user_b_email,
            "password": user_b_pass,
        })
        assert reg_b_resp.status_code == 201
        user_b_tokens = reg_b_resp.json()
        user_b_id = user_b_tokens["user"]["id"]

        # Login User B
        login_b_resp = await client.post("/auth/login", json={
            "email": user_b_email,
            "password": user_b_pass,
        })
        assert login_b_resp.status_code == 200
        user_b_tokens = login_b_resp.json()
        b_headers = {"Authorization": f"Bearer {user_b_tokens['access_token']}"}
        logger.log("User B", "Register & Login", True, "User B authenticated successfully")

        # Verify User B sees NONE of User A's data
        # Accounts
        b_accs = (await client.get("/accounts", headers=b_headers)).json()
        passed = len(b_accs) == 0
        logger.log("Isolation", "Accounts Isolation", passed, f"User B sees {len(b_accs)} accounts (expected 0)")

        # Transactions
        b_txs = (await client.get("/transactions", headers=b_headers)).json()
        passed = len(b_txs) == 0
        logger.log("Isolation", "Transactions Isolation", passed, f"User B sees {len(b_txs)} transactions (expected 0)")

        # Budgets
        b_budgets = (await client.get("/budgets", headers=b_headers)).json()
        passed = len(b_budgets) == 0
        logger.log("Isolation", "Budgets Isolation", passed, f"User B sees {len(b_budgets)} budgets (expected 0)")

        # Splits / Groups
        b_groups = (await client.get("/groups", headers=b_headers)).json()
        passed = len(b_groups) == 0
        logger.log("Isolation", "Split Groups Isolation", passed, f"User B sees {len(b_groups)} groups (expected 0)")

        # Goals
        b_goals = (await client.get("/goals", headers=b_headers)).json()
        passed = len(b_goals) == 0
        logger.log("Isolation", "Goals Isolation", passed, f"User B sees {len(b_goals)} goals (expected 0)")

        # Recurring
        b_rec = (await client.get("/recurring", headers=b_headers)).json()
        passed = len(b_rec) == 0
        logger.log("Isolation", "Recurring Isolation", passed, f"User B sees {len(b_rec)} recurring payments (expected 0)")

        # Reports
        b_rep = (await client.get("/reports/monthly", headers=b_headers)).json()
        passed = float(b_rep.get("income", 0)) == 0.0 and float(b_rep.get("spending", 0)) == 0.0
        logger.log("Isolation", "Reports Isolation", passed, f"User B reports income=0, spending=0")

        # Net worth
        b_nw = (await client.get("/net-worth", headers=b_headers)).json()
        passed = float(b_nw.get("net_worth", -1)) == 0.0
        logger.log("Isolation", "Net Worth Isolation", passed, f"User B net worth = Rs. {b_nw.get('net_worth')}")

        # AI
        b_ai = (await client.get("/ai/conversations", headers=b_headers)).json()
        passed = len(b_ai) == 0
        logger.log("Isolation", "AI Conversations Isolation", passed, f"User B sees {len(b_ai)} AI conversations (expected 0)")

        # Direct cross-tenant access attempts by User B to User A's objects
        acc_attack = await client.get(f"/accounts/{user_a_data['acc1']['id']}", headers=b_headers)
        passed = acc_attack.status_code in (403, 404)
        logger.log("Isolation", "Cross-User Account Direct Access", passed, f"Blocked with {acc_attack.status_code}")

        tx_attack = await client.get(f"/transactions/{user_a_data['exp1']['id']}", headers=b_headers)
        passed = tx_attack.status_code in (403, 404)
        logger.log("Isolation", "Cross-User Transaction Direct Access", passed, f"Blocked with {tx_attack.status_code}")

        bg_attack = await client.get(f"/budgets/{user_a_data['budget1']['id']}", headers=b_headers)
        passed = bg_attack.status_code in (403, 404)
        logger.log("Isolation", "Cross-User Budget Direct Access", passed, f"Blocked with {bg_attack.status_code}")

        grp_attack = await client.get(f"/groups/{user_a_data['group1']['id']}", headers=b_headers)
        passed = grp_attack.status_code in (403, 404)
        logger.log("Isolation", "Cross-User Group Direct Access", passed, f"Blocked with {grp_attack.status_code}")

        goal_attack = await client.get(f"/goals/{user_a_data['goal1']['id']}", headers=b_headers)
        passed = goal_attack.status_code in (403, 404)
        logger.log("Isolation", "Cross-User Goal Direct Access", passed, f"Blocked with {goal_attack.status_code}")

        rec_attack = await client.get(f"/recurring/{user_a_data['rec1']['id']}", headers=b_headers)
        passed = rec_attack.status_code in (403, 404)
        logger.log("Isolation", "Cross-User Recurring Direct Access", passed, f"Blocked with {rec_attack.status_code}")

        ai_attack = await client.get(f"/ai/conversations/{user_a_data['ai_conv']['id']}", headers=b_headers)
        passed = ai_attack.status_code in (403, 404)
        logger.log("Isolation", "Cross-User AI Conv Direct Access", passed, f"Blocked with {ai_attack.status_code}")

    # =========================================================================
    # ADMIN PANEL & PRIVILEGE VERIFICATION
    # =========================================================================
    print("\n--- ADMIN PANEL VERIFICATION ---")
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    login_url = f"{ADMIN_BASE}/admin/login/"
    req = urllib.request.Request(login_url)
    resp = opener.open(req)
    html = resp.read().decode("utf-8")
    csrf_token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)

    login_data = urllib.parse.urlencode({
        "csrfmiddlewaretoken": csrf_token,
        "username": "admin@dhan.local",
        "password": "DhanAdmin@2026!",
        "next": "/admin/",
    }).encode("utf-8")

    req = urllib.request.Request(login_url, data=login_data, headers={"Referer": login_url})
    resp = opener.open(req)
    dashboard_html = resp.read().decode("utf-8")
    passed = "administration" in dashboard_html.lower() or "dhan" in dashboard_html.lower()
    logger.log("Admin", "Admin Login & Dashboard", passed, f"Admin dashboard accessed: URL {resp.geturl()}")

    # Admin accesses core models
    models_to_check = [
        ("DHAN Users", "/admin/core/dhanuser/"),
        ("Admin Audit Logs", "/admin/core/adminauditlog/"),
        ("Accounts", "/admin/core/account/"),
        ("Transactions", "/admin/core/transaction/"),
        ("Budgets", "/admin/core/budget/"),
        ("Split Groups", "/admin/core/splitgroup/"),
        ("Goals", "/admin/core/goal/"),
        ("Recurring Payments", "/admin/core/recurringpayment/"),
        ("Assets", "/admin/core/asset/"),
    ]
    for model_name, path in models_to_check:
        try:
            m_resp = opener.open(f"{ADMIN_BASE}{path}")
            m_html = m_resp.read().decode("utf-8")
            passed = m_resp.status == 200 and ("change" in m_html.lower() or "select" in m_html.lower() or "dhan" in m_html.lower())
            logger.log("Admin", f"Access {model_name}", passed, f"Status 200 on {path}")
        except Exception as e:
            logger.log("Admin", f"Access {model_name}", False, str(e))

    # Verify normal user CANNOT access Django Admin
    cj_normal = http.cookiejar.CookieJar()
    opener_normal = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_normal))
    req_norm = urllib.request.Request(login_url)
    resp_norm = opener_normal.open(req_norm)
    csrf_norm = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp_norm.read().decode("utf-8")).group(1)

    normal_login_data = urllib.parse.urlencode({
        "csrfmiddlewaretoken": csrf_norm,
        "username": user_a_email,
        "password": user_a_pass,
        "next": "/admin/",
    }).encode("utf-8")
    req_norm_post = urllib.request.Request(login_url, data=normal_login_data, headers={"Referer": login_url})
    resp_norm_post = opener_normal.open(req_norm_post)
    norm_result_html = resp_norm_post.read().decode("utf-8")
    # Normal user must not be granted admin session (should remain on login page with error)
    passed = "Please enter the correct username and password" in norm_result_html or "not authorized" in norm_result_html.lower() or "/admin/login/" in resp_norm_post.geturl()
    logger.log("Admin Security", "Normal User Admin Login Rejection", passed, "Normal user credentials rejected by Django Admin")

    # =========================================================================
    # EDGE CASES & ROBUSTNESS TESTS
    # =========================================================================
    print("\n--- EDGE CASES & ROBUSTNESS TESTING ---")
    async with httpx.AsyncClient(base_url=API_BASE, timeout=15.0) as client:
        # Invalid Token
        inv_resp = await client.get("/accounts", headers={"Authorization": "Bearer invalid_gibberish_token_xyz"})
        passed = inv_resp.status_code == 401
        logger.log("Robustness", "Invalid Token", passed, f"Status: {inv_resp.status_code}")

        # Expired Token
        expired_payload = {
            "sub": str(user_a_id),
            "exp": dt.datetime.now(dt.UTC) - dt.timedelta(hours=1),
            "type": "access",
        }
        expired_jwt = jwt.encode(expired_payload, JWT_SECRET, algorithm="HS256")
        exp_jwt_resp = await client.get("/accounts", headers={"Authorization": f"Bearer {expired_jwt}"})
        passed = exp_jwt_resp.status_code == 401
        logger.log("Robustness", "Expired Token", passed, f"Status: {exp_jwt_resp.status_code}")

        # Revoked Refresh Token cannot refresh
        rev_refresh_resp = await client.post("/auth/refresh", json={
            "refresh_token": user_a_tokens.get("refresh_token"),
        })
        # Since User A logged out and revoked refresh token, refresh should fail (401)
        passed = rev_refresh_resp.status_code == 401
        logger.log("Robustness", "Revoked Token on Refresh", passed, f"Status: {rev_refresh_resp.status_code}")

        # Re-login User A for remaining tests
        re_login = await client.post("/auth/login", json={"email": user_a_email, "password": user_a_pass})
        a_headers = {"Authorization": f"Bearer {re_login.json()['access_token']}"}

        # Invalid Data: Negative transaction amount
        neg_resp = await client.post("/transactions", headers=a_headers, json={
            "account_id": user_a_data["acc1"]["id"],
            "amount": "-500.00",
            "type": "expense",
            "description": "Negative amount test",
        })
        passed = neg_resp.status_code == 422
        logger.log("Robustness", "Invalid Data (Negative Amount)", passed, f"Status: {neg_resp.status_code}")

        # Invalid Data: Blank account name
        blank_resp = await client.post("/accounts", headers=a_headers, json={
            "name": "   ",
            "type": "savings",
        })
        passed = blank_resp.status_code == 422
        logger.log("Robustness", "Invalid Data (Blank Name)", passed, f"Status: {blank_resp.status_code}")

        # Empty States: User B querying budgets/categories/transactions
        empty_b_resp = await client.get("/budgets", headers=b_headers)
        passed = empty_b_resp.status_code == 200 and empty_b_resp.json() == []
        logger.log("Robustness", "Empty States (Budgets)", passed, "Returns empty list without error")

        # Pagination: Limit and offset
        page_resp = await client.get("/transactions?limit=1&offset=0", headers=a_headers)
        passed = page_resp.status_code == 200 and len(page_resp.json()) == 1 and "X-Total-Count" in page_resp.headers
        logger.log("Robustness", "Pagination", passed, f"Returned 1 item, X-Total-Count={page_resp.headers.get('X-Total-Count')}")

        # Filtering: Filter by type=expense
        filter_resp = await client.get("/transactions?type=expense", headers=a_headers)
        passed = filter_resp.status_code == 200 and all(tx["type"] == "expense" for tx in filter_resp.json())
        logger.log("Robustness", "Filtering (type=expense)", passed, f"{len(filter_resp.json())} expense transactions matched")

        # Search: Search transactions by note/description
        search_resp = await client.get("/transactions?search=Restaurant", headers=a_headers)
        passed = search_resp.status_code == 200 and len(search_resp.json()) >= 1
        logger.log("Robustness", "Search", passed, f"Search 'Restaurant' matched {len(search_resp.json())} transactions")

        # Concurrent Operations: 5 simultaneous transactions
        concurrent_payloads = [
            {
                "account_id": user_a_data["acc1"]["id"],
                "amount": f"{100 + i}.00",
                "type": "expense",
                "description": f"Concurrent Tx #{i}",
            }
            for i in range(5)
        ]
        tasks = [client.post("/transactions", headers=a_headers, json=p) for p in concurrent_payloads]
        concur_responses = await asyncio.gather(*tasks)
        all_passed = all(r.status_code == 201 for r in concur_responses)
        logger.log("Robustness", "Concurrent Transactions", all_passed, f"All 5 concurrent requests succeeded")

        # Database Rollback: Invalid transfer with non-existent destination account
        fake_acc_id = str(uuid.uuid4())
        bad_transfer = await client.post("/transactions", headers=a_headers, json={
            "account_id": user_a_data["acc1"]["id"],
            "destination_account_id": fake_acc_id,
            "amount": "2000.00",
            "type": "transfer",
            "description": "Faulty transfer",
        })
        passed = bad_transfer.status_code in (400, 404, 422)
        logger.log("Robustness", "Database Rollback on Failure", passed, f"Faulty transfer rejected with status {bad_transfer.status_code}")

    # =========================================================================
    # FINANCIAL INVARIANTS VERIFICATION
    # =========================================================================
    print("\n--- FINANCIAL INVARIANTS VERIFICATION ---")
    async with httpx.AsyncClient(base_url=API_BASE, timeout=15.0) as client:
        # Check Account 1 & Account 2 balances
        acc1 = (await client.get(f"/accounts/{user_a_data['acc1']['id']}", headers=a_headers)).json()
        acc2 = (await client.get(f"/accounts/{user_a_data['acc2']['id']}", headers=a_headers)).json()

        # Expected Account 1:
        # initial 50,000 - 1500 (exp1) + 25000 (inc1) - 3000 (transfer1) - sum(100..104) (concurrent 510)
        # = 50000 - 1500 + 25000 - 3000 - 510 = 69,990.00
        # Expected Account 2:
        # initial 5000 + 3000 (transfer1) = 8,000.00
        expected_acc1 = 69990.0
        expected_acc2 = 8000.0

        actual_acc1 = float(acc1["balance"])
        actual_acc2 = float(acc2["balance"])
        passed = (actual_acc1 == expected_acc1) and (actual_acc2 == expected_acc2)
        logger.log("Invariants", "Account Balances Math", passed,
                   f"Acc1: Rs. {actual_acc1} (exp Rs. {expected_acc1}), Acc2: Rs. {actual_acc2} (exp Rs. {expected_acc2})")

        # Invariant 2: Net balance = sum(accounts)
        all_accs = (await client.get("/accounts", headers=a_headers)).json()
        sum_balances = sum(float(a["balance"]) for a in all_accs if a["include_in_total"])

        nw_data = (await client.get("/net-worth", headers=a_headers)).json()
        actual_net_balance = float(nw_data["net_balance"]["total"])
        passed = round(sum_balances, 2) == round(actual_net_balance, 2)
        logger.log("Invariants", "Net Balance Equals Sum of Accounts", passed,
                   f"Sum: Rs. {sum_balances} == Net Balance: Rs. {actual_net_balance}")

        # Invariant 3: Net Worth = Total Assets - Total Liabilities
        actual_nw = float(nw_data["net_worth"])
        assets_total = float(nw_data["total_assets"])
        liab_total = float(nw_data["total_liabilities"])
        expected_nw = assets_total - liab_total
        passed = round(actual_nw, 2) == round(expected_nw, 2)
        logger.log("Invariants", "Net Worth = Total Assets - Total Liabilities", passed,
                   f"Rs. {actual_nw} == Rs. {expected_nw}")

        # Invariant 4: Monthly Report: net = income - spent
        month_rep = (await client.get("/reports/monthly", headers=a_headers)).json()
        m_inc = float(month_rep["income"])
        m_spent = float(month_rep["spent"])
        m_net = float(month_rep["net"])
        passed = round(m_net, 2) == round(m_inc - m_spent, 2)
        logger.log("Invariants", "Reports Cashflow Equation", passed,
                   f"Net Rs. {m_net} == Income Rs. {m_inc} - Spent Rs. {m_spent}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    total_tests = len(logger.results)
    passed_tests = sum(1 for r in logger.results if r["passed"])
    failed_tests = total_tests - passed_tests

    print("\n" + "=" * 80)
    print(f"E2E QA SUMMARY: {passed_tests}/{total_tests} PASSED ({failed_tests} FAILED)")
    print("=" * 80)

    if failed_tests > 0:
        print("\nFailed Tests:")
        for r in logger.results:
            if not r["passed"]:
                print(f"  - {r['category']} :: {r['name']} => {r['detail']}")
        return False
    return True

if __name__ == "__main__":
    success = asyncio.run(run_e2e_qa())
    exit(0 if success else 1)
