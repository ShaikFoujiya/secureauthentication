# API Documentation - Secure Authentication System

## Overview

This document provides comprehensive API documentation for the Secure Authentication System. The API follows RESTful principles and uses JSON for data exchange.

## Base URL

```
http://127.0.0.1:5000
```

## Authentication

The system uses Flask sessions for authentication. After successful login, a session is created and maintained for subsequent requests.

## Content Types

- **Request**: `application/x-www-form-urlencoded` (for form data)
- **Response**: `application/json`

## Error Handling

All API endpoints return consistent error responses:

```json
{
    "status": "error",
    "message": "Error description"
}
```

## Endpoints

### 1. User Registration

#### POST /register

Register a new user with face image.

**Request Body:**
```
Content-Type: application/x-www-form-urlencoded

username: string (required, 2+ characters)
email: string (required, valid email format)
password: string (required, 3+ characters)
face_image_base64: string (required, base64 encoded image)
```

**Example Request:**
```bash
curl -X POST http://127.0.0.1:5000/register \
  -F "username=john_doe" \
  -F "email=john@example.com" \
  -F "password=securepass123" \
  -F "face_image_base64=data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
```

**Success Response (200):**
```json
{
    "status": "success",
    "message": "User registered successfully"
}
```

**Error Responses:**
- `400 Bad Request`: Missing fields or invalid data
- `500 Internal Server Error`: Database or server error

**Validation Rules:**
- Username: 2+ characters, unique
- Email: Valid email format, unique
- Password: 3+ characters
- Face image: Valid base64 encoded image, minimum size 1000 bytes

---

### 2. Email/Password Login

#### POST /login_email

Authenticate user with email, username, and password.

**Request Body:**
```
Content-Type: application/x-www-form-urlencoded

email: string (required, valid email format)
username: string (required, 2+ characters)
password: string (required)
```

**Example Request:**
```bash
curl -X POST http://127.0.0.1:5000/login_email \
  -F "email=john@example.com" \
  -F "username=john_doe" \
  -F "password=securepass123"
```

**Success Response (200):**
```json
{
    "status": "success",
    "message": "Login successful for john_doe",
    "redirect": "/loginface"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid input or validation errors
- `401 Unauthorized`: Invalid credentials
- `500 Internal Server Error`: Database or server error

**Session Creation:**
On successful login, the following session variables are set:
- `session['username']`: User's username
- `session['email']`: User's email

---

### 3. Face Recognition Login

#### POST /login_face

Verify user identity using face recognition.

**Request Body:**
```
Content-Type: application/x-www-form-urlencoded

username: string (required, 2+ characters)
face_image_base64: string (required, base64 encoded image)
```

**Example Request:**
```bash
curl -X POST http://127.0.0.1:5000/login_face \
  -F "username=john_doe" \
  -F "face_image_base64=data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
