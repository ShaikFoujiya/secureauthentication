from flask import Flask, request, jsonify, send_file, render_template, session, send_from_directory, redirect
from flask_cors import CORS
import mysql.connector
import bcrypt
import numpy as np
from PIL import Image
import io
import base64
import os

# Import DeepFace conditionally to avoid startup issues
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: DeepFace not available: {e}")
    DEEPFACE_AVAILABLE = False

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this in production
CORS(app)  # Allow cross-origin requests from frontend

# MySQL config
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "secure"
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# Allowed image types
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def image_bytes_to_np(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return np.array(img)
    except:
        return None


def get_embedding(image_bytes):
    if not DEEPFACE_AVAILABLE:
        raise Exception("DeepFace not available")
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    embedding = DeepFace.represent(img_path=np.array(img), model_name="Facenet")[0]["embedding"]
    return np.array(embedding, dtype=np.float32)


def compare_embeddings(a, b):
    return np.linalg.norm(a - b)

# ---------------- Register User ----------------
@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    face_image_base64 = request.form.get("face_image_base64")

    if not all([username, email, password, face_image_base64]):
        return jsonify({"status": "error", "message": "All fields are required"}), 400

    # Decode and save the image
    try:
        header, encoded = face_image_base64.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        os.makedirs("faces", exist_ok=True)
        image_path = f"faces/registered_face_{username}.jpg"
        with open(image_path, "wb") as f:
            f.write(image_bytes)
    except Exception:
        return jsonify({"status": "error", "message": "Invalid face image"}), 400

    # Hash password
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Store in MySQL (save image path)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password, image_path) VALUES (%s, %s, %s, %s)",
            (username, email, hashed_pw, image_path)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": "User registered successfully"})
    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")


