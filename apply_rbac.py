import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Replace role_required decorator logic
old_decorator = '''    # Role protection decorator
    def role_required(*allowed_roles):
        def decorator(f):
            @wraps(f)
            @login_required
            def decorated_function(*args, **kwargs):
                if not current_user.is_authenticated or current_user.role not in allowed_roles:
                    flash('Access Denied: You do not have permission to access this page.', 'danger')
                    if current_user.is_authenticated:
                        if current_user.role == 'admin':
                            return redirect(url_for('admin_dashboard'))
                        elif current_user.role == 'dealer':
                            return redirect(url_for('dealer_pos'))
                        
                    return redirect(url_for('login'))
                return f(*args, **kwargs)
            return decorated_function
        return decorator'''

new_decorator = '''    # Role protection decorator
    def role_required(*allowed_roles):
        def decorator(f):
            @wraps(f)
            @login_required
            def decorated_function(*args, **kwargs):
                if not current_user.is_authenticated or current_user.role not in allowed_roles:
                    if current_user.role == 'dealer':
                        flash('Access Denied: Dealers can only access their assigned Shop Billing and operations.', 'danger')
                        return redirect(url_for('dealer_pos'))
                    elif current_user.role in ['admin', 'inspector']:
                        flash('Access Denied: Billing operations are restricted to Shop Dealers only. Admins can view and monitor transactions.', 'danger')
                        return redirect(url_for('admin_dashboard'))
                    else:
                        flash('Access Denied: You do not have permission to access this page.', 'danger')
                        return redirect(url_for('login'))
                return f(*args, **kwargs)
            return decorated_function
        return decorator'''

if old_decorator in code:
    code = code.replace(old_decorator, new_decorator)

# 2. Update all @role_required('admin', 'dealer') on admin routes to @role_required('admin', 'inspector')
# We replace @role_required('admin', 'dealer') on admin routes
admin_routes = [
    '/admin/dashboard',
    '/admin/shops',
    '/admin/shops/<int:shop_id>/edit',
    '/admin/beneficiaries',
    '/admin/beneficiaries/<int:card_id>/delete',
    '/admin/beneficiaries/<int:card_id>/edit',
    '/admin/allocations',
    '/admin/stock',
    '/admin/stock/adjust',
    '/admin/anomalies',
    '/admin/anomalies/<int:anomaly_id>/resolve',
    '/admin/grievances',
    '/admin/grievances/<int:grv_id>/update',
    '/admin/reports'
]

for route in admin_routes:
    pattern = rf"(@app\.route\('{re.escape(route)}'[^)]*\)\s*)@role_required\('[^']+', '[^']+'\)"
    code = re.sub(pattern, r"\1@role_required('admin', 'inspector')", code)

# 3. Update dealer routes to @role_required('dealer') strictly
dealer_routes = [
    '/dealer/pos',
    '/dealer/pos/process-sale',
    '/dealer/stock',
    '/dealer/sales-history'
]

for route in dealer_routes:
    pattern = rf"(@app\.route\('{re.escape(route)}'[^)]*\)\s*)@role_required\('[^']+', '[^']+'\)"
    code = re.sub(pattern, r"\1@role_required('dealer')", code)

# Write updated code
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Updated app.py authorization decorators!")