```

**Success Response (200):**
```json
{
    "status": "success",
    "message": "Face recognized successfully!"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid input or image processing error
- `401 Unauthorized`: Face not recognized
- `404 Not Found`: User not found
- `500 Internal Server Error`: Face recognition system error

**Face Recognition Process:**
1. Validates input parameters
2. Decodes and saves login face image
3. Retrieves registered face image from database
4. Uses DeepFace to compare images with multiple models:
   - VGG-Face
   - Facenet
   - ArcFace
5. Returns verification result

---

### 4. Page Endpoints

#### GET /

**Purpose:** Serve the login page
**Response:** HTML content (login.html)
**Authentication:** None required

#### GET /register

**Purpose:** Serve the registration page
**Response:** HTML content (register.html)
**Authentication:** None required

#### GET /loginface

**Purpose:** Serve the face verification page
**Response:** HTML content (loginface.html)
**Authentication:** Requires valid session

**Error Response (401):**
```json
{
    "error": "Please login first"
}
```

#### GET /dashboard

**Purpose:** Serve the user dashboard
**Response:** HTML content (dashboard.html)
**Authentication:** Requires valid session

**Template Variables:**
- `username`: User's username
- `email`: User's email
- `user_face_url`: URL to user's face image

**Error Response (401):**
```json
{
    "error": "Please complete login process"
}
```

**Error Response (500):**
```json
{
    "error": "Failed to load dashboard"
}
```

---

### 5. Asset Endpoints

#### GET /faces/<filename>

**Purpose:** Serve face images
**Parameters:**
- `filename`: Name of the face image file

**Example Request:**
```bash
curl http://127.0.0.1:5000/faces/registered_face_john_doe.jpg
```

**Success Response (200):**
- Content-Type: `image/jpeg` or `image/png`
- Body: Binary image data

**Fallback Response (404):**
- Serves default avatar if face image not found

---

### 6. Session Management

#### GET /logout

**Purpose:** Clear user session and log out
**Authentication:** None required (clears any existing session)

**Success Response (200):**
```json
{
    "status": "success",
    "message": "Logged out successfully"
}
```

---

## Face Recognition Models

The system uses multiple AI models for face recognition to ensure accuracy and compatibility:

### Supported Models
1. **VGG-Face**: High accuracy, good for general use
2. **Facenet**: Google's face recognition model
3. **ArcFace**: State-of-the-art face recognition

### Supported Backends
1. **OpenCV**: Fast, good for real-time processing
2. **RetinaFace**: High accuracy face detection
3. **MTCNN**: Multi-task CNN for face detection

### Verification Process
1. System tries each model-backend combination
2. Uses cosine similarity for distance calculation
3. Falls back to non-enforced detection if needed
4. Returns success if any combination verifies the face

---

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    image_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | INT | Primary key, auto-increment |
| username | VARCHAR(255) | Unique username (2+ characters) |
| email | VARCHAR(255) | Unique email address |
| password | VARCHAR(255) | bcrypt hashed password |
| image_path | VARCHAR(500) | Path to registered face image |
| created_at | TIMESTAMP | Account creation time |

---

## Security Considerations

### Password Security
- Passwords are hashed using bcrypt with salt
- Minimum password length: 3 characters
- Passwords are never stored in plain text

### Session Security
- Sessions use secure secret key
- Session data includes username and email
- Sessions are cleared on logout

### Input Validation
- All inputs are validated server-side
- Email format validation using regex
- Image size and format validation
- SQL injection prevention using parameterized queries

### Face Recognition Security
- Multiple model verification for accuracy
- Image quality validation
- Secure image storage and serving

---

## Rate Limiting

Currently, no rate limiting is implemented. For production deployment, consider implementing:

- Login attempt limiting
- Registration rate limiting
- API request throttling

---

## CORS Configuration

The API includes CORS (Cross-Origin Resource Sharing) support for frontend integration:

```python
from flask_cors import CORS
CORS(app)
```

---

## Error Codes Reference

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Authentication failed |
| 404 | Not Found - Resource not found |
| 500 | Internal Server Error - Server error |

---

## Example Integration

### JavaScript Frontend Integration

```javascript
// Login with email/password
async function loginWithEmail(email, username, password) {
    const formData = new FormData();
    formData.append('email', email);
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await fetch('/login_email', {
        method: 'POST',
        body: formData
    });
    
    const data = await response.json();
    
    if (data.status === 'success') {
        window.location.href = data.redirect;
    } else {
        alert(data.error || data.message);
    }
}

// Face recognition login
async function loginWithFace(username, faceImageBase64) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('face_image_base64', faceImageBase64);
    
    const response = await fetch('/login_face', {
        method: 'POST',
        body: formData
    });
    
    const data = await response.json();
    
    if (data.status === 'success') {
        window.location.href = '/dashboard';
    } else {
        alert(data.message || 'Face recognition failed');
    }
}
```

### Python Client Integration

```python
import requests

# Login with email/password
def login_with_email(email, username, password):
    data = {
        'email': email,
        'username': username,
        'password': password
    }
    
    response = requests.post('http://127.0.0.1:5000/login_email', data=data)
    return response.json()

# Face recognition login
def login_with_face(username, face_image_base64):
    data = {
        'username': username,
        'face_image_base64': face_image_base64
    }
    
    response = requests.post('http://127.0.0.1:5000/login_face', data=data)
    return response.json()
```

---

## Testing

### Unit Testing

```python
import unittest
import requests

class TestAuthenticationAPI(unittest.TestCase):
    def setUp(self):
        self.base_url = 'http://127.0.0.1:5000'
    
    def test_registration(self):
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass',
            'face_image_base64': 'data:image/jpeg;base64,test'
        }
        response = requests.post(f'{self.base_url}/register', data=data)
        self.assertEqual(response.status_code, 200)
    
    def test_login(self):
        data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'testpass'
        }
        response = requests.post(f'{self.base_url}/login_email', data=data)
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
```

---

## Version History

- **v1.0.0**: Initial release with basic authentication
- **v1.1.0**: Added face recognition
- **v1.2.0**: Enhanced security and error handling
- **v1.3.0**: Added session management and dashboard

---

## Support

For API support and questions:
- Check the troubleshooting section in README.md
- Review error messages and status codes
- Test with provided examples
- Create an issue on GitHub for bugs or feature requests
