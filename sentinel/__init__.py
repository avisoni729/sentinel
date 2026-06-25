# Make Python use the operating system's certificate verifier instead of its
# bundled OpenSSL. This lets HTTPS work even behind a TLS-intercepting proxy or
# antivirus whose CA the OS already trusts (common on shared/PG networks).
# Harmless on clean networks (incl. Streamlit Cloud).
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass
