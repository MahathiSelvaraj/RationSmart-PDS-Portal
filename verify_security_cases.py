import urllib.request
import urllib.parse
import http.cookiejar
import re

def run_tests():
    print("==================================================================")
    print(" Running Security & Permission Test Suite for RationSmart System")
    print("==================================================================")
    
    # Setup opener with CookieJar
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    urllib.request.install_opener(opener)

    def login(username, password):
        cj.clear()
        data = urllib.parse.urlencode({'username': username, 'password': password}).encode('utf-8')
        req = urllib.request.Request('http://127.0.0.1:5000/login', data=data)
        res = urllib.request.urlopen(req)
        return res

    def get(url):
        req = urllib.request.Request('http://127.0.0.1:5000' + url)
        try:
            res = urllib.request.urlopen(req)
            return res.status, res.url, res.read().decode('utf-8', errors='ignore')
        except urllib.error.HTTPError as e:
            return e.code, e.url, e.read().decode('utf-8', errors='ignore')

    # TEST CASE 1: Admin login -> Admin dashboard
    login('admin', 'admin123')
    status, url, body = get('/admin/dashboard')
    print(f"Test 1: Admin Dashboard -> Status {status} | {'PASSED' if status==200 and '/admin/dashboard' in url else 'FAILED'}")

    # TEST CASE 2: Admin -> View all shops
    status, url, body = get('/admin/shops')
    print(f"Test 2: Admin View All Shops -> Status {status} | {'PASSED' if status==200 and '/admin/shops' in url else 'FAILED'}")

    # TEST CASE 3: Admin -> View all dealer information
    print(f"Test 3: Admin View Dealer Info -> Status {status} | {'PASSED' if status==200 and 'FPS-101' in body else 'FAILED'}")

    # TEST CASE 4: Admin -> View all transactions
    status, url, body = get('/admin/transactions')
    print(f"Test 4: Admin View All Transactions -> Status {status} | {'PASSED' if status==200 and '/admin/transactions' in url else 'FAILED'}")

    # TEST CASE 5: Admin -> Create bill attempt
    status, url, body = get('/dealer/pos')
    print(f"Test 5: Admin Create Bill Attempt (Blocked) -> Redirected to {url} | {'PASSED' if '/admin/dashboard' in url else 'FAILED'}")

    # TEST CASE 6: Dealer 1 -> Dealer dashboard (POS)
    login('dealer1', 'dealer123')
    status, url, body = get('/dealer/pos')
    print(f"Test 6: Dealer 1 POS Access -> Status {status} | {'PASSED' if status==200 and 'FPS-101' in body else 'FAILED'}")

    # TEST CASE 7: Dealer 1 -> Shop 1 data
    status, url, body = get('/dealer/stock')
    print(f"Test 7: Dealer 1 Shop 1 Stock Data -> Status {status} | {'PASSED' if status==200 and 'FPS-101' in body else 'FAILED'}")

    # TEST CASE 8: Dealer 1 -> Create Shop 1 bill
    card_data = urllib.parse.urlencode({
        'ration_card_id': 1, # RC-AAY-1001 (assigned to Shop 1)
        'qty_1': 5, # Rice
        'auth_mode': 'OTP',
        'payment_mode': 'Cash'
    }).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:5000/dealer/pos/process-sale', data=card_data)
    res = urllib.request.urlopen(req)
    receipt_body = res.read().decode('utf-8', errors='ignore')
    print(f"Test 8: Dealer 1 Create Shop 1 Bill -> Status {res.status} | {'PASSED' if '/receipt/' in res.url else 'FAILED'}")

    # TEST CASE 9: Dealer 1 -> View Shop 1 stock
    status, url, body = get('/dealer/stock')
    print(f"Test 9: Dealer 1 View Shop Stock -> Status {status} | {'PASSED' if status==200 and 'FPS-101' in body else 'FAILED'}")

    # TEST CASE 10: Dealer 1 -> Access Shop 2 data manually via URL
    status, url, body = get('/dealer/pos?shop_id=2')
    print(f"Test 10: Dealer 1 Access Shop 2 URL (Forced to Shop 1) -> {'PASSED' if 'FPS-101' in body and 'FPS-102' not in body else 'FAILED'}")

    # TEST CASE 11: Dealer 1 -> Create Shop 2 bill (card assigned to Shop 2: RC-AAY-1003)
    status, url, body = get('/dealer/pos?card_number=RC-AAY-1003')
    print(f"Test 11: Dealer 1 Search Shop 2 Card (Blocked for Billing) -> {'PASSED' if 'Access Restriction' in body or 'belongs to' in body else 'FAILED'}")

    # TEST CASE 12: Dealer 1 -> Change shop ID manually in POST form
    card_data2 = urllib.parse.urlencode({
        'ration_card_id': 9, # RC-AAY-1003 (assigned to Shop 2)
        'shop_id': 2,
        'qty_1': 5
    }).encode('utf-8')
    req2 = urllib.request.Request('http://127.0.0.1:5000/dealer/pos/process-sale', data=card_data2)
    res2 = urllib.request.urlopen(req2)
    res2_body = res2.read().decode('utf-8', errors='ignore')
    print(f"Test 12: Dealer 1 POST Shop 2 Bill (Security Blocked) -> {'PASSED' if 'Security Enforcement' in res2_body or 'belong' in res2_body or '/dealer/pos' in res2.url else 'FAILED'}")

    # TEST CASE 13: Dealer 1 -> Access Admin dashboard manually
    status, url, body = get('/admin/dashboard')
    print(f"Test 13: Dealer 1 Access Admin Dashboard (Access Denied) -> Redirected to {url} | {'PASSED' if '/dealer/pos' in url else 'FAILED'}")

    # TEST CASE 14: Dealer 2 -> Only Shop 2 data
    login('dealer2', 'dealer123')
    status, url, body = get('/dealer/pos')
    print(f"Test 14: Dealer 2 POS Access -> Status {status} | {'PASSED' if status==200 and 'FPS-102' in body else 'FAILED'}")

    # TEST CASE 15: Dealer 2 -> Access Shop 1 data manually via URL
    status, url, body = get('/dealer/pos?shop_id=1')
    print(f"Test 15: Dealer 2 Access Shop 1 URL (Forced to Shop 2) -> {'PASSED' if 'FPS-102' in body and 'FPS-101' not in body else 'FAILED'}")

    # TEST CASE 16: Dealer logout -> reset permissions
    get('/logout')
    status, url, body = get('/admin/dashboard')
    print(f"Test 16: Logged out User Accessing Admin (Redirected to Login) -> Redirected to {url} | {'PASSED' if '/login' in url else 'FAILED'}")

    print("==================================================================")
    print(" All Security Verification Tests Completed!")
    print("==================================================================")

if __name__ == '__main__':
    run_tests()
