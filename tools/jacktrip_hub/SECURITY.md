# JackTrip Hub Security Features

## Overview

The JackTrip Hub implements a comprehensive security model with authentication, encryption, and access control.

## Authentication System

### User Registration & Login
- **Bcrypt password hashing** - Passwords never stored in plaintext
- **SQLite database** - Persistent user accounts in `hub.db`
- **Session tokens** - Bearer token authentication for API requests
- **No default credentials** - Users must register before creating rooms

### Token-Based API Access
All room operations require a valid Bearer token:
```bash
Authorization: Bearer <your-token-here>
```

Tokens are returned from `/auth/register` and `/auth/login` endpoints.

## Transport Security

### HTTPS/TLS
- **Auto-generated certificates** for development (self-signed)
- **Production certificates** via environment variables
- **All traffic encrypted** - passwords never sent in plaintext
- **WebSocket Secure (WSS)** for real-time patchbay updates

### Certificate Setup

**Development:**
```bash
# Automatic - just run the server
python hub_server.py
# Certificate auto-generated at certs/cert.pem and certs/key.pem
```

**Production:**
```bash
# Use Let's Encrypt certificates
export SSL_CERTFILE=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
export SSL_KEYFILE=/etc/letsencrypt/live/yourdomain.com/privkey.pem
python hub_server.py
```

## Room Security

### Public vs Private Rooms
- **Public rooms** - Any authenticated user can join
- **Private rooms** - Require passphrase to join

### Room Passphrases
- Optional on room creation
- Hashed with bcrypt (never stored plaintext)
- Required for joining private rooms
- Room creator controls privacy level

Example creating a private room:
```bash
curl -k -X POST https://localhost:8000/rooms \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Private Jam",
    "passphrase": "secret123",
    "max_participants": 4
  }'
```

Example joining a private room:
```bash
curl -k -X POST https://localhost:8000/rooms/$ROOM_ID/join \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "passphrase": "secret123"
  }'
```

## Database Security

### SQLite Database (`hub.db`)

**Users Table:**
- `id` - UUID primary key
- `username` - Unique username
- `password_hash` - Bcrypt hashed password
- `email` - Optional email (not currently used)
- `created_at` - Account creation timestamp

**Sessions Table:**
- `token` - UUID session token (primary key)
- `user_id` - Foreign key to users
- `created_at` - Session creation time
- `expires_at` - Optional expiration (not currently implemented)

### Hashing Parameters
- **Bcrypt** with auto-generated salt
- Default work factor (12 rounds)
- One-way hashing (cannot be reversed)

## Best Practices

### For Administrators

1. **Use production certificates** - Never use self-signed certs in production
2. **Strong passwords** - Enforce password requirements if desired
3. **Regular backups** - Back up `hub.db` regularly
4. **Monitor logs** - Watch for suspicious activity
5. **Firewall rules** - Limit access to trusted networks if possible
6. **Update regularly** - Keep dependencies updated

### For Users

1. **Use strong passwords** - Long, unique passwords for your account
2. **Use passphrases for private rooms** - Don't share passphrases publicly
3. **Trust the certificate** - Verify certificate fingerprint on first connect
4. **Log out** - Token management (logout endpoint not yet implemented)

### For Developers

1. **Never log passwords** - Even hashed ones
2. **Validate inputs** - Check all user inputs
3. **Rate limiting** - Consider adding rate limits for API endpoints
4. **SQL injection** - Use parameterized queries (already done)
5. **XSS protection** - Sanitize any user-generated content in web interface

## Security Limitations

### Current Limitations

1. **No token expiration** - Sessions don't expire automatically yet
2. **No rate limiting** - No protection against brute force attempts
3. **No 2FA** - Two-factor authentication not implemented
4. **No email verification** - Registration doesn't verify email
5. **No password reset** - Lost passwords require manual database intervention
6. **No account deletion** - No self-service account deletion
7. **No session management** - Can't view/revoke active sessions

### Future Enhancements

- Token expiration and refresh
- Rate limiting per user/IP
- Optional 2FA (TOTP)
- Email verification
- Password reset flow
- Session management dashboard
- Account deletion
- Audit logging
- IP allowlist/blocklist

## Threat Model

### Protected Against

✅ Password interception (HTTPS encryption)  
✅ Password database theft (bcrypt hashing)  
✅ Unauthorized room creation (authentication required)  
✅ Private room access without passphrase  
✅ SQL injection (parameterized queries)  

### Not Protected Against

❌ Brute force attacks (no rate limiting)  
❌ Token theft if attacker has network access  
❌ Malicious room creators (no moderation)  
❌ DDoS attacks (no traffic shaping)  
❌ Compromised server (no client-side encryption)  

## Compliance Notes

- **GDPR**: Users can have accounts, but no automated deletion
- **Password storage**: Follows OWASP recommendations (bcrypt)
- **Transport security**: TLS 1.2+ recommended
- **Data retention**: No automatic cleanup of old sessions

## Reporting Security Issues

If you discover a security vulnerability, please email the maintainer directly rather than opening a public issue.

## Version History

- **v0.2.0** - Added HTTPS, bcrypt, user registration, room passphrases
- **v0.1.0** - Initial release (demo credentials only, HTTP)
