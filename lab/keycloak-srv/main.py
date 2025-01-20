from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware      # type: ignore
from jose import jwt
from jose.exceptions import JWTError
import requests
from typing import Dict

# Keycloak Configuration
KEYCLOAK_ISSUER = "http://127.0.0.1:8080/realms/csa"
KEYCLOAK_AUDIENCE = "account"
KEYCLOAK_CERTS_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"

# Security Dependency
security = HTTPBearer()

# Fetch Keycloak Public Keys
def get_public_key(kid: str):
    try:
        response = requests.get(KEYCLOAK_CERTS_URL)
        response.raise_for_status()
        jwks = response.json()
        for key in jwks["keys"]:
            if key["kid"] == kid:
                # Return the key directly (RSA public key in JSON Web Key format)
                return key
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching public keys: {e}")
    raise HTTPException(status_code=401, detail="Public key not found")

# Decode and Verify JWT
def decode_token(token: str) -> Dict:
    try:
        # Get the unverified header to extract 'kid'
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="Token header missing 'kid'")
        
        # Fetch the public key from Keycloak using 'kid'
        public_key = get_public_key(kid)

        # Decode the token using the public key
        payload = jwt.decode(
            token,
            public_key,  # This is now the public key directly, no need for from_jwk
            algorithms=["RS256"],
            audience=KEYCLOAK_AUDIENCE,
            issuer=KEYCLOAK_ISSUER,
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token validation error: {e}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Error decoding token: {e}")

# Dependency for Secured Endpoints
def get_current_user(authorization: str = Depends(security)):
    try:
        token = authorization.credentials
        return decode_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Unauthorized: {e}")

# Example Endpoints
app = FastAPI()
#TODO: Improve security. CORS 
app = FastAPI()
origins = [
#    "http://localhost:3000",
    "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/secured")
async def secured_endpoint(current_user: dict = Depends(get_current_user)):
    return {"message": "Welcome to the secured endpoint!", "user": current_user}

@app.get("/public")
async def public_endpoint():
    return {"message": "Welcome to the public endpoint!"}
