import signal
import threading
from fabric import Connection
from tempfile import TemporaryDirectory
import sys
import psutil
import subprocess
import os
import click
import yaml
import contextlib

@contextlib.contextmanager
@click.command()
@click.option('--foreground', '-f', help="don't open a subshell", is_flag=True, default=False)
@click.option('--user', '-u', default='exoadmin', help="Login to host as")
@click.argument('host')
def main(foreground, host, user):
    tmp = TemporaryDirectory(suffix='_kubism')
    # create a kubeconfig in tmp...
    kc_path = f"{tmp.name}/admin.kubeconfig"

    with Connection(host=host, user=user) as c:

        if host.startswith('kube-master'):
            KUBE_CRYPTO_PATH = "/etc/kubernetes/ssl"
            tls_files = [
                'ca-master.pem',
                'admin-cert.pem',
                'admin-key.pem'
            ]
        else:
            KUBE_CRYPTO_PATH = "/var/lib/kubernetes/tls.d"
            tls_files = [
                'ca-controlplane.pem',
                'admin-certificate.pem',
                'admin-private-key.pem'
            ]

        try:
            fwd = c.forward_local(0, remote_host='localhost', remote_port=6443)
        except OSError as e:
            print("failure to connect", e)
        else:
            with fwd:
                # gotta find what port was bound, using psutil...
                port = 0
                for conn in psutil.net_connections(kind='inet'):
                    if conn.status == 'LISTEN' and conn.pid == psutil.Process().pid:
                        port = conn.laddr.port

                if port == 0:
                    print('fail to seek the opened port...')
                    sys.exit(1)

                for tf in tls_files:
                    r = c.sudo(f"cat {KUBE_CRYPTO_PATH}/{tf}", hide=True)
                    with open(f"{tmp.name}/{tf}", mode='w') as f:
                        f.write(r.stdout)

                with open(kc_path, 'w') as f:
                    yaml.dump(stream=f, data={
                        'apiVersion': 'v1',
                        'kind': 'Config',
                        'current-context': host,
                        'clusters': [{
                            'name': 'cluster',
                            'cluster': {
                                'certificate-authority': tls_files[0],
                                'server': f'https://localhost:{port}'
                            }
                        }],
                        'users': [{
                            'name': 'user',
                            'user': {
                                'client-certificate': tls_files[1],
                                'client-key': tls_files[2]
                            }
                        }],
                        'contexts': [{
                            'name': host,
                            'context': { 'cluster': 'cluster', 'user': 'user' }
                        }]
                    })

                _sig_handler()
                if foreground:
                    print(f"Use:\nexport KUBECONFIG={kc_path}")
                    forever = threading.Event()
                    forever.wait()
                else:
                    os.environ['KUBECONFIG'] = kc_path
                    subprocess.run([os.environ.get('SHELL')])

def _exit_handler(s, f):
    print(f"caught signal {s}: {f}")
    sys.exit(0)

def _sig_handler():
    # this should catch most cases
    sigs = [
        signal.SIGTERM,
        signal.SIGQUIT,
        signal.SIGINT,
        signal.SIGHUP
    ]
    for sig in sigs:
        try:
            signal.signal(sig, _exit_handler)
        except Exception as e:
            print(f"{sig}: {e}")

if __name__ == '__main__':
    main()