# ---------------- Login User ----------------
@app.route("/login_email", methods=["POST"])
def login_email():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    username = request.form.get("username", "").strip()

    # Validate all fields are provided
    if not email or not password or not username:
        return jsonify({"error": "All fields (email, password, username) are required"}), 400

    # Validate email format
    import re
    email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_pattern, email):
        return jsonify({"error": "Please enter a valid email address"}), 400

    # Validate password length
    if len(password) < 3:
        return jsonify({"error": "Password must be at least 3 characters long"}), 400

    # Validate username length
    if len(username) < 2:
        return jsonify({"error": "Username must be at least 2 characters long"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists with exact email and username match
        cursor.execute("SELECT username, password, role FROM users WHERE email=%s AND username=%s", (email, username))
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            return jsonify({"error": "Invalid credentials. Please check your email, username, and password"}), 401

        stored_username, hashed_pw, user_role = user
        
        # Ensure hashed_pw is bytes for bcrypt
        if isinstance(hashed_pw, str):
            hashed_pw = hashed_pw.encode('utf-8')
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), hashed_pw):
            cursor.close()
            conn.close()
            return jsonify({"error": "Invalid credentials. Please check your email, username, and password"}), 401

        cursor.close()
        conn.close()
        
        # Store user info in session for face login
        session['username'] = stored_username
        session['email'] = email
        session['role'] = user_role or 'user'  # Default to 'user' if role is None
        
        # For admin users, redirect directly to dashboard (skip face verification)
        if user_role == 'admin':
            return jsonify({"status": "success", "message": f"Admin login successful for {stored_username}", "redirect": "/dashboard"})
        
        return jsonify({"status": "success", "message": f"Login successful for {stored_username}", "redirect": "/loginface"})
        
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {str(err)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Login error: {str(e)}"}), 500


@app.route("/login_face", methods=["POST"])
def login_face():
    # Clear any existing session to avoid conflicts
    session.clear()
    
    # Get username ONLY from form data (ignore session completely for face verification)
    username = request.form.get("username", "").strip()
    face_image_base64 = request.form.get("face_image_base64")
    
    print(f"=== FACE VERIFICATION REQUEST ===")
    print(f"Form username: '{request.form.get('username', '')}'")
    print(f"Final username: '{username}'")
    print(f"Username length: {len(username)}")
    print(f"Face image provided: {bool(face_image_base64)}")
    print(f"Request URL: {request.url}")
    print(f"All form data: {dict(request.form)}")
    print(f"=================================")

    # Validate input
    if not username or not face_image_base64:
        return jsonify({"status": "error", "message": "Username and face image are required"}), 400

    if len(username) < 2:
        return jsonify({"status": "error", "message": "Username must be at least 2 characters long"}), 400
    
    # Quick check if user exists in database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE username=%s", (username,))
        user_exists = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user_exists:
            print(f"User '{username}' not found in database during initial check")
            return jsonify({"status": "error", "message": f"User '{username}' not found. Please check your username or register first."}), 404
    except Exception as e:
        print(f"Error checking user existence: {e}")
        return jsonify({"status": "error", "message": "Database error during user validation"}), 500

    # Decode and save the login face image
    try:
        if "," not in face_image_base64:
            return jsonify({"status": "error", "message": "Invalid image format"}), 400
            
        header, encoded = face_image_base64.split(",", 1)
        if not header.startswith("data:image/"):
            return jsonify({"status": "error", "message": "Invalid image data format"}), 400
            
        image_bytes = base64.b64decode(encoded)
        if len(image_bytes) < 1000:  # Minimum image size check
            return jsonify({"status": "error", "message": "Image too small or corrupted"}), 400
            
        os.makedirs("faces", exist_ok=True)
        login_image_path = f"faces/login_face_{username}.jpg"
        with open(login_image_path, "wb") as f:
            f.write(image_bytes)
            
        print(f"Login face image saved: {login_image_path}")
        
    except Exception as e:
        print(f"Image processing error: {e}")
        return jsonify({"status": "error", "message": "Failed to process face image. Please try again."}), 400

    # Get registered image path from DB
    try:
        print(f"Looking for user in database: '{username}'")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Debug: Check if user exists at all
        cursor.execute("SELECT username, email, image_path, role FROM users WHERE username=%s", (username,))
        row = cursor.fetchone()
        
        if not row:
            # Debug: Check all users in database
            cursor.execute("SELECT username FROM users")
            all_users = cursor.fetchall()
            print(f"All users in database: {[user[0] for user in all_users]}")
            print(f"Username being searched: '{username}' (length: {len(username)})")
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": f"User '{username}' not found. Please check your username."}), 404
            
        registered_image_path = row[2]  # image_path is the 3rd column
        user_role = row[3] or 'user'  # role is the 4th column
        print(f"Found user: {row[0]}, email: {row[1]}, image_path: {registered_image_path}, role: {user_role}")
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"status": "error", "message": "Database error. Please try again."}), 500

    # Check if DeepFace is available
    if not DEEPFACE_AVAILABLE:
        return jsonify({"status": "error", "message": "Face recognition not available. Please use email/password login."}), 500
    
    # Check if both image files exist
    if not os.path.exists(registered_image_path):
        return jsonify({"status": "error", "message": "Registered face image not found. Please register again."}), 404
    
    if not os.path.exists(login_image_path):
        return jsonify({"status": "error", "message": "Login face image not found. Please try again."}), 404

    # Use DeepFace to verify with optimized single model approach
    try:
        print("Starting face verification...")
        
        # Use the fastest and most reliable combination with strict verification
        try:
            print(f"Verifying face for user: {username}")
            print(f"Registered image: {registered_image_path}")
            print(f"Login image: {login_image_path}")
            
            result = DeepFace.verify(
                img1_path=registered_image_path,
                img2_path=login_image_path,
                model_name='Facenet',  # Fast and accurate
                detector_backend='opencv',  # Fastest backend
                enforce_detection=False,  # More lenient face detection
                distance_metric='cosine',
                threshold=0.6  # More lenient threshold (higher = more lenient)
            )
            
            print(f"Verification result: {result}")
            print(f"Distance: {result.get('distance', 'N/A')}")
            print(f"Threshold: {result.get('threshold', 'N/A')}")
            print(f"Verified: {result.get('verified', 'N/A')}")
            
            # Additional security check - ensure distance is within acceptable range
            distance = result.get('distance', 1.0)
            threshold = result.get('threshold', 0.4)
            
            if result["verified"] and distance <= threshold:
                print(f"Face verification successful for {username}!")
                # Set session for successful face login
                session['username'] = username
                session['role'] = user_role
                # Get email from database for session
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT email FROM users WHERE username=%s", (username,))
                    user_row = cursor.fetchone()
                    if user_row:
                        session['email'] = user_row[0]
                    cursor.close()
                    conn.close()
                except Exception as e:
                    print(f"Error getting email for session: {e}")
                
                return jsonify({"status": "success", "message": f"Face recognized successfully for {username}!"})
            else:
                print(f"Face not verified for {username}. Distance: {distance}, Threshold: {threshold}")
                return jsonify({"status": "error", "message": f"Face not recognized for {username}. Please try again or use email/password login."}), 401
                
        except Exception as primary_error:
            print(f"Primary verification failed: {primary_error}")
            # Quick fallback with VGG-Face (also strict)
            try:
                print(f"Trying fallback verification for {username}...")
                result = DeepFace.verify(
                    img1_path=registered_image_path,
                    img2_path=login_image_path,
                    model_name='VGG-Face',
                    detector_backend='opencv',
                    enforce_detection=False,
                    threshold=0.6
                )
                
                print(f"Fallback verification result: {result}")
                distance = result.get('distance', 1.0)
                threshold = result.get('threshold', 0.6)
                
                if result["verified"] and distance <= threshold:
                    print(f"Fallback face verification successful for {username}!")
                    # Set session for successful face login
                    session['username'] = username
                    session['role'] = user_role
                    # Get email from database for session
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT email FROM users WHERE username=%s", (username,))
                        user_row = cursor.fetchone()
                        if user_row:
                            session['email'] = user_row[0]
                        cursor.close()
                        conn.close()
                    except Exception as e:
                        print(f"Error getting email for session: {e}")
                    
                    return jsonify({"status": "success", "message": f"Face recognized successfully for {username}!"})
                else:
                    print(f"Fallback face not verified for {username}. Distance: {distance}, Threshold: {threshold}")
                    return jsonify({"status": "error", "message": f"Face not recognized for {username}. Please try again or use email/password login."}), 401
                    
            except Exception as fallback_error:
                print(f"Fallback verification failed: {fallback_error}")
                return jsonify({"status": "error", "message": "Face recognition failed. Please try again or use email/password login."}), 401
            
    except Exception as e:
        print(f"DeepFace verification error: {e}")
        return jsonify({"status": "error", "message": "Face recognition is temporarily unavailable. Please use email/password login."}), 500


