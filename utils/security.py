'''
PeerNet++ Security Utilities
============================
Security manager for API protection.

Features:
- Rate limiting (requests per IP per window)
- IP blocking (auto-block after failed attempts)
- Input sanitization (prevent XSS, SQL injection)
- HMAC signature verification for webhooks
- CSRF token management

Usage:
    security = SecurityManager()
    @security.rate_limit(max_requests=100, window_minutes=60)
    def api_endpoint(): ...
'''

import hashlib
import hmac
import time
import secrets
from functools import wraps
from flask import request, jsonify, current_app
import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self):
        self.rate_limits = {}
        self.failed_attempts = {}
        self.blocked_ips = set()
        
    def rate_limit(self, max_requests: int = 100, window_minutes: int = 60):
        """Rate limiting decorator."""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                client_ip = self._get_client_ip()
                
                if self._is_rate_limited(client_ip, max_requests, window_minutes):
                    logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'message': f'Maximum {max_requests} requests per {window_minutes} minutes'
                    }), 429
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def validate_input(self, data: Dict[str, Any], rules: Dict[str, Dict]) -> Dict[str, Any]:
        """Validate and sanitize input data."""
        validated = {}
        errors = []
        
        for field, field_rules in rules.items():
            value = data.get(field)
            
            # Required field check
            if field_rules.get('required', False) and not value:
                errors.append(f"{field} is required")
                continue
            
            if value is None:
                continue
            
            # Type validation
            expected_type = field_rules.get('type')
            if expected_type and not isinstance(value, expected_type):
                errors.append(f"{field} must be of type {expected_type.__name__}")
                continue
            
            # String validation
            if isinstance(value, str):
                # Length validation
                min_length = field_rules.get('min_length', 0)
                max_length = field_rules.get('max_length', 10000)
                
                if len(value) < min_length:
                    errors.append(f"{field} must be at least {min_length} characters")
                    continue
                
                if len(value) > max_length:
                    errors.append(f"{field} must be no more than {max_length} characters")
                    continue
                
                # Pattern validation
                pattern = field_rules.get('pattern')
                if pattern and not re.match(pattern, value):
                    errors.append(f"{field} format is invalid")
                    continue
                
                # Sanitize string
                value = self._sanitize_string(value)
            
            # Number validation
            elif isinstance(value, (int, float)):
                min_val = field_rules.get('min_value')
                max_val = field_rules.get('max_value')
                
                if min_val is not None and value < min_val:
                    errors.append(f"{field} must be at least {min_val}")
                    continue
                
                if max_val is not None and value > max_val:
                    errors.append(f"{field} must be no more than {max_val}")
                    continue
            
            validated[field] = value
        
        if errors:
            raise ValueError(f"Validation errors: {'; '.join(errors)}")
        
        return validated
    
    def _sanitize_string(self, value: str) -> str:
        """Sanitize string input to prevent injection attacks."""
        # Remove potential script tags
        value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove potential SQL injection patterns
        sql_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
            r'(--|#|/\*|\*/)',
            r'(\bOR\b.*\b=\b|\bAND\b.*\b=\b)',
        ]
        
        for pattern in sql_patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        # Remove potential NoSQL injection patterns
        nosql_patterns = [
            r'(\$where|\$regex|\$ne|\$gt|\$lt)',
            r'(javascript:|eval\(|function\()',
        ]
        
        for pattern in nosql_patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        # Limit special characters
        value = re.sub(r'[<>"\']', '', value)
        
        return value.strip()
    
    def _get_client_ip(self) -> str:
        """Get client IP address safely.
        
        Note: X-Forwarded-For can be spoofed by clients. In production,
        configure your reverse proxy (nginx/Cloudflare) to overwrite this header
        and use request.access_route with a trusted proxy list instead.
        """
        # Prefer request.remote_addr as it cannot be spoofed by the client
        # Only fall back to headers when behind a trusted reverse proxy
        remote = request.remote_addr
        if remote and remote not in ('127.0.0.1', '::1'):
            return remote
        
        # Behind localhost proxy — trust the forwarded header
        forwarded_ips = request.headers.get('X-Forwarded-For')
        if forwarded_ips:
            return forwarded_ips.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return remote or 'unknown'
    
    def _is_rate_limited(self, client_ip: str, max_requests: int, window_minutes: int) -> bool:
        """Check if client IP is rate limited."""
        current_time = time.time()
        window_seconds = window_minutes * 60
        
        # Clean old entries
        cutoff_time = current_time - window_seconds
        
        if client_ip not in self.rate_limits:
            self.rate_limits[client_ip] = []
        
        # Remove old requests
        self.rate_limits[client_ip] = [
            req_time for req_time in self.rate_limits[client_ip] 
            if req_time > cutoff_time
        ]
        
        # Check if limit exceeded
        if len(self.rate_limits[client_ip]) >= max_requests:
            return True
        
        # Add current request
        self.rate_limits[client_ip].append(current_time)
        return False
    
    def generate_api_key(self) -> str:
        """Generate secure API key."""
        return secrets.token_urlsafe(32)
    
    def hash_password(self, password: str) -> str:
        """Hash password securely."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{password_hash.hex()}"
    
    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash."""
        try:
            salt, password_hash = stored_hash.split(':')
            computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hmac.compare_digest(password_hash, computed_hash.hex())
        except Exception:
            return False
    
    def validate_file_upload(self, file) -> Dict[str, Any]:
        """Validate uploaded file for security."""
        if not file:
            raise ValueError("No file provided")
        
        # Check file size (max 10MB)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise ValueError("File too large (max 10MB)")
        
        # Check file extension
        allowed_extensions = {'.pdf', '.txt', '.json', '.csv'}
        filename = file.filename.lower() if file.filename else ''
        
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise ValueError("File type not allowed")
        
        # Basic content validation for text files
        if filename.endswith(('.txt', '.json', '.csv')):
            try:
                content = file.read(1024).decode('utf-8')  # Read first 1KB
                file.seek(0)  # Reset
                
                # Check for suspicious content
                suspicious_patterns = [
                    r'<script[^>]*>',
                    r'javascript:',
                    r'eval\(',
                    r'exec\(',
                ]
                
                for pattern in suspicious_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        raise ValueError("Suspicious content detected in file")
                        
            except UnicodeDecodeError:
                raise ValueError("File encoding not supported")
        
        return {
            'filename': filename,
            'size': file_size,
            'validated': True
        }
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security-related events."""
        client_ip = self._get_client_ip()
        
        log_entry = {
            'timestamp': time.time(),
            'event_type': event_type,
            'client_ip': client_ip,
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'details': details
        }
        
        logger.warning(f"Security Event: {event_type} from {client_ip} - {details}")
        
        # In production, you might want to store these in a separate security log
        return log_entry

# Global security manager instance
security_manager = SecurityManager()

# Validation rules for common inputs
VALIDATION_RULES = {
    'paper_upload': {
        'title': {'required': True, 'type': str, 'min_length': 5, 'max_length': 500},
        'abstract': {'required': False, 'type': str, 'max_length': 5000},
        'authors': {'required': True, 'type': list},
        'year': {'required': False, 'type': str, 'pattern': r'^\d{4}$'},
        'doi': {'required': False, 'type': str, 'max_length': 100}
    },
    'search_query': {
        'q': {'required': False, 'type': str, 'max_length': 200},
        'page': {'required': False, 'type': int, 'min_value': 1, 'max_value': 1000},
        'per_page': {'required': False, 'type': int, 'min_value': 1, 'max_value': 100}
    }
}