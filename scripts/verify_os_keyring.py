"""Check only an isolated acceptance credential, never an existing account."""
import argparse
import hashlib
import json
import re
import sys
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['probe', 'write', 'read', 'delete'])
    parser.add_argument('origin')
    parser.add_argument('--digest')
    args = parser.parse_args()
    if not re.fullmatch(r'https://nexscope-acceptance-[0-9a-f]{32}\.invalid', args.origin):
        raise ValueError('Only a unique fictional acceptance origin is allowed.')
    import keyring

    store = keyring.get_keyring()
    backend = type(store).__module__
    if args.action == 'probe':
        from nexscope_cli.core.errors import Failure
        from nexscope_cli.main import Client

        try:
            client = Client(args.origin)
            client.load('credential')
        except Failure:
            print(json.dumps({'status': 'UNAVAILABLE_FAIL_CLOSED', 'backend': backend}))
        except Exception as error:
            print(json.dumps({'status': 'UNAVAILABLE', 'backend': backend, 'errorType': type(error).__name__}))
        else:
            print(json.dumps({'status': 'AVAILABLE', 'backend': backend}))
        return
    if backend not in ('keyring.backends.Windows', 'keyring.backends.macOS',
                        'keyring.backends.SecretService', 'keyring.backends.kwallet'):
        raise ValueError('A supported real OS credential store is required.')
    service = 'nexscope-cli:' + args.origin
    if args.action == 'write':
        from nexscope_cli.main import Client

        client = Client(args.origin)
        if client.load('credential') is not None:
            raise ValueError('Acceptance namespace already exists; refusing to overwrite it.')
        value = {'apiKey': uuid.uuid4().hex, 'acceptanceOrigin': args.origin}
        try:
            client.save('credential', value)
            if client.load('credential') != value:
                raise ValueError('OS credential-store round trip changed the acceptance value.')
        except Exception:
            try:
                store.delete_password(service, 'credential')
            except Exception:
                pass
            raise
    else:
        raw = store.get_password(service, 'credential')
        value = json.loads(raw) if raw else None
    if not isinstance(value, dict) or value.get('acceptanceOrigin') != args.origin:
        raise ValueError('Acceptance credential is missing or has an unexpected owner marker.')
    digest = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    if args.action != 'write' and digest != args.digest:
        raise ValueError('Acceptance credential changed; refusing to delete or certify it.')
    if args.action == 'delete':
        store.delete_password(service, 'credential')
        if store.get_password(service, 'credential') is not None:
            raise ValueError('Acceptance credential cleanup failed.')
    print(json.dumps({'status': 'PASSED', 'action': args.action, 'backend': backend, 'digest': digest}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'FAILED', 'errorType': type(error).__name__,
                          'message': 'OS credential-store acceptance failed; no credential values are printed.'}))
        sys.exit(1)
