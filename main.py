import shlex
import shutil
import threading
from fabric import Connection
from tempfile import TemporaryDirectory
import sys
import psutil
import subprocess

kubectl_path = shutil.which("kubectl")
if len(sys.argv) != 2 and kubectl_path:
    print("depends on having kubectl...")
    print("usage: exec controlplane_hostname")
    sys.exit(1)

CP_USER = "exoadmin"
CP_HOST = sys.argv[1]

tmp = TemporaryDirectory(suffix='_kubism')

# create a kubeconfig in tmp...
kc_path = f"{tmp.name}/admin.kubeconfig"

with Connection(host=CP_HOST, user=CP_USER) as c:
    # c.get('/var/lib/kubernetes/admin.kubeconfig', local=x.name + "admin.kubeconfig")

    if CP_HOST.startswith('kube-master'):
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

    with c.forward_local(0, remote_host='localhost', remote_port=6443):
        # gotta find what port was bound, using psutil...
        port = 0
        pid = psutil.Process().pid
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
        
        commands = [
            f"kubectl config --kubeconfig {kc_path} set-credentials user \
                        --client-certificate {tmp.name}/{tls_files[1]} \
                        --client-key {tmp.name}/{tls_files[2]}",
            f"kubectl config --kubeconfig {kc_path} set-cluster cluster \
                        --server https://localhost:{port} \
                        --certificate-authority {tmp.name}/{tls_files[0]}",
            f"kubectl config --kubeconfig {kc_path} set-context {CP_HOST} \
                        --cluster cluster --user user",
            f"kubectl config --kubeconfig {kc_path} use-context {CP_HOST}"
        ]
        for cmd in commands:
            subprocess.check_call(shlex.split(cmd))
        print(f"Use:\nexport KUBECONFIG={kc_path}")

        forever = threading.Event()
        try:
            forever.wait()
        except KeyboardInterrupt:
            sys.exit(0)
