from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from functools import wraps
from flask_cors import CORS
import cx_Oracle
import hashlib
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from chatbot_service import get_chatbot

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_123')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_NAME'] = 'travel_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
CORS(app, 
     supports_credentials=True,
     resources={r"/api/*": {"origins": "*"}}
)

# Oracle Database Configuration
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_DSN = os.environ.get('DB_DSN', 'localhost:1521/XE')

# Connection Pool
pool = None

def init_session_pool():
    global pool
    try:
        pool = cx_Oracle.SessionPool(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN,
            min=2,
            max=5,
            increment=1,
            encoding="UTF-8"
        )
        print("Database connection pool created")
    except cx_Oracle.Error as error:
        print(f"Error creating pool: {error}")

def get_db_connection():
    """Get connection from pool"""
    global pool
    if pool is None:
        init_session_pool()
    
    if pool:
        try:
            return pool.acquire()
        except cx_Oracle.Error as error:
            print(f"Error acquiring connection: {error}")
            return None
    return None

@app.errorhandler(Exception)
def handle_exception(e):
    """Global error handler"""
    print(f"Global error: {e}")
    
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': str(e)}), 500
        
    return render_template('error.html', 
                         title='Something went wrong', 
                         message='We encountered an unexpected error. Please try again later.',
                         error_code=500), 500

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Login required'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"Admin check - Session: {session}")
        
        if 'user_id' not in session:
            print("No user_id in session")
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            return redirect(url_for('login_page'))
        
        if session.get('role') != 'admin':
            print(f"Role is {session.get('role')}, not admin")
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Admin access required'}), 403
            return render_template('error.html', title='Access Denied', message='You do not have permission to view this page.', error_code=403), 403
        
        print("Admin check passed")
        return f(*args, **kwargs)
    return decorated_function

