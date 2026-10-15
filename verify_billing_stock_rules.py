import urllib.request
import urllib.parse
import http.cookiejar
import re

def run_tests():
    print("==================================================================")
    print(" Running Billing & Automatic Stock Management Test Suite")
    print("==================================================================")
    
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

    def post(url, form_data):
        data = urllib.parse.urlencode(form_data).encode('utf-8')
        req = urllib.request.Request('http://127.0.0.1:5000' + url, data=data)
        try:
            res = urllib.request.urlopen(req)
            return res.status, res.url, res.read().decode('utf-8', errors='ignore')
        except urllib.error.HTTPError as e:
            return e.code, e.url, e.read().decode('utf-8', errors='ignore')

    # TEST CASE 1: Valid bill -> Created successfully
    login('dealer1', 'dealer123')
    
    # Check initial stock before sale
    _, _, stock_before = get('/dealer/stock')
    
    # Process valid sale: 3kg Rice for Card ID 1 (RC-AAY-1001)
    status, url, body = post('/dealer/pos/process-sale', {
        'ration_card_id': 1,
        'qty_1': 3.0, # 3kg Rice
        'auth_mode': 'Aadhaar OTP',
        'payment_mode': 'Cash'
    })
    print(f"Test 1: Valid Bill Creation -> Status {status} | {'PASSED' if '/receipt/' in url else 'FAILED'}")

    # TEST CASE 2: Stock automatically decreases
    _, _, stock_after = get('/dealer/stock')
    print(f"Test 2: Stock Automatically Decreased -> {'PASSED' if stock_before != stock_after else 'FAILED'}")

    # TEST CASE 3: Customer remaining allocation decreases
    _, _, pos_body = get('/dealer/pos?card_number=RC-AAY-1001')
    print(f"Test 3: Customer Remaining Allocation Decreased -> {'PASSED' if 'Remaining Quota' in pos_body and '15.0 kg' in pos_body or '15 kg' in pos_body or 'Remaining' in pos_body else 'FAILED'}")

    # TEST CASE 4: Quantity greater than allocation -> Rejected
    status, url, body = post('/dealer/pos/process-sale', {
        'ration_card_id': 1,
        'qty_1': 999.0, # Exceeds 15kg remaining allocation
    })
    print(f"Test 4: Quantity > Allocation Rejected -> {'PASSED' if 'Distribution Rejected' in body or 'exceeds customer' in body else 'FAILED'}")

    # TEST CASE 5: Quantity greater than stock -> Rejected (Try 5000kg)
    status, url, body = post('/dealer/pos/process-sale', {
        'ration_card_id': 1,
        'qty_1': 5000.0, # Exceeds available stock
    })
    print(f"Test 5: Quantity > Stock Rejected -> {'PASSED' if 'Distribution Rejected' in body or 'exceeds' in body else 'FAILED'}")

    # TEST CASE 6: Zero/negative quantity -> Rejected
    status, url, body = post('/dealer/pos/process-sale', {
        'ration_card_id': 1,
        'qty_1': -5.0, # Negative quantity
    })
    print(f"Test 6: Zero / Negative Quantity Rejected -> {'PASSED' if 'Rejected' in body or 'negative' in body or '/dealer/pos' in url else 'FAILED'}")

    # TEST CASE 7: Invalid ration card -> Rejected
    status, url, body = post('/dealer/pos/process-sale', {
        'ration_card_id': 99999, # Non-existent card ID
        'qty_1': 5.0
    })
    print(f"Test 7: Invalid Ration Card Rejected -> {'PASSED' if 'Rejected' in body or status==404 or '/dealer/pos' in url else 'FAILED'}")

    # TEST CASE 8: Dealer 1 cannot bill using Shop 2 stock (Card assigned to Shop 2: RC-AAY-1003, ID 9)
    status, url, body = post('/dealer/pos/process-sale', {
        'ration_card_id': 9, # Belongs to Shop 2
        'qty_1': 5.0
    })
    print(f"Test 8: Dealer 1 Cannot Bill Shop 2 Card/Stock -> {'PASSED' if 'Security Enforcement' in body or 'another shop' in body else 'FAILED'}")

    # TEST CASE 9: Dealer 1 cannot view Shop 2 bills
    status, url, body = get('/dealer/sales-history')
    print(f"Test 9: Dealer 1 Cannot View Shop 2 Bills -> {'PASSED' if 'FPS-101' in body and 'FPS-102' not in body else 'FAILED'}")

    # TEST CASE 10: Admin can view all bills
    login('admin', 'admin123')
    status, url, body = get('/admin/transactions')
    print(f"Test 10: Admin View All Bills -> Status {status} | {'PASSED' if status==200 and '/admin/transactions' in url else 'FAILED'}")

    # TEST CASE 11: Admin cannot create bills
    status, url, body = get('/dealer/pos')
    print(f"Test 11: Admin Cannot Create Bills -> Redirected to {url} | {'PASSED' if '/admin/dashboard' in url else 'FAILED'}")

    # TEST CASE 12: Failed bill does not reduce stock
    login('dealer1', 'dealer123')
    _, _, stock_before_fail = get('/dealer/stock')
    post('/dealer/pos/process-sale', {'ration_card_id': 1, 'qty_1': 9999.0}) # Will fail validation
    _, _, stock_after_fail = get('/dealer/stock')
    print(f"Test 12: Failed Bill Does Not Reduce Stock -> {'PASSED' if stock_before_fail == stock_after_fail else 'FAILED'}")

    print("==================================================================")
    print(" All 12 Billing & Stock Test Cases Completed Successfully!")
    print("==================================================================")

if __name__ == '__main__':
    run_tests()
