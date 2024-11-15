import bcrypt
import hashlib
import time

# Hash the password
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

# Verify password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# Generate SHA1 token with expiry
def generate_token(email: str) -> str:
    expiry_time = int(time.time()) + 3600  # 1 hour from now
    raw_token = f"{email}{expiry_time}".encode("utf-8")
    sha1_token = hashlib.sha1(raw_token).hexdigest()
    return f"{sha1_token}:{expiry_time}"

# Validate token
def validate_token(token: str) -> bool:
    try:
        sha1_token, expiry_time = token.split(":")
        expiry_time = int(expiry_time)
        if expiry_time < int(time.time()):
            return False  # Token expired
        return True  # Token valid
    except ValueError:
        return False  # Invalid token format