@app.route("/")
def home():
    return render_template("login.html")

@app.route("/loginface")
def loginface():
    # Get username from session or URL parameter
    username = session.get('username') or request.args.get('username')
    
    if not username:
        return jsonify({"error": "Username is required. Please login first or provide username parameter."}), 400
    
    return render_template("loginface.html", username=username)


@app.route("/dashboard")
def dashboard():
    """Role-based dashboard routing"""
    if 'username' not in session:
        return redirect("/")
    
    user_role = session.get('role', 'user')
    username = session.get('username', 'Unknown')
    email = session.get('email', 'Unknown')
    
    if user_role == 'admin':
        return redirect("/admin/users")
    else:
        return render_template("user_dashboard.html", 
                             username=username,
                             email=email,
                             role=user_role)

@app.route("/faces/<filename>")
def serve_face_image(filename):
    """Serve face images from the faces directory"""
    try:
        print(f"Serving face image: {filename}")
        return send_from_directory("faces", filename)
    except FileNotFoundError:
        print(f"Face image not found: {filename}, serving default avatar")
        return send_from_directory("static", "default-avatar.svg")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/clear-session")
def clear_session():
    """Clear all session data - useful for debugging"""
    session.clear()
    return jsonify({"status": "success", "message": "Session cleared"})

