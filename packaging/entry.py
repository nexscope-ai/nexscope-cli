"""Entry point for the standalone nexscope binary built by packaging/build.py."""
import os
import sys

# The bundled OpenSSL looks for CA certificates at the build machine's paths, which do not exist on
# users' machines; use certifi's bundle (as requests does) unless the user chose their own.
if not (os.environ.get('SSL_CERT_FILE') or os.environ.get('SSL_CERT_DIR')):
    import certifi

    os.environ['SSL_CERT_FILE'] = certifi.where()

if len(sys.argv) > 1 and sys.argv[1] == '--nexscope-runner':
    # `nexscope run` re-enters the binary here instead of calling a Python interpreter.
    from nexscope_cli import runner

    sys.argv = sys.argv[1:]
    runner.main()
else:
    from nexscope_cli.main import main

    sys.exit(main())
