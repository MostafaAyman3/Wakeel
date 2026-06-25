import sys
import os
import uvicorn
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Add the src directory to the system path so imports work correctly
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# Import the app from src.main
# We use a try-except block to handle potential import errors gracefully during setup
try:
    from src.main import app
except ImportError as e:
    print(f"Error importing app: {e}")
    print("Make sure the 'src' directory exists and contains 'main.py'.")
    sys.exit(1)

def ensure_ssl_certs(cert_path="cert.pem", key_path="key.pem"):
    """Generates self-signed certificates if they don't exist."""
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return True

    print("Generating self-signed SSL certificates for development...")
    try:
        # Generate private key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Generate a self-signed certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            # Use bot-hosting identifier in cert if possible, or just localhost
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Mini-RAG Development"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.DNSName("127.0.0.1")]),
            critical=False,
        ).sign(key, hashes.SHA256())

        # Write private key
        with open(key_path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))

        # Write certificate
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"Successfully generated certificates: {cert_path}, {key_path}")
        return True
    except Exception as e:
        print(f"Failed to generate SSL certificates: {e}")
        return False

if __name__ == "__main__":
    # Get the port from environment variable or default to 20905
    try:
        port = int(os.environ.get("PORT", 20905))
    except ValueError:
        port = 20905

    cert_path = "cert.pem"
    key_path = "key.pem"
    
    # Try to ensure certs exist before starting uvicorn
    if ensure_ssl_certs(cert_path, key_path):
        print(f"Starting server with HTTPS on port {port}...")
        uvicorn.run(app, host="0.0.0.0", port=port, ssl_certfile=cert_path, ssl_keyfile=key_path)
    else:
        print(f"Starting server with HTTP on port {port} (SSL setup failed or skipped)...")
        uvicorn.run(app, host="0.0.0.0", port=port)