@app.route("/debug/users")
def debug_users():
    """Debug route to check all users in database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, email, image_path FROM users")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        
        user_list = []
        for user in users:
            user_list.append({
                "username": user[0],
                "email": user[1], 
                "image_path": user[2],
                "image_exists": os.path.exists(user[2]) if user[2] else False
            })
        
        return jsonify({"users": user_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/debug/face-test/<username>")
def debug_face_test(username):
    """Debug route to test face recognition with different settings"""
    try:
        # Get user's registered image
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT image_path FROM users WHERE username=%s", (username,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return jsonify({"error": f"User {username} not found"}), 404
        
        registered_image_path = row[0]
        if not os.path.exists(registered_image_path):
            return jsonify({"error": f"Image file not found: {registered_image_path}"}), 404
        
        # Test with different settings
        results = {}
        
        if DEEPFACE_AVAILABLE:
            try:
                # Test with lenient settings
                result = DeepFace.verify(
                    img1_path=registered_image_path,
                    img2_path=registered_image_path,  # Same image for testing
                    model_name='Facenet',
                    detector_backend='opencv',
                    enforce_detection=False,
                    threshold=0.6
                )
                results["lenient"] = result
                
                # Test with strict settings
                result = DeepFace.verify(
                    img1_path=registered_image_path,
                    img2_path=registered_image_path,
                    model_name='Facenet',
                    detector_backend='opencv',
                    enforce_detection=True,
                    threshold=0.4
                )
                results["strict"] = result
                
            except Exception as e:
                results["error"] = str(e)
        else:
            results["error"] = "DeepFace not available"
        
        return jsonify({
            "username": username,
            "image_path": registered_image_path,
            "results": results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/user/<int:user_id>")
def api_user_detail(user_id):
    """API endpoint to get specific user details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, image_path, created_at FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return jsonify({
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "image_path": user[3],
                "created_at": user[4].strftime("%Y-%m-%d %H:%M:%S") if user[4] else "N/A",
                "image_exists": os.path.exists(user[3]) if user[3] else False
            })
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/user/<int:user_id>", methods=["DELETE"])
def api_delete_user(user_id):
    """API endpoint to delete a user"""
    # Check if user is admin
    if session.get('role') != 'admin':
        return jsonify({"error": "Access denied. Admin privileges required."}), 403
    
    try:
        # Get user info first
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, image_path FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            return jsonify({"error": "User not found"}), 404
        
        username, image_path = user
        
        # Delete user from database
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        # Delete face image file if it exists
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as e:
                print(f"Warning: Could not delete image file {image_path}: {e}")
        
        return jsonify({"status": "success", "message": f"User {username} deleted successfully"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/user-profile")
def api_user_profile():
    """API endpoint to get current user's profile"""
    if 'username' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, email, image_path, role FROM users WHERE username = %s", (session['username'],))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return jsonify({
                "username": user[0],
                "email": user[1],
                "image_path": user[2],
                "role": user[3],
                "image_exists": os.path.exists(user[2]) if user[2] else False
            })
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/users", methods=["GET"])
def admin_users_page():
    """Admin page to manage users - Admin only"""
    if session.get('role') != 'admin':
        return redirect("/dashboard")
    
    return render_template("admin_dashboard.html", 
                         username=session.get('username', 'Unknown'),
                         email=session.get('email', 'Unknown'),
                         role=session.get('role', 'user'))
@app.route("/api/users")
def api_users():
    """API endpoint to get all users data - Admin only"""
    # Check if user is admin
    if session.get('role') != 'admin':
        return jsonify({"error": "Access denied. Admin privileges required."}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, image_path, role, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        
        user_list = []
        for user in users:
            user_list.append({
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "image_path": user[3],
                "role": user[4] or 'user',
                "created_at": user[5].strftime("%Y-%m-%d %H:%M:%S") if user[5] else "N/A",
                "image_exists": os.path.exists(user[3]) if user[3] else False
            })
        
        return jsonify({"users": user_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
