#!/usr/bin/env python3
"""Mint the three local JWTs backend/.env needs for the local stack.
Run: python backend/scripts/mint_local_jwts.py >> backend/.env"""
import jwt

SECRET = "local-test-jwt-secret-32-bytes-minimum!!"
service = jwt.encode({"role": "service_role", "iss": "local", "exp": 9999999999}, SECRET, algorithm="HS256")
anon = jwt.encode({"role": "anon", "iss": "local", "exp": 9999999999}, SECRET, algorithm="HS256")
print("POSTGREST_URL=http://127.0.0.1:3000")
print(f"SUPABASE_JWT_SECRET={SECRET}")
print(f"SUPABASE_SERVICE_ROLE_KEY={service}")
print(f"SUPABASE_ANON_KEY={anon}")
print("AUTH_ENABLED=true")