def vendor_required(f):
    """Decorator to require vendor role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Login required'}), 401
            return redirect(url_for('login_page'))
        
        if session.get('role') not in ['vendor', 'admin']:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Vendor access required'}), 403
            return render_template('error.html', title='Access Denied', message='Only vendors can access this page.', error_code=403), 403
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def default():
    """Default route - redirect to login"""
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    """Login page"""
    return render_template('login.html')

@app.route('/register')
def register_page():
    """Register page"""
    return render_template('register.html')

@app.route('/index')
@login_required
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/about')
@login_required
def about():
    """About/Services page"""
    return render_template('about.html')

@app.route('/places')
@login_required
def places():
    """Places/Destinations page"""
    return render_template('places.html')

@app.route('/packages')
@login_required
def packages():
    """Packages page"""
    return render_template('packages.html')

@app.route('/contact')
@login_required
def contact():
    """Contact/Booking page"""
    return render_template('contact.html')

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard page"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login_page'))
    return render_template('admin.html')

@app.route('/api/destinations', methods=['GET'])
def get_destinations():
    """Fetch all destinations from database"""
    connection = None
    cursor = None
    try:
        print("=== Fetching destinations ===")
        connection = get_db_connection()
        if not connection:
            print("ERROR: Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        print("Database connected successfully")
        cursor = connection.cursor()
        
        # Query with TO_CHAR to convert CLOB to string
        cursor.execute("""
            SELECT destination_id, name, country, 
                   TO_CHAR(description) as description, 
                   image_url, created_at
            FROM destinations
            ORDER BY name
        """)
        
        columns = [col[0].lower() for col in cursor.description]
        destinations = []
        
        for row in cursor.fetchall():
            destination = dict(zip(columns, row))
            # Convert datetime to string if present
            if destination.get('created_at'):
                destination['created_at'] = destination['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            destinations.append(destination)
        
        print(f"Found {len(destinations)} destinations")
        print(f"Destinations data: {destinations}")
        return jsonify({'success': True, 'destinations': destinations}), 200
        
    except cx_Oracle.Error as error:
        print(f"Database error: {error}")
        return jsonify({'success': False, 'message': f'Database error: {str(error)}'}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Admin endpoints
@app.route('/api/admin/all-bookings', methods=['GET'])
@admin_required
def get_all_bookings():
    """Get all bookings across the platform (admin only)"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        cursor.execute("""
            SELECT b.booking_id, b.user_id, b.package_id, b.departure_date as travel_date, 
                   b.num_adults as adults, b.num_children as children, b.num_infants as infants,
                   b.total_price as total_amount, b.status, b.booking_date as created_at,
                   b.customer_full_name as full_name, b.customer_email as email, 
                   b.customer_phone as phone, p.name as package_name,
                   d.name as destination_name, vp.company_name as vendor_name
            FROM bookings b
            JOIN packages p ON b.package_id = p.package_id
            JOIN destinations d ON p.destination_id = d.destination_id
            JOIN vendor_profiles vp ON p.vendor_id = vp.vendor_id
            ORDER BY b.booking_date DESC
        """)
        
        columns = [col[0].lower() for col in cursor.description]
        bookings = []
        for row in cursor.fetchall():
            booking = dict(zip(columns, row))
            if booking.get('travel_date'):
                booking['travel_date'] = booking['travel_date'].strftime('%Y-%m-%d')
            if booking.get('created_at'):
                booking['created_at'] = booking['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if booking.get('total_amount'):
                booking['total_amount'] = float(booking['total_amount'])
            bookings.append(booking)
        
        return jsonify({'success': True, 'bookings': bookings}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/api/admin/pending-vendors', methods=['GET'])
@admin_required
def get_pending_vendors():
    """Get all pending vendor approvals"""
    print("=== get_pending_vendors called ===")  # Debug log
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            print("Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        query = """
            SELECT vp.vendor_id, vp.user_id, u.username, u.email, u.full_name, u.phone,
                   vp.company_name, vp.business_license, vp.verification_status, 
                   vp.created_at, vp.image_url
            FROM vendor_profiles vp
            JOIN users u ON vp.user_id = u.user_id
            WHERE vp.verification_status = 'pending'
            ORDER BY vp.created_at DESC
        """
        
        print(f"Executing query: {query}")
        cursor.execute(query)
        
        columns = [col[0].lower() for col in cursor.description]
        vendors = []
        
        for row in cursor.fetchall():
            vendor = dict(zip(columns, row))
            # Convert Oracle datetime to string
            if vendor.get('created_at'):
                try:
                    vendor['created_at'] = vendor['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                except:
                    vendor['created_at'] = str(vendor['created_at'])
            vendors.append(vendor)
        
        print(f"Found {len(vendors)} pending vendors")
        print(f"Vendors: {vendors}")
        
        return jsonify({'success': True, 'vendors': vendors}), 200
        
    except cx_Oracle.Error as error:
        print(f"Database error: {error}")
        return jsonify({'success': False, 'message': f'Database error: {str(error)}'}), 500
    except Exception as e:
        print(f"Error in get_pending_vendors: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/admin/approve-vendor/<int:vendor_id>', methods=['POST'])
@admin_required
def approve_vendor(vendor_id):
    """Approve a vendor"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Get user_id from vendor_id
        cursor.execute("""
            SELECT user_id FROM vendor_profiles 
            WHERE vendor_id = :vendor_id AND verification_status = 'pending'
        """, {'vendor_id': vendor_id})
        
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Vendor not found or already processed'}), 404
        
        user_id = result[0]
        
        # Update vendor status to verified
        cursor.execute("""
            UPDATE vendor_profiles 
            SET verification_status = 'verified'
            WHERE vendor_id = :vendor_id
        """, {'vendor_id': vendor_id})
        
        # Activate user account
        cursor.execute("""
            UPDATE users 
            SET is_active = 1
            WHERE user_id = :user_id
        """, {'user_id': user_id})
        
        connection.commit()
        
        print(f"Vendor {vendor_id} approved successfully")  # Debug log
        return jsonify({'success': True, 'message': 'Vendor approved successfully'}), 200
        
    except cx_Oracle.Error as error:
        if connection:
            connection.rollback()
        print(f"Database error: {error}")
        return jsonify({'success': False, 'message': f'Database error: {str(error)}'}), 500
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/admin/reject-vendor/<int:vendor_id>', methods=['POST'])
@admin_required
def reject_vendor(vendor_id):
    """Reject a vendor and delete their account"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Get user_id before deletion
        cursor.execute("""
            SELECT user_id FROM vendor_profiles 
            WHERE vendor_id = :vendor_id
        """, {'vendor_id': vendor_id})
        
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Vendor not found'}), 404
        
        user_id = result[0]
        
        # Delete vendor profile
        cursor.execute("""
            DELETE FROM vendor_profiles 
            WHERE vendor_id = :vendor_id
        """, {'vendor_id': vendor_id})
        
        # Delete user roles
        cursor.execute("""
            DELETE FROM user_roles 
            WHERE user_id = :user_id
        """, {'user_id': user_id})
        
        # Delete user account
        cursor.execute("""
            DELETE FROM users 
            WHERE user_id = :user_id
        """, {'user_id': user_id})
        
        connection.commit()
        
        print(f"Vendor {vendor_id} rejected and deleted")  # Debug log
        return jsonify({'success': True, 'message': 'Vendor rejected and removed'}), 200
        
    except cx_Oracle.Error as error:
        if connection:
            connection.rollback()
        print(f"Database error: {error}")
        return jsonify({'success': False, 'message': f'Database error: {str(error)}'}), 500
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Vendor endpoints
@app.route('/api/vendor/my-destinations', methods=['GET'])
@vendor_required
def get_vendor_destinations():
    """Get destinations submitted by current vendor"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        vendor_id = session.get('vendor_id')
        
        cursor.execute("""
            SELECT pd.pending_id, pd.vendor_id, pd.name, pd.country, 
                   TO_CHAR(pd.description) as description, pd.image_url, 
                   pd.status, pd.submitted_at, pd.reviewed_at,
                   vp.company_name
            FROM pending_destinations pd
            JOIN vendor_profiles vp ON pd.vendor_id = vp.vendor_id
            WHERE pd.vendor_id = :vendor_id
            ORDER BY pd.submitted_at DESC
        """, {'vendor_id': vendor_id})
        
        columns = [col[0].lower() for col in cursor.description]
        destinations = []
        
        for row in cursor.fetchall():
            dest = dict(zip(columns, row))
            if dest.get('submitted_at'):
                dest['submitted_at'] = dest['submitted_at'].strftime('%Y-%m-%d %H:%M:%S')
            if dest.get('reviewed_at') and dest['reviewed_at']:
                dest['reviewed_at'] = dest['reviewed_at'].strftime('%Y-%m-%d %H:%M:%S')
            destinations.append(dest)
        
        return jsonify({'success': True, 'destinations': destinations}), 200
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/vendor/my-pending-packages', methods=['GET'])
@vendor_required
def get_vendor_pending_packages():
    """Get pending packages submitted by current vendor"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        vendor_id = session.get('vendor_id')
        
        cursor.execute("""
            SELECT pp.pending_pkg_id, pp.vendor_id, pp.destination_id, pp.name,
                   TO_CHAR(pp.description) as description, pp.duration_days, pp.max_travelers,
                   TO_CHAR(pp.includes) as includes, pp.image_url, pp.adult_price,
                   pp.child_price, pp.infant_price, pp.economy_adult_price, 
                   pp.economy_child_price, pp.economy_infant_price,
                   pp.business_adult_price, pp.business_child_price, pp.business_infant_price,
                   pp.status, pp.submitted_at, pp.reviewed_at,
                   vp.company_name, d.name as destination_name, d.country
            FROM pending_packages pp
            JOIN vendor_profiles vp ON pp.vendor_id = vp.vendor_id
            JOIN destinations d ON pp.destination_id = d.destination_id
            WHERE pp.vendor_id = :vendor_id
            ORDER BY pp.submitted_at DESC
        """, {'vendor_id': vendor_id})
        
        columns = [col[0].lower() for col in cursor.description]
        packages = []
        
        for row in cursor.fetchall():
            pkg = dict(zip(columns, row))
            if pkg.get('submitted_at'):
                pkg['submitted_at'] = pkg['submitted_at'].strftime('%Y-%m-%d %H:%M:%S')
            if pkg.get('reviewed_at') and pkg['reviewed_at']:
                pkg['reviewed_at'] = pkg['reviewed_at'].strftime('%Y-%m-%d %H:%M:%S')
            if pkg.get('adult_price'):
                pkg['adult_price'] = float(pkg['adult_price'])
            packages.append(pkg)
        
        return jsonify({'success': True, 'packages': packages}), 200
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/api/vendor/my-packages', methods=['GET'])
@vendor_required
def get_vendor_packages():
    """Get packages created by the current vendor"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        vendor_id = session.get('vendor_id')
        
        cursor.execute("""
            SELECT p.package_id, p.destination_id, p.name, 
                   TO_CHAR(p.description) as description,
                   p.duration_days, p.max_travelers, TO_CHAR(p.includes) as includes,
                   p.image_url, p.adult_price, p.child_price, p.infant_price,
                   p.economy_adult_price, p.economy_child_price, p.economy_infant_price,
                   p.business_adult_price, p.business_child_price, p.business_infant_price,
                   p.is_active, p.created_at, d.name as destination_name, d.country
            FROM packages p
            JOIN destinations d ON p.destination_id = d.destination_id
            WHERE p.vendor_id = :vendor_id
            ORDER BY p.created_at DESC
        """, {'vendor_id': vendor_id})
        
        columns = [col[0].lower() for col in cursor.description]
        packages = []
        
        for row in cursor.fetchall():
            pkg = dict(zip(columns, row))
            if pkg.get('created_at'):
                pkg['created_at'] = pkg['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            # Convert numeric fields to float
            numeric_fields = ['adult_price', 'child_price', 'infant_price',
                            'economy_adult_price', 'economy_child_price', 'economy_infant_price',
                            'business_adult_price', 'business_child_price', 'business_infant_price']
            for field in numeric_fields:
                if pkg.get(field) is not None:
                    pkg[field] = float(pkg[field])
            packages.append(pkg)
        
        return jsonify({'success': True, 'packages': packages}), 200
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/vendor/update-package/<int:package_id>', methods=['PUT'])
@vendor_required
def update_vendor_package(package_id):
    """Update a package (only if it belongs to the vendor)"""
    connection = None
    cursor = None
    try:
        data = request.json
        vendor_id = session.get('vendor_id')
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Verify package belongs to this vendor
        cursor.execute("""
            SELECT vendor_id FROM packages WHERE package_id = :package_id
        """, {'package_id': package_id})
        
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Package not found'}), 404
        
        if result[0] != vendor_id:
            return jsonify({'success': False, 'message': 'Unauthorized: This package does not belong to you'}), 403
        
        # Update package
        cursor.execute("""
            UPDATE packages SET
                destination_id = :destination_id,
                name = :name,
                description = :description,
                duration_days = :duration_days,
                max_travelers = :max_travelers,
                includes = :includes,
                image_url = :image_url,
                adult_price = :adult_price,
                child_price = :child_price,
                infant_price = :infant_price,
                economy_adult_price = :economy_adult_price,
                economy_child_price = :economy_child_price,
                economy_infant_price = :economy_infant_price,
                business_adult_price = :business_adult_price,
                business_child_price = :business_child_price,
                business_infant_price = :business_infant_price
            WHERE package_id = :package_id
        """, {
            'package_id': package_id,
            'destination_id': data.get('destination_id'),
            'name': data.get('name'),
            'description': data.get('description'),
            'duration_days': data.get('duration_days'),
            'max_travelers': data.get('max_travelers'),
            'includes': data.get('includes'),
            'image_url': data.get('image_url'),
            'adult_price': data.get('adult_price'),
            'child_price': data.get('child_price'),
            'infant_price': data.get('infant_price'),
            'economy_adult_price': data.get('economy_adult_price'),
            'economy_child_price': data.get('economy_child_price'),
            'economy_infant_price': data.get('economy_infant_price'),
            'business_adult_price': data.get('business_adult_price'),
            'business_child_price': data.get('business_child_price'),
            'business_infant_price': data.get('business_infant_price')
        })
        
        connection.commit()
        return jsonify({'success': True, 'message': 'Package updated successfully'}), 200
        
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/vendor/delete-package/<int:package_id>', methods=['DELETE'])
@vendor_required
def delete_vendor_package(package_id):
    """Delete a package (only if it belongs to the vendor)"""
    connection = None
    cursor = None
    try:
        vendor_id = session.get('vendor_id')
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Verify package belongs to this vendor
        cursor.execute("""
            SELECT vendor_id FROM packages WHERE package_id = :package_id
        """, {'package_id': package_id})
        
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Package not found'}), 404
        
        if result[0] != vendor_id:
            return jsonify({'success': False, 'message': 'Unauthorized: This package does not belong to you'}), 403
        
        # Soft delete - set is_active to 0 instead of deleting
        cursor.execute("""
            UPDATE packages SET is_active = 0 
            WHERE package_id = :package_id
        """, {'package_id': package_id})
        
        connection.commit()
        return jsonify({'success': True, 'message': 'Package deleted successfully'}), 200
        
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/vendor/toggle-package/<int:package_id>', methods=['POST'])
@vendor_required
def toggle_package_status(package_id):
    """Toggle package active status (enable/disable)"""
    connection = None
    cursor = None
    try:
        vendor_id = session.get('vendor_id')
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Verify package belongs to this vendor
        cursor.execute("""
            SELECT vendor_id, is_active FROM packages WHERE package_id = :package_id
        """, {'package_id': package_id})
        
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Package not found'}), 404
        
        if result[0] != vendor_id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        # Toggle status
        new_status = 0 if result[1] == 1 else 1
        
        cursor.execute("""
            UPDATE packages SET is_active = :status 
            WHERE package_id = :package_id
        """, {'status': new_status, 'package_id': package_id})
        
        connection.commit()
        
        status_text = 'activated' if new_status == 1 else 'deactivated'
        return jsonify({'success': True, 'message': f'Package {status_text} successfully'}), 200
        
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/api/vendor/add-destination', methods=['POST'])
@vendor_required
def vendor_add_destination():
    """Vendor submits destination for approval"""
    connection = None
    cursor = None
    try:
        data = request.json
        name = data.get('name', '').strip()
        country = data.get('country', '').strip()
        description = data.get('description', '').strip()
        image_url = data.get('image_url', '').strip()
        
        if not all([name, country, description]):
            return jsonify({'success': False, 'message': 'Name, country, and description are required'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        cursor.execute("""
            INSERT INTO pending_destinations (vendor_id, name, country, description, image_url, status)
            VALUES (:vendor_id, :name, :country, :description, :image_url, 'pending')
        """, {
            'vendor_id': session.get('vendor_id'),
            'name': name,
            'country': country,
            'description': description,
            'image_url': image_url if image_url else None
        })
        
        connection.commit()
        return jsonify({'success': True, 'message': 'Destination submitted for admin approval'}), 201
        
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/admin/pending-destinations', methods=['GET'])
@admin_required
def get_pending_destinations():
    """Get all pending destination approvals"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        cursor.execute("""
            SELECT pd.pending_id, pd.vendor_id, pd.name, pd.country, 
                   TO_CHAR(pd.description) as description, pd.image_url, 
                   pd.status, pd.submitted_at, vp.company_name
            FROM pending_destinations pd
            JOIN vendor_profiles vp ON pd.vendor_id = vp.vendor_id
            WHERE pd.status = 'pending'
            ORDER BY pd.submitted_at DESC
        """)
        
        columns = [col[0].lower() for col in cursor.description]
        destinations = []
        for row in cursor.fetchall():
            dest = dict(zip(columns, row))
            if dest.get('submitted_at'):
                dest['submitted_at'] = dest['submitted_at'].strftime('%Y-%m-%d %H:%M:%S')
            destinations.append(dest)
        
        return jsonify({'success': True, 'destinations': destinations}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/admin/approve-destination/<int:pending_id>', methods=['POST'])
@admin_required
def approve_destination(pending_id):
    """Approve a pending destination"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Get pending destination details
        cursor.execute("""
            SELECT vendor_id, name, country, description, image_url
            FROM pending_destinations
            WHERE pending_id = :pending_id AND status = 'pending'
        """, {'pending_id': pending_id})
        
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Destination not found'}), 404
        
        vendor_id, name, country, description, image_url = result
        
        # Insert into destinations table
        cursor.execute("""
            INSERT INTO destinations (name, country, description, image_url)
            VALUES (:name, :country, :description, :image_url)
        """, {
            'name': name,
            'country': country,
            'description': description,
            'image_url': image_url
        })
        
        # Update pending status
        cursor.execute("""
            UPDATE pending_destinations
            SET status = 'approved', reviewed_at = CURRENT_TIMESTAMP,
                reviewed_by = :admin_id
            WHERE pending_id = :pending_id
        """, {'admin_id': session.get('user_id'), 'pending_id': pending_id})
        
        connection.commit()
        return jsonify({'success': True, 'message': 'Destination approved'}), 200
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/admin/reject-destination/<int:pending_id>', methods=['POST'])
@admin_required
def reject_destination(pending_id):
    """Reject a pending destination"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE pending_destinations
            SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP,
                reviewed_by = :admin_id
            WHERE pending_id = :pending_id
        """, {'admin_id': session.get('user_id'), 'pending_id': pending_id})
        
        connection.commit()
        return jsonify({'success': True, 'message': 'Destination rejected'}), 200
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/vendor/add-package', methods=['POST'])
@vendor_required
def vendor_add_package():
    """Vendor submits package for approval"""
    connection = None
    cursor = None
    try:
        data = request.json
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO pending_packages (vendor_id, destination_id, name, description, 
                duration_days, max_travelers, includes, image_url, adult_price, child_price,
                infant_price, economy_adult_price, economy_child_price, economy_infant_price,
                business_adult_price, business_child_price, business_infant_price, status)
            VALUES (:vendor_id, :destination_id, :name, :description, :duration_days,
                :max_travelers, :includes, :image_url, :adult_price, :child_price, :infant_price,
                :economy_adult_price, :economy_child_price, :economy_infant_price,
                :business_adult_price, :business_child_price, :business_infant_price, 'pending')
        """, {
            'vendor_id': session.get('vendor_id'),
            'destination_id': data.get('destination_id'),
            'name': data.get('name'),
            'description': data.get('description'),
            'duration_days': data.get('duration_days'),
            'max_travelers': data.get('max_travelers'),
            'includes': data.get('includes'),
            'image_url': data.get('image_url'),
            'adult_price': data.get('adult_price'),
            'child_price': data.get('child_price'),
            'infant_price': data.get('infant_price'),
            'economy_adult_price': data.get('economy_adult_price'),
            'economy_child_price': data.get('economy_child_price'),
            'economy_infant_price': data.get('economy_infant_price'),
            'business_adult_price': data.get('business_adult_price'),
            'business_child_price': data.get('business_child_price'),
            'business_infant_price': data.get('business_infant_price')
        })
        
        connection.commit()
        return jsonify({'success': True, 'message': 'Package submitted for approval'}), 201
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/admin/pending-packages', methods=['GET'])
@admin_required
def get_pending_packages():
    """Get all pending package approvals"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        cursor.execute("""
            SELECT pp.pending_pkg_id, pp.vendor_id, pp.destination_id, pp.name,
                   TO_CHAR(pp.description) as description, pp.duration_days, pp.max_travelers,
                   TO_CHAR(pp.includes) as includes, pp.image_url, pp.adult_price,
                   pp.submitted_at, vp.company_name, d.name as destination_name
            FROM pending_packages pp
            JOIN vendor_profiles vp ON pp.vendor_id = vp.vendor_id
            JOIN destinations d ON pp.destination_id = d.destination_id
            WHERE pp.status = 'pending'
            ORDER BY pp.submitted_at DESC
        """)
        
        columns = [col[0].lower() for col in cursor.description]
        packages = []
        for row in cursor.fetchall():
            pkg = dict(zip(columns, row))
            if pkg.get('submitted_at'):
                pkg['submitted_at'] = pkg['submitted_at'].strftime('%Y-%m-%d %H:%M:%S')
            if pkg.get('adult_price'):
                pkg['adult_price'] = float(pkg['adult_price'])
            packages.append(pkg)
        
        return jsonify({'success': True, 'packages': packages}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/admin/approve-package/<int:pending_pkg_id>', methods=['POST'])
@admin_required
def approve_package(pending_pkg_id):
    """Approve a pending package"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Get pending package details
        cursor.execute("""
            SELECT vendor_id, destination_id, name, description, duration_days,
                   max_travelers, includes, image_url, adult_price, child_price,
                   infant_price, economy_adult_price, economy_child_price,
                   economy_infant_price, business_adult_price, business_child_price,
                   business_infant_price
            FROM pending_packages
            WHERE pending_pkg_id = :id AND status = 'pending'
        """, {'id': pending_pkg_id})
        
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Package not found'}), 404
        
        # Insert into packages table
        cursor.execute("""
            INSERT INTO packages (vendor_id, destination_id, name, description, duration_days,
                max_travelers, includes, image_url, adult_price, child_price, infant_price,
                economy_adult_price, economy_child_price, economy_infant_price,
                business_adult_price, business_child_price, business_infant_price, is_active)
            VALUES (:v1, :v2, :v3, :v4, :v5, :v6, :v7, :v8, :v9, :v10, :v11, :v12, :v13, :v14, :v15, :v16, :v17, 1)
        """, {
            'v1': result[0], 'v2': result[1], 'v3': result[2], 'v4': result[3],
            'v5': result[4], 'v6': result[5], 'v7': result[6], 'v8': result[7],
            'v9': result[8], 'v10': result[9], 'v11': result[10], 'v12': result[11],
            'v13': result[12], 'v14': result[13], 'v15': result[14], 'v16': result[15],
            'v17': result[16]
        })
        
        # Update pending status
        cursor.execute("""
            UPDATE pending_packages
            SET status = 'approved', reviewed_at = CURRENT_TIMESTAMP,
                reviewed_by = :admin_id
            WHERE pending_pkg_id = :id
        """, {'admin_id': session.get('user_id'), 'id': pending_pkg_id})
        
        connection.commit()
        return jsonify({'success': True, 'message': 'Package approved'}), 200
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/admin/reject-package/<int:pending_pkg_id>', methods=['POST'])
@admin_required
def reject_package(pending_pkg_id):
    """Reject a pending package"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE pending_packages
            SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP,
                reviewed_by = :admin_id
            WHERE pending_pkg_id = :id
        """, {'admin_id': session.get('user_id'), 'id': pending_pkg_id})
        
        connection.commit()
        return jsonify({'success': True, 'message': 'Package rejected'}), 200
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/vendor/bookings', methods=['GET'])
@vendor_required
def get_vendor_bookings():
    """Get all bookings for packages offered by the current vendor"""
    connection = None
    cursor = None
    try:
        print("=== Fetching vendor bookings ===")
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Get vendor's company name from session
        user_id = session.get('user_id')
        
        # First, get the vendor's company name
        cursor.execute("""
            SELECT company_name 
            FROM vendor_profiles 
            WHERE user_id = :user_id
        """, {'user_id': user_id})
        
        vendor_row = cursor.fetchone()
        if not vendor_row:
            return jsonify({'success': False, 'message': 'Vendor profile not found'}), 404
        
        vendor_company_name = vendor_row[0]
        print(f"Vendor company name: {vendor_company_name}")
        
        # Get all bookings where:
        # 1. The preferred_airline matches the vendor's company name, OR
        # 2. The package belongs to this vendor
        cursor.execute("""
            SELECT 
                b.booking_id,
                b.user_id,
                b.package_id,
                b.departure_date,
                b.return_date,
                b.num_adults,
                b.num_children,
                b.num_infants,
                b.num_travelers,
                b.total_price,
                b.status,
                b.booking_date as created_at,
                b.customer_full_name,
                b.customer_email,
                b.customer_phone,
                b.from_location,
                b.to_location,
                b.departure_time,
                b.return_time,
                b.preferred_airline,
                b.preferred_seating,
                b.fare_type,
                b.message as special_requests,
                b.payment_status,
                p.name as package_name,
                d.name as destination_name
            FROM bookings b
            LEFT JOIN packages p ON b.package_id = p.package_id
            LEFT JOIN destinations d ON p.destination_id = d.destination_id
            LEFT JOIN vendor_profiles v ON p.vendor_id = v.vendor_id
            WHERE UPPER(TRIM(b.preferred_airline)) = UPPER(TRIM(:company_name))
               OR UPPER(TRIM(v.company_name)) = UPPER(TRIM(:company_name))
            ORDER BY b.booking_date DESC
        """, {'company_name': vendor_company_name})
        
        columns = [col[0].lower() for col in cursor.description]
        print(f"DEBUG: Query columns: {columns}")
        bookings = []
        
        rows = cursor.fetchall()
        print(f"DEBUG: Fetched {len(rows)} raw rows")
        
        for row in rows:
            booking = dict(zip(columns, row))
            
            # Convert datetime fields to strings
            if booking.get('departure_date'):
                try:
                    booking['departure_date'] = booking['departure_date'].strftime('%Y-%m-%d')
                except:
                    booking['departure_date'] = str(booking['departure_date'])
            if booking.get('return_date'):
                try:
                    booking['return_date'] = booking['return_date'].strftime('%Y-%m-%d')
                except:
                    booking['return_date'] = str(booking['return_date'])
            if booking.get('created_at'):
                try:
                    booking['created_at'] = booking['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                except:
                    booking['created_at'] = str(booking['created_at'])
            
            # Convert numeric fields
            if booking.get('total_price'):
                booking['total_price'] = float(booking['total_price'])
            if booking.get('num_travelers'):
                booking['num_travelers'] = int(booking['num_travelers'])
            
            bookings.append(booking)
        
        print(f"Found {len(bookings)} bookings for vendor {vendor_company_name}")
        return jsonify({'success': True, 'bookings': bookings}), 200
        
    except cx_Oracle.Error as error:
        print(f"Database error: {error}")
        return jsonify({'success': False, 'message': f'Database error: {str(error)}'}), 500
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/api/vendor/bookings/<int:booking_id>/status', methods=['POST'])
@vendor_required
def update_booking_status(booking_id):
    """Update booking status (approve/reject)"""
    connection = None
    cursor = None
    try:
        data = request.get_json()
        new_status = data.get('status')
        # Support both 'message' from frontend and 'rejection_reason'
        rejection_reason = data.get('message') or data.get('rejection_reason', '')
        
        if new_status not in ['confirmed', 'cancelled', 'pending', 'completed']:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Get vendor's company name
        user_id = session.get('user_id')
        cursor.execute("""
            SELECT company_name 
            FROM vendor_profiles 
            WHERE user_id = :user_id
        """, {'user_id': user_id})
        
        vendor_row = cursor.fetchone()
        if not vendor_row:
            return jsonify({'success': False, 'message': 'Vendor profile not found'}), 404
        
        vendor_company_name = vendor_row[0]
        
        # Verify this booking belongs to this vendor
        cursor.execute("""
            SELECT b.booking_id 
            FROM bookings b
            LEFT JOIN packages p ON b.package_id = p.package_id
            LEFT JOIN vendor_profiles v ON p.vendor_id = v.vendor_id
            WHERE b.booking_id = :booking_id
              AND (UPPER(TRIM(b.preferred_airline)) = UPPER(TRIM(:company_name)) 
                   OR UPPER(TRIM(v.company_name)) = UPPER(TRIM(:company_name)))
        """, {'booking_id': booking_id, 'company_name': vendor_company_name})
        
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': 'Booking not found or unauthorized'}), 404
        
        # Update the booking status
        if new_status == 'cancelled':
            cursor.execute("""
                UPDATE bookings 
                SET status = :status, rejection_reason = :reason
                WHERE booking_id = :booking_id
            """, {'status': new_status, 'reason': rejection_reason, 'booking_id': booking_id})
        else:
            cursor.execute("""
                UPDATE bookings 
                SET status = :status
                WHERE booking_id = :booking_id
            """, {'status': new_status, 'booking_id': booking_id})
        
        connection.commit()
        
        status_text = {
            'confirmed': 'approved',
            'cancelled': 'rejected',
            'pending': 'set to pending',
            'completed': 'completed'
        }
        
        return jsonify({
            'success': True, 
            'message': f'Booking successfully {status_text[new_status]}'
        }), 200
        
    except cx_Oracle.Error as error:
        if connection:
            connection.rollback()
        print(f"Database error: {error}")
        return jsonify({'success': False, 'message': f'Database error: {str(error)}'}), 500
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/my-requests')
@login_required
def my_requests_page():
    """My Requests page for customers"""
    return render_template('my_requests.html')

@app.route('/api/customer/my-bookings', methods=['GET'])
@login_required
def get_my_bookings():
    """Get bookings for the logged-in customer"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        user_id = session.get('user_id')
        
        cursor.execute("""
            SELECT 
                b.booking_id,
                b.departure_date as travel_date,
                b.return_date,
                b.status,
                b.rejection_reason,
                b.booking_date as created_at,
                b.total_price,
                b.payment_status,
                p.name as package_name,
                p.image_url,
                d.name as destination_name,
                d.country,
                vp.company_name as vendor_name
            FROM bookings b
            JOIN packages p ON b.package_id = p.package_id
            JOIN destinations d ON p.destination_id = d.destination_id
            JOIN vendor_profiles vp ON p.vendor_id = vp.vendor_id
            WHERE b.user_id = :user_id
            ORDER BY b.booking_date DESC
        """, {'user_id': user_id})
        
        columns = [col[0].lower() for col in cursor.description]
        bookings = []
        
        for row in cursor.fetchall():
            booking = dict(zip(columns, row))
            
            # Format dates
            if booking.get('travel_date'):
                booking['travel_date'] = booking['travel_date'].strftime('%Y-%m-%d')
            if booking.get('return_date'):
                booking['return_date'] = booking['return_date'].strftime('%Y-%m-%d')
            if booking.get('created_at'):
                booking['created_at'] = booking['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if booking.get('total_price'):
                booking['total_price'] = float(booking.get('total_price'))
                
            bookings.append(booking)
        
        return jsonify({'success': True, 'bookings': bookings}), 200
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/highlights', methods=['GET'])
def get_highlights():
    """Fetch top 3 destinations for highlights section"""
    connection = None
    cursor = None
    try:
        print("=== Fetching highlights ===")
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT destination_id, name as city, country,
                   TO_CHAR(description) as description, 
                   image_url
            FROM destinations
            WHERE ROWNUM <= 3
            ORDER BY name
        """)
        
        columns = [col[0].lower() for col in cursor.description]
        highlights = []
        
        for row in cursor.fetchall():
            destination = dict(zip(columns, row))
            highlights.append(destination)
        
        print(f"Found {len(highlights)} highlights")
        return jsonify({'success': True, 'highlights': highlights}), 200
        
    except cx_Oracle.Error as error:
        print(f"Database error: {error}")
        return jsonify({'success': False, 'message': f'Database error: {str(error)}'}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/api/packages', methods=['GET'])
def get_packages():
    """Fetch all packages from database, optionally filtered by destination"""
    connection = None
    cursor = None
    try:
        print("=== Fetching packages ===")
        destination_id = request.args.get('destination_id')
        print(f"Destination filter: {destination_id}")
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = connection.cursor()
        
        # Build query with optional destination filter
        query = """
            SELECT 
                p.package_id,
                p.vendor_id,
                p.destination_id,
                p.name AS package_name,
                TO_CHAR(p.description) AS description,
                p.duration_days,
                p.max_travelers,
                TO_CHAR(p.includes) AS includes,
                p.image_url,
                p.is_active,
                p.adult_price,
                p.child_price,
                p.infant_price,
                p.economy_adult_price,
                p.economy_child_price,
                p.economy_infant_price,
                p.business_adult_price,
                p.business_child_price,
                p.business_infant_price,
                d.name AS destination_name,
                d.country,
                vp.company_name AS vendor_name,
                vp.rating AS vendor_rating,
                p.created_at
            FROM packages p
            JOIN destinations d ON p.destination_id = d.destination_id
            JOIN vendor_profiles vp ON p.vendor_id = vp.vendor_id
            WHERE p.is_active = 1
        """
        
        if destination_id:
            query += " AND p.destination_id = :dest_id"
            cursor.execute(query + " ORDER BY vp.company_name", {'dest_id': destination_id})
        else:
            cursor.execute(query + " ORDER BY d.name")

        columns = [c[0].lower() for c in cursor.description]
        packages = []
        
        for row in cursor.fetchall():
            pkg = dict(zip(columns, row))
            if pkg.get('created_at'):
                pkg['created_at'] = pkg['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            # Convert all numeric fields to float
            numeric_fields = ['price', 'vendor_rating', 'adult_price', 'child_price', 'infant_price',
                            'economy_adult_price', 'economy_child_price', 'economy_infant_price',
                            'business_adult_price', 'business_child_price', 'business_infant_price']
            for field in numeric_fields:
                if pkg.get(field) is not None:
                    pkg[field] = float(pkg[field])
            packages.append(pkg)

        print(f"Found {len(packages)} packages")
        return jsonify({'success': True, 'packages': packages}), 200

    except cx_Oracle.Error as error:
        print(f"Database error: {error}")
        return jsonify({'success': False, 'message': f'Database error: {str(error)}'}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    finally:
        if cursor: 
            cursor.close()
        if connection: 
            connection.close()

@app.route('/api/vendors', methods=['GET'])
def get_vendors():
    """Fetch all vendors from database"""
    connection = None
    cursor = None
    try:
        print("=== Fetching vendors ===")
        connection = get_db_connection()
        if not connection:
            print("ERROR: Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        print("Database connected successfully")
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT vendor_id, user_id, company_name, business_license, 
                   commission_rate, rating, verification_status, created_at, image_url
            FROM vendor_profiles
            ORDER BY rating DESC, company_name
        """)
        
        columns = [col[0].lower() for col in cursor.description]
        vendors = []
        
        for row in cursor.fetchall():
            vendor = dict(zip(columns, row))
            if vendor.get('created_at'):
                vendor['created_at'] = vendor['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if vendor.get('rating'):
                vendor['rating'] = float(vendor['rating'])
            if vendor.get('commission_rate'):
                vendor['commission_rate'] = float(vendor['commission_rate'])
            if vendor.get('image_url'):
                vendor['image_url'] = vendor['image_url'].replace('../static/', '/static/')
            vendors.append(vendor)
        
        print(f"Found {len(vendors)} vendors")
        return jsonify({'success': True, 'vendors': vendors}), 200
        
    except cx_Oracle.Error as error:
        print(f"Database error: {error}")
        return jsonify({'success': False, 'message': f'Database error: {str(error)}'}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/register', methods=['POST'])
def register():
    """Register new user with role-based approval"""
    connection = None
    cursor = None
    try:
        data = request.json
        full_name = data.get('full_name', '').strip()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()
        password = data.get('password', '')
        account_type = data.get('account_type', 'customer')  # 'customer' or 'vendor'
        
        # Validation
        if not all([full_name, username, email, phone, password]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Get ROLE_ID from USER_ROLES table based on account_type
        cursor.execute("""
            SELECT ROLE_ID FROM USER_ROLES WHERE ROLE_NAME = :role_name
        """, {'role_name': account_type})
        
        role_result = cursor.fetchone()
        if not role_result:
            return jsonify({'success': False, 'message': 'Invalid account type'}), 400
        
        role_id = role_result[0]
        
        # Check if username or email already exists
        cursor.execute("""
            SELECT USER_ID FROM USERS 
            WHERE USERNAME = :username OR EMAIL = :email
        """, {'username': username, 'email': email})
        
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Username or email already exists'}), 400

        # Secure password hashing
        password_hash = generate_password_hash(password)

        user_id_var = cursor.var(cx_Oracle.NUMBER)
        
        # Insert user with ROLE_ID and RETURNING clause
        cursor.execute("""
            INSERT INTO USERS (USERNAME, EMAIL, PASSWORD_HASH, FULL_NAME, PHONE, ROLE_ID, IS_ACTIVE, CREATED_AT)
            VALUES (:username, :email, :password_hash, :full_name, :phone, :role_id, :is_active, SYSDATE)
            RETURNING USER_ID INTO :user_id
        """, {
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'full_name': full_name,
            'phone': phone,
            'role_id': role_id,
            'is_active': 1 if account_type == 'customer' else 0,  # Vendors need admin approval
            'user_id': user_id_var
        })
        
        # Get the returned user_id
        user_id = user_id_var.getvalue()[0]
        
        # If vendor, create vendor profile with pending status
        if account_type == 'vendor':
            company_name = data.get('company_name', '').strip()
            business_license = data.get('business_license', '').strip()
            image_url = data.get('image_url', '').strip()
            
            if not company_name or not business_license:
                connection.rollback()
                return jsonify({'success': False, 'message': 'Company name and business license are required for vendors'}), 400
            
            cursor.execute("""
                INSERT INTO VENDOR_PROFILES (USER_ID, COMPANY_NAME, BUSINESS_LICENSE, 
                    COMMISSION_RATE, RATING, VERIFICATION_STATUS, CREATED_AT, IMAGE_URL)
                VALUES (:user_id, :company_name, :business_license, 10, 0, 'pending', SYSDATE, :image_url)
            """, {
                'user_id': user_id,
                'company_name': company_name,
                'business_license': business_license,
                'image_url': image_url if image_url else None
            })
            
            connection.commit()
            return jsonify({
                'success': True,
                'message': 'Vendor registration submitted! Your account will be activated after admin approval. You will receive an email notification.'
            }), 201
        
        connection.commit()
        return jsonify({
            'success': True,
            'message': 'Registration successful! You can now login.'
        }), 201
        
    except cx_Oracle.Error as error:
        if connection:
            connection.rollback()
        print(f"Database error: {error}")
        return jsonify({'success': False, 'message': f'Database error: {str(error)}'}), 500
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/login', methods=['POST'])
def login():
    """Login endpoint with role checking"""
    connection = None
    cursor = None
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Get user details including stored hash
        cursor.execute("""
            SELECT u.USER_ID, u.USERNAME, u.EMAIL, u.FULL_NAME, u.IS_ACTIVE, 
                   ur.ROLE_NAME, vp.VENDOR_ID, vp.VERIFICATION_STATUS, u.PASSWORD_HASH
            FROM USERS u
            JOIN USER_ROLES ur ON u.ROLE_ID = ur.ROLE_ID
            LEFT JOIN VENDOR_PROFILES vp ON u.USER_ID = vp.USER_ID
            WHERE u.USERNAME = :username
        """, {'username': username})
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        user_id, username_db, email, full_name, is_active, role_name, vendor_id, verification_status, stored_hash = user
        
        # Verify password (support both new and legacy hashes)
        verified = False
        password_needs_rehash = False
        
        # 1. Try secure check
        try:
            if check_password_hash(stored_hash, password):
                verified = True
        except:
            pass
            
        # 2. If not verified, try legacy SHA-256
        if not verified:
            legacy_hash = hashlib.sha256(password.encode()).hexdigest()
            if legacy_hash == stored_hash:
                verified = True
                password_needs_rehash = True
        
        if not verified:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
            
        # Migrate legacy hash to secure hash
        if password_needs_rehash:
            try:
                new_hash = generate_password_hash(password)
                cursor.execute("UPDATE USERS SET PASSWORD_HASH = :h WHERE USER_ID = :id", 
                             {'h': new_hash, 'id': user_id})
                connection.commit()
                print(f"Migrated password for user {username_db}")
            except Exception as e:
                print(f"Error migrating password: {e}")
        
        # Check if account is active
        if not is_active:
            if role_name == 'vendor':
                return jsonify({
                    'success': False,
                    'message': 'Your vendor account is pending admin approval. Please wait for activation email.'
                }), 403
            else:
                return jsonify({'success': False, 'message': 'Account is inactive'}), 403
        
        # Check vendor verification status
        if role_name == 'vendor' and verification_status != 'verified':
            return jsonify({
                'success': False,
                'message': f'Vendor account status: {verification_status}. Please contact admin.'
            }), 403
        
        # Update last login
        cursor.execute("""
            UPDATE USERS SET LAST_LOGIN = CURRENT_TIMESTAMP 
            WHERE USER_ID = :user_id
        """, {'user_id': user_id})
        connection.commit()
        
        session.permanent = True
        session['user_id'] = int(user_id)
        session['username'] = username_db
        session['email'] = email
        session['full_name'] = full_name
        session['role'] = role_name
        if vendor_id:
            session['vendor_id'] = int(vendor_id)
        
        # Determine redirect URL based on role
        redirect_url = '/admin' if role_name == 'admin' else '/index'
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'redirect': redirect_url,
            'user': {
                'user_id': int(user_id),
                'username': username_db,
                'email': email,
                'full_name': full_name,
                'role': role_name
            }
        }), 200
        
    except cx_Oracle.Error as error:
        print(f"Database error: {error}")
        return jsonify({'success': False, 'message': 'Database error occurred'}), 500
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'message': 'Login failed. Please try again.'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/api/session', methods=['GET'])
def check_session():
    """Check current session"""
    if 'user_id' in session:
        return jsonify({
            'success': True,
            'user': {
                'user_id': session.get('user_id'),
                'username': session.get('username'),
                'email': session.get('email'),
                'full_name': session.get('full_name'),
                'role': session.get('role'),
                'vendor_id': session.get('vendor_id')
            }
        }), 200
    return jsonify({'success': False, 'message': 'Not logged in'}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout endpoint"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200

@app.route('/api/user/profile', methods=['GET'])
def get_profile():
    """Get user profile"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT user_id, username, email, full_name, phone, created_at, last_login
            FROM users WHERE user_id = :user_id
        """, {'user_id': session['user_id']})
        
        user = cursor.fetchone()
        
        if user:
            return jsonify({
                'success': True,
                'user': {
                    'user_id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'full_name': user[3],
                    'phone': user[4],
                    'created_at': str(user[5]),
                    'last_login': str(user[6]) if user[6] else None
                }
            }), 200
        else:
            return jsonify({'success': False, 'message': 'User not found'}), 404
    
    except cx_Oracle.Error as error:
        print(f"Database error: {error}")
        return jsonify({'success': False, 'message': f'Database error: {str(error)}'}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    """Create a new booking from contact form"""
    try:
        print(f"=== BOOKING REQUEST ===")
        print(f"Session contents: {dict(session)}")
        
        user_id = session.get('user_id')
        print(f"User ID from session: {user_id}")
        
        if not user_id:
            print("ERROR: No user_id in session - user not logged in")
            return jsonify({
                'success': False, 
                'message': 'Please login to make a booking.'
            }), 401
        
        data = request.get_json()
        print(f"Booking data received: {data}")
        
        # Required fields including package_id and total_price
        required_fields = ['package_id', 'from_location', 'to_location', 'departure_date', 
                         'departure_time', 'preferred_airline', 'preferred_seating', 
                         'num_adults', 'fare_type', 'full_name', 'phone', 'email', 'total_price']
        
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Get and validate package_id
        try:
            package_id = int(data['package_id'])
            print(f"Package ID: {package_id}")
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid package selected'}), 400
        
        from_location = data['from_location'].strip()
        to_location = data['to_location'].strip()
        departure_date = data['departure_date'].strip()
        departure_time = data['departure_time'].strip()
        preferred_airline = data['preferred_airline']
        preferred_seating = data['preferred_seating']
        num_adults = int(data.get('num_adults', 1))
        num_children = int(data.get('num_children', 0))
        num_infants = int(data.get('num_infants', 0))
        fare_type = data['fare_type']
        return_date = data.get('return_date', '').strip() if fare_type == 'round_trip' else None
        return_time = data.get('return_time', '').strip() if fare_type == 'round_trip' else None
        message = data.get('message', '').strip()
        full_name = data['full_name'].strip()
        phone = data['phone'].strip()
        email = data['email'].strip().lower()
        total_price = float(data['total_price'])
        
        if '@' not in email or '.' not in email:
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400
        
        if fare_type == 'round_trip' and (not return_date or not return_time):
            return jsonify({'success': False, 'message': 'Return date and time required for round trip'}), 400
        
        total_travelers = num_adults + num_children + num_infants
        
        if total_travelers == 0:
            return jsonify({'success': False, 'message': 'At least one traveler is required'}), 400
        
        if total_price <= 0:
            return jsonify({'success': False, 'message': 'Invalid total price'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        try:
            # Verify package exists and get name
            cursor.execute("""
                SELECT package_id, name FROM packages WHERE package_id = :pkg_id
            """, {'pkg_id': package_id})
            
            package_row = cursor.fetchone()
            if not package_row:
                return jsonify({'success': False, 'message': 'Selected package not found'}), 404
            
            package_name = package_row[1]
            print(f"Total price from frontend: ${total_price}")
            
            booking_id_var = cursor.var(cx_Oracle.NUMBER)
            
            # Insert booking
            cursor.execute("""
                INSERT INTO bookings (
                    user_id, package_id, from_location, to_location,
                    departure_date, departure_time, return_date, return_time,
                    preferred_airline, preferred_seating,
                    num_adults, num_children, num_infants, num_travelers,
                    fare_type, message, total_price,
                    customer_full_name, customer_phone, customer_email,
                    status, booking_date
                ) VALUES (
                    :user_id, :package_id, :from_loc, :to_loc,
                    TO_DATE(:dep_date, 'YYYY-MM-DD'), :dep_time, 
                    TO_DATE(:ret_date, 'YYYY-MM-DD'), :ret_time,
                    :airline, :seating,
                    :adults, :children, :infants, :total,
                    :fare_type, :message, :total_price,
                    :full_name, :phone, :email,
                    'pending', SYSDATE
                ) RETURNING booking_id INTO :booking_id
            """, {
                'user_id': user_id,
                'package_id': package_id,
                'from_loc': from_location,
                'to_loc': to_location,
                'dep_date': departure_date,
                'dep_time': departure_time,
                'ret_date': return_date if return_date else None,
                'ret_time': return_time if return_time else None,
                'airline': preferred_airline,
                'seating': preferred_seating,
                'adults': num_adults,
                'children': num_children,
                'infants': num_infants,
                'total': total_travelers,
                'fare_type': fare_type,
                'message': message,
                'total_price': total_price,
                'full_name': full_name,
                'phone': phone,
                'email': email,
                'booking_id': booking_id_var
            })
            
            connection.commit()
            booking_id = booking_id_var.getvalue()[0]
            print(f"Booking created successfully! ID: {booking_id}")
            
            return jsonify({
                'success': True,
                'message': 'Booking submitted! Proceeding to payment...',
                'booking_id': int(booking_id),
                'total_price': total_price,
                'package_name': package_name
            }), 201
            
        except cx_Oracle.Error as error:
            connection.rollback()
            print(f"Database error: {error}")
            return jsonify({'success': False, 'message': f'Booking failed: {str(error)}'}), 500
        finally:
            cursor.close()
            connection.close()
            
    except ValueError as ve:
        print(f"ValueError: {ve}")
        return jsonify({'success': False, 'message': 'Invalid number format'}), 400
    except Exception as e:
        print(f"Error in booking: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/test-db', methods=['GET'])
def test_db():
    """Test database connection and check destinations"""
    connection = None
    cursor = None
    try:
        print("=== Testing database connection ===")
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Cannot connect to database'}), 500
        
        cursor = connection.cursor()
        
        # Test basic connection
        cursor.execute("SELECT 'Database connected!' FROM DUAL")
        result = cursor.fetchone()
        print(f"Connection test: {result[0]}")
        
        # Check if destinations table exists
        cursor.execute("""
            SELECT COUNT(*) FROM user_tables WHERE table_name = 'DESTINATIONS'
        """)
        table_exists = cursor.fetchone()[0]
        print(f"Destinations table exists: {table_exists > 0}")
        
        # Count destinations
        cursor.execute("SELECT COUNT(*) FROM destinations")
        dest_count = cursor.fetchone()[0]
        print(f"Number of destinations: {dest_count}")
        
        # Get sample destination
        cursor.execute("SELECT destination_id, name, country FROM destinations WHERE ROWNUM = 1")
        sample = cursor.fetchone()
        
        return jsonify({
            'success': True,
            'message': 'Database connection successful',
            'table_exists': table_exists > 0,
            'destination_count': dest_count,
            'sample_destination': {
                'id': sample[0],
                'name': sample[1],
                'country': sample[2]
            } if sample else None
        }), 200
        
    except cx_Oracle.Error as error:
        print(f"Database error: {error}")
        return jsonify({'success': False, 'message': f'Database error: {str(error)}'}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/api/chat', methods=['POST'])
def chat_with_ai():
    """AI Chatbot endpoint for travel assistance"""
    connection = None
    cursor = None
    try:
        data = request.json or {}
        user_message = data.get('message', '').strip()
        conversation_history = data.get('history', [])
        
        if not user_message:
            return jsonify({'success': False, 'message': 'Please enter a message'}), 400
        
        # Get chatbot instance
        chatbot = get_chatbot()
        
        # Fetch destinations and packages from database for context
        destinations = []
        packages = []
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            
            # Get destinations
            try:
                cursor.execute("""
                    SELECT destination_id, name, country, 
                           TO_CHAR(description) as description
                    FROM destinations
                    ORDER BY name
                """)
                columns = [col[0].lower() for col in cursor.description]
                for row in cursor.fetchall():
                    destinations.append(dict(zip(columns, row)))
            except Exception as e:
                print(f"Error fetching destinations for chatbot: {e}")
            
            # Get active packages with details
            try:
                cursor.execute("""
                    SELECT p.package_id, p.name, p.duration_days, p.adult_price,
                           d.name as destination_name, d.country,
                           TO_CHAR(p.description) as description,
                           vp.company_name as vendor_name
                    FROM packages p
                    JOIN destinations d ON p.destination_id = d.destination_id
                    JOIN vendor_profiles vp ON p.vendor_id = vp.vendor_id
                    WHERE p.is_active = 1
                    ORDER BY p.adult_price
                """)
                columns = [col[0].lower() for col in cursor.description]
                for row in cursor.fetchall():
                    pkg = dict(zip(columns, row))
                    if pkg.get('adult_price'):
                        pkg['adult_price'] = float(pkg['adult_price'])
                    packages.append(pkg)
            except Exception as e:
                print(f"Error fetching packages for chatbot: {e}")
        
        # Get AI response
        response = chatbot.chat(
            user_message=user_message,
            destinations=destinations,
            packages=packages,
            conversation_history=conversation_history
        )
        
        return jsonify(response), 200 if response.get('success') else 500
        
    except Exception as e:
        print(f"Chat endpoint error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Sorry, something went wrong. Please try again.'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/api/chat/suggestions', methods=['GET'])
def get_chat_suggestions():
    """Get quick reply suggestions for the chatbot"""
    try:
        context = request.args.get('context', '')
        chatbot = get_chatbot()
        suggestions = chatbot.get_quick_replies(context)
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        }), 200
    except Exception as e:
        print(f"Suggestions error: {e}")
        return jsonify({
            'success': True,
            'suggestions': [
                "🏖️ Beach destinations",
                "✈️ How to book?",
                "💰 Budget options"
            ]
        }), 200


@app.route('/api/ai/generate-description', methods=['POST'])
def generate_ai_description():
    """Generate AI-powered description for destinations or packages"""
    try:
        data = request.json or {}
        name = data.get('name', '').strip()
        country = data.get('country', '').strip()
        description_type = data.get('type', 'destination')
        additional_context = data.get('context', '')
        
        if not name:
            return jsonify({
                'success': False,
                'error': 'Please provide a destination name'
            }), 400
        
        if not country:
            return jsonify({
                'success': False,
                'error': 'Please provide a country'
            }), 400
        
        # Get chatbot instance and generate description
        chatbot = get_chatbot()
        result = chatbot.generate_description(
            name=name,
            country=country,
            description_type=description_type,
            additional_context=additional_context
        )
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'description': result.get('description')
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to generate description')
            }), 500
            
    except Exception as e:
        print(f"AI description error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Error generating description. Please try again.'
        }), 500


@app.route('/api/ai/recommend-packages', methods=['POST'])
@login_required
def get_ai_recommendations():
    """Smart Recommender endpoint using RAG approach"""
    connection = None
    cursor = None
    try:
        data = request.json or {}
        preferences = {
            'min_budget': data.get('min_budget', 0),
            'max_budget': data.get('max_budget', 5000),
            'interests': data.get('interests', []),
            'month': data.get('month', 'Any'),
            'duration': data.get('duration', 'Any'),
            'travelers': data.get('travelers', 1)
        }
        
        # Get chatbot instance
        chatbot = get_chatbot()
        
        # Fetch all active packages for context (RAG)
        packages = []
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT p.package_id, p.name as package_name, 
                       d.name as destination_name, d.country,
                       p.economy_adult_price, p.duration_days,
                       TO_CHAR(p.description) as description,
                       TO_CHAR(p.includes) as highlights
                FROM packages p
                JOIN destinations d ON p.destination_id = d.destination_id
                WHERE p.is_active = 1
            """)
            columns = [col[0].lower() for col in cursor.description]
            for row in cursor.fetchall():
                pkg = dict(zip(columns, row))
                # Convert price to float
                if pkg.get('economy_adult_price'):
                    pkg['economy_adult_price'] = float(pkg['economy_adult_price'])
                packages.append(pkg)
        
        if not packages:
            return jsonify({
                'success': False,
                'message': 'No packages available for recommendation at the moment.'
            }), 404
            
        # Get recommendations from AI
        recommendations = chatbot.recommend_packages(preferences, packages)
        
        return jsonify({
            'success': True,
            'recommendations': recommendations
        }), 200
        
    except Exception as e:
        print(f"Recommendation API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Error generating recommendations. Please try again.'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/api/ai/booking-assistant', methods=['POST'])
@login_required
def ai_booking_assistant():
    """
    Natural language booking search using AI intent extraction
    """
    connection = None
    cursor = None
    try:
        data = request.json
        user_query = data.get('query', '').strip()
        
        if not user_query:
            return jsonify({
                'success': False,
                'message': 'Please provide a search query'
            }), 400
        
        # Get chatbot instance
        chatbot = get_chatbot()
        
        # Extract booking intent using AI
        extracted_params = chatbot.extract_booking_intent(user_query)
        
        if not extracted_params:
            return jsonify({
                'success': False,
                'message': 'I couldn\'t understand your request. Try something like "Book a 5-day beach trip for 2 under $2000"'
            }), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
            
        cursor = connection.cursor()
        
        # Base query
        query = """
            SELECT 
                p.package_id,
                p.name as package_name,
                d.name as destination_name,
                d.country as destination_country,
                p.economy_adult_price as price,
                p.duration_days as duration,
                TO_CHAR(p.description) as description,
                TO_CHAR(p.includes) as highlights
            FROM packages p
            JOIN destinations d ON p.destination_id = d.destination_id
            WHERE p.is_active = 1
        """
        
        sql_params = {}
        conditions = []
        
        # Filter by destination type (fuzzy match on description or highlights)
        if extracted_params.get('destination_type') and extracted_params['destination_type'] != 'Any':
            dest_type = extracted_params['destination_type']
            conditions.append(
                "(LOWER(TO_CHAR(p.description)) LIKE :dest_type OR LOWER(TO_CHAR(p.includes)) LIKE :dest_type OR LOWER(d.name) LIKE :dest_type)"
            )
            sql_params['dest_type'] = f"%{dest_type.lower()}%"
        
        # Filter by specific destination name
        if extracted_params.get('destination_name'):
            conditions.append("LOWER(d.name) LIKE :dest_name")
            sql_params['dest_name'] = f"%{extracted_params['destination_name'].lower()}%"
        
        # Filter by duration (±1 day tolerance)
        if extracted_params.get('duration_days'):
            duration = extracted_params['duration_days']
            conditions.append("p.duration_days BETWEEN :min_duration AND :max_duration")
            sql_params['min_duration'] = max(1, duration - 1)
            sql_params['max_duration'] = duration + 1
        
        # Filter by budget (per person)
        if extracted_params.get('max_budget'):
            conditions.append("p.economy_adult_price <= :max_budget")
            sql_params['max_budget'] = extracted_params['max_budget']
        
        # Add conditions to query
        if conditions:
            query += " AND " + " AND ".join(conditions)
        
        query += " ORDER BY p.economy_adult_price ASC"
        
        # Execute query
        cursor.execute(query, sql_params)
        
        columns = [col[0].lower() for col in cursor.description]
        packages = []
        for row in cursor.fetchall():
            pkg = dict(zip(columns, row))
            # Convert price to float
            if pkg.get('price'):
                pkg['price'] = float(pkg['price'])
            packages.append(pkg)
        
        # Calculate total price based on travelers
        num_adults = extracted_params.get('adults', 1)
        num_children = extracted_params.get('children', 0)
        total_travelers = num_adults + num_children
        
        for pkg in packages:
            pkg['total_price'] = pkg['price'] * total_travelers
        
        # Limit to top 10 results
        packages = packages[:10]
        
        # Generate AI summary
        summary = chatbot.generate_search_summary(
            user_query, 
            extracted_params, 
            len(packages)
        )
        
        return jsonify({
            'success': True,
            'query': user_query,
            'extracted_params': extracted_params,
            'summary': summary,
            'packages': packages,
            'total_results': len(packages)
        }), 200
        
    except Exception as e:
        print(f"Error in booking assistant: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'An error occurred while searching. Please try again.'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/api/packages/<int:package_id>/reviews', methods=['GET'])
def get_reviews(package_id):
    """Get all reviews for a package"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = """
            SELECT 
                r.review_id,
                r.user_name,
                r.rating,
                r.created_at,
                u.username
            FROM reviews r
            LEFT JOIN users u ON r.user_id = u.user_id
            WHERE r.package_id = :package_id
            ORDER BY r.created_at DESC
        """
        
        cursor.execute(query, {'package_id': package_id})
        
        columns = [col[0].lower() for col in cursor.description]
        reviews = []
        for row in cursor.fetchall():
            rev = dict(zip(columns, row))
            # Format date
            if rev.get('created_at'):
                rev['created_at_formatted'] = rev['created_at'].strftime('%B %d, %Y')
            
            # Use username if available, else user_name
            rev['display_name'] = rev['username'] if rev.get('username') else (rev['user_name'] if rev.get('user_name') else 'Anonymous')
            reviews.append(rev)
        
        return jsonify({
            'success': True,
            'reviews': reviews,
            'total': len(reviews)
        })
        
    except Exception as e:
        print(f"Error fetching reviews: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to load reviews'
        }), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()


@app.route('/api/packages/<int:package_id>/reviews', methods=['POST'])
def submit_review(package_id):
    """Submit a new review"""
    connection = None
    cursor = None
    try:
        data = request.json
        rating = data.get('rating')
        if not rating or int(rating) not in [1, 2, 3, 4, 5]:
            return jsonify({
                'success': False,
                'message': 'Please provide a valid rating (1-5)'
            }), 400
        
        user_name = data.get('user_name', '').strip()
        if not user_name:
            user_name = 'Anonymous'
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Check if package exists
        cursor.execute("SELECT package_id FROM packages WHERE package_id = :id", {'id': package_id})
        if not cursor.fetchone():
            return jsonify({
                'success': False,
                'message': 'Package not found'
            }), 404
        
        # Determine user_id if logged in
        user_id = None
        if 'user_id' in session:
            user_id = session['user_id']
        
        # Get next ID explicitly
        cursor.execute("SELECT review_id_seq.NEXTVAL FROM DUAL")
        next_id = cursor.fetchone()[0]
        
        # Insert review
        cursor.execute("""
            INSERT INTO reviews (review_id, package_id, user_id, user_name, rating)
            VALUES (:rid, :pkg_id, :u_id, :name, :rating)
        """, {
            'rid': next_id,
            'pkg_id': package_id,
            'u_id': user_id,
            'name': user_name,
            'rating': int(rating)
        })
        
        connection.commit()
        return jsonify({
            'success': True,
            'message': 'Review submitted successfully!'
        })
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"DEBUG: Error submitting review: {error_msg}")
        traceback.print_exc()
        if connection: connection.rollback()
        return jsonify({
            'success': False,
            'message': f'Failed to submit review: {error_msg}'
        }), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()


@app.route('/api/ai/summarize-reviews/<int:package_id>', methods=['GET'])
def summarize_package_reviews(package_id):
    """Generate AI summary of all reviews for a package"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Get package name
        cursor.execute(
            "SELECT name FROM packages WHERE package_id = :id",
            {'id': package_id}
        )
        package_row = cursor.fetchone()
        if not package_row:
            return jsonify({
                'success': False,
                'message': 'Package not found'
            }), 404
        
        package_name = package_row[0]
        
        # Fetch reviews
        cursor.execute("""
            SELECT rating
            FROM reviews
            WHERE package_id = :id
            ORDER BY created_at DESC
        """, {'id': package_id})
        
        reviews = []
        for row in cursor.fetchall():
            reviews.append({
                'rating': row[0]
            })
        
        cursor.close()
        connection.close()
        
        # Get chatbot instance
        chatbot = get_chatbot()
        
        # Generate AI summary
        summary = chatbot.summarize_reviews(reviews, package_name)
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to generate summary'
        }), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()


def generate_transaction_id():
    """Generate a mock transaction ID"""
    import random
    import string
    prefix = 'TXN'
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    return f"{prefix}{random_part}"


@app.route('/api/bookings/<int:booking_id>/payment-info', methods=['GET'])
def get_payment_info(booking_id):
    """Get booking payment information"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = """
            SELECT 
                b.booking_id,
                b.total_price,
                b.payment_status,
                p.name as package_name,
                d.name as destination_name,
                b.num_adults,
                b.num_children,
                b.num_infants
            FROM bookings b
            JOIN packages p ON b.package_id = p.package_id
            JOIN destinations d ON p.destination_id = d.destination_id
            WHERE b.booking_id = :booking_id
        """
        
        cursor.execute(query, {'booking_id': booking_id})
        row = cursor.fetchone()
        
        if not row:
            return jsonify({
                'success': False,
                'message': 'Booking not found'
            }), 404
        
        return jsonify({
            'success': True,
            'booking': {
                'booking_id': row[0],
                'total_amount': float(row[1]) if row[1] else 0,
                'payment_status': row[2],
                'package_name': row[3],
                'destination': row[4],
                'travelers': {
                    'adults': row[5],
                    'children': row[6],
                    'infants': row[7]
                }
            }
        })
        
    except Exception as e:
        print(f"Error fetching payment info: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to load payment information'
        }), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()


@app.route('/api/bookings/<int:booking_id>/pay', methods=['POST'])
def process_payment(booking_id):
    """
    Process payment (simulator)
    """
    connection = None
    cursor = None
    try:
        data = request.json
        
        # Validate card details (basic simulation)
        card_number = data.get('card_number', '').replace(' ', '')
        card_holder = data.get('card_holder', '').strip()
        expiry_month = data.get('expiry_month')
        expiry_year = data.get('expiry_year')
        cvv = data.get('cvv', '')
        
        # Basic validation
        if len(card_number) != 16 or not card_number.isdigit():
            return jsonify({'success': False, 'message': 'Invalid card number'}), 400
        
        if not card_holder or len(card_holder) < 3:
            return jsonify({'success': False, 'message': 'Invalid cardholder name'}), 400
        
        if not expiry_month or not expiry_year:
            return jsonify({'success': False, 'message': 'Invalid expiry date'}), 400
        
        if len(cvv) != 3 or not cvv.isdigit():
            return jsonify({'success': False, 'message': 'Invalid CVV'}), 400
        
        # Simulate payment processing delay
        import time
        import random
        time.sleep(1.5)  # Simulate network delay
        
        # Simulate payment success (95% success rate for realism)
        payment_success = random.random() < 0.95
        
        if not payment_success:
            return jsonify({
                'success': False,
                'message': 'Payment declined. Please try a different card or contact your bank.'
            }), 400
        
        # Generate transaction ID
        transaction_id = generate_transaction_id()
        
        # Update booking with payment information
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # First, get the total amount
        cursor.execute(
            "SELECT total_price FROM bookings WHERE booking_id = :id",
            {'id': booking_id}
        )
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        total_price_val = result[0]
        
        # Update payment status
        cursor.execute("""
            UPDATE bookings
            SET payment_status = 'Paid',
                payment_method = :method,
                payment_date = CURRENT_TIMESTAMP,
                payment_transaction_id = :txn_id
            WHERE booking_id = :id
        """, {
            'method': f"Credit Card (****{card_number[-4:]})",
            'txn_id': transaction_id,
            'id': booking_id
        })
        
        connection.commit()
        
        return jsonify({
            'success': True,
            'message': 'Payment processed successfully!',
            'transaction_id': transaction_id,
            'amount': float(total_price_val) if total_price_val else 0,
            'payment_method': f"****{card_number[-4:]}"
        })
        
    except Exception as e:
        print(f"Error processing payment: {e}")
        if connection: connection.rollback()
        return jsonify({
            'success': False,
            'message': 'Payment processing failed. Please try again.'
        }), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()


@app.route('/api/bookings/<int:booking_id>/receipt', methods=['GET'])
def get_receipt(booking_id):
    """Get payment receipt details"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = """
            SELECT 
                b.booking_id,
                b.booking_date,
                b.departure_date,
                b.return_date,
                b.num_adults,
                b.num_children,
                b.num_infants,
                b.total_price,
                b.payment_status,
                b.payment_method,
                b.payment_date,
                b.payment_transaction_id,
                p.name as package_name,
                p.adult_price,
                p.duration_days,
                d.name as destination_name,
                d.country as destination_country,
                u.username,
                u.email
            FROM bookings b
            JOIN packages p ON b.package_id = p.package_id
            JOIN destinations d ON p.destination_id = d.destination_id
            LEFT JOIN users u ON b.user_id = u.user_id
            WHERE b.booking_id = :id
        """
        
        cursor.execute(query, {'id': booking_id})
        row = cursor.fetchone()
        
        if not row:
            return jsonify({
                'success': False,
                'message': 'Receipt not found'
            }), 404
        
        receipt = {
            'booking_id': row[0],
            'booking_date': row[1].strftime('%B %d, %Y') if row[1] else None,
            'departure_date': row[2].strftime('%B %d, %Y') if row[2] else None,
            'return_date': row[3].strftime('%B %d, %Y') if row[3] else None,
            'travelers': {
                'adults': row[4],
                'children': row[5],
                'infants': row[6]
            },
            'total_amount': float(row[7]) if row[7] else 0,
            'payment_status': row[8],
            'payment_method': row[9],
            'payment_date': row[10].strftime('%B %d, %Y %I:%M %p') if row[10] else None,
            'transaction_id': row[11],
            'package': {
                'name': row[12],
                'base_price': float(row[13]) if row[13] else 0,
                'duration': row[14],
                'destination': f"{row[15]}, {row[16]}"
            },
            'customer': {
                'name': row[17] if row[17] else 'Guest',
                'email': row[18] if row[18] else 'N/A'
            }
        }
        
        return jsonify({
            'success': True,
            'receipt': receipt
        })
        
    except Exception as e:
        print(f"Error fetching receipt: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to load receipt'
        }), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
