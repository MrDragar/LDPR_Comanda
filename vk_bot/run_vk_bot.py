import os

import certifi

ca_bundle = certifi.where()
os.environ.setdefault("SSL_CERT_FILE", ca_bundle)
os.environ.setdefault("REQUESTS_CA_BUNDLE", ca_bundle)

from src.main import main


if __name__ == "__main__":
    main()
