import threading
from fabric import Connection
from tempfile import TemporaryDirectory
import sys
import psutil
import subprocess
import os
import click
import yaml
from tmp_handler import TempFileHandler

@click.command()
@click.option('--foreground', '-f', help="don't open a subshell", is_flag=True, default=False)
@click.option('--user', '-u', default='exoadmin', help="Login to host as")
@click.argument('host')
def main(foreground, host, user):
    kubeconfig = TempFileHandler()
    kubeconfig.create()

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

                ca = TempFileHandler()
                ca.create()
                r = c.sudo(f"cat {KUBE_CRYPTO_PATH}/{tls_files[0]}", hide=True)
                os.write(ca.fd, bytes(r.stdout, encoding='utf-8'))
                crt = TempFileHandler()
                crt.create()
                r = c.sudo(f"cat {KUBE_CRYPTO_PATH}/{tls_files[1]}", hide=True)
                os.write(crt.fd, bytes(r.stdout, encoding='utf-8'))
                key = TempFileHandler()
                key.create()
                r = c.sudo(f"cat {KUBE_CRYPTO_PATH}/{tls_files[2]}", hide=True)
                os.write(key.fd, bytes(r.stdout, encoding='utf-8'))

                kc_content = yaml.dump(data={
                    'apiVersion': 'v1',
                    'kind': 'Config',
                    'current-context': host,
                    'clusters': [{
                        'name': 'cluster',
                        'cluster': {
                            'certificate-authority': f"/proc/{os.getpid()}/fd/{ca.fd}",
                            'server': f'https://localhost:{port}'
                        }
                    }],
                    'users': [{
                        'name': 'user',
                        'user': {
                            'client-certificate': f"/proc/{os.getpid()}/fd/{crt.fd}",
                            'client-key': f"/proc/{os.getpid()}/fd/{key.fd}"
                        }
                    }],
                    'contexts': [{
                        'name': host,
                        'context': { 'cluster': 'cluster', 'user': 'user' }
                    }]
                })
                os.write(kubeconfig.fd, bytes(kc_content, encoding='utf-8'))

                if foreground:
                    print(f"Use:\nexport KUBECONFIG=/proc/{os.getpid()}/fd/{kubeconfig.fd}")
                    forever = threading.Event()
                    try:
                        forever.wait()
                    except KeyboardInterrupt:
                        sys.exit(0)
                else:
                    os.environ['KUBECONFIG'] = f"/proc/self/fd/{kubeconfig.fd}"
                    subprocess.run([os.environ.get('SHELL')], pass_fds=[kubeconfig.fd, ca.fd, crt.fd, key.fd])

if __name__ == '__main__':
    main()
