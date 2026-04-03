import os
from pathlib import Path
from datetime import datetime, timedelta

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class CertificateManager:

    def __init__(self, cert_dir=None):

        base_dir = Path(__file__).resolve().parent

        if cert_dir:
            self.cert_dir = Path(cert_dir)
        else:
            self.cert_dir = base_dir / "certs"

        self.cert_dir.mkdir(parents=True, exist_ok=True)

        # mitmproxy expected filenames
        self.key_path = self.cert_dir / "mitmproxy-ca.pem"
        self.cert_path = self.cert_dir / "browser_certificate.pem"
        self.cer_path = self.cert_dir / "android_certificate.cer"

    def generate_ca(self):
        """
        Generate CA only if it does not exist
        """

        if self.check_certificates():
            print("Certificates already exist, skipping generation.")
            return
            
        print("Generating new CA certificates...")

        # generate private key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "EG"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "xServer Magic"),
            x509.NameAttribute(NameOID.COMMON_NAME, "xServer Magic Proxy CA"),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=3650))
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )
            .sign(key, hashes.SHA256())
        )

        # save private key
        with open(self.key_path, "wb") as f:
            f.write(
                key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.TraditionalOpenSSL,
                    serialization.NoEncryption(),
                )
            )
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        # save PEM certificate
        with open(self.cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        # save CER (for android/windows)
        with open(self.cer_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.DER))

        print("CA certificate generated successfully.")
        print("Certificate directory:", self.cert_dir)


    def check_certificates(self):
        return (
            self.key_path.exists()
            and self.cert_path.exists()
            and self.cer_path.exists()
        )


    def remove_certificates(self):

        try:
            for file in [self.key_path, self.cert_path, self.cer_path]:
                if file.exists():
                    file.unlink()

            print("Certificates removed successfully.")
            return True

        except Exception as e:
            print("Error removing certificates:", e)
            return False


    def get_cert_dir(self):
        return str(self.cert_dir)

    def get_pem_path(self):
        return str(self.cert_path)

    def get_cer_path(self):
        return str(self.cer_path)

    def get_key_path(self):
        return str(self.key_path)



if __name__ == "__main__":

    manager = CertificateManager()

    manager.generate_ca()

    print("Key:", manager.get_key_path())
    print("Browser PEM:", manager.get_pem_path())
    print("Android CER:", manager.get_cer_path())
